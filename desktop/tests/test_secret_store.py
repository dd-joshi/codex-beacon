"""Protected secret storage and legacy migration contracts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from codex_beacon.packs.agent.secrets import (
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


if __name__ == "__main__":
    unittest.main()
