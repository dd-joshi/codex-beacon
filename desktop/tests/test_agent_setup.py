from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_beacon.agent_setup import (
    HOOK_EVENTS,
    install_global_hooks,
    uninstall_codex_beacon_hooks,
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
            original = {
                "description": "Keep this description",
                "hooks": {
                    "PreToolUse": [{"matcher": "Bash", "hooks": [peer]}],
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
                ours = [
                    handler
                    for handler in handlers
                    if "CODEX_BEACON_CONFIG" in handler.get("command", "")
                ]
                self.assertEqual(len(ours), 1, event)
                self.assertIs(ours[0]["async"], False)
                self.assertEqual(ours[0]["timeout"], 3)
                escaped_repository = str(repository.resolve()).replace("'", "''")
                self.assertIn(escaped_repository, ours[0]["commandWindows"])
            pre_tool_handlers = [
                handler
                for group in configured["hooks"]["PreToolUse"]
                for handler in group["hooks"]
            ]
            self.assertIn(peer, pre_tool_handlers)
            backup = codex_home / "hooks.json.codex-beacon.bak"
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

    def test_uninstall_removes_only_codex_beacon_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._repository(root)
            codex_home = root / ".codex"
            codex_home.mkdir()
            peer = {"type": "command", "command": "python peer_hook.py"}
            path = codex_home / "hooks.json"
            path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [{"hooks": [peer]}],
                            "Stop": [{"hooks": [peer]}],
                        }
                    }
                ),
                encoding="utf-8",
            )

            install_global_hooks(repository, codex_home=codex_home)
            removed = uninstall_codex_beacon_hooks(codex_home=codex_home)

            self.assertEqual(removed, [path.resolve()])
            document = json.loads(path.read_text(encoding="utf-8"))
            for event in HOOK_EVENTS:
                handlers = [
                    handler
                    for group in document["hooks"].get(event, [])
                    for handler in group["hooks"]
                ]
                self.assertFalse(
                    any("CODEX_BEACON_CONFIG" in handler.get("command", "") for handler in handlers)
                )
            self.assertEqual(document["hooks"]["PreToolUse"], [{"hooks": [peer]}])
            self.assertEqual(document["hooks"]["Stop"], [{"hooks": [peer]}])

    @staticmethod
    def _repository(root: Path) -> Path:
        repository = root / "Codex Beacon friend's copy"
        python = repository / ".venv" / "Scripts" / "python.exe"
        sender = repository / ".codex" / "hooks" / "codex_beacon_hook.py"
        python.parent.mkdir(parents=True)
        sender.parent.mkdir(parents=True)
        python.write_bytes(b"python")
        sender.write_text("# sender", encoding="utf-8")
        return repository


if __name__ == "__main__":
    unittest.main()
