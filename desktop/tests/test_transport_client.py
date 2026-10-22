from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from peri6.protocol.crypto import b64url_encode
from peri6.protocol.model import DEFAULT_CAPABILITIES, DeviceScene
from peri6.tester.config import load_local_test_config
from peri6.tester.presets import RAINBOW, off_scene, pulse_scene, rainbow_chase_scene, static_scene
from peri6.testing.device_simulator import DeviceSimulator
from peri6.transport.client import ProtocolClientError, ProtocolSession, normalize_endpoint


class _FakeWebSocket:
    def __init__(self, simulator: DeviceSimulator) -> None:
        self.simulator = simulator
        self.responses: list[str] = []
        self.closed = False

    def getsubprotocol(self) -> str:
        return "peri6.scene.v1"

    def send(self, payload: str) -> None:
        message = json.loads(payload)
        if message.get("type") == "HELLO":
            response = self.simulator.begin_handshake(message)
            self.responses.append(json.dumps(response, separators=(",", ":")))
        elif message.get("type") == "AUTH":
            authenticated, capabilities = self.simulator.finish_handshake(message)
            self.responses.extend(
                json.dumps(response, separators=(",", ":"))
                for response in (authenticated, capabilities)
            )
        else:
            response = self.simulator.handle_text(payload)
            self.responses.append(json.dumps(response, separators=(",", ":")))

    def recv(self) -> str:
        if not self.responses:
            raise AssertionError("client requested an unexpected response")
        return self.responses.pop(0)

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def close(self) -> None:
        self.closed = True


class HardwareTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = bytes(range(32))
        self.device = DeviceSimulator(secret=self.secret, device_id="p6-c3-afb810")
        self.socket = _FakeWebSocket(self.device)

    def authenticate(self) -> ProtocolSession:
        values = iter((bytes(range(16)), bytes(range(16, 32))))
        return ProtocolSession.authenticate(
            self.socket,
            endpoint="ws://p6-c3-afb810.local:8765/ws/v1",
            secret=self.secret,
            expected_device_id="p6-c3-afb810",
            random_bytes=lambda size: next(values),
        )

    def test_handshake_load_keepalive_status_and_clear(self) -> None:
        session = self.authenticate()
        self.assertIsNotNone(session.info)
        assert session.info is not None
        self.assertEqual(session.info.device_id, "p6-c3-afb810")

        scene = static_scene(RAINBOW, 72)
        load_sequence = session.send_command("LOAD_SCENE", scene)
        load_ack = session.receive()
        self.assertEqual(load_ack.message_type, "ACK")
        self.assertEqual(load_ack.body["reply_to"], load_sequence)

        scene_id = scene["scene_id"]
        keepalive_sequence = session.send_command("KEEPALIVE", {"scene_id": scene_id})
        keepalive_ack = session.receive()
        self.assertEqual(keepalive_ack.body["reply_to"], keepalive_sequence)

        status_sequence = session.send_command("STATUS", {})
        status = session.receive()
        self.assertEqual(status.message_type, "STATUS")
        self.assertEqual(status.body["reply_to"], status_sequence)
        self.assertEqual(status.body["active_scene_id"], scene_id)

        clear_sequence = session.send_command("CLEAR", {"scene_id": scene_id})
        clear_ack = session.receive()
        self.assertEqual(clear_ack.body["reply_to"], clear_sequence)

    def test_authenticated_device_id_mismatch_is_rejected(self) -> None:
        values = iter((bytes(range(16)), bytes(range(16, 32))))
        with self.assertRaisesRegex(ProtocolClientError, "expected p6-c3-deadbe"):
            ProtocolSession.authenticate(
                self.socket,
                endpoint="ws://127.0.0.1:8765/ws/v1",
                secret=self.secret,
                expected_device_id="p6-c3-deadbe",
                random_bytes=lambda size: next(values),
            )

    def test_presets_validate_against_frozen_profile(self) -> None:
        scenes = (
            static_scene(RAINBOW, 72),
            rainbow_chase_scene(72),
            pulse_scene((96, 32, 192), 72),
            off_scene(),
        )
        for body in scenes:
            DeviceScene.from_body(body, DEFAULT_CAPABILITIES)

    def test_local_config_and_endpoint_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local-config.json"
            path.write_text(
                json.dumps(
                    {
                        "endpoint": "p6-c3-afb810.local",
                        "expected_device_id": "p6-c3-afb810",
                        "device_secret_b64url": b64url_encode(self.secret),
                    }
                ),
                encoding="utf-8",
            )
            config = load_local_test_config(path)
        self.assertEqual(config.endpoint, "ws://p6-c3-afb810.local:8765/ws/v1")
        self.assertEqual(config.secret, self.secret)
        self.assertEqual(normalize_endpoint("192.168.1.50"), "ws://192.168.1.50:8765/ws/v1")


if __name__ == "__main__":
    unittest.main()