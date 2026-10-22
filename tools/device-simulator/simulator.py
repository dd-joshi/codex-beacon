"""Small smoke-test entry point for the in-memory P0 device model."""

from __future__ import annotations

import sys
from pathlib import Path


DESKTOP_SRC = Path(__file__).resolve().parents[2] / "desktop" / "src"
sys.path.insert(0, str(DESKTOP_SRC))

from peri6.testing import DeviceSimulator  # noqa: E402


def main() -> int:
    device = DeviceSimulator(secret=bytes(range(32)))
    print(
        "Peri6 protocol-v1 in-memory simulator ready: "
        f"{device.device_id}, {device.capabilities.cell_count} cells"
    )
    print("Run `python -m unittest discover -s desktop/tests -v` for scenarios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
