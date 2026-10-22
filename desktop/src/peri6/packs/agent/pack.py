"""Built-in Agent state pack driven by privacy-safe Codex hook events."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import cast

from peri6.contracts import (
    AttentionClass,
    Cells6,
    Explanation,
    PackContext,
    PackInput,
    PackProposal,
    Playback,
    RGB,
    RecipeFrame,
    Timeline,
    Transition,
    VisualRecipe,
)

from .bridge import AgentEventServer
from .events import (
    PROVIDER_LABELS,
    AgentObservation,
    AgentOutcome,
    AgentState,
    AgentTask,
)


REFRESH_SECONDS = 45.0
ACTIVE_VALID_FOR_MS = 60_000
TERMINAL_VALID_FOR_MS = 10_000
# Codex does not emit Stop when a user cancels a turn. Bound ordinary
# thinking/working/editing states so a missing terminal hook cannot leave the
# companion active indefinitely. Tests and builds retain their longer lease.
STALE_ACTIVE_NS = 2 * 60 * 1_000_000_000
STALE_LONG_TASK_NS = 2 * 60 * 60 * 1_000_000_000
STALE_WAITING_NS = 30 * 60 * 1_000_000_000
STALE_REVIEW_NS = 5 * 60 * 1_000_000_000
SEEN_LIMIT = 256

OFF = RGB(0, 0, 0)
VIOLET = RGB(126, 82, 224)
VIOLET_LOW = RGB(25, 12, 56)
CYAN = RGB(0, 174, 210)
CYAN_LOW = RGB(0, 35, 48)
MAGENTA = RGB(205, 58, 154)
MAGENTA_LOW = RGB(48, 8, 34)
AMBER = RGB(224, 142, 0)
AMBER_LOW = RGB(54, 29, 0)
COBALT = RGB(49, 111, 232)
COBALT_LOW = RGB(8, 22, 56)
ORANGE = RGB(232, 86, 24)
ORANGE_LOW = RGB(55, 13, 2)
GREEN = RGB(20, 184, 88)
GREEN_LOW = RGB(3, 48, 21)
RED = RGB(218, 54, 48)
RED_LOW = RGB(55, 5, 5)
LAVENDER = RGB(174, 139, 242)


class AgentPack:
    """Translate normalized local Agent observations into six-cell recipes."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._context: PackContext | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: AgentEventServer | None = None
        self._state = AgentState.IDLE
        self._active_provider = "codex"
        self._sessions: dict[str, AgentObservation] = {}
        self._last_received_ns = 0
        self._seen_order: deque[str] = deque()
        self._seen: set[str] = set()
        self._finished_tool_order: deque[str] = deque()
        self._finished_tools: set[str] = set()
        self._terminal_turn_order: deque[str] = deque()
        self._terminal_turns: set[str] = set()
        self._started = False
        self._stopped = False

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def listen_port(self) -> int | None:
        server = self._server
        return server.port if server is not None else None

    async def start(self, context: PackContext) -> None:
        settings = context.settings
        unexpected = set(settings) - {"listen_port", "bearer_token"}
        if unexpected:
            raise ValueError("Agent settings contain unsupported fields")
        port = settings.get("listen_port")
        token = settings.get("bearer_token")
        if isinstance(port, bool) or not isinstance(port, int):
            raise TypeError("listen_port must be an integer")
        if not isinstance(token, str):
            raise TypeError("bearer_token must be a string")

        async with self._lock:
            if self._started and not self._stopped:
                raise RuntimeError("Agent pack is already active")
            self._context = context
            self._loop = asyncio.get_running_loop()
            self._started = True
            self._stopped = False
            self._state = AgentState.IDLE
            self._active_provider = "codex"
            self._sessions.clear()
            self._last_received_ns = context.clock.monotonic_ns()
            self._seen_order.clear()
            self._seen.clear()
            self._finished_tool_order.clear()
            self._finished_tools.clear()
            self._terminal_turn_order.clear()
            self._terminal_turns.clear()
            self._server = AgentEventServer(
                port=port,
                bearer_token=token,
                callback=self._receive_from_thread,
            )
            self._server.start()
            await self._publish_locked()
            context.spawn(self._refresh_loop(), name="agent-state-refresh")

    async def stop(self) -> None:
        server: AgentEventServer | None
        async with self._lock:
            if not self._started or self._stopped:
                return
            self._stopped = True
            server = self._server
            self._server = None
            self._context = None
            self._loop = None
        if server is not None:
            await asyncio.to_thread(server.stop)

    async def handle_input(self, _event: PackInput) -> None:
        # Agent mode is observational. Physical and tray actions never control Codex.
        return

    async def observe(self, observation: AgentObservation) -> None:
        """Accept a validated observation; public for contract tests."""

        async with self._lock:
            context = self._context
            if context is None or self._stopped:
                return
            if observation.event_id in self._seen:
                return
            self._remember_locked(observation.event_id)
            if observation.turn_key in self._terminal_turns:
                return
            if (
                observation.event == "tool_started"
                and observation.tool_key is not None
                and observation.tool_key in self._finished_tools
            ):
                return
            if observation.event == "tool_finished" and observation.tool_key is not None:
                self._remember_bounded_locked(
                    observation.tool_key,
                    self._finished_tools,
                    self._finished_tool_order,
                )
            if observation.event in {"turn_stopped", "turn_cancelled", "session_ended"}:
                self._remember_bounded_locked(
                    observation.turn_key,
                    self._terminal_turns,
                    self._terminal_turn_order,
                )
            self._last_received_ns = context.clock.monotonic_ns()
            session = observation.session_key or "legacy"
            if observation.event in {"turn_cancelled", "session_ended"}:
                self._sessions.pop(session, None)
            else:
                self._sessions[session] = observation
            self._state, self._active_provider = _elect_session_state(self._sessions)
            await self._publish_locked()

    def _receive_from_thread(self, observation: AgentObservation) -> None:
        loop = self._loop
        if loop is None or loop.is_closed() or self._stopped:
            return
        loop.call_soon_threadsafe(self._schedule_observation, observation)

    def _schedule_observation(self, observation: AgentObservation) -> None:
        context = self._context
        if context is None or self._stopped:
            return
        context.spawn(
            self.observe(observation),
            name=f"agent-observation-{observation.event_id[:8]}",
        )

    def _remember_locked(self, event_id: str) -> None:
        self._remember_bounded_locked(event_id, self._seen, self._seen_order)

    @staticmethod
    def _remember_bounded_locked(
        value: str,
        values: set[str],
        order: deque[str],
    ) -> None:
        values.add(value)
        order.append(value)
        while len(order) > SEEN_LIMIT:
            values.discard(order.popleft())

    async def _refresh_loop(self) -> None:
        while True:
            context = self._context
            if context is None or self._stopped:
                return
            await context.clock.sleep(REFRESH_SECONDS)
            async with self._lock:
                context = self._context
                if context is None or self._stopped:
                    return
                state = self._state
                if state is AgentState.IDLE:
                    continue
                age = context.clock.monotonic_ns() - self._last_received_ns
                if age >= _stale_after_ns(state):
                    self._state = AgentState.IDLE
                    await self._publish_locked()
                elif state not in {AgentState.SUCCESS, AgentState.FAILURE}:
                    # Refresh only the desktop freshness lease. Equivalent device
                    # scenes are coalesced and their animation remains on the ESP.
                    await self._publish_locked()

    async def _publish_locked(self) -> None:
        context = self._context
        if context is None or self._stopped:
            return
        state = self._state
        await context.publish(
            PackProposal(
                state_key=f"agent.{state.value}",
                source_observed_at=context.clock.utcnow(),
                valid_for_ms=(
                    TERMINAL_VALID_FOR_MS
                    if state in {AgentState.SUCCESS, AgentState.FAILURE}
                    else ACTIVE_VALID_FOR_MS
                ),
                confidence=1.0,
                explanation=_explanation(state, self._active_provider),
                recipe=_recipe(state),
            )
        )


def _next_state(observation: AgentObservation) -> AgentState:
    if observation.event == "turn_started":
        return AgentState.THINKING
    if observation.event == "approval_waiting":
        return AgentState.WAITING
    if observation.event == "input_waiting":
        return AgentState.INPUT_WAITING
    if observation.event == "turn_stopped":
        return AgentState.REVIEW
    if observation.event == "tool_started":
        return _state_for_task(observation.task)
    if observation.event == "tool_finished":
        if observation.task in {AgentTask.TESTING, AgentTask.BUILDING}:
            if observation.outcome is AgentOutcome.SUCCESS:
                return AgentState.SUCCESS
            if observation.outcome is AgentOutcome.FAILURE:
                return AgentState.FAILURE
        return AgentState.THINKING
    return AgentState.IDLE


def _elect_session_state(
    sessions: dict[str, AgentObservation],
) -> tuple[AgentState, str]:
    if not sessions:
        return AgentState.IDLE, "codex"
    winner = max(
        sessions.values(),
        key=lambda observation: (
            _state_priority(_next_state(observation)),
            observation.occurred_monotonic_ns,
        ),
    )
    return _next_state(winner), winner.provider


def _state_priority(state: AgentState) -> int:
    return {
        AgentState.IDLE: 0,
        AgentState.SUCCESS: 1,
        AgentState.FAILURE: 1,
        AgentState.REVIEW: 2,
        AgentState.THINKING: 3,
        AgentState.EDITING: 4,
        AgentState.WORKING: 5,
        AgentState.TESTING: 6,
        AgentState.BUILDING: 6,
        AgentState.INPUT_WAITING: 7,
        AgentState.WAITING: 8,
    }[state]


def _state_for_task(task: AgentTask) -> AgentState:
    return {
        AgentTask.THINKING: AgentState.THINKING,
        AgentTask.WORKING: AgentState.WORKING,
        AgentTask.EDITING: AgentState.EDITING,
        AgentTask.TESTING: AgentState.TESTING,
        AgentTask.BUILDING: AgentState.BUILDING,
    }[task]


def _stale_after_ns(state: AgentState) -> int:
    if state in {AgentState.TESTING, AgentState.BUILDING}:
        return STALE_LONG_TASK_NS
    if state is AgentState.WAITING:
        return STALE_WAITING_NS
    if state is AgentState.REVIEW:
        return STALE_REVIEW_NS
    return STALE_ACTIVE_NS


def _explanation(state: AgentState, provider: str) -> Explanation:
    label = PROVIDER_LABELS.get(provider, "Agent")
    values = {
        AgentState.IDLE: (
            f"Waiting for {label}.",
            f"No active {label} turn is being observed.",
            None,
        ),
        AgentState.THINKING: (
            f"{label} is thinking.",
            f"A local {label} turn is active.",
            None,
        ),
        AgentState.WORKING: (
            f"{label} is working.",
            "A local tool is running.",
            None,
        ),
        AgentState.EDITING: (
            f"{label} is editing.",
            "A local file-edit operation is running.",
            None,
        ),
        AgentState.TESTING: (
            "Tests are running.",
            "Completion is unknown until the command exits.",
            None,
        ),
        AgentState.BUILDING: (
            "A build is running.",
            "Completion is unknown until the command exits.",
            None,
        ),
        AgentState.WAITING: (
            f"{label} needs approval.",
            "The current operation is waiting for a local decision.",
            "Approve or reply on your PC.",
        ),
        AgentState.INPUT_WAITING: (
            f"{label} needs input.",
            "The current turn is waiting for a local reply.",
            "Reply on your PC.",
        ),
        AgentState.SUCCESS: (
            "Checks passed.",
            "A test or build command reported exit code zero.",
            None,
        ),
        AgentState.FAILURE: (
            "A check failed.",
            "A test or build command reported a non-zero result.",
            "Open the failed check on your PC.",
        ),
        AgentState.REVIEW: (
            "Ready for review.",
            f"{label} stopped; this is not a verified build or test result.",
            "Review the result on your PC.",
        ),
    }
    summary, detail, suggested_action = values[state]
    return Explanation(
        summary,
        detail,
        evidence=("Local Agent lifecycle hook",),
        suggested_action=suggested_action,
    )


def _recipe(state: AgentState) -> VisualRecipe:
    if state is AgentState.IDLE:
        return _visual(
            _loop(_frame(_cells(), 0, 1_000, Transition.STEP)),
            _cells(),
            0.0,
            AttentionClass.AMBIENT,
        )
    if state is AgentState.THINKING:
        low = _cells(VIOLET_LOW)
        center = _cells_at({2: VIOLET, 3: VIOLET}, VIOLET_LOW)
        inner = _cells_at(
            {1: VIOLET, 2: VIOLET, 3: VIOLET, 4: VIOLET},
            VIOLET_LOW,
        )
        return _visual(
            _loop(
                _frame(center, 420, 120),
                _frame(inner, 420, 120),
                _frame(_cells(VIOLET), 420, 160),
                _frame(inner, 420, 120),
                _frame(center, 420, 120),
                _frame(low, 420, 220),
            ),
            center,
            0.50,
            AttentionClass.AMBIENT,
        )
    if state is AgentState.WORKING:
        return _runner(
            CYAN,
            CYAN_LOW,
            transition_ms=190,
            hold_ms=110,
            brightness=0.58,
        )
    if state is AgentState.EDITING:
        even = _cells_at({0: MAGENTA, 2: MAGENTA, 4: MAGENTA}, MAGENTA_LOW)
        odd = _cells_at({1: MAGENTA, 3: MAGENTA, 5: MAGENTA}, MAGENTA_LOW)
        return _visual(
            _loop(
                _frame(even, 120, 240),
                _frame(_cells(MAGENTA_LOW), 120, 100),
                _frame(odd, 120, 240),
                _frame(_cells(MAGENTA_LOW), 120, 100),
            ),
            even,
            0.56,
            AttentionClass.NORMAL,
        )
    if state is AgentState.TESTING:
        outer = _cells_at({0: AMBER, 5: AMBER}, AMBER_LOW)
        middle = _cells_at({1: AMBER, 4: AMBER}, AMBER_LOW)
        center = _cells_at({2: AMBER, 3: AMBER}, AMBER_LOW)
        return _visual(
            _loop(
                _frame(outer, 180, 130),
                _frame(middle, 180, 130),
                _frame(center, 180, 170),
                _frame(middle, 180, 130),
            ),
            outer,
            0.62,
            AttentionClass.NORMAL,
        )
    if state is AgentState.BUILDING:
        left = _cells_at({0: COBALT, 1: COBALT}, COBALT_LOW)
        center = _cells_at({2: COBALT, 3: COBALT}, COBALT_LOW)
        right = _cells_at({4: COBALT, 5: COBALT}, COBALT_LOW)
        return _visual(
            _loop(
                _frame(left, 240, 170),
                _frame(center, 240, 170),
                _frame(right, 240, 170),
                _frame(center, 240, 170),
            ),
            left,
            0.62,
            AttentionClass.NORMAL,
        )
    if state is AgentState.WAITING:
        outer_high = _cells_at({0: ORANGE, 5: ORANGE})
        outer_low = _cells_at({0: ORANGE_LOW, 5: ORANGE_LOW})
        return _visual(
            _loop(_frame(outer_low, 650, 420), _frame(outer_high, 650, 420)),
            outer_high,
            0.66,
            AttentionClass.ATTENTION,
        )
    if state is AgentState.INPUT_WAITING:
        return _recipe(AgentState.WAITING)
    if state is AgentState.SUCCESS:
        frames = (
            _frame(_cells_at({2: GREEN, 3: GREEN}, GREEN_LOW), 150, 100),
            _frame(
                _cells_at(
                    {1: GREEN, 2: GREEN, 3: GREEN, 4: GREEN},
                    GREEN_LOW,
                ),
                150,
                100,
            ),
            _frame(_cells(GREEN), 170, 220),
            _frame(_cells(GREEN_LOW), 260, 120),
            _frame(_cells(GREEN), 260, 600),
        )
        return _visual(
            Timeline(frames, Playback.ONCE_HOLD),
            _cells(GREEN),
            0.68,
            AttentionClass.NORMAL,
            reduced_playback=Playback.ONCE_HOLD,
        )
    if state is AgentState.FAILURE:
        outer = _cells_at({0: RED, 5: RED}, RED_LOW)
        standard = Timeline(
            (
                _frame(_cells(RED), 0, 180, Transition.STEP),
                _frame(_cells(), 0, 110, Transition.STEP),
                _frame(_cells(RED), 0, 180, Transition.STEP),
                _frame(_cells(), 0, 110, Transition.STEP),
                _frame(outer, 220, 600),
            ),
            Playback.ONCE_HOLD,
        )
        return _visual(
            standard,
            outer,
            0.72,
            AttentionClass.ATTENTION,
            reduced_playback=Playback.ONCE_HOLD,
        )

    center = _cells_at({2: LAVENDER, 3: LAVENDER})
    middle = _cells_at({1: LAVENDER, 4: LAVENDER})
    bookends = _cells_at({0: LAVENDER, 5: LAVENDER})
    return _visual(
        Timeline(
            (
                _frame(center, 220, 130),
                _frame(middle, 220, 130),
                _frame(bookends, 260, 700),
            ),
            Playback.ONCE_HOLD,
        ),
        bookends,
        0.50,
        AttentionClass.NORMAL,
        reduced_playback=Playback.ONCE_HOLD,
    )


def _runner(
    head: RGB,
    tail: RGB,
    *,
    transition_ms: int,
    hold_ms: int,
    brightness: float,
) -> VisualRecipe:
    frames = []
    for index in range(6):
        colors = {index: head}
        if index > 0:
            colors[index - 1] = tail
        frames.append(_frame(_cells_at(colors), transition_ms, hold_ms))
    representative = _cells_at({0: head, 1: tail})
    return _visual(_loop(*frames), representative, brightness, AttentionClass.NORMAL)


def _visual(
    standard: Timeline,
    reduced_cells: Cells6,
    brightness: float,
    attention: AttentionClass,
    *,
    reduced_playback: Playback = Playback.LOOP,
) -> VisualRecipe:
    reduced = Timeline(
        (_frame(reduced_cells, 0, 1_000, Transition.STEP),),
        reduced_playback,
    )
    return VisualRecipe(standard, reduced, brightness, attention)


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
    return cast(Cells6, (color,) * 6)


def _cells_at(values: dict[int, RGB], background: RGB = OFF) -> Cells6:
    return cast(Cells6, tuple(values.get(index, background) for index in range(6)))


__all__ = ["AgentPack"]
