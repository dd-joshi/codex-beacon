"""Pure phone-status projection and local configuration.

The phone page consumes this semantic status instead of the six-cell scene or
the Qt presentation state.  It therefore carries only application-level text
and bounded timing data, never prompts, commands, paths, transcripts, device
credentials, or the Agent bearer token.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from codex_beacon.companion.presentation import FocusPhase, OutputPhase, PresentationState
from codex_beacon.contracts import AttentionClass
from codex_beacon.packs.registry import AGENT_PACK_ID, FOCUS_PACK_ID


PHONE_STATUS_VERSION = 1
DEFAULT_PHONE_STATUS_PORT = 8765
MIN_PHONE_STATUS_PORT = 1024
MAX_PHONE_STATUS_PORT = 65535
LIVE_STALE_AFTER_SECONDS = 90.0
TERMINAL_STALE_AFTER_SECONDS = 20.0

_STABLE_LIVE_STATE_KEYS = frozenset({"agent.idle"})
_TERMINAL_STATE_KEYS = frozenset(
    {
        "agent.success",
        "agent.failure",
        "focus.completed",
        "focus.cancelled",
    }
)


class StatusPhase(str, Enum):
    LIVE = "live"
    LAST_KNOWN = "last_known"
    STALE = "stale"
    OFFLINE = "offline"
    ERROR = "error"


class NotificationIntent(str, Enum):
    NONE = "none"
    CHIME = "chime"
    URGENT = "urgent"


@dataclass(frozen=True, slots=True)
class PhoneStatusConfig:
    path: Path
    enabled: bool
    port: int
    token: str


@dataclass(frozen=True, slots=True)
class StatusSnapshot:
    pack_id: str
    pack_name: str
    state_key: str
    headline: str
    detail: str
    suggested_action: str | None
    attention: AttentionClass
    phase: StatusPhase
    notify: NotificationIntent
    transition_id: str
    updated_at: datetime | None
    age_seconds: float | None
    progress: float | None
    focus_remaining_seconds: int | None
    is_focus: bool
    cells: tuple[tuple[int, int, int], ...]

    def to_json(self) -> dict[str, object]:
        return {
            "version": PHONE_STATUS_VERSION,
            "pack_id": self.pack_id,
            "pack_name": self.pack_name,
            "state_key": self.state_key,
            "headline": self.headline,
            "detail": self.detail,
            "suggested_action": self.suggested_action,
            "attention": self.attention.value,
            "phase": self.phase.value,
            "notify": self.notify.value,
            "transition_id": self.transition_id,
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
            "age_seconds": (
                round(self.age_seconds, 1) if self.age_seconds is not None else None
            ),
            "progress": self.progress,
            "focus_remaining_seconds": self.focus_remaining_seconds,
            "is_focus": self.is_focus,
            "cells": [list(cell) for cell in self.cells],
        }


class StatusProjector:
    """Convert the companion's presentation state into a phone-safe snapshot."""

    def __init__(self) -> None:
        self._session_id = secrets.token_hex(4)
        self._semantic_key: tuple[str, int, str] | None = None
        self._transition_sequence = 0

    def project(
        self,
        state: PresentationState,
        *,
        now_monotonic_ns: int | None = None,
        now_utc: datetime | None = None,
    ) -> StatusSnapshot:
        now_ns = now_monotonic_ns if now_monotonic_ns is not None else time.monotonic_ns()
        current_utc = now_utc or datetime.now(timezone.utc)

        semantic_key = (
            state.active_pack_id,
            state.activation_generation,
            state.active_state_key,
        )
        if semantic_key != self._semantic_key:
            self._semantic_key = semantic_key
            self._transition_sequence += 1

        phase = _phase(state, now_ns)
        headline, detail = _headline_and_detail(state)
        suggested_action = _suggested_action(state)
        updated_at = state.source_observed_at
        age_seconds = _age_seconds(updated_at, current_utc)

        return StatusSnapshot(
            pack_id=state.active_pack_id,
            pack_name=state.active_pack_name,
            state_key=state.active_state_key,
            headline=headline,
            detail=detail,
            suggested_action=suggested_action,
            attention=state.attention,
            phase=phase,
            notify=_notification_intent(state, phase),
            transition_id=(
                f"{self._session_id}:{state.active_pack_id}:"
                f"{state.activation_generation}:{self._transition_sequence}"
            ),
            updated_at=updated_at,
            age_seconds=age_seconds,
            progress=state.progress if state.is_focus else None,
            focus_remaining_seconds=(
                state.remaining_seconds if state.is_focus else None
            ),
            is_focus=state.is_focus,
            cells=tuple((cell.r, cell.g, cell.b) for cell in state.semantic_cells),
        )


def _phase(state: PresentationState, now_ns: int) -> StatusPhase:
    if state.notice:
        return StatusPhase.ERROR
    if state.output_accepted_monotonic_ns == 0 and state.output_sequence is None:
        return StatusPhase.OFFLINE
    # The phone page is a software-only companion. A device connection is
    # optional, so a fresh host proposal is live even when OutputPhase is OFF
    # because no physical display accepted the scene.
    if state.output_accepted_monotonic_ns > 0:
        expires = state.output_expires_monotonic_ns
        if expires is None or now_ns < expires:
            return StatusPhase.LIVE
        return _expired_phase(state)
    if state.output in {OutputPhase.PENDING, OutputPhase.ACTIVE}:
        expires = state.output_expires_monotonic_ns
        if expires is not None and now_ns >= expires:
            return _expired_phase(state)
        return StatusPhase.LIVE
    return _expired_phase(state)


def _expired_phase(state: PresentationState) -> StatusPhase:
    if state.active_pack_id == AGENT_PACK_ID:
        if state.active_state_key == "agent.idle":
            # Idle is a stable semantic state even though the device lease has
            # expired; the Agent pack is still observing the workspace.
            return StatusPhase.LIVE
        if state.active_state_key in {
            "agent.success",
            "agent.failure",
            "agent.review",
        }:
            return StatusPhase.LAST_KNOWN
        return StatusPhase.STALE
    if state.active_pack_id == FOCUS_PACK_ID:
        if state.focus in {FocusPhase.COMPLETED, FocusPhase.CANCELLED}:
            return StatusPhase.LAST_KNOWN
        return StatusPhase.STALE
    return StatusPhase.LAST_KNOWN


def _headline_and_detail(state: PresentationState) -> tuple[str, str]:
    if state.notice:
        return (
            "Companion error",
            "Codex Beacon reported a local error. Check the companion on the PC.",
        )
    if state.is_focus:
        headline = {
            FocusPhase.IDLE: "Focus ready",
            FocusPhase.WORKING: "Focus running",
            FocusPhase.PAUSED: "Focus paused",
            FocusPhase.COMPLETED: "Focus complete",
            FocusPhase.CANCELLED: "Focus cancelled",
            FocusPhase.UNKNOWN: "Focus state unavailable",
        }[state.focus]
        return headline, state.detail
    headline = state.headline or state.active_pack_name
    return headline, state.detail


def _suggested_action(state: PresentationState) -> str | None:
    if state.notice:
        return "Check Codex Beacon on the PC."
    if state.suggested_action:
        return state.suggested_action
    if state.active_state_key in {"agent.waiting", "agent.input"}:
        return "Finish the approval on your PC."
    if state.active_state_key == "agent.review":
        return "Review the result on your PC."
    if state.active_state_key == "agent.failure":
        return "Open the failed check on your PC."
    return None


def _notification_intent(
    state: PresentationState, phase: StatusPhase
) -> NotificationIntent:
    if phase is not StatusPhase.LIVE:
        return NotificationIntent.NONE
    if state.active_pack_id == AGENT_PACK_ID:
        if state.active_state_key in {"agent.waiting", "agent.input", "agent.failure"}:
            return NotificationIntent.URGENT
        if state.active_state_key in {"agent.success", "agent.review"}:
            return NotificationIntent.CHIME
    if state.is_focus and state.focus is FocusPhase.COMPLETED:
        return NotificationIntent.CHIME
    return NotificationIntent.NONE


def _age_seconds(updated_at: datetime | None, now_utc: datetime) -> float | None:
    if updated_at is None:
        return None
    if updated_at.tzinfo is None or updated_at.utcoffset() is None:
        return None
    return max(0.0, (now_utc - updated_at).total_seconds())


def freshen_snapshot(
    snapshot: StatusSnapshot,
    *,
    now_utc: datetime | None = None,
) -> StatusSnapshot:
    """Recompute freshness for a stored snapshot at request time.

    The companion republishes every few seconds while healthy.  If its event
    loop stalls, the HTTP thread must not keep advertising an old live state as
    current merely because the last stored snapshot said "live".
    """

    current_utc = now_utc or datetime.now(timezone.utc)
    age = _age_seconds(snapshot.updated_at, current_utc)
    if age is None:
        return snapshot
    phase = snapshot.phase
    notify = snapshot.notify
    if phase is StatusPhase.LIVE and snapshot.state_key not in _STABLE_LIVE_STATE_KEYS:
        if (
            snapshot.state_key in _TERMINAL_STATE_KEYS
            and age > TERMINAL_STALE_AFTER_SECONDS
        ):
            phase = StatusPhase.LAST_KNOWN
            notify = NotificationIntent.NONE
        elif age > LIVE_STALE_AFTER_SECONDS:
            phase = StatusPhase.STALE
            notify = NotificationIntent.NONE
    return replace(snapshot, phase=phase, notify=notify, age_seconds=age)


def default_phone_status_path(agent_config_path: Path) -> Path:
    return agent_config_path.with_name("phone-status.json")


def load_phone_status_config(path: Path) -> PhoneStatusConfig:
    """Load or create the local phone-page settings file."""

    if not path.exists():
        config = PhoneStatusConfig(
            path=path,
            enabled=True,
            port=DEFAULT_PHONE_STATUS_PORT,
            token=secrets.token_urlsafe(32),
        )
        save_phone_status_config(config)
        return config

    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Phone status config is unreadable: {path}") from exc
    expected = {"version", "enabled", "port", "token"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("Phone status config fields are not exact")
    if value.get("version") != PHONE_STATUS_VERSION:
        raise ValueError("Unsupported phone status config version")
    enabled = value.get("enabled")
    port = value.get("port")
    token = value.get("token")
    if not isinstance(enabled, bool):
        raise ValueError("Phone status enabled must be a boolean")
    if isinstance(port, bool) or not isinstance(port, int):
        raise ValueError("Phone status port must be an integer")
    if not MIN_PHONE_STATUS_PORT <= port <= MAX_PHONE_STATUS_PORT:
        raise ValueError("Phone status port is outside the allowed range")
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("Phone status token is too short")
    return PhoneStatusConfig(path=path, enabled=enabled, port=port, token=token)


def save_phone_status_config(config: PhoneStatusConfig) -> None:
    path = config.path
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "version": PHONE_STATUS_VERSION,
        "enabled": config.enabled,
        "port": config.port,
        "token": config.token,
    }
    rendered = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def rotate_phone_status_token(config: PhoneStatusConfig) -> PhoneStatusConfig:
    rotated = replace(config, token=secrets.token_urlsafe(32))
    save_phone_status_config(rotated)
    return rotated


__all__ = [
    "DEFAULT_PHONE_STATUS_PORT",
    "LIVE_STALE_AFTER_SECONDS",
    "MAX_PHONE_STATUS_PORT",
    "MIN_PHONE_STATUS_PORT",
    "NotificationIntent",
    "PHONE_STATUS_VERSION",
    "PhoneStatusConfig",
    "StatusPhase",
    "StatusProjector",
    "StatusSnapshot",
    "TERMINAL_STALE_AFTER_SECONDS",
    "default_phone_status_path",
    "freshen_snapshot",
    "load_phone_status_config",
    "rotate_phone_status_token",
    "save_phone_status_config",
]
