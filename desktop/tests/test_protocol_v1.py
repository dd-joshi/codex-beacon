from __future__ import annotations

import json
import hmac
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "desktop" / "src"))

from peri6.protocol.crypto import (  # noqa: E402
    EnvelopeError,
    auth_proof,
    b64url_decode,
    b64url_encode,
    derive_session_keys,
    open_envelope,
    seal_envelope,
)
from peri6.protocol.model import (  # noqa: E402
    Capabilities,
    DeviceScene,
    ProtocolValidationError,
)
from peri6.testing import DeviceSimulator, SessionClosed  # noqa: E402


EXAMPLES = REPO / "protocol" / "examples"
SECRET = bytes(range(32))
REQUEST_ID = "00112233445566778899aabbccddeeff"
CLIENT_NONCE = bytes(range(16))


def load_json(name: str):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def authenticate(device: DeviceSimulator):
    hello = {
        "v": 1,
        "type": "HELLO",
        "request_id": REQUEST_ID,
        "client_name": "Peri6 Desktop",
        "client_version": "0.1.0",
        "client_nonce": b64url_encode(CLIENT_NONCE),
    }
    challenge = device.begin_handshake(hello)
    device_nonce = b64url_decode(challenge["device_nonce"])
    expected_device_proof = auth_proof(
        SECRET,
        role="device",
        request_id=REQUEST_ID,
        session_id=challenge["sid"],
        client_nonce=CLIENT_NONCE,
        device_nonce=device_nonce,
    )
    if challenge["device_proof"] != expected_device_proof:
        raise AssertionError("device proof did not verify")
    keys = derive_session_keys(
        SECRET,
        request_id=REQUEST_ID,
        session_id=challenge["sid"],
        client_nonce=CLIENT_NONCE,
        device_nonce=device_nonce,
    )
    auth = {
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
    authenticated, capabilities = device.finish_handshake(auth)
    expected_server_proof = auth_proof(
        SECRET,
        role="server",
        request_id=REQUEST_ID,
        session_id=challenge["sid"],
        client_nonce=CLIENT_NONCE,
        device_nonce=device_nonce,
    )
    if authenticated["server_proof"] != expected_server_proof:
        raise AssertionError("server proof did not verify")
    message_type, sequence, body = open_envelope(
        capabilities,
        key=keys.device_to_client,
        expected_session_id=challenge["sid"],
        max_body_bytes=device.capabilities.max_body_bytes,
        expected_sequence=1,
    )
    if (message_type, sequence, body["cell_count"]) != ("CAPABILITIES", 1, 6):
        raise AssertionError("invalid initial capabilities")
    return challenge["sid"], keys


class ProtocolV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.device = DeviceSimulator(secret=SECRET)
        self.sid, self.keys = authenticate(self.device)
        self.next_device_sequence = 2

    def command(self, sequence: int, message_type: str, body: dict):
        envelope = seal_envelope(
            message_type=message_type,
            session_id=self.sid,
            sequence=sequence,
            body=body,
            key=self.keys.client_to_device,
        )
        response = self.device.handle_envelope(envelope)
        decoded = open_envelope(
            response,
            key=self.keys.device_to_client,
            expected_session_id=self.sid,
            max_body_bytes=self.device.capabilities.max_body_bytes,
            expected_sequence=self.next_device_sequence,
        )
        self.next_device_sequence += 1
        return decoded

    def test_authentication_fixture_is_stable(self) -> None:
        fixture = load_json("authentication-fixture.json")
        device_nonce = b64url_decode(fixture["device_nonce"])
        client_nonce = b64url_decode(fixture["client_nonce"])
        secret = bytes.fromhex(fixture["secret_hex"])
        for role, field in (
            ("device", "device_proof"),
            ("client", "client_proof"),
            ("server", "server_proof"),
        ):
            self.assertEqual(
                auth_proof(
                    secret,
                    role=role,
                    request_id=fixture["request_id"],
                    session_id=fixture["sid"],
                    client_nonce=client_nonce,
                    device_nonce=device_nonce,
                ),
                fixture[field],
            )
        keys = derive_session_keys(
            secret,
            request_id=fixture["request_id"],
            session_id=fixture["sid"],
            client_nonce=client_nonce,
            device_nonce=device_nonce,
        )
        self.assertEqual(b64url_encode(keys.client_to_device), fixture["client_to_device_key"])
        self.assertEqual(b64url_encode(keys.device_to_client), fixture["device_to_client_key"])

    def test_device_direction_replay_is_rejected(self) -> None:
        response = self.device.emit_ambient(
            event_id="11223344556677889900aabbccddeeff", level_u16=1234
        )
        decoded = open_envelope(
            response,
            key=self.keys.device_to_client,
            expected_session_id=self.sid,
            max_body_bytes=self.device.capabilities.max_body_bytes,
            expected_sequence=2,
        )
        self.assertEqual(decoded[0], "SENSOR_EVENT")
        with self.assertRaisesRegex(EnvelopeError, "expected sequence"):
            open_envelope(
                response,
                key=self.keys.device_to_client,
                expected_session_id=self.sid,
                max_body_bytes=self.device.capabilities.max_body_bytes,
                expected_sequence=3,
            )

    def test_valid_scene_is_atomic_and_expires_exactly(self) -> None:
        scene = load_json("valid-load-scene.json")
        response_type, _, response_body = self.command(1, "LOAD_SCENE", scene)
        self.assertEqual(response_type, "ACK")
        self.assertEqual(response_body["scene_id"], scene["scene_id"])
        self.assertEqual(self.device.status_body()["active_scene_id"], scene["scene_id"])
        self.device.advance(2999)
        self.assertEqual(self.device.status_body()["active_scene_id"], scene["scene_id"])
        self.device.advance(1)
        self.assertIsNone(self.device.status_body()["active_scene_id"])
        self.assertTrue(all((cell.r, cell.g, cell.b) == (0, 0, 0) for cell in self.device.render_cells()))

    def test_invalid_candidate_preserves_old_scene_and_deadline(self) -> None:
        valid = load_json("valid-load-scene.json")
        invalid = load_json("invalid-cell-count.json")
        self.command(1, "LOAD_SCENE", valid)
        self.device.advance(1000)
        response_type, _, response_body = self.command(2, "LOAD_SCENE", invalid)
        self.assertEqual(response_type, "ERROR")
        self.assertEqual(response_body["code"], "INVALID_CELLS")
        self.assertEqual(self.device.status_body()["lease_remaining_ms"], 2000)
        self.device.advance(2000)
        self.assertIsNone(self.device.status_body()["active_scene_id"])

    def test_matching_keepalive_extends_without_restarting(self) -> None:
        valid = load_json("valid-load-scene.json")
        self.command(1, "LOAD_SCENE", valid)
        self.device.advance(1250)
        before = self.device.render_cells(unscaled=True)
        response_type, _, _ = self.command(
            2, "KEEPALIVE", {"scene_id": valid["scene_id"]}
        )
        self.assertEqual(response_type, "ACK")
        self.assertEqual(self.device.render_cells(unscaled=True), before)
        self.assertEqual(self.device.status_body()["lease_remaining_ms"], 3000)

    def test_stale_clear_cannot_remove_newer_scene(self) -> None:
        first = load_json("valid-load-scene.json")
        second = json.loads(json.dumps(first))
        second["scene_id"] = "zBEiM0RVZneImaq7zN3u_w"
        self.command(1, "LOAD_SCENE", first)
        self.command(2, "LOAD_SCENE", second)
        response_type, _, body = self.command(
            3, "CLEAR", {"scene_id": first["scene_id"]}
        )
        self.assertEqual((response_type, body["code"]), ("ERROR", "SCENE_MISMATCH"))
        self.assertEqual(self.device.status_body()["active_scene_id"], second["scene_id"])

    def test_sequence_gap_closes_without_renewing_lease(self) -> None:
        valid = load_json("valid-load-scene.json")
        self.command(1, "LOAD_SCENE", valid)
        self.device.advance(1000)
        response_type, _, body = self.command(
            3, "KEEPALIVE", {"scene_id": valid["scene_id"]}
        )
        self.assertEqual((response_type, body["code"]), ("ERROR", "SEQUENCE_ERROR"))
        self.assertFalse(self.device.session_open)
        self.device.advance(2000)
        self.assertIsNone(self.device.status_body()["active_scene_id"])

    def test_sequence_error_precedes_malformed_body_decode(self) -> None:
        encoded_body = b64url_encode(b"not-json")
        sequence = 3
        mac_input = (
            f"PERI6-MSG-V1\n1\nKEEPALIVE\n{self.sid}\n{sequence}\n{encoded_body}"
        ).encode("ascii")
        response = self.device.handle_envelope(
            {
                "v": 1,
                "type": "KEEPALIVE",
                "sid": self.sid,
                "seq": sequence,
                "body": encoded_body,
                "mac": b64url_encode(
                    hmac.digest(self.keys.client_to_device, mac_input, "sha256")
                ),
            }
        )
        response_type, _, body = open_envelope(
            response,
            key=self.keys.device_to_client,
            expected_session_id=self.sid,
            max_body_bytes=self.device.capabilities.max_body_bytes,
            expected_sequence=2,
        )
        self.assertEqual((response_type, body["code"]), ("ERROR", "SEQUENCE_ERROR"))
        self.assertFalse(self.device.session_open)

    def test_tampered_message_closes_session_without_output(self) -> None:
        envelope = seal_envelope(
            message_type="LOAD_SCENE",
            session_id=self.sid,
            sequence=1,
            body=load_json("valid-load-scene.json"),
            key=self.keys.client_to_device,
        )
        envelope["body"] = envelope["body"][:-1] + ("A" if envelope["body"][-1] != "A" else "B")
        with self.assertRaises(SessionClosed):
            self.device.handle_envelope(envelope)
        self.assertIsNone(self.device.status_body()["active_scene_id"])

    def test_old_session_packet_cannot_close_new_session(self) -> None:
        old_sid, old_keys = self.sid, self.keys
        new_sid, new_keys = authenticate(self.device)
        old_packet = seal_envelope(
            message_type="STATUS",
            session_id=old_sid,
            sequence=1,
            body={},
            key=old_keys.client_to_device,
        )
        with self.assertRaises(SessionClosed):
            self.device.handle_envelope(old_packet)
        self.assertTrue(self.device.session_open)
        response = self.device.handle_envelope(
            seal_envelope(
                message_type="STATUS",
                session_id=new_sid,
                sequence=1,
                body={},
                key=new_keys.client_to_device,
            )
        )
        response_type, response_seq, _ = open_envelope(
            response,
            key=new_keys.device_to_client,
            expected_session_id=new_sid,
            max_body_bytes=self.device.capabilities.max_body_bytes,
            expected_sequence=2,
        )
        self.assertEqual((response_type, response_seq), ("STATUS", 2))

    def test_non_json_number_cannot_be_sealed(self) -> None:
        with self.assertRaisesRegex(EnvelopeError, "strict JSON"):
            seal_envelope(
                message_type="STATUS",
                session_id=self.sid,
                sequence=1,
                body={"bad": float("nan")},
                key=self.keys.client_to_device,
            )

    def test_duplicate_members_are_rejected_in_frame_and_signed_body(self) -> None:
        with self.assertRaises(SessionClosed):
            self.device.handle_text('{"v":1,"v":1}')

        duplicate_json = (
            b'{"scene_id":"ABEiM0RVZneImaq7zN3u_w",'
            b'"scene_id":"zBEiM0RVZneImaq7zN3u_w"}'
        )
        encoded_body = b64url_encode(duplicate_json)
        mac_input = (
            f"PERI6-MSG-V1\n1\nKEEPALIVE\n{self.sid}\n1\n{encoded_body}"
        ).encode("ascii")
        duplicate_body_envelope = {
            "v": 1,
            "type": "KEEPALIVE",
            "sid": self.sid,
            "seq": 1,
            "body": encoded_body,
            "mac": b64url_encode(
                hmac.digest(self.keys.client_to_device, mac_input, "sha256")
            ),
        }
        with self.assertRaisesRegex(EnvelopeError, "UTF-8 JSON"):
            open_envelope(
                duplicate_body_envelope,
                key=self.keys.client_to_device,
                expected_session_id=self.sid,
                max_body_bytes=self.device.capabilities.max_body_bytes,
                expected_sequence=1,
            )

    def test_boolean_protocol_version_is_rejected(self) -> None:
        envelope = seal_envelope(
            message_type="STATUS",
            session_id=self.sid,
            sequence=1,
            body={},
            key=self.keys.client_to_device,
        )
        envelope["v"] = True
        with self.assertRaisesRegex(EnvelopeError, "only protocol v1"):
            open_envelope(
                envelope,
                key=self.keys.client_to_device,
                expected_session_id=self.sid,
                max_body_bytes=self.device.capabilities.max_body_bytes,
                expected_sequence=1,
            )

    def test_oversized_websocket_frame_closes_with_1009(self) -> None:
        with self.assertRaises(SessionClosed) as caught:
            self.device.handle_text("x" * (self.device.capabilities.max_websocket_bytes + 1))
        self.assertEqual(caught.exception.close_code, 1009)

    def test_invalid_example_is_rejected_by_logical_model(self) -> None:
        with self.assertRaises(ProtocolValidationError):
            DeviceScene.from_body(load_json("invalid-cell-count.json"))

    def test_capabilities_cannot_change_six_cell_contract(self) -> None:
        with self.assertRaisesRegex(ValueError, "six RGB888"):
            Capabilities(cell_count=7)

    def test_minimum_lease_is_three_keepalive_intervals(self) -> None:
        with self.assertRaisesRegex(ValueError, "three keepalive"):
            Capabilities(min_lease_ms=2999)
        scene = load_json("valid-load-scene.json")
        scene["lease_ms"] = 1000
        with self.assertRaises(ProtocolValidationError) as caught:
            DeviceScene.from_body(scene)
        self.assertEqual(caught.exception.code, "OUT_OF_RANGE")

    def test_keepalive_at_advertised_interval_has_margin(self) -> None:
        scene = load_json("valid-load-scene.json")
        self.command(1, "LOAD_SCENE", scene)
        self.device.advance(self.device.capabilities.keepalive_interval_ms)
        response_type, _, _ = self.command(
            2, "KEEPALIVE", {"scene_id": scene["scene_id"]}
        )
        self.assertEqual(response_type, "ACK")
        self.assertEqual(
            self.device.status_body()["lease_remaining_ms"],
            self.device.capabilities.default_lease_ms,
        )

    def test_once_hold_and_once_off_are_distinct(self) -> None:
        base = load_json("valid-load-scene.json")
        base["keyframes"] = [
            {
                "transition": {"kind": "step", "duration_ms": 0},
                "hold_ms": 100,
                "cells": [[255, 0, 0]] * 6,
            }
        ]
        base["playback"] = {"mode": "once", "on_complete": "hold"}
        self.command(1, "LOAD_SCENE", base)
        self.device.advance(100)
        self.assertTrue(any(cell.r > 0 for cell in self.device.render_cells()))

        off = json.loads(json.dumps(base))
        off["scene_id"] = "zBEiM0RVZneImaq7zN3u_w"
        off["playback"]["on_complete"] = "off"
        self.command(2, "LOAD_SCENE", off)
        self.device.advance(100)
        self.assertTrue(all(cell.r == 0 for cell in self.device.render_cells()))


class UnauthenticatedTests(unittest.TestCase):
    def test_unauthenticated_client_cannot_send_scene(self) -> None:
        device = DeviceSimulator(secret=SECRET)
        with self.assertRaises(SessionClosed):
            device.handle_envelope({})
        self.assertIsNone(device.status_body()["active_scene_id"])

    def test_malformed_auth_consumes_challenge(self) -> None:
        device = DeviceSimulator(secret=SECRET)
        challenge = device.begin_handshake(
            {
                "v": 1,
                "type": "HELLO",
                "request_id": REQUEST_ID,
                "client_name": "Peri6 Desktop",
                "client_version": "0.1.0",
                "client_nonce": b64url_encode(CLIENT_NONCE),
            }
        )
        with self.assertRaises(ValueError):
            device.finish_handshake({"v": 1, "type": "AUTH"})
        device_nonce = b64url_decode(challenge["device_nonce"])
        valid_auth = {
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
        with self.assertRaisesRegex(ValueError, "missing or expired"):
            device.finish_handshake(valid_auth)


if __name__ == "__main__":
    unittest.main()
