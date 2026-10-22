from __future__ import annotations

import queue
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from peri6.companion import CompanionEvent, CompanionRuntime
from peri6.host import HostEvent
from peri6.packs.focus import ACTION_CANCEL, ACTION_START_PAUSE
from peri6.packs.registry import AGENT_PACK_ID, FOCUS_PACK_ID


class CompanionRuntimeTests(unittest.TestCase):
    def test_focus_vertical_slice_runs_without_a_connected_device(self) -> None:
        events: queue.Queue[CompanionEvent] = queue.Queue()
        runtime = CompanionRuntime(events.put, duration_minutes=1)
        try:
            activated = self._wait_for_host(events, "activated")
            self.assertIsNotNone(activated.output)
            assert activated.output is not None
            self.assertEqual(activated.output.proposal.state_key, "focus.idle")

            runtime.send_action(ACTION_START_PAUSE)
            working = self._wait_for_state(events, "focus.working")
            self.assertLess(working.output.proposal.progress, 0.01)  # type: ignore[union-attr]

            runtime.send_action(ACTION_CANCEL)
            cancelled = self._wait_for_state(events, "focus.cancelled")
            self.assertEqual(cancelled.output.proposal.state_key, "focus.cancelled")  # type: ignore[union-attr]
        finally:
            runtime.shutdown()

    def test_companion_module_help_does_not_open_the_gui(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "peri6.companion.app", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Peri6 first-party desktop companion", completed.stdout)

    def test_runtime_switches_to_agent_and_accepts_a_loopback_event(self) -> None:
        events: queue.Queue[CompanionEvent] = queue.Queue()
        with tempfile.TemporaryDirectory() as directory:
            port = self._free_port()
            token = "r" * 43
            config_path = Path(directory) / "agent-hook.json"
            config_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "endpoint": f"http://127.0.0.1:{port}/v1/events",
                        "bearer_token": token,
                    }
                ),
                encoding="utf-8",
            )
            runtime = CompanionRuntime(events.put, agent_config_path=config_path)
            try:
                self._wait_for_state(events, "focus.idle")
                runtime.activate_pack(AGENT_PACK_ID)
                self._wait_for_state(events, "agent.idle")

                repository = Path(__file__).resolve().parents[2]
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(repository / ".codex" / "hooks" / "peri6_agent_hook.py"),
                    ],
                    input=json.dumps(
                        {
                            "session_id": "session-local",
                            "turn_id": "turn-local",
                            "hook_event_name": "PreToolUse",
                            "tool_name": "Bash",
                            "tool_use_id": "tool-local",
                            "tool_input": {"command": "python -m unittest discover"},
                        }
                    ),
                    text=True,
                    capture_output=True,
                    timeout=3,
                    env=os.environ | {"PERI6_AGENT_CONFIG": str(config_path)},
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stdout, "")
                self._wait_for_state(events, "agent.testing")

                runtime.activate_pack(FOCUS_PACK_ID)
                self._wait_for_state(events, "focus.idle")
            finally:
                runtime.shutdown()

    def test_runtime_can_start_directly_in_agent_mode(self) -> None:
        events: queue.Queue[CompanionEvent] = queue.Queue()
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "agent-hook.json"
            runtime = CompanionRuntime(
                events.put,
                agent_config_path=config_path,
                initial_pack_id=AGENT_PACK_ID,
            )
            try:
                activated = self._wait_for_state(events, "agent.idle")
                self.assertEqual(
                    activated.output.proposal.state_key,  # type: ignore[union-attr]
                    "agent.idle",
                )
                self.assertTrue(config_path.is_file())
            finally:
                runtime.shutdown()

    @staticmethod
    def _free_port() -> int:
        with socket.socket() as connection:
            connection.bind(("127.0.0.1", 0))
            return int(connection.getsockname()[1])

    def _wait_for_host(
        self, events: queue.Queue[CompanionEvent], kind: str, timeout: float = 3
    ) -> HostEvent:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                event = events.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if event.kind == "host" and isinstance(event.payload, HostEvent):
                if event.payload.kind == kind:
                    return event.payload
        self.fail(f"host event {kind!r} was not emitted")

    def _wait_for_state(
        self, events: queue.Queue[CompanionEvent], state_key: str, timeout: float = 3
    ) -> HostEvent:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                event = events.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if event.kind != "host" or not isinstance(event.payload, HostEvent):
                continue
            output = event.payload.output
            if output is not None and output.proposal.state_key == state_key:
                return event.payload
        self.fail(f"Pack state {state_key!r} was not emitted")


if __name__ == "__main__":
    unittest.main()