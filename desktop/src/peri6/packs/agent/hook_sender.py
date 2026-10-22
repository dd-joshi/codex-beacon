"""Non-blocking Codex hook adapter for the local Agent pack.

The raw hook payload is classified in this short-lived process and discarded.
Only the bounded semantic AgentObservation is sent to Peri6.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from urllib.error import URLError
from urllib.request import Request, urlopen

from .config import default_agent_config_path, load_agent_config
from .events import AgentObservation, AgentOutcome, AgentTask


TEST_PATTERN = re.compile(
    r"(?:^|[;&|\s])(?:pytest|py\.test|ctest|go\s+test|cargo\s+test|dotnet\s+test|"
    r"npm\s+(?:run\s+)?test|pnpm\s+(?:run\s+)?test|yarn\s+test|python(?:\.exe)?\s+-m\s+unittest)(?:\s|$)",
    re.IGNORECASE,
)
BUILD_PATTERN = re.compile(
    r"(?:^|[;&|\s])(?:cmake\s+--build|cargo\s+build|dotnet\s+build|"
    r"npm\s+run\s+build|pnpm\s+(?:run\s+)?build|yarn\s+build|"
    r"python(?:\.exe)?\s+-m\s+build|pio\s+run|platformio\s+run|msbuild|ninja|make)(?:\s|$)",
    re.IGNORECASE,
)
EXIT_PATTERN = re.compile(r"(?:exit\s+code|returncode)\s*[:=]\s*(-?\d+)", re.IGNORECASE)
DIAGNOSTIC_LOG_MAX_BYTES = 64 * 1024


def normalize_hook_payload(payload: Mapping[str, object]) -> AgentObservation | None:
    hook = payload.get("hook_event_name")
    if not isinstance(hook, str):
        return None
    mapping = {
        "UserPromptSubmit": "turn_started",
        "PreToolUse": "tool_started",
        "PermissionRequest": "approval_waiting",
        "Notification": "approval_waiting",
        "PostToolUse": "tool_finished",
        "Stop": "turn_stopped",
    }
    event = mapping.get(hook)
    if event is None:
        return None
    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        return None
    # Codex provides turn_id; Claude payloads may not.  A stable per-session
    # digest keeps ordering deterministic for providers without turn ids.
    turn_id = payload.get("turn_id")
    if not isinstance(turn_id, str):
        turn_id = ""
    task = _classify_task(payload)
    outcome = _classify_outcome(payload, task) if hook == "PostToolUse" else AgentOutcome.UNKNOWN
    turn_key = _digest(session_id, turn_id)
    tool_id = payload.get("tool_use_id")
    event_id = _digest(session_id, turn_id, hook, tool_id if isinstance(tool_id, str) else "")
    tool_key = (
        _digest(session_id, turn_id, tool_id) if isinstance(tool_id, str) else None
    )
    return AgentObservation(
        event_id=event_id,
        turn_key=turn_key,
        tool_key=tool_key,
        event=event,
        task=task,
        outcome=outcome,
        occurred_monotonic_ns=time.monotonic_ns(),
    )


def _classify_task(payload: Mapping[str, object]) -> AgentTask:
    hook = payload.get("hook_event_name")
    if hook in {"UserPromptSubmit", "Stop"}:
        return AgentTask.THINKING
    tool_name = payload.get("tool_name")
    if isinstance(tool_name, str) and tool_name.lower() == "apply_patch":
        return AgentTask.EDITING
    command = _command(payload.get("tool_input"))
    if command and TEST_PATTERN.search(command):
        return AgentTask.TESTING
    if command and BUILD_PATTERN.search(command):
        return AgentTask.BUILDING
    return AgentTask.WORKING


def _classify_outcome(payload: Mapping[str, object], task: AgentTask) -> AgentOutcome:
    if task not in {AgentTask.TESTING, AgentTask.BUILDING}:
        return AgentOutcome.UNKNOWN
    response = payload.get("tool_response")
    code = _find_exit_code(response)
    if code is not None:
        return AgentOutcome.SUCCESS if code == 0 else AgentOutcome.FAILURE
    if isinstance(response, Mapping) and response.get("isError") is True:
        return AgentOutcome.FAILURE
    return AgentOutcome.UNKNOWN


def _find_exit_code(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return None
    if isinstance(value, str):
        match = EXIT_PATTERN.search(value)
        return int(match.group(1)) if match else None
    if isinstance(value, Mapping):
        for key in ("exit_code", "exitCode", "returncode", "return_code"):
            code = value.get(key)
            if isinstance(code, int) and not isinstance(code, bool):
                return code
        for child in value.values():
            found = _find_exit_code(child)
            if found is not None:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_exit_code(child)
            if found is not None:
                return found
    return None


def _command(value: object) -> str:
    if isinstance(value, Mapping):
        command = value.get("command")
        return command if isinstance(command, str) else ""
    return ""


def _digest(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8", errors="replace"))
        digest.update(b"\0")
    return digest.hexdigest()[:32]


def send_observation(observation: AgentObservation) -> bool:
    try:
        config = load_agent_config(default_agent_config_path())
        body = json.dumps(observation.to_json(), separators=(",", ":")).encode("utf-8")
        request = Request(
            config.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {config.bearer_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=0.35) as response:
            return response.status == 202
    except (OSError, ValueError, URLError):
        return False


def _record_delivery(hook_name: str, delivered: bool) -> None:
    """Keep a bounded, content-free trace for local hook troubleshooting."""
    try:
        path = default_agent_config_path().with_name("agent-hook.log")
        if path.exists() and path.stat().st_size >= DIAGNOSTIC_LOG_MAX_BYTES:
            path.write_text("", encoding="utf-8")
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        status = "delivered" if delivered else "failed"
        with path.open("a", encoding="utf-8") as stream:
            stream.write(f"{timestamp} {hook_name or 'invalid'} {status}\n")
    except OSError:
        pass


def main() -> None:
    hook_name = ""
    try:
        raw = sys.stdin.buffer.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            raise ValueError("hook input is too large")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("hook input must be an object")
        hook_name = payload.get("hook_event_name", "") if isinstance(payload.get("hook_event_name"), str) else ""
        observation = normalize_hook_payload(payload)
        if observation is not None:
            delivered = send_observation(observation)
            _record_delivery(hook_name, delivered)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        pass
    # Stop requires JSON output on a successful hook. This affirmative no-op
    # never asks Codex to continue, block, approve, or modify a tool call.
    if hook_name == "Stop":
        sys.stdout.write('{"continue":true}\n')


if __name__ == "__main__":
    main()


__all__ = ["main", "normalize_hook_payload", "send_observation"]
