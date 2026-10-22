#pragma once

// Copy to peri6_local_config.h and keep that file local/ignored.
#define PERI6_WIFI_SSID "private-lan-ssid"
#define PERI6_WIFI_PASSWORD "private-lan-password"

// Exactly 32 random bytes encoded as canonical base64url without '=' padding.
#define PERI6_DEVICE_SECRET_B64URL \
  "replace-with-a-random-43-character-base64url-value"

// Set to 1 only after an LDR circuit on GPIO0 is fitted and characterized.
#define PERI6_AMBIENT_ENABLED 0

