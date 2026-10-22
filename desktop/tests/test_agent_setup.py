from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from peri6.agent_setup import (
    HOOK_EVENTS,
    VSCODE_CLI_SETTING,
    install_global_hooks,
    install_vscode_cli_override,
)


class AgentSetupTests(unittest.TestCase):
    def test_global_install_preserves_peer_hooks_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            codex_home = root / "user" / ".codex"
            codex_home.mkdir(parents=True)
            peer = {
                "type": "command",
                "command": "python peer_hook.py",
                "async": True,
            }
            old_peri6 = {
                "type": "command",
                "command": (
                    "PERI6_AGENT_CONFIG=old python old/peri6_agent_hook.py"
                ),
            }
            original = {
                "description": "Keep this description",
                "hooks": {
                    "PreToolUse": [{"matcher": "Bash", "hooks": [peer, old_peri6]}],
                    "SessionStart": [{"hooks": [peer]}],
                },
                "custom": {"preserved": True},
            }
            path = codex_home / "hooks.json"
            original_text = json.dumps(original)
            path.write_text(original_text, encoding="utf-8")

            installed, changed = install_global_hooks(
                repository,
                codex_home=codex_home,
            )
            first = installed.read_text(encoding="utf-8")
            installed_again, changed_again = install_global_hooks(
                repository,
                codex_home=codex_home,
            )

            self.assertTrue(changed)
            self.assertFalse(changed_again)
            self.assertEqual(installed, installed_again)
            self.assertEqual(first, installed_again.read_text(encoding="utf-8"))
            configured = json.loads(first)
            self.assertEqual(configured["description"], "Keep this description")
            self.assertEqual(configured["custom"], {"preserved": True})
            self.assertEqual(configured["hooks"]["SessionStart"], [{"hooks": [peer]}])

            for event in HOOK_EVENTS:
                handlers = [
                    handler
                    for group in configured["hooks"][event]
                    for handler in group["hooks"]
                ]
                peri6 = [
                    handler
                    for handler in handlers
                    if "PERI6_AGENT_CONFIG" in handler.get("command", "")
                ]
                self.assertEqual(len(peri6), 1, event)
                self.assertIs(peri6[0]["async"], False)
                self.assertEqual(peri6[0]["timeout"], 3)
                escaped_repository = str(repository.resolve()).replace("'", "''")
                self.assertIn(escaped_repository, peri6[0]["commandWindows"])
            pre_tool_handlers = [
                handler
                for group in configured["hooks"]["PreToolUse"]
                for handler in group["hooks"]
            ]
            self.assertIn(peer, pre_tool_handlers)
            backup = codex_home / "hooks.json.peri6.bak"
            self.assertEqual(backup.read_text(encoding="utf-8"), original_text)

    def test_global_install_honors_codex_home_environment_variable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            configured_home = root / "alternate-codex-home"

            with patch.dict(os.environ, {"CODEX_HOME": str(configured_home)}):
                installed, changed = install_global_hooks(repository)

            self.assertTrue(changed)
            self.assertEqual(installed, configured_home.resolve() / "hooks.json")

    def test_invalid_existing_hooks_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            codex_home = root / ".codex"
            codex_home.mkdir()
            path = codex_home / "hooks.json"
            path.write_text("{not-json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                install_global_hooks(repository, codex_home=codex_home)
            self.assertEqual(path.read_text(encoding="utf-8"), "{not-json")

    def test_global_install_preserves_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            codex_home = root / ".codex"
            codex_home.mkdir()
            path = codex_home / "hooks.json"
            path.write_text('\ufeff{"hooks": {}}\n', encoding="utf-8")

            install_global_hooks(repository, codex_home=codex_home)

            self.assertTrue(path.read_text(encoding="utf-8").startswith("\ufeff{"))

    def test_vscode_override_preserves_existing_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "Code" / "User" / "settings.json"
            settings.parent.mkdir(parents=True)
            original = json.dumps({"editor.formatOnSave": True})
            settings.write_text(original, encoding="utf-8")
            executable = root / "bin" / "codex.exe"
            executable.parent.mkdir()
            executable.write_bytes(b"test")

            path, changed = install_vscode_cli_override(
                executable,
                settings_path=settings,
            )
            _, changed_again = install_vscode_cli_override(
                executable,
                settings_path=settings,
            )
            configured = json.loads(path.read_text(encoding="utf-8"))

            self.assertTrue(changed)
            self.assertFalse(changed_again)
            self.assertIs(configured["editor.formatOnSave"], True)
            self.assertEqual(configured[VSCODE_CLI_SETTING], str(executable.resolve()))
            self.assertEqual(
                settings.with_name("settings.json.peri6.bak").read_text(encoding="utf-8"),
                original,
            )

    def test_vscode_override_preserves_jsonc_comments_and_trailing_comma(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.json"
            settings.write_text(
                '{\n  // Keep this explanation.\n  "editor.fontSize": 15,\n}\n',
                encoding="utf-8",
            )
            executable = root / "Codex path" / "codex.exe"
            executable.parent.mkdir()
            executable.write_bytes(b"test")

            path, changed = install_vscode_cli_override(
                executable,
                settings_path=settings,
            )
            first = path.read_text(encoding="utf-8")
            _, changed_again = install_vscode_cli_override(
                executable,
                settings_path=settings,
            )

            self.assertTrue(changed)
            self.assertFalse(changed_again)
            self.assertIn("// Keep this explanation.", first)
            self.assertIn('"editor.fontSize": 15,', first)
            self.assertIn('"chatgpt.cliExecutable"', first)
            self.assertIn(str(executable.resolve()).replace("\\", "\\\\"), first)

    @staticmethod
    def _repository(root: Path) -> Path:
        repository = root / "Peri6 friend's copy"
        python = repository / ".venv" / "Scripts" / "python.exe"
        sender = repository / ".codex" / "hooks" / "peri6_agent_hook.py"
        python.parent.mkdir(parents=True)
        sender.parent.mkdir(parents=True)
        python.write_bytes(b"python")
        sender.write_text("# sender", encoding="utf-8")
        return repository


if __name__ == "__main__":
    unittest.main()