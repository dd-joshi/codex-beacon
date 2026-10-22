"""Generic six-cell scenes used only by the hardware test console."""

from __future__ import annotations

import secrets
from typing import Iterable, Sequence

from peri6.protocol.crypto import b64url_encode
from peri6.protocol.model import DEFAULT_CAPABILITIES, DeviceScene


RGBTuple = tuple[int, int, int]
Cells = tuple[RGBTuple, RGBTuple, RGBTuple, RGBTuple, RGBTuple, RGBTuple]
RAINBOW: Cells = (
    (255, 0, 0),
    (255, 96, 0),
    (255, 220, 0),
    (0, 200, 64),
    (0, 96, 255),
    (150, 32, 255),
)


def scene_id() -> str:
    return b64url_encode(secrets.token_bytes(16))


def normalize_cells(values: Iterable[Sequence[int]]) -> Cells:
    cells = tuple(tuple(int(channel) for channel in cell) for cell in values)
    if len(cells) != 6 or any(len(cell) != 3 for cell in cells):
        raise ValueError("exactly six RGB triplets are required")
    if any(not 0 <= channel <= 255 for cell in cells for channel in cell):
        raise ValueError("RGB channels must be in 0..255")
    return cells  # type: ignore[return-value]


def static_scene(cells: Iterable[Sequence[int]], brightness: int) -> dict[str, object]:
    normalized = normalize_cells(cells)
    return _validated(
        {
            "scene_id": scene_id(),
            "lease_ms": 3000,
            "brightness": int(brightness),
            "playback": {"mode": "loop"},
            "keyframes": [_frame(normalized, "step", 0, 1000)],
        }
    )


def rainbow_chase_scene(brightness: int) -> dict[str, object]:
    frames: list[dict[str, object]] = []
    for offset in range(6):
        rotated = RAINBOW[-offset:] + RAINBOW[:-offset] if offset else RAINBOW
        frames.append(_frame(rotated, "linear", 100, 100))
    return _validated(
        {
            "scene_id": scene_id(),
            "lease_ms": 3000,
            "brightness": int(brightness),
            "playback": {"mode": "loop"},
            "keyframes": frames,
        }
    )


def pulse_scene(color: Sequence[int], brightness: int) -> dict[str, object]:
    rgb = normalize_cells([color] * 6)
    black = normalize_cells([(0, 0, 0)] * 6)
    return _validated(
        {
            "scene_id": scene_id(),
            "lease_ms": 3000,
            "brightness": int(brightness),
            "playback": {"mode": "loop"},
            "keyframes": [
                _frame(rgb, "linear", 400, 200),
                _frame(black, "linear", 400, 200),
            ],
        }
    )


def off_scene() -> dict[str, object]:
    black = normalize_cells([(0, 0, 0)] * 6)
    return _validated(
        {
            "scene_id": scene_id(),
            "lease_ms": 3000,
            "brightness": 0,
            "playback": {"mode": "once", "on_complete": "off"},
            "keyframes": [_frame(black, "step", 0, 100)],
        }
    )


def _frame(cells: Cells, kind: str, duration_ms: int, hold_ms: int) -> dict[str, object]:
    return {
        "transition": {"kind": kind, "duration_ms": duration_ms},
        "hold_ms": hold_ms,
        "cells": [list(cell) for cell in cells],
    }


def _validated(body: dict[str, object]) -> dict[str, object]:
    DeviceScene.from_body(body, DEFAULT_CAPABILITIES)
    return body
