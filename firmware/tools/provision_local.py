"""Interactively create the ignored desk-prototype configuration header."""

from __future__ import annotations

import base64
import getpass
import json
import secrets
from pathlib import Path


CONFIRMED_DEVICE_ID = "p6-c3-afb810"
CONFIRMED_ENDPOINT = f"ws://{CONFIRMED_DEVICE_ID}.local:8765/ws/v1"


def c_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def main() -> None:
    repository = Path(__file__).resolve().parents[2]
    firmware_target = repository / "firmware" / "include" / "peri6_local_config.h"
    desktop_target = repository / "desktop" / "local-config.json"
    existing = [target for target in (firmware_target, desktop_target) if target.exists()]
    if existing:
        raise SystemExit(
            "Refusing to replace an existing local configuration: "
            + ", ".join(str(target) for target in existing)
        )

    ssid = input("Private LAN SSID: ").strip()
    if not 1 <= len(ssid.encode("utf-8")) <= 32:
        raise SystemExit("SSID must contain 1..32 UTF-8 bytes")
    password = getpass.getpass("Private LAN password (input hidden): ")
    if len(password.encode("utf-8")) > 63:
        raise SystemExit("LAN password must not exceed 63 UTF-8 bytes")
    secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    firmware_target.write_text(
        "#pragma once\n\n"
        f'#define PERI6_WIFI_SSID "{c_string(ssid)}"\n'
        f'#define PERI6_WIFI_PASSWORD "{c_string(password)}"\n'
        f'#define PERI6_DEVICE_SECRET_B64URL "{secret}"\n'
        "#define PERI6_AMBIENT_ENABLED 0\n",
        encoding="utf-8",
    )
    desktop_target.write_text(
        json.dumps(
            {
                "endpoint": CONFIRMED_ENDPOINT,
                "expected_device_id": CONFIRMED_DEVICE_ID,
                "device_secret_b64url": secret,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Created {firmware_target}")
    print(f"Created {desktop_target}")
    print("The LAN password and device secret were not printed.")


if __name__ == "__main__":
    main()
