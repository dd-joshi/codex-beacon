"""Built-in privacy-safe Codex activity pack.

Imports stay lazy so the tiny stdlib-only hook sender does not load Qt,
jsonschema, WebSocket, or the device host in every short-lived hook process.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .events import AgentObservation, AgentOutcome, AgentState, AgentTask
    from .pack import AgentPack


def create_pack() -> "AgentPack":
    """Return a fresh Agent activation instance."""

    from .pack import AgentPack

    return AgentPack()


def __getattr__(name: str) -> object:
    if name in {"AgentObservation", "AgentOutcome", "AgentState", "AgentTask"}:
        from . import events

        return getattr(events, name)
    if name == "AgentPack":
        from .pack import AgentPack

        return AgentPack
    raise AttributeError(name)


__all__ = [
    "AgentObservation",
    "AgentOutcome",
    "AgentPack",
    "AgentState",
    "AgentTask",
    "create_pack",
]
