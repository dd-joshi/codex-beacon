"""Wall-clock persistence contracts for the Focus timer."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from codex_beacon.packs.focus.store import (
    clear_timer_state,
    load_timer_state,
    save_timer_state,
)


class TimerStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "timer.json"
        self.addCleanup(self._tmp.cleanup)

    def test_working_timer_persists_an_absolute_deadline(self) -> None:
        now = datetime.now(tz=timezone.utc)
        save_timer_state(
            25,
            phase="working",
            remaining_seconds=600,
            now_utc=now,
            path=self.path,
        )
        document = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(
            document["deadline_utc"],
            (now + timedelta(seconds=600)).isoformat(),
        )
        restored = load_timer_state(now_utc=now + timedelta(seconds=300), path=self.path)
        assert restored is not None
        self.assertEqual(restored["phase"], "working")
        self.assertAlmostEqual(restored["remaining_seconds"], 300, delta=1)

    def test_expired_deadline_reports_completed_and_clears(self) -> None:
        now = datetime.now(tz=timezone.utc)
        save_timer_state(10, phase="working", remaining_seconds=60, now_utc=now, path=self.path)
        restored = load_timer_state(now_utc=now + timedelta(seconds=120), path=self.path)
        assert restored is not None
        self.assertEqual(restored["phase"], "completed")
        self.assertFalse(self.path.exists())

    def test_paused_timer_keeps_remaining_seconds(self) -> None:
        now = datetime.now(tz=timezone.utc)
        save_timer_state(15, phase="paused", remaining_seconds=333, now_utc=now, path=self.path)
        later = now + timedelta(hours=2)
        restored = load_timer_state(now_utc=later, path=self.path)
        assert restored is not None
        self.assertEqual(restored["phase"], "paused")
        self.assertEqual(restored["remaining_seconds"], 333)

    def test_corrupt_state_is_removed_not_trusted(self) -> None:
        self.path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(load_timer_state(path=self.path))
        self.assertFalse(self.path.exists())

    def test_clear_removes_the_file(self) -> None:
        save_timer_state(5, phase="paused", remaining_seconds=10, path=self.path)
        clear_timer_state(path=self.path)
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
