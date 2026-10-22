"""Local bootstrap configuration for an optional development device.

Codex Beacon's supported mode is the software-only phone status page and does
not need this file.  The legacy desktop transport can still read an ignored
``desktop/local-config.json`` supplied by hand.  Callers must treat this module
as a bootstrap boundary and never display or log ``secret``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from codex_beacon.protocol.crypto import EnvelopeError, b64url_decode
from codex_beacon.transport.client import ProtocolClientError, normalize_endpoint


@dataclass(frozen=True, slots=True)
class LocalDeviceConfig:
    path: Path
    endpoint: str
    expected_device_id: str
    secret: bytes


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_config_path() -> Path:
    return repository_root() / "desktop" / "local-config.json"


def load_local_device_config(path: Path) -> LocalDeviceConfig:
    """Load the ignored prototype config without exposing its device secret."""

    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ProtocolClientError(
            f"Local configuration is absent: {path}. "
            "Codex Beacon does not need a device; use the phone status page."
        ) from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProtocolClientError("Desktop local configuration is not valid JSON.") from exc

    expected_fields = {"endpoint", "expected_device_id", "device_secret_b64url"}
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise ProtocolClientError("Desktop local configuration fields are not exact.")
    endpoint = value.get("endpoint")
    expected_device_id = value.get("expected_device_id")
    secret_text = value.get("device_secret_b64url")
    if not all(isinstance(item, str) for item in (endpoint, expected_device_id, secret_text)):
        raise ProtocolClientError("Desktop local configuration values must be strings.")
    try:
        secret = b64url_decode(secret_text)
    except EnvelopeError as exc:
        raise ProtocolClientError("Desktop local device secret is invalid.") from exc
    if len(secret) != 32:
        raise ProtocolClientError("Desktop local device secret must contain 32 bytes.")

    return LocalDeviceConfig(
        path=path,
        endpoint=normalize_endpoint(endpoint),
        expected_device_id=expected_device_id,
        secret=secret,
    )


__all__ = [
    "LocalDeviceConfig",
    "default_config_path",
    "load_local_device_config",
    "repository_root",
]
