"""Deterministic, local-only Focus timer application pack."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import cast

from codex_beacon.contracts import (
    AttentionClass,
    ButtonBinding,
    ButtonGesture,
    ButtonInput,
    Cells6,
    Clock,
    Explanation,
    PackContext,
    PackInput,
    PackProposal,
    Playback,
    RGB,
    RecipeFrame,
    Timeline,
    Transition,
    TrayActionInput,
    VisualRecipe,
)


ACTION_START_PAUSE = "focus.start_pause"
ACTION_RESET = "focus.reset"
ACTION_CANCEL = "focus.cancel"

DEFAULT_DURATION_MINUTES = 25
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 240
STAGE_COUNT = 6
NANOSECONDS_PER_SECOND = 1_000_000_000
WORKING_REFRESH_SECONDS = 1.0
WORKING_VALID_FOR_MS = 2_000
STEADY_VALID_FOR_MS = 60_000
COMPLETION_VALID_FOR_MS = 15_000


class FocusState(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


BUTTON_BINDINGS = (
    ButtonBinding(ButtonGesture.TAP, ACTION_START_PAUSE, "Start or pause Focus"),
    ButtonBinding(ButtonGesture.PRESS, ACTION_RESET, "Reset Focus"),
    ButtonBinding(ButtonGesture.LONG_PRESS, ACTION_CANCEL, "Cancel Focus"),
)


OFF = RGB(0, 0, 0)
IDLE_LOW = RGB(0, 4, 10)
IDLE_HIGH = RGB(0, 10, 22)
WORK_DONE = RGB(0, 76, 176)
WORK_CURRENT_LOW = RGB(0, 32, 76)
WORK_CURRENT_HIGH = RGB(0, 118, 220)
PAUSED_DONE = RGB(116, 58, 0)
PAUSED_CURRENT_LOW = RGB(84, 34, 0)
PAUSED_CURRENT_HIGH = RGB(188, 96, 0)
COMPLETE_LOW = RGB(0, 52, 22)
COMPLETE_HIGH = RGB(0, 176, 70)
CANCELLED_LOW = RGB(72, 4, 4)
CANCELLED_HIGH = RGB(156, 12, 8)
UNKNOWN_LOW = RGB(42, 10, 64)
UNKNOWN_HIGH = RGB(112, 28, 150)


def completed_stages(elapsed_ns: int, duration_ns: int) -> int:
    """Return the completed stage count with exact integer boundaries."""

    for name, value in (("elapsed_ns", elapsed_ns), ("duration_ns", duration_ns)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
    if duration_ns <= 0:
        raise ValueError("duration_ns must be positive")
    if elapsed_ns <= 0:
        return 0
    if elapsed_ns >= duration_ns:
        return STAGE_COUNT
    return (elapsed_ns * STAGE_COUNT) // duration_ns


class FocusPack:
    """One activation of the built-in six-stage Focus timer."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._context: PackContext | None = None
        self._state = FocusState.IDLE
        self._duration_ns = DEFAULT_DURATION_MINUTES * 60 * NANOSECONDS_PER_SECOND
        self._remaining_ns = self._duration_ns
        self._deadline_ns: int | None = None
        self._worker: asyncio.Task[None] | None = None
        self._epoch = 0
        self._started = False
        self._stopped = False
        self._settings_error: str | None = None

    @property
    def state(self) -> FocusState:
        """Current semantic state, primarily for local diagnostics."""

        return self._state

    @property
    def duration_minutes(self) -> int:
        return self._duration_ns // (60 * NANOSECONDS_PER_SECOND)

    async def start(self, context: PackContext) -> None:
        """Activate the timer and publish its required idle proposal."""

        async with self._lock:
            if self._started and not self._stopped:
                raise RuntimeError("Focus pack is already active")
            self._context = context
            self._started = True
            self._stopped = False
            self._epoch += 1
            self._worker = None
            self._deadline_ns = None
            try:
                duration_minutes = _duration_minutes(context)
            except (TypeError, ValueError) as exc:
                self._settings_error = str(exc)
                self._state = FocusState.UNKNOWN
                self._remaining_ns = self._duration_ns
            else:
                self._settings_error = None
                self._duration_ns = duration_minutes * 60 * NANOSECONDS_PER_SECOND
                self._remaining_ns = self._duration_ns
                self._state = FocusState.IDLE
            await self._publish_locked()

    async def stop(self) -> None:
        """Invalidate and settle the timer job without publishing a final state."""

        task: asyncio.Task[None] | None
        async with self._lock:
            if not self._started or self._stopped:
                return
            self._stopped = True
            self._epoch += 1
            task = self._detach_worker_locked()
            self._deadline_ns = None
            self._context = None
        await _settle_cancelled(task)

    async def handle_input(self, event: PackInput) -> None:
        """Apply one host-deduplicated button or tray action."""

        task: asyncio.Task[None] | None = None
        async with self._lock:
            if not self._started or self._stopped or self._context is None:
                return
            action = _action_for_input(event)
            if action == ACTION_START_PAUSE:
                task = await self._start_pause_locked()
            elif action == ACTION_RESET:
                task = await self._reset_locked()
            elif action == ACTION_CANCEL:
                task = await self._cancel_locked()
            else:
                task = self._invalidate_worker_locked()
                self._deadline_ns = None
                self._state = FocusState.UNKNOWN
                await self._publish_locked()
        await _settle_cancelled(task)

    async def _start_pause_locked(self) -> asyncio.Task[None] | None:
        if self._settings_error is not None:
            self._state = FocusState.UNKNOWN
            await self._publish_locked()
            return None

        if self._state is FocusState.WORKING:
            now = self._clock_locked().monotonic_ns()
            assert self._deadline_ns is not None
            self._remaining_ns = max(0, self._deadline_ns - now)
            task = self._invalidate_worker_locked()
            self._deadline_ns = None
            self._state = (
                FocusState.COMPLETED
                if self._remaining_ns == 0
                else FocusState.PAUSED
            )
            await self._publish_locked()
            return task

        task = self._invalidate_worker_locked()
        if self._state is not FocusState.PAUSED or self._remaining_ns <= 0:
            self._remaining_ns = self._duration_ns
        self._deadline_ns = self._clock_locked().monotonic_ns() + self._remaining_ns
        self._state = FocusState.WORKING
        epoch = self._epoch
        await self._publish_locked()
        context = self._context
        assert context is not None
        self._worker = context.spawn(
            self._working_loop(epoch),
            name=f"focus-countdown-{epoch}",
        )
        return task

    async def _reset_locked(self) -> asyncio.Task[None] | None:
        task = self._invalidate_worker_locked()
        self._deadline_ns = None
        self._remaining_ns = self._duration_ns
        self._state = (
            FocusState.UNKNOWN if self._settings_error is not None else FocusState.IDLE
        )
        await self._publish_locked()
        return task

    async def _cancel_locked(self) -> asyncio.Task[None] | None:
        if self._state is FocusState.WORKING:
            now = self._clock_locked().monotonic_ns()
            assert self._deadline_ns is not None
            self._remaining_ns = max(0, self._deadline_ns - now)
        task = self._invalidate_worker_locked()
        self._deadline_ns = None
        self._state = (
            FocusState.UNKNOWN if self._settings_error is not None else FocusState.CANCELLED
        )
        await self._publish_locked()
        return task

    async def _working_loop(self, epoch: int) -> None:
        try:
            while True:
                async with self._lock:
                    if not self._working_is_current_locked(epoch):
                        return
                    now = self._clock_locked().monotonic_ns()
                    assert self._deadline_ns is not None
                    remaining_ns = max(0, self._deadline_ns - now)
                    if remaining_ns == 0:
                        self._remaining_ns = 0
                        self._deadline_ns = None
                        self._state = FocusState.COMPLETED
                        self._worker = None
                        self._epoch += 1
                        await self._publish_locked()
                        return
                    sleep_seconds = min(
                        WORKING_REFRESH_SECONDS,
                        remaining_ns / NANOSECONDS_PER_SECOND,
                    )

                await self._clock_for_epoch(epoch).sleep(sleep_seconds)

                async with self._lock:
                    if not self._working_is_current_locked(epoch):
                        return
                    now = self._clock_locked().monotonic_ns()
                    assert self._deadline_ns is not None
                    self._remaining_ns = max(0, self._deadline_ns - now)
                    if self._remaining_ns == 0:
                        self._deadline_ns = None
                        self._state = FocusState.COMPLETED
                        self._worker = None
                        self._epoch += 1
                        await self._publish_locked()
                        return
                    await self._publish_locked()
        except asyncio.CancelledError:
            raise

    def _working_is_current_locked(self, epoch: int) -> bool:
        return (
            self._started
            and not self._stopped
            and self._context is not None
            and self._state is FocusState.WORKING
            and self._deadline_ns is not None
            and self._epoch == epoch
            and self._worker is asyncio.current_task()
        )

    def _clock_for_epoch(self, epoch: int) -> Clock:
        context = self._context
        if (
            context is None
            or self._stopped
            or self._epoch != epoch
            or self._state is not FocusState.WORKING
        ):
            raise asyncio.CancelledError
        return context.clock

    def _clock_locked(self) -> Clock:
        context = self._context
        if context is None:
            raise RuntimeError("Focus pack is not active")
        return context.clock

    def _detach_worker_locked(self) -> asyncio.Task[None] | None:
        task = self._worker
        self._worker = None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
        return task

    def _invalidate_worker_locked(self) -> asyncio.Task[None] | None:
        self._epoch += 1
        return self._detach_worker_locked()

    async def _publish_locked(self) -> None:
        context = self._context
        if context is None or self._stopped:
            return
        now_ns = context.clock.monotonic_ns()
        remaining_ns = self._remaining_at_locked(now_ns)
        elapsed_ns = max(0, self._duration_ns - remaining_ns)
        progress = min(1.0, elapsed_ns / self._duration_ns)
        stage = completed_stages(elapsed_ns, self._duration_ns)
        state = self._state
        valid_for_ms = (
            WORKING_VALID_FOR_MS
            if state is FocusState.WORKING
            else COMPLETION_VALID_FOR_MS
            if state is FocusState.COMPLETED
            else STEADY_VALID_FOR_MS
        )
        await context.publish(
            PackProposal(
                state_key=f"focus.{state.value}",
                source_observed_at=context.clock.utcnow(),
                valid_for_ms=valid_for_ms,
                confidence=0.0 if state is FocusState.UNKNOWN else 1.0,
                explanation=_explanation(state, remaining_ns, self._settings_error),
                recipe=_recipe(state, stage),
                progress=None if state is FocusState.UNKNOWN else progress,
                button_bindings=BUTTON_BINDINGS,
            )
        )

    def _remaining_at_locked(self, now_ns: int) -> int:
        if self._state is FocusState.WORKING and self._deadline_ns is not None:
            return max(0, self._deadline_ns - now_ns)
        return self._remaining_ns


def _duration_minutes(context: PackContext) -> int:
    settings = context.settings
    unexpected = set(settings) - {"duration_minutes"}
    if unexpected:
        raise ValueError("Focus settings contain unsupported fields")
    value = settings.get("duration_minutes", DEFAULT_DURATION_MINUTES)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("duration_minutes must be an integer")
    if not MIN_DURATION_MINUTES <= value <= MAX_DURATION_MINUTES:
        raise ValueError("duration_minutes must be between 1 and 240")
    return value


def _action_for_input(event: PackInput) -> str | None:
    if isinstance(event, ButtonInput):
        return {
            ButtonGesture.TAP: ACTION_START_PAUSE,
            ButtonGesture.PRESS: ACTION_RESET,
            ButtonGesture.LONG_PRESS: ACTION_CANCEL,
        }.get(event.gesture)
    if isinstance(event, TrayActionInput):
        return event.action_id
    return None


async def _settle_cancelled(task: asyncio.Task[None] | None) -> None:
    if task is None or task is asyncio.current_task():
        return
    try:
        await task
    except asyncio.CancelledError:
        pass


def _explanation(
    state: FocusState,
    remaining_ns: int,
    settings_error: str | None,
) -> Explanation:
    if state is FocusState.IDLE:
        return Explanation(
            "Focus timer is ready.",
            "Start when you are ready to focus.",
            suggested_action="Start Focus",
        )
    if state is FocusState.WORKING:
        return Explanation(
            "Focus session is running.",
            f"{_remaining_text(remaining_ns)} remain in this local countdown.",
            evidence=("Local monotonic timer",),
            suggested_action="Pause Focus",
        )
    if state is FocusState.PAUSED:
        return Explanation(
            "Focus session is paused.",
            f"{_remaining_text(remaining_ns)} remain.",
            evidence=("Local monotonic timer",),
            suggested_action="Resume Focus",
        )
    if state is FocusState.COMPLETED:
        return Explanation(
            "Focus session is complete.",
            "The local countdown reached its deadline.",
            evidence=("Local monotonic timer",),
            suggested_action="Reset Focus",
        )
    if state is FocusState.CANCELLED:
        return Explanation(
            "Focus session was cancelled.",
            "The countdown stopped before completion.",
            suggested_action="Start Focus",
        )
    return Explanation(
        "Focus state is unavailable.",
        settings_error or "The Focus pack received an unsupported action.",
        suggested_action="Check Focus settings",
    )


def _remaining_text(remaining_ns: int) -> str:
    total_seconds = max(
        0,
        (remaining_ns + NANOSECONDS_PER_SECOND - 1) // NANOSECONDS_PER_SECOND,
    )
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def _recipe(state: FocusState, stage: int) -> VisualRecipe:
    if state is FocusState.IDLE:
        standard = _loop(
            _frame(_solid_with_last(IDLE_LOW), 700, 800),
            _frame(_solid_with_last(IDLE_HIGH), 700, 800),
        )
        reduced = _loop(_frame(_cells(), 0, 1_000, Transition.STEP))
        return VisualRecipe(standard, reduced, 0.18, AttentionClass.AMBIENT)

    if state is FocusState.WORKING:
        standard = _loop(
            _frame(_progress_cells(stage, WORK_CURRENT_HIGH, WORK_DONE), 450, 550),
            _frame(_progress_cells(stage, WORK_CURRENT_LOW, WORK_DONE), 450, 550),
        )
        reduced = _loop(
            _frame(
                _progress_cells(stage, WORK_CURRENT_LOW, WORK_DONE),
                0,
                1_000,
                Transition.STEP,
            )
        )
        return VisualRecipe(standard, reduced, 0.68, AttentionClass.NORMAL)

    if state is FocusState.PAUSED:
        standard = _loop(
            _frame(_progress_cells(stage, PAUSED_CURRENT_HIGH, PAUSED_DONE), 650, 650),
            _frame(_progress_cells(stage, PAUSED_CURRENT_LOW, PAUSED_DONE), 650, 650),
        )
        reduced = _loop(
            _frame(
                _progress_cells(stage, PAUSED_CURRENT_LOW, PAUSED_DONE),
                0,
                1_000,
                Transition.STEP,
            )
        )
        return VisualRecipe(standard, reduced, 0.54, AttentionClass.NORMAL)

    if state is FocusState.COMPLETED:
        standard = Timeline(
            (
                _frame(_cells(COMPLETE_LOW), 0, 250, Transition.STEP),
                _frame(_cells(COMPLETE_HIGH), 700, 1_300),
            ),
            Playback.ONCE_HOLD,
        )
        reduced = Timeline(
            (_frame(_cells(COMPLETE_HIGH), 0, 2_000, Transition.STEP),),
            Playback.ONCE_HOLD,
        )
        return VisualRecipe(standard, reduced, 0.72, AttentionClass.ATTENTION)

    if state is FocusState.CANCELLED:
        standard = Timeline(
            (
                _frame(_cells(CANCELLED_HIGH), 0, 350, Transition.STEP),
                _frame(_cells(CANCELLED_LOW), 700, 950),
            ),
            Playback.ONCE_HOLD,
        )
        reduced = Timeline(
            (_frame(_cells(CANCELLED_LOW), 0, 2_000, Transition.STEP),),
            Playback.ONCE_HOLD,
        )
        return VisualRecipe(standard, reduced, 0.46, AttentionClass.NORMAL)

    standard = _loop(
        _frame(_alternating(UNKNOWN_LOW, OFF), 800, 700),
        _frame(_alternating(OFF, UNKNOWN_HIGH), 800, 700),
    )
    reduced = _loop(
        _frame(_alternating(UNKNOWN_LOW, OFF), 0, 1_000, Transition.STEP)
    )
    return VisualRecipe(standard, reduced, 0.42, AttentionClass.ATTENTION)


def _loop(*frames: RecipeFrame) -> Timeline:
    return Timeline(tuple(frames), Playback.LOOP)


def _frame(
    cells: Cells6,
    transition_ms: int,
    hold_ms: int,
    transition: Transition = Transition.LINEAR,
) -> RecipeFrame:
    return RecipeFrame(cells, transition_ms, hold_ms, transition)


def _cells(color: RGB = OFF) -> Cells6:
    return cast(Cells6, (color,) * STAGE_COUNT)


def _solid_with_last(color: RGB) -> Cells6:
    return cast(Cells6, (OFF, OFF, OFF, OFF, OFF, color))


def _alternating(even: RGB, odd: RGB) -> Cells6:
    return cast(
        Cells6,
        tuple(even if index % 2 == 0 else odd for index in range(STAGE_COUNT)),
    )


def _progress_cells(stage: int, current: RGB, completed: RGB) -> Cells6:
    values = [completed if index < stage else OFF for index in range(STAGE_COUNT)]
    if stage < STAGE_COUNT:
        values[stage] = current
    return cast(Cells6, tuple(values))
