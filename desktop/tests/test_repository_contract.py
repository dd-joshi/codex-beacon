from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "desktop" / "src"))

from peri6.protocol.model import DEFAULT_CAPABILITIES  # noqa: E402


def schema(name: str) -> dict:
    return json.loads(
        (REPO / "protocol" / "schemas" / name).read_text(encoding="utf-8")
    )


class RepositoryContractTests(unittest.TestCase):
    def test_all_protocol_json_files_parse(self) -> None:
        files = sorted((REPO / "protocol").rglob("*.json"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path.relative_to(REPO)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_schema_ids_are_unique_and_use_draft_2020_12(self) -> None:
        schemas = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((REPO / "protocol" / "schemas").glob("*.json"))
        ]
        self.assertTrue(schemas)
        self.assertEqual(len({schema["$id"] for schema in schemas}), len(schemas))
        for schema in schemas:
            self.assertEqual(
                schema["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )
            Draft202012Validator.check_schema(schema)

    def test_scene_and_manifest_examples_validate_against_schemas(self) -> None:
        scene_validator = Draft202012Validator(schema("load-scene-body-v1.schema.json"))
        valid = json.loads(
            (REPO / "protocol" / "examples" / "valid-load-scene.json").read_text(
                encoding="utf-8"
            )
        )
        invalid = json.loads(
            (REPO / "protocol" / "examples" / "invalid-cell-count.json").read_text(
                encoding="utf-8"
            )
        )
        scene_validator.validate(valid)
        with self.assertRaises(ValidationError):
            scene_validator.validate(invalid)

        manifest_validator = Draft202012Validator(schema("pack-manifest-v1.schema.json"))
        for name in ("focus-manifest.json", "dummy-manifest.json"):
            manifest_validator.validate(
                json.loads(
                    (REPO / "protocol" / "examples" / name).read_text(
                        encoding="utf-8"
                    )
                )
            )

    def test_generated_device_bodies_validate_and_battery_is_forbidden(self) -> None:
        scene_id = "ABEiM0RVZneImaq7zN3u_w"
        values = {
            "capabilities-body-v1.schema.json": DEFAULT_CAPABILITIES.to_body(
                device_id="p6-c3-000001", firmware_version="0.1.0"
            ),
            "ack-body-v1.schema.json": {
                "reply_to": 1,
                "scene_id": scene_id,
                "result": "accepted",
            },
            "error-body-v1.schema.json": {
                "reply_to": 2,
                "code": "INVALID_CELLS",
                "detail": "six cells required",
            },
            "status-body-v1.schema.json": {
                "reply_to": 3,
                "boot_id": "00112233445566778899aabbccddeeff",
                "uptime_ms": 100,
                "scene_state": "active",
                "active_scene_id": scene_id,
                "frame_index": 0,
                "lease_remaining_ms": 2900,
            },
            "button-event-body-v1.schema.json": {
                "event_id": "11223344556677889900aabbccddeeff",
                "gesture": "tap",
                "duration_ms": 100,
            },
            "sensor-event-body-v1.schema.json": {
                "event_id": "22334455667788990011aabbccddeeff",
                "sensor": "ambient",
                "level_u16": 32768,
            },
        }
        for name, value in values.items():
            with self.subTest(schema=name):
                Draft202012Validator(schema(name)).validate(value)

        forbidden = dict(values["capabilities-body-v1.schema.json"])
        forbidden["battery"] = {"available": True}
        with self.assertRaises(ValidationError):
            Draft202012Validator(
                schema("capabilities-body-v1.schema.json")
            ).validate(forbidden)

    def test_local_secret_paths_are_ignored_and_untracked(self) -> None:
        if not (REPO / ".git").exists():
            self.skipTest("source-control metadata is absent from this workspace copy")
        forbidden = (
            REPO / "firmware" / "include" / "peri6_secrets.h",
            REPO / "desktop" / "secrets.json",
            REPO / "desktop" / "local-config.json",
        )
        for path in forbidden:
            relative = path.relative_to(REPO).as_posix()
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", relative],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(tracked.returncode, 0, f"secret/config is tracked: {relative}")
            ignored = subprocess.run(
                ["git", "check-ignore", "-q", relative],
                cwd=REPO,
                check=False,
            )
            self.assertEqual(ignored.returncode, 0, f"secret/config is not ignored: {relative}")

    def test_documented_scenarios_execute(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(REPO / "tools" / "scenario-runner" / "run_scenarios.py")],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS expired-scenario.json", completed.stdout)
        self.assertIn("PASS out-of-order-scenario.json", completed.stdout)


if __name__ == "__main__":
    unittest.main()
