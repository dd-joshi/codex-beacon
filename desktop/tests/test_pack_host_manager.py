from __future__ import annotations

import asyncio
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "desktop" / "src"))

import peri6.host.manager as manager_module  # noqa: E402
from peri6.contracts import (  # noqa: E402
    AttentionClass,
    Explanation,
    PackProposal,
    Playback,
    PublishStatus,
    RGB,
    RecipeFrame,
    Timeline,
    Transition,
    TrayActionInput,
    VisualRecipe,
)
from peri6.host import ActivePackManager, PackActivationError  # noqa: E402


def manifest(
    pack_id: str,
    *,
    settings_schema: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "manifest_version": 1,
        "id": pack_id,
        "display_name": pack_id.rsplit(".", 1)[-1].title(),
        "version": "0.1.0",
        "host_api": {"major": 1, "min_minor": 0},
        "entry_point": "tests.fake:create_pack",
        "maturity": "Prototype",
        "permissions": [],
        "supported_applications": [],
        "settings_schema": settings_schema
        or {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
        },
    }


def proposal(state: str, *, ttl_ms: int = 5000, red: int = 32) -> PackProposal:
    cells = tuple(RGB(red, 0, 0) for _ in range(6))
    frame = RecipeFrame(cells, 0, 1000, Transition.STEP)
    timeline = Timeline((frame,), Playback.LOOP)
    return PackProposal(
        state_key=state,
        source_observed_at=datetime.now(timezone.utc),
        valid_for_ms=ttl_ms,
        confidence=1.0,
        explanation=Explanation(state),
        recipe=VisualRecipe(
            standard=timeline,
            reduced_motion=timeline,
            requested_brightness=0.5,
            attention=AttentionClass.NORMAL,
        ),
    )


class FakeClock:
    def __init__(self) -> None:
        self.now_ns = 1_000_000_000
        self.base_utc = datetime(2026, 8, 20, tzinfo=timezone.utc)
        self.waiters: list[tuple[int, asyncio.Future[None]]] = []

    def monotonic_ns(self) -> int:
        return self.now_ns

    def utcnow(self) -> datetime:
        return self.base_utc + timedelta(
            microseconds=(self.now_ns - 1_000_000_000) // 1000
        )

    async def sleep(self, seconds: float) -> None:
        deadline = self.now_ns + round(seconds * 1_000_000_000)
        if deadline <= self.now_ns:
            return
        future = asyncio.get_running_loop().create_future()
        self.waiters.append((deadline, future))
        try:
            await future
        finally:
            self.waiters = [item for item in self.waiters if item[1] is not future]

    def advance_ms(self, milliseconds: int) -> None:
        self.now_ns += milliseconds * 1_000_000
        for deadline, future in tuple(self.waiters):
            if deadline <= self.now_ns and not future.done():
                future.set_result(None)


class RecordingPack:
    def __init__(self) -> None:
        self.context = None
        self.start_calls = 0
        self.stop_calls = 0
        self.inputs = []

    async def start(self, context) -> None:
        self.context = context
        self.start_calls += 1

    async def stop(self) -> None:
        self.stop_calls += 1

    async def handle_input(self, event) -> None:
        self.inputs.append(event)


class PublishingPack(RecordingPack):
    def __init__(self, state: str = "pack.ready", *, ttl_ms: int = 5000) -> None:
        super().__init__()
        self.state = state
        self.ttl_ms = ttl_ms
        self.receipt = None

    async def start(self, context) -> None:
        await super().start(context)
        self.receipt = await context.publish(proposal(self.state, ttl_ms=self.ttl_ms))


class PackHostManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.clock = FakeClock()
        self.dispatches = []
        self.events = []
        self.manager = ActivePackManager(
            self.dispatches.append,
            self.events.append,
            clock=self.clock,
            stop_timeout=0.05,
            start_timeout=0.05,
        )

    async def asyncTearDown(self) -> None:
        await self.manager.shutdown()

    async def test_invalid_settings_leave_current_activation_untouched(self) -> None:
        old = PublishingPack("old.ready")
        generation = await self.manager.activate(manifest("dev.peri6.old"), {}, lambda: old)
        dispatch_count = len(self.dispatches)
        factory_called = False

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "required": ["duration"],
            "properties": {"duration": {"type": "integer", "minimum": 1}},
        }

        def candidate_factory():
            nonlocal factory_called
            factory_called = True
            return RecordingPack()

        with self.assertRaisesRegex(ValueError, "invalid settings"):
            await self.manager.activate(
                manifest("dev.peri6.invalid", settings_schema=schema),
                {},
                candidate_factory,
            )

        self.assertFalse(factory_called)
        self.assertEqual(self.manager.generation, generation)
        self.assertEqual(self.manager.active_pack_id, "dev.peri6.old")
        self.assertEqual(old.stop_calls, 0)
        self.assertEqual(len(self.dispatches), dispatch_count)
        self.assertEqual(self.manager.current_output.proposal.state_key, "old.ready")

    async def test_start_buffers_only_newest_output_and_sequences_are_monotonic(self) -> None:
        scene_counts_during_start: list[int] = []

        class BufferingPack(RecordingPack):
            async def start(inner_self, context) -> None:
                await super().start(context)
                inner_self.first = await context.publish(proposal("buffer.first", red=10))
                scene_counts_during_start.append(
                    sum(dispatch.scene is not None for dispatch in self.dispatches)
                )
                inner_self.second = await context.publish(proposal("buffer.second", red=20))

        pack = BufferingPack()
        await self.manager.activate(manifest("dev.peri6.buffer"), {}, lambda: pack)

        self.assertEqual(scene_counts_during_start, [0])
        self.assertEqual(pack.first.output_sequence, 1)
        self.assertEqual(pack.second.output_sequence, 2)
        scenes = [dispatch for dispatch in self.dispatches if dispatch.scene is not None]
        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0].reason, "activated")
        self.assertEqual(self.manager.current_output.proposal.state_key, "buffer.second")

        third = await pack.context.publish(proposal("buffer.third", red=30))
        self.assertEqual((third.status, third.output_sequence), (PublishStatus.ACCEPTED, 3))
        self.assertEqual(self.manager.current_output.output_sequence, 3)

    async def test_old_context_is_stale_before_stop_begins(self) -> None:
        class StopPublisher(PublishingPack):
            async def stop(inner_self) -> None:
                await super().stop()
                inner_self.stop_receipt = await inner_self.context.publish(
                    proposal("old.late")
                )

        old = StopPublisher("old.ready")
        await self.manager.activate(manifest("dev.peri6.old"), {}, lambda: old)
        candidate = RecordingPack()
        await self.manager.activate(
            manifest("dev.peri6.candidate"), {}, lambda: candidate
        )

        self.assertEqual(
            old.stop_receipt.status, PublishStatus.REJECTED_STALE_ACTIVATION
        )
        self.assertEqual(self.manager.active_pack_id, "dev.peri6.candidate")
        self.assertFalse(
            any(
                event.output is not None
                and event.output.proposal.state_key == "old.late"
                for event in self.events
            )
        )

    async def test_generation_is_rechecked_after_compilation(self) -> None:
        pack = RecordingPack()
        await self.manager.activate(manifest("dev.peri6.compile"), {}, lambda: pack)
        activation = self.manager._activation
        self.assertIsNotNone(activation)
        assert activation is not None
        original_token = activation.token
        original_compiler = manager_module.compile_proposal
        scene_count = sum(dispatch.scene is not None for dispatch in self.dispatches)

        def invalidate_during_compile(*args, **kwargs):
            scene = original_compiler(*args, **kwargs)
            activation.token = object()
            return scene

        with patch.object(manager_module, "compile_proposal", invalidate_during_compile):
            receipt = await pack.context.publish(proposal("compile.late"))

        activation.token = original_token
        self.assertEqual(receipt.status, PublishStatus.REJECTED_STALE_ACTIVATION)
        self.assertEqual(
            sum(dispatch.scene is not None for dispatch in self.dispatches), scene_count
        )

    async def test_start_failure_never_commits_buffered_output(self) -> None:
        class FailingPack(RecordingPack):
            async def start(inner_self, context) -> None:
                await super().start(context)
                inner_self.receipt = await context.publish(proposal("bad.start"))
                raise RuntimeError("start exploded")

        pack = FailingPack()
        with self.assertRaisesRegex(PackActivationError, "start exploded"):
            await self.manager.activate(manifest("dev.peri6.failing"), {}, lambda: pack)

        self.assertEqual(pack.receipt.status, PublishStatus.ACCEPTED)
        self.assertEqual(pack.stop_calls, 1)
        self.assertIsNone(self.manager.active_pack_id)
        self.assertIsNone(self.manager.current_output)
        self.assertFalse(any(dispatch.scene is not None for dispatch in self.dispatches))
        self.assertEqual(self.dispatches[-1].reason, "start_failed")

    async def test_start_timeout_invalidates_and_stops_candidate(self) -> None:
        class HungStartPack(RecordingPack):
            async def start(inner_self, context) -> None:
                await super().start(context)
                inner_self.started = asyncio.Event()
                inner_self.started.set()
                await asyncio.Event().wait()

        pack = HungStartPack()
        with self.assertRaisesRegex(PackActivationError, "start timed out"):
            await self.manager.activate(
                manifest("dev.peri6.hung-start"), {}, lambda: pack
            )

        self.assertTrue(pack.started.is_set())
        self.assertEqual(pack.stop_calls, 1)
        self.assertIsNone(self.manager.active_pack_id)
        self.assertIsNone(self.manager.current_output)
        self.assertEqual(self.dispatches[-1].reason, "start_failed")

    async def test_stop_timeout_leaves_neutral_and_does_not_start_candidate(self) -> None:
        class HungStopPack(PublishingPack):
            def __init__(inner_self) -> None:
                super().__init__("hung.ready")
                inner_self.stop_started = asyncio.Event()

            async def stop(inner_self) -> None:
                inner_self.stop_calls += 1
                inner_self.stop_started.set()
                await asyncio.Event().wait()

        old = HungStopPack()
        await self.manager.activate(manifest("dev.peri6.hung"), {}, lambda: old)
        candidate = RecordingPack()

        with self.assertRaisesRegex(PackActivationError, "stop timed out"):
            await self.manager.activate(
                manifest("dev.peri6.never-started"), {}, lambda: candidate
            )

        self.assertTrue(old.stop_started.is_set())
        self.assertEqual(candidate.start_calls, 0)
        self.assertIsNone(self.manager.active_pack_id)
        self.assertIsNone(self.manager.current_output)
        self.assertEqual(self.dispatches[-1].reason, "switching")

    async def test_tracked_jobs_cancel_and_stale_generation_input_is_dropped(self) -> None:
        class JobPack(RecordingPack):
            def __init__(inner_self) -> None:
                super().__init__()
                inner_self.job_cancelled = asyncio.Event()

            async def start(inner_self, context) -> None:
                await super().start(context)

                async def worker() -> None:
                    try:
                        await asyncio.Event().wait()
                    finally:
                        inner_self.job_cancelled.set()

                inner_self.job = context.spawn(worker(), name="test-pack-job")

        old = JobPack()
        old_generation = await self.manager.activate(
            manifest("dev.peri6.jobs"), {}, lambda: old
        )
        await asyncio.sleep(0)
        current = RecordingPack()
        current_generation = await self.manager.activate(
            manifest("dev.peri6.current"), {}, lambda: current
        )
        await asyncio.sleep(0)

        event = TrayActionInput(uuid4(), "focus.start", self.clock.monotonic_ns())
        await self.manager.dispatch_input(event, expected_generation=old_generation)
        self.assertEqual(current.inputs, [])
        await self.manager.dispatch_input(event, expected_generation=current_generation)

        self.assertTrue(old.job_cancelled.is_set())
        self.assertTrue(old.job.cancelled())
        self.assertEqual(current.inputs, [event])

    async def test_expiry_replay_and_shutdown_are_safe(self) -> None:
        pack = PublishingPack("short.ready", ttl_ms=250)
        generation = await self.manager.activate(
            manifest("dev.peri6.short"), {}, lambda: pack
        )
        await asyncio.sleep(0)

        self.assertTrue(await self.manager.replay_current())
        self.assertEqual(self.dispatches[-1].reason, "replay")
        self.clock.advance_ms(249)
        await asyncio.sleep(0)
        self.assertIsNotNone(self.manager.current_output)
        self.clock.advance_ms(1)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        self.assertIsNone(self.manager.current_output)
        self.assertEqual(self.dispatches[-1].reason, "proposal_expired")
        self.assertFalse(await self.manager.replay_current())

        await self.manager.shutdown()
        self.assertTrue(self.manager.stopping)
        self.assertGreater(self.manager.generation, generation)
        self.assertEqual(self.dispatches[-1].reason, "shutdown")
        receipt = await pack.context.publish(proposal("after.shutdown"))
        self.assertEqual(receipt.status, PublishStatus.REJECTED_HOST_STOPPING)

    async def test_factory_reuse_is_rejected_before_current_pack_is_touched(self) -> None:
        pack = RecordingPack()
        generation = await self.manager.activate(
            manifest("dev.peri6.fresh"), {}, lambda: pack
        )
        dispatch_count = len(self.dispatches)

        with self.assertRaisesRegex(PackActivationError, "fresh instance"):
            await self.manager.activate(
                manifest("dev.peri6.reused"), {}, lambda: pack
            )

        self.assertEqual(self.manager.generation, generation)
        self.assertEqual(self.manager.active_pack_id, "dev.peri6.fresh")
        self.assertEqual(pack.stop_calls, 0)
        self.assertEqual(len(self.dispatches), dispatch_count)

    async def test_concurrent_switches_serialize(self) -> None:
        class GatedPack(RecordingPack):
            def __init__(inner_self) -> None:
                super().__init__()
                inner_self.entered = asyncio.Event()
                inner_self.release = asyncio.Event()

            async def start(inner_self, context) -> None:
                await super().start(context)
                inner_self.entered.set()
                await inner_self.release.wait()

        first = GatedPack()
        second = RecordingPack()
        first_switch = asyncio.create_task(
            self.manager.activate(manifest("dev.peri6.first"), {}, lambda: first)
        )
        await first.entered.wait()
        second_switch = asyncio.create_task(
            self.manager.activate(manifest("dev.peri6.second"), {}, lambda: second)
        )
        await asyncio.sleep(0)
        self.assertFalse(second_switch.done())

        first.release.set()
        first_generation = await first_switch
        second_generation = await second_switch

        self.assertEqual((first_generation, second_generation), (1, 2))
        self.assertEqual(first.stop_calls, 1)
        self.assertEqual(second.start_calls, 1)
        self.assertEqual(self.manager.active_pack_id, "dev.peri6.second")
        activated = [event for event in self.events if event.kind == "activated"]
        self.assertEqual([event.generation for event in activated], [1, 2])


if __name__ == "__main__":
    unittest.main()