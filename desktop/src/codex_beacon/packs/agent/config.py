"""Local ignored configuration shared by the companion and hook sender."""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path


DEFAULT_AGENT_PORT = 49_326
CONFIG_FILENAME = "agent-hook.json"


@dataclass(frozen=True, slots=True)
class AgentHookConfig:
    endpoint: str
    bearer_token: str

    @property
    def port(self) -> int:
        prefix = "http://127.0.0.1:"
        suffix = "/v1/events"
        if not self.endpoint.startswith(prefix) or not self.endpoint.endswith(suffix):
            raise ValueError("Agent endpoint must use the Codex Beacon loopback format")
        value = self.endpoint[len(prefix) : -len(suffix)]
        try:
            port = int(value)
        except ValueError as exc:
            raise ValueError("Agent endpoint has an invalid port") from exc
        if not 1 <= port <= 65535:
            raise ValueError("Agent endpoint port is outside its valid range")
        return port

    def to_json(self) -> dict[str, object]:
        return {"version": 1, "endpoint": self.endpoint, "bearer_token": self.bearer_token}


def default_agent_config_path() -> Path:
    override = os.environ.get("CODEX_BEACON_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    candidate = _find_project_config(Path.cwd())
    if candidate is not None:
        return candidate
    return Path.cwd() / "desktop" / CONFIG_FILENAME


def ensure_agent_config(path: Path, *, port: int = DEFAULT_AGENT_PORT) -> AgentHookConfig:
    """Explicit-path behavior (tests, custom deployments): plaintext JSON."""

    path = path.resolve()
    if path.exists():
        return load_agent_config(path)
    config = AgentHookConfig(
        endpoint=f"http://127.0.0.1:{port}/v1/events",
        bearer_token=secrets.token_urlsafe(32),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(config.to_json(), stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return config


def ensure_protected_agent_config(*, port: int = DEFAULT_AGENT_PORT) -> AgentHookConfig:
    """Default-path flow: DPAPI-protected per-user store with one-time migration."""

    from .secrets import (
        load_agent_secret,
        migrate_legacy_config,
        save_agent_secret,
        store_exists,
    )

    if not store_exists():
        migrated = migrate_legacy_config(default_agent_config_path())
        if migrated is not None:
            pass  # legacy token scrubbed in place after verified copy
    protected = load_agent_secret()
    if protected is not None:
        return AgentHookConfig(protected.endpoint, protected.bearer_token)
    endpoint = f"http://127.0.0.1:{port}/v1/events"
    try:
        save_agent_secret(endpoint, secrets.token_urlsafe(32))
        protected = load_agent_secret()
    except Exception as exc:  # noqa: BLE001 - fail closed below
        raise ValueError(f"Could not protect Agent credentials: {exc}") from exc
    assert protected is not None
    return AgentHookConfig(protected.endpoint, protected.bearer_token)


def load_agent_config(path: Path) -> AgentHookConfig:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read Agent hook configuration: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Agent hook configuration must contain an object")
    if "bearer_token_dpapi_b64" in value:
        # Protected user-store format: decrypt through the secrets module.
        from .secrets import load_agent_secret

        secret = load_agent_secret(path)
        if secret is None:
            raise ValueError("Agent hook configuration is absent")
        return AgentHookConfig(secret.endpoint, secret.bearer_token)
    if set(value) != {"version", "endpoint", "bearer_token"}:
        raise ValueError("Agent hook configuration fields are not exact")
    if value.get("version") != 1:
        raise ValueError("Unsupported Agent hook configuration version")
    endpoint = value.get("endpoint")
    token = value.get("bearer_token")
    if not isinstance(endpoint, str) or not isinstance(token, str) or len(token) < 32:
        raise ValueError("Agent hook configuration is invalid")
    config = AgentHookConfig(endpoint, token)
    config.port
    return config


def _find_project_config(start: Path) -> Path | None:
    current = start.resolve()
    for directory in (current, *current.parents):
        candidate = directory / "desktop" / CONFIG_FILENAME
        if (directory / ".codex").is_dir() or candidate.exists():
            return candidate
    return None


__all__ = [
    "AgentHookConfig",
    "CONFIG_FILENAME",
    "DEFAULT_AGENT_PORT",
    "default_agent_config_path",
    "ensure_agent_config",
    "load_agent_config",
]
