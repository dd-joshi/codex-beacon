from __future__ import annotations

import json
import socket
import time
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from peri6.companion.presentation import OutputPhase, PresentationState
from peri6.companion.status import (
    NotificationIntent,
    StatusPhase,
    StatusProjector,
)
from peri6.companion.status_server import StatusServer
from peri6.contracts import AttentionClass, RGB
from peri6.packs.registry import AGENT_PACK_ID


TOKEN = "a" * 43
NOW = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
NOW_NS = 1_000_000_000


def waiting_snapshot(observed_at: datetime = NOW):
    state = replace(
        PresentationState.initial(1),
        active_pack_id=AGENT_PACK_ID,
        active_pack_name="Agent",
        active_state_key="agent.waiting",
        headline="Needs approval",
        attention=AttentionClass.ATTENTION,
        detail="The current operation is waiting for a local decision.",
        suggested_action="Approve or reply on your PC.",
        source_observed_at=observed_at,
        output_expires_monotonic_ns=NOW_NS + 60_000_000_000,
        output_accepted_monotonic_ns=1,
        activation_generation=1,
        output_sequence=1,
        output=OutputPhase.ACTIVE,
        semantic_cells=(RGB(255, 154, 90),) * 6,
    )
    return StatusProjector().project(
        state,
        now_monotonic_ns=NOW_NS,
        now_utc=observed_at,
    )


class StatusServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = StatusServer(
            token=TOKEN,
            port=0,
            bind_host="127.0.0.1",
        )
        self.server.start()
        self.server.publish(waiting_snapshot(datetime.now(timezone.utc)))
        self.base = f"http://127.0.0.1:{self.server.port}"

    def tearDown(self) -> None:
        self.server.stop()

    def test_healthz_needs_no_token(self) -> None:
        with urlopen(self.base + "/healthz", timeout=5) as response:
            self.assertEqual(response.status, 204)

    def test_status_requires_the_exact_bearer_token(self) -> None:
        for headers in ({}, {"Authorization": "Bearer wrong"}, {"Authorization": TOKEN}):
            with self.subTest(headers=headers):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(
                        Request(self.base + "/api/status", headers=headers),
                        timeout=5,
                    )
                self.assertEqual(raised.exception.code, 401)
                raised.exception.close()

        request = Request(
            self.base + "/api/status",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        with urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(
                response.headers["Content-Type"],
                "application/json; charset=utf-8",
            )
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload["state_key"], "agent.waiting")
        self.assertEqual(payload["phase"], StatusPhase.LIVE.value)
        self.assertEqual(payload["notify"], "urgent")
        self.assertEqual(payload["headline"], "Needs approval")
        self.assertNotIn("token", json.dumps(payload).lower())

    def test_old_live_snapshot_is_reported_stale(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(seconds=120)
        self.server.publish(waiting_snapshot(old))
        request = Request(
            self.base + "/api/status",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload["phase"], StatusPhase.STALE.value)
        self.assertEqual(payload["notify"], NotificationIntent.NONE.value)
        self.assertGreaterEqual(payload["age_seconds"], 119)

    def test_old_terminal_snapshot_becomes_last_known(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(seconds=30)
        snapshot = replace(
            waiting_snapshot(old),
            state_key="agent.success",
            headline="Checks passed",
            attention=AttentionClass.NORMAL,
            notify=NotificationIntent.CHIME,
        )
        self.server.publish(snapshot)
        request = Request(
            self.base + "/api/status",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload["phase"], StatusPhase.LAST_KNOWN.value)
        self.assertEqual(payload["notify"], NotificationIntent.NONE.value)

    def test_stalled_publisher_marks_even_idle_as_stale(self) -> None:
        idle = replace(
            waiting_snapshot(datetime.now(timezone.utc)),
            state_key="agent.idle",
            headline="Codex is idle",
            attention=AttentionClass.NORMAL,
            notify=NotificationIntent.NONE,
        )
        self.server.publish(idle)
        with self.server._lock:  # noqa: SLF001 - deterministic clock override
            self.server._published_monotonic_ns = (
                time.monotonic_ns() - 31_000_000_000
            )
        request = Request(
            self.base + "/api/status",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload["phase"], StatusPhase.STALE.value)
        self.assertEqual(payload["notify"], NotificationIntent.NONE.value)

    def test_page_and_assets_are_tokenized(self) -> None:
        with urlopen(f"{self.base}/s/{TOKEN}/", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/html", response.headers["Content-Type"])
            html = response.read().decode("utf-8")
        self.assertIn("Peri6", html)

        with urlopen(f"{self.base}/s/{TOKEN}/app.css", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/css", response.headers["Content-Type"])
            self.assertIn("status-card", response.read().decode("utf-8"))

        with urlopen(f"{self.base}/s/{TOKEN}/app.js", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("Bearer", response.read().decode("utf-8"))

        with self.assertRaises(HTTPError) as raised:
            urlopen(f"{self.base}/s/wrong/", timeout=5)
        self.assertEqual(raised.exception.code, 404)
        raised.exception.close()

    def test_page_redirects_to_trailing_slash(self) -> None:
        with urlopen(f"{self.base}/s/{TOKEN}", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertTrue(response.geturl().endswith(f"/s/{TOKEN}/"))

    def test_traversal_is_rejected(self) -> None:
        with self.assertRaises(HTTPError) as raised:
            urlopen(f"{self.base}/s/{TOKEN}/../status_server.py", timeout=5)
        self.assertEqual(raised.exception.code, 404)
        raised.exception.close()

    def test_status_is_503_before_the_first_publish(self) -> None:
        server = StatusServer(token=TOKEN, port=0, bind_host="127.0.0.1")
        server.start()
        try:
            request = Request(
                f"http://127.0.0.1:{server.port}/api/status",
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
            with self.assertRaises(HTTPError) as raised:
                urlopen(request, timeout=5)
            self.assertEqual(raised.exception.code, 503)
            raised.exception.close()
        finally:
            server.stop()

    def test_starting_twice_is_rejected_without_replacing_the_server(self) -> None:
        with self.assertRaises(RuntimeError):
            self.server.start()
        self.assertTrue(self.server.running)
        self.assertEqual(self.server.port, int(self.base.rsplit(":", 1)[1]))

    def test_port_conflict_raises_and_leaves_server_stopped(self) -> None:
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            blocker.bind(("127.0.0.1", 0))
            blocker.listen(1)
            port = int(blocker.getsockname()[1])
            server = StatusServer(
                token=TOKEN,
                port=port,
                bind_host="127.0.0.1",
            )
            try:
                with self.assertRaises(OSError):
                    server.start()
                self.assertFalse(server.running)
            finally:
                server.stop()
        finally:
            blocker.close()

    def test_web_assets_are_present(self) -> None:
        web = Path(__file__).resolve().parents[1] / "src" / "peri6" / "companion" / "web"
        for name in (
            "index.html",
            "app.css",
            "app.js",
            "manifest.webmanifest",
            "icon.svg",
        ):
            with self.subTest(name=name):
                self.assertTrue((web / name).is_file())


if __name__ == "__main__":
    unittest.main()
