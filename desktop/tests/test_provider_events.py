"""Contract tests for the provider-neutral Agent event core."""

from __future__ import annotations

import time
import unittest
from datetime import datetime, timezone

from codex_beacon.packs.agent.events import AgentObservation
from codex_beacon.packs.agent.pack import AgentPack


def _v2(
    index: int,
    event: str,
    *,
    provider: str = "claude",
    session: str = "a" * 32,
    task: str = "thinking",
    outcome: str = "unknown",
) -> AgentObservation:
    payload = {
        "version": 2,
        "event_id": format(index, "x").rjust(32, "0"),
        "turn_key": ("1" + format(index, "x")).rjust(32, "0")[:32],
        "tool_key": None,
        "event": event,
        "task": task,
        "outcome": outcome,
        "occurred_monotonic_ns": index,
        "provider": provider,
        "session_key": session,
        "workspace_key": None,
    }
    return AgentObservation.from_json(payload)


class _Context:
    def __init__(self) -> None:
        self.proposals: list[object] = []
        self.settings: dict[str, object] = {"listen_port": 0, "bearer_token": "x" * 43}

    @property
    def clock(self) -> "_Clock":
        return _Clock()

    async def publish(self, proposal: object) -> None:
        self.proposals.append(proposal)

    def spawn(self, coroutine: object, name: str = "") -> None:  # noqa: ARG002
        coroutine.close()  # type: ignore[union-attr]


class _Clock:
    def monotonic_ns(self) -> int:
        return time.monotonic_ns()

    def utcnow(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    @staticmethod
    async def sleep(_seconds: float) -> None:
        return None


class ProviderNeutralEventTests(unittest.TestCase):
    def test_v1_payload_parses_exactly_as_before(self) -> None:
        payload = {
            "version": 1,
            "event_id": "a" * 32,
            "turn_key": "b" * 32,
            "tool_key": None,
            "event": "turn_started",
            "task": "thinking",
            "outcome": "unknown",
            "occurred_monotonic_ns": 5,
        }
        observation = AgentObservation.from_json(payload)
        self.assertEqual(observation.version, 1)
        self.assertEqual(observation.to_json(), payload)

    def test_v2_payload_round_trips_and_canonicalizes_aliases(self) -> None:
        observation = _v2(1, "tool_completed", task="testing", outcome="success")
        self.assertEqual(observation.event, "tool_finished")
        self.assertEqual(observation.version, 2)
        reparsed = AgentObservation.from_json(observation.to_json())
        self.assertEqual(reparsed, observation)

    def test_unknown_provider_is_rejected(self) -> None:
        payload = _v2(2, "turn_started").to_json()
        payload["provider"] = "gpt"
        with self.assertRaises(ValueError):
            AgentObservation.from_json(payload)

    def test_extra_fields_are_rejected_at_the_boundary(self) -> None:
        payload = _v2(3, "turn_started").to_json()
        payload["prompt"] = "should never appear"
        with self.assertRaises(ValueError):
            AgentObservation.from_json(payload)


if __name__ == "__main__":
    unittest.main()
