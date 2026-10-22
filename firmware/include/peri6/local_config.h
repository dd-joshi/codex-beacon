#pragma once

#if __has_include("peri6_local_config.h")
#include "peri6_local_config.h"
#define PERI6_LOCAL_CONFIG_AVAILABLE 1
#else
#define PERI6_LOCAL_CONFIG_AVAILABLE 0
#define PERI6_WIFI_SSID ""
#define PERI6_WIFI_PASSWORD ""
#define PERI6_DEVICE_SECRET_B64URL ""
#define PERI6_AMBIENT_ENABLED 0
#endif

