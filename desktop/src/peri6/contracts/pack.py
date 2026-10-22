"""Frozen application-pack API v1.

These types are desktop-only.  Firmware and transport modules must never receive
pack IDs, application state, explanations, confidence, progress, or button
meanings.
"""

from __future__ import annotations

import asyncio
import math
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Awaitable, Mapping, Protocol, TypeAlias, runtime_checkable
from uuid import UUID


STATE_KEY_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
MIN_PROPOSAL_TTL_MS = 250
MAX_PROPOSAL_TTL_MS = 60_000
MAX_EXPLANATION_SUMMARY = 160


class Playback(str, Enum):
    LOOP = "loop"
    ONCE_CLEAR = "once_clear"
    ONCE_HOLD = "once_hold"


class Transition(str, Enum):
    STEP = "step"
    LINEAR = "linear"


class AttentionClass(str, Enum):
    AMBIENT = "ambient"
    NORMAL = "normal"
    ATTENTION = "attention"
    URGENT = "urgent"


class ButtonGesture(str, Enum):
    TAP = "tap"
    PRESS = "press"
    LONG_PRESS = "long_press"


@dataclass(frozen=True, slots=True)
class RGB:
    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for channel in (self.r, self.g, self.b):
            if isinstance(channel, bool) or not isinstance(channel, int):
                raise TypeError("RGB channels must be integers")
            if not 0 <= channel <= 255:
                raise ValueError("RGB channels must be between 0 and 255")


Cells6: TypeAlias = tuple[RGB, RGB, RGB, RGB, RGB, RGB]


@dataclass(frozen=True, slots=True)
class RecipeFrame:
    cells: Cells6
    transition_ms: int
    hold_ms: int
    transition: Transition = Transition.LINEAR


@dataclass(frozen=True, slots=True)
class Timeline:
    frames: tuple[RecipeFrame, ...]
    playback: Playback


@dataclass(frozen=True, slots=True)
class VisualRecipe:
    """A pack-owned pattern with a mandatory reduced-motion alternative."""

    standard: Timeline
    reduced_motion: Timeline
    requested_brightness: float
    attention: AttentionClass = AttentionClass.NORMAL


@dataclass(frozen=True, slots=True)
class Explanation:
    summary: str
    detail: str = ""
    evidence: tuple[str, ...] = ()
    suggested_action: str | None = None


@dataclass(frozen=True, slots=True)
class ButtonBinding:
    gesture: ButtonGesture
    action_id: str
    label: str


@dataclass(frozen=True, slots=True)
class PackProposal:
    """A pack's desktop-only semantic output."""

    state_key: str
    source_observed_at: datetime
    valid_for_ms: int
    confidence: float
    explanation: Explanation
    recipe: VisualRecipe
    progress: float | None = None
    button_bindings: tuple[ButtonBinding, ...] = ()


@dataclass(frozen=True, slots=True)
class ButtonInput:
    input_id: UUID
    gesture: ButtonGesture
    occurred_monotonic_ns: int


@dataclass(frozen=True, slots=True)
class TrayActionInput:
    input_id: UUID
    action_id: str
    occurred_monotonic_ns: int


PackInput: TypeAlias = ButtonInput | TrayActionInput


class PublishStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED_STALE_ACTIVATION = "rejected_stale_activation"
    REJECTED_INVALID = "rejected_invalid"
    REJECTED_HOST_STOPPING = "rejected_host_stopping"


@dataclass(frozen=True, slots=True)
class PublishReceipt:
    status: PublishStatus
    output_sequence: int | None = None
    reason: str | None = None


class Clock(Protocol):
    def monotonic_ns(self) -> int: ...

    def utcnow(self) -> datetime: ...

    async def sleep(self, seconds: float) -> None: ...


class PackContext(Protocol):
    @property
    def pack_id(self) -> str: ...

    @property
    def activation_id(self) -> UUID: ...

    @property
    def generation(self) -> int: ...

    @property
    def settings(self) -> Mapping[str, object]: ...

    @property
    def clock(self) -> Clock: ...

    async def publish(self, proposal: PackProposal) -> PublishReceipt: ...

    def spawn(self, job: Awaitable[None], *, name: str) -> asyncio.Task[None]: ...


@runtime_checkable
class ApplicationPack(Protocol):
    async def start(self, context: PackContext) -> None: ...

    async def stop(self) -> None: ...

    async def handle_input(self, event: PackInput) -> None: ...


class PackFactory(Protocol):
    def __call__(self) -> ApplicationPack: ...


@dataclass(frozen=True, slots=True)
class ActivePackOutput:
    """Host-owned wrapper around the currently accepted proposal."""

    pack_id: str
    activation_id: UUID
    generation: int
    output_sequence: int
    accepted_monotonic_ns: int
    expires_monotonic_ns: int
    proposal: PackProposal


def validate_proposal(proposal: PackProposal) -> None:
    """Validate pack-local bounds before any scene compilation begins."""

    if not isinstance(proposal, PackProposal):
        raise TypeError("proposal must be a PackProposal")
    if not isinstance(proposal.state_key, str) or not STATE_KEY_RE.fullmatch(
        proposal.state_key
    ):
        raise ValueError("invalid state_key")
    if not isinstance(proposal.source_observed_at, datetime) or (
        proposal.source_observed_at.tzinfo is None
        or proposal.source_observed_at.utcoffset() is None
    ):
        raise ValueError("source_observed_at must be timezone-aware")
    if (
        isinstance(proposal.valid_for_ms, bool)
        or not isinstance(proposal.valid_for_ms, int)
        or not MIN_PROPOSAL_TTL_MS
        <= proposal.valid_for_ms
        <= MAX_PROPOSAL_TTL_MS
    ):
        raise ValueError("valid_for_ms is outside the host API v1 range")
    _finite_unit_interval("confidence", proposal.confidence)
    if proposal.progress is not None:
        _finite_unit_interval("progress", proposal.progress)
    if not isinstance(proposal.recipe, VisualRecipe):
        raise TypeError("recipe must be a VisualRecipe")
    _finite_unit_interval(
        "requested_brightness", proposal.recipe.requested_brightness
    )
    if not isinstance(proposal.recipe.attention, AttentionClass):
        raise TypeError("attention must be an AttentionClass")
    if not isinstance(proposal.explanation, Explanation):
        raise TypeError("explanation must be an Explanation")
    if not isinstance(proposal.explanation.summary, str) or not (
        1 <= len(proposal.explanation.summary) <= MAX_EXPLANATION_SUMMARY
    ):
        raise ValueError("explanation summary must contain 1 to 160 characters")
    if not isinstance(proposal.explanation.detail, str):
        raise TypeError("explanation detail must be a string")
    if not isinstance(proposal.explanation.evidence, tuple) or not all(
        isinstance(item, str) for item in proposal.explanation.evidence
    ):
        raise TypeError("explanation evidence must be a tuple of strings")
    if proposal.explanation.suggested_action is not None and not isinstance(
        proposal.explanation.suggested_action, str
    ):
        raise TypeError("suggested_action must be a string or None")
    if not isinstance(proposal.button_bindings, tuple):
        raise TypeError("button_bindings must be a tuple")
    seen_gestures: set[ButtonGesture] = set()
    for binding in proposal.button_bindings:
        if not isinstance(binding, ButtonBinding) or not isinstance(
            binding.gesture, ButtonGesture
        ):
            raise TypeError("invalid button binding")
        if binding.gesture in seen_gestures:
            raise ValueError("a gesture may be bound only once")
        seen_gestures.add(binding.gesture)
        if not STATE_KEY_RE.fullmatch(binding.action_id):
            raise ValueError("invalid button action_id")
        if not isinstance(binding.label, str) or not 1 <= len(binding.label) <= 64:
            raise ValueError("button label must contain 1 to 64 characters")
    _validate_timeline(proposal.recipe.standard)
    _validate_timeline(proposal.recipe.reduced_motion)


def _finite_unit_interval(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and between 0 and 1")


def _validate_timeline(timeline: Timeline) -> None:
    if not isinstance(timeline, Timeline):
        raise TypeError("timeline must be a Timeline")
    if not isinstance(timeline.playback, Playback):
        raise TypeError("timeline playback must be a Playback")
    if not isinstance(timeline.frames, tuple):
        raise TypeError("timeline frames must be a tuple")
    if not timeline.frames:
        raise ValueError("each timeline needs at least one frame")
    for frame in timeline.frames:
        if not isinstance(frame, RecipeFrame):
            raise TypeError("timeline items must be RecipeFrame values")
        if not isinstance(frame.transition, Transition):
            raise TypeError("frame transition must be a Transition")
        if not isinstance(frame.cells, tuple):
            raise TypeError("frame cells must be a tuple")
        if len(frame.cells) != 6:
            raise ValueError("each recipe frame needs exactly six cells")
        if not all(isinstance(cell, RGB) for cell in frame.cells):
            raise TypeError("every recipe cell must be an RGB value")
        for name, value in (
            ("transition_ms", frame.transition_ms),
            ("hold_ms", frame.hold_ms),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if frame.transition is Transition.STEP and frame.transition_ms != 0:
            raise ValueError("step transitions must have transition_ms = 0")
