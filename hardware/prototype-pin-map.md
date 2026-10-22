# ESP32-C3 prototype pin map

**Status:** P0 pin assignment and inspected prototype carrier confirmed on 14 August 2026.

## Inspected prototype carrier

- Carrier: common ESP32-C3 SuperMini development board; the inspected sample has no separate PCB revision marking.
- Device check: ESP32-C3 revision v0.4 with 4 MB embedded flash, detected over native USB Serial/JTAG on COM12.
- Evidence: founder/embedded-engineer inspection confirmed GPIO0, GPIO1, GPIO3, and GPIO10 are exposed and unused by onboard peripherals on this sample.
- Wiring disposition confirmed: WS2812 `DIN` on GPIO3, external button from GPIO10 to GND, common signal ground, and GPIO1 physically unconnected.

This evidence applies to the inspected prototype only. It does not qualify other unstandardized SuperMini clones.

## Selected pins

| Function | ESP32-C3 pin | Firmware direction | P0 disposition |
|---|---:|---|---|
| Six-LED WS2812 data | GPIO3 | Output | Use now |
| Ambient LDR input | GPIO0 / ADC1_CH0 | Analog input | Available for P1 ambient sensing |
| Battery-monitor input | GPIO1 / ADC1_CH1 | Analog input | Reserved only; do not connect or implement in this repository |
| User button | GPIO10 | Digital input with internal pull-up | Use now; momentary switch to GND, pressed = `LOW` |

This selection keeps both analog inputs on ADC1. GPIO3 and GPIO10 are ordinary digital GPIOs during application runtime. It avoids:

- GPIO2, GPIO8, and GPIO9, which are ESP32-C3 strapping pins;
- GPIO5 / ADC2_CH0, avoiding an unnecessary ADC2 dependency while Wi-Fi is active;
- GPIO12 through GPIO17, normally used by SPI flash;
- GPIO18 and GPIO19, used by native USB/JTAG;
- GPIO20 and GPIO21, normally used for UART0;
- GPIO4 through GPIO7, which can be assigned to external JTAG on a specially reconfigured chip;
- GPIO8, which also drives the onboard RGB LED on Espressif's C3 DevKitM-1 and on some compatible boards.

The assignments are valid for an ESP32-C3-DevKitM-1 and for a common ESP32-C3 SuperMini only when all four pins are actually broken out and not repurposed by that particular carrier. This assumes the normal in-package-flash module, no fitted 32.768 kHz crystal on GPIO0/GPIO1, and default USB-JTAG routing rather than altered JTAG eFuses. Clone layouts are not standardized, so inspect the silk labels or board schematic before wiring.

## Signal rules for this prototype

- Configure GPIO3 as the WS2812/RMT output and initialize its output level low before starting the LED driver.
- Configure GPIO0 as the LDR's ADC1 input. Keep GPIO1 unconfigured, physically unconnected, and reserved for the excluded future battery-monitor scope.
- Configure GPIO10 as `INPUT_PULLUP`; connect the external momentary button only between GPIO10 and GND. Do not reuse the board's BOOT or RESET button.
- Debounce the button in firmware for 30 ms. The firmware reports semantic-free gestures; the desktop's active pack assigns application meaning.
- Use a common signal ground between the ESP and the existing LED assembly. Verify that the particular WS2812 assembly accepts the ESP's 3.3 V data-high level; add an appropriate logic-level interface if it does not. This is a signal-interface check, not battery/power-system development.

## Explicit battery boundary

GPIO1 is a namespace and routing reservation only. No voltage divider, filter, calibration, battery chemistry, charging, protection, conversion, state-of-charge model, runtime estimate, indication, sleep behavior, or battery firmware is authorized by this file.

## Before first firmware flash

Record the exact carrier name/revision or add clear front/back photos here, then verify:

1. silk labels expose GPIO0, GPIO1, GPIO3, and GPIO10;
2. no onboard peripheral or existing desk wiring uses those pins;
3. the LED data wire reaches GPIO3 and the first LED's `DIN`, not `DOUT`;
4. the external button is GPIO10-to-GND and not connected to BOOT/EN;
5. GPIO1 remains physically unconnected during the current software-only scope.

Official references: [ESP32-C3 GPIO restrictions](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-reference/peripherals/gpio.html), [ESP32-C3 ADC channel map](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/peripherals/adc/index.html), and [ESP32-C3-DevKitM-1 header map](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html).
