from __future__ import annotations

import json
import math
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "desktop" / "src"))

from peri6.contracts import (  # noqa: E402
    AttentionClass,
    Explanation,
    PackProposal,
    Playback,
    RGB,
    RecipeFrame,
    Timeline,
    Transition,
    VisualRecipe,
    validate_manifest,
    validate_proposal,
)
from peri6.protocol import compile_proposal  # noqa: E402


EXAMPLES = REPO / "protocol" / "examples"


def cells(*values: tuple[int, int, int]):
    padded = values + ((0, 0, 0),) * (6 - len(values))
    return tuple(RGB(*value) for value in padded)


def proposal() -> PackProposal:
    standard = Timeline(
        frames=(
            RecipeFrame(cells((96, 0, 96)), 0, 500, Transition.STEP),
            RecipeFrame(cells((0, 96, 96)), 400, 500, Transition.LINEAR),
        ),
        playback=Playback.LOOP,
    )
    reduced = Timeline(
        frames=(RecipeFrame(cells((48, 0, 48)), 0, 1000, Transition.STEP),),
        playback=Playback.LOOP,
    )
    return PackProposal(
        state_key="render.running",
        source_observed_at=datetime.now(timezone.utc),
        valid_for_ms=5000,
        confidence=0.9,
        explanation=Explanation("Render is still running"),
        recipe=VisualRecipe(
            standard=standard,
            reduced_motion=reduced,
            requested_brightness=0.75,
            attention=AttentionClass.NORMAL,
        ),
        progress=0.5,
    )


class PackApiV1Tests(unittest.TestCase):
    def test_examples_have_compatible_manifests(self) -> None:
        for name in ("focus-manifest.json", "dummy-manifest.json"):
            value = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
            manifest = validate_manifest(value)
            self.assertEqual(manifest.host_api_major, 1)

    def test_boolean_manifest_version_is_rejected(self) -> None:
        value = json.loads((EXAMPLES / "dummy-manifest.json").read_text(encoding="utf-8"))
        value["manifest_version"] = True
        with self.assertRaisesRegex(ValueError, "manifest v1"):
            validate_manifest(value)

    def test_remote_settings_ref_is_rejected(self) -> None:
        value = json.loads((EXAMPLES / "dummy-manifest.json").read_text(encoding="utf-8"))
        value["settings_schema"] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "$ref": "https://example.test/schema.json",
        }
        with self.assertRaisesRegex(ValueError, "remote"):
            validate_manifest(value)

    def test_settings_schema_must_declare_draft_and_object_root(self) -> None:
        value = json.loads((EXAMPLES / "dummy-manifest.json").read_text(encoding="utf-8"))
        del value["settings_schema"]["$schema"]
        with self.assertRaisesRegex(ValueError, "Draft 2020-12"):
            validate_manifest(value)

    def test_malformed_draft_2020_12_schema_is_rejected(self) -> None:
        value = json.loads((EXAMPLES / "dummy-manifest.json").read_text(encoding="utf-8"))
        value["settings_schema"]["properties"] = []
        with self.assertRaisesRegex(ValueError, "not valid Draft 2020-12"):
            validate_manifest(value)

    def test_proposal_compiles_through_semantic_firewall(self) -> None:
        source = proposal()
        validate_proposal(source)
        scene = compile_proposal(
            source,
            scene_id="ABEiM0RVZneImaq7zN3u_w",
            reduced_motion=False,
        )
        wire_body = scene.to_body()
        self.assertEqual(
            set(wire_body),
            {"scene_id", "lease_ms", "brightness", "playback", "keyframes"},
        )
        serialized = json.dumps(wire_body).lower()
        for forbidden in (
            "render.running",
            "render is still running",
            "progress",
            "confidence",
            "pack",
            "application",
            "blender",
            "focus",
            "lite",
            "pro",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_reduced_motion_timeline_is_independently_compiled(self) -> None:
        source = proposal()
        standard = compile_proposal(
            source, scene_id="ABEiM0RVZneImaq7zN3u_w", reduced_motion=False
        )
        reduced = compile_proposal(
            source, scene_id="zBEiM0RVZneImaq7zN3u_w", reduced_motion=True
        )
        self.assertNotEqual(standard.keyframes, reduced.keyframes)

    def test_nonfinite_pack_values_are_rejected(self) -> None:
        invalid = replace(proposal(), confidence=math.nan)
        with self.assertRaises(ValueError):
            validate_proposal(invalid)

    def test_wrong_cell_count_is_rejected_before_compilation(self) -> None:
        source = proposal()
        bad_frame = replace(source.recipe.standard.frames[0], cells=cells((1, 2, 3))[:5])
        bad_timeline = replace(source.recipe.standard, frames=(bad_frame,))
        invalid = replace(source, recipe=replace(source.recipe, standard=bad_timeline))
        with self.assertRaisesRegex(ValueError, "six cells"):
            validate_proposal(invalid)

    def test_plain_string_playback_is_rejected(self) -> None:
        source = proposal()
        invalid_timeline = replace(source.recipe.standard, playback="bogus")
        invalid = replace(source, recipe=replace(source.recipe, standard=invalid_timeline))
        with self.assertRaisesRegex(TypeError, "Playback"):
            validate_proposal(invalid)

    def test_plain_string_transition_is_rejected(self) -> None:
        source = proposal()
        invalid_frame = replace(source.recipe.standard.frames[0], transition="step")
        invalid_timeline = replace(source.recipe.standard, frames=(invalid_frame,))
        invalid = replace(source, recipe=replace(source.recipe, standard=invalid_timeline))
        with self.assertRaisesRegex(TypeError, "Transition"):
            validate_proposal(invalid)


if __name__ == "__main__":
    unittest.main()
