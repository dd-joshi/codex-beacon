"""Dependency-free HMAC framing for scene protocol v1."""

from __future__ import annotations

import base64
import binascii
import hmac
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


ID_RE = re.compile(r"^[0-9a-f]{32}$")
TYPE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
B64_RE = re.compile(r"^[A-Za-z0-9_-]*$")
MAX_SEQUENCE = 0xFFFFFFFF


class EnvelopeError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class SessionKeys:
    client_to_device: bytes
    device_to_client: bytes


def b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    if not isinstance(value, str) or not B64_RE.fullmatch(value):
        raise EnvelopeError("INVALID_BASE64URL", "invalid base64url characters")
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(
            value + padding, altchars=b"-_", validate=True
        )
    except (binascii.Error, ValueError) as exc:
        raise EnvelopeError("INVALID_BASE64URL", "invalid base64url value") from exc
    if b64url_encode(decoded) != value:
        raise EnvelopeError("INVALID_BASE64URL", "base64url value is not canonical")
    return decoded


def auth_proof(
    secret: bytes,
    *,
    role: str,
    request_id: str,
    session_id: str,
    client_nonce: bytes,
    device_nonce: bytes,
) -> str:
    _validate_auth_values(secret, role, request_id, session_id, client_nonce, device_nonce)
    transcript = _auth_transcript(
        request_id, session_id, client_nonce, device_nonce
    )
    return b64url_encode(hmac.digest(secret, role.encode("ascii") + b"\x00" + transcript, "sha256"))


def derive_session_keys(
    secret: bytes,
    *,
    request_id: str,
    session_id: str,
    client_nonce: bytes,
    device_nonce: bytes,
) -> SessionKeys:
    _validate_auth_values(
        secret, "session", request_id, session_id, client_nonce, device_nonce
    )
    transcript = _auth_transcript(
        request_id, session_id, client_nonce, device_nonce
    )
    pseudorandom_key = hmac.digest(secret, b"session\x00" + transcript, "sha256")
    return SessionKeys(
        client_to_device=hmac.digest(
            pseudorandom_key, b"PERI6-C2D-V1", "sha256"
        ),
        device_to_client=hmac.digest(
            pseudorandom_key, b"PERI6-D2C-V1", "sha256"
        ),
    )


def seal_envelope(
    *, message_type: str, session_id: str, sequence: int, body: Mapping[str, Any], key: bytes
) -> dict[str, object]:
    _validate_envelope_header(message_type, session_id, sequence)
    try:
        body_bytes = json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EnvelopeError("INVALID_JSON", "body is not strict JSON") from exc
    encoded_body = b64url_encode(body_bytes)
    mac = hmac.digest(
        key,
        _mac_input(message_type, session_id, sequence, encoded_body),
        "sha256",
    )
    return {
        "v": 1,
        "type": message_type,
        "sid": session_id,
        "seq": sequence,
        "body": encoded_body,
        "mac": b64url_encode(mac),
    }


def open_envelope(
    envelope: Mapping[str, object],
    *,
    key: bytes,
    expected_session_id: str,
    max_body_bytes: int,
    expected_sequence: int,
) -> tuple[str, int, dict[str, Any]]:
    if set(envelope) != {"v", "type", "sid", "seq", "body", "mac"}:
        raise EnvelopeError("INVALID_ENVELOPE", "envelope fields are not exact")
    if isinstance(envelope["v"], bool) or envelope["v"] != 1:
        raise EnvelopeError("UNSUPPORTED_VERSION", "only protocol v1 is supported")
    message_type = envelope["type"]
    session_id = envelope["sid"]
    sequence = envelope["seq"]
    encoded_body = envelope["body"]
    encoded_mac = envelope["mac"]
    if not isinstance(message_type, str) or not isinstance(session_id, str):
        raise EnvelopeError("INVALID_ENVELOPE", "type and sid must be strings")
    _validate_envelope_header(message_type, session_id, sequence)
    if session_id != expected_session_id:
        raise EnvelopeError("SESSION_MISMATCH", "message belongs to another session")
    if not isinstance(encoded_body, str) or not isinstance(encoded_mac, str):
        raise EnvelopeError("INVALID_ENVELOPE", "body and mac must be strings")
    supplied_mac = b64url_decode(encoded_mac)
    expected_mac = hmac.digest(
        key,
        _mac_input(message_type, session_id, sequence, encoded_body),
        "sha256",
    )
    if len(supplied_mac) != 32 or not hmac.compare_digest(supplied_mac, expected_mac):
        raise EnvelopeError("BAD_MAC", "message authentication failed")
    if sequence != expected_sequence:
        raise EnvelopeError(
            "SEQUENCE_ERROR",
            f"expected sequence {expected_sequence}, received {sequence}",
        )
    body_bytes = b64url_decode(encoded_body)
    if len(body_bytes) > max_body_bytes:
        raise EnvelopeError("BODY_TOO_LARGE", "decoded body exceeds capability")
    try:
        body = json.loads(
            body_bytes.decode("utf-8"),
            parse_constant=lambda value: _reject_json_constant(value),
            object_pairs_hook=_strict_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise EnvelopeError("INVALID_JSON", "body is not a UTF-8 JSON value") from exc
    if not isinstance(body, dict):
        raise EnvelopeError("INVALID_BODY", "body must decode to a JSON object")
    return message_type, sequence, body


def _reject_json_constant(value: str):
    raise ValueError(f"non-JSON numeric constant {value}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON member {key}")
        value[key] = child
    return value


def _auth_transcript(
    request_id: str, session_id: str, client_nonce: bytes, device_nonce: bytes
) -> bytes:
    return (
        b"PERI6-AUTH-V1\x00"
        + bytes.fromhex(request_id)
        + bytes.fromhex(session_id)
        + client_nonce
        + device_nonce
    )


def _validate_auth_values(
    secret: bytes,
    role: str,
    request_id: str,
    session_id: str,
    client_nonce: bytes,
    device_nonce: bytes,
) -> None:
    if len(secret) != 32:
        raise ValueError("device secret must contain exactly 32 bytes")
    if role not in {"device", "client", "server", "session"}:
        raise ValueError("invalid authentication role")
    if not ID_RE.fullmatch(request_id) or not ID_RE.fullmatch(session_id):
        raise ValueError("request and session IDs must be 16-byte lowercase hex")
    if len(client_nonce) != 16 or len(device_nonce) != 16:
        raise ValueError("authentication nonces must contain exactly 16 bytes")


def _validate_envelope_header(message_type: str, session_id: str, sequence: object) -> None:
    if not TYPE_RE.fullmatch(message_type):
        raise EnvelopeError("INVALID_TYPE", "invalid message type")
    if not ID_RE.fullmatch(session_id):
        raise EnvelopeError("INVALID_SESSION", "invalid session ID")
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise EnvelopeError("INVALID_SEQUENCE", "sequence must be an integer")
    if not 1 <= sequence <= MAX_SEQUENCE:
        raise EnvelopeError("INVALID_SEQUENCE", "sequence is outside uint32 range")


def _mac_input(
    message_type: str, session_id: str, sequence: int, encoded_body: str
) -> bytes:
    return (
        f"PERI6-MSG-V1\n1\n{message_type}\n{session_id}\n"
        f"{sequence}\n{encoded_body}"
    ).encode("ascii")
