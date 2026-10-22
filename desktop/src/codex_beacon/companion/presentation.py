"""Pure presentation state for the Codex Beacon companion.

The product UI consumes this module instead of interpreting host messages or
device prose directly.  Keeping the reducer free of GUI dependencies makes the
session, connection, and physical-output states independently testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import cast

from codex_beacon.companion.runtime import CompanionEvent
from codex_beacon.contracts import (
    ActivePackOutput,
    AttentionClass,
    Cells6,
    Playback,
    RGB,
    Timeline,
)
from codex_beacon.host import HostEvent
from codex_beacon.packs.registry import AGENT_PACK_ID, FOCUS_PACK_ID
from codex_beacon.transport import DeviceEvent


CELL_COUNT = 6
OFF_CELLS = (RGB(0, 0, 0),) * CELL_COUNT


class ConnectionPhase(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ATTENTION = "attention"


class FocusPhase(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class OutputPhase(str, Enum):
    OFF = "off"
    PENDING = "pending"
    ACTIVE = "active"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CellLabelGroup:
    """Desktop-only meaning for a contiguous group of physical cells.

    These labels belong to pack presentation and must never enter DeviceScene
    or the application-agnostic ESP protocol.
    """

    start: int
    span: int
    label: str
    value: str | None = None

    def __post_init__(self) -> None:
        if self.start < 0 or self.span < 1 or self.start + self.span > CELL_COUNT:
            raise ValueError("cell label group is outside the six-cell display")
        if not self.label.strip():
            raise ValueError("cell label group requires a label")


@dataclass(frozen=True, slots=True)
class PresentationState:
    duration_seconds: int
    active_pack_id: str = FOCUS_PACK_ID
    active_pack_name: str = "Focus"
    active_state_key: str = "focus.idle"
    headline: str = ""
    connection: ConnectionPhase = ConnectionPhase.DISCONNECTED
    connection_label: str = "Not connected"
    device_id: str | None = None
    focus: FocusPhase = FocusPhase.IDLE
    remaining_seconds: int = 0
    progress: float = 0.0
    semantic_cells: tuple[RGB, ...] = OFF_CELLS
    visual_timeline: Timeline | None = None
    visual_started_monotonic_ns: int = 0
    visual_initial_cells: tuple[RGB, ...] = OFF_CELLS
    reduced_motion: bool = False
    cell_label_groups: tuple[CellLabelGroup, ...] = ()
    output: OutputPhase = OutputPhase.OFF
    notice: str | None = None
    attention: AttentionClass = AttentionClass.NORMAL
    detail: str = ""
    suggested_action: str | None = None
    source_observed_at: datetime | None = None
    output_expires_monotonic_ns: int | None = None
    output_accepted_monotonic_ns: int = 0
    activation_generation: int = 0
    output_sequence: int | None = None

    @classmethod
    def initial(
        cls,
        duration_minutes: int,
        *,
        reduced_motion: bool = False,
    ) -> "PresentationState":
        duration_seconds = duration_minutes * 60
        return cls(
            duration_seconds=duration_seconds,
            remaining_seconds=duration_seconds,
            reduced_motion=reduced_motion,
        )

    @property
    def timer_text(self) -> str:
        return format_duration(self.remaining_seconds)

    @property
    def main_text(self) -> str:
        return self.timer_text if self.is_focus else self.headline

    @property
    def is_focus(self) -> bool:
        return self.active_pack_id == FOCUS_PACK_ID

    @property
    def displayed_cells(self) -> tuple[RGB, ...]:
        """Return the static semantic frame retained for compatibility."""

        if self.output in {OutputPhase.PENDING, OutputPhase.ACTIVE}:
            return self.semantic_cells
        return OFF_CELLS

    def displayed_cells_at(self, monotonic_ns: int) -> tuple[RGB, ...]:
        """Sample the same keyframe timeline sent to the physical renderer."""

        if self.output not in {OutputPhase.PENDING, OutputPhase.ACTIVE}:
            return OFF_CELLS
        timeline = self.visual_timeline
        if timeline is None:
            return self.semantic_cells
        elapsed_ms = max(
            0,
            (monotonic_ns - self.visual_started_monotonic_ns) // 1_000_000,
        )
        return sample_timeline_cells(
            timeline,
            elapsed_ms,
            cast(Cells6, self.visual_initial_cells),
        )

    @property
    def primary_action_name(self) -> str:
        if not self.is_focus:
            return ""
        if self.focus is FocusPhase.WORKING:
            return "Pause Focus"
        if self.focus is FocusPhase.PAUSED:
            return "Resume Focus"
        if self.focus in {FocusPhase.COMPLETED, FocusPhase.CANCELLED}:
            return "Start Focus again"
        return "Start Focus"

    @property
    def can_stop(self) -> bool:
        return self.is_focus and self.focus in {FocusPhase.WORKING, FocusPhase.PAUSED}


def reduce_event(state: PresentationState, event: CompanionEvent) -> PresentationState:
    """Reduce one runtime event without mutating the previous state."""

    if event.kind == "host" and isinstance(event.payload, HostEvent):
        return _reduce_host(state, event.payload)
    if event.kind == "device" and isinstance(event.payload, DeviceEvent):
        return _reduce_device(state, event.payload)
    if event.kind == "error":
        return replace(state, notice=event.message)
    return state


def with_duration(state: PresentationState, duration_minutes: int) -> PresentationState:
    duration_seconds = duration_minutes * 60
    if not state.is_focus:
        return replace(state, duration_seconds=duration_seconds, notice=None)
    return replace(
        state,
        duration_seconds=duration_seconds,
        remaining_seconds=duration_seconds,
        focus=FocusPhase.IDLE,
        progress=0.0,
        semantic_cells=OFF_CELLS,
        visual_timeline=None,
        visual_started_monotonic_ns=0,
        visual_initial_cells=OFF_CELLS,
        output=OutputPhase.PENDING
        if state.connection is ConnectionPhase.CONNECTED
        else OutputPhase.OFF,
        notice=None,
    )


def format_duration(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3_600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _reduce_host(state: PresentationState, event: HostEvent) -> PresentationState:
    if event.kind == "proposal_expired":
        # The event intentionally carries the previous output for diagnostics.
        # It is not current renderer output and must never repaint stale cells.
        return replace(state, output=OutputPhase.OFF)
    if event.kind in {"switching", "stopping", "stopped"}:
        return replace(state, output=OutputPhase.OFF)
    if event.kind in {
        "start_failed",
        "stop_failed",
        "input_failed",
        "scene_sink_failed",
        "proposal_rejected",
    }:
        return replace(state, output=OutputPhase.OFF, notice=event.message)
    if event.output is None:
        return state

    next_state = _from_output(state, event.output)
    if state.output is OutputPhase.ACTIVE:
        return replace(next_state, output=OutputPhase.ACTIVE)
    output = (
        OutputPhase.PENDING
        if state.connection is ConnectionPhase.CONNECTED
        else OutputPhase.OFF
    )
    return replace(next_state, output=output)


def _reduce_device(state: PresentationState, event: DeviceEvent) -> PresentationState:
    if event.kind == "connecting":
        return replace(
            state,
            connection=ConnectionPhase.CONNECTING,
            connection_label="Connecting",
            output=OutputPhase.UNKNOWN,
        )
    if event.kind == "reconnecting":
        return replace(
            state,
            connection=ConnectionPhase.RECONNECTING,
            connection_label="Reconnecting",
            output=OutputPhase.UNKNOWN,
        )
    if event.kind == "connected":
        body = event.body or {}
        device_id = body.get("device_id")
        return replace(
            state,
            connection=ConnectionPhase.CONNECTED,
            connection_label="Connected",
            device_id=device_id if isinstance(device_id, str) else None,
            output=OutputPhase.PENDING,
            notice=None,
        )
    if event.kind == "disconnected":
        return replace(
            state,
            connection=ConnectionPhase.DISCONNECTED,
            connection_label="Not connected",
            output=OutputPhase.UNKNOWN,
        )
    if event.kind == "error":
        return replace(
            state,
            connection=ConnectionPhase.ATTENTION,
            connection_label="Connection issue",
            output=OutputPhase.UNKNOWN,
            notice=event.message,
        )
    if event.kind == "device_error":
        return replace(state, notice=event.message)
    if event.kind == "scene_loaded":
        return replace(state, output=OutputPhase.ACTIVE)
    if event.kind == "scene_cleared":
        return replace(state, output=OutputPhase.OFF)
    if event.kind == "status" and event.body is not None:
        scene_state = event.body.get("scene_state")
        if scene_state == "active":
            return replace(state, output=OutputPhase.ACTIVE)
        if scene_state in {"off", "idle", "expired"}:
            return replace(state, output=OutputPhase.OFF)
    return state


def _from_output(state: PresentationState, output: ActivePackOutput) -> PresentationState:
    proposal = output.proposal
    timeline = (
        proposal.recipe.reduced_motion
        if state.reduced_motion
        else proposal.recipe.standard
    )
    frames = timeline.frames
    if not frames:
        cells: tuple[RGB, ...] = OFF_CELLS
    elif timeline.playback is Playback.ONCE_HOLD:
        # The last frame is what the renderer physically holds after the cue.
        cells = frames[-1].cells
    else:
        cells = frames[0].cells
    same_visual = (
        state.active_pack_id == output.pack_id
        and state.active_state_key == proposal.state_key
        and state.visual_timeline == timeline
    )
    if same_visual:
        visual_started = state.visual_started_monotonic_ns
        visual_initial = state.visual_initial_cells
    else:
        visual_started = output.accepted_monotonic_ns
        visual_initial = state.displayed_cells_at(visual_started)
    semantic = {
        "attention": proposal.recipe.attention,
        "detail": proposal.explanation.detail,
        "suggested_action": proposal.explanation.suggested_action,
        "source_observed_at": proposal.source_observed_at,
        "output_expires_monotonic_ns": output.expires_monotonic_ns,
        "output_accepted_monotonic_ns": output.accepted_monotonic_ns,
        "activation_generation": output.generation,
        "output_sequence": output.output_sequence,
    }
    if output.pack_id == FOCUS_PACK_ID:
        focus = _focus_phase(proposal.state_key)
        progress = proposal.progress if proposal.progress is not None else 0.0
        remaining = _remaining_seconds(focus, state.duration_seconds, progress)
        return replace(
            state,
            active_pack_id=FOCUS_PACK_ID,
            active_pack_name="Focus",
            active_state_key=proposal.state_key,
            headline="",
            focus=focus,
            remaining_seconds=remaining,
            progress=progress,
            semantic_cells=cells,
            visual_timeline=timeline,
            visual_started_monotonic_ns=visual_started,
            visual_initial_cells=visual_initial,
            cell_label_groups=(),
            notice=None,
            **semantic,
        )
    if output.pack_id == AGENT_PACK_ID:
        return replace(
            state,
            active_pack_id=AGENT_PACK_ID,
            active_pack_name="Agent",
            active_state_key=proposal.state_key,
            headline=_agent_headline(proposal.state_key),
            focus=FocusPhase.IDLE,
            progress=0.0,
            semantic_cells=cells,
            visual_timeline=timeline,
            visual_started_monotonic_ns=visual_started,
            visual_initial_cells=visual_initial,
            cell_label_groups=(),
            notice=None,
            **semantic,
        )
    return replace(
        state,
        active_pack_id=output.pack_id,
        active_pack_name=output.pack_id.rsplit(".", 1)[-1].title(),
        active_state_key=proposal.state_key,
        headline=proposal.explanation.summary.rstrip("."),
        focus=FocusPhase.UNKNOWN,
        progress=proposal.progress or 0.0,
        semantic_cells=cells,
        visual_timeline=timeline,
        visual_started_monotonic_ns=visual_started,
        visual_initial_cells=visual_initial,
        notice=None,
        **semantic,
    )


def sample_timeline_cells(
    timeline: Timeline,
    elapsed_ms: int,
    initial_cells: Cells6 = cast(Cells6, OFF_CELLS),
) -> Cells6:
    """Mirror the firmware renderer's keyframe timing and interpolation."""

    frames = timeline.frames
    if not frames:
        return cast(Cells6, OFF_CELLS)
    elapsed = max(0, int(elapsed_ms))
    cycle_ms = sum(frame.transition_ms + frame.hold_ms for frame in frames)
    source = initial_cells
    if timeline.playback is Playback.LOOP:
        if cycle_ms <= 0:
            return frames[-1].cells
        if elapsed >= cycle_ms:
            elapsed %= cycle_ms
            source = frames[-1].cells
    elif elapsed >= cycle_ms:
        if timeline.playback is Playback.ONCE_HOLD:
            return frames[-1].cells
        return cast(Cells6, OFF_CELLS)

    cursor = 0
    for frame in frames:
        transition_end = cursor + frame.transition_ms
        if elapsed < transition_end:
            within = elapsed - cursor
            return cast(
                Cells6,
                tuple(
                    RGB(
                        _interpolate_channel(before.r, after.r, within, frame.transition_ms),
                        _interpolate_channel(before.g, after.g, within, frame.transition_ms),
                        _interpolate_channel(before.b, after.b, within, frame.transition_ms),
                    )
                    for before, after in zip(source, frame.cells, strict=True)
                ),
            )
        cursor = transition_end
        hold_end = cursor + frame.hold_ms
        if elapsed < hold_end:
            return frame.cells
        cursor = hold_end
        source = frame.cells
    return frames[-1].cells


def _interpolate_channel(start: int, end: int, elapsed: int, duration: int) -> int:
    if duration == 0:
        return end
    return start + (end - start) * elapsed // duration


def _agent_headline(state_key: str) -> str:
    value = state_key.removeprefix("agent.")
    return {
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
    }.get(value, "Agent state unavailable")


def _focus_phase(state_key: str) -> FocusPhase:
    value = state_key.removeprefix("focus.")
    try:
        return FocusPhase(value)
    except ValueError:
        return FocusPhase.UNKNOWN


def _remaining_seconds(
    focus: FocusPhase, duration_seconds: int, progress: float
) -> int:
    if focus is FocusPhase.COMPLETED:
        return 0
    if focus in {FocusPhase.WORKING, FocusPhase.PAUSED, FocusPhase.CANCELLED}:
        # Progress crosses the frozen pack boundary as a float.  Remove only a
        # sub-nanosecond representation residue before applying the pack's
        # ceiling rule, otherwise exact second boundaries can display +1 sec.
        remaining = duration_seconds * (1.0 - progress)
        return max(0, math.ceil(remaining - 1e-9))
    return duration_seconds


__all__ = [
    "CellLabelGroup",
    "ConnectionPhase",
    "FocusPhase",
    "OFF_CELLS",
    "OutputPhase",
    "PresentationState",
    "format_duration",
    "reduce_event",
    "sample_timeline_cells",
    "with_duration",
]