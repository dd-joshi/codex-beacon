from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codex_beacon.agent_setup import (
    HOOK_EVENTS,
    build_codex_beacon_handler,
    install_global_hooks,
    install_project_hooks,
    uninstall_legacy_global_hooks,
)


class AgentSetupTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Requires Windows cmd.exe")
    def test_windows_command_preserves_quoted_paths_and_hook_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            sender = repository / ".codex" / "hooks" / "codex_beacon_hook.py"
            launcher = repository / "desktop" / "codex-beacon-hook.cmd"
            launcher.write_text(
                f'@echo off\n"{sys.executable}" "{sender}"\n', encoding="utf-8"
            )
            sender.write_text("import sys\nsys.stdout.write(sys.stdin.read())\n", encoding="utf-8")
            handler = build_codex_beacon_handler(repository)
            command = str(handler["commandWindows"])
            other_workspace = root / "Other project's & workspace"
            other_workspace.mkdir()
            payload = {"hook_event_name": "Stop", "session_id": "quoting-test"}
            # Pass a raw command line, as cmd's /c argument is shell syntax,
            # not a normal argv string escaped with C-runtime backslashes.
            result = subprocess.run(
                f'"{os.environ.get("COMSPEC", "cmd.exe")}" /d /s /c {command}',
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=other_workspace,
                timeout=5,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), payload)

    def test_global_install_uses_user_hook_file_and_preserves_peers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            codex_home = root / "user" / ".codex"
            codex_home.mkdir(parents=True)
            peer = {"type": "command", "command": "python peer_hook.py"}
            path = codex_home / "hooks.json"
            path.write_text(
                json.dumps(
                    {
                        "description": "Keep this description",
                        "hooks": {"PreToolUse": [{"hooks": [peer]}]},
                    }
                ),
                encoding="utf-8",
            )

            installed, changed = install_global_hooks(
                repository, codex_home=codex_home
            )

            self.assertTrue(changed)
            self.assertEqual(installed, path.resolve())
            configured = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(configured["hooks"]["PreToolUse"], [{"hooks": [peer]}])
            for event in HOOK_EVENTS:
                handlers = [
                    handler
                    for group in configured["hooks"][event]
                    for handler in group["hooks"]
                ]
                self.assertEqual(len(handlers), 1)
                self.assertNotIn("CODEX_BEACON_CONFIG", handlers[0]["commandWindows"])

    def test_project_install_preserves_peer_hooks_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            hooks_dir = repository / ".codex"
            peer = {
                "type": "command",
                "command": "python peer_hook.py",
                "async": True,
            }
            original = {
                "description": "Keep this description",
                "hooks": {
                    "PreToolUse": [{"matcher": "Bash", "hooks": [peer]}],
                    "SessionStart": [{"hooks": [peer]}],
                },
                "custom": {"preserved": True},
            }
            path = hooks_dir / "hooks.json"
            original_text = json.dumps(original)
            path.write_text(original_text, encoding="utf-8")

            installed, changed = install_project_hooks(repository)
            first = installed.read_text(encoding="utf-8")
            installed_again, changed_again = install_project_hooks(repository)

            self.assertTrue(changed)
            self.assertFalse(changed_again)
            self.assertEqual(installed, installed_again)
            self.assertEqual(first, installed_again.read_text(encoding="utf-8"))
            configured = json.loads(first)
            self.assertEqual(configured["description"], "Keep this description")
            self.assertEqual(configured["custom"], {"preserved": True})
            self.assertEqual(configured["hooks"]["SessionStart"], [{"hooks": [peer]}])

            sender = str(repository / ".codex" / "hooks" / "codex_beacon_hook.py")
            for event in HOOK_EVENTS:
                handlers = [
                    handler
                    for group in configured["hooks"][event]
                    for handler in group["hooks"]
                ]
                ours = [
                    handler
                    for handler in handlers
                    if sender in handler.get("command", "")
                ]
                self.assertEqual(len(ours), 1, event)
                self.assertNotIn("CODEX_BEACON_CONFIG", ours[0]["commandWindows"])
                self.assertIs(ours[0]["async"], False)
                self.assertEqual(ours[0]["timeout"], 3)
            pre_tool_handlers = [
                handler
                for group in configured["hooks"]["PreToolUse"]
                for handler in group["hooks"]
            ]
            self.assertIn(peer, pre_tool_handlers)
            backup = hooks_dir / "hooks.json.codex-beacon.bak"
            self.assertEqual(backup.read_text(encoding="utf-8"), original_text)

    def test_invalid_existing_project_hooks_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            path = repository / ".codex" / "hooks.json"
            path.write_text("{not-json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                install_project_hooks(repository)
            self.assertEqual(path.read_text(encoding="utf-8"), "{not-json")

    def test_project_install_preserves_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            path = repository / ".codex" / "hooks.json"
            path.write_text('\ufeff{"hooks": {}}\n', encoding="utf-8")

            install_project_hooks(repository)

            self.assertTrue(path.read_text(encoding="utf-8").startswith("\ufeff{"))

    def test_project_install_removes_verbose_tool_event_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            path, _ = install_project_hooks(repository)
            document = json.loads(path.read_text(encoding="utf-8"))
            handler = document["hooks"]["UserPromptSubmit"][0]["hooks"][0]
            for event in ("PreToolUse", "PostToolUse"):
                document["hooks"][event] = [{"hooks": [handler]}]
            path.write_text(json.dumps(document), encoding="utf-8")

            install_project_hooks(repository)

            configured = json.loads(path.read_text(encoding="utf-8"))
            for event in ("PreToolUse", "PostToolUse"):
                handlers = [
                    item
                    for group in configured["hooks"].get(event, [])
                    for item in group["hooks"]
                ]
                self.assertFalse(
                    any("codex_beacon_hook.py" in item.get("command", "") for item in handlers)
                )

    def test_legacy_cleanup_removes_only_this_repositorys_global_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            other_repository = self._repository(root / "other")
            codex_home = root / ".codex"
            codex_home.mkdir()
            peer = {"type": "command", "command": "python peer_hook.py"}
            ours = self._legacy_handler(repository)
            other = self._legacy_handler(other_repository)
            path = codex_home / "hooks.json"
            path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [{"hooks": [peer, ours, other]}],
                            "Stop": [{"hooks": [ours, other]}],
                        }
                    }
                ),
                encoding="utf-8",
            )

            removed = uninstall_legacy_global_hooks(
                repository, codex_home=codex_home
            )

            self.assertEqual(removed, [path.resolve()])
            document = json.loads(path.read_text(encoding="utf-8"))
            pre_tool_handlers = document["hooks"]["PreToolUse"][0]["hooks"]
            self.assertEqual(pre_tool_handlers, [peer, other])
            self.assertEqual(document["hooks"]["Stop"][0]["hooks"], [other])

    @staticmethod
    def _legacy_handler(repository: Path) -> dict[str, object]:
        sender = repository / ".codex" / "hooks" / "codex_beacon_hook.py"
        return {
            "type": "command",
            "command": (
                "powershell.exe -NoProfile -Command \""
                "$env:CODEX_BEACON_CONFIG = 'unused'; "
                f"& 'python.exe' '{sender}'\""
            ),
        }

    @staticmethod
    def _repository(root: Path) -> Path:
        repository = root / "Codex Beacon friend's copy"
        python = repository / ".venv" / "Scripts" / "python.exe"
        sender = repository / ".codex" / "hooks" / "codex_beacon_hook.py"
        python.parent.mkdir(parents=True)
        sender.parent.mkdir(parents=True)
        launcher = repository / "desktop" / "codex-beacon-hook.cmd"
        launcher.parent.mkdir(parents=True)
        python.write_bytes(b"python")
        sender.write_text("# sender", encoding="utf-8")
        launcher.write_text("@echo off\n", encoding="utf-8")
        return repository.resolve()


if __name__ == "__main__":
    unittest.main()
