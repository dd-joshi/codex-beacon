"""Idempotent Codex hook setup for Codex Beacon."""

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
    "PermissionRequest",
    "Stop",
)
CODEX_BEACON_SENDER_MARKER = "codex_beacon_hook.py"
BACKUP_SUFFIX = ".codex-beacon.bak"


def default_codex_home() -> Path:
    """Return Codex's configured home, falling back to the normal user home."""

    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def build_codex_beacon_handler(repository: Path) -> dict[str, object]:
    """Build one direct, environment-independent Codex hook handler."""

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
    windows_launcher = repository / "desktop" / "codex-beacon-hook.cmd"
    missing = [path for path in (python, sender, windows_launcher) if not path.is_file()]
    if missing:
        rendered = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Codex Beacon setup files are missing: {rendered}")

    # The entry point supplies its config path directly. Use a small batch
    # launcher because Codex's Windows shell adds another parsing layer around
    # commandWindows. An explicit nested cmd invocation preserves a quoted
    # launcher path even when this repository is stored below a path with spaces.
    command = f'"{python}" "{sender}"'
    return {
        "type": "command",
        "command": command,
        "commandWindows": f'cmd.exe /d /s /c call "{windows_launcher}"',
        "async": False,
        "timeout": 3,
    }


def install_project_hooks(repository: Path) -> tuple[Path, bool]:
    """Merge Codex Beacon hooks into this repository without replacing peers."""

    repository = repository.resolve()
    path = repository / ".codex" / "hooks.json"
    document, had_bom = _load_hook_document(path, "project Codex hooks")
    if not document:
        document = {
            "description": (
                "Project-local lifecycle hooks for privacy-safe Codex Beacon status."
            ),
            "hooks": {},
        }
    hooks = document.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"Existing Codex hooks field must contain an object: {path}")

    # First remove any prior Beacon handlers from every event.  This makes an
    # existing five-event installation migrate down to the lightweight profile
    # instead of leaving PreToolUse and PostToolUse running in parallel.
    for event, raw_groups in list(hooks.items()):
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
                item
                for item in raw_handlers
                if not _is_codex_beacon_handler(item, repository=repository)
            ]
            if retained:
                groups.append(raw_group | {"hooks": retained})
        hooks[event] = groups

    handler = build_codex_beacon_handler(repository)
    for event in HOOK_EVENTS:
        groups = list(hooks.get(event, []))
        groups.append({"hooks": [handler]})
        hooks[event] = groups

    return _write_hook_document(path, document, had_bom)


def install_global_hooks(
    repository: Path,
    *,
    codex_home: Path | None = None,
) -> tuple[Path, bool]:
    """Merge lightweight Beacon hooks into the user's Codex configuration."""

    repository = repository.resolve()
    home = (codex_home or default_codex_home()).expanduser().resolve()
    path = home / "hooks.json"
    document, had_bom = _load_hook_document(path, "user-level Codex hooks")
    if not document:
        document = {
            "description": (
                "User-level lifecycle hooks for privacy-safe Codex Beacon status."
            ),
            "hooks": {},
        }
    hooks = document.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"Existing Codex hooks field must contain an object: {path}")

    for event, raw_groups in list(hooks.items()):
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
                item
                for item in raw_handlers
                if not _is_codex_beacon_handler(item, repository=repository)
            ]
            if retained:
                groups.append(raw_group | {"hooks": retained})
        hooks[event] = groups

    handler = build_codex_beacon_handler(repository)
    for event in HOOK_EVENTS:
        groups = list(hooks.get(event, []))
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
            retained = [item for item in raw_handlers if not _is_codex_beacon_handler(item)]
            if len(retained) != len(raw_handlers):
                changed = True
            if retained:
                groups.append(raw_group | {"hooks": retained})
        hooks[event] = groups
    if not changed:
        return []
    _write_hook_document(path, document, had_bom)
    return [path]


def uninstall_legacy_global_hooks(
    repository: Path,
    *,
    codex_home: Path | None = None,
) -> list[Path]:
    """Remove only global Beacon handlers for ``repository``."""

    home = (codex_home or default_codex_home()).expanduser().resolve()
    path = home / "hooks.json"
    return _uninstall_repository_handlers(path, "Codex hooks", repository)


def uninstall_project_hooks(repository: Path) -> list[Path]:
    """Remove this repository's Beacon handlers from its local hooks file."""

    repository = repository.resolve()
    path = repository / ".codex" / "hooks.json"
    return _uninstall_repository_handlers(path, "project Codex hooks", repository)


def _uninstall_repository_handlers(
    path: Path, label: str, repository: Path
) -> list[Path]:
    """Remove matching Beacon handlers while preserving all unrelated hooks."""

    if not path.exists():
        return []
    document, had_bom = _load_hook_document(path, label)
    hooks = document.get("hooks")
    if not isinstance(hooks, dict):
        raise ValueError(f"Existing {label} field must contain an object: {path}")
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
                item
                for item in raw_handlers
                if not _is_codex_beacon_handler(item, repository=repository)
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


def _is_codex_beacon_handler(value: object, *, repository: Path | None = None) -> bool:
    if not isinstance(value, Mapping):
        return False
    sender = (
        str((repository.resolve() / ".codex" / "hooks" / CODEX_BEACON_SENDER_MARKER))
        if repository is not None
        else None
    )
    commands = (value.get("command"), value.get("commandWindows"))
    for command in commands:
        if not isinstance(command, str):
            continue
        if CODEX_BEACON_SENDER_MARKER not in command:
            continue
        if sender is None or sender.casefold() in command.casefold():
            return True
    return False


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
        description="Install privacy-safe Codex Beacon hooks"
    )
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument(
        "--scope",
        choices=("user", "project"),
        default="user",
        help="Install for every local Codex project (user) or this repository only (project)",
    )
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    if arguments.scope == "user":
        hooks_path, hooks_changed = install_global_hooks(
            arguments.repository, codex_home=arguments.codex_home
        )
        removed_paths = uninstall_project_hooks(arguments.repository)
        scope_label = "User"
    else:
        hooks_path, hooks_changed = install_project_hooks(arguments.repository)
        removed_paths = uninstall_legacy_global_hooks(
            arguments.repository, codex_home=arguments.codex_home
        )
        scope_label = "Project"
    print(
        f"{scope_label} Codex hooks: {hooks_path} "
        f"({'updated' if hooks_changed else 'current'})"
    )
    if removed_paths:
        print(f"Removed duplicate Codex Beacon hooks: {removed_paths[0]}")


if __name__ == "__main__":
    main()


__all__ = [
    "BACKUP_SUFFIX",
    "CODEX_BEACON_SENDER_MARKER",
    "HOOK_EVENTS",
    "build_codex_beacon_handler",
    "default_codex_home",
    "install_global_hooks",
    "install_project_hooks",
    "main",
    "uninstall_legacy_global_hooks",
    "uninstall_codex_beacon_hooks",
    "uninstall_project_hooks",
]
