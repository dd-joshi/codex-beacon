"""Run the documented expiry and sequence scenarios against the P0 simulator."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "desktop" / "src"))

from peri6.protocol.crypto import (  # noqa: E402
    auth_proof,
    b64url_decode,
    b64url_encode,
    derive_session_keys,
    open_envelope,
    seal_envelope,
)
from peri6.testing import DeviceSimulator  # noqa: E402


SECRET = bytes(range(32))
REQUEST_ID = "00112233445566778899aabbccddeeff"
CLIENT_NONCE = bytes(range(16))
EXAMPLES = REPO / "protocol" / "examples"


def connect(device: DeviceSimulator):
    challenge = device.begin_handshake(
        {
            "v": 1,
            "type": "HELLO",
            "request_id": REQUEST_ID,
            "client_name": "P0 Scenario Runner",
            "client_version": "0.1.0",
            "client_nonce": b64url_encode(CLIENT_NONCE),
        }
    )
    device_nonce = b64url_decode(challenge["device_nonce"])
    keys = derive_session_keys(
        SECRET,
        request_id=REQUEST_ID,
        session_id=challenge["sid"],
        client_nonce=CLIENT_NONCE,
        device_nonce=device_nonce,
    )
    _, capabilities = device.finish_handshake(
        {
            "v": 1,
            "type": "AUTH",
            "request_id": REQUEST_ID,
            "sid": challenge["sid"],
            "client_proof": auth_proof(
                SECRET,
                role="client",
                request_id=REQUEST_ID,
                session_id=challenge["sid"],
                client_nonce=CLIENT_NONCE,
                device_nonce=device_nonce,
            ),
        }
    )
    first_type, first_seq, _ = open_envelope(
        capabilities,
        key=keys.device_to_client,
        expected_session_id=challenge["sid"],
        max_body_bytes=device.capabilities.max_body_bytes,
        expected_sequence=1,
    )
    if (first_type, first_seq) != ("CAPABILITIES", 1):
        raise AssertionError("CAPABILITIES was not the first signed device message")
    return challenge["sid"], keys


def run(path: Path) -> None:
    scenario = json.loads(path.read_text(encoding="utf-8"))
    device = DeviceSimulator(secret=SECRET)
    sid, keys = connect(device)
    next_device_sequence = 2
    for step in scenario["steps"]:
        if "advance_ms" in step:
            device.advance(step["advance_ms"])
        if "send_seq" in step:
            body = step.get("body")
            if body is None:
                body = json.loads((EXAMPLES / step["body_file"]).read_text(encoding="utf-8"))
            response = device.handle_envelope(
                seal_envelope(
                    message_type=step["type"],
                    session_id=sid,
                    sequence=step["send_seq"],
                    body=body,
                    key=keys.client_to_device,
                )
            )
            response_type, _, response_body = open_envelope(
                response,
                key=keys.device_to_client,
                expected_session_id=sid,
                max_body_bytes=device.capabilities.max_body_bytes,
                expected_sequence=next_device_sequence,
            )
            next_device_sequence += 1
            expected = step.get("expect")
            if expected == "ERROR_WITH_SEQUENCE_ERROR_AND_CLOSE":
                if not (
                    response_type == "ERROR"
                    and response_body.get("code") == "SEQUENCE_ERROR"
                    and not device.session_open
                ):
                    raise AssertionError("expected sequence error and closed session")
            elif expected is not None and response_type != expected:
                raise AssertionError(f"expected {expected}, received {response_type}")
        if "expect_scene" in step:
            actual = device.status_body()["active_scene_id"]
            if actual != step["expect_scene"]:
                raise AssertionError(
                    f"expected scene {step['expect_scene']!r}, received {actual!r}"
                )
        if "expect_cells" in step:
            actual = [[cell.r, cell.g, cell.b] for cell in device.render_cells()]
            if actual != step["expect_cells"]:
                raise AssertionError(f"unexpected cells: {actual}")
    print(f"PASS {path.name}: {scenario['name']}")


def main() -> int:
    for name in ("expired-scenario.json", "out-of-order-scenario.json"):
        run(EXAMPLES / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
