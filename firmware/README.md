# Peri6 ESP32-C3 firmware

This native ESP-IDF project implements P1 of the authoritative local-Wi-Fi prototype plan: a
pack-agnostic, authenticated six-cell keyframe renderer. It contains no pack,
application, state, entitlement, battery, or updater behavior.

## Board profile

- ESP32-C3 SuperMini / 4 MB flash
- WS2812 data: GPIO3, six cells, GRB/800 kHz
- button: GPIO10 to GND with `INPUT_PULLUP` and 30 ms debounce
- optional ambient input: GPIO0 / ADC1
- GPIO1: deliberately never configured or read
- native USB Serial/JTAG: development flash, logs, and recovery only

## Safe unconfigured build

The firmware builds and boots with all cells off when
`include/peri6_local_config.h` is absent. In that state it does not start Wi-Fi,
mDNS, or the WebSocket server. Public fixture secrets are never used.

Create the ignored local configuration interactively when LAN testing is ready:

```powershell
python firmware\tools\provision_local.py
```

The provisioner creates the ignored firmware header and the matching ignored
`desktop/local-config.json` used by the physical-device test console. It never
prints the LAN password or generated 32-byte device secret.

Do not copy credentials or the generated device secret into logs, issues, pack
settings, or committed files. The matching desktop test client entry is created
during the authenticated LAN integration step.

## Build, test, flash

```powershell
powershell -ExecutionPolicy Bypass -File firmware\tools\pio.ps1 test -d firmware -e native
powershell -ExecutionPolicy Bypass -File firmware\tools\pio.ps1 run -d firmware -e esp32-c3-supermini
powershell -ExecutionPolicy Bypass -File firmware\tools\pio.ps1 run -d firmware -e esp32-c3-supermini -t upload --upload-port COM12
powershell -ExecutionPolicy Bypass -File firmware\tools\pio.ps1 device monitor --port COM12 --baud 115200
```

The wrapper only works around the local Windows profile path containing spaces;
it forwards every argument unchanged to the pinned PlatformIO installation.

The P1 evidence scripts and on-device integration tests are added alongside the
implementation. A successful build or safe boot alone does not complete P1.
