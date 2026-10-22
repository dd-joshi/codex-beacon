"""Tkinter console for authenticated testing of one physical Peri6 device."""

from __future__ import annotations

import argparse
import json
import queue
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from peri6.tester.config import default_config_path, load_local_test_config
from peri6.tester.presets import RAINBOW, off_scene, pulse_scene, rainbow_chase_scene, static_scene
from peri6.transport.client import ClientEvent, HardwareClient, ProtocolClientError


DEFAULT_ENDPOINT = "ws://p6-c3-afb810.local:8765/ws/v1"


class HardwareTestApp:
    def __init__(self, root: tk.Tk, config_path: Path, endpoint_override: str | None) -> None:
        self.root = root
        self.root.title("Peri6 ESP32-C3 Hardware Test")
        self.root.minsize(780, 650)
        self.config_path = config_path
        self.events: queue.SimpleQueue[ClientEvent] = queue.SimpleQueue()
        self.client = HardwareClient(self.events.put)
        self.colors: list[tuple[int, int, int]] = list(RAINBOW)
        self.action_widgets: list[tk.Widget] = []

        self.endpoint = tk.StringVar(value=endpoint_override or DEFAULT_ENDPOINT)
        self.state = tk.StringVar(value="Not connected")
        self.brightness = tk.IntVar(value=72)
        self.config_label = tk.StringVar(value=str(config_path))

        self._build()
        self._try_prefill_config(endpoint_override)
        self._paint_cells()
        self._set_connected(False)
        self.root.after(75, self._poll_events)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        connection = ttk.LabelFrame(outer, text="Device connection", padding=10)
        connection.grid(row=0, column=0, sticky="ew")
        connection.columnconfigure(1, weight=1)
        ttk.Label(connection, text="Local config").grid(row=0, column=0, sticky="w")
        ttk.Entry(connection, textvariable=self.config_label, state="readonly").grid(
            row=0, column=1, columnspan=2, sticky="ew", padx=(8, 4)
        )
        ttk.Button(connection, text="Browse…", command=self._browse_config).grid(row=0, column=3)
        ttk.Label(connection, text="Endpoint").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.endpoint_entry = ttk.Entry(connection, textvariable=self.endpoint)
        self.endpoint_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(8, 0))
        self.connect_button = ttk.Button(connection, text="Connect", command=self._connect)
        self.connect_button.grid(row=1, column=2, pady=(8, 0))
        self.disconnect_button = ttk.Button(connection, text="Disconnect", command=self._disconnect)
        self.disconnect_button.grid(row=1, column=3, padx=(4, 0), pady=(8, 0))
        ttk.Label(connection, textvariable=self.state).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )

        cells = ttk.LabelFrame(outer, text="Six cells — click to choose RGB", padding=10)
        cells.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.cell_buttons: list[tk.Button] = []
        for index in range(6):
            button = tk.Button(
                cells,
                text=f"Cell {index + 1}",
                width=10,
                height=3,
                relief="raised",
                command=lambda cell=index: self._choose_cell(cell),
            )
            button.grid(row=0, column=index, padx=4, sticky="ew")
            cells.columnconfigure(index, weight=1)
            self.cell_buttons.append(button)
        ttk.Label(cells, text="Brightness limit (0–96)").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        ttk.Scale(
            cells, from_=0, to=96, orient="horizontal", variable=self.brightness,
            command=lambda value: self.brightness.set(round(float(value))),
        ).grid(row=1, column=2, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Label(cells, textvariable=self.brightness, width=4).grid(row=1, column=5, pady=(10, 0))

        actions = ttk.LabelFrame(outer, text="Generic renderer tests", padding=10)
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        definitions = [
            ("Send static", self._send_static),
            ("One-color solid…", self._send_solid),
            ("Rainbow static", self._send_rainbow),
            ("Rainbow chase", self._send_chase),
            ("Pulse cell-1 color", self._send_pulse),
            ("Off", self._send_off),
            ("Clear active", self._clear),
            ("Status", self._status),
        ]
        for index, (label, callback) in enumerate(definitions):
            widget = ttk.Button(actions, text=label, command=callback)
            widget.grid(row=index // 4, column=index % 4, padx=4, pady=4, sticky="ew")
            actions.columnconfigure(index % 4, weight=1)
            self.action_widgets.append(widget)

        log_frame = ttk.LabelFrame(outer, text="Authenticated protocol log", padding=8)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=15, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._write_log("Ready. The device secret is loaded locally and is never displayed.")

    def _try_prefill_config(self, endpoint_override: str | None) -> None:
        try:
            config = load_local_test_config(self.config_path)
        except ProtocolClientError:
            return
        if endpoint_override is None:
            self.endpoint.set(config.endpoint)

    def _browse_config(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select ignored Peri6 local config",
            initialdir=str(self.config_path.parent),
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.config_path = Path(selected)
            self.config_label.set(selected)
            self._try_prefill_config(None)

    def _connect(self) -> None:
        try:
            config = load_local_test_config(self.config_path)
            endpoint = self.endpoint.get().strip() or config.endpoint
            self.client.connect(endpoint, config.secret, config.expected_device_id)
        except ProtocolClientError as exc:
            messagebox.showerror("Peri6 connection", str(exc), parent=self.root)
            return
        self.state.set("Connecting…")
        self.connect_button.configure(state="disabled")
        self.endpoint_entry.configure(state="disabled")

    def _disconnect(self) -> None:
        self.client.disconnect()

    def _choose_cell(self, index: int) -> None:
        current = "#%02x%02x%02x" % self.colors[index]
        chosen = colorchooser.askcolor(current, title=f"Cell {index + 1} color", parent=self.root)[0]
        if chosen is not None:
            self.colors[index] = tuple(round(channel) for channel in chosen)  # type: ignore[assignment]
            self._paint_cells()

    def _paint_cells(self) -> None:
        for button, color in zip(self.cell_buttons, self.colors):
            value = "#%02x%02x%02x" % color
            luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
            foreground = "black" if luminance > 145 else "white"
            button.configure(bg=value, activebackground=value, fg=foreground, activeforeground=foreground)

    def _send(self, scene: dict[str, object], label: str) -> None:
        self.client.load_scene(scene)
        self._write_log(f"Queued {label}; auto-keepalive will run every second after ACK.")

    def _send_static(self) -> None:
        self._send(static_scene(self.colors, self.brightness.get()), "static scene")

    def _send_solid(self) -> None:
        chosen = colorchooser.askcolor("#6030c0", title="Solid color", parent=self.root)[0]
        if chosen is None:
            return
        color = tuple(round(channel) for channel in chosen)
        self.colors = [color] * 6  # type: ignore[list-item]
        self._paint_cells()
        self._send_static()

    def _send_rainbow(self) -> None:
        self.colors = list(RAINBOW)
        self._paint_cells()
        self._send_static()

    def _send_chase(self) -> None:
        self._send(rainbow_chase_scene(self.brightness.get()), "rainbow chase")

    def _send_pulse(self) -> None:
        color = self.colors[0] if self.colors[0] != (0, 0, 0) else (96, 32, 192)
        self._send(pulse_scene(color, self.brightness.get()), "pulse")

    def _send_off(self) -> None:
        self._send(off_scene(), "all-off scene")

    def _clear(self) -> None:
        self.client.clear()

    def _status(self) -> None:
        self.client.status()

    def _set_connected(self, connected: bool) -> None:
        state = "normal" if connected else "disabled"
        for widget in self.action_widgets:
            widget.configure(state=state)
        self.disconnect_button.configure(state="normal" if connected else "disabled")
        if not connected:
            self.connect_button.configure(state="normal")
            self.endpoint_entry.configure(state="normal")

    def _poll_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self._write_log(event.message, event.body)
            if event.kind == "connected":
                self.state.set(event.message)
                self._set_connected(True)
            elif event.kind == "disconnected":
                self.state.set("Not connected")
                self._set_connected(False)
            elif event.kind == "error":
                self.state.set("Connection error")
        self.root.after(75, self._poll_events)

    def _write_log(self, message: str, body: object | None = None) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        text = f"[{stamp}] {message}\n"
        if body is not None:
            text += json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n"
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _close(self) -> None:
        self.client.disconnect()
        self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Peri6 physical hardware test console")
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--endpoint", help="Override hostname/IP or ws:// endpoint")
    arguments = parser.parse_args()
    root = tk.Tk()
    HardwareTestApp(root, arguments.config.resolve(), arguments.endpoint)
    root.mainloop()


if __name__ == "__main__":
    main()