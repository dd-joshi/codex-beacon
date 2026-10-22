"""Wall-clock persistence for the Focus timer across application restarts.

State lives in ``%LOCALAPPDATA%\\CodexBeacon\\timer.json`` (per-user, outside the
repository).  A running timer stores an absolute UTC deadline so the remaining
time survives desktop restarts; a paused timer stores its remaining seconds.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_STORE_FILENAME = "timer.json"


class TimerStoreError(Exception):
    pass


def timer_state_path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(
            Path.home() / "AppData" / "Local"
        )
        return Path(base) / "CodexBeacon" / _STORE_FILENAME
    return Path.home() / ".codex-beacon" / _STORE_FILENAME


def save_timer_state(
    duration_minutes: int,
    *,
    phase: str,
    remaining_seconds: int,
    now_utc: datetime | None = None,
    path: Path | None = None,
) -> Path:
    if phase not in {"working", "paused"}:
        raise TimerStoreError("only working or paused timers are persisted")
    now = now_utc or datetime.now(tz=timezone.utc)
    deadline = (
        _isoformat(now + _timedelta(seconds=remaining_seconds))
        if phase == "working"
        else None
    )
    document = {
        "version": 1,
        "duration_minutes": int(duration_minutes),
        "phase": phase,
        "remaining_seconds": int(remaining_seconds),
        "deadline_utc": deadline,
        "saved_utc": _isoformat(now),
    }
    target = path or timer_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return target


def load_timer_state(
    *, now_utc: datetime | None = None, path: Path | None = None
) -> dict[str, object] | None:
    """Return {'phase','remaining_seconds','duration_minutes'} or None.

    A working timer whose deadline has already passed is treated as finished
    and cleared.  Corrupt or unknown files are removed rather than trusted.
    """

    target = path or timer_state_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        document = json.loads(raw)
        if (
            not isinstance(document, dict)
            or document.get("version") != 1
            or document.get("phase") not in {"working", "paused"}
        ):
            raise ValueError("unknown timer state")
        remaining = int(document["remaining_seconds"])  # type: ignore[arg-type]
        duration = int(document["duration_minutes"])  # type: ignore[arg-type]
        if remaining < 0 or duration < 1:
            raise ValueError("invalid timer values")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        target.unlink(missing_ok=True)
        return None
    phase = str(document["phase"])
    now = now_utc or datetime.now(tz=timezone.utc)
    if phase == "working":
        deadline_text = document.get("deadline_utc")
        if not isinstance(deadline_text, str):
            target.unlink(missing_ok=True)
            return None
        try:
            deadline = datetime.fromisoformat(deadline_text)
        except ValueError:
            target.unlink(missing_ok=True)
            return None
        remaining = _seconds_between(now, deadline)
        if remaining <= 0:
            target.unlink(missing_ok=True)
            return {"phase": "completed", "remaining_seconds": 0, "duration_minutes": duration}
    return {
        "phase": phase,
        "remaining_seconds": remaining,
        "duration_minutes": duration,
    }


def clear_timer_state(path: Path | None = None) -> None:
    (path or timer_state_path()).unlink(missing_ok=True)


def _timedelta(**kwargs: int):
    from datetime import timedelta

    return timedelta(**kwargs)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _seconds_between(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds())


__all__ = [
    "TimerStoreError",
    "clear_timer_state",
    "load_timer_state",
    "save_timer_state",
    "timer_state_path",
]
