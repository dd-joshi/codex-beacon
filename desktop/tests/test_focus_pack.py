from __future__ import annotations

import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from importlib.resources import files
from types import MappingProxyType
from uuid import UUID, uuid4

from peri6.contracts import (
    ButtonGesture,
    ButtonInput,
    PackProposal,
    PublishReceipt,
    PublishStatus,
    TrayActionInput,
    validate_manifest,
    validate_proposal,
)
from peri6.packs.focus import (
    ACTION_CANCEL,
    ACTION_RESET,
    ACTION_START_PAUSE,
    FocusPack,
    FocusState,
    completed_stages,
    create_pack,
)
from peri6.protocol import compile_proposal


NANOSECONDS_PER_SECOND = 1_000_000_000


class _ManualClock:
    def __init__(self) -> None:
        self.now_ns = 0
        self.epoch = datetime(2026, 8, 20, tzinfo=timezone.utc)
        self.sleepers: list[tuple[int, asyncio.Future[None]]] = []

    def monotonic_ns(self) -> int:
        return self.now_ns

    def utcnow(self) -> datetime:
        return self.epoch + timedelta(seconds=self.now_ns / NANOSECONDS_PER_SECOND)

    async def sleep(self, seconds: float) -> None:
        future = asyncio.get_running_loop().create_future()
        deadline = self.now_ns + round(seconds * NANOSECONDS_PER_SECOND)
        self.sleepers.append((deadline, future))
        await future

    def advance(self, seconds: float) -> None:
        self.now_ns += round(seconds * NANOSECONDS_PER_SECOND)
        pending: list[tuple[int, asyncio.Future[None]]] = []
        for deadline, future in self.sleepers:
            if deadline <= self.now_ns:
                if not future.done():
                    future.set_result(None)
            else:
                pending.append((deadline, future))
        self.sleepers = pending


class _Context:
    def __init__(self, settings: dict[str, object] | None = None) -> None:
        self._settings = MappingProxyType(dict(settings or {}))
        self._clock = _ManualClock()
        self.proposals: list[PackProposal] = []
        self.tasks: list[asyncio.Task[None]] = []

    @property
    def pack_id(self) -> str:
        return "com.peri6.focus"

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
    def clock(self) -> _ManualClock:
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


def _tray(context: _Context, action: str) -> TrayActionInput:
    return TrayActionInput(uuid4(), action, context.clock.monotonic_ns())


def _button(context: _Context, gesture: ButtonGesture) -> ButtonInput:
    return ButtonInput(uuid4(), gesture, context.clock.monotonic_ns())


async def _drain() -> None:
    for _ in range(4):
        await asyncio.sleep(0)


class FocusPackContractTests(unittest.IsolatedAsyncioTestCase):
    def test_factory_and_packaged_manifest(self) -> None:
        first = create_pack()
        second = create_pack()
        self.assertIsInstance(first, FocusPack)
        self.assertIsInstance(second, FocusPack)
        self.assertIsNot(first, second)

        manifest_text = files("peri6.packs.focus").joinpath("manifest.json").read_text(
            encoding="utf-8"
        )
        manifest = validate_manifest(json.loads(manifest_text))
        self.assertEqual(manifest.pack_id, "com.peri6.focus")
        self.assertEqual(manifest.entry_point, "peri6.packs.focus:create_pack")

    def test_six_stage_boundaries_are_exact(self) -> None:
        duration = 60 * NANOSECONDS_PER_SECOND
        self.assertEqual(completed_stages(0, duration), 0)
        for stage in range(1, 6):
            boundary = duration * stage // 6
            self.assertEqual(completed_stages(boundary - 1, duration), stage - 1)
            self.assertEqual(completed_stages(boundary, duration), stage)
        self.assertEqual(completed_stages(duration - 1, duration), 5)
        self.assertEqual(completed_stages(duration, duration), 6)
        self.assertEqual(completed_stages(duration + 1, duration), 6)

    async def test_start_publishes_idle_and_honors_duration_setting(self) -> None:
        context = _Context({"duration_minutes": 30})
        pack = create_pack()
        await pack.start(context)
        self.assertEqual(pack.state, FocusState.IDLE)
        self.assertEqual(pack.duration_minutes, 30)
        self.assertEqual(context.proposals[-1].state_key, "focus.idle")
        self.assertEqual(context.proposals[-1].progress, 0.0)
        self.assertEqual(
            {
                binding.gesture: binding.action_id
                for binding in context.proposals[-1].button_bindings
            },
            {
                ButtonGesture.TAP: ACTION_START_PAUSE,
                ButtonGesture.PRESS: ACTION_RESET,
                ButtonGesture.LONG_PRESS: ACTION_CANCEL,
            },
        )
        self.assertNotEqual(
            context.proposals[-1].recipe.standard,
            context.proposals[-1].recipe.reduced_motion,
        )
        await pack.stop()

    async def test_invalid_settings_publish_unknown(self) -> None:
        for settings in (
            {"duration_minutes": True},
            {"duration_minutes": 0},
            {"duration_minutes": 241},
            {"extra": "field"},
        ):
            with self.subTest(settings=settings):
                context = _Context(settings)
                pack = create_pack()
                await pack.start(context)
                self.assertEqual(pack.state, FocusState.UNKNOWN)
                self.assertEqual(context.proposals[-1].state_key, "focus.unknown")
                self.assertIsNone(context.proposals[-1].progress)
                await pack.stop()

    async def test_actions_and_button_gestures_drive_all_timer_states(self) -> None:
        context = _Context({"duration_minutes": 1})
        pack = create_pack()
        await pack.start(context)

        await pack.handle_input(_tray(context, ACTION_START_PAUSE))
        self.assertEqual(pack.state, FocusState.WORKING)
        self.assertEqual(context.proposals[-1].state_key, "focus.working")
        self.assertEqual(context.proposals[-1].valid_for_ms, 2_000)

        await _drain()
        context.clock.advance(10)
        await _drain()
        proposal = context.proposals[-1]
        self.assertEqual(proposal.state_key, "focus.working")
        self.assertAlmostEqual(proposal.progress or 0.0, 1 / 6)
        first_frame = proposal.recipe.reduced_motion.frames[0]
        self.assertNotEqual(first_frame.cells[0], first_frame.cells[2])

        await pack.handle_input(_button(context, ButtonGesture.TAP))
        self.assertEqual(pack.state, FocusState.PAUSED)
        paused_count = len(context.proposals)
        context.clock.advance(10)
        await _drain()
        self.assertEqual(len(context.proposals), paused_count)

        await pack.handle_input(_button(context, ButtonGesture.TAP))
        self.assertEqual(pack.state, FocusState.WORKING)
        await pack.handle_input(_button(context, ButtonGesture.PRESS))
        self.assertEqual(pack.state, FocusState.IDLE)
        self.assertEqual(context.proposals[-1].progress, 0.0)

        await pack.handle_input(_tray(context, ACTION_START_PAUSE))
        await pack.handle_input(_button(context, ButtonGesture.LONG_PRESS))
        self.assertEqual(pack.state, FocusState.CANCELLED)
        self.assertEqual(context.proposals[-1].state_key, "focus.cancelled")
        await pack.stop()

    async def test_deadline_completion_is_exact_and_recipes_compile(self) -> None:
        context = _Context({"duration_minutes": 1})
        pack = create_pack()
        await pack.start(context)
        await pack.handle_input(_tray(context, ACTION_START_PAUSE))

        context.clock.advance(60)
        await _drain()
        self.assertEqual(pack.state, FocusState.COMPLETED)
        proposal = context.proposals[-1]
        self.assertEqual(proposal.state_key, "focus.completed")
        self.assertEqual(proposal.progress, 1.0)
        standard = compile_proposal(
            proposal,
            scene_id="ABEiM0RVZneImaq7zN3u_w",
            reduced_motion=False,
        )
        reduced = compile_proposal(
            proposal,
            scene_id="zBEiM0RVZneImaq7zN3u_w",
            reduced_motion=True,
        )
        self.assertNotEqual(standard.keyframes, reduced.keyframes)
        await pack.stop()

    async def test_working_output_refreshes_well_inside_its_ttl(self) -> None:
        context = _Context({"duration_minutes": 1})
        pack = create_pack()
        await pack.start(context)
        await pack.handle_input(_tray(context, ACTION_START_PAUSE))
        await _drain()
        initial_count = len(context.proposals)

        context.clock.advance(0.5)
        await _drain()
        self.assertEqual(len(context.proposals), initial_count)

        context.clock.advance(0.5)
        await _drain()
        self.assertEqual(len(context.proposals), initial_count + 1)
        self.assertEqual(context.proposals[-1].valid_for_ms, 2_000)
        self.assertEqual(context.proposals[-1].state_key, "focus.working")
        await pack.stop()

    async def test_cancel_and_stop_prevent_later_publication(self) -> None:
        context = _Context({"duration_minutes": 1})
        pack = create_pack()
        await pack.start(context)
        await pack.handle_input(_tray(context, ACTION_START_PAUSE))
        await pack.handle_input(_tray(context, ACTION_CANCEL))
        count_after_cancel = len(context.proposals)
        context.clock.advance(120)
        await _drain()
        self.assertEqual(len(context.proposals), count_after_cancel)

        await pack.handle_input(_tray(context, ACTION_START_PAUSE))
        await pack.stop()
        count_after_stop = len(context.proposals)
        context.clock.advance(120)
        await _drain()
        self.assertEqual(len(context.proposals), count_after_stop)
        self.assertTrue(all(task.done() for task in context.tasks))

    async def test_unknown_tray_action_has_honest_unknown_state(self) -> None:
        context = _Context()
        pack = create_pack()
        await pack.start(context)
        self.assertEqual(pack.duration_minutes, 25)
        await pack.handle_input(_tray(context, "focus.unsupported"))
        self.assertEqual(pack.state, FocusState.UNKNOWN)
        self.assertEqual(context.proposals[-1].confidence, 0.0)
        await pack.handle_input(_tray(context, ACTION_RESET))
        self.assertEqual(pack.state, FocusState.IDLE)
        await pack.stop()


if __name__ == "__main__":
    unittest.main()