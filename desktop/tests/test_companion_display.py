from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timezone

from codex_beacon.companion.display import (
    DisplayMotion,
    DisplaySpec,
    DisplayTone,
    display_cells_at,
    display_semantic_cells,
    display_spec,
    recolor_cell,
)
from codex_beacon.companion.presentation import (
    OFF_CELLS,
    FocusPhase,
    OutputPhase,
    PresentationState,
)
from codex_beacon.contracts import Playback, RGB, RecipeFrame, Timeline, Transition
from codex_beacon.packs.registry import AGENT_PACK_ID, FOCUS_PACK_ID


NOW = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
NOW_NS = 2_000_000_000
LATER_NS = NOW_NS + 60_000_000_000
PACK_BLUE = RGB(0, 90, 210)
PACK_LAVENDER = RGB(174, 139, 242)
PACK_AMBER = RGB(188, 96, 0)
PACK_RED = RGB(156, 12, 8)


def state_for(
    state_key: str,
    *,
    pack_id: str = AGENT_PACK_ID,
    pack_name: str = "Agent",
    focus: FocusPhase = FocusPhase.IDLE,
    semantic_cells: tuple[RGB, ...] = (PACK_BLUE,) * 6,
    output: OutputPhase = OutputPhase.OFF,
    accepted_ns: int = NOW_NS,
    expires_ns: int | None = LATER_NS,
    timeline: Timeline | None = None,
    visual_started_ns: int = 0,
    visual_initial_cells: tuple[RGB, ...] = OFF_CELLS,
) -> PresentationState:
    return replace(
        PresentationState.initial(25),
        active_pack_id=pack_id,
        active_pack_name=pack_name,
        active_state_key=state_key,
        headline=state_key,
        focus=focus,
        source_observed_at=NOW,
        semantic_cells=semantic_cells,
        visual_timeline=timeline,
        visual_started_monotonic_ns=visual_started_ns,
        visual_initial_cells=visual_initial_cells,
        output=output,
        output_accepted_monotonic_ns=accepted_ns,
        output_expires_monotonic_ns=expires_ns,
        output_sequence=7,
        activation_generation=3,
    )


class DisplayLanguageTests(unittest.TestCase):
    def test_review_is_green_with_a_settle_motion(self) -> None:
        state = state_for("agent.review", semantic_cells=(PACK_LAVENDER,) * 6)
        spec = display_spec(state)
        self.assertEqual(spec.tone, DisplayTone.GREEN)
        self.assertEqual(spec.motion, DisplayMotion.SETTLE)
        cells = display_semantic_cells(state)
        self.assertEqual(cells, (RGB(34, 197, 94),) * 6)

    def test_focus_paused_is_amber_with_slow_breathing(self) -> None:
        state = state_for(
            "focus.paused",
            pack_id=FOCUS_PACK_ID,
            pack_name="Focus",
            focus=FocusPhase.PAUSED,
            semantic_cells=(PACK_AMBER,) * 6,
        )
        spec = display_spec(state)
        self.assertEqual(spec.tone, DisplayTone.AMBER)
        self.assertEqual(spec.motion, DisplayMotion.BREATHE)
        cells = display_semantic_cells(state)
        self.assertTrue(all(cell.r > cell.g > cell.b for cell in cells))
        self.assertGreater(cells[0].r, 200)

    def test_focus_cancelled_is_grey_not_red(self) -> None:
        state = state_for(
            "focus.cancelled",
            pack_id=FOCUS_PACK_ID,
            pack_name="Focus",
            focus=FocusPhase.CANCELLED,
            semantic_cells=(PACK_RED,) * 6,
        )
        spec = display_spec(state)
        self.assertEqual(spec.tone, DisplayTone.GREY)
        self.assertEqual(spec.motion, DisplayMotion.PULSE)
        cells = display_semantic_cells(state)
        for cell in cells:
            spread = max(cell.r, cell.g, cell.b) - min(cell.r, cell.g, cell.b)
            self.assertLessEqual(spread, 24)
            self.assertGreater(cell.r, 0)
            self.assertLess(cell.r, 120)

    def test_agent_states_share_the_product_palette(self) -> None:
        cases = {
            "agent.idle": (DisplayTone.GREY, DisplayMotion.OFF),
            "agent.thinking": (DisplayTone.BLUE, DisplayMotion.BREATHE),
            "agent.working": (DisplayTone.BLUE, DisplayMotion.RUNNER),
            "agent.editing": (DisplayTone.BLUE, DisplayMotion.RUNNER),
            "agent.testing": (DisplayTone.BLUE, DisplayMotion.RUNNER),
            "agent.building": (DisplayTone.BLUE, DisplayMotion.RUNNER),
            "agent.waiting": (DisplayTone.YELLOW, DisplayMotion.PULSE),
            "agent.input": (DisplayTone.YELLOW, DisplayMotion.PULSE),
            "agent.success": (DisplayTone.GREEN, DisplayMotion.SETTLE),
            "agent.review": (DisplayTone.GREEN, DisplayMotion.SETTLE),
            "agent.failure": (DisplayTone.RED, DisplayMotion.FLASH),
        }
        for state_key, expected in cases.items():
            with self.subTest(state_key=state_key):
                spec = display_spec(state_for(state_key))
                self.assertEqual((spec.tone, spec.motion), expected)

    def test_focus_states_share_the_product_palette(self) -> None:
        cases = {
            FocusPhase.IDLE: (DisplayTone.BLUE, DisplayMotion.BREATHE),
            FocusPhase.WORKING: (DisplayTone.BLUE, DisplayMotion.PROGRESS),
            FocusPhase.PAUSED: (DisplayTone.AMBER, DisplayMotion.BREATHE),
            FocusPhase.COMPLETED: (DisplayTone.GREEN, DisplayMotion.SETTLE),
            FocusPhase.CANCELLED: (DisplayTone.GREY, DisplayMotion.PULSE),
            FocusPhase.UNKNOWN: (DisplayTone.GREY, DisplayMotion.PULSE),
        }
        for phase, expected in cases.items():
            with self.subTest(phase=phase):
                spec = display_spec(
                    state_for(
                        f"focus.{phase.value}",
                        pack_id=FOCUS_PACK_ID,
                        pack_name="Focus",
                        focus=phase,
                    )
                )
                self.assertEqual((spec.tone, spec.motion), expected)

    def test_notice_is_red_and_no_proposal_is_off(self) -> None:
        notice = replace(state_for("agent.working"), notice="Host error")
        self.assertEqual(
            display_spec(notice),
            DisplaySpec(DisplayTone.RED, DisplayMotion.PULSE),
        )
        offline = replace(
            state_for("agent.working"),
            output_accepted_monotonic_ns=0,
            output_sequence=None,
        )
        self.assertEqual(
            display_spec(offline),
            DisplaySpec(DisplayTone.GREY, DisplayMotion.OFF),
        )
        self.assertEqual(display_semantic_cells(offline), OFF_CELLS)


class DisplayCellTests(unittest.TestCase):
    def test_recoloring_preserves_brightness_ordering_and_off_cells(self) -> None:
        bright = recolor_cell(RGB(200, 200, 200), DisplayTone.BLUE)
        dim = recolor_cell(RGB(50, 50, 50), DisplayTone.BLUE)
        self.assertEqual(
            recolor_cell(RGB(0, 0, 0), DisplayTone.BLUE),
            RGB(0, 0, 0),
        )
        self.assertGreater(
            max(bright.r, bright.g, bright.b),
            max(dim.r, dim.g, dim.b),
        )
        self.assertGreater(bright.b, bright.g)
        self.assertGreater(bright.g, bright.r)

    def test_phone_uses_the_brightest_loop_frame(self) -> None:
        timeline = Timeline(
            (
                RecipeFrame((PACK_BLUE,) * 6, 0, 500),
                RecipeFrame((PACK_LAVENDER,) * 6, 0, 500),
            ),
            Playback.LOOP,
        )
        state = state_for(
            "agent.waiting",
            semantic_cells=(PACK_BLUE,) * 6,
            timeline=timeline,
        )
        self.assertEqual(
            display_semantic_cells(state),
            (RGB(250, 204, 21),) * 6,
        )

    def test_fresh_proposal_renders_without_a_physical_display(self) -> None:
        timeline = Timeline(
            (RecipeFrame((PACK_BLUE,) * 6, 0, 1_000, Transition.STEP),),
            Playback.LOOP,
        )
        state = state_for(
            "agent.working",
            output=OutputPhase.OFF,
            timeline=timeline,
            visual_started_ns=NOW_NS,
        )
        self.assertEqual(
            display_cells_at(state, NOW_NS),
            (RGB(59, 130, 246),) * 6,
        )

    def test_expired_active_output_is_dimmed_but_not_treated_as_off(self) -> None:
        live = state_for(
            "agent.working",
            semantic_cells=(RGB(0, 174, 210),) * 6,
            expires_ns=LATER_NS,
        )
        stale = replace(live, output_expires_monotonic_ns=NOW_NS - 1)
        live_cells = display_cells_at(live, NOW_NS)
        stale_cells = display_cells_at(stale, NOW_NS)
        self.assertNotEqual(stale_cells, OFF_CELLS)
        self.assertLess(
            sum(cell.r + cell.g + cell.b for cell in stale_cells),
            sum(cell.r + cell.g + cell.b for cell in live_cells),
        )
        for cell in stale_cells:
            spread = max(cell.r, cell.g, cell.b) - min(cell.r, cell.g, cell.b)
            self.assertLessEqual(spread, 24)

    def test_expired_active_output_freezes_instead_of_animating(self) -> None:
        timeline = Timeline(
            (
                RecipeFrame((PACK_BLUE,) * 6, 0, 500, Transition.STEP),
                RecipeFrame((RGB(0, 174, 210),) * 6, 0, 500, Transition.STEP),
            ),
            Playback.LOOP,
        )
        state = state_for(
            "agent.working",
            semantic_cells=(PACK_BLUE,) * 6,
            timeline=timeline,
            expires_ns=NOW_NS - 1,
        )
        first = display_cells_at(state, NOW_NS)
        second = display_cells_at(state, NOW_NS + 600_000_000)
        self.assertEqual(first, second)

    def test_expired_terminal_output_keeps_a_dim_last_known_tone(self) -> None:
        state = state_for(
            "agent.review",
            semantic_cells=(PACK_LAVENDER,) * 6,
            expires_ns=NOW_NS - 1,
        )
        cells = display_cells_at(state, NOW_NS)
        self.assertTrue(
            all(cell.g > cell.r and cell.g > cell.b for cell in cells)
        )
        self.assertNotEqual(cells, (RGB(34, 197, 94),) * 6)


if __name__ == "__main__":
    unittest.main()
