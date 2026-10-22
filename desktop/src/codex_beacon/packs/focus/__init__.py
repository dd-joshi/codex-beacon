"""Built-in local Focus timer pack."""

from .pack import (
    ACTION_CANCEL,
    ACTION_RESET,
    ACTION_START_PAUSE,
    FocusPack,
    FocusState,
    completed_stages,
)


def create_pack() -> FocusPack:
    """Return a fresh Focus activation instance."""

    return FocusPack()


__all__ = [
    "ACTION_CANCEL",
    "ACTION_RESET",
    "ACTION_START_PAUSE",
    "FocusPack",
    "FocusState",
    "completed_stages",
    "create_pack",
]

