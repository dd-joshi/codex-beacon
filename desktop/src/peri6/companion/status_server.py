"""Small authenticated HTTP server for the Peri6 phone status page."""

from __future__ import annotations

import hmac
import json
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from peri6.companion.status import (
    NotificationIntent,
    StatusPhase,
    StatusSnapshot,
    freshen_snapshot,
)


PUBLISH_STALE_AFTER_SECONDS = 30.0


_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".json": "application/json; charset=utf-8",
}
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "connect-src 'self'; "
        "img-src 'self' data:; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "frame-ancestors 'none'"
    ),
}


class StatusServer:
    """Serve the phone page and a read-only status API on the local network."""

    def __init__(
        self,
        *,
        token: str,
        port: int,
        bind_host: str = "0.0.0.0",
        page_directory: Path | None = None,
    ) -> None:
        if not isinstance(token, str) or len(token) < 32:
            raise ValueError("Phone status token is too short")
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError("Phone status port must be between 0 and 65535")
        if not isinstance(bind_host, str) or not bind_host:
            raise ValueError("Phone status bind host must be a non-empty string")
        self._token = token
        self._bind_host = bind_host
        self._page_directory = (
            page_directory
            if page_directory is not None
            else Path(__file__).with_name("web")
        ).resolve()
        self._lock = threading.Lock()
        self._snapshot: StatusSnapshot | None = None
        self._published_monotonic_ns: int | None = None
        self._thread: threading.Thread | None = None
        self._httpd: ThreadingHTTPServer | None = None
        owner = self

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        class Handler(BaseHTTPRequestHandler):
            server_version = "Peri6Status/1"
            sys_version = ""

            def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
                owner._handle_get(self)

            def log_message(self, _format: str, *args: object) -> None:
                return

        self._server_class = Server
        self._handler_class = Handler
        self._requested_port = port

    @property
    def token(self) -> str:
        return self._token

    @property
    def port(self) -> int:
        httpd = self._httpd
        if httpd is None:
            return self._requested_port
        return int(httpd.server_address[1])

    @property
    def running(self) -> bool:
        return self._httpd is not None and self._thread is not None

    def start(self) -> None:
        if self._httpd is not None:
            raise RuntimeError("Phone status server is already running")
        httpd = self._server_class(
            (self._bind_host, self._requested_port),
            self._handler_class,
        )
        httpd.timeout = 0.1
        self._httpd = httpd
        self._thread = threading.Thread(
            target=httpd.serve_forever,
            kwargs={"poll_interval": 0.1},
            name="peri6-phone-status",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        httpd = self._httpd
        thread = self._thread
        self._httpd = None
        self._thread = None
        if httpd is None:
            return
        httpd.shutdown()
        httpd.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def publish(self, snapshot: StatusSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot
            self._published_monotonic_ns = time.monotonic_ns()

    def _handle_get(self, handler: BaseHTTPRequestHandler) -> None:
        path = handler.path.split("?", 1)[0]
        if path == "/healthz":
            self._send(handler, 204, b"", None)
            return
        if path == "/api/status":
            self._handle_status(handler)
            return
        if path == "/":
            self._send(
                handler,
                200,
                b"Open the phone status URL shown in Peri6.\n",
                "text/plain; charset=utf-8",
            )
            return
        if path.startswith("/s/"):
            self._handle_page(handler, path)
            return
        self._send(handler, 404, b"Not found\n", "text/plain; charset=utf-8")

    def _handle_status(self, handler: BaseHTTPRequestHandler) -> None:
        authorization = handler.headers.get("Authorization", "")
        expected = f"Bearer {self._token}"
        if not hmac.compare_digest(authorization, expected):
            self._send(handler, 401, b"Unauthorized\n", "text/plain; charset=utf-8")
            return
        with self._lock:
            snapshot = self._snapshot
            published_monotonic_ns = self._published_monotonic_ns
        if snapshot is None:
            self._send(
                handler,
                503,
                b'{"error":"status-not-ready"}',
                "application/json; charset=utf-8",
            )
            return
        current = freshen_snapshot(snapshot)
        publisher_stale = False
        if published_monotonic_ns is not None:
            publisher_age = (
                time.monotonic_ns() - published_monotonic_ns
            ) / 1_000_000_000
            publisher_stale = publisher_age > PUBLISH_STALE_AFTER_SECONDS
        if current.phase is StatusPhase.LIVE and publisher_stale:
            current = replace(
                current,
                phase=StatusPhase.STALE,
                notify=NotificationIntent.NONE,
            )
        payload = json.dumps(
            current.to_json(),
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        self._send(handler, 200, payload, "application/json; charset=utf-8")

    def _handle_page(self, handler: BaseHTTPRequestHandler, path: str) -> None:
        parts = path.split("/")
        # ["", "s", token, ...asset]
        if len(parts) < 3:
            self._send(handler, 404, b"Not found\n", "text/plain; charset=utf-8")
            return
        token = parts[2]
        if not hmac.compare_digest(token, self._token):
            self._send(handler, 404, b"Not found\n", "text/plain; charset=utf-8")
            return
        if len(parts) == 3:
            target = "/s/" + token + "/"
            self._send_redirect(handler, target)
            return
        asset = "/".join(parts[3:])
        if not asset:
            asset = "index.html"
        try:
            relative = Path(asset)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError
            candidate = (self._page_directory / relative).resolve()
            candidate.relative_to(self._page_directory)
        except (OSError, ValueError):
            self._send(handler, 404, b"Not found\n", "text/plain; charset=utf-8")
            return
        if not candidate.is_file():
            self._send(handler, 404, b"Not found\n", "text/plain; charset=utf-8")
            return
        content_type = _CONTENT_TYPES.get(
            candidate.suffix.lower(), "application/octet-stream"
        )
        try:
            body = candidate.read_bytes()
        except OSError:
            self._send(handler, 500, b"Could not read page asset\n", "text/plain; charset=utf-8")
            return
        self._send(handler, 200, body, content_type)

    @staticmethod
    def _send_redirect(handler: BaseHTTPRequestHandler, location: str) -> None:
        handler.send_response(301)
        handler.send_header("Location", location)
        handler.send_header("Content-Length", "0")
        for name, value in _SECURITY_HEADERS.items():
            handler.send_header(name, value)
        handler.end_headers()

    @staticmethod
    def _send(
        handler: BaseHTTPRequestHandler,
        status: int,
        body: bytes,
        content_type: str | None,
    ) -> None:
        handler.send_response(status)
        if content_type is not None:
            handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(body)))
        for name, value in _SECURITY_HEADERS.items():
            handler.send_header(name, value)
        handler.end_headers()
        if body:
            handler.wfile.write(body)


__all__ = ["StatusServer"]
