"""One LED tone and motion language for the desktop and phone surfaces.

Packs still own their timelines and semantic state.  This module recolors those
timelines into the product palette and exposes the motion category used by the
phone page.  It deliberately does not alter proposals, notification intents, or
the status payload shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import cast

from codex_beacon.companion.presentation import (
    OFF_CELLS,
    FocusPhase,
    PresentationState,
    sample_timeline_cells,
)
from codex_beacon.contracts import Cells6, Playback, RGB
from codex_beacon.packs.registry import AGENT_PACK_ID, FOCUS_PACK_ID


class DisplayTone(str, Enum):
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    AMBER = "amber"
    RED = "red"
    GREY = "grey"


class DisplayMotion(str, Enum):
    OFF = "off"
    BREATHE = "breathe"
    RUNNER = "runner"
    PULSE = "pulse"
    PROGRESS = "progress"
    SETTLE = "settle"
    FLASH = "flash"


@dataclass(frozen=True, slots=True)
class DisplaySpec:
    tone: DisplayTone
    motion: DisplayMotion


# Keep these values in step with the phone page's CSS variables.  The reference
# peak lets bright pack cells reach the full tone while low cells stay visibly
# dimmer instead of every lit cell becoming the same intensity.
TONE_COLORS: dict[DisplayTone, RGB] = {
    DisplayTone.BLUE: RGB(59, 130, 246),
    DisplayTone.GREEN: RGB(34, 197, 94),
    DisplayTone.YELLOW: RGB(250, 204, 21),
    DisplayTone.AMBER: RGB(245, 158, 11),
    DisplayTone.RED: RGB(239, 68, 68),
    DisplayTone.GREY: RGB(75, 85, 99),
}
REFERENCE_PEAK = 200.0

_NO_PROPOSAL = DisplaySpec(DisplayTone.GREY, DisplayMotion.OFF)
_ERROR = DisplaySpec(DisplayTone.RED, DisplayMotion.PULSE)
_UNKNOWN = DisplaySpec(DisplayTone.GREY, DisplayMotion.PULSE)
_OTHER_PACK = DisplaySpec(DisplayTone.BLUE, DisplayMotion.BREATHE)

_AGENT_SPECS: dict[str, DisplaySpec] = {
    "agent.idle": DisplaySpec(DisplayTone.GREY, DisplayMotion.OFF),
    "agent.thinking": DisplaySpec(DisplayTone.BLUE, DisplayMotion.BREATHE),
    "agent.working": DisplaySpec(DisplayTone.BLUE, DisplayMotion.RUNNER),
    "agent.editing": DisplaySpec(DisplayTone.BLUE, DisplayMotion.RUNNER),
    "agent.testing": DisplaySpec(DisplayTone.BLUE, DisplayMotion.RUNNER),
    "agent.building": DisplaySpec(DisplayTone.BLUE, DisplayMotion.RUNNER),
    "agent.waiting": DisplaySpec(DisplayTone.YELLOW, DisplayMotion.PULSE),
    "agent.input": DisplaySpec(DisplayTone.YELLOW, DisplayMotion.PULSE),
    "agent.success": DisplaySpec(DisplayTone.GREEN, DisplayMotion.SETTLE),
    "agent.review": DisplaySpec(DisplayTone.GREEN, DisplayMotion.SETTLE),
    "agent.failure": DisplaySpec(DisplayTone.RED, DisplayMotion.FLASH),
}

_FOCUS_SPECS: dict[FocusPhase, DisplaySpec] = {
    FocusPhase.IDLE: DisplaySpec(DisplayTone.BLUE, DisplayMotion.BREATHE),
    FocusPhase.WORKING: DisplaySpec(DisplayTone.BLUE, DisplayMotion.PROGRESS),
    FocusPhase.PAUSED: DisplaySpec(DisplayTone.AMBER, DisplayMotion.BREATHE),
    FocusPhase.COMPLETED: DisplaySpec(DisplayTone.GREEN, DisplayMotion.SETTLE),
    FocusPhase.CANCELLED: DisplaySpec(DisplayTone.GREY, DisplayMotion.PULSE),
    FocusPhase.UNKNOWN: _UNKNOWN,
}

_TERMINAL_AGENT_KEYS = frozenset(
    {"agent.success", "agent.failure", "agent.review"}
)
_TERMINAL_FOCUS_PHASES = frozenset(
    {FocusPhase.COMPLETED, FocusPhase.CANCELLED}
)


def display_spec(state: PresentationState) -> DisplaySpec:
    """Return the unified tone and motion for the current semantic state."""

    if state.notice:
        return _ERROR
    if not _has_proposal(state):
        return _NO_PROPOSAL
    if state.active_pack_id == FOCUS_PACK_ID:
        return _FOCUS_SPECS.get(state.focus, _UNKNOWN)
    if state.active_pack_id == AGENT_PACK_ID:
        return _AGENT_SPECS.get(state.active_state_key, _UNKNOWN)
    return _OTHER_PACK


def display_cells_at(
    state: PresentationState,
    monotonic_ns: int,
) -> Cells6:
    """Sample and recolor the pack timeline for the desktop LED strip.

    A fresh host proposal is displayable even when no physical device accepted
    the scene.  That keeps the desktop useful in software-only mode.
    """

    if not _has_proposal(state):
        return cast(Cells6, OFF_CELLS)
    spec = display_spec(state)
    timeline = state.visual_timeline
    stale_active = _is_stale_active(state, monotonic_ns)
    if stale_active:
        # Freeze rather than animating an expired active state.  A moving grey
        # strip would still imply that Codex is doing something.
        sampled = cast(Cells6, state.semantic_cells)
    elif timeline is None:
        sampled = cast(Cells6, state.semantic_cells)
    else:
        elapsed_ms = max(
            0,
            (monotonic_ns - state.visual_started_monotonic_ns) // 1_000_000,
        )
        sampled = sample_timeline_cells(
            timeline,
            elapsed_ms,
            cast(Cells6, state.visual_initial_cells),
        )
    tone = DisplayTone.GREY if stale_active else spec.tone
    cells = recolor_cells(sampled, tone)
    return _scale_cells(cells, _freshness_scale(state, monotonic_ns))


def display_semantic_cells(state: PresentationState) -> Cells6:
    """Return the unified static cells carried by the phone status payload."""

    if not _has_proposal(state):
        return cast(Cells6, OFF_CELLS)
    return recolor_cells(_representative_cells(state), display_spec(state).tone)


def recolor_cells(cells: tuple[RGB, ...], tone: DisplayTone) -> Cells6:
    """Map pack colors to one tone while preserving each cell's brightness."""

    return cast(Cells6, tuple(recolor_cell(cell, tone) for cell in cells))


def recolor_cell(cell: RGB, tone: DisplayTone) -> RGB:
    peak = max(cell.r, cell.g, cell.b)
    if peak <= 0:
        return RGB(0, 0, 0)
    intensity = min(1.0, peak / REFERENCE_PEAK)
    base = TONE_COLORS[tone]
    return RGB(
        _tone_channel(base.r, intensity),
        _tone_channel(base.g, intensity),
        _tone_channel(base.b, intensity),
    )


def _tone_channel(value: int, intensity: float) -> int:
    return max(0, min(255, int(round(value * intensity))))


def _scale_cells(cells: tuple[RGB, ...], scale: float) -> Cells6:
    if scale >= 1.0:
        return cast(Cells6, cells)
    return cast(
        Cells6,
        tuple(
            RGB(
                _tone_channel(cell.r, scale),
                _tone_channel(cell.g, scale),
                _tone_channel(cell.b, scale),
            )
            for cell in cells
        ),
    )


def _representative_cells(state: PresentationState) -> Cells6:
    timeline = state.visual_timeline
    if (
        timeline is not None
        and timeline.playback is Playback.LOOP
        and timeline.frames
    ):
        # A looping phone frame should show the brightest part of the cycle,
        # not whichever low frame happened to be first.  One-shot cues keep
        # their held last frame so success/failure/cancelled remain honest.
        return max(
            timeline.frames,
            key=lambda frame: sum(
                cell.r + cell.g + cell.b for cell in frame.cells
            ),
        ).cells
    return cast(Cells6, state.semantic_cells)


def _has_proposal(state: PresentationState) -> bool:
    return (
        state.output_accepted_monotonic_ns > 0
        or state.output_sequence is not None
    )


def _is_terminal(state: PresentationState) -> bool:
    if state.active_pack_id == AGENT_PACK_ID:
        return state.active_state_key in _TERMINAL_AGENT_KEYS
    if state.active_pack_id == FOCUS_PACK_ID:
        return state.focus in _TERMINAL_FOCUS_PHASES
    return False


def _is_stale_active(state: PresentationState, monotonic_ns: int) -> bool:
    if state.notice or _is_terminal(state):
        return False
    if (
        state.active_pack_id == AGENT_PACK_ID
        and state.active_state_key == "agent.idle"
    ):
        return False
    expires = state.output_expires_monotonic_ns
    return expires is not None and monotonic_ns >= expires


def _freshness_scale(state: PresentationState, monotonic_ns: int) -> float:
    """Dim expired output without pretending an active state is still live."""

    if state.notice:
        return 1.0
    if (
        state.active_pack_id == AGENT_PACK_ID
        and state.active_state_key == "agent.idle"
    ):
        return 1.0
    expires = state.output_expires_monotonic_ns
    if expires is None or monotonic_ns < expires:
        return 1.0
    return 0.72 if _is_terminal(state) else 0.32


__all__ = [
    "DisplayMotion",
    "DisplaySpec",
    "DisplayTone",
    "REFERENCE_PEAK",
    "TONE_COLORS",
    "display_cells_at",
    "display_semantic_cells",
    "display_spec",
    "recolor_cell",
    "recolor_cells",
]
