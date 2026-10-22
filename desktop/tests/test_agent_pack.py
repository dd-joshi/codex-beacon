from __future__ import annotations

import asyncio
import json
import socket
import time
import unittest
from datetime import datetime, timezone
from importlib.resources import files
from types import MappingProxyType
from uuid import UUID

from peri6.contracts import (
    PackProposal,
    Playback,
    PublishReceipt,
    PublishStatus,
    validate_manifest,
    validate_proposal,
)
from peri6.companion.presentation import sample_timeline_cells
from peri6.packs.agent import (
    AgentObservation,
    AgentOutcome,
    AgentPack,
    AgentState,
    AgentTask,
    create_pack,
)
from peri6.packs.agent.pack import STALE_ACTIVE_NS, _stale_after_ns
from peri6.protocol import compile_proposal


class _Clock:
    def monotonic_ns(self) -> int:
        return time.monotonic_ns()

    def utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class _Context:
    def __init__(self, port: int) -> None:
        self._settings = MappingProxyType(
            {"listen_port": port, "bearer_token": "t" * 43}
        )
        self._clock = _Clock()
        self.proposals: list[PackProposal] = []
        self.tasks: list[asyncio.Task[None]] = []

    @property
    def pack_id(self) -> str:
        return "com.peri6.agent"

    @property
    def activation_id(self) -> UUID:
        return UUID("00112233-4455-6677-8899-aabbccddeeff")

    @property
    def generation(self) -> int:
        return 1

    @property
    def settings(self):
        return self._settings

    @property
    def clock(self) -> _Clock:
        return self._clock

    async def publish(self, proposal: PackProposal) -> PublishReceipt:
        validate_proposal(proposal)
        compile_proposal(
            proposal,
            scene_id="ABEiM0RVZneImaq7zN3u_w",
            reduced_motion=False,
        )
        compile_proposal(
            proposal,
            scene_id="zBEiM0RVZneImaq7zN3u_w",
            reduced_motion=True,
        )
        self.proposals.append(proposal)
        return PublishReceipt(PublishStatus.ACCEPTED, len(self.proposals))

    def spawn(self, job, *, name: str) -> asyncio.Task[None]:
        task = asyncio.create_task(job, name=name)
        self.tasks.append(task)
        return task

    async def cancel_tasks(self) -> None:
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)


def _free_port() -> int:
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        return int(connection.getsockname()[1])


def _observation(
    index: int,
    event: str,
    task: AgentTask,
    outcome: AgentOutcome = AgentOutcome.UNKNOWN,
    *,
    tool_key: str | None = None,
) -> AgentObservation:
    return AgentObservation(
        f"{index:032x}",
        "f" * 32,
        tool_key,
        event,
        task,
        outcome,
        index,
    )


class AgentPackContractTests(unittest.IsolatedAsyncioTestCase):
    def test_unterminated_interactive_state_has_bounded_stale_lease(self) -> None:
        self.assertEqual(STALE_ACTIVE_NS, 2 * 60 * 1_000_000_000)
        for state in (
            AgentState.THINKING,
            AgentState.WORKING,
            AgentState.EDITING,
        ):
            self.assertEqual(_stale_after_ns(state), STALE_ACTIVE_NS)

    def test_factory_and_manifest(self) -> None:
        first = create_pack()
        second = create_pack()
        self.assertIsInstance(first, AgentPack)
        self.assertIsNot(first, second)
        manifest = validate_manifest(
            json.loads(
                files("peri6.packs.agent")
                .joinpath("manifest.json")
                .read_text(encoding="utf-8")
            )
        )
        self.assertEqual(manifest.pack_id, "com.peri6.agent")
        self.assertEqual(manifest.permissions, ("application.loopback.listen",))

    async def test_state_flow_distinguishes_verified_success_from_stop(self) -> None:
        context = _Context(_free_port())
        pack = create_pack()
        await pack.start(context)
        try:
            self.assertEqual(pack.state, AgentState.IDLE)
            self.assertEqual(context.proposals[-1].state_key, "agent.idle")

            await pack.observe(_observation(1, "turn_started", AgentTask.THINKING))
            self.assertEqual(pack.state, AgentState.THINKING)
            await pack.observe(_observation(2, "tool_started", AgentTask.TESTING))
            self.assertEqual(pack.state, AgentState.TESTING)
            self.assertIsNone(context.proposals[-1].progress)

            await pack.observe(
                _observation(
                    3,
                    "tool_finished",
                    AgentTask.TESTING,
                    AgentOutcome.SUCCESS,
                )
            )
            self.assertEqual(pack.state, AgentState.SUCCESS)
            self.assertEqual(context.proposals[-1].state_key, "agent.success")

            await pack.observe(_observation(4, "turn_stopped", AgentTask.THINKING))
            self.assertEqual(pack.state, AgentState.REVIEW)
            self.assertEqual(context.proposals[-1].state_key, "agent.review")
            self.assertIn("not a verified", context.proposals[-1].explanation.detail)
        finally:
            await pack.stop()
            await context.cancel_tasks()

    async def test_interactive_states_include_phone_safe_actions(self) -> None:
        context = _Context(_free_port())
        pack = create_pack()
        await pack.start(context)
        try:
            cases = (
                (
                    _observation(40, "approval_waiting", AgentTask.WORKING),
                    "Approve or reply on your PC.",
                ),
                (
                    _observation(41, "input_waiting", AgentTask.THINKING),
                    "Reply on your PC.",
                ),
                (
                    _observation(42, "turn_stopped", AgentTask.THINKING),
                    "Review the result on your PC.",
                ),
            )
            for observation, expected_action in cases:
                with self.subTest(event=observation.event):
                    await pack.observe(observation)
                    self.assertEqual(
                        context.proposals[-1].explanation.suggested_action,
                        expected_action,
                    )
        finally:
            await pack.stop()
            await context.cancel_tasks()

    async def test_all_non_thinking_states_publish_the_expected_semantics(self) -> None:
        context = _Context(_free_port())
        pack = create_pack()
        await pack.start(context)
        try:
            self.assertEqual(pack.state, AgentState.IDLE)
            recipes = {}
            proposals = {}
            valid_for = {}
            cases = (
                (_observation(20, "tool_started", AgentTask.WORKING), AgentState.WORKING),
                (_observation(21, "tool_started", AgentTask.EDITING), AgentState.EDITING),
                (_observation(22, "tool_started", AgentTask.TESTING), AgentState.TESTING),
                (_observation(23, "tool_started", AgentTask.BUILDING), AgentState.BUILDING),
                (_observation(24, "approval_waiting", AgentTask.WORKING), AgentState.WAITING),
                (
                    _observation(
                        25,
                        "tool_finished",
                        AgentTask.TESTING,
                        AgentOutcome.SUCCESS,
                    ),
                    AgentState.SUCCESS,
                ),
                (
                    _observation(
                        26,
                        "tool_finished",
                        AgentTask.BUILDING,
                        AgentOutcome.FAILURE,
                    ),
                    AgentState.FAILURE,
                ),
                (_observation(27, "turn_stopped", AgentTask.THINKING), AgentState.REVIEW),
            )
            for observation, expected in cases:
                with self.subTest(state=expected.value):
                    await pack.observe(observation)
                    self.assertEqual(pack.state, expected)
                    proposal = context.proposals[-1]
                    self.assertEqual(proposal.state_key, f"agent.{expected.value}")
                    self.assertIsNone(proposal.progress)
                    recipes[expected] = proposal.recipe
                    proposals[expected] = proposal
                    valid_for[expected] = proposal.valid_for_ms

            visual_states = (
                AgentState.WORKING,
                AgentState.EDITING,
                AgentState.TESTING,
                AgentState.BUILDING,
                AgentState.WAITING,
                AgentState.SUCCESS,
                AgentState.FAILURE,
                AgentState.REVIEW,
            )
            reduced_palettes = [
                tuple(
                    (cell.r, cell.g, cell.b)
                    for cell in recipes[state].reduced_motion.frames[-1].cells
                )
                for state in visual_states
            ]
            self.assertEqual(len(set(reduced_palettes)), len(visual_states))
            self.assertNotEqual(
                recipes[AgentState.TESTING].standard,
                recipes[AgentState.BUILDING].standard,
            )
            for terminal in (
                AgentState.SUCCESS,
                AgentState.FAILURE,
                AgentState.REVIEW,
            ):
                self.assertEqual(
                    recipes[terminal].standard.playback,
                    Playback.ONCE_HOLD,
                )
                self.assertTrue(
                    any(
                        (cell.r, cell.g, cell.b) != (0, 0, 0)
                        for cell in recipes[terminal].standard.frames[-1].cells
                    )
                )
            self.assertEqual(valid_for[AgentState.SUCCESS], 10_000)
            self.assertEqual(valid_for[AgentState.FAILURE], 10_000)
            self.assertEqual(valid_for[AgentState.REVIEW], 60_000)

            review = recipes[AgentState.REVIEW]
            for timeline in (review.standard, review.reduced_motion):
                lit = {
                    index
                    for index, cell in enumerate(timeline.frames[-1].cells)
                    if (cell.r, cell.g, cell.b) != (0, 0, 0)
                }
                self.assertEqual(lit, {0, 5})

            success_proposal = proposals[AgentState.SUCCESS]
            success = success_proposal.recipe.standard
            hardware_scene = compile_proposal(
                success_proposal,
                scene_id="ABEiM0RVZneImaq7zN3u_w",
                reduced_motion=False,
            )
            self.assertEqual(hardware_scene.playback_mode, "once")
            self.assertEqual(hardware_scene.on_complete, "hold")
            self.assertEqual(len(hardware_scene.keyframes), len(success.frames))
            elapsed_ms = 0
            for desktop_frame, hardware_frame in zip(
                success.frames,
                hardware_scene.keyframes,
                strict=True,
            ):
                self.assertEqual(
                    tuple((cell.r, cell.g, cell.b) for cell in desktop_frame.cells),
                    tuple((cell.r, cell.g, cell.b) for cell in hardware_frame.cells),
                )
                elapsed_ms += desktop_frame.transition_ms
                self.assertEqual(
                    sample_timeline_cells(success, elapsed_ms),
                    desktop_frame.cells,
                )
                elapsed_ms += desktop_frame.hold_ms
            self.assertEqual(
                sample_timeline_cells(success, elapsed_ms + 5_000),
                success.frames[-1].cells,
            )
        finally:
            await pack.stop()
            await context.cancel_tasks()

    async def test_duplicate_and_late_tool_start_do_not_rewind_state(self) -> None:
        context = _Context(_free_port())
        pack = create_pack()
        await pack.start(context)
        try:
            finished = _observation(
                10,
                "tool_finished",
                AgentTask.TESTING,
                AgentOutcome.SUCCESS,
                tool_key="a" * 32,
            )
            await pack.observe(finished)
            count = len(context.proposals)
            await pack.observe(finished)
            await pack.observe(
                _observation(
                    9,
                    "tool_started",
                    AgentTask.TESTING,
                    tool_key="a" * 32,
                )
            )
            self.assertEqual(pack.state, AgentState.SUCCESS)
            self.assertEqual(len(context.proposals), count)

            await pack.observe(_observation(11, "turn_stopped", AgentTask.THINKING))
            count = len(context.proposals)
            await pack.observe(
                _observation(
                    12,
                    "tool_finished",
                    AgentTask.TESTING,
                    AgentOutcome.FAILURE,
                    tool_key="b" * 32,
                )
            )
            self.assertEqual(pack.state, AgentState.REVIEW)
            self.assertEqual(len(context.proposals), count)
        finally:
            await pack.stop()
            await context.cancel_tasks()


if __name__ == "__main__":
    unittest.main()
