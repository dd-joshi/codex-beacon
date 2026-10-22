from __future__ import annotations

import json
import unittest

from codex_beacon.packs.agent import AgentOutcome, AgentTask
from codex_beacon.packs.agent.hook_sender import normalize_hook_payload


def payload(event: str, **extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "session_id": "session-secret-value",
        "turn_id": "turn-secret-value",
        "hook_event_name": event,
    }
    value.update(extra)
    return value


class AgentHookSenderTests(unittest.TestCase):
    def test_prompt_becomes_content_free_thinking_observation(self) -> None:
        source = payload("UserPromptSubmit", prompt="private customer prompt")
        observed = normalize_hook_payload(source)
        self.assertIsNotNone(observed)
        assert observed is not None
        self.assertEqual(observed.event, "turn_started")
        self.assertEqual(observed.task, AgentTask.THINKING)
        serialized = json.dumps(observed.to_json())
        self.assertNotIn("private", serialized)
        self.assertNotIn("session-secret", serialized)
        self.assertNotIn("turn-secret", serialized)

    def test_test_and_build_commands_are_classified_without_forwarding_them(self) -> None:
        testing = normalize_hook_payload(
            payload(
                "PreToolUse",
                tool_name="Bash",
                tool_use_id="tool-1",
                tool_input={"command": "python -m unittest discover -v"},
            )
        )
        building = normalize_hook_payload(
            payload(
                "PreToolUse",
                tool_name="Bash",
                tool_use_id="tool-2",
                tool_input={"command": "npm run build"},
            )
        )
        self.assertEqual(testing.task, AgentTask.TESTING)  # type: ignore[union-attr]
        self.assertEqual(building.task, AgentTask.BUILDING)  # type: ignore[union-attr]
        self.assertNotIn("command", testing.to_json())  # type: ignore[union-attr]

    def test_non_thinking_lifecycle_events_are_classified(self) -> None:
        working = normalize_hook_payload(
            payload(
                "PreToolUse",
                tool_name="Read",
                tool_use_id="tool-work",
                tool_input={},
            )
        )
        editing = normalize_hook_payload(
            payload(
                "PreToolUse",
                tool_name="apply_patch",
                tool_use_id="tool-edit",
                tool_input={},
            )
        )
        waiting = normalize_hook_payload(payload("PermissionRequest"))
        review = normalize_hook_payload(payload("Stop"))

        self.assertEqual(working.event, "tool_started")  # type: ignore[union-attr]
        self.assertEqual(working.task, AgentTask.WORKING)  # type: ignore[union-attr]
        self.assertEqual(editing.event, "tool_started")  # type: ignore[union-attr]
        self.assertEqual(editing.task, AgentTask.EDITING)  # type: ignore[union-attr]
        self.assertEqual(waiting.event, "approval_waiting")  # type: ignore[union-attr]
        self.assertEqual(review.event, "turn_stopped")  # type: ignore[union-attr]

    def test_only_verified_test_or_build_exit_status_becomes_outcome(self) -> None:
        success = normalize_hook_payload(
            payload(
                "PostToolUse",
                tool_name="Bash",
                tool_use_id="tool-1",
                tool_input={"command": "pytest -q"},
                tool_response="Exit code: 0\n12 passed",
            )
        )
        failure = normalize_hook_payload(
            payload(
                "PostToolUse",
                tool_name="Bash",
                tool_use_id="tool-2",
                tool_input={"command": "cargo build"},
                tool_response={"returncode": 2, "output": "private compiler text"},
            )
        )
        edit = normalize_hook_payload(
            payload(
                "PostToolUse",
                tool_name="apply_patch",
                tool_use_id="tool-3",
                tool_input={"command": "private patch"},
                tool_response="Exit code: 0",
            )
        )
        self.assertEqual(success.outcome, AgentOutcome.SUCCESS)  # type: ignore[union-attr]
        self.assertEqual(failure.outcome, AgentOutcome.FAILURE)  # type: ignore[union-attr]
        self.assertEqual(edit.outcome, AgentOutcome.UNKNOWN)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()