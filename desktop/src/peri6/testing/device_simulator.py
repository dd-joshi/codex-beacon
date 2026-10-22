"""In-memory reference ESP for scene protocol v1.

It intentionally has no sockets or LED driver.  P0 tests can advance a monotonic
clock deterministically and exercise authentication, sequence rules, validation,
atomic replacement, animation, keepalive, and expiry.
"""

from __future__ import annotations

import hmac
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from peri6.protocol.crypto import (
    EnvelopeError,
    ID_RE,
    SessionKeys,
    auth_proof,
    b64url_decode,
    b64url_encode,
    derive_session_keys,
    open_envelope,
    seal_envelope,
)
from peri6.protocol.model import (
    DEFAULT_CAPABILITIES,
    Capabilities,
    DeviceScene,
    ProtocolValidationError,
    RGB,
    validate_scene_id_body,
)


SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
OFF = (RGB(0, 0, 0),) * 6


class SessionClosed(RuntimeError):
    def __init__(self, reason: str, close_code: int = 1008):
        super().__init__(reason)
        self.reason = reason
        self.close_code = close_code


@dataclass(slots=True)
class _Challenge:
    request_id: str
    session_id: str
    client_nonce: bytes
    device_nonce: bytes
    expires_ms: int


@dataclass(slots=True)
class _ActiveScene:
    scene: DeviceScene
    loaded_ms: int
    expires_ms: int
    start_cells: tuple[RGB, RGB, RGB, RGB, RGB, RGB]


class DeviceSimulator:
    """The executable device-side contract for P0."""

    def __init__(
        self,
        *,
        secret: bytes,
        device_id: str = "p6-c3-000001",
        firmware_version: str = "0.1.0",
        capabilities: Capabilities = DEFAULT_CAPABILITIES,
        random_bytes: Callable[[int], bytes] = os.urandom,
    ) -> None:
        if len(secret) != 32:
            raise ValueError("device secret must contain exactly 32 bytes")
        if not re.fullmatch(r"p6-[a-z0-9-]{3,32}", device_id):
            raise ValueError("invalid device_id")
        if not SEMVER_RE.fullmatch(firmware_version):
            raise ValueError("firmware_version must be MAJOR.MINOR.PATCH")
        self.secret = secret
        self.device_id = device_id
        self.firmware_version = firmware_version
        self.capabilities = capabilities
        self._random_bytes = random_bytes
        self.now_ms = 0
        self.boot_id = self._random_bytes(16).hex()
        self._challenge: _Challenge | None = None
        self.session_id: str | None = None
        self.session_keys: SessionKeys | None = None
        self.session_open = False
        self.expected_client_sequence = 1
        self.next_device_sequence = 1
        self._active: _ActiveScene | None = None

    def begin_handshake(self, hello: Mapping[str, object]) -> dict[str, object]:
        expected = {
            "v",
            "type",
            "request_id",
            "client_name",
            "client_version",
            "client_nonce",
        }
        if (
            set(hello) != expected
            or isinstance(hello.get("v"), bool)
            or hello.get("v") != 1
            or hello.get("type") != "HELLO"
        ):
            raise ValueError("invalid HELLO")
        request_id = hello["request_id"]
        if not isinstance(request_id, str) or not ID_RE.fullmatch(request_id):
            raise ValueError("invalid request_id")
        if not isinstance(hello["client_name"], str) or not 1 <= len(hello["client_name"]) <= 64:
            raise ValueError("invalid client_name")
        if not isinstance(hello["client_version"], str) or not SEMVER_RE.fullmatch(
            hello["client_version"]
        ):
            raise ValueError("invalid client_version")
        client_nonce_value = hello["client_nonce"]
        if not isinstance(client_nonce_value, str):
            raise ValueError("invalid client_nonce")
        client_nonce = b64url_decode(client_nonce_value)
        if len(client_nonce) != 16:
            raise ValueError("client_nonce must contain 16 bytes")
        session_id = self._random_bytes(16).hex()
        device_nonce = self._random_bytes(16)
        self._challenge = _Challenge(
            request_id=request_id,
            session_id=session_id,
            client_nonce=client_nonce,
            device_nonce=device_nonce,
            expires_ms=self.now_ms + 10_000,
        )
        return {
            "v": 1,
            "type": "CHALLENGE",
            "request_id": request_id,
            "sid": session_id,
            "device_id": self.device_id,
            "device_nonce": b64url_encode(device_nonce),
            "auth": "hmac-sha256-v1",
            "device_proof": auth_proof(
                self.secret,
                role="device",
                request_id=request_id,
                session_id=session_id,
                client_nonce=client_nonce,
                device_nonce=device_nonce,
            ),
        }

    def finish_handshake(
        self, auth: Mapping[str, object]
    ) -> tuple[dict[str, object], dict[str, object]]:
        challenge = self._challenge
        self._challenge = None
        expected = {"v", "type", "request_id", "sid", "client_proof"}
        if (
            set(auth) != expected
            or isinstance(auth.get("v"), bool)
            or auth.get("v") != 1
            or auth.get("type") != "AUTH"
        ):
            raise ValueError("invalid AUTH")
        if challenge is None or self.now_ms >= challenge.expires_ms:
            raise ValueError("challenge missing or expired")
        if auth["request_id"] != challenge.request_id or auth["sid"] != challenge.session_id:
            raise ValueError("AUTH does not match the challenge")
        proof = auth["client_proof"]
        if not isinstance(proof, str):
            raise ValueError("invalid client proof")
        expected_proof = auth_proof(
            self.secret,
            role="client",
            request_id=challenge.request_id,
            session_id=challenge.session_id,
            client_nonce=challenge.client_nonce,
            device_nonce=challenge.device_nonce,
        )
        if not hmac.compare_digest(proof, expected_proof):
            raise ValueError("authentication failed")

        self.session_id = challenge.session_id
        self.session_keys = derive_session_keys(
            self.secret,
            request_id=challenge.request_id,
            session_id=challenge.session_id,
            client_nonce=challenge.client_nonce,
            device_nonce=challenge.device_nonce,
        )
        self.session_open = True
        self.expected_client_sequence = 1
        self.next_device_sequence = 1
        authenticated = {
            "v": 1,
            "type": "AUTHENTICATED",
            "request_id": challenge.request_id,
            "sid": challenge.session_id,
            "server_proof": auth_proof(
                self.secret,
                role="server",
                request_id=challenge.request_id,
                session_id=challenge.session_id,
                client_nonce=challenge.client_nonce,
                device_nonce=challenge.device_nonce,
            ),
        }
        return authenticated, self._outgoing(
            "CAPABILITIES",
            self.capabilities.to_body(
                device_id=self.device_id, firmware_version=self.firmware_version
            ),
        )

    def handle_text(self, frame: str) -> dict[str, object]:
        """Validate a complete WebSocket text frame before dispatch."""

        self._require_session()
        if not isinstance(frame, str):
            self._close_session()
            raise SessionClosed("BINARY_OR_NON_TEXT_FRAME", 1003)
        if len(frame.encode("utf-8")) > self.capabilities.max_websocket_bytes:
            self._close_session()
            raise SessionClosed("FRAME_TOO_LARGE", 1009)
        try:
            envelope = json.loads(
                frame,
                parse_constant=lambda value: _reject_json_constant(value),
                object_pairs_hook=_strict_object,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            self._close_session()
            raise SessionClosed("INVALID_JSON", 1008) from exc
        if not isinstance(envelope, dict):
            self._close_session()
            raise SessionClosed("INVALID_ENVELOPE", 1008)
        return self.handle_envelope(envelope)

    def handle_envelope(self, envelope: Mapping[str, object]) -> dict[str, object]:
        self._require_session()
        assert self.session_id is not None and self.session_keys is not None
        try:
            message_type, sequence, body = open_envelope(
                envelope,
                key=self.session_keys.client_to_device,
                expected_session_id=self.session_id,
                max_body_bytes=self.capabilities.max_body_bytes,
                expected_sequence=self.expected_client_sequence,
            )
        except EnvelopeError as exc:
            if exc.code == "SEQUENCE_ERROR":
                sequence = envelope.get("seq")
                assert isinstance(sequence, int) and not isinstance(sequence, bool)
                response = self._error(
                    "SEQUENCE_ERROR",
                    f"expected seq {self.expected_client_sequence}, received {sequence}",
                    reply_to=sequence,
                )
                self._close_session()
                return response
            # A message carrying another SID belongs to an obsolete/foreign
            # socket and must not close the newly authenticated controller.
            if exc.code != "SESSION_MISMATCH":
                self._close_session()
            close_code = 1009 if exc.code == "BODY_TOO_LARGE" else 1008
            raise SessionClosed(exc.code, close_code) from exc

        self.expected_client_sequence += 1
        self._expire_if_needed()

        try:
            if message_type == "LOAD_SCENE":
                scene = DeviceScene.from_body(body, self.capabilities)
                current = self.render_cells(unscaled=True)
                self._active = _ActiveScene(
                    scene=scene,
                    loaded_ms=self.now_ms,
                    expires_ms=self.now_ms + scene.lease_ms,
                    start_cells=current,
                )
                return self._ack(sequence, scene_id=scene.scene_id)
            if message_type == "KEEPALIVE":
                scene_id = validate_scene_id_body(body, "KEEPALIVE")
                if self._active is None or self._active.scene.scene_id != scene_id:
                    raise ProtocolValidationError(
                        "SCENE_MISMATCH", "keepalive does not match the active scene"
                    )
                self._active.expires_ms = self.now_ms + self._active.scene.lease_ms
                return self._ack(sequence, scene_id=scene_id)
            if message_type == "CLEAR":
                scene_id = validate_scene_id_body(body, "CLEAR")
                if self._active is None or self._active.scene.scene_id != scene_id:
                    raise ProtocolValidationError(
                        "SCENE_MISMATCH", "clear does not match the active scene"
                    )
                self._active = None
                return self._ack(sequence, scene_id=scene_id)
            if message_type == "STATUS":
                if body:
                    raise ProtocolValidationError(
                        "INVALID_FIELDS", "STATUS request body must be empty"
                    )
                return self._outgoing("STATUS", self.status_body(reply_to=sequence))
            raise ProtocolValidationError(
                "UNSUPPORTED_TYPE", f"unsupported controller message {message_type}"
            )
        except ProtocolValidationError as exc:
            return self._error(exc.code, exc.detail, reply_to=sequence)

    def advance(self, milliseconds: int) -> None:
        if isinstance(milliseconds, bool) or not isinstance(milliseconds, int) or milliseconds < 0:
            raise ValueError("advance requires a non-negative integer")
        self.now_ms += milliseconds
        self._expire_if_needed()

    def status_body(self, *, reply_to: int | None = None) -> dict[str, object]:
        self._expire_if_needed()
        body: dict[str, object] = {
            "boot_id": self.boot_id,
            "uptime_ms": self.now_ms,
            "scene_state": "active" if self._active else "off",
            "active_scene_id": self._active.scene.scene_id if self._active else None,
            "frame_index": self._frame_index() if self._active else None,
            "lease_remaining_ms": (
                max(0, self._active.expires_ms - self.now_ms) if self._active else 0
            ),
        }
        if reply_to is not None:
            body["reply_to"] = reply_to
        return body

    def emit_button(self, *, event_id: str, gesture: str, duration_ms: int) -> dict[str, object]:
        self._require_session()
        if not ID_RE.fullmatch(event_id):
            raise ValueError("invalid event_id")
        if gesture not in {"tap", "press", "long_press"}:
            raise ValueError("invalid gesture")
        if not isinstance(duration_ms, int) or isinstance(duration_ms, bool) or duration_ms < 0:
            raise ValueError("invalid duration_ms")
        return self._outgoing(
            "BUTTON_EVENT",
            {"event_id": event_id, "gesture": gesture, "duration_ms": duration_ms},
        )

    def emit_ambient(self, *, event_id: str, level_u16: int) -> dict[str, object]:
        self._require_session()
        if not ID_RE.fullmatch(event_id):
            raise ValueError("invalid event_id")
        if (
            isinstance(level_u16, bool)
            or not isinstance(level_u16, int)
            or not 0 <= level_u16 <= 65_535
        ):
            raise ValueError("level_u16 must be an integer from 0 to 65535")
        return self._outgoing(
            "SENSOR_EVENT",
            {"event_id": event_id, "sensor": "ambient", "level_u16": level_u16},
        )

    def render_cells(
        self, *, unscaled: bool = False
    ) -> tuple[RGB, RGB, RGB, RGB, RGB, RGB]:
        self._expire_if_needed()
        if self._active is None:
            return OFF
        active = self._active
        elapsed = self.now_ms - active.loaded_ms
        cells = self._render_timeline(active, elapsed)
        if unscaled:
            return cells
        brightness = active.scene.brightness
        return tuple(
            RGB(
                cell.r * brightness // 255,
                cell.g * brightness // 255,
                cell.b * brightness // 255,
            )
            for cell in cells
        )  # type: ignore[return-value]

    def _render_timeline(
        self, active: _ActiveScene, elapsed: int
    ) -> tuple[RGB, RGB, RGB, RGB, RGB, RGB]:
        scene = active.scene
        cycle = sum(
            frame.transition_ms + frame.hold_ms for frame in scene.keyframes
        )
        source = active.start_cells
        if scene.playback_mode == "loop" and elapsed >= cycle:
            elapsed %= cycle
            source = scene.keyframes[-1].cells
        elif scene.playback_mode == "once" and elapsed >= cycle:
            return scene.keyframes[-1].cells if scene.on_complete == "hold" else OFF

        cursor = 0
        for frame in scene.keyframes:
            transition_end = cursor + frame.transition_ms
            if elapsed < transition_end:
                return _interpolate(source, frame.cells, elapsed - cursor, frame.transition_ms)
            cursor = transition_end
            hold_end = cursor + frame.hold_ms
            if elapsed < hold_end:
                return frame.cells
            cursor = hold_end
            source = frame.cells
        return scene.keyframes[-1].cells

    def _frame_index(self) -> int:
        assert self._active is not None
        scene = self._active.scene
        cycle = sum(frame.transition_ms + frame.hold_ms for frame in scene.keyframes)
        elapsed = self.now_ms - self._active.loaded_ms
        if scene.playback_mode == "loop":
            elapsed %= cycle
        elif elapsed >= cycle:
            return len(scene.keyframes) - 1
        cursor = 0
        for index, frame in enumerate(scene.keyframes):
            cursor += frame.transition_ms + frame.hold_ms
            if elapsed < cursor:
                return index
        return len(scene.keyframes) - 1

    def _expire_if_needed(self) -> None:
        if self._active is not None and self.now_ms >= self._active.expires_ms:
            self._active = None

    def _ack(self, reply_to: int, *, scene_id: str) -> dict[str, object]:
        return self._outgoing(
            "ACK", {"reply_to": reply_to, "scene_id": scene_id, "result": "accepted"}
        )

    def _error(self, code: str, detail: str, *, reply_to: int) -> dict[str, object]:
        return self._outgoing(
            "ERROR", {"reply_to": reply_to, "code": code, "detail": detail[:160]}
        )

    def _outgoing(self, message_type: str, body: Mapping[str, Any]) -> dict[str, object]:
        self._require_session()
        assert self.session_id is not None and self.session_keys is not None
        response = seal_envelope(
            message_type=message_type,
            session_id=self.session_id,
            sequence=self.next_device_sequence,
            body=body,
            key=self.session_keys.device_to_client,
        )
        self.next_device_sequence += 1
        return response

    def _require_session(self) -> None:
        if not self.session_open or self.session_id is None or self.session_keys is None:
            raise SessionClosed("no authenticated session")

    def _close_session(self) -> None:
        self.session_open = False
        self.session_id = None
        self.session_keys = None
        self.expected_client_sequence = 1
        self.next_device_sequence = 1


def _interpolate(
    start: tuple[RGB, RGB, RGB, RGB, RGB, RGB],
    end: tuple[RGB, RGB, RGB, RGB, RGB, RGB],
    elapsed: int,
    duration: int,
) -> tuple[RGB, RGB, RGB, RGB, RGB, RGB]:
    if duration <= 0:
        return end

    def channel(a: int, b: int) -> int:
        return a + (b - a) * elapsed // duration

    return tuple(
        RGB(
            channel(first.r, last.r),
            channel(first.g, last.g),
            channel(first.b, last.b),
        )
        for first, last in zip(start, end)
    )  # type: ignore[return-value]


def _reject_json_constant(value: str):
    raise ValueError(f"non-JSON numeric constant {value}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON member {key}")
        value[key] = child
    return value
