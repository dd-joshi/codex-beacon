"""Small authenticated WebSocket client for physical P1 hardware tests."""

from __future__ import annotations

import hmac
import json
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlsplit, urlunsplit

from peri6.protocol.crypto import (
    EnvelopeError,
    auth_proof,
    b64url_decode,
    b64url_encode,
    derive_session_keys,
    open_envelope,
    seal_envelope,
)


SUBPROTOCOL = "peri6.scene.v1"
PATH = "/ws/v1"
PORT = 8765
ID_RE = re.compile(r"^[0-9a-f]{32}$")
DEVICE_ID_RE = re.compile(r"^p6-[a-z0-9-]{3,32}$")
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
HARD_MAX_BODY_BYTES = 3072
HARD_MAX_WEBSOCKET_BYTES = 6144


class ProtocolClientError(RuntimeError):
    """A bounded, user-displayable transport or protocol error."""


class WebSocketLike(Protocol):
    def send(self, payload: str) -> object: ...
    def recv(self) -> object: ...
    def settimeout(self, timeout: float) -> object: ...
    def close(self) -> object: ...
    def getsubprotocol(self) -> str | None: ...


@dataclass(frozen=True, slots=True)
class ConnectionInfo:
    endpoint: str
    device_id: str
    firmware_version: str
    max_body_bytes: int
    max_websocket_bytes: int
    keepalive_interval_ms: int
    capabilities: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ReceivedMessage:
    message_type: str
    sequence: int
    body: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ClientEvent:
    kind: str
    message: str
    body: Mapping[str, Any] | None = None


def normalize_endpoint(value: str) -> str:
    """Return the one supported ws:// endpoint from a hostname/IP or URL."""
    candidate = value.strip()
    if not candidate:
        raise ProtocolClientError("Enter the device hostname or IPv4 address.")
    if "://" not in candidate:
        host = candidate.rstrip("/")
        if "/" in host:
            raise ProtocolClientError("Use a hostname/IP, or the complete /ws/v1 URL.")
        if not re.search(r":\d+$", host):
            host = f"{host}:{PORT}"
        return f"ws://{host}{PATH}"

    parsed = urlsplit(candidate)
    if parsed.scheme != "ws" or not parsed.hostname:
        raise ProtocolClientError("Only private-LAN ws:// endpoints are supported.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProtocolClientError("The endpoint must not contain credentials, query, or fragment.")
    path = parsed.path or PATH
    if path != PATH:
        raise ProtocolClientError(f"The protocol endpoint path must be {PATH}.")
    port = parsed.port or PORT
    netloc = parsed.hostname if port == PORT and parsed.port is None else f"{parsed.hostname}:{port}"
    return urlunsplit(("ws", netloc, PATH, "", ""))


class ProtocolSession:
    """Synchronous authenticated session; the caller owns socket serialization."""

    def __init__(self, socket: WebSocketLike, endpoint: str, session_id: str, keys: Any) -> None:
        self._socket = socket
        self._endpoint = endpoint
        self._session_id = session_id
        self._keys = keys
        self._next_tx_sequence = 1
        self._next_rx_sequence = 1
        self._max_body_bytes = HARD_MAX_BODY_BYTES
        self._max_websocket_bytes = HARD_MAX_WEBSOCKET_BYTES
        self.info: ConnectionInfo | None = None

    @classmethod
    def authenticate(
        cls,
        socket: WebSocketLike,
        *,
        endpoint: str,
        secret: bytes,
        expected_device_id: str | None = None,
        client_name: str = "Peri6 Hardware Test",
        client_version: str = "0.1.0",
        random_bytes: Callable[[int], bytes] = os.urandom,
    ) -> "ProtocolSession":
        if len(secret) != 32:
            raise ProtocolClientError("The local device secret must decode to exactly 32 bytes.")
        if not isinstance(client_name, str) or not 1 <= len(client_name.encode("utf-8")) <= 64:
            raise ProtocolClientError("The client name must contain 1 to 64 UTF-8 bytes.")
        if not isinstance(client_version, str) or not SEMVER_RE.fullmatch(client_version):
            raise ProtocolClientError("The client version must be MAJOR.MINOR.PATCH.")
        selected = socket.getsubprotocol()
        if selected != SUBPROTOCOL:
            raise ProtocolClientError(
                f"Device did not negotiate required WebSocket subprotocol {SUBPROTOCOL}."
            )

        request_id = random_bytes(16).hex()
        client_nonce = random_bytes(16)
        hello = {
            "v": 1,
            "type": "HELLO",
            "request_id": request_id,
            "client_name": client_name,
            "client_version": client_version,
            "client_nonce": b64url_encode(client_nonce),
        }
        _send_json(socket, hello, HARD_MAX_WEBSOCKET_BYTES)
        challenge = _receive_plain_object(socket)
        _require_exact_fields(
            challenge,
            {"v", "type", "request_id", "sid", "device_id", "device_nonce", "auth", "device_proof"},
            "CHALLENGE",
        )
        if challenge.get("v") != 1 or isinstance(challenge.get("v"), bool):
            raise ProtocolClientError("Device returned an unsupported handshake version.")
        if challenge.get("type") != "CHALLENGE" or challenge.get("request_id") != request_id:
            raise ProtocolClientError("Device challenge does not match this HELLO.")
        session_id = challenge.get("sid")
        device_id = challenge.get("device_id")
        if not isinstance(session_id, str) or not ID_RE.fullmatch(session_id):
            raise ProtocolClientError("Device returned an invalid session ID.")
        if not isinstance(device_id, str) or not DEVICE_ID_RE.fullmatch(device_id):
            raise ProtocolClientError("Device returned an invalid device ID.")
        if challenge.get("auth") != "hmac-sha256-v1":
            raise ProtocolClientError("Device returned an unsupported authentication method.")
        device_nonce_text = challenge.get("device_nonce")
        device_proof = challenge.get("device_proof")
        if not isinstance(device_nonce_text, str) or not isinstance(device_proof, str):
            raise ProtocolClientError("Device challenge is missing authentication values.")
        try:
            device_nonce = b64url_decode(device_nonce_text)
            supplied_device_proof = b64url_decode(device_proof)
        except EnvelopeError as exc:
            raise ProtocolClientError("Device challenge contains invalid base64url.") from exc
        if len(device_nonce) != 16 or len(supplied_device_proof) != 32:
            raise ProtocolClientError("Device challenge contains values of the wrong size.")
        expected_proof = b64url_decode(
            auth_proof(
                secret,
                role="device",
                request_id=request_id,
                session_id=session_id,
                client_nonce=client_nonce,
                device_nonce=device_nonce,
            )
        )
        if not hmac.compare_digest(supplied_device_proof, expected_proof):
            raise ProtocolClientError("Device proof failed; endpoint or local secret is wrong.")
        if expected_device_id and device_id != expected_device_id:
            raise ProtocolClientError(
                f"Authenticated device ID is {device_id}, expected {expected_device_id}."
            )

        client_proof = auth_proof(
            secret,
            role="client",
            request_id=request_id,
            session_id=session_id,
            client_nonce=client_nonce,
            device_nonce=device_nonce,
        )
        _send_json(
            socket,
            {
                "v": 1,
                "type": "AUTH",
                "request_id": request_id,
                "sid": session_id,
                "client_proof": client_proof,
            },
            HARD_MAX_WEBSOCKET_BYTES,
        )
        authenticated = _receive_plain_object(socket)
        _require_exact_fields(
            authenticated,
            {"v", "type", "request_id", "sid", "server_proof"},
            "AUTHENTICATED",
        )
        if (
            authenticated.get("v") != 1
            or isinstance(authenticated.get("v"), bool)
            or authenticated.get("type") != "AUTHENTICATED"
            or authenticated.get("request_id") != request_id
            or authenticated.get("sid") != session_id
        ):
            raise ProtocolClientError("AUTHENTICATED response does not match this handshake.")
        server_proof = authenticated.get("server_proof")
        expected_server_proof = auth_proof(
            secret,
            role="server",
            request_id=request_id,
            session_id=session_id,
            client_nonce=client_nonce,
            device_nonce=device_nonce,
        )
        if not isinstance(server_proof, str) or not hmac.compare_digest(
            server_proof, expected_server_proof
        ):
            raise ProtocolClientError("Server proof failed.")

        keys = derive_session_keys(
            secret,
            request_id=request_id,
            session_id=session_id,
            client_nonce=client_nonce,
            device_nonce=device_nonce,
        )
        session = cls(socket, endpoint, session_id, keys)
        capabilities = session.receive()
        if capabilities.message_type != "CAPABILITIES":
            raise ProtocolClientError("First signed device message was not CAPABILITIES.")
        session._accept_capabilities(device_id, capabilities.body)
        return session

    def _accept_capabilities(self, device_id: str, body: Mapping[str, Any]) -> None:
        if body.get("device_id") != device_id:
            raise ProtocolClientError("CAPABILITIES device ID does not match the challenge.")
        firmware_version = body.get("firmware_version")
        max_body = _bounded_int(body.get("max_body_bytes"), 1, HARD_MAX_BODY_BYTES, "max_body_bytes")
        max_ws = _bounded_int(
            body.get("max_websocket_bytes"), max_body, HARD_MAX_WEBSOCKET_BYTES,
            "max_websocket_bytes",
        )
        lease = body.get("lease")
        if not isinstance(lease, dict):
            raise ProtocolClientError("CAPABILITIES lease profile is invalid.")
        keepalive = _bounded_int(
            lease.get("keepalive_interval_ms"), 100, 5000, "keepalive_interval_ms"
        )
        if not isinstance(firmware_version, str):
            raise ProtocolClientError("CAPABILITIES firmware version is invalid.")
        self._max_body_bytes = max_body
        self._max_websocket_bytes = max_ws
        self.info = ConnectionInfo(
            endpoint=self._endpoint,
            device_id=device_id,
            firmware_version=firmware_version,
            max_body_bytes=max_body,
            max_websocket_bytes=max_ws,
            keepalive_interval_ms=keepalive,
            capabilities=dict(body),
        )

    def send_command(self, message_type: str, body: Mapping[str, Any]) -> int:
        sequence = self._next_tx_sequence
        envelope = seal_envelope(
            message_type=message_type,
            session_id=self._session_id,
            sequence=sequence,
            body=body,
            key=self._keys.client_to_device,
        )
        _send_json(self._socket, envelope, self._max_websocket_bytes)
        if sequence == 0xFFFFFFFF:
            raise ProtocolClientError("Controller sequence exhausted; reconnect required.")
        self._next_tx_sequence += 1
        return sequence

    def receive(self) -> ReceivedMessage:
        raw = self._socket.recv()
        if not isinstance(raw, str) or not raw:
            raise ProtocolClientError("WebSocket closed or returned a non-text message.")
        if len(raw.encode("utf-8")) > self._max_websocket_bytes:
            raise ProtocolClientError("Device message exceeds the negotiated frame limit.")
        envelope = _strict_json_object(raw)
        try:
            message_type, sequence, body = open_envelope(
                envelope,
                key=self._keys.device_to_client,
                expected_session_id=self._session_id,
                max_body_bytes=self._max_body_bytes,
                expected_sequence=self._next_rx_sequence,
            )
        except EnvelopeError as exc:
            raise ProtocolClientError(f"Signed device message failed: {exc.code}.") from exc
        if sequence == 0xFFFFFFFF:
            raise ProtocolClientError("Device sequence exhausted; reconnect required.")
        self._next_rx_sequence += 1
        return ReceivedMessage(message_type, sequence, body)

    def settimeout(self, timeout: float) -> None:
        self._socket.settimeout(timeout)

    def close(self) -> None:
        self._socket.close()


class HardwareClient:
    """Background-thread facade suitable for a Tkinter application."""

    def __init__(self, event_callback: Callable[[ClientEvent], None]) -> None:
        self._callback = event_callback
        self._commands: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket: WebSocketLike | None = None
        self._socket_lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def connect(
        self,
        endpoint: str,
        secret: bytes,
        expected_device_id: str | None = None,
    ) -> None:
        if self.running:
            raise ProtocolClientError("A connection attempt is already running.")
        endpoint = normalize_endpoint(endpoint)
        self._commands = queue.Queue()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._worker,
            args=(endpoint, bytes(secret), expected_device_id),
            name="peri6-hardware-client",
            daemon=True,
        )
        self._thread.start()

    def disconnect(self) -> None:
        self._stop.set()
        with self._socket_lock:
            socket = self._socket
        if socket is not None:
            try:
                socket.close()
            except Exception:
                pass

    def load_scene(self, body: Mapping[str, Any]) -> None:
        self._commands.put(("LOAD_SCENE", dict(body)))

    def clear(self) -> None:
        self._commands.put(("CLEAR", None))

    def status(self) -> None:
        self._commands.put(("STATUS", {}))

    def _emit(self, kind: str, message: str, body: Mapping[str, Any] | None = None) -> None:
        try:
            self._callback(ClientEvent(kind, message, body))
        except Exception:
            pass

    def _worker(self, endpoint: str, secret: bytes, expected_device_id: str | None) -> None:
        # Import only in the actual worker so protocol unit tests need no live socket.
        from websocket import (
            WebSocketConnectionClosedException,
            WebSocketTimeoutException,
            create_connection,
        )

        session: ProtocolSession | None = None
        active_scene_id: str | None = None
        next_keepalive = float("inf")
        pending: dict[int, tuple[str, str | None]] = {}
        control_pending = False
        user_stopped = False
        try:
            self._emit("state", f"Connecting to {endpoint} …")
            socket = create_connection(
                endpoint,
                subprotocols=[SUBPROTOCOL],
                timeout=5,
                enable_multithread=True,
                http_proxy_host=None,
                http_proxy_port=None,
            )
            with self._socket_lock:
                self._socket = socket
            session = ProtocolSession.authenticate(
                socket,
                endpoint=endpoint,
                secret=secret,
                expected_device_id=expected_device_id,
            )
            assert session.info is not None
            session.settimeout(0.15)
            self._emit(
                "connected",
                f"Authenticated {session.info.device_id} (firmware {session.info.firmware_version}).",
                session.info.capabilities,
            )

            while not self._stop.is_set():
                now = time.monotonic()
                for _ in range(4):
                    try:
                        command, value = self._commands.get_nowait()
                    except queue.Empty:
                        break
                    if command == "LOAD_SCENE":
                        scene_id = value.get("scene_id") if isinstance(value, dict) else None
                        sequence = session.send_command(command, value)
                        pending[sequence] = (command, scene_id if isinstance(scene_id, str) else None)
                        control_pending = True
                        self._emit("tx", f"LOAD_SCENE sent (seq {sequence}).")
                    elif command == "CLEAR":
                        if active_scene_id is None:
                            self._emit("warning", "No known active scene; request STATUS or send Off.")
                        else:
                            sequence = session.send_command("CLEAR", {"scene_id": active_scene_id})
                            pending[sequence] = ("CLEAR", active_scene_id)
                            control_pending = True
                            self._emit("tx", f"CLEAR sent (seq {sequence}).")
                    elif command == "STATUS":
                        sequence = session.send_command("STATUS", {})
                        pending[sequence] = ("STATUS", None)
                        self._emit("tx", f"STATUS sent (seq {sequence}).")

                now = time.monotonic()
                if active_scene_id and not control_pending and now >= next_keepalive:
                    sequence = session.send_command("KEEPALIVE", {"scene_id": active_scene_id})
                    pending[sequence] = ("KEEPALIVE", active_scene_id)
                    next_keepalive = now + session.info.keepalive_interval_ms / 1000.0

                try:
                    incoming = session.receive()
                except WebSocketTimeoutException:
                    continue
                self._handle_incoming(incoming, pending)
                if incoming.message_type == "ACK":
                    reply_to = incoming.body.get("reply_to")
                    request = pending.pop(reply_to, None) if isinstance(reply_to, int) else None
                    if request:
                        request_type, scene_id = request
                        if request_type == "LOAD_SCENE" and scene_id:
                            active_scene_id = scene_id
                            next_keepalive = time.monotonic() + session.info.keepalive_interval_ms / 1000.0
                            control_pending = False
                        elif request_type == "CLEAR":
                            active_scene_id = None
                            next_keepalive = float("inf")
                            control_pending = False
                elif incoming.message_type == "ERROR":
                    reply_to = incoming.body.get("reply_to")
                    request = pending.pop(reply_to, None) if isinstance(reply_to, int) else None
                    if request and request[0] in {"LOAD_SCENE", "CLEAR"}:
                        control_pending = False
                    if request and request[0] == "KEEPALIVE":
                        active_scene_id = None
                        next_keepalive = float("inf")
                elif incoming.message_type == "STATUS":
                    scene = incoming.body.get("active_scene_id")
                    active_scene_id = scene if isinstance(scene, str) else None
                    next_keepalive = (
                        time.monotonic() + session.info.keepalive_interval_ms / 1000.0
                        if active_scene_id else float("inf")
                    )
        except (ProtocolClientError, OSError, WebSocketConnectionClosedException) as exc:
            user_stopped = self._stop.is_set()
            if not user_stopped:
                self._emit("error", str(exc) or type(exc).__name__)
        except Exception as exc:
            user_stopped = self._stop.is_set()
            if not user_stopped:
                self._emit("error", f"Unexpected client failure: {type(exc).__name__}: {exc}")
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
            with self._socket_lock:
                self._socket = None
            self._emit("disconnected", "Disconnected." if user_stopped else "Connection closed.")

    def _handle_incoming(
        self, incoming: ReceivedMessage, pending: Mapping[int, tuple[str, str | None]]
    ) -> None:
        body = incoming.body
        if incoming.message_type == "ACK":
            reply = body.get("reply_to")
            request = pending.get(reply) if isinstance(reply, int) else None
            if request and request[0] != "KEEPALIVE":
                self._emit("rx", f"ACK for {request[0]} (seq {reply}).", body)
            return
        if incoming.message_type == "ERROR":
            self._emit(
                "error",
                f"Device ERROR {body.get('code', 'UNKNOWN')}: {body.get('detail', '')}",
                body,
            )
            return
        if incoming.message_type == "STATUS":
            self._emit("status", "Renderer status received.", body)
            return
        if incoming.message_type == "BUTTON_EVENT":
            self._emit(
                "event", f"Button {body.get('gesture')} ({body.get('duration_ms')} ms).", body
            )
            return
        if incoming.message_type == "SENSOR_EVENT":
            self._emit("event", f"Ambient level {body.get('level_u16')}.", body)
            return
        self._emit("rx", f"Received {incoming.message_type}.", body)


def _send_json(socket: WebSocketLike, value: Mapping[str, Any], maximum: int) -> None:
    try:
        text = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise ProtocolClientError("Attempted to send non-strict JSON.") from exc
    if len(text.encode("utf-8")) > maximum:
        raise ProtocolClientError("Outgoing WebSocket message exceeds the negotiated limit.")
    socket.send(text)


def _receive_plain_object(socket: WebSocketLike) -> dict[str, Any]:
    raw = socket.recv()
    if not isinstance(raw, str) or not raw:
        raise ProtocolClientError("WebSocket closed during authentication.")
    if len(raw.encode("utf-8")) > HARD_MAX_WEBSOCKET_BYTES:
        raise ProtocolClientError("Handshake response exceeds the frame limit.")
    return _strict_json_object(raw)


def _strict_json_object(raw: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-JSON numeric constant {value}")

    def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON member {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, parse_constant=reject_constant, object_pairs_hook=strict_pairs)
    except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
        raise ProtocolClientError("Received malformed or duplicate-member JSON.") from exc
    if not isinstance(value, dict):
        raise ProtocolClientError("Received JSON root is not an object.")
    return value


def _require_exact_fields(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if set(value) != fields:
        raise ProtocolClientError(f"{name} fields are not the frozen v1 set.")


def _bounded_int(value: object, minimum: int, maximum: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ProtocolClientError(f"CAPABILITIES {name} is outside the supported bound.")
    return value