"""Compact first-party Windows companion for Codex Beacon."""

from __future__ import annotations

import argparse
import ctypes
import queue
import socket
import sys
import time
from collections import deque
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QLockFile, QRectF, QSize, QStandardPaths, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QColor,
    QCloseEvent,
    QDesktopServices,
    QFont,
    QHideEvent,
    QPainter,
    QPen,
    QRadialGradient,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from codex_beacon.companion.presentation import (
    CellLabelGroup,
    ConnectionPhase,
    FocusPhase,
    PresentationState,
    reduce_event,
    with_duration,
)
from codex_beacon.companion.runtime import CompanionEvent, CompanionRuntime
from codex_beacon.companion.status import (
    DEFAULT_PHONE_STATUS_PORT,
    MAX_PHONE_STATUS_PORT,
    MIN_PHONE_STATUS_PORT,
    PhoneStatusConfig,
    StatusProjector,
    StatusSnapshot,
    default_phone_status_path,
    load_phone_status_config,
    rotate_phone_status_token,
    save_phone_status_config,
)
from codex_beacon.companion.status_server import StatusServer
from codex_beacon.config import LocalDeviceConfig, default_config_path, load_local_device_config
from codex_beacon.contracts import RGB
from codex_beacon.host import HostEvent
from codex_beacon.packs.focus import ACTION_CANCEL, ACTION_START_PAUSE
from codex_beacon.packs.registry import AGENT_PACK_ID, BUILTIN_PACKS, FOCUS_PACK_ID
from codex_beacon.transport import ProtocolClientError


WINDOW_STYLE = """
QMainWindow, QDialog {
    background: #0f1115;
    color: #f3f5fb;
}
QWidget {
    color: #e7eaf2;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QLabel#Brand {
    color: #f3f5fb;
    font-size: 16pt;
    font-weight: 650;
}
QToolButton#PackButton {
    color: #aeb6c8;
    background: transparent;
    border: none;
    border-radius: 7px;
    min-height: 28px;
    padding: 0 8px;
    font-size: 12pt;
    font-weight: 600;
}
QToolButton#PackButton:hover, QToolButton#PackButton:focus {
    color: #f3f5fb;
    background: #1b1f2a;
}
QToolButton#PackButton::menu-indicator {
    image: none;
    width: 0px;
}
QMenu {
    background: #171a23;
    color: #e7eaf2;
    border: 1px solid #2b3040;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    border-radius: 6px;
    padding: 7px 30px 7px 12px;
}
QMenu::item:selected {
    color: #f3f5fb;
    background: #1e2635;
}
QMenu::separator {
    height: 1px;
    background: #2b3040;
    margin: 5px 7px;
}
QToolButton#StatusDot {
    background: transparent;
    border: none;
    border-radius: 13px;
    min-width: 26px;
    min-height: 26px;
    font-size: 17pt;
    padding: 0;
}
QToolButton#StatusDot:hover {
    background: #1b1f2a;
}
QToolButton#SettingsButton {
    color: #aeb6c8;
    border: none;
    border-radius: 16px;
    min-width: 32px;
    min-height: 32px;
    font-size: 15pt;
}
QToolButton#SettingsButton:hover {
    color: #f3f5fb;
    background: #1b1f2a;
}
QLabel#Timer {
    color: #f3f5fb;
    font-size: 18pt;
    font-weight: 600;
}
QLabel#Timer[timerMode="true"] {
    font-size: 30pt;
}
QLabel#Notice {
    color: #fca5a5;
    background: #2a1518;
    border: 1px solid #5a252a;
    border-radius: 7px;
    padding: 6px 10px;
}
QToolButton#PrimaryAction, QToolButton#SecondaryAction {
    color: #9aa2b5;
    background: transparent;
    border: none;
    border-radius: 8px;
    min-height: 36px;
    padding: 0 12px;
    font-size: 9.5pt;
    font-weight: 600;
}
QToolButton#PrimaryAction {
    color: #ffffff;
    background: #2563eb;
    border: 1px solid #3b82f6;
}
QToolButton#PrimaryAction:hover {
    background: #3b82f6;
}
QToolButton#PrimaryAction:pressed {
    background: #1d4ed8;
}
QToolButton#SecondaryAction:hover {
    color: #f3f5fb;
    background: #1b1f2a;
}
QToolButton#SecondaryAction:pressed {
    background: #232a38;
}
QLineEdit, QSpinBox, QPlainTextEdit, QTextEdit {
    color: #e7eaf2;
    background: #12151c;
    border: 1px solid #2b3040;
    border-radius: 8px;
    padding: 5px 7px;
    selection-color: #ffffff;
    selection-background-color: #1e3a5f;
}
QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border-color: #3b82f6;
}
QPlainTextEdit#Diagnostics {
    color: #c9d1e0;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 10.5pt;
}
QPushButton {
    color: #d7dce8;
    background: transparent;
    border: 1px solid #2b3040;
    border-radius: 8px;
    min-height: 32px;
    padding: 0 12px;
}
QPushButton:hover {
    color: #f3f5fb;
    background: #1b1f2a;
}
QPushButton:pressed {
    background: #232a38;
}
QPushButton:default, QPushButton#Primary {
    color: #ffffff;
    background: #2563eb;
    border-color: #3b82f6;
}
QPushButton:default:hover, QPushButton#Primary:hover {
    background: #3b82f6;
}
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    color: #8a93a8;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 14px;
    margin-right: 6px;
}
QTabBar::tab:selected {
    color: #f3f5fb;
    border-bottom: 2px solid #3b82f6;
}
QTabBar::tab:hover:!selected {
    color: #c9d1e0;
}
QCheckBox {
    color: #d7dce8;
    spacing: 8px;
}
QToolTip {
    color: #e7eaf2;
    background: #171a23;
    border: 1px solid #2b3040;
    padding: 5px 7px;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #2b3040;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


def _apply_dark_title_bar(widget: QWidget) -> None:
    """Ask Windows to render the native title bar in dark mode."""

    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        value = ctypes.c_int(1)
        dwmapi = ctypes.windll.dwmapi
        for attribute in (20, 19):
            if (
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    attribute,
                    ctypes.byref(value),
                    ctypes.sizeof(value),
                )
                == 0
            ):
                break
    except Exception:
        # Dark title bars are cosmetic; never let an unsupported Windows
        # build prevent the companion from opening.
        pass


class LightStrip(QWidget):
    """Six quiet LED pips with optional desktop-only semantic labels."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cells: tuple[RGB, ...] = (RGB(0, 0, 0),) * 6
        self._groups: tuple[CellLabelGroup, ...] = ()
        self.setMinimumSize(300, 64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("Six Codex Beacon lights")

    def sizeHint(self) -> QSize:
        return QSize(380, 104 if self._groups else 64)

    def set_presentation(
        self,
        cells: tuple[RGB, ...],
        groups: tuple[CellLabelGroup, ...] = (),
    ) -> None:
        if cells == self._cells and groups == self._groups:
            return
        self._cells = cells
        self._groups = groups
        details = ", ".join(
            f"{group.label}: {group.value}" if group.value else group.label
            for group in groups
        )
        self.setAccessibleDescription(details)
        self.setMinimumHeight(104 if groups else 64)
        self.updateGeometry()
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        diameter = 30.0
        gap = 14.0
        total_width = 6 * diameter + 5 * gap
        start_x = (self.width() - total_width) / 2
        top = 58.0 if self._groups else (self.height() - diameter) / 2

        if self._groups:
            painter.setPen(QColor("#8a93a8"))
            label_font = painter.font()
            label_font.setPointSizeF(8.5)
            painter.setFont(label_font)
            for group in self._groups:
                first_center = start_x + group.start * (diameter + gap) + diameter / 2
                last_index = group.start + group.span - 1
                last_center = start_x + last_index * (diameter + gap) + diameter / 2
                center = (first_center + last_center) / 2
                painter.drawText(
                    QRectF(center - 62, 4, 124, 18),
                    Qt.AlignmentFlag.AlignCenter,
                    group.label,
                )
                if group.value:
                    value_font = painter.font()
                    value_font.setPointSizeF(9.5)
                    value_font.setBold(True)
                    painter.setFont(value_font)
                    painter.setPen(QColor("#e7eaf2"))
                    painter.drawText(
                        QRectF(center - 62, 24, 124, 20),
                        Qt.AlignmentFlag.AlignCenter,
                        group.value,
                    )
                    painter.setFont(label_font)
                    painter.setPen(QColor("#8a93a8"))

        for index, rgb in enumerate(self._cells):
            left = start_x + index * (diameter + gap)
            rect = QRectF(left, top, diameter, diameter)
            active = any((rgb.r, rgb.g, rgb.b))

            if active:
                base = QColor(rgb.r, rgb.g, rgb.b)
                if max(rgb.r, rgb.g, rgb.b) < 48:
                    base = base.lighter(260)
                glow = QRadialGradient(
                    rect.center(),
                    diameter * 0.75,
                )
                center_glow = QColor(base)
                center_glow.setAlpha(120)
                edge_glow = QColor(base)
                edge_glow.setAlpha(0)
                glow.setColorAt(0.0, center_glow)
                glow.setColorAt(0.58, center_glow)
                glow.setColorAt(1.0, edge_glow)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(
                    rect.adjusted(
                        -diameter * 0.25,
                        -diameter * 0.25,
                        diameter * 0.25,
                        diameter * 0.25,
                    )
                )

                gradient = QRadialGradient(rect.center(), diameter / 2)
                gradient.setColorAt(0.0, base.lighter(175))
                gradient.setColorAt(0.62, base.lighter(125))
                gradient.setColorAt(1.0, base.darker(118))
                painter.setBrush(gradient)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(rect)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor("#3a4050"), 1.5))
                painter.drawEllipse(rect.adjusted(0.75, 0.75, -0.75, -0.75))


class ElidedLabel(QLabel):
    """A single-line label that keeps its full text in the tooltip."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setMinimumWidth(0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.set_full_text(text)

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text)
        self._refresh_text()

    def _refresh_text(self) -> None:
        self.setText(
            self.fontMetrics().elidedText(
                self._full_text,
                Qt.TextElideMode.ElideMiddle,
                max(0, self.width() - 2),
            )
        )

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._refresh_text()


class SettingsDialog(QDialog):
    def __init__(self, owner: "CompanionWindow") -> None:
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle("Codex Beacon Settings")
        self.resize(620, 560)
        self.setStyleSheet(WINDOW_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        general = QWidget()
        general_layout = QVBoxLayout(general)
        general_layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.duration = QSpinBox()
        self.duration.setRange(1, 240)
        self.duration.setValue(owner.duration_minutes)
        self.duration.valueChanged.connect(self._update_duration_suffix)
        self._update_duration_suffix(self.duration.value())
        self.duration.setAccessibleName("Focus duration in minutes")
        form.addRow("Focus duration", self.duration)
        general_layout.addLayout(form)

        apply_duration = QPushButton("Apply duration and reset")
        apply_duration.setObjectName("Primary")
        apply_duration.clicked.connect(self._apply_duration)
        general_layout.addWidget(apply_duration, 0, Qt.AlignmentFlag.AlignRight)
        general_layout.addStretch(1)
        tabs.addTab(general, "General")

        agent = QWidget()
        agent_layout = QVBoxLayout(agent)
        agent_layout.setContentsMargins(16, 16, 16, 16)
        agent_title = QLabel("Codex activity")
        agent_title.setStyleSheet("font-size: 12pt; font-weight: 600;")
        agent_layout.addWidget(agent_title)
        agent_copy = QLabel(
            "1. Select Agent from the mode menu.\n"
            "2. In Codex, open /hooks and trust Codex Beacon's five User Config hooks.\n"
            "3. Keep Codex Beacon running. It receives only state changes—never "
            "prompts, commands, paths, or tool output."
        )
        agent_copy.setWordWrap(True)
        agent_layout.addWidget(agent_copy)
        agent_path = ElidedLabel(str(owner.agent_config_path))
        agent_path.setStyleSheet("color: #8a93a8;")
        agent_path.setAccessibleName("Agent hook configuration path")
        agent_layout.addWidget(agent_path)
        agent_layout.addStretch(1)
        tabs.addTab(agent, "Agent")

        phone = QWidget()
        phone_layout = QVBoxLayout(phone)
        phone_layout.setContentsMargins(16, 16, 16, 16)
        phone_title = QLabel("Phone status page")
        phone_title.setStyleSheet("font-size: 12pt; font-weight: 600;")
        phone_layout.addWidget(phone_title)
        phone_copy_note = QLabel(
            "Keep this page open on an old phone on the same Wi-Fi. It shows "
            "Codex or Focus status and can chime or vibrate when something needs "
            "attention or finishes. It is read-only: the phone can never approve "
            "or control Codex."
        )
        phone_copy_note.setWordWrap(True)
        phone_layout.addWidget(phone_copy_note)

        phone_form = QFormLayout()
        phone_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        self.phone_enabled = QCheckBox("Serve the status page on this PC")
        self.phone_enabled.setChecked(
            owner.phone_config.enabled if owner.phone_config else False
        )
        phone_form.addRow("Enabled", self.phone_enabled)
        self.phone_port = QSpinBox()
        self.phone_port.setRange(MIN_PHONE_STATUS_PORT, MAX_PHONE_STATUS_PORT)
        self.phone_port.setValue(
            owner.phone_config.port
            if owner.phone_config
            else DEFAULT_PHONE_STATUS_PORT
        )
        self.phone_port.setAccessibleName("Phone status page port")
        self.phone_port.setMaximumWidth(160)
        phone_form.addRow("Port", self.phone_port)
        self.phone_url = ElidedLabel(owner.phone_url or "Not running")
        self.phone_url.setAccessibleName("Phone status page URL")
        phone_form.addRow("Phone URL", self.phone_url)
        self.phone_status = QLabel(owner.phone_status_text())
        self.phone_status.setWordWrap(True)
        self.phone_status.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        phone_form.addRow("Status", self.phone_status)
        phone_layout.addLayout(phone_form)

        phone_buttons = QHBoxLayout()
        self.phone_copy = QPushButton("Copy URL")
        self.phone_copy.clicked.connect(self._copy_phone_url)
        self.phone_open = QPushButton("Open on this PC")
        self.phone_open.clicked.connect(owner.open_phone_page)
        self.phone_rotate = QPushButton("Rotate token")
        self.phone_rotate.clicked.connect(self._rotate_phone_token)
        phone_buttons.addWidget(self.phone_copy)
        phone_buttons.addWidget(self.phone_open)
        phone_buttons.addWidget(self.phone_rotate)
        phone_buttons.addStretch(1)
        phone_layout.addLayout(phone_buttons)

        phone_hint = QLabel(
            "Phone and PC must be on the same Wi-Fi. Allow inbound TCP 8765 from "
            "the local subnet in Windows Firewall; a Private-only rule will not "
            "work on a network marked Public. Guest Wi-Fi or client isolation "
            "will block the page."
        )
        phone_hint.setWordWrap(True)
        phone_hint.setStyleSheet("color: #8a93a8;")
        phone_layout.addWidget(phone_hint)
        apply_phone = QPushButton("Apply phone settings")
        apply_phone.setObjectName("Primary")
        apply_phone.clicked.connect(self._apply_phone)
        phone_layout.addWidget(apply_phone, 0, Qt.AlignmentFlag.AlignRight)
        phone_layout.addStretch(1)
        tabs.addTab(phone, "Phone")

        device = QWidget()
        # Keep the hidden tab alive when software-only mode does not add it.
        self._device_tab = device
        device_layout = QVBoxLayout(device)
        device_layout.setContentsMargins(16, 16, 16, 16)
        device_form = QFormLayout()
        self.endpoint = QLineEdit(owner.endpoint)
        self.endpoint.setAccessibleName("Codex Beacon device endpoint")
        device_form.addRow("Endpoint", self.endpoint)
        self.connection = QLabel()
        device_form.addRow("Status", self.connection)
        self.device_id = QLabel(owner.state.device_id or "—")
        self.device_id.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        device_form.addRow("Device", self.device_id)
        device_layout.addLayout(device_form)

        connection_buttons = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._connect)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(owner.disconnect_device)
        self.status_button = QPushButton("Request renderer status")
        self.status_button.clicked.connect(owner.runtime.status)
        connection_buttons.addWidget(self.connect_button)
        connection_buttons.addWidget(self.disconnect_button)
        connection_buttons.addStretch(1)
        connection_buttons.addWidget(self.status_button)
        device_layout.addLayout(connection_buttons)
        device_layout.addStretch(1)
        if owner.has_device_config:
            tabs.addTab(device, "Display")

        diagnostics = QWidget()
        diagnostics_layout = QVBoxLayout(diagnostics)
        diagnostics_layout.setContentsMargins(12, 12, 12, 12)
        self.log = QPlainTextEdit()
        self.log.setObjectName("Diagnostics")
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.log.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log.setAccessibleName("Codex Beacon diagnostic activity")
        diagnostics_layout.addWidget(self.log, 1)
        tabs.addTab(diagnostics, "Diagnostics")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.refresh()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        _apply_dark_title_bar(self)

    def refresh(self) -> None:
        state = self.owner.state
        self.connection.setText(state.connection_label)
        self.device_id.setText(state.device_id or "—")
        connected = state.connection is ConnectionPhase.CONNECTED
        busy = state.connection in {
            ConnectionPhase.CONNECTING,
            ConnectionPhase.RECONNECTING,
        }
        self.connect_button.setEnabled(not connected and not busy)
        self.disconnect_button.setEnabled(connected or busy)
        self.status_button.setEnabled(connected)
        self.log.setPlainText("\n".join(self.owner.activity))
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.phone_url.set_full_text(self.owner.phone_url or "Not running")
        self.phone_status.setText(self.owner.phone_status_text())

    def _apply_phone(self) -> None:
        self.owner.apply_phone_settings(
            self.phone_enabled.isChecked(),
            self.phone_port.value(),
        )
        self.refresh()

    def _copy_phone_url(self) -> None:
        url = self.owner.phone_url
        if not url:
            self.phone_status.setText("Start the phone status page first.")
            return
        QApplication.clipboard().setText(url)
        self.phone_status.setText("Phone URL copied.")

    def _rotate_phone_token(self) -> None:
        self.owner.rotate_phone_token()
        self.refresh()

    def _connect(self) -> None:
        self.owner.connect_device(self.endpoint.text().strip())

    def _update_duration_suffix(self, value: int) -> None:
        self.duration.setSuffix(" minute" if value == 1 else " minutes")

    def _apply_duration(self) -> None:
        if self.owner.state.focus in {FocusPhase.WORKING, FocusPhase.PAUSED}:
            answer = QMessageBox.question(
                self,
                "Reset Focus?",
                "Changing the duration will stop and reset the current Focus session.",
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Apply,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Apply:
                return
        self.owner.apply_duration(self.duration.value())


class CompanionWindow(QMainWindow):
    def __init__(
        self,
        *,
        config_path: Path,
        endpoint_override: str | None,
        duration_minutes: int,
        auto_connect: bool,
        reduced_motion: bool,
        initial_pack_id: str = AGENT_PACK_ID,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Codex Beacon")
        self.setMinimumSize(560, 290)
        self.resize(680, 320)
        self.setStyleSheet(WINDOW_STYLE)

        self._events: queue.SimpleQueue[CompanionEvent] = queue.SimpleQueue()
        self._config_path = config_path
        self.agent_config_path = config_path.with_name("agent-hook.json")
        self._phone_config_path = default_phone_status_path(config_path)
        self._phone_config: PhoneStatusConfig | None = None
        self._status_projector = StatusProjector()
        self._status_server: StatusServer | None = None
        self._status_server_error: str | None = None
        self._last_status: StatusSnapshot | None = None
        self._config: LocalDeviceConfig | None = None
        self._closing = False
        self._really_quit = False
        self._settings: SettingsDialog | None = None
        self._tray: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None
        self._tray_available = False
        self._tray_hint_shown = False
        self.activity: deque[str] = deque(maxlen=160)
        self.duration_minutes = duration_minutes
        self.reduced_motion = reduced_motion
        self.endpoint = endpoint_override or ""
        self.state = PresentationState.initial(
            duration_minutes,
            reduced_motion=reduced_motion,
        )

        self._build()
        self._load_config(endpoint_override)
        try:
            self.runtime = CompanionRuntime(
                self._events.put,
                duration_minutes=duration_minutes,
                reduced_motion=reduced_motion,
                agent_config_path=self.agent_config_path,
                initial_pack_id=initial_pack_id,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Codex Beacon", f"The companion could not start: {exc}")
            raise

        self._build_tray()
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(60)
        self._poll_timer.timeout.connect(self._poll_events)
        self._poll_timer.start()
        self._animation_timer = QTimer(self)
        self._animation_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._animation_timer.setInterval(33)
        self._animation_timer.timeout.connect(self._render_lights)
        self._animation_timer.start()
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(5_000)
        self._status_timer.timeout.connect(self._publish_status)
        self._status_timer.start()
        self._render()
        self._start_phone_status()
        if auto_connect and self._config is not None:
            QTimer.singleShot(350, self.connect_device)

    def _build(self) -> None:
        central = QWidget()
        central.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(22, 16, 22, 18)
        outer.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(2)
        brand = QLabel("Codex Beacon")
        brand.setObjectName("Brand")
        header.addWidget(brand)

        self.pack_button = QToolButton()
        self.pack_button.setObjectName("PackButton")
        self.pack_button.setText("Focus  ▾")
        self.pack_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.pack_button.setAccessibleName("Focus mode. Open mode selector")
        self.pack_button.setToolTip("Focus mode")
        pack_menu = QMenu(self.pack_button)
        self._pack_actions = {}
        for descriptor in BUILTIN_PACKS:
            action = pack_menu.addAction(descriptor.display_name)
            action.setCheckable(True)
            action.triggered.connect(
                lambda _checked=False, pack_id=descriptor.pack_id: self._select_pack(pack_id)
            )
            self._pack_actions[descriptor.pack_id] = action
        pack_menu.addSeparator()
        add_pack = pack_menu.addAction("Add new…")
        add_pack.triggered.connect(self._open_add_pack)
        self.pack_button.setMenu(pack_menu)
        header.addWidget(self.pack_button)
        header.addStretch(1)

        self.status_chip = QToolButton()
        self.status_chip.setObjectName("StatusDot")
        self.status_chip.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.status_chip.clicked.connect(self.open_settings)
        self.status_chip.setAccessibleName("Codex Beacon status")
        header.addWidget(self.status_chip)

        settings = QToolButton()
        settings.setObjectName("SettingsButton")
        settings.setText("\ue713")
        settings.setStyleSheet(
            'font-family: "Segoe MDL2 Assets"; font-size: 12pt;'
        )
        settings.setToolTip("Settings")
        settings.setAccessibleName("Open Settings")
        settings.clicked.connect(self.open_settings)
        header.addWidget(settings)
        outer.addLayout(header)

        content = QVBoxLayout()
        content.setContentsMargins(0, 15, 0, 0)
        content.setSpacing(4)
        content.addStretch(1)

        self.timer = QLabel("25:00")
        self.timer.setObjectName("Timer")
        self.timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer.setAccessibleName("Focus time remaining")
        content.addWidget(self.timer)

        self.lights = LightStrip()
        content.addWidget(self.lights, 0, Qt.AlignmentFlag.AlignCenter)

        controls = QHBoxLayout()
        controls.setSpacing(3)
        controls.addStretch(1)
        self.primary = QToolButton()
        self.primary.setObjectName("PrimaryAction")
        self.primary.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.primary.setIconSize(QSize(12, 12))
        self.primary.clicked.connect(
            lambda: self.runtime.send_action(ACTION_START_PAUSE)
        )
        controls.addWidget(self.primary)

        self.stop = QToolButton()
        self.stop.setObjectName("SecondaryAction")
        self.stop.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.stop.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
        )
        self.stop.setIconSize(QSize(10, 10))
        self.stop.setText("Stop")
        self.stop.setToolTip("Stop Focus")
        self.stop.setAccessibleName("Stop Focus")
        self.stop.clicked.connect(lambda: self.runtime.send_action(ACTION_CANCEL))
        controls.addWidget(self.stop)
        controls.addStretch(1)
        content.addLayout(controls)

        self.notice = QLabel()
        self.notice.setObjectName("Notice")
        self.notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notice.setWordWrap(True)
        self.notice.setVisible(False)
        content.addWidget(self.notice, 0, Qt.AlignmentFlag.AlignCenter)
        content.addStretch(1)
        outer.addLayout(content, 1)
        central.setFocus()

    def _open_add_pack(self) -> None:
        QMessageBox.information(
            self,
            "Add a Codex Beacon mode",
            "Focus and Agent are the reviewed built-in modes in this prototype. "
            "Installing third-party packs is not enabled yet.",
        )

    def _select_pack(self, pack_id: str) -> None:
        if pack_id == self.state.active_pack_id:
            self._render()
            return
        self.runtime.activate_pack(pack_id)

    def _load_config(self, endpoint_override: str | None) -> None:
        if not self._config_path.is_file():
            self._log(
                "No hardware display configured; using the phone status page."
            )
            return
        try:
            self._config = load_local_device_config(self._config_path)
        except (OSError, ProtocolClientError) as exc:
            self._log(f"Hardware display configuration is invalid: {exc}")
            return
        if endpoint_override is None:
            self.endpoint = self._config.endpoint

    @property
    def has_device_config(self) -> bool:
        return self._config is not None

    @property
    def phone_config(self) -> PhoneStatusConfig | None:
        return self._phone_config

    @property
    def phone_url(self) -> str | None:
        if self._status_server is None or self._phone_config is None:
            return None
        address = self._lan_address()
        return (
            f"http://{address}:{self._status_server.port}/"
            f"s/{self._phone_config.token}/"
        )

    def phone_status_text(self) -> str:
        if self._status_server is not None and self._phone_config is not None:
            return f"Serving on port {self._status_server.port}."
        if self._phone_config is not None and not self._phone_config.enabled:
            return "Disabled."
        if self._status_server_error:
            return self._status_server_error
        return "Not running."

    @staticmethod
    def _lan_address() -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("8.8.8.8", 80))
                address = probe.getsockname()[0]
                if address and not address.startswith("127."):
                    return address
        except OSError:
            pass
        try:
            address = socket.gethostbyname(socket.gethostname())
        except OSError:
            address = "127.0.0.1"
        return address or "127.0.0.1"

    def _build_tray(self) -> None:
        if self._tray is not None:
            return
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._log("System tray unavailable; closing the window quits Codex Beacon.")
            return
        self._tray_available = True
        tray = QSystemTrayIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon),
            self,
        )
        tray.setToolTip("Codex Beacon")
        menu = QMenu(self)
        show_action = menu.addAction("Show Codex Beacon")
        show_action.triggered.connect(self._show_from_tray)
        open_action = menu.addAction("Open status page")
        open_action.triggered.connect(self.open_phone_page)
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._quit_from_tray)
        tray.setContextMenu(menu)
        tray.activated.connect(self._tray_activated)
        tray.show()
        self._tray = tray
        self._tray_menu = menu

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def open_phone_page(self) -> None:
        url = self.phone_url
        if not url:
            QMessageBox.information(
                self,
                "Phone status page",
                "The phone status page is not running. Enable it in Settings > Phone.",
            )
            return
        QDesktopServices.openUrl(QUrl(url))

    def _quit_from_tray(self) -> None:
        self._really_quit = True
        self._shutdown()
        self.close()
        application = QApplication.instance()
        if application is not None:
            application.quit()

    def _start_phone_status(self) -> None:
        self._stop_phone_status()
        try:
            config = load_phone_status_config(self._phone_config_path)
        except (OSError, ValueError) as exc:
            self._phone_config = None
            self._status_server_error = f"Phone status settings unavailable: {exc}"
            self._log(self._status_server_error)
            self._refresh_status_chip()
            return
        self._phone_config = config
        if not config.enabled:
            self._status_server_error = None
            self._refresh_status_chip()
            return
        server = StatusServer(token=config.token, port=config.port)
        try:
            server.start()
        except OSError as exc:
            self._status_server_error = (
                f"Could not start the phone page on port {config.port}: {exc}"
            )
            self._log(self._status_server_error)
            self._refresh_status_chip()
            return
        self._status_server = server
        self._status_server_error = None
        self._publish_status()
        self._log(f"Phone status page ready on port {server.port}.")
        self._refresh_status_chip()

    def _stop_phone_status(self) -> None:
        if self._status_server is not None:
            self._status_server.stop()
            self._status_server = None

    def _restart_phone_status(self) -> None:
        self._stop_phone_status()
        self._start_phone_status()

    def apply_phone_settings(self, enabled: bool, port: int) -> None:
        try:
            config = self._phone_config or load_phone_status_config(
                self._phone_config_path
            )
            updated = replace(config, enabled=enabled, port=port)
            save_phone_status_config(updated)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Phone status page",
                f"Could not save the phone settings: {exc}",
            )
            return
        self._phone_config = updated
        self._restart_phone_status()
        self._render()

    def rotate_phone_token(self) -> None:
        if self._phone_config is None:
            QMessageBox.information(
                self,
                "Phone status page",
                "Phone settings are not available. Enable the page first.",
            )
            return
        try:
            self._phone_config = rotate_phone_status_token(self._phone_config)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Phone status page",
                f"Could not rotate the phone access token: {exc}",
            )
            return
        self._restart_phone_status()
        self._render()

    def _publish_status(self) -> None:
        snapshot = self._status_projector.project(
            self.state,
            now_monotonic_ns=time.monotonic_ns(),
        )
        self._last_status = snapshot
        if self._status_server is not None:
            self._status_server.publish(snapshot)
        if self._tray is not None:
            phase = snapshot.phase.value.replace("_", " ")
            self._tray.setToolTip(f"Codex Beacon · {snapshot.headline} ({phase})")

    def connect_device(self, endpoint: str | None = None) -> None:
        if self._config is None:
            QMessageBox.critical(
                self,
                "Codex Beacon connection",
                "No local device configuration is available. Codex Beacon's "
                "supported mode uses the phone status page.",
            )
            return
        selected_endpoint = endpoint or self.endpoint or self._config.endpoint
        try:
            self.runtime.connect(
                selected_endpoint,
                self._config.secret,
                self._config.expected_device_id,
            )
        except (ProtocolClientError, RuntimeError) as exc:
            QMessageBox.critical(self, "Codex Beacon connection", str(exc))
            return
        self.endpoint = selected_endpoint

    def disconnect_device(self) -> None:
        self.runtime.disconnect()

    def apply_duration(self, duration_minutes: int) -> None:
        self.duration_minutes = duration_minutes
        self.state = with_duration(self.state, duration_minutes)
        self.runtime.apply_duration(duration_minutes)
        self._render()
        self._publish_status()

    def open_settings(self) -> None:
        if self._settings is None:
            self._settings = SettingsDialog(self)
            self._settings.finished.connect(self._settings_closed)
        self._settings.refresh()
        self._settings.show()
        self._settings.raise_()
        self._settings.activateWindow()

    def _settings_closed(self, _result: int) -> None:
        if self._settings is not None:
            self._settings.deleteLater()
            self._settings = None

    def _poll_events(self) -> None:
        if self._closing:
            return
        changed = False
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            changed = True
            noisy_refresh = (
                event.kind == "host"
                and isinstance(event.payload, HostEvent)
                and event.payload.kind == "proposal_accepted"
            )
            if not noisy_refresh:
                self._log(event.message)
            self.state = reduce_event(self.state, event)
        if changed:
            self._render()
            self._publish_status()

    def _render(self) -> None:
        self.pack_button.setText(f"{self.state.active_pack_name}  ▾")
        self.pack_button.setToolTip(f"{self.state.active_pack_name} mode")
        self.pack_button.setAccessibleName(
            f"{self.state.active_pack_name} mode. Open mode selector"
        )
        for pack_id, action in self._pack_actions.items():
            action.setChecked(pack_id == self.state.active_pack_id)

        self.timer.setText(self.state.main_text)
        self.timer.setProperty(
            "timerMode",
            "true" if self.state.is_focus else "false",
        )
        self.timer.style().unpolish(self.timer)
        self.timer.style().polish(self.timer)
        timer_font = self.timer.font()
        timer_font.setFeature(QFont.Tag("tnum"), 1)
        self.timer.setFont(timer_font)
        self.timer.setAccessibleName(
            "Focus time remaining" if self.state.is_focus else self.state.headline
        )
        self._render_lights()

        pause = self.state.focus is FocusPhase.WORKING
        icon = QStyle.StandardPixmap.SP_MediaPause if pause else QStyle.StandardPixmap.SP_MediaPlay
        self.primary.setIcon(self.style().standardIcon(icon))
        self.primary.setText(
            "Pause"
            if self.state.focus is FocusPhase.WORKING
            else "Resume"
            if self.state.focus is FocusPhase.PAUSED
            else "Start"
        )
        self.primary.setToolTip(self.state.primary_action_name)
        self.primary.setAccessibleName(self.state.primary_action_name)
        self.primary.setVisible(self.state.is_focus)
        self.stop.setVisible(self.state.can_stop)

        self._refresh_status_chip()

        if self.state.notice:
            self.notice.setText(self.state.notice)
            self.notice.setVisible(True)
        else:
            self.notice.setVisible(False)

        if self._settings is not None:
            self._settings.refresh()

    def _status_chip_presentation(self) -> tuple[str, str]:
        if self._config is None:
            if self._status_server is not None:
                return "Phone page serving, no hardware", "#22c55e"
            if self._status_server_error:
                return "Phone page needs attention", "#ef4444"
            return "Phone page not running", "#6e768a"
        dot_color = {
            ConnectionPhase.CONNECTED: "#22c55e",
            ConnectionPhase.CONNECTING: "#facc15",
            ConnectionPhase.RECONNECTING: "#facc15",
            ConnectionPhase.ATTENTION: "#ef4444",
            ConnectionPhase.DISCONNECTED: "#6e768a",
        }[self.state.connection]
        return self.state.connection_label, dot_color

    def _refresh_status_chip(self) -> None:
        status_label, dot_color = self._status_chip_presentation()
        self.status_chip.setText("●")
        self.status_chip.setStyleSheet(f"color: {dot_color};")
        tooltip = (
            status_label
            if self._config is None
            else f"Codex Beacon {status_label}"
        )
        self.status_chip.setToolTip(tooltip)
        self.status_chip.setAccessibleName(
            f"Codex Beacon status: {status_label}. Open settings"
        )

    def _render_lights(self) -> None:
        self.lights.set_presentation(
            self.state.displayed_cells_at(time.monotonic_ns()),
            self.state.cell_label_groups,
        )

    def _log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.activity.append(f"[{stamp}] {message}")

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        _apply_dark_title_bar(self)
        if hasattr(self, "_animation_timer"):
            self._animation_timer.start()

    def hideEvent(self, event: QHideEvent) -> None:
        if hasattr(self, "_animation_timer"):
            self._animation_timer.stop()
        super().hideEvent(event)

    def _shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._poll_timer.stop()
        self._animation_timer.stop()
        self._status_timer.stop()
        self._stop_phone_status()
        self.runtime.shutdown()
        if self._tray is not None:
            self._tray.hide()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._really_quit or not self._tray_available:
            self._shutdown()
            event.accept()
            if not self._tray_available:
                application = QApplication.instance()
                if application is not None:
                    application.quit()
            return
        event.ignore()
        if self._settings is not None:
            self._settings.close()
        self.hide()
        if not self._tray_hint_shown and self._tray is not None:
            self._tray.showMessage(
                "Codex Beacon is still running",
                "The phone status page is still available. Use the tray icon "
                "to reopen Codex Beacon or quit.",
                QSystemTrayIcon.MessageIcon.Information,
                5_000,
            )
            self._tray_hint_shown = True


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex Beacon first-party desktop companion")
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--endpoint", help="Override the private-LAN hostname/IP or ws:// URL")
    parser.add_argument(
        "--duration", type=int, default=25, choices=range(1, 241), metavar="MINUTES"
    )
    parser.add_argument("--no-auto-connect", action="store_true")
    parser.add_argument("--reduced-motion", action="store_true")
    parser.add_argument(
        "--focus",
        action="store_true",
        help="Start in the optional Focus timer mode instead of Agent status mode",
    )
    parser.add_argument("--agent", action="store_true", help=argparse.SUPPRESS)
    return parser


def _instance_lock() -> QLockFile:
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.TempLocation
    )
    lock = QLockFile(str(Path(location or ".") / "codex-beacon-companion.lock"))
    lock.setStaleLockTime(10_000)
    return lock


def main() -> None:
    arguments = _argument_parser().parse_args()
    application = QApplication.instance() or QApplication([])
    application.setApplicationName("Codex Beacon")
    application.setOrganizationName("Codex Beacon")
    application.setQuitOnLastWindowClosed(False)
    instance_lock = _instance_lock()
    if not instance_lock.tryLock(0):
        QMessageBox.information(
            None,
            "Codex Beacon",
            "Codex Beacon is already running. Use the tray icon to open it.",
        )
        return
    window = CompanionWindow(
        config_path=arguments.config.resolve(),
        endpoint_override=arguments.endpoint,
        duration_minutes=arguments.duration,
        auto_connect=not arguments.no_auto_connect,
        reduced_motion=arguments.reduced_motion,
        initial_pack_id=FOCUS_PACK_ID if arguments.focus else AGENT_PACK_ID,
    )
    application.aboutToQuit.connect(window._shutdown)
    window.show()
    raise SystemExit(application.exec())


if __name__ == "__main__":
    main()