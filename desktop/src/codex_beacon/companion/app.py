"""Compact first-party Windows companion for Codex Beacon."""

from __future__ import annotations

import argparse
import queue
import socket
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
    QHideEvent,
    QPainter,
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
    background: #f7f7fa;
    color: #171922;
}
QWidget {
    font-family: "Segoe UI";
    font-size: 10pt;
}
QToolButton#PackButton {
    color: #30333c;
    background: transparent;
    border: none;
    border-radius: 7px;
    min-height: 28px;
    padding: 0 6px;
    font-size: 12pt;
}
QToolButton#PackButton:hover, QToolButton#PackButton:focus {
    background: #ececf1;
}
QToolButton#PackButton::menu-indicator {
    image: none;
    width: 0px;
}
QMenu {
    background: #ffffff;
    color: #20222a;
    border: 1px solid #dfe1e8;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    border-radius: 6px;
    padding: 7px 30px 7px 12px;
}
QMenu::item:selected {
    background: #eeeaf9;
}
QMenu::separator {
    height: 1px;
    background: #e7e8ed;
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
    background: #ececf1;
}
QToolButton#SettingsButton {
    border: none;
    border-radius: 16px;
    min-width: 32px;
    min-height: 32px;
    font-size: 15pt;
}
QToolButton#SettingsButton:hover {
    background: #eceaf3;
}
QLabel#Timer {
    color: #171922;
    font-size: 33pt;
    font-weight: 600;
}
QLabel#Notice {
    color: #9d2d28;
    background: #fff0ef;
    border-radius: 7px;
    padding: 6px 10px;
}
QToolButton#SessionControl {
    color: #686c77;
    background: transparent;
    border: none;
    border-radius: 7px;
    min-height: 29px;
    padding: 0 8px;
    font-size: 9pt;
}
QToolButton#SessionControl:hover {
    color: #272a32;
    background: #ececf1;
}
QToolButton#SessionControl:pressed {
    background: #e1e1e8;
}
QLineEdit, QSpinBox, QPlainTextEdit {
    background: #ffffff;
    border: 1px solid #dfe1e8;
    border-radius: 7px;
    padding: 5px 7px;
}
QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus {
    border-color: #8b63ee;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #d8dae2;
    border-radius: 7px;
    min-height: 30px;
    padding: 0 12px;
}
QPushButton:hover {
    background: #f0eef7;
}
QPushButton:default {
    color: #ffffff;
    background: #7651d9;
    border-color: #7651d9;
}
QTabWidget::pane {
    border: 1px solid #dfe1e8;
    border-radius: 7px;
    background: #ffffff;
}
QTabBar::tab {
    padding: 7px 13px;
}
"""


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

        diameter = 18.0
        gap = 17.0
        total_width = 6 * diameter + 5 * gap
        start_x = (self.width() - total_width) / 2
        top = 63.0 if self._groups else (self.height() - diameter) / 2

        if self._groups:
            painter.setPen(QColor("#5f6370"))
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
                    painter.setPen(QColor("#242731"))
                    painter.drawText(
                        QRectF(center - 62, 24, 124, 20),
                        Qt.AlignmentFlag.AlignCenter,
                        group.value,
                    )
                    painter.setFont(label_font)
                    painter.setPen(QColor("#5f6370"))

        for index, rgb in enumerate(self._cells):
            left = start_x + index * (diameter + gap)
            rect = QRectF(left, top, diameter, diameter)
            active = any((rgb.r, rgb.g, rgb.b))

            if active:
                base = QColor(rgb.r, rgb.g, rgb.b)
                if max(rgb.r, rgb.g, rgb.b) < 48:
                    base = base.lighter(260)
                glow = QColor(base.lighter(145))
                glow.setAlpha(34)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(rect.adjusted(-6, -6, 6, 6))

                gradient = QRadialGradient(rect.center(), diameter / 2)
                gradient.setColorAt(0.0, base.lighter(175))
                gradient.setColorAt(0.62, base.lighter(125))
                gradient.setColorAt(1.0, base.darker(118))
                painter.setBrush(gradient)
            else:
                painter.setBrush(QColor("#f0f1f4"))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)


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
            "Select Agent from the pack menu, then review and trust Codex Beacon's "
            "five User Config hooks in Codex using /hooks. Codex Beacon receives "
            "only state "
            "changes such as thinking, testing, and ready for review—never "
            "prompts, commands, file paths, or tool output."
        )
        agent_copy.setWordWrap(True)
        agent_layout.addWidget(agent_copy)
        agent_path = QLabel(str(owner.agent_config_path))
        agent_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        agent_path.setStyleSheet("color: #686c77;")
        agent_path.setWordWrap(True)
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
            "Codex status and can chime or vibrate when Codex needs attention. "
            "It is read-only: the phone can never approve or control Codex."
        )
        phone_copy_note.setWordWrap(True)
        phone_layout.addWidget(phone_copy_note)

        phone_form = QFormLayout()
        phone_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
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
        phone_form.addRow("Port", self.phone_port)
        self.phone_url = QLabel(owner.phone_url or "Not running")
        self.phone_url.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.phone_url.setWordWrap(True)
        phone_form.addRow("Phone URL", self.phone_url)
        self.phone_status = QLabel(owner.phone_status_text())
        self.phone_status.setWordWrap(True)
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
            "Phone and PC must be on the same Wi-Fi. On first use, allow Codex Beacon "
            "through Windows Firewall for Private networks. Guest Wi-Fi or "
            "client isolation will block the page."
        )
        phone_hint.setWordWrap(True)
        phone_hint.setStyleSheet("color: #686c77;")
        phone_layout.addWidget(phone_hint)
        apply_phone = QPushButton("Apply phone settings")
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
        self.phone_url.setText(self.owner.phone_url or "Not running")
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
        brand.setStyleSheet("font-size: 16pt; font-weight: 650; color: #171922;")
        header.addWidget(brand)

        self.pack_button = QToolButton()
        self.pack_button.setObjectName("PackButton")
        self.pack_button.setText("Focus")
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
        self.status_chip.setAccessibleName("Device connection status")
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
        self.primary.setObjectName("SessionControl")
        self.primary.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.primary.setIconSize(QSize(12, 12))
        self.primary.clicked.connect(
            lambda: self.runtime.send_action(ACTION_START_PAUSE)
        )
        controls.addWidget(self.primary)

        self.stop = QToolButton()
        self.stop.setObjectName("SessionControl")
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
        self.pack_button.setText(self.state.active_pack_name)
        self.pack_button.setToolTip(f"{self.state.active_pack_name} mode")
        self.pack_button.setAccessibleName(
            f"{self.state.active_pack_name} mode. Open mode selector"
        )
        for pack_id, action in self._pack_actions.items():
            action.setChecked(pack_id == self.state.active_pack_id)

        self.timer.setText(self.state.main_text)
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
                return "Phone status page ready", "#20b26b"
            if self._status_server_error:
                return "Phone status page needs attention", "#c4483e"
            return "Phone status page not running", "#969aa5"
        dot_color = {
            ConnectionPhase.CONNECTED: "#20b26b",
            ConnectionPhase.CONNECTING: "#d18a12",
            ConnectionPhase.RECONNECTING: "#d18a12",
            ConnectionPhase.ATTENTION: "#c4483e",
            ConnectionPhase.DISCONNECTED: "#969aa5",
        }[self.state.connection]
        return self.state.connection_label, dot_color

    def _refresh_status_chip(self) -> None:
        status_label, dot_color = self._status_chip_presentation()
        self.status_chip.setText("●")
        self.status_chip.setStyleSheet(f"color: {dot_color};")
        self.status_chip.setToolTip(f"Codex Beacon {status_label}")
        self.status_chip.setAccessibleName(
            f"Codex Beacon {status_label}. Open settings"
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
        help="Start in the inherited Focus mode instead of Codex status mode",
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