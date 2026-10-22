from __future__ import annotations

import json
import threading
import time
import unittest
from collections import deque
from dataclasses import replace
from unittest import mock

from websocket import WebSocketConnectionClosedException, WebSocketTimeoutException

from peri6.protocol.crypto import b64url_decode
from peri6.protocol.model import Capabilities, DeviceScene
from peri6.tester.presets import RAINBOW, static_scene
from peri6.testing.device_simulator import DeviceSimulator
from peri6.transport import DeviceEvent, DeviceManager, ProtocolSession
from peri6.transport import device_manager as manager_module


class _ManagerWebSocket:
    def __init__(
        self,
        simulator: DeviceSimulator,
        *,
        hold_load: bool = False,
        hold_keepalive: bool = False,
    ) -> None:
        self.simulator = simulator
        self.hold_load = hold_load
        self.hold_keepalive = hold_keepalive
        self.timeout = 0.05
        self.closed = False
        self.hello: dict[str, object] | None = None
        self.commands: list[tuple[str, dict[str, object]]] = []
        self._responses: deque[str] = deque()
        self._held_load_responses: deque[str] = deque()
        self._held_keepalive_responses: deque[str] = deque()
        self._condition = threading.Condition()

    def getsubprotocol(self) -> str:
        return "peri6.scene.v1"

    def send(self, payload: str) -> None:
        message = json.loads(payload)
        with self._condition:
            if self.closed:
                raise WebSocketConnectionClosedException("socket is closed")
            if message.get("type") == "HELLO":
                self.hello = message
                response = self.simulator.begin_handshake(message)
                self._responses.append(json.dumps(response, separators=(",", ":")))
            elif message.get("type") == "AUTH":
                authenticated, capabilities = self.simulator.finish_handshake(message)
                self._responses.extend(
                    json.dumps(response, separators=(",", ":"))
                    for response in (authenticated, capabilities)
                )
            else:
                message_type = message["type"]
                body = json.loads(b64url_decode(message["body"]).decode("utf-8"))
                self.commands.append((message_type, body))
                response = json.dumps(
                    self.simulator.handle_text(payload), separators=(",", ":")
                )
                if message_type == "LOAD_SCENE" and self.hold_load:
                    self._held_load_responses.append(response)
                elif message_type == "KEEPALIVE" and self.hold_keepalive:
                    self._held_keepalive_responses.append(response)
                    self.hold_keepalive = False
                else:
                    self._responses.append(response)
            self._condition.notify_all()

    def recv(self) -> str:
        with self._condition:
            if not self._responses and not self.closed:
                self._condition.wait(self.timeout)
            if self.closed:
                raise WebSocketConnectionClosedException("socket is closed")
            if self._responses:
                return self._responses.popleft()
        raise WebSocketTimeoutException("timed out")

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def close(self) -> None:
        with self._condition:
            self.closed = True
            self._condition.notify_all()

    def force_close(self) -> None:
        self.close()

    def release_load_response(self) -> None:
        with self._condition:
            self._responses.extend(self._held_load_responses)
            self._held_load_responses.clear()
            self._condition.notify_all()

    def release_keepalive_response(self) -> None:
        with self._condition:
            self._responses.extend(self._held_keepalive_responses)
            self._held_keepalive_responses.clear()
            self._condition.notify_all()

    def emit_button(self, *, event_id: str) -> None:
        with self._condition:
            response = self.simulator.emit_button(
                event_id=event_id, gesture="tap", duration_ms=120
            )
            self._responses.append(json.dumps(response, separators=(",", ":")))
            self._condition.notify_all()

    def wait_for_command(self, message_type: str, timeout: float = 2.0) -> dict[str, object]:
        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                for recorded_type, body in self.commands:
                    if recorded_type == message_type:
                        return body
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError(f"timed out waiting for {message_type}")
                self._condition.wait(remaining)

    def command_types(self) -> list[str]:
        with self._condition:
            return [message_type for message_type, _ in self.commands]


class _Connector:
    def __init__(
        self,
        simulator: DeviceSimulator,
        *,
        hold_first_load: bool = False,
        hold_first_keepalive: bool = False,
    ) -> None:
        self.simulator = simulator
        self.hold_first_load = hold_first_load
        self.hold_first_keepalive = hold_first_keepalive
        self.sockets: list[_ManagerWebSocket] = []
        self._condition = threading.Condition()

    def __call__(self, *args, **kwargs) -> _ManagerWebSocket:
        with self._condition:
            socket = _ManagerWebSocket(
                self.simulator,
                hold_load=self.hold_first_load and not self.sockets,
                hold_keepalive=self.hold_first_keepalive and not self.sockets,
            )
            self.sockets.append(socket)
            self._condition.notify_all()
            return socket

    def wait_for_socket(self, count: int, timeout: float = 2.0) -> _ManagerWebSocket:
        deadline = time.monotonic() + timeout
        with self._condition:
            while len(self.sockets) < count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError(f"timed out waiting for socket {count}")
                self._condition.wait(remaining)
            return self.sockets[count - 1]


class _EventLog:
    def __init__(self) -> None:
        self.events: list[DeviceEvent] = []
        self._condition = threading.Condition()

    def __call__(self, event: DeviceEvent) -> None:
        with self._condition:
            self.events.append(event)
            self._condition.notify_all()

    def wait_for(self, kind: str, count: int = 1, timeout: float = 2.0) -> DeviceEvent:
        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                matches = [event for event in self.events if event.kind == kind]
                if len(matches) >= count:
                    return matches[count - 1]
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError(f"timed out waiting for event {kind} #{count}")
                self._condition.wait(remaining)

    def count(self, kind: str) -> int:
        with self._condition:
            return sum(event.kind == kind for event in self.events)


class DeviceManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = bytes(range(32))
        self.device = DeviceSimulator(secret=self.secret, device_id="p6-c3-afb810")
        self.scene = DeviceScene.from_body(static_scene(RAINBOW, 72))
        self.endpoint = "ws://p6-c3-afb810.local:8765/ws/v1"

    def manager_patch(self, connector: _Connector):
        return mock.patch.multiple(
            manager_module,
            create_connection=connector,
            SOCKET_POLL_SECONDS=0.01,
            RESPONSE_TIMEOUT_SECONDS=0.5,
            RECONNECT_DELAYS_SECONDS=(0.01,),
            AUTH_FAILURE_DELAY_SECONDS=0.01,
        )

    def test_fresh_scene_uses_new_id_deduplicates_button_and_clears(self) -> None:
        connector = _Connector(self.device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene, generation=7, valid_until_monotonic_ns=time.monotonic_ns() + 3_000_000_000
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                loaded = events.wait_for("scene_loaded")
                socket = connector.wait_for_socket(1)
                load_body = socket.wait_for_command("LOAD_SCENE")
                self.assertEqual(socket.hello["client_name"], "Peri6 Desktop")
                self.assertEqual(socket.hello["client_version"], "0.1.0")
                self.assertNotEqual(load_body["scene_id"], self.scene.scene_id)
                self.assertEqual(loaded.body["scene_id"], load_body["scene_id"])

                event_id = "ab" * 16
                socket.emit_button(event_id=event_id)
                socket.emit_button(event_id=event_id)
                button = events.wait_for("button")
                time.sleep(0.05)
                self.assertEqual(button.generation, 7)
                self.assertEqual(events.count("button"), 1)

                manager.set_desired_scene(None, generation=7, valid_until_monotonic_ns=None)
                cleared = events.wait_for("scene_cleared")
                self.assertEqual(cleared.body["scene_id"], load_body["scene_id"])
            finally:
                manager.disconnect()

    def test_neutral_resync_clears_status_scene_without_keepalive(self) -> None:
        bootstrap = _ManagerWebSocket(self.device)
        session = ProtocolSession.authenticate(
            bootstrap,
            endpoint=self.endpoint,
            secret=self.secret,
            expected_device_id="p6-c3-afb810",
        )
        session.send_command("LOAD_SCENE", self.scene.to_body())
        session.receive()
        bootstrap.close()

        connector = _Connector(self.device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(None, generation=1, valid_until_monotonic_ns=None)
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                events.wait_for("scene_cleared")
                socket = connector.wait_for_socket(1)
                types = [message_type for message_type, _ in socket.commands]
                self.assertEqual(types[:2], ["STATUS", "CLEAR"])
                self.assertNotIn("KEEPALIVE", types)
            finally:
                manager.disconnect()

    def test_stale_load_ack_is_not_adopted_and_is_cleared(self) -> None:
        connector = _Connector(self.device, hold_first_load=True)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene, generation=2, valid_until_monotonic_ns=time.monotonic_ns() + 3_000_000_000
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                socket = connector.wait_for_socket(1)
                load = socket.wait_for_command("LOAD_SCENE")
                manager.set_desired_scene(None, generation=2, valid_until_monotonic_ns=None)
                socket.release_load_response()
                warning = events.wait_for("warning")
                cleared = events.wait_for("scene_cleared")
                self.assertIn("Stale LOAD", warning.message)
                self.assertEqual(cleared.body["scene_id"], load["scene_id"])
                self.assertEqual(events.count("scene_loaded"), 0)
            finally:
                manager.disconnect()

    def test_ready_response_is_drained_at_timeout_threshold(self) -> None:
        connector = _Connector(self.device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=2,
            valid_until_monotonic_ns=time.monotonic_ns() + 2_000_000_000,
        )
        with self.manager_patch(connector), mock.patch.object(
            manager_module, "RESPONSE_TIMEOUT_SECONDS", 0.0
        ):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                events.wait_for("scene_loaded")
                time.sleep(0.05)
                self.assertEqual(events.count("error"), 0)
                self.assertEqual(len(connector.sockets), 1)
            finally:
                manager.disconnect()

    def test_timeout_identifies_command_without_scene_content(self) -> None:
        connector = _Connector(self.device, hold_first_load=True)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=2,
            valid_until_monotonic_ns=time.monotonic_ns() + 3_000_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                socket = connector.wait_for_socket(1)
                load = socket.wait_for_command("LOAD_SCENE")
                error = events.wait_for("error", timeout=1.5)

                self.assertRegex(
                    error.message,
                    r"^Device response timed out waiting for LOAD_SCENE "
                    r"\(seq 2, age \d+ ms\)\.$",
                )
                self.assertNotIn(str(load["scene_id"]), error.message)
                self.assertNotIn(self.secret.hex(), error.message)
            finally:
                manager.disconnect()

    def test_equivalent_refresh_does_not_stale_an_inflight_load(self) -> None:
        connector = _Connector(self.device, hold_first_load=True)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=3,
            valid_until_monotonic_ns=time.monotonic_ns() + 2_000_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                socket = connector.wait_for_socket(1)
                socket.wait_for_command("LOAD_SCENE")
                equivalent = replace(
                    self.scene,
                    scene_id="zBEiM0RVZneImaq7zN3u_w",
                )
                manager.set_desired_scene(
                    equivalent,
                    generation=3,
                    valid_until_monotonic_ns=time.monotonic_ns() + 3_000_000_000,
                )
                socket.release_load_response()

                loaded = events.wait_for("scene_loaded")
                time.sleep(0.05)
                self.assertEqual(loaded.generation, 3)
                self.assertEqual(socket.command_types().count("LOAD_SCENE"), 1)
                self.assertEqual(events.count("warning"), 0)
            finally:
                manager.disconnect()

    def test_equivalent_refresh_does_not_stale_an_inflight_keepalive(self) -> None:
        device = DeviceSimulator(
            secret=self.secret,
            device_id="p6-c3-afb810",
            capabilities=Capabilities(keepalive_interval_ms=100),
        )
        connector = _Connector(device, hold_first_keepalive=True)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=4,
            valid_until_monotonic_ns=time.monotonic_ns() + 2_000_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                events.wait_for("scene_loaded")
                socket = connector.wait_for_socket(1)
                socket.wait_for_command("KEEPALIVE")
                manager.set_desired_scene(
                    replace(self.scene, scene_id="zBEiM0RVZneImaq7zN3u_w"),
                    generation=4,
                    valid_until_monotonic_ns=time.monotonic_ns() + 3_000_000_000,
                )

                time.sleep(0.05)
                self.assertEqual(socket.command_types().count("LOAD_SCENE"), 1)
                socket.release_keepalive_response()
                time.sleep(0.15)
                self.assertEqual(socket.command_types().count("LOAD_SCENE"), 1)
                self.assertEqual(events.count("disconnected"), 0)
            finally:
                manager.disconnect()

    def test_equivalent_refresh_extends_freshness_without_reloading(self) -> None:
        device = DeviceSimulator(
            secret=self.secret,
            device_id="p6-c3-afb810",
            capabilities=Capabilities(keepalive_interval_ms=100),
        )
        connector = _Connector(device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=5,
            valid_until_monotonic_ns=time.monotonic_ns() + 300_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                events.wait_for("scene_loaded")
                socket = connector.wait_for_socket(1)
                equivalent = replace(
                    self.scene,
                    scene_id="zBEiM0RVZneImaq7zN3u_w",
                )
                manager.set_desired_scene(
                    equivalent,
                    generation=5,
                    valid_until_monotonic_ns=time.monotonic_ns() + 1_000_000_000,
                )

                time.sleep(0.4)
                types = socket.command_types()
                self.assertEqual(types.count("LOAD_SCENE"), 1)
                self.assertGreaterEqual(types.count("KEEPALIVE"), 1)
                self.assertNotIn("CLEAR", types)
                self.assertEqual(events.count("scene_loaded"), 1)
            finally:
                manager.disconnect()

    def test_equivalent_refresh_honors_a_shorter_expiry(self) -> None:
        connector = _Connector(self.device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=5,
            valid_until_monotonic_ns=time.monotonic_ns() + 2_000_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                loaded = events.wait_for("scene_loaded")
                socket = connector.wait_for_socket(1)
                manager.set_desired_scene(
                    replace(self.scene, scene_id="zBEiM0RVZneImaq7zN3u_w"),
                    generation=5,
                    valid_until_monotonic_ns=time.monotonic_ns() + 200_000_000,
                )

                cleared = events.wait_for("scene_cleared", timeout=1.0)
                self.assertEqual(cleared.body["scene_id"], loaded.body["scene_id"])
                self.assertEqual(socket.command_types().count("LOAD_SCENE"), 1)
            finally:
                manager.disconnect()

    def test_equivalent_scene_after_expiry_uses_a_new_load(self) -> None:
        connector = _Connector(self.device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=5,
            valid_until_monotonic_ns=time.monotonic_ns() + 200_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                first = events.wait_for("scene_loaded", 1)
                events.wait_for("scene_cleared")
                socket = connector.wait_for_socket(1)
                manager.set_desired_scene(
                    replace(self.scene, scene_id="zBEiM0RVZneImaq7zN3u_w"),
                    generation=5,
                    valid_until_monotonic_ns=time.monotonic_ns() + 2_000_000_000,
                )

                second = events.wait_for("scene_loaded", 2)
                self.assertNotEqual(first.body["scene_id"], second.body["scene_id"])
                self.assertEqual(socket.command_types().count("LOAD_SCENE"), 2)
            finally:
                manager.disconnect()

    def test_changed_rendered_scene_still_reloads(self) -> None:
        connector = _Connector(self.device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=6,
            valid_until_monotonic_ns=time.monotonic_ns() + 3_000_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                events.wait_for("scene_loaded", 1)
                socket = connector.wait_for_socket(1)
                manager.set_desired_scene(
                    replace(self.scene, brightness=self.scene.brightness - 1),
                    generation=6,
                    valid_until_monotonic_ns=time.monotonic_ns() + 3_000_000_000,
                )

                events.wait_for("scene_loaded", 2)
                self.assertEqual(socket.command_types().count("LOAD_SCENE"), 2)
            finally:
                manager.disconnect()

    def test_equivalent_scene_in_a_new_generation_reloads(self) -> None:
        connector = _Connector(self.device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=10,
            valid_until_monotonic_ns=time.monotonic_ns() + 3_000_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                events.wait_for("scene_loaded", 1)
                socket = connector.wait_for_socket(1)
                manager.set_desired_scene(
                    replace(self.scene, scene_id="zBEiM0RVZneImaq7zN3u_w"),
                    generation=11,
                    valid_until_monotonic_ns=time.monotonic_ns() + 3_000_000_000,
                )

                second = events.wait_for("scene_loaded", 2)
                self.assertEqual(second.generation, 11)
                self.assertEqual(socket.command_types().count("LOAD_SCENE"), 2)
            finally:
                manager.disconnect()

    def test_reconnect_resyncs_with_another_fresh_scene_id(self) -> None:
        connector = _Connector(self.device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene, generation=4, valid_until_monotonic_ns=time.monotonic_ns() + 4_000_000_000
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                first = events.wait_for("scene_loaded", 1)
                connector.wait_for_socket(1).force_close()
                second = events.wait_for("scene_loaded", 2)
                connector.wait_for_socket(2)
                self.assertNotEqual(first.body["scene_id"], second.body["scene_id"])
                self.assertNotEqual(second.body["scene_id"], self.scene.scene_id)
            finally:
                manager.disconnect()

    def test_expiry_stops_keepalive_and_clears_without_neutral_dispatch(self) -> None:
        device = DeviceSimulator(
            secret=self.secret,
            device_id="p6-c3-afb810",
            capabilities=Capabilities(keepalive_interval_ms=100),
        )
        connector = _Connector(device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=8,
            valid_until_monotonic_ns=time.monotonic_ns() + 500_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                loaded = events.wait_for("scene_loaded")
                cleared = events.wait_for("scene_cleared")
                socket = connector.wait_for_socket(1)
                types_at_clear = socket.command_types()
                self.assertIn("KEEPALIVE", types_at_clear)
                self.assertIn("CLEAR", types_at_clear)
                self.assertEqual(cleared.body["scene_id"], loaded.body["scene_id"])
                keepalives_at_clear = types_at_clear.count("KEEPALIVE")
                time.sleep(0.2)
                types_after_wait = socket.command_types()
                self.assertEqual(types_after_wait.count("KEEPALIVE"), keepalives_at_clear)
                self.assertEqual(types_after_wait.count("CLEAR"), 1)
            finally:
                manager.disconnect()

    def test_lower_generation_update_is_ignored(self) -> None:
        device = DeviceSimulator(
            secret=self.secret,
            device_id="p6-c3-afb810",
            capabilities=Capabilities(keepalive_interval_ms=100),
        )
        connector = _Connector(device)
        events = _EventLog()
        manager = DeviceManager(events)
        manager.set_desired_scene(
            self.scene,
            generation=9,
            valid_until_monotonic_ns=time.monotonic_ns() + 2_000_000_000,
        )
        with self.manager_patch(connector):
            manager.connect(self.endpoint, self.secret, "p6-c3-afb810")
            try:
                loaded = events.wait_for("scene_loaded")
                manager.set_desired_scene(
                    None, generation=8, valid_until_monotonic_ns=None
                )
                time.sleep(0.25)
                socket = connector.wait_for_socket(1)
                types = socket.command_types()
                self.assertEqual(loaded.generation, 9)
                self.assertIn("KEEPALIVE", types)
                self.assertNotIn("CLEAR", types)
                self.assertEqual(events.count("scene_cleared"), 0)
            finally:
                manager.disconnect()


if __name__ == "__main__":
    unittest.main()
