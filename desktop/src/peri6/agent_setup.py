"""Idempotent user-level Codex Agent setup for a Peri6 workspace."""

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
CLAUDE_HOOK_EVENT = "UserPromptSubmit"
PERI6_COMMAND_MARKERS = ("PERI6_AGENT_CONFIG", "peri6_agent_hook.py")
VSCODE_CLI_SETTING = "chatgpt.cliExecutable"


def default_codex_home() -> Path:
    """Return Codex's configured home, falling back to the normal user home."""

    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def default_vscode_user_settings() -> Path:
    """Return the normal VS Code user-settings path on Windows."""

    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")
    return (Path(appdata).expanduser() / "Code" / "User" / "settings.json").resolve()


def default_claude_home() -> Path:
    """Return Claude Code's configured home, falling back to the normal user home."""

    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".claude").resolve()


def build_peri6_handler(repository: Path) -> dict[str, object]:
    """Build one portable-to-this-install hook handler."""

    repository = repository.resolve()
    python_candidates = (
        repository / ".venv" / "Scripts" / "python.exe",
        repository / "desktop" / ".venv" / "Scripts" / "python.exe",
    )
    python = next((path for path in python_candidates if path.is_file()), python_candidates[0])
    sender = repository / ".codex" / "hooks" / "peri6_agent_hook.py"
    config = repository / "desktop" / "agent-hook.json"
    missing = [path for path in (python, sender) if not path.is_file()]
    if missing:
        rendered = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Peri6 setup files are missing: {rendered}")

    command = (
        "powershell.exe -NoProfile -Command \""
        f"$env:PERI6_AGENT_CONFIG = '{_powershell_literal(config)}'; "
        f"& '{_powershell_literal(python)}' '{_powershell_literal(sender)}'\""
    )
    return {
        "type": "command",
        "command": command,
        "commandWindows": command,
        "async": False,
        "timeout": 3,
    }


def build_claude_handler(repository: Path) -> dict[str, object]:
    """Build the Claude Code equivalent of the Peri6 lifecycle hook."""

    repository = repository.resolve()
    python_candidates = (
        repository / ".venv" / "Scripts" / "python.exe",
        repository / "desktop" / ".venv" / "Scripts" / "python.exe",
    )
    python = next((path for path in python_candidates if path.is_file()), python_candidates[0])
    sender = repository / ".claude" / "hooks" / "peri6_agent_hook.py"
    config = repository / "desktop" / "agent-hook.json"
    missing = [path for path in (python, sender) if not path.is_file()]
    if missing:
        rendered = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Peri6 setup files are missing: {rendered}")

    command = (
        "powershell.exe -NoProfile -Command \""
        f"$env:PERI6_AGENT_CONFIG = '{_powershell_literal(config)}'; "
        f"& '{_powershell_literal(python)}' '{_powershell_literal(sender)}'\""
    )
    return {
        "type": "command",
        "command": command,
        "async": False,
        "timeout": 3,
    }


def install_claude_hooks(
    repository: Path,
    *,
    claude_home: Path | None = None,
) -> tuple[Path, bool]:
    """Merge the Peri6 prompt hook into Claude Code without replacing peers."""

    home = (claude_home or default_claude_home()).expanduser().resolve()
    path = home / "settings.json"
    document, had_bom = _load_hook_document(path, "Claude settings")
    hooks = document.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"Existing Claude hooks field must contain an object: {path}")

    raw_groups = hooks.get(CLAUDE_HOOK_EVENT, [])
    if not isinstance(raw_groups, list):
        raise ValueError(f"Claude hook event {CLAUDE_HOOK_EVENT!r} must contain a list")
    groups: list[object] = []
    for raw_group in raw_groups:
        if not isinstance(raw_group, dict):
            groups.append(raw_group)
            continue
        raw_handlers = raw_group.get("hooks")
        if not isinstance(raw_handlers, list):
            groups.append(raw_group)
            continue
        retained = [item for item in raw_handlers if not _is_peri6_handler(item)]
        if retained:
            groups.append(raw_group | {"hooks": retained})
    groups.append({"matcher": "", "hooks": [build_claude_handler(repository)]})
    hooks[CLAUDE_HOOK_EVENT] = groups
    return _write_hook_document(path, document, had_bom)


def uninstall_peri6_hooks(
    *,
    codex_home: Path | None = None,
    claude_home: Path | None = None,
) -> list[Path]:
    """Remove only Peri6 handlers from user-level Codex and Claude hook files."""

    candidates = (
        ((codex_home or default_codex_home()).expanduser().resolve() / "hooks.json", "Codex hooks"),
        ((claude_home or default_claude_home()).expanduser().resolve() / "settings.json", "Claude settings"),
    )
    changed_paths: list[Path] = []
    for path, label in candidates:
        if not path.exists():
            continue
        document, had_bom = _load_hook_document(path, label)
        hooks = document.get("hooks")
        if not isinstance(hooks, dict):
            raise ValueError(f"Existing {label} hooks field must contain an object: {path}")
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
                retained = [item for item in raw_handlers if not _is_peri6_handler(item)]
                if len(retained) != len(raw_handlers):
                    changed = True
                if retained:
                    groups.append(raw_group | {"hooks": retained})
            hooks[event] = groups
        if changed:
            _write_hook_document(path, document, had_bom)
            changed_paths.append(path)
    return changed_paths


def install_global_hooks(
    repository: Path,
    *,
    codex_home: Path | None = None,
) -> tuple[Path, bool]:
    """Merge Peri6 hooks into the user's Codex config without replacing peers."""

    home = (codex_home or default_codex_home()).expanduser().resolve()
    path = home / "hooks.json"
    had_bom = False
    if path.exists():
        source = path.read_text(encoding="utf-8")
        had_bom = source.startswith("\ufeff")
        try:
            document = json.loads(source.removeprefix("\ufeff"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Existing Codex hooks file is not valid JSON: {path}") from exc
        if not isinstance(document, dict):
            raise ValueError(f"Existing Codex hooks file must contain an object: {path}")
    else:
        document = {
            "description": (
                "User-level lifecycle hooks, including privacy-safe Peri6 Agent state."
            ),
            "hooks": {},
        }

    hooks = document.get("hooks")
    if not isinstance(hooks, dict):
        raise ValueError(f"Existing Codex hooks field must contain an object: {path}")

    handler = build_peri6_handler(repository)
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
            retained = [item for item in raw_handlers if not _is_peri6_handler(item)]
            if retained:
                groups.append(raw_group | {"hooks": retained})
        groups.append({"hooks": [handler]})
        hooks[event] = groups

    bom = "\ufeff" if had_bom else ""
    rendered = bom + json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    changed = previous != rendered
    if changed:
        if path.exists():
            backup = path.with_name(f"{path.name}.peri6.bak")
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
        _atomic_write(path, rendered)
    return path, changed


def install_vscode_cli_override(
    codex_executable: Path,
    *,
    settings_path: Path | None = None,
) -> tuple[Path, bool]:
    """Set VS Code's user-level Codex executable while preserving JSONC settings."""

    executable = codex_executable.expanduser().resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"Codex executable does not exist: {executable}")
    path = (settings_path or default_vscode_user_settings()).expanduser().resolve()
    if path.exists():
        previous = path.read_text(encoding="utf-8")
    else:
        previous = "{}\n"
    rendered = _set_jsonc_object_property(
        previous,
        VSCODE_CLI_SETTING,
        str(executable),
    )
    changed = previous != rendered
    if changed:
        if path.exists():
            backup = path.with_name(f"{path.name}.peri6.bak")
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
        _atomic_write(path, rendered)
    return path, changed


def _set_jsonc_object_property(source: str, key: str, value: str) -> str:
    """Minimally set a top-level JSONC property without discarding comments."""

    opening, closing = _jsonc_root_object_bounds(source)
    properties = _jsonc_top_level_properties(source, opening, closing)
    matches = [item for item in properties if item[0] == key]
    if len(matches) > 1:
        raise ValueError(f"VS Code settings contain duplicate {key!r} properties")
    encoded = json.dumps(value, ensure_ascii=False)
    if matches:
        _, value_start, value_end, _ = matches[0]
        return source[:value_start] + encoded + source[value_end:]

    newline = "\r\n" if "\r\n" in source else "\n"
    indent = "  "
    if properties:
        first_key_start = properties[0][3]
        line_start = source.rfind("\n", opening + 1, first_key_start) + 1
        candidate = source[line_start:first_key_start]
        if candidate and candidate.isspace() and "\r" not in candidate:
            indent = candidate
    entry = f"{json.dumps(key)}: {encoded}"
    comma = "," if properties else ""
    remainder = source[opening + 1 : closing]
    if remainder.startswith(("\n", "\r\n")):
        insertion = f"{newline}{indent}{entry}{comma}"
    else:
        insertion = f"{newline}{indent}{entry}{comma}{newline}"
    return source[: opening + 1] + insertion + source[opening + 1 :]


def _jsonc_root_object_bounds(source: str) -> tuple[int, int]:
    start = _skip_jsonc_trivia(source, 0, len(source))
    if start >= len(source) or source[start] != "{":
        raise ValueError("VS Code settings must contain one JSON object")
    closing = _scan_jsonc_container(source, start, len(source)) - 1
    if _skip_jsonc_trivia(source, closing + 1, len(source)) != len(source):
        raise ValueError("VS Code settings contain data after the root object")
    return start, closing


def _jsonc_top_level_properties(
    source: str,
    opening: int,
    closing: int,
) -> list[tuple[str, int, int, int]]:
    properties: list[tuple[str, int, int, int]] = []
    cursor = _skip_jsonc_trivia(source, opening + 1, closing)
    while cursor < closing:
        if source[cursor] == ",":
            cursor = _skip_jsonc_trivia(source, cursor + 1, closing)
            if cursor == closing:
                break
            raise ValueError("VS Code settings contain an unexpected comma")
        if source[cursor] != '"':
            raise ValueError("VS Code settings property names must be quoted")
        key_start = cursor
        key_end = _scan_jsonc_string(source, cursor, closing)
        try:
            key = json.loads(source[cursor:key_end])
        except json.JSONDecodeError as exc:
            raise ValueError("VS Code settings contain an invalid property name") from exc
        cursor = _skip_jsonc_trivia(source, key_end, closing)
        if cursor >= closing or source[cursor] != ":":
            raise ValueError("VS Code settings property is missing ':'")
        value_start = _skip_jsonc_trivia(source, cursor + 1, closing)
        value_end = _scan_jsonc_value(source, value_start, closing)
        properties.append((key, value_start, value_end, key_start))
        cursor = _skip_jsonc_trivia(source, value_end, closing)
        if cursor == closing:
            break
        if source[cursor] != ",":
            raise ValueError("VS Code settings properties must be comma-separated")
        cursor = _skip_jsonc_trivia(source, cursor + 1, closing)
        if cursor == closing:
            break
    return properties


def _scan_jsonc_value(source: str, start: int, limit: int) -> int:
    if start >= limit:
        raise ValueError("VS Code settings contain a missing value")
    first = source[start]
    if first == '"':
        return _scan_jsonc_string(source, start, limit)
    if first in "[{":
        return _scan_jsonc_container(source, start, limit)
    cursor = start
    while cursor < limit:
        if source[cursor] in ",}":
            break
        if source.startswith("//", cursor) or source.startswith("/*", cursor):
            break
        if source[cursor].isspace():
            break
        cursor += 1
    if cursor == start:
        raise ValueError("VS Code settings contain a missing value")
    return cursor


def _scan_jsonc_container(source: str, start: int, limit: int) -> int:
    pairs = {"{": "}", "[": "]"}
    stack = [pairs[source[start]]]
    cursor = start + 1
    while cursor < limit:
        if source[cursor] == '"':
            cursor = _scan_jsonc_string(source, cursor, limit)
            continue
        if source.startswith("//", cursor):
            newline = source.find("\n", cursor + 2, limit)
            cursor = limit if newline < 0 else newline + 1
            continue
        if source.startswith("/*", cursor):
            end = source.find("*/", cursor + 2, limit)
            if end < 0:
                raise ValueError("VS Code settings contain an unterminated comment")
            cursor = end + 2
            continue
        character = source[cursor]
        if character in pairs:
            stack.append(pairs[character])
        elif character in "}]":
            if not stack or character != stack.pop():
                raise ValueError("VS Code settings contain mismatched brackets")
            if not stack:
                return cursor + 1
        cursor += 1
    raise ValueError("VS Code settings contain an unterminated object or array")


def _scan_jsonc_string(source: str, start: int, limit: int) -> int:
    cursor = start + 1
    while cursor < limit:
        if source[cursor] == "\\":
            cursor += 2
            continue
        if source[cursor] == '"':
            return cursor + 1
        if source[cursor] in "\r\n":
            break
        cursor += 1
    raise ValueError("VS Code settings contain an unterminated string")


def _skip_jsonc_trivia(source: str, start: int, limit: int) -> int:
    cursor = start
    while cursor < limit:
        if source[cursor].isspace() or source[cursor] == "\ufeff":
            cursor += 1
            continue
        if source.startswith("//", cursor):
            newline = source.find("\n", cursor + 2, limit)
            return limit if newline < 0 else _skip_jsonc_trivia(source, newline + 1, limit)
        if source.startswith("/*", cursor):
            end = source.find("*/", cursor + 2, limit)
            if end < 0:
                raise ValueError("VS Code settings contain an unterminated comment")
            cursor = end + 2
            continue
        break
    return cursor


def _is_peri6_handler(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    commands = (value.get("command"), value.get("commandWindows"))
    return any(
        isinstance(command, str)
        and all(marker in command for marker in PERI6_COMMAND_MARKERS)
        for command in commands
    )


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
            backup = path.with_name(f"{path.name}.peri6.bak")
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
        description="Install privacy-safe Peri6 Agent hooks for this Windows user"
    )
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--claude-home", type=Path)
    parser.add_argument("--codex-executable", type=Path)
    parser.add_argument("--vscode-settings", type=Path)
    parser.add_argument("--skip-vscode", action="store_true")
    parser.add_argument("--skip-claude", action="store_true")
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    hooks_path, hooks_changed = install_global_hooks(
        arguments.repository,
        codex_home=arguments.codex_home,
    )
    print(f"Codex hooks: {hooks_path} ({'updated' if hooks_changed else 'current'})")
    if arguments.skip_claude:
        print("Claude hooks: skipped")
    else:
        claude_path, claude_changed = install_claude_hooks(
            arguments.repository,
            claude_home=arguments.claude_home,
        )
        print(
            f"Claude hooks: {claude_path} "
            f"({'updated' if claude_changed else 'current'})"
        )
    if not arguments.skip_vscode:
        if arguments.codex_executable is None:
            raise SystemExit("--codex-executable is required unless --skip-vscode is used")
        settings_path, settings_changed = install_vscode_cli_override(
            arguments.codex_executable,
            settings_path=arguments.vscode_settings,
        )
        print(
            f"VS Code settings: {settings_path} "
            f"({'updated' if settings_changed else 'current'})"
        )


if __name__ == "__main__":
    main()


__all__ = [
    "HOOK_EVENTS",
    "CLAUDE_HOOK_EVENT",
    "VSCODE_CLI_SETTING",
    "build_claude_handler",
    "build_peri6_handler",
    "default_claude_home",
    "default_codex_home",
    "default_vscode_user_settings",
    "install_claude_hooks",
    "install_global_hooks",
    "install_vscode_cli_override",
    "main",
    "uninstall_peri6_hooks",
]
