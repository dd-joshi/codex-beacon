"""Small semantic event contract between Codex hooks and the Agent pack.

No prompt, command, tool input, tool output, file path, or transcript content is
accepted by this boundary.  Identifiers are one-way digests made by the hook
sender and are useful only for ordering and duplicate suppression.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    EDITING = "editing"
    TESTING = "testing"
    BUILDING = "building"
    WAITING = "waiting"
    INPUT_WAITING = "input"
    SUCCESS = "success"
    FAILURE = "failure"
    REVIEW = "review"


class AgentTask(str, Enum):
    THINKING = "thinking"
    WORKING = "working"
    EDITING = "editing"
    TESTING = "testing"
    BUILDING = "building"


class AgentOutcome(str, Enum):
    UNKNOWN = "unknown"
    SUCCESS = "success"
    FAILURE = "failure"


EVENTS = frozenset(
    {
        "turn_started",
        "tool_started",
        "approval_waiting",
        "tool_finished",
        "turn_stopped",
    }
)

# v2 adds provider-neutral states plus alias spellings.  Aliases canonicalize
# onto the v1 names so the reducer keeps one code path.
V2_ONLY_EVENTS = frozenset(
    {
        "input_waiting",
        "tool_completed",
        "turn_completed",
        "turn_cancelled",
        "session_ended",
    }
)
ALL_EVENTS = EVENTS | V2_ONLY_EVENTS
EVENT_ALIASES = {"tool_completed": "tool_finished", "turn_completed": "turn_stopped"}
PROVIDERS = frozenset({"codex", "claude", "copilot", "vscode", "unknown"})
PROVIDER_LABELS = {
    "codex": "Codex",
    "claude": "Claude",
    "copilot": "Copilot",
    "vscode": "VS Code",
    "unknown": "Agent",
}

_V1_FIELDS = {
    "version",
    "event_id",
    "turn_key",
    "tool_key",
    "event",
    "task",
    "outcome",
    "occurred_monotonic_ns",
}
_V2_FIELDS = _V1_FIELDS | {"provider", "session_key", "workspace_key"}


@dataclass(frozen=True, slots=True)
class AgentObservation:
    event_id: str
    turn_key: str
    tool_key: str | None
    event: str
    task: AgentTask
    outcome: AgentOutcome
    occurred_monotonic_ns: int
    provider: str = "unknown"
    session_key: str | None = None
    workspace_key: str | None = None

    @classmethod
    def from_json(cls, value: Mapping[str, object]) -> "AgentObservation":
        if not isinstance(value, dict):
            raise ValueError("Agent event fields are not exact")
        version = value.get("version")
        if version == 1:
            fields = _V1_FIELDS
        elif version == 2:
            fields = _V2_FIELDS
        else:
            raise ValueError("Agent event fields are not exact")
        if set(value) != fields:
            raise ValueError("Agent event fields are not exact")
        event_id = _digest(value.get("event_id"), "event_id")
        turn_key = _digest(value.get("turn_key"), "turn_key")
        raw_tool_key = value.get("tool_key")
        tool_key = (
            None if raw_tool_key is None else _digest(raw_tool_key, "tool_key")
        )
        event = value.get("event")
        if not isinstance(event, str) or event not in ALL_EVENTS:
            raise ValueError("unsupported Agent event")
        event = EVENT_ALIASES.get(event, event)
        try:
            task = AgentTask(value.get("task"))
            outcome = AgentOutcome(value.get("outcome"))
        except ValueError as exc:
            raise ValueError("unsupported Agent task or outcome") from exc
        occurred = value.get("occurred_monotonic_ns")
        if isinstance(occurred, bool) or not isinstance(occurred, int) or occurred < 0:
            raise ValueError("occurred_monotonic_ns must be a non-negative integer")
        provider = value.get("provider", "unknown") if version == 2 else "unknown"
        if not isinstance(provider, str) or provider not in PROVIDERS:
            raise ValueError("unsupported Agent provider")
        session_key: str | None = None
        workspace_key: str | None = None
        if version == 2:
            for name, target in (
                ("session_key", "session"),
                ("workspace_key", "workspace"),
            ):
                raw = value.get(name)
                if raw is not None:
                    _digest(raw, name)
                if name == "session_key":
                    session_key = raw
                else:
                    workspace_key = raw
        return cls(
            event_id,
            turn_key,
            tool_key,
            event,
            task,
            outcome,
            occurred,
            provider,
            session_key,
            workspace_key,
        )

    def to_json(self) -> dict[str, object]:
        if self.version == 1:
            return {
                "version": 1,
                "event_id": self.event_id,
                "turn_key": self.turn_key,
                "tool_key": self.tool_key,
                "event": self.event,
                "task": self.task.value,
                "outcome": self.outcome.value,
                "occurred_monotonic_ns": self.occurred_monotonic_ns,
            }
        return {
            "version": 2,
            "event_id": self.event_id,
            "turn_key": self.turn_key,
            "tool_key": self.tool_key,
            "event": self.event,
            "task": self.task.value,
            "outcome": self.outcome.value,
            "occurred_monotonic_ns": self.occurred_monotonic_ns,
            "provider": self.provider,
            "session_key": self.session_key,
            "workspace_key": self.workspace_key,
        }

    @property
    def version(self) -> int:
        return 2 if (self.session_key is not None or self.provider != "unknown" or self.workspace_key is not None) else 1


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 32:
        raise ValueError(f"{name} must be a 32-character digest")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be lowercase hexadecimal")
    return value


__all__ = [
    "ALL_EVENTS",
    "AgentObservation",
    "AgentOutcome",
    "AgentState",
    "AgentTask",
    "EVENT_ALIASES",
    "EVENTS",
    "PROVIDERS",
    "PROVIDER_LABELS",
    "V2_ONLY_EVENTS",
]
