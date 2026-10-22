"""Authenticated loopback bridge owned only by an active Agent pack."""

from __future__ import annotations

import hmac
import json
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from .events import AgentObservation


MAX_BODY_BYTES = 8_192
MAX_EVENTS_PER_SECOND = 24


class AgentEventServer:
    """A deliberately small HTTP server bound to IPv4 loopback only."""

    def __init__(
        self,
        *,
        port: int,
        bearer_token: str,
        callback: Callable[[AgentObservation], None],
        control_callback: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError("Agent listen port must be between 0 and 65535")
        if not isinstance(bearer_token, str) or len(bearer_token) < 32:
            raise ValueError("Agent bearer token is too short")
        if not callable(callback):
            raise TypeError("Agent event callback must be callable")
        self._token = bearer_token
        self._callback = callback
        self._control_callback = control_callback
        self._rate_lock = threading.Lock()
        self._recent: deque[float] = deque()
        owner = self

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        class Handler(BaseHTTPRequestHandler):
            server_version = "Peri6Agent/1"
            sys_version = ""

            def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
                owner._handle_post(self)

            def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
                if self.path == "/v1/health":
                    owner._respond(self, 204)
                else:
                    owner._respond(self, 404)

            def log_message(self, _format: str, *args: object) -> None:
                return

        self._server = Server(("127.0.0.1", port), Handler)
        self._server.timeout = 0.1
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={"poll_interval": 0.1},
            name="peri6-agent-loopback",
            daemon=True,
        )

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        if self._thread.is_alive():
            self._server.shutdown()
            self._thread.join(timeout=1.0)
        self._server.server_close()

    def _handle_post(self, handler: BaseHTTPRequestHandler) -> None:
        if handler.path not in {"/v1/events", "/v1/control"}:
            self._respond(handler, 404)
            return
        is_control = handler.path == "/v1/control"
        if handler.headers.get("Origin") is not None:
            self._respond(handler, 403)
            return
        authorization = handler.headers.get("Authorization", "")
        expected = f"Bearer {self._token}"
        if not hmac.compare_digest(authorization, expected):
            self._respond(handler, 401)
            return
        if not self._rate_allowed():
            self._respond(handler, 429)
            return
        content_type = handler.headers.get_content_type()
        if content_type != "application/json":
            self._respond(handler, 415)
            return
        raw_length = handler.headers.get("Content-Length")
        try:
            length = int(raw_length or "")
        except ValueError:
            self._respond(handler, 400)
            return
        if not 1 <= length <= MAX_BODY_BYTES:
            self._respond(handler, 413)
            return
        try:
            body = handler.rfile.read(length)
            value = json.loads(body.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Agent event must be an object")
            if is_control:
                self._handle_control(value)
            else:
                observation = AgentObservation.from_json(value)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._respond(handler, 400)
            return
        try:
            if is_control:
                pass  # handled synchronously above
            else:
                self._callback(observation)  # type: ignore[possibly-undefined]
        except Exception:
            self._respond(handler, 503)
            return
        self._respond(handler, 202)

    def _handle_control(self, value: dict[str, object]) -> None:
        callback = self._control_callback
        if callback is None:
            raise ValueError("control channel is disabled")
        callback(value)

    def _rate_allowed(self) -> bool:
        now = time.monotonic()
        with self._rate_lock:
            while self._recent and self._recent[0] <= now - 1.0:
                self._recent.popleft()
            if len(self._recent) >= MAX_EVENTS_PER_SECOND:
                return False
            self._recent.append(now)
            return True

    @staticmethod
    def _respond(handler: BaseHTTPRequestHandler, status: int) -> None:
        handler.send_response(status)
        handler.send_header("Content-Length", "0")
        handler.end_headers()


__all__ = ["AgentEventServer", "MAX_BODY_BYTES"]
