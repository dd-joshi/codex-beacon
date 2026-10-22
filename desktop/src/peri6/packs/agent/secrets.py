"""Per-user protected storage for Agent bridge secrets.

Secrets (bearer token, workspace salt) live outside the repository in
``%LOCALAPPDATA%\\Peri6\\secrets`` and are encrypted at rest with DPAPI
(CRYPTPROTECT_UI_FORBIDDEN). The file ACL is restricted to the current user.
Nothing in this module logs or returns secret material through exceptions.

A legacy plaintext ``desktop/agent-hook.json`` is migrated once: after the
protected copy is verified, the legacy token value is replaced with an empty
string and a ``migrated_to_user_store`` marker so no plaintext token remains
in the repository.
"""

from __future__ import annotations

import base64
import ctypes
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_DPAPI_DESCRIPTION = b"peri6-agent-secret"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1
_STORE_FILENAME = "agent-secret.json"
_LEGACY_TOKEN_PLACEHOLDER = ""


class SecretStoreError(Exception):
    """Raised when protected storage cannot be used safely."""


@dataclass(frozen=True, slots=True)
class AgentSecret:
    endpoint: str
    bearer_token: str
    store_path: Path


def secrets_directory() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Local")
        return Path(base) / "Peri6" / "secrets"
    return Path.home() / ".peri6" / "secrets"


def store_path() -> Path:
    return secrets_directory() / _STORE_FILENAME


def _blob_struct():
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    return _Blob


def _dpapi_transform(data: bytes, protect: bool) -> bytes:
    if sys.platform != "win32":
        raise SecretStoreError("DPAPI protection requires Windows")
    blob_type = _blob_struct()
    buffer = ctypes.create_string_buffer(data, len(data))
    source = blob_type(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    result = blob_type()
    crypt32 = ctypes.windll.crypt32
    if protect:
        ok = crypt32.CryptProtectData(
            ctypes.byref(source),
            _DPAPI_DESCRIPTION,
            None,
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(result),
        )
    else:
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(result),
        )
    if not ok:
        action = "protection" if protect else "unprotection"
        raise SecretStoreError(f"DPAPI {action} failed")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)


def restrict_to_user(path: Path) -> bool:
    """Best-effort user-only ACL. Returns True when applied or already safe."""

    if sys.platform != "win32":
        try:
            os.chmod(path, 0o600)
            return True
        except OSError:
            return False
    domain = os.environ.get("USERDOMAIN")
    user = os.environ.get("USERNAME")
    if not domain or not user:
        return False
    account = f"{domain}\\{user}"
    try:
        remove = subprocess.run(
            ["icacls", str(path), "/inheritance:r"],
            capture_output=True,
            check=False,
        )
        grant = subprocess.run(
            ["icacls", str(path), "/grant:r", f"{account}:F"],
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return remove.returncode == 0 and grant.returncode == 0


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass

def save_agent_secret(endpoint: str, bearer_token: str, path: Path | None = None) -> Path:
    if not endpoint or not bearer_token:
        raise SecretStoreError("endpoint and bearer_token are required")
    target = path or store_path()
    blob = _dpapi_transform(bearer_token.encode("utf-8"), protect=True)
    document = {
        "version": 1,
        "endpoint": endpoint,
        "bearer_token_dpapi_b64": base64.b64encode(blob).decode("ascii"),
    }
    _atomic_write(target, (json.dumps(document, indent=2) + "\n").encode("utf-8"))
    if not restrict_to_user(target):
        # Fail closed: never leave an unprotected secret behind.
        target.unlink(missing_ok=True)
        raise SecretStoreError("could not restrict secret file to the current user")
    return target


def load_agent_secret(path: Path | None = None) -> AgentSecret | None:
    target = path or store_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SecretStoreError("protected secret file is not valid JSON") from exc
    expected = {"version", "endpoint", "bearer_token_dpapi_b64"}
    if not isinstance(document, dict) or set(document) != expected:
        raise SecretStoreError("protected secret file fields are not exact")
    if document.get("version") != 1:
        raise SecretStoreError("unsupported protected secret version")
    endpoint = document.get("endpoint")
    blob_b64 = document.get("bearer_token_dpapi_b64")
    if not isinstance(endpoint, str) or not isinstance(blob_b64, str):
        raise SecretStoreError("protected secret file values are invalid")
    try:
        blob = base64.b64decode(blob_b64, validate=True)
        token = _dpapi_transform(blob, protect=False).decode("utf-8")
    except (ValueError, SecretStoreError) as exc:
        raise SecretStoreError(f"protected secret is unreadable: {exc}") from exc
    if not token:
        raise SecretStoreError("protected secret file contains an empty token")
    return AgentSecret(endpoint=endpoint, bearer_token=token, store_path=target)


def store_exists(path: Path | None = None) -> bool:
    return (path or store_path()).is_file()


def migrate_legacy_config(
    legacy_path: Path, target: Path | None = None
) -> tuple[Path, bool] | None:
    """Migrate a plaintext legacy config into the protected store.

    Returns (store_path, created) or None when there is nothing to migrate.
    The legacy file keeps its endpoint; its token value is scrubbed only after
    a verified protected copy exists.
    """

    try:
        raw = legacy_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SecretStoreError("legacy agent config is not valid JSON") from exc
    if not isinstance(document, dict):
        raise SecretStoreError("legacy agent config must contain an object")
    if document.get("migrated_to_user_store") is True:
        return None
    token = document.get("bearer_token")
    endpoint = document.get("endpoint")
    if not isinstance(endpoint, str) or not isinstance(token, str) or len(token) < 32:
        return None
    target = save_agent_secret(endpoint, token, target)
    reloaded = load_agent_secret(target)
    if reloaded is None or reloaded.bearer_token != token:
        raise SecretStoreError("migration verification failed; legacy file untouched")
    document["bearer_token"] = _LEGACY_TOKEN_PLACEHOLDER
    document["migrated_to_user_store"] = True
    _atomic_write(legacy_path, (json.dumps(document, indent=2) + "\n").encode("utf-8"))
    restrict_to_user(legacy_path)
    return target, True


def resolve_agent_config_path() -> Path:
    """Config resolution order: env override, protected store, then legacy."""

    override = os.environ.get("PERI6_AGENT_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    existing = load_agent_secret()
    if existing is not None:
        return existing.store_path
    return store_path()


__all__ = [
    "AgentSecret",
    "SecretStoreError",
    "load_agent_secret",
    "migrate_legacy_config",
    "resolve_agent_config_path",
    "restrict_to_user",
    "save_agent_secret",
    "secrets_directory",
    "store_exists",
    "store_path",
]
