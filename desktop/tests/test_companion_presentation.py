from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from codex_beacon.companion.presentation import (
    CellLabelGroup,
    ConnectionPhase,
    FocusPhase,
    OFF_CELLS,
    OutputPhase,
    PresentationState,
    format_duration,
    reduce_event,
    sample_timeline_cells,
)
from codex_beacon.companion.runtime import CompanionEvent
from codex_beacon.contracts import (
    ActivePackOutput,
    Explanation,
    PackProposal,
    Playback,
    RGB,
    RecipeFrame,
    Timeline,
    Transition,
    VisualRecipe,
)
from codex_beacon.host import HostEvent
from codex_beacon.transport import DeviceEvent


BLUE = RGB(0, 90, 210)


def output(
    state_key: str,
    progress: float,
    *,
    pack_id: str = "com.codexbeacon.focus",
) -> ActivePackOutput:
    frame = RecipeFrame((BLUE,) * 6, 0, 1_000, Transition.STEP)
    timeline = Timeline((frame,), Playback.LOOP)
    proposal = PackProposal(
        state_key=state_key,
        source_observed_at=datetime.now(timezone.utc),
        valid_for_ms=2_000,
        confidence=1.0,
        explanation=Explanation("Test"),
        recipe=VisualRecipe(timeline, timeline, 0.5),
        progress=progress,
    )
    return ActivePackOutput(
        pack_id=pack_id,
        activation_id=uuid4(),
        generation=1,
        output_sequence=1,
        accepted_monotonic_ns=1,
        expires_monotonic_ns=2,
        proposal=proposal,
    )


class PresentationStateTests(unittest.TestCase):
    def test_formats_short_and_long_durations(self) -> None:
        self.assertEqual(format_duration(0), "0:00")
        self.assertEqual(format_duration(2_067), "34:27")
        self.assertEqual(format_duration(14_400), "4:00:00")

    def test_cell_label_groups_are_desktop_only_six_cell_metadata(self) -> None:
        groups = (
            CellLabelGroup(0, 2, "Temperature", "31 C"),
            CellLabelGroup(2, 2, "Humidity", "64%"),
            CellLabelGroup(4, 2, "Rain chance", "20%"),
        )
        self.assertEqual(groups[2].start + groups[2].span, 6)
        with self.assertRaises(ValueError):
            CellLabelGroup(5, 2, "Outside")

    def test_countdown_is_derived_from_progress_not_explanation_text(self) -> None:
        state = replace(
            PresentationState.initial(2),
            connection=ConnectionPhase.CONNECTED,
        )
        event = CompanionEvent(
            "host",
            "accepted",
            HostEvent("proposal_accepted", "accepted", 1, output("focus.working", 0.25)),
        )
        reduced = reduce_event(state, event)
        self.assertEqual(reduced.focus, FocusPhase.WORKING)
        self.assertEqual(reduced.remaining_seconds, 90)
        self.assertEqual(reduced.semantic_cells, (BLUE,) * 6)
        self.assertEqual(reduced.output, OutputPhase.PENDING)

    def test_exact_second_progress_does_not_display_an_extra_second(self) -> None:
        state = replace(
            PresentationState.initial(1),
            connection=ConnectionPhase.CONNECTED,
        )
        event = CompanionEvent(
            "host",
            "accepted",
            HostEvent(
                "proposal_accepted",
                "accepted",
                1,
                output("focus.working", 20 / 60),
            ),
        )
        self.assertEqual(reduce_event(state, event).remaining_seconds, 40)

    def test_expired_event_does_not_repaint_its_previous_output(self) -> None:
        state = replace(
            PresentationState.initial(1),
            connection=ConnectionPhase.CONNECTED,
            focus=FocusPhase.COMPLETED,
            semantic_cells=(BLUE,) * 6,
            output=OutputPhase.ACTIVE,
        )
        event = CompanionEvent(
            "host",
            "expired",
            HostEvent("proposal_expired", "expired", 1, output("focus.completed", 1.0)),
        )
        reduced = reduce_event(state, event)
        self.assertEqual(reduced.focus, FocusPhase.COMPLETED)
        self.assertEqual(reduced.output, OutputPhase.OFF)
        self.assertEqual(reduced.displayed_cells, OFF_CELLS)

    def test_session_and_connection_states_remain_independent(self) -> None:
        state = replace(
            PresentationState.initial(1),
            focus=FocusPhase.WORKING,
            remaining_seconds=42,
            output=OutputPhase.ACTIVE,
        )
        reduced = reduce_event(
            state,
            CompanionEvent(
                "device",
                "lost",
                DeviceEvent("disconnected", "Device connection lost."),
            ),
        )
        self.assertEqual(reduced.connection, ConnectionPhase.DISCONNECTED)
        self.assertEqual(reduced.focus, FocusPhase.WORKING)
        self.assertEqual(reduced.remaining_seconds, 42)
        self.assertEqual(reduced.output, OutputPhase.UNKNOWN)

    def test_scene_ack_marks_output_active(self) -> None:
        state = replace(
            PresentationState.initial(1),
            connection=ConnectionPhase.CONNECTED,
            output=OutputPhase.PENDING,
        )
        reduced = reduce_event(
            state,
            CompanionEvent(
                "device",
                "accepted",
                DeviceEvent("scene_loaded", "Fresh desired scene accepted."),
            ),
        )
        self.assertEqual(reduced.output, OutputPhase.ACTIVE)

    def test_once_hold_uses_the_physically_held_last_frame(self) -> None:
        first = RecipeFrame((RGB(0, 30, 10),) * 6, 0, 100, Transition.STEP)
        held = RecipeFrame((RGB(0, 176, 70),) * 6, 400, 1_000)
        timeline = Timeline((first, held), Playback.ONCE_HOLD)
        original = output("focus.completed", 1.0)
        proposal = replace(
            original.proposal,
            recipe=VisualRecipe(timeline, timeline, 0.7),
        )
        event = CompanionEvent(
            "host",
            "completed",
            HostEvent(
                "proposal_accepted",
                "completed",
                1,
                replace(original, proposal=proposal),
            ),
        )
        state = replace(
            PresentationState.initial(1),
            connection=ConnectionPhase.CONNECTED,
        )
        reduced = reduce_event(state, event)
        self.assertEqual(reduced.semantic_cells, held.cells)

    def test_agent_output_uses_a_state_headline_and_hides_focus_actions(self) -> None:
        headlines = {
            "idle": "Waiting for Codex",
            "thinking": "Thinking",
            "working": "Working",
            "editing": "Editing",
            "testing": "Running tests",
            "building": "Building",
            "waiting": "Needs approval",
            "input": "Needs input",
            "success": "Checks passed",
            "failure": "Check failed",
            "review": "Ready for review",
        }
        for state, headline in headlines.items():
            with self.subTest(state=state):
                event = CompanionEvent(
                    "host",
                    "agent",
                    HostEvent(
                        "proposal_accepted",
                        "agent",
                        2,
                        output(
                            f"agent.{state}",
                            0.0,
                            pack_id="com.codexbeacon.agent",
                        ),
                    ),
                )
                reduced = reduce_event(PresentationState.initial(25), event)
                self.assertEqual(reduced.active_pack_name, "Agent")
                self.assertEqual(reduced.main_text, headline)
                self.assertFalse(reduced.is_focus)
                self.assertEqual(reduced.primary_action_name, "")
                self.assertFalse(reduced.can_stop)

    def test_agent_preview_samples_the_same_timeline_as_the_device(self) -> None:
        red = RGB(120, 0, 0)
        green = RGB(0, 120, 0)
        red_cells = (red,) * 6
        green_cells = (green,) * 6
        timeline = Timeline(
            (
                RecipeFrame(red_cells, 100, 100),
                RecipeFrame(green_cells, 100, 100),
            ),
            Playback.LOOP,
        )
        start_ns = 1_000_000_000
        original = output("agent.working", 0.0, pack_id="com.codexbeacon.agent")
        agent_output = replace(
            original,
            accepted_monotonic_ns=start_ns,
            proposal=replace(
                original.proposal,
                recipe=VisualRecipe(timeline, timeline, 0.5),
            ),
        )
        state = replace(
            PresentationState.initial(25),
            connection=ConnectionPhase.CONNECTED,
        )
        reduced = reduce_event(
            state,
            CompanionEvent(
                "host",
                "agent",
                HostEvent("proposal_accepted", "agent", 2, agent_output),
            ),
        )

        self.assertEqual(
            reduced.displayed_cells_at(start_ns + 50_000_000),
            (RGB(60, 0, 0),) * 6,
        )
        self.assertEqual(
            reduced.displayed_cells_at(start_ns + 150_000_000),
            red_cells,
        )
        self.assertEqual(
            reduced.displayed_cells_at(start_ns + 250_000_000),
            (RGB(60, 60, 0),) * 6,
        )
        self.assertEqual(
            reduced.displayed_cells_at(start_ns + 450_000_000),
            (RGB(60, 60, 0),) * 6,
        )

    def test_agent_terminal_preview_holds_or_clears_like_device_playback(self) -> None:
        lit = (RGB(40, 80, 120),) * 6
        frame = RecipeFrame(lit, 0, 100, Transition.STEP)
        held = Timeline((frame,), Playback.ONCE_HOLD)
        cleared = Timeline((frame,), Playback.ONCE_CLEAR)

        self.assertEqual(sample_timeline_cells(held, 500), lit)
        self.assertEqual(sample_timeline_cells(cleared, 500), OFF_CELLS)


if __name__ == "__main__":
    unittest.main()