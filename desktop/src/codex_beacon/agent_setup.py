"""Idempotent user-level Codex hook setup for Codex Beacon."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Mapping


HOOK_EVENTS = (
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "Stop",
)
CODEX_BEACON_COMMAND_MARKERS = ("CODEX_BEACON_CONFIG", "codex_beacon_hook.py")
BACKUP_SUFFIX = ".codex-beacon.bak"


def default_codex_home() -> Path:
    """Return Codex's configured home, falling back to the normal user home."""

    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def build_codex_beacon_handler(repository: Path) -> dict[str, object]:
    """Build one portable-to-this-install Codex hook handler."""

    repository = repository.resolve()
    python_candidates = (
        repository / ".venv" / "Scripts" / "python.exe",
        repository / "desktop" / ".venv" / "Scripts" / "python.exe",
    )
    python = next(
        (path for path in python_candidates if path.is_file()),
        python_candidates[0],
    )
    sender = repository / ".codex" / "hooks" / "codex_beacon_hook.py"
    config = repository / "desktop" / "agent-hook.json"
    missing = [path for path in (python, sender) if not path.is_file()]
    if missing:
        rendered = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Codex Beacon setup files are missing: {rendered}")

    command = (
        "powershell.exe -NoProfile -Command \""
        f"$env:CODEX_BEACON_CONFIG = '{_powershell_literal(config)}'; "
        f"& '{_powershell_literal(python)}' '{_powershell_literal(sender)}'\""
    )
    return {
        "type": "command",
        "command": command,
        "commandWindows": command,
        "async": False,
        "timeout": 3,
    }


def install_global_hooks(
    repository: Path,
    *,
    codex_home: Path | None = None,
) -> tuple[Path, bool]:
    """Merge Codex Beacon hooks into the user's Codex config without replacing peers."""

    home = (codex_home or default_codex_home()).expanduser().resolve()
    path = home / "hooks.json"
    document, had_bom = _load_hook_document(path, "Codex hooks")
    if not document:
        document = {
            "description": (
                "User-level lifecycle hooks, including privacy-safe Codex Beacon status."
            ),
            "hooks": {},
        }
    hooks = document.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"Existing Codex hooks field must contain an object: {path}")

    handler = build_codex_beacon_handler(repository)
    for event in HOOK_EVENTS:
        raw_groups = hooks.get(event, [])
        if not isinstance(raw_groups, list):
            raise ValueError(f"Codex hook event {event!r} must contain a list")
        groups: list[object] = []
        for raw_group in raw_groups:
            if not isinstance(raw_group, dict):
                groups.append(raw_group)
                continue
            raw_handlers = raw_group.get("hooks")
            if not isinstance(raw_handlers, list):
                groups.append(raw_group)
                continue
            retained = [
                item for item in raw_handlers if not _is_codex_beacon_handler(item)
            ]
            if retained:
                groups.append(raw_group | {"hooks": retained})
        groups.append({"hooks": [handler]})
        hooks[event] = groups

    return _write_hook_document(path, document, had_bom)


def uninstall_codex_beacon_hooks(
    *,
    codex_home: Path | None = None,
) -> list[Path]:
    """Remove only Codex Beacon handlers from the user-level Codex hook file."""

    home = (codex_home or default_codex_home()).expanduser().resolve()
    path = home / "hooks.json"
    if not path.exists():
        return []
    document, had_bom = _load_hook_document(path, "Codex hooks")
    hooks = document.get("hooks")
    if not isinstance(hooks, dict):
        raise ValueError(f"Existing Codex hooks field must contain an object: {path}")
    changed = False
    for event, raw_groups in list(hooks.items()):
        if not isinstance(raw_groups, list):
            continue
        groups: list[object] = []
        for raw_group in raw_groups:
            if not isinstance(raw_group, dict):
                groups.append(raw_group)
                continue
            raw_handlers = raw_group.get("hooks")
            if not isinstance(raw_handlers, list):
                groups.append(raw_group)
                continue
            retained = [
                item for item in raw_handlers if not _is_codex_beacon_handler(item)
            ]
            if len(retained) != len(raw_handlers):
                changed = True
            if retained:
                groups.append(raw_group | {"hooks": retained})
        hooks[event] = groups
    if not changed:
        return []
    _write_hook_document(path, document, had_bom)
    return [path]


def _is_codex_beacon_handler(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    commands = (value.get("command"), value.get("commandWindows"))
    for command in commands:
        if not isinstance(command, str):
            continue
        if all(marker in command for marker in CODEX_BEACON_COMMAND_MARKERS):
            return True
    return False


def _powershell_literal(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def _load_hook_document(path: Path, label: str) -> tuple[dict[str, object], bool]:
    if not path.exists():
        return {}, False
    source = path.read_text(encoding="utf-8")
    had_bom = source.startswith("\ufeff")
    try:
        document = json.loads(source.removeprefix("\ufeff"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Existing {label} file is not valid JSON: {path}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"Existing {label} file must contain an object: {path}")
    return document, had_bom


def _write_hook_document(
    path: Path,
    document: Mapping[str, object],
    had_bom: bool,
) -> tuple[Path, bool]:
    rendered = ("\ufeff" if had_bom else "") + json.dumps(
        document, indent=2, ensure_ascii=False
    ) + "\n"
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    changed = previous != rendered
    if changed:
        if path.exists():
            backup = path.with_name(f"{path.name}{BACKUP_SUFFIX}")
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
        _atomic_write(path, rendered)
    return path, changed


def _atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install privacy-safe Codex Beacon hooks for this Windows user"
    )
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path)
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    hooks_path, hooks_changed = install_global_hooks(
        arguments.repository,
        codex_home=arguments.codex_home,
    )
    print(
        f"Codex hooks: {hooks_path} "
        f"({'updated' if hooks_changed else 'current'})"
    )


if __name__ == "__main__":
    main()


__all__ = [
    "BACKUP_SUFFIX",
    "CODEX_BEACON_COMMAND_MARKERS",
    "HOOK_EVENTS",
    "build_codex_beacon_handler",
    "default_codex_home",
    "install_global_hooks",
    "main",
    "uninstall_codex_beacon_hooks",
]
