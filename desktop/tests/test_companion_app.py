from __future__ import annotations

import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QTabWidget, QWidget

from codex_beacon.companion.app import SettingsDialog
from codex_beacon.companion.presentation import PresentationState


class _FakeRuntime:
    def status(self) -> None:
        pass


class _FakeOwner(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.duration_minutes = 25
        self.agent_config_path = Path("agent-hook.json")
        self.phone_config = None
        self.phone_url = "http://phone.example/s/token/"
        self.endpoint = ""
        self.state = PresentationState.initial(self.duration_minutes)
        self.activity: list[str] = []
        self.runtime = _FakeRuntime()
        self.has_device_config = False

    def phone_status_text(self) -> str:
        return "Serving on port 8765."

    def apply_phone_settings(self, enabled: bool, port: int) -> None:
        pass

    def rotate_phone_token(self) -> None:
        pass

    def open_phone_page(self) -> None:
        pass

    def connect_device(self, endpoint: str) -> None:
        pass

    def disconnect_device(self) -> None:
        pass

    def apply_duration(self, duration_minutes: int) -> None:
        pass


class SettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_software_only_settings_omit_the_legacy_device_tab(self) -> None:
        owner = _FakeOwner()
        dialog = SettingsDialog(owner)
        try:
            tabs = dialog.findChild(QTabWidget)
            self.assertIsNotNone(tabs)
            assert tabs is not None
            names = [tabs.tabText(index) for index in range(tabs.count())]
            self.assertNotIn("Device", names)
            self.assertNotIn("Display", names)
            self.assertIn("Phone", names)
            dialog.refresh()
        finally:
            dialog.close()
            dialog.deleteLater()
            owner.close()

    def test_hardware_display_tab_is_opt_in(self) -> None:
        owner = _FakeOwner()
        owner.has_device_config = True  # type: ignore[assignment]
        dialog = SettingsDialog(owner)
        try:
            tabs = dialog.findChild(QTabWidget)
            self.assertIsNotNone(tabs)
            assert tabs is not None
            names = [tabs.tabText(index) for index in range(tabs.count())]
            self.assertIn("Display", names)
            self.assertNotIn("Device", names)
            dialog.refresh()
        finally:
            dialog.close()
            dialog.deleteLater()
            owner.close()


if __name__ == "__main__":
    unittest.main()
