from __future__ import annotations

import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from codex_beacon.packs.agent import AgentObservation, AgentOutcome, AgentTask
from codex_beacon.packs.agent.bridge import AgentEventServer


TOKEN = "a" * 43


class AgentBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.received: list[AgentObservation] = []
        self.server = AgentEventServer(
            port=0,
            bearer_token=TOKEN,
            callback=self.received.append,
        )
        self.server.start()
        self.url = f"http://127.0.0.1:{self.server.port}/v1/events"

    def tearDown(self) -> None:
        self.server.stop()

    def test_accepts_only_authenticated_exact_semantic_events(self) -> None:
        observation = AgentObservation(
            "1" * 32,
            "2" * 32,
            "3" * 32,
            "tool_started",
            AgentTask.TESTING,
            AgentOutcome.UNKNOWN,
            123,
        )
        request = Request(
            self.url,
            data=json.dumps(observation.to_json()).encode(),
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            self.assertEqual(response.status, 202)
        self.assertEqual(self.received, [observation])

        bad = observation.to_json() | {"prompt": "must not cross boundary"}
        request = Request(
            self.url,
            data=json.dumps(bad).encode(),
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)
        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()

    def test_rejects_missing_auth_and_browser_origins(self) -> None:
        body = json.dumps(
            AgentObservation(
                "1" * 32,
                "2" * 32,
                None,
                "turn_started",
                AgentTask.THINKING,
                AgentOutcome.UNKNOWN,
                1,
            ).to_json()
        ).encode()
        for headers, expected in (
            ({"Content-Type": "application/json"}, 401),
            (
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {TOKEN}",
                    "Origin": "https://example.test",
                },
                403,
            ),
        ):
            with self.subTest(expected=expected):
                request = Request(self.url, data=body, headers=headers, method="POST")
                with self.assertRaises(HTTPError) as raised:
                    urlopen(request, timeout=2)
                self.assertEqual(raised.exception.code, expected)
                raised.exception.close()


if __name__ == "__main__":
    unittest.main()
