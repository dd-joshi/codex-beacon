"""Reference pack-proposal to semantic-free device-scene compiler."""

from __future__ import annotations

from peri6.contracts.pack import PackProposal, Playback, validate_proposal

from .model import DEFAULT_CAPABILITIES, Capabilities, DeviceScene


def compile_proposal(
    proposal: PackProposal,
    *,
    scene_id: str,
    reduced_motion: bool,
    capabilities: Capabilities = DEFAULT_CAPABILITIES,
) -> DeviceScene:
    """Compile a valid proposal without forwarding desktop semantics.

    Scene freshness is enforced by the host deciding whether to continue sending
    keepalives.  The short device lease is therefore independent of the proposal
    TTL.
    """

    validate_proposal(proposal)
    timeline = (
        proposal.recipe.reduced_motion if reduced_motion else proposal.recipe.standard
    )
    if timeline.playback is Playback.LOOP:
        playback: dict[str, str] = {"mode": "loop"}
    elif timeline.playback is Playback.ONCE_HOLD:
        playback = {"mode": "once", "on_complete": "hold"}
    elif timeline.playback is Playback.ONCE_CLEAR:
        playback = {"mode": "once", "on_complete": "off"}
    else:  # defensive even though validate_proposal rejects this
        raise ValueError("unsupported playback")

    body = {
        "scene_id": scene_id,
        "lease_ms": capabilities.default_lease_ms,
        "brightness": min(
            capabilities.max_brightness,
            int(proposal.recipe.requested_brightness * capabilities.max_brightness),
        ),
        "playback": playback,
        "keyframes": [
            {
                "transition": {
                    "kind": frame.transition.value,
                    "duration_ms": frame.transition_ms,
                },
                "hold_ms": frame.hold_ms,
                "cells": [[cell.r, cell.g, cell.b] for cell in frame.cells],
            }
            for frame in timeline.frames
        ],
    }
    return DeviceScene.from_body(body, capabilities)
