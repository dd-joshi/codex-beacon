"""Reconnect-safe production device manager for one Peri6 renderer.

The manager owns transport liveness, but not application freshness.  Its input
is a generation-stamped, expiring ``DeviceScene`` selected by the desktop host.
It never derives desired state from device STATUS and never extends a lease for
an output that is no longer the current fresh host output.
"""

from __future__ import annotations

import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping

from websocket import (
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
    create_connection,
)

from peri6.protocol.crypto import b64url_encode
from peri6.protocol.model import DeviceScene, SCENE_ID_RE

from .client import (
    ProtocolClientError,
    ProtocolSession,
    ReceivedMessage,
    SUBPROTOCOL,
    normalize_endpoint,
)


CLIENT_NAME = "Peri6 Desktop"
CLIENT_VERSION = "0.1.0"
SOCKET_CONNECT_TIMEOUT_SECONDS = 5.0
SOCKET_POLL_SECONDS = 0.15
RESPONSE_TIMEOUT_SECONDS = 2.0
RECONNECT_DELAYS_SECONDS = (1.0, 2.0, 4.0, 8.0, 16.0, 30.0)
AUTH_FAILURE_DELAY_SECONDS = 30.0
MAX_DEDUPLICATED_EVENT_IDS = 256
EVENT_ID_RE = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True, slots=True)
class DeviceEvent:
    """A structured, secret-free event emitted from the manager thread."""

    kind: str
    message: str
    generation: int | None = None
    body: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class _DesiredState:
    version: int
    generation: int
    scene: DeviceScene | None
    valid_until_ns: int | None

    @property
    def stamp(self) -> tuple[int, int]:
        return self.generation, self.version

    def fresh(self, now_ns: int) -> bool:
        return (
            self.scene is not None
            and self.valid_until_ns is not None
            and now_ns < self.valid_until_ns
        )


@dataclass(frozen=True, slots=True)
class _AppliedScene:
    scene_id: str
    stamp: tuple[int, int]
    valid_until_ns: int


@dataclass(frozen=True, slots=True)
class _PendingCommand:
    kind: str
    sent_ns: int
    scene_id: str | None = None
    stamp: tuple[int, int] | None = None
    initial_status: bool = False


class DeviceManager:
    """Background device session driven only by current, expiring host state."""

    def __init__(self, callback: Callable[[DeviceEvent], None]) -> None:
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._callback = callback
        self._state_lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._socket_lock = threading.Lock()
        self._desired = _DesiredState(0, -1, None, None)
        self._status_requested = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket: Any | None = None
        self._seen_event_ids: set[str] = set()
        self._event_id_order: deque[str] = deque()

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def connect(
        self,
        endpoint: str,
        secret: bytes,
        expected_device_id: str | None = None,
    ) -> None:
        """Start connecting and keep reconnecting until ``disconnect`` is called."""

        normalized = normalize_endpoint(endpoint)
        secret_copy = bytes(secret)
        if len(secret_copy) != 32:
            raise ProtocolClientError("The local device secret must contain exactly 32 bytes.")
        with self._lifecycle_lock:
            if self.running:
                raise ProtocolClientError("The device manager is already running.")
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._worker,
                args=(normalized, secret_copy, expected_device_id),
                name="peri6-device-manager",
                daemon=True,
            )
            self._thread.start()

    def disconnect(self) -> None:
        """Stop reconnecting and make a bounded best effort to clear owned output."""

        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=0.5)
        if thread is not None and thread.is_alive():
            with self._socket_lock:
                socket = self._socket
            if socket is not None:
                try:
                    socket.close()
                except Exception:
                    pass

    def set_desired_scene(
        self,
        scene: DeviceScene | None,
        generation: int,
        valid_until_monotonic_ns: int | None,
    ) -> None:
        """Replace desired output; lower-generation late callbacks are ignored."""

        if scene is not None and not isinstance(scene, DeviceScene):
            raise TypeError("scene must be a DeviceScene or None")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ValueError("generation must be a non-negative integer")
        if scene is None:
            if valid_until_monotonic_ns is not None:
                raise ValueError("a neutral desired state must not have an expiry")
        elif (
            isinstance(valid_until_monotonic_ns, bool)
            or not isinstance(valid_until_monotonic_ns, int)
        ):
            raise ValueError("a desired scene requires a monotonic expiry in nanoseconds")

        with self._state_lock:
            current = self._desired
            if generation < current.generation:
                return
            now_ns = time.monotonic_ns()
            if (
                generation == current.generation
                and scene is not None
                and current.scene is not None
                and current.fresh(now_ns)
                and valid_until_monotonic_ns is not None
                and now_ns < valid_until_monotonic_ns
                and _same_rendered_scene(current.scene, scene)
            ):
                # Packs may refresh semantic data and host freshness more often than
                # the physical pixels change.  Preserve the transport stamp so an
                # in-flight LOAD/KEEPALIVE remains current and the renderer does not
                # receive another full scene for identical output.
                self._desired = _DesiredState(
                    version=current.version,
                    generation=generation,
                    scene=scene,
                    valid_until_ns=valid_until_monotonic_ns,
                )
                return
            self._desired = _DesiredState(
                version=current.version + 1,
                generation=generation,
                scene=scene,
                valid_until_ns=valid_until_monotonic_ns if scene is not None else None,
            )

    def status(self) -> None:
        """Request a signed renderer status; repeated outstanding requests coalesce."""

        with self._state_lock:
            self._status_requested = True

    def _worker(
        self, endpoint: str, secret: bytes, expected_device_id: str | None
    ) -> None:
        reconnect_index = 0
        try:
            while not self._stop.is_set():
                session: ProtocolSession | None = None
                socket_connected = False
                authenticated = False
                self._emit(
                    "connecting",
                    f"Connecting to {endpoint}.",
                    body={"endpoint": endpoint},
                )
                try:
                    socket = create_connection(
                        endpoint,
                        subprotocols=[SUBPROTOCOL],
                        timeout=SOCKET_CONNECT_TIMEOUT_SECONDS,
                        enable_multithread=True,
                        http_proxy_host=None,
                        http_proxy_port=None,
                    )
                    socket_connected = True
                    with self._socket_lock:
                        self._socket = socket
                    session = ProtocolSession.authenticate(
                        socket,
                        endpoint=endpoint,
                        secret=secret,
                        expected_device_id=expected_device_id,
                        client_name=CLIENT_NAME,
                        client_version=CLIENT_VERSION,
                    )
                    authenticated = True
                    reconnect_index = 0
                    assert session.info is not None
                    session.settimeout(SOCKET_POLL_SECONDS)
                    self._emit(
                        "connected",
                        f"Authenticated {session.info.device_id}.",
                        body={
                            "endpoint": endpoint,
                            "device_id": session.info.device_id,
                            "firmware_version": session.info.firmware_version,
                            "capabilities": dict(session.info.capabilities),
                        },
                    )
                    self._run_session(session)
                except (
                    ProtocolClientError,
                    OSError,
                    WebSocketConnectionClosedException,
                    WebSocketTimeoutException,
                ) as exc:
                    if not self._stop.is_set():
                        self._emit(
                            "error",
                            str(exc) or type(exc).__name__,
                            body={"error_type": type(exc).__name__, "retryable": True},
                        )
                except Exception as exc:
                    if not self._stop.is_set():
                        self._emit(
                            "error",
                            f"Unexpected device-manager failure: {type(exc).__name__}: {exc}",
                            body={"error_type": type(exc).__name__, "retryable": True},
                        )
                finally:
                    if session is not None:
                        try:
                            session.close()
                        except Exception:
                            pass
                    with self._socket_lock:
                        self._socket = None

                if self._stop.is_set():
                    break
                if authenticated:
                    self._emit("disconnected", "Device connection lost.")
                delay = RECONNECT_DELAYS_SECONDS[
                    min(reconnect_index, len(RECONNECT_DELAYS_SECONDS) - 1)
                ]
                reconnect_index += 1
                if socket_connected and not authenticated:
                    delay = max(delay, AUTH_FAILURE_DELAY_SECONDS)
                self._emit(
                    "reconnecting",
                    f"Retrying in {delay:g} seconds.",
                    body={"delay_seconds": delay, "attempt": reconnect_index},
                )
                self._stop.wait(delay)
        finally:
            self._emit("disconnected", "Disconnected.")

    def _run_session(self, session: ProtocolSession) -> None:
        assert session.info is not None
        pending: dict[int, _PendingCommand] = {}
        applied: _AppliedScene | None = None
        observed_scene_id: str | None = None
        rejected_stamp: tuple[int, int] | None = None
        next_keepalive_ns = 0
        resync_complete = False

        status_sequence = session.send_command("STATUS", {})
        pending[status_sequence] = _PendingCommand(
            "status", time.monotonic_ns(), initial_status=True
        )

        while not self._stop.is_set():
            now_ns = time.monotonic_ns()
            timeout_candidate = _oldest_overdue_command(pending, now_ns)

            # Once a response reaches its deadline, do not enqueue more work.  Give
            # the already-authenticated socket one final bounded receive so an ACK
            # that is queued at the threshold is processed instead of discarded.
            if timeout_candidate is None:
                desired = self._desired_snapshot()
                desired_fresh = desired.fresh(now_ns)
                control_pending = any(
                    command.kind in {"load", "clear"} for command in pending.values()
                )

                if resync_complete and not control_pending:
                    if desired_fresh and rejected_stamp != desired.stamp:
                        if applied is None or applied.stamp != desired.stamp:
                            sent = self._send_load_if_current(session, desired)
                            if sent is not None:
                                sequence, scene_id = sent
                                pending[sequence] = _PendingCommand(
                                    "load",
                                    time.monotonic_ns(),
                                    scene_id=scene_id,
                                    stamp=desired.stamp,
                                )
                        elif (
                            now_ns >= next_keepalive_ns
                            and not any(
                                command.kind == "keepalive" for command in pending.values()
                            )
                        ):
                            sequence = self._send_keepalive_if_current(
                                session, desired, applied.scene_id
                            )
                            if sequence is not None:
                                pending[sequence] = _PendingCommand(
                                    "keepalive",
                                    time.monotonic_ns(),
                                    scene_id=applied.scene_id,
                                    stamp=desired.stamp,
                                )
                                next_keepalive_ns = (
                                    now_ns
                                    + session.info.keepalive_interval_ms * 1_000_000
                                )
                    else:
                        target = applied.scene_id if applied is not None else observed_scene_id
                        if target is not None:
                            sequence = session.send_command("CLEAR", {"scene_id": target})
                            pending[sequence] = _PendingCommand(
                                "clear",
                                time.monotonic_ns(),
                                scene_id=target,
                                stamp=desired.stamp,
                            )

                if (
                    resync_complete
                    and not any(command.kind == "status" for command in pending.values())
                    and self._take_status_request()
                ):
                    sequence = session.send_command("STATUS", {})
                    pending[sequence] = _PendingCommand("status", time.monotonic_ns())

            try:
                incoming = session.receive()
            except WebSocketTimeoutException:
                if timeout_candidate is not None:
                    raise _response_timeout_error(*timeout_candidate)
                continue

            if incoming.message_type == "ACK":
                request = self._pop_ack_request(incoming, pending)
                assert request.scene_id is not None
                if request.kind == "load":
                    accepted_expiry = self._fresh_expiry_for_stamp(request.stamp)
                    if accepted_expiry is not None:
                        applied = _AppliedScene(
                            request.scene_id, request.stamp, accepted_expiry
                        )
                        observed_scene_id = None
                        rejected_stamp = None
                        next_keepalive_ns = (
                            time.monotonic_ns()
                            + session.info.keepalive_interval_ms * 1_000_000
                        )
                        self._emit(
                            "scene_loaded",
                            "Fresh desired scene accepted.",
                            generation=self._stamp_generation(request.stamp),
                            body={"scene_id": request.scene_id},
                        )
                    else:
                        applied = None
                        observed_scene_id = request.scene_id
                        self._emit(
                            "warning",
                            "Stale LOAD acknowledgment ignored; scene will be cleared.",
                            generation=self._stamp_generation(request.stamp),
                            body={"scene_id": request.scene_id},
                        )
                elif request.kind == "clear":
                    if applied is not None and applied.scene_id == request.scene_id:
                        applied = None
                    if observed_scene_id == request.scene_id:
                        observed_scene_id = None
                    self._emit(
                        "scene_cleared",
                        "Scene cleared.",
                        generation=self._stamp_generation(request.stamp),
                        body={"scene_id": request.scene_id},
                    )
                elif request.kind == "keepalive":
                    if not self._stamp_is_current_and_fresh(request.stamp):
                        if applied is not None and applied.scene_id == request.scene_id:
                            observed_scene_id = applied.scene_id
                            applied = None
            elif incoming.message_type == "ERROR":
                request = self._pop_error_request(incoming, pending)
                code = incoming.body.get("code")
                if request is not None:
                    if request.kind == "load" and self._stamp_is_current(request.stamp):
                        rejected_stamp = request.stamp
                    elif request.kind in {"keepalive", "clear"}:
                        if applied is not None and applied.scene_id == request.scene_id:
                            applied = None
                        if observed_scene_id == request.scene_id:
                            observed_scene_id = None
                    elif request.kind == "status" and request.initial_status:
                        resync_complete = True
                generation = self._stamp_generation(request.stamp) if request else None
                self._emit(
                    "device_error",
                    f"Device rejected {request.kind if request else 'command'}: {code}.",
                    generation=generation,
                    body=dict(incoming.body),
                )
                if code == "SEQUENCE_ERROR":
                    raise ProtocolClientError("Device reported a sequence error.")
            elif incoming.message_type == "STATUS":
                request = self._pop_status_request(incoming, pending)
                if request.initial_status:
                    resync_complete = True
                active_id = self._status_scene_id(incoming.body)
                observed_scene_id = active_id
                if applied is not None and applied.scene_id != active_id:
                    applied = None
                desired_at_receipt = self._desired_snapshot()
                self._emit(
                    "status",
                    "Renderer status received.",
                    generation=self._event_generation(desired_at_receipt),
                    body=dict(incoming.body),
                )
            elif incoming.message_type == "BUTTON_EVENT":
                self._handle_button(incoming.body)
            elif incoming.message_type == "SENSOR_EVENT":
                self._handle_sensor(incoming.body)
            else:
                self._emit(
                    "warning",
                    f"Unexpected signed device message {incoming.message_type}.",
                    body=dict(incoming.body),
                )

            if timeout_candidate is not None and timeout_candidate[0] in pending:
                raise _response_timeout_error(*timeout_candidate)

        self._best_effort_clear(session, applied, observed_scene_id, pending)

    def _send_load_if_current(
        self, session: ProtocolSession, desired: _DesiredState
    ) -> tuple[int, str] | None:
        assert desired.scene is not None
        materialized = replace(desired.scene, scene_id=b64url_encode(os.urandom(16)))
        with self._state_lock:
            current = self._desired
            if current.stamp != desired.stamp or not current.fresh(time.monotonic_ns()):
                return None
            sequence = session.send_command("LOAD_SCENE", materialized.to_body())
        return sequence, materialized.scene_id

    def _send_keepalive_if_current(
        self, session: ProtocolSession, desired: _DesiredState, scene_id: str
    ) -> int | None:
        with self._state_lock:
            current = self._desired
            if current.stamp != desired.stamp or not current.fresh(time.monotonic_ns()):
                return None
            return session.send_command("KEEPALIVE", {"scene_id": scene_id})

    def _best_effort_clear(
        self,
        session: ProtocolSession,
        applied: _AppliedScene | None,
        observed_scene_id: str | None,
        pending: Mapping[int, _PendingCommand],
    ) -> None:
        targets = [
            command.scene_id
            for command in reversed(tuple(pending.values()))
            if command.kind == "load" and command.scene_id is not None
        ]
        if applied is not None:
            targets.append(applied.scene_id)
        if observed_scene_id is not None:
            targets.append(observed_scene_id)
        sent: set[str] = set()
        for target in targets:
            if target in sent:
                continue
            sent.add(target)
            try:
                session.send_command("CLEAR", {"scene_id": target})
            except Exception:
                return

    def _pop_ack_request(
        self, incoming: ReceivedMessage, pending: dict[int, _PendingCommand]
    ) -> _PendingCommand:
        body = incoming.body
        if set(body) != {"reply_to", "scene_id", "result"} or body.get("result") != "accepted":
            raise ProtocolClientError("Device ACK body is invalid.")
        reply_to = body.get("reply_to")
        scene_id = body.get("scene_id")
        if isinstance(reply_to, bool) or not isinstance(reply_to, int):
            raise ProtocolClientError("Device ACK reply_to is invalid.")
        request = pending.pop(reply_to, None)
        if (
            request is None
            or request.kind not in {"load", "clear", "keepalive"}
            or not isinstance(scene_id, str)
            or scene_id != request.scene_id
        ):
            raise ProtocolClientError("Device ACK does not match an outstanding command.")
        return request

    def _pop_error_request(
        self, incoming: ReceivedMessage, pending: dict[int, _PendingCommand]
    ) -> _PendingCommand | None:
        body = incoming.body
        if set(body) != {"reply_to", "code", "detail"}:
            raise ProtocolClientError("Device ERROR body is invalid.")
        reply_to = body.get("reply_to")
        code = body.get("code")
        detail = body.get("detail")
        if (
            isinstance(reply_to, bool)
            or not isinstance(reply_to, int)
            or not isinstance(code, str)
            or not isinstance(detail, str)
        ):
            raise ProtocolClientError("Device ERROR body is invalid.")
        return pending.pop(reply_to, None)

    def _pop_status_request(
        self, incoming: ReceivedMessage, pending: dict[int, _PendingCommand]
    ) -> _PendingCommand:
        reply_to = incoming.body.get("reply_to")
        if isinstance(reply_to, bool) or not isinstance(reply_to, int):
            raise ProtocolClientError("Device STATUS reply_to is invalid.")
        request = pending.pop(reply_to, None)
        if request is None or request.kind != "status":
            raise ProtocolClientError("Device STATUS does not match an outstanding request.")
        return request

    def _status_scene_id(self, body: Mapping[str, Any]) -> str | None:
        state = body.get("scene_state")
        scene_id = body.get("active_scene_id")
        if state == "off" and scene_id is None:
            return None
        if state == "active" and isinstance(scene_id, str) and SCENE_ID_RE.fullmatch(scene_id):
            return scene_id
        raise ProtocolClientError("Device STATUS scene state is invalid.")

    def _handle_button(self, body: Mapping[str, Any]) -> None:
        if set(body) != {"event_id", "gesture", "duration_ms"}:
            raise ProtocolClientError("BUTTON_EVENT body is invalid.")
        event_id = body.get("event_id")
        gesture = body.get("gesture")
        duration = body.get("duration_ms")
        if (
            not isinstance(event_id, str)
            or not EVENT_ID_RE.fullmatch(event_id)
            or gesture not in {"tap", "press", "long_press"}
            or isinstance(duration, bool)
            or not isinstance(duration, int)
            or duration < 0
        ):
            raise ProtocolClientError("BUTTON_EVENT body is invalid.")
        if not self._remember_event_id(event_id):
            return
        desired = self._desired_snapshot()
        self._emit(
            "button",
            f"Button {gesture} received.",
            generation=self._event_generation(desired),
            body=dict(body),
        )

    def _handle_sensor(self, body: Mapping[str, Any]) -> None:
        if set(body) != {"event_id", "sensor", "level_u16"}:
            raise ProtocolClientError("SENSOR_EVENT body is invalid.")
        event_id = body.get("event_id")
        level = body.get("level_u16")
        if (
            not isinstance(event_id, str)
            or not EVENT_ID_RE.fullmatch(event_id)
            or body.get("sensor") != "ambient"
            or isinstance(level, bool)
            or not isinstance(level, int)
            or not 0 <= level <= 65_535
        ):
            raise ProtocolClientError("SENSOR_EVENT body is invalid.")
        if not self._remember_event_id(event_id):
            return
        desired = self._desired_snapshot()
        self._emit(
            "sensor",
            "Ambient sensor event received.",
            generation=self._event_generation(desired),
            body=dict(body),
        )

    def _remember_event_id(self, event_id: str) -> bool:
        if event_id in self._seen_event_ids:
            return False
        self._seen_event_ids.add(event_id)
        self._event_id_order.append(event_id)
        while len(self._event_id_order) > MAX_DEDUPLICATED_EVENT_IDS:
            oldest = self._event_id_order.popleft()
            self._seen_event_ids.discard(oldest)
        return True

    def _desired_snapshot(self) -> _DesiredState:
        with self._state_lock:
            return self._desired

    @staticmethod
    def _event_generation(desired: _DesiredState) -> int | None:
        return desired.generation if desired.generation >= 0 else None

    @staticmethod
    def _stamp_generation(stamp: tuple[int, int] | None) -> int | None:
        return stamp[0] if stamp is not None and stamp[0] >= 0 else None

    def _stamp_is_current(self, stamp: tuple[int, int] | None) -> bool:
        if stamp is None:
            return False
        with self._state_lock:
            return self._desired.stamp == stamp

    def _stamp_is_current_and_fresh(self, stamp: tuple[int, int] | None) -> bool:
        return self._fresh_expiry_for_stamp(stamp) is not None

    def _fresh_expiry_for_stamp(self, stamp: tuple[int, int] | None) -> int | None:
        if stamp is None:
            return None
        with self._state_lock:
            if self._desired.stamp != stamp or not self._desired.fresh(time.monotonic_ns()):
                return None
            return self._desired.valid_until_ns

    def _take_status_request(self) -> bool:
        with self._state_lock:
            requested = self._status_requested
            self._status_requested = False
            return requested

    def _emit(
        self,
        kind: str,
        message: str,
        *,
        generation: int | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> None:
        try:
            self._callback(DeviceEvent(kind, message, generation, body))
        except Exception:
            pass


def _same_rendered_scene(left: DeviceScene, right: DeviceScene) -> bool:
    """Compare the device-visible scene while ignoring its one-use identity."""

    return (
        left.lease_ms == right.lease_ms
        and left.brightness == right.brightness
        and left.playback_mode == right.playback_mode
        and left.on_complete == right.on_complete
        and left.keyframes == right.keyframes
    )


def _oldest_overdue_command(
    pending: Mapping[int, _PendingCommand], now_ns: int
) -> tuple[int, _PendingCommand] | None:
    if not pending:
        return None
    sequence, command = min(pending.items(), key=lambda item: item[1].sent_ns)
    timeout_ns = int(RESPONSE_TIMEOUT_SECONDS * 1_000_000_000)
    if now_ns - command.sent_ns < timeout_ns:
        return None
    return sequence, command


def _response_timeout_error(sequence: int, command: _PendingCommand) -> ProtocolClientError:
    age_ms = max(0, (time.monotonic_ns() - command.sent_ns) // 1_000_000)
    command_name = {
        "load": "LOAD_SCENE",
        "clear": "CLEAR",
        "keepalive": "KEEPALIVE",
        "status": "STATUS",
    }.get(command.kind, command.kind.upper())
    return ProtocolClientError(
        f"Device response timed out waiting for {command_name} "
        f"(seq {sequence}, age {age_ms} ms)."
    )
