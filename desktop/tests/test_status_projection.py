from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from peri6.companion.presentation import FocusPhase, OutputPhase, PresentationState
from peri6.companion.status import (
    NotificationIntent,
    StatusPhase,
    StatusProjector,
    freshen_snapshot,
    load_phone_status_config,
    rotate_phone_status_token,
    save_phone_status_config,
)
from peri6.contracts import AttentionClass, RGB
from peri6.packs.registry import AGENT_PACK_ID, FOCUS_PACK_ID


BLUE = RGB(0, 90, 210)
NOW = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
NOW_NS = 1_000_000_000


def state_for(
    state_key: str,
    *,
    pack_id: str = AGENT_PACK_ID,
    pack_name: str = "Agent",
    headline: str = "Agent is working",
    attention: AttentionClass = AttentionClass.NORMAL,
    detail: str = "A local tool is running.",
    suggested_action: str | None = None,
    expires_ns: int = NOW_NS + 60_000_000_000,
    output: OutputPhase = OutputPhase.ACTIVE,
    focus: FocusPhase = FocusPhase.IDLE,
) -> PresentationState:
    return replace(
        PresentationState.initial(1),
        active_pack_id=pack_id,
        active_pack_name=pack_name,
        active_state_key=state_key,
        headline=headline,
        attention=attention,
        detail=detail,
        suggested_action=suggested_action,
        source_observed_at=NOW,
        output_expires_monotonic_ns=expires_ns,
        output_accepted_monotonic_ns=1,
        activation_generation=4,
        output_sequence=7,
        output=output,
        semantic_cells=(BLUE,) * 6,
        focus=focus,
    )


class StatusProjectionTests(unittest.TestCase):
    def test_agent_input_is_urgent_and_carries_its_action(self) -> None:
        projector = StatusProjector()
        snapshot = projector.project(
            state_for(
                "agent.input",
                headline="Needs input",
                attention=AttentionClass.URGENT,
                suggested_action="Reply on your PC.",
            ),
            now_monotonic_ns=NOW_NS,
            now_utc=NOW,
        )
        self.assertEqual(snapshot.phase, StatusPhase.LIVE)
        self.assertEqual(snapshot.notify, NotificationIntent.URGENT)
        self.assertEqual(snapshot.headline, "Needs input")
        self.assertEqual(snapshot.suggested_action, "Reply on your PC.")
        self.assertEqual(snapshot.attention, AttentionClass.URGENT)

    def test_notification_policy_for_each_agent_state(self) -> None:
        expected = {
            "agent.idle": NotificationIntent.NONE,
            "agent.thinking": NotificationIntent.NONE,
            "agent.working": NotificationIntent.NONE,
            "agent.editing": NotificationIntent.NONE,
            "agent.testing": NotificationIntent.NONE,
            "agent.building": NotificationIntent.NONE,
            "agent.waiting": NotificationIntent.URGENT,
            "agent.input": NotificationIntent.URGENT,
            "agent.success": NotificationIntent.CHIME,
            "agent.failure": NotificationIntent.URGENT,
            "agent.review": NotificationIntent.CHIME,
        }
        for state_key, intent in expected.items():
            with self.subTest(state_key=state_key):
                projector = StatusProjector()
                snapshot = projector.project(
                    state_for(state_key),
                    now_monotonic_ns=NOW_NS,
                    now_utc=NOW,
                )
                self.assertEqual(snapshot.notify, intent)

    def test_transition_id_is_stable_across_freshness_refreshes(self) -> None:
        projector = StatusProjector()
        working = state_for("agent.working")
        first = projector.project(working, now_monotonic_ns=NOW_NS, now_utc=NOW)
        refreshed = projector.project(
            replace(working, source_observed_at=NOW.replace(second=15)),
            now_monotonic_ns=NOW_NS + 1_000_000_000,
            now_utc=NOW,
        )
        self.assertEqual(first.transition_id, refreshed.transition_id)

        waiting = projector.project(
            replace(working, active_state_key="agent.waiting"),
            now_monotonic_ns=NOW_NS + 2_000_000_000,
            now_utc=NOW,
        )
        self.assertNotEqual(first.transition_id, waiting.transition_id)
        self.assertEqual(waiting.notify, NotificationIntent.URGENT)

    def test_expired_working_output_becomes_stale_and_silent(self) -> None:
        projector = StatusProjector()
        snapshot = projector.project(
            state_for("agent.working", expires_ns=NOW_NS + 1_000_000_000),
            now_monotonic_ns=NOW_NS + 2_000_000_000,
            now_utc=NOW,
        )
        self.assertEqual(snapshot.phase, StatusPhase.STALE)
        self.assertEqual(snapshot.notify, NotificationIntent.NONE)

    def test_expired_success_is_last_known_not_a_fake_live_state(self) -> None:
        projector = StatusProjector()
        snapshot = projector.project(
            state_for(
                "agent.success",
                headline="Checks passed",
                attention=AttentionClass.NORMAL,
                expires_ns=NOW_NS + 10_000_000_000,
            ),
            now_monotonic_ns=NOW_NS + 20_000_000_000,
            now_utc=NOW,
        )
        self.assertEqual(snapshot.phase, StatusPhase.LAST_KNOWN)
        self.assertEqual(snapshot.notify, NotificationIntent.NONE)

    def test_idle_remains_live_after_the_device_lease_expires(self) -> None:
        projector = StatusProjector()
        snapshot = projector.project(
            state_for("agent.idle", expires_ns=NOW_NS + 1_000_000_000),
            now_monotonic_ns=NOW_NS + 2_000_000_000,
            now_utc=NOW,
        )
        self.assertEqual(snapshot.phase, StatusPhase.LIVE)
        self.assertEqual(snapshot.notify, NotificationIntent.NONE)

    def test_freshening_an_old_working_snapshot_marks_it_stale(self) -> None:
        snapshot = StatusProjector().project(
            state_for("agent.working"),
            now_monotonic_ns=NOW_NS,
            now_utc=NOW,
        )
        freshened = freshen_snapshot(
            snapshot,
            now_utc=NOW + timedelta(seconds=120),
        )
        self.assertEqual(freshened.phase, StatusPhase.STALE)
        self.assertEqual(freshened.notify, NotificationIntent.NONE)
        self.assertGreaterEqual(freshened.age_seconds, 119)

    def test_freshening_an_old_success_marks_it_last_known(self) -> None:
        snapshot = StatusProjector().project(
            state_for(
                "agent.success",
                headline="Checks passed",
                attention=AttentionClass.NORMAL,
            ),
            now_monotonic_ns=NOW_NS,
            now_utc=NOW,
        )
        freshened = freshen_snapshot(
            snapshot,
            now_utc=NOW + timedelta(seconds=30),
        )
        self.assertEqual(freshened.phase, StatusPhase.LAST_KNOWN)
        self.assertEqual(freshened.notify, NotificationIntent.NONE)

    def test_freshening_keeps_idle_live(self) -> None:
        snapshot = StatusProjector().project(
            state_for("agent.idle"),
            now_monotonic_ns=NOW_NS,
            now_utc=NOW,
        )
        freshened = freshen_snapshot(
            snapshot,
            now_utc=NOW + timedelta(minutes=5),
        )
        self.assertEqual(freshened.phase, StatusPhase.LIVE)
        self.assertEqual(freshened.notify, NotificationIntent.NONE)

    def test_freshening_keeps_a_recent_live_snapshot_live(self) -> None:
        snapshot = StatusProjector().project(
            state_for("agent.waiting"),
            now_monotonic_ns=NOW_NS,
            now_utc=NOW,
        )
        freshened = freshen_snapshot(
            snapshot,
            now_utc=NOW + timedelta(seconds=5),
        )
        self.assertEqual(freshened.phase, StatusPhase.LIVE)
        self.assertEqual(freshened.notify, NotificationIntent.URGENT)

    def test_focus_completion_chimes_once_per_transition(self) -> None:
        projector = StatusProjector()
        state = state_for(
            "focus.completed",
            pack_id=FOCUS_PACK_ID,
            pack_name="Focus",
            headline="",
            focus=FocusPhase.COMPLETED,
        )
        first = projector.project(state, now_monotonic_ns=NOW_NS, now_utc=NOW)
        self.assertEqual(first.phase, StatusPhase.LIVE)
        self.assertEqual(first.notify, NotificationIntent.CHIME)
        self.assertEqual(first.headline, "Focus complete")
        refreshed = projector.project(
            replace(state, source_observed_at=NOW.replace(second=30)),
            now_monotonic_ns=NOW_NS + 1_000_000_000,
            now_utc=NOW,
        )
        self.assertEqual(first.transition_id, refreshed.transition_id)

    def test_host_notice_is_an_error_and_does_not_alert(self) -> None:
        projector = StatusProjector()
        snapshot = projector.project(
            replace(state_for("agent.working"), notice="Host error"),
            now_monotonic_ns=NOW_NS,
            now_utc=NOW,
        )
        self.assertEqual(snapshot.phase, StatusPhase.ERROR)
        self.assertEqual(snapshot.notify, NotificationIntent.NONE)
        self.assertEqual(snapshot.headline, "Companion error")
        self.assertEqual(snapshot.suggested_action, "Check Peri6 on the PC.")

    def test_no_output_is_offline(self) -> None:
        projector = StatusProjector()
        snapshot = projector.project(
            PresentationState.initial(1),
            now_monotonic_ns=NOW_NS,
            now_utc=NOW,
        )
        self.assertEqual(snapshot.phase, StatusPhase.OFFLINE)
        self.assertEqual(snapshot.notify, NotificationIntent.NONE)

    def test_payload_contains_only_phone_safe_fields(self) -> None:
        projector = StatusProjector()
        payload = projector.project(
            state_for("agent.waiting", headline="Needs approval"),
            now_monotonic_ns=NOW_NS,
            now_utc=NOW,
        ).to_json()
        self.assertEqual(
            set(payload),
            {
                "version",
                "pack_id",
                "pack_name",
                "state_key",
                "headline",
                "detail",
                "suggested_action",
                "attention",
                "phase",
                "notify",
                "transition_id",
                "updated_at",
                "age_seconds",
                "progress",
                "focus_remaining_seconds",
                "is_focus",
                "cells",
            },
        )
        rendered = json.dumps(payload)
        for forbidden in (
            "token",
            "prompt",
            "command",
            "transcript",
            "tool_output",
            "device_secret",
        ):
            self.assertNotIn(forbidden, rendered.lower())


class PhoneConfigTests(unittest.TestCase):
    def test_config_is_created_loaded_and_rotated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phone-status.json"
            created = load_phone_status_config(path)
            self.assertTrue(path.exists())
            self.assertTrue(created.enabled)
            self.assertGreaterEqual(len(created.token), 32)

            loaded = load_phone_status_config(path)
            self.assertEqual(loaded.port, created.port)
            self.assertEqual(loaded.token, created.token)

            rotated = rotate_phone_status_token(loaded)
            self.assertNotEqual(rotated.token, loaded.token)
            reloaded = load_phone_status_config(path)
            self.assertEqual(reloaded.token, rotated.token)

    def test_config_writes_are_atomic_and_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phone-status.json"
            config = load_phone_status_config(path)
            save_phone_status_config(config)
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                set(value),
                {"version", "enabled", "port", "token"},
            )

    def test_corrupt_config_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phone-status.json"
            path.write_text('{"enabled": true}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_phone_status_config(path)


if __name__ == "__main__":
    unittest.main()
