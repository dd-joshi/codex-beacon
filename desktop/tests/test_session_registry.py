"""Session-registry behavior: election, cancellation, input-wait, endings."""

from __future__ import annotations

import unittest

from codex_beacon.packs.agent.events import AgentObservation, AgentState
from codex_beacon.packs.agent.pack import AgentPack
from test_provider_events import _Context, _v2


class SessionRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def _pack_with(self, *observations):
        pack = AgentPack()
        context = _Context()
        await pack.start(context)  # type: ignore[arg-type]
        for observation in observations:
            await pack.observe(observation)
        return pack, context

    async def test_parallel_sessions_never_merge_and_approval_wins(self) -> None:
        pack, _ = await self._pack_with(
            _v2(1, "turn_started", provider="codex", session="1" * 32),
            _v2(2, "turn_started", provider="claude", session="2" * 32),
            _v2(3, "tool_started", provider="codex", session="1" * 32, task="working"),
        )
        self.assertEqual(pack.state, AgentState.WORKING)
        await pack.observe(
            _v2(4, "approval_waiting", provider="claude", session="2" * 32)
        )
        self.assertEqual(pack.state, AgentState.WAITING)
        await pack.stop()

    async def test_input_waiting_state_and_provider_label(self) -> None:
        pack, context = await self._pack_with(
            _v2(1, "turn_started", provider="claude"),
            _v2(2, "input_waiting", provider="claude"),
        )
        self.assertEqual(pack.state, AgentState.INPUT_WAITING)
        explanation = context.proposals[-1].explanation
        self.assertIn("Claude", explanation.summary)
        await pack.stop()

    async def test_turn_cancelled_leaves_thinking_promptly(self) -> None:
        pack, _ = await self._pack_with(
            _v2(1, "turn_started", provider="codex"),
            _v2(2, "turn_cancelled", provider="codex"),
        )
        self.assertEqual(pack.state, AgentState.IDLE)
        await pack.stop()

    async def test_session_ended_drops_only_that_session(self) -> None:
        pack, _ = await self._pack_with(
            _v2(1, "turn_started", provider="codex", session="1" * 32),
            _v2(2, "turn_started", provider="claude", session="2" * 32),
            _v2(3, "session_ended", provider="claude", session="2" * 32),
        )
        self.assertEqual(pack.state, AgentState.THINKING)
        await pack.observe(_v2(4, "session_ended", provider="codex", session="1" * 32))
        self.assertEqual(pack.state, AgentState.IDLE)
        await pack.stop()

    async def test_v1_stream_still_behaves_as_one_global_session(self) -> None:
        payload_base = {
            "version": 1,
            "turn_key": "b" * 32,
            "tool_key": None,
            "task": "testing",
            "outcome": "unknown",
            "occurred_monotonic_ns": 0,
        }
        events = []
        for index, (event, outcome) in enumerate(
            (
                ("turn_started", "unknown"),
                ("tool_started", "unknown"),
                ("tool_finished", "failure"),
            )
        ):
            payload = dict(payload_base)
            payload.update(
                {
                    "event_id": format(index + 1, "x").rjust(32, "0"),
                    "event": event,
                    "outcome": outcome,
                }
            )
            events.append(AgentObservation.from_json(payload))
        pack, _ = await self._pack_with(*events)
        self.assertEqual(pack.state, AgentState.FAILURE)
        await pack.stop()


if __name__ == "__main__":
    unittest.main()
