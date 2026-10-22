"""Strict logical-message model for Codex Beacon scene protocol v1."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


PROTOCOL_VERSION = 1
SCENE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{21}[AQgw]$")


class ProtocolValidationError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class Capabilities:
    cell_count: int = 6
    color_format: str = "rgb888"
    max_keyframes: int = 16
    max_body_bytes: int = 3_072
    max_websocket_bytes: int = 6_144
    transitions: tuple[str, ...] = ("step", "linear")
    max_transition_ms: int = 30_000
    max_hold_ms: int = 60_000
    max_cycle_ms: int = 120_000
    min_loop_cycle_ms: int = 100
    min_lease_ms: int = 3_000
    max_lease_ms: int = 5_000
    default_lease_ms: int = 3_000
    keepalive_interval_ms: int = 1_000
    render_tick_ms: int = 20
    max_brightness: int = 96
    button_events: bool = True
    ambient_events: bool = True

    def __post_init__(self) -> None:
        integer_fields = {
            "cell_count": self.cell_count,
            "max_keyframes": self.max_keyframes,
            "max_body_bytes": self.max_body_bytes,
            "max_websocket_bytes": self.max_websocket_bytes,
            "max_transition_ms": self.max_transition_ms,
            "max_hold_ms": self.max_hold_ms,
            "max_cycle_ms": self.max_cycle_ms,
            "min_loop_cycle_ms": self.min_loop_cycle_ms,
            "min_lease_ms": self.min_lease_ms,
            "max_lease_ms": self.max_lease_ms,
            "default_lease_ms": self.default_lease_ms,
            "keepalive_interval_ms": self.keepalive_interval_ms,
            "render_tick_ms": self.render_tick_ms,
            "max_brightness": self.max_brightness,
        }
        for name, value in integer_fields.items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.cell_count != 6 or self.color_format != "rgb888":
            raise ValueError("scene protocol v1 requires six RGB888 cells")
        if not self.transitions or len(set(self.transitions)) != len(self.transitions):
            raise ValueError("transitions must be non-empty and unique")
        if not set(self.transitions) <= {"step", "linear"}:
            raise ValueError("unsupported transition capability")
        if self.max_websocket_bytes < self.max_body_bytes:
            raise ValueError("WebSocket limit must not be below decoded-body limit")
        if self.max_cycle_ms < self.min_loop_cycle_ms:
            raise ValueError("cycle bounds are inconsistent")
        if not self.min_lease_ms <= self.default_lease_ms <= self.max_lease_ms:
            raise ValueError("default lease must fall inside lease bounds")
        if self.keepalive_interval_ms * 3 > self.min_lease_ms:
            raise ValueError("minimum lease must be at least three keepalive intervals")
        if not 1 <= self.max_brightness <= 255:
            raise ValueError("max_brightness must be between 1 and 255")
        if not isinstance(self.button_events, bool) or not isinstance(
            self.ambient_events, bool
        ):
            raise ValueError("event capabilities must be booleans")

    def to_body(self, *, device_id: str, firmware_version: str) -> dict[str, Any]:
        return {
            "device_id": device_id,
            "firmware_version": firmware_version,
            "cell_count": self.cell_count,
            "color_format": self.color_format,
            "max_keyframes": self.max_keyframes,
            "max_body_bytes": self.max_body_bytes,
            "max_websocket_bytes": self.max_websocket_bytes,
            "transitions": list(self.transitions),
            "timing": {
                "max_transition_ms": self.max_transition_ms,
                "max_hold_ms": self.max_hold_ms,
                "max_cycle_ms": self.max_cycle_ms,
                "min_loop_cycle_ms": self.min_loop_cycle_ms,
                "render_tick_ms": self.render_tick_ms,
            },
            "lease": {
                "min_ms": self.min_lease_ms,
                "max_ms": self.max_lease_ms,
                "default_ms": self.default_lease_ms,
                "keepalive_interval_ms": self.keepalive_interval_ms,
            },
            "brightness": {"min": 0, "max": self.max_brightness},
            "events": {
                "button": self.button_events,
                "ambient": self.ambient_events,
            },
            "fallback": "off",
        }


DEFAULT_CAPABILITIES = Capabilities()


@dataclass(frozen=True, slots=True)
class RGB:
    r: int
    g: int
    b: int

    @classmethod
    def from_value(cls, value: object) -> "RGB":
        if not isinstance(value, list) or len(value) != 3:
            _fail("INVALID_CELLS", "each cell must be a three-element RGB array")
        for channel in value:
            if isinstance(channel, bool) or not isinstance(channel, int):
                _fail("INVALID_RGB", "RGB channels must be integers")
            if not 0 <= channel <= 255:
                _fail("INVALID_RGB", "RGB channels must be between 0 and 255")
        return cls(value[0], value[1], value[2])

    def to_value(self) -> list[int]:
        return [self.r, self.g, self.b]


@dataclass(frozen=True, slots=True)
class Keyframe:
    transition_kind: str
    transition_ms: int
    hold_ms: int
    cells: tuple[RGB, RGB, RGB, RGB, RGB, RGB]

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition": {
                "kind": self.transition_kind,
                "duration_ms": self.transition_ms,
            },
            "hold_ms": self.hold_ms,
            "cells": [cell.to_value() for cell in self.cells],
        }


@dataclass(frozen=True, slots=True)
class DeviceScene:
    scene_id: str
    lease_ms: int
    brightness: int
    playback_mode: str
    on_complete: str | None
    keyframes: tuple[Keyframe, ...]

    @classmethod
    def from_body(
        cls,
        body: Mapping[str, object],
        capabilities: Capabilities = DEFAULT_CAPABILITIES,
    ) -> "DeviceScene":
        _exact_fields(
            body,
            {"scene_id", "lease_ms", "brightness", "playback", "keyframes"},
            "LOAD_SCENE",
        )
        if _encoded_size(body) > capabilities.max_body_bytes:
            _fail("BODY_TOO_LARGE", "decoded LOAD_SCENE body exceeds capability")

        scene_id = body["scene_id"]
        if not isinstance(scene_id, str) or not SCENE_ID_RE.fullmatch(scene_id):
            _fail("INVALID_SCENE_ID", "scene_id must encode exactly 16 random bytes")

        lease_ms = _bounded_int(
            "lease_ms",
            body["lease_ms"],
            capabilities.min_lease_ms,
            capabilities.max_lease_ms,
        )
        brightness = _bounded_int(
            "brightness", body["brightness"], 0, capabilities.max_brightness
        )

        playback = body["playback"]
        if not isinstance(playback, Mapping):
            _fail("INVALID_PLAYBACK", "playback must be an object")
        mode = playback.get("mode")
        if mode == "loop":
            _exact_fields(playback, {"mode"}, "playback")
            on_complete = None
        elif mode == "once":
            _exact_fields(playback, {"mode", "on_complete"}, "playback")
            on_complete = playback.get("on_complete")
            if on_complete not in ("hold", "off"):
                _fail("INVALID_PLAYBACK", "on_complete must be hold or off")
        else:
            _fail("INVALID_PLAYBACK", "playback mode must be loop or once")

        raw_frames = body["keyframes"]
        if not isinstance(raw_frames, list) or not (
            1 <= len(raw_frames) <= capabilities.max_keyframes
        ):
            _fail(
                "INVALID_KEYFRAME_COUNT",
                f"keyframes must contain 1-{capabilities.max_keyframes} items",
            )

        keyframes: list[Keyframe] = []
        cycle_ms = 0
        for raw_frame in raw_frames:
            if not isinstance(raw_frame, Mapping):
                _fail("INVALID_KEYFRAME", "each keyframe must be an object")
            _exact_fields(
                raw_frame, {"transition", "hold_ms", "cells"}, "keyframe"
            )
            raw_transition = raw_frame["transition"]
            if not isinstance(raw_transition, Mapping):
                _fail("INVALID_TRANSITION", "transition must be an object")
            _exact_fields(
                raw_transition, {"kind", "duration_ms"}, "transition"
            )
            kind = raw_transition["kind"]
            if kind not in capabilities.transitions:
                _fail("UNSUPPORTED_TRANSITION", "transition is not supported")
            transition_ms = _bounded_int(
                "transition.duration_ms",
                raw_transition["duration_ms"],
                0,
                capabilities.max_transition_ms,
            )
            if kind == "step" and transition_ms != 0:
                _fail("INVALID_TRANSITION", "step duration must be zero")
            if kind == "linear" and 0 < transition_ms < capabilities.render_tick_ms:
                _fail(
                    "INVALID_TRANSITION",
                    "a non-zero linear transition must be at least one render tick",
                )
            hold_ms = _bounded_int(
                "hold_ms", raw_frame["hold_ms"], 0, capabilities.max_hold_ms
            )
            raw_cells = raw_frame["cells"]
            if not isinstance(raw_cells, list) or len(raw_cells) != capabilities.cell_count:
                _fail(
                    "INVALID_CELLS",
                    f"each keyframe must contain exactly {capabilities.cell_count} cells",
                )
            cells = tuple(RGB.from_value(value) for value in raw_cells)
            keyframes.append(
                Keyframe(kind, transition_ms, hold_ms, cells)  # type: ignore[arg-type]
            )
            cycle_ms += transition_ms + hold_ms

        if cycle_ms > capabilities.max_cycle_ms:
            _fail("SCENE_TOO_LONG", "scene cycle exceeds capability")
        if mode == "loop" and cycle_ms < capabilities.min_loop_cycle_ms:
            _fail("SCENE_TOO_FAST", "loop cycle is shorter than capability")

        return cls(
            scene_id=scene_id,
            lease_ms=lease_ms,
            brightness=brightness,
            playback_mode=mode,
            on_complete=on_complete,
            keyframes=tuple(keyframes),
        )

    def to_body(self) -> dict[str, Any]:
        playback: dict[str, str] = {"mode": self.playback_mode}
        if self.on_complete is not None:
            playback["on_complete"] = self.on_complete
        return {
            "scene_id": self.scene_id,
            "lease_ms": self.lease_ms,
            "brightness": self.brightness,
            "playback": playback,
            "keyframes": [frame.to_dict() for frame in self.keyframes],
        }


def validate_scene_id_body(body: Mapping[str, object], context: str) -> str:
    _exact_fields(body, {"scene_id"}, context)
    scene_id = body["scene_id"]
    if not isinstance(scene_id, str) or not SCENE_ID_RE.fullmatch(scene_id):
        _fail("INVALID_SCENE_ID", "invalid scene_id")
    return scene_id


def _encoded_size(value: Mapping[str, object]) -> int:
    try:
        return len(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        )
    except (TypeError, ValueError) as exc:
        _fail("INVALID_JSON", f"body is not JSON-compatible: {exc}")


def _exact_fields(
    value: Mapping[str, object], expected: set[str], context: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        _fail(
            "INVALID_FIELDS",
            f"{context} fields differ; missing={missing}, extra={extra}",
        )


def _bounded_int(name: str, value: object, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail("INVALID_NUMBER", f"{name} must be an integer")
    if not minimum <= value <= maximum:
        _fail("OUT_OF_RANGE", f"{name} must be between {minimum} and {maximum}")
    return value


def _fail(code: str, detail: str):
    raise ProtocolValidationError(code, detail)
