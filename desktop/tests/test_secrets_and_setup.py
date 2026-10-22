"""Secret storage migration and Claude hook installation contracts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from peri6.agent_setup import (
    build_claude_handler,
    install_claude_hooks,
    uninstall_peri6_hooks,
)
from peri6.packs.agent.secrets import (
    load_agent_secret,
    migrate_legacy_config,
    restrict_to_user,
    save_agent_secret,
)


class SecretStoreTests(unittest.TestCase):
    def test_save_load_round_trip_and_user_acl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "agent-secret.json"
            saved = save_agent_secret("http://127.0.0.1:9/v1/events", "t" * 43, path)
            self.assertTrue(restrict_to_user(saved))
            secret = load_agent_secret(saved)
            assert secret is not None
            self.assertEqual(secret.bearer_token, "t" * 43)
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("t" * 43, raw)

    def test_migration_scrubs_legacy_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "agent-hook.json"
            legacy.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "endpoint": "http://127.0.0.1:8/v1/events",
                        "bearer_token": "m" * 43,
                    }
                ),
                encoding="utf-8",
            )
            result = migrate_legacy_config(legacy, root / "store.json")
            assert result is not None
            store, created = result
            self.assertTrue(created)
            secret = load_agent_secret(store)
            assert secret is not None
            self.assertEqual(secret.bearer_token, "m" * 43)
            migrated = json.loads(legacy.read_text(encoding="utf-8"))
            self.assertEqual(migrated["bearer_token"], "")
            self.assertTrue(migrated["migrated_to_user_store"])
            self.assertIsNone(migrate_legacy_config(legacy, root / "store.json"))

    def test_short_token_is_not_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory) / "agent-hook.json"
            legacy.write_text(
                json.dumps(
                    {"version": 1, "endpoint": "http://x", "bearer_token": "short"}
                ),
                encoding="utf-8",
            )
            self.assertIsNone(migrate_legacy_config(legacy, Path(directory) / "s.json"))

    def test_unreadable_store_raises_instead_of_returning_none(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(Exception):
                load_agent_secret(path)


class ClaudeHookSetupTests(unittest.TestCase):
    def test_claude_hooks_install_and_uninstall_surgically(self) -> None:
        repository = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "claude"
            home.mkdir()
            settings = home / "settings.json"
            settings.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "UserPromptSubmit": [
                                {
                                    "matcher": "",
                                    "hooks": [
                                        {"type": "command", "command": "peer-tool"}
                                    ],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            _, changed = install_claude_hooks(repository, claude_home=home)
            self.assertTrue(changed)
            document = json.loads(settings.read_text(encoding="utf-8"))
            peer = document["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
            self.assertEqual(peer, "peer-tool")
            peri6_entries = document["hooks"]["UserPromptSubmit"][1]["hooks"]
            self.assertEqual(len(peri6_entries), 1)
            handler = build_claude_handler(repository)
            self.assertIn("peri6_agent_hook.py", handler["command"])
            self.assertIn("PERI6_AGENT_CONFIG", handler["command"])

            removed = uninstall_peri6_hooks(
                codex_home=Path(directory) / "codex", claude_home=home
            )
            self.assertEqual(len(removed), 1)
            self.assertTrue(removed[0].samefile(settings))
            document = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(len(document["hooks"]["UserPromptSubmit"]), 1)
            self.assertEqual(
                document["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"],
                "peer-tool",
            )

    def test_install_is_idempotent(self) -> None:
        repository = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "claude"
            _, first = install_claude_hooks(repository, claude_home=home)
            _, second = install_claude_hooks(repository, claude_home=home)
            self.assertTrue(first)
            self.assertFalse(second)


if __name__ == "__main__":
    unittest.main()
