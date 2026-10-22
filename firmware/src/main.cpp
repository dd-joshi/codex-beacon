#include <algorithm>
#include <cstdio>
#include <cstring>

#include "esp_event.h"
#include "esp_check.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "mdns.h"
#include "mbedtls/platform_util.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "peri6/config.h"
#include "peri6/device_io.h"
#include "peri6/local_config.h"
#include "peri6/protocol_codec.h"
#include "peri6/session_server.h"

namespace {

constexpr char kTag[] = "peri6";
constexpr EventBits_t kNetworkReady = BIT0;

EventGroupHandle_t gNetworkEvents = nullptr;

std::uint64_t nowMs() {
  return static_cast<std::uint64_t>(esp_timer_get_time() / 1000);
}

void networkEvent(void*, esp_event_base_t base, int32_t id, void* data) {
  if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
    const auto* disconnected =
        static_cast<const wifi_event_sta_disconnected_t*>(data);
    ESP_LOGW(kTag, "Wi-Fi station disconnected (reason=%u); reconnecting",
             disconnected == nullptr ? 0U
                                     : static_cast<unsigned>(disconnected->reason));
    xEventGroupClearBits(gNetworkEvents, kNetworkReady);
    const esp_err_t reconnect = esp_wifi_connect();
    if (reconnect != ESP_OK) {
      ESP_LOGW(kTag, "Wi-Fi reconnect request failed: %s",
               esp_err_to_name(reconnect));
    }
  } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
    const auto* address = static_cast<const ip_event_got_ip_t*>(data);
    if (address != nullptr) {
      ESP_LOGI(kTag, "IPv4 address " IPSTR, IP2STR(&address->ip_info.ip));
    }
    xEventGroupSetBits(gNetworkEvents, kNetworkReady);
  }
}

esp_err_t startWifi(const char* ssid, const char* password) {
  ESP_RETURN_ON_ERROR(esp_netif_init(), kTag, "initialize network interface");
  const esp_err_t eventLoop = esp_event_loop_create_default();
  if (eventLoop != ESP_OK && eventLoop != ESP_ERR_INVALID_STATE) return eventLoop;
  if (esp_netif_create_default_wifi_sta() == nullptr) return ESP_FAIL;

  wifi_init_config_t initialization = WIFI_INIT_CONFIG_DEFAULT();
  ESP_RETURN_ON_ERROR(esp_wifi_init(&initialization), kTag, "initialize Wi-Fi");
  ESP_RETURN_ON_ERROR(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                                 &networkEvent, nullptr),
                      kTag, "register Wi-Fi events");
  ESP_RETURN_ON_ERROR(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                                 &networkEvent, nullptr),
                      kTag, "register IP events");

  wifi_config_t station{};
  std::strncpy(reinterpret_cast<char*>(station.sta.ssid), ssid,
               sizeof(station.sta.ssid) - 1);
  std::strncpy(reinterpret_cast<char*>(station.sta.password), password,
               sizeof(station.sta.password) - 1);
  station.sta.threshold.authmode =
      password[0] == '\0' ? WIFI_AUTH_OPEN : WIFI_AUTH_WPA2_PSK;
  station.sta.pmf_cfg.capable = true;
  station.sta.pmf_cfg.required = false;
  station.sta.sae_pwe_h2e = WPA3_SAE_PWE_BOTH;

  ESP_RETURN_ON_ERROR(esp_wifi_set_storage(WIFI_STORAGE_FLASH), kTag,
                      "persist Wi-Fi config storage");
  ESP_RETURN_ON_ERROR(esp_wifi_set_mode(WIFI_MODE_STA), kTag,
                      "set Wi-Fi station mode");
  ESP_RETURN_ON_ERROR(esp_wifi_set_config(WIFI_IF_STA, &station), kTag,
                      "set Wi-Fi configuration");
  ESP_RETURN_ON_ERROR(esp_wifi_start(), kTag, "start Wi-Fi");
  return esp_wifi_connect();
}

esp_err_t startMdns(const char* deviceId) {
  ESP_RETURN_ON_ERROR(mdns_init(), kTag, "initialize mDNS");
  ESP_RETURN_ON_ERROR(mdns_hostname_set(deviceId), kTag, "set mDNS hostname");
  char instance[64]{};
  std::snprintf(instance, sizeof(instance), "peri6-%s", deviceId);
  ESP_RETURN_ON_ERROR(mdns_instance_name_set(instance), kTag,
                      "set mDNS instance");
  mdns_txt_item_t text[] = {{"pv", "1"}, {"id", deviceId},
                            {"path", peri6::kWebSocketPath}};
  return mdns_service_add(instance, "_peri6", "_tcp", peri6::kWebSocketPort,
                          text, sizeof(text) / sizeof(text[0]));
}

void createDeviceId(char output[36]) {
  std::uint8_t mac[6]{};
  ESP_ERROR_CHECK(esp_read_mac(mac, ESP_MAC_WIFI_STA));
  std::snprintf(output, 36, "p6-c3-%02x%02x%02x", mac[3], mac[4], mac[5]);
}

bool localConfiguration(std::uint8_t secret[32]) {
#if PERI6_LOCAL_CONFIG_AVAILABLE
  if (std::strlen(PERI6_WIFI_SSID) == 0 || std::strlen(PERI6_WIFI_SSID) > 32 ||
      std::strlen(PERI6_WIFI_PASSWORD) > 63)
    return false;
  std::size_t size = 0;
  return peri6::base64UrlDecode(PERI6_DEVICE_SECRET_B64URL, secret, 32, size) &&
         size == 32;
#else
  (void)secret;
  return false;
#endif
}

constexpr char kNvsNamespace[] = "peri6";
constexpr char kNvsSsid[] = "wifi.ssid";
constexpr char kNvsPassword[] = "wifi.pass";
constexpr char kNvsSecret[] = "dev.secret";

bool loadStoredWifi(char* ssid, size_t ssidCap, char* password, size_t passwordCap) {
  nvs_handle_t handle = 0;
  if (nvs_open(kNvsNamespace, NVS_READONLY, &handle) != ESP_OK) return false;
  size_t ssidSize = ssidCap;
  size_t passwordSize = passwordCap;
  const bool ok =
      nvs_get_str(handle, kNvsSsid, ssid, &ssidSize) == ESP_OK &&
      nvs_get_str(handle, kNvsPassword, password, &passwordSize) == ESP_OK &&
      ssidSize > 1;
  nvs_close(handle);
  return ok;
}

bool loadStoredSecret(std::uint8_t secret[32]) {
  nvs_handle_t handle = 0;
  if (nvs_open(kNvsNamespace, NVS_READONLY, &handle) != ESP_OK) return false;
  size_t size = 32;
  const bool ok = nvs_get_blob(handle, kNvsSecret, secret, &size) == ESP_OK &&
                  size == 32;
  nvs_close(handle);
  return ok;
}

bool saveProvisioned(const char* ssid, const char* password,
                     const std::uint8_t secret[32]) {
  nvs_handle_t handle = 0;
  if (nvs_open(kNvsNamespace, NVS_READWRITE, &handle) != ESP_OK) return false;
  const bool ok = nvs_set_str(handle, kNvsSsid, ssid) == ESP_OK &&
                  nvs_set_str(handle, kNvsPassword, password) == ESP_OK &&
                  nvs_set_blob(handle, kNvsSecret, secret, 32) == ESP_OK &&
                  nvs_commit(handle) == ESP_OK;
  nvs_close(handle);
  return ok;
}

void eraseProvisioned() {
  nvs_handle_t handle = 0;
  if (nvs_open(kNvsNamespace, NVS_READWRITE, &handle) != ESP_OK) return;
  nvs_erase_key(handle, kNvsSsid);
  nvs_erase_key(handle, kNvsPassword);
  nvs_erase_key(handle, kNvsSecret);
  nvs_commit(handle);
  nvs_close(handle);
}

// One console line (no echo side effects beyond the bootloader default).
bool readLineTimeout(char* out, size_t cap, std::uint64_t timeoutMs) {
  size_t used = 0;
  const std::uint64_t deadline = nowMs() + timeoutMs;
  while (nowMs() < deadline) {
    char character = 0;
    const int read = uart_read_bytes(UART_NUM_0, &character, 1,
                                     pdMS_TO_TICKS(50));
    if (read <= 0) continue;
    if (character == '\r') continue;
    if (character == '\n') {
      out[used] = '\0';
      return true;
    }
    if (used + 1 < cap) out[used++] = character;
  }
  return false;
}

// Blocks until a friend's desktop sends the four-line provisioning frame:
//   PERI6 / <ssid> / <password> / <device-secret b64url>
// The password is parsed straight into NVS and never logged.
bool provisionOverUsb(char* ssid, size_t ssidCap, char* password,
                      size_t passwordCap, std::uint8_t secret[32]) {
  uart_driver_install(UART_NUM_0, 1024, 0, 0, nullptr, 0);
  uart_config_t uartConfig{};
  uartConfig.baud_rate = 115200;
  uartConfig.data_bits = UART_DATA_8_BITS;
  uartConfig.parity = UART_PARITY_DISABLE;
  uartConfig.stop_bits = UART_STOP_BITS_1;
  uartConfig.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  uartConfig.source_clk = UART_SCLK_DEFAULT;
  uart_param_config(UART_NUM_0, &uartConfig);
  ESP_LOGI(kTag,
           "USB provisioning ready. Send: PERI6 / <ssid> / <password> / "
           "<secret>. ESP32-C3 supports 2.4 GHz Wi-Fi only.");
  char line[128]{};
  while (true) {
    if (!readLineTimeout(line, sizeof(line), 30000)) continue;
    if (std::strcmp(line, "PERI6RESET") == 0) {
      eraseProvisioned();
      std::printf("RESET\n");
      fflush(stdout);
      esp_restart();
    }
    if (std::strncmp(line, "PERI6 / ", 8) != 0) continue;
    char* cursor = line + 8;
    char* separator = std::strchr(cursor, '/');
    if (separator == nullptr) continue;
    *separator = '\0';
    // Trim the single trailing space before '/'.
    if (cursor > line && *(separator - 1) == ' ') *(separator - 1) = '\0';
    char* next = separator + 1;
    separator = std::strchr(next, '/');
    if (separator == nullptr) continue;
    *separator = '\0';
    if (*(separator - 1) == ' ') *(separator - 1) = '\0';
    char* secretLine = separator + 1;
    while (*secretLine == ' ') ++secretLine;

    if (std::strlen(cursor) == 0 || std::strlen(cursor) > 32 ||
        std::strlen(next) > 63) {
      std::printf("ERR ssid/password length (SSID 1..32, key <=63)\n");
      continue;
    }
    std::size_t decoded = 0;
    if (!peri6::base64UrlDecode(secretLine, secret, 32, decoded) ||
        decoded != 32) {
      std::printf("ERR device secret must be 32 bytes, base64url\n");
      continue;
    }
    if (std::strlen(cursor) >= ssidCap || std::strlen(next) >= passwordCap)
      continue;
    std::snprintf(ssid, ssidCap, "%s", cursor);
    std::snprintf(password, passwordCap, "%s", next);
    if (!saveProvisioned(ssid, password, secret)) {
      std::printf("ERR could not write NVS\n");
      continue;
    }
    mbedtls_platform_zeroize(line, sizeof(line));
    std::printf("OK provisioned; joining network\n");
    return true;
  }
}

}  // namespace

extern "C" void app_main() {
  ESP_LOGI(kTag, "Peri6 firmware %s booting", peri6::kFirmwareVersion);

  esp_err_t nvs = nvs_flash_init();
  if (nvs == ESP_ERR_NVS_NO_FREE_PAGES ||
      nvs == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    nvs = nvs_flash_init();
  }
  ESP_ERROR_CHECK(nvs);

  peri6::DeviceIo device;
  const bool requestedAmbient = PERI6_AMBIENT_ENABLED == 1;
  ESP_ERROR_CHECK(device.begin(requestedAmbient));
  device.off();

  char deviceId[36]{};
  char bootId[33]{};
  createDeviceId(deviceId);
  peri6::randomHexId(bootId);

  char wifiSsid[33]{};
  char wifiPassword[64]{};
  const bool storedWifi =
      loadStoredWifi(wifiSsid, sizeof(wifiSsid), wifiPassword, sizeof(wifiPassword));
  std::uint8_t secret[32]{};
  bool configured = localConfiguration(secret);
  if (!configured && loadStoredSecret(secret)) {
    configured = true;
  }
  if (!storedWifi && configured) {
    std::snprintf(wifiSsid, sizeof(wifiSsid), "%s", PERI6_WIFI_SSID);
    std::snprintf(wifiPassword, sizeof(wifiPassword), "%s", PERI6_WIFI_PASSWORD);
  }
  if (!configured && !storedWifi) {
    ESP_LOGW(kTag,
             "ESP32-C3 supports 2.4 GHz Wi-Fi only; waiting on USB serial for "
             "provisioning credentials");
    configured = provisionOverUsb(wifiSsid, sizeof(wifiSsid), wifiPassword,
                                  sizeof(wifiPassword), secret);
  }
  peri6::SessionServer sessions;
  if (configured && !sessions.configure(secret, deviceId, bootId,
                                        device.ambientEnabled())) {
    ESP_LOGE(kTag, "local configuration validation failed");
    esp_restart();
  }
  mbedtls_platform_zeroize(secret, sizeof(secret));

  gNetworkEvents = xEventGroupCreate();
  if (gNetworkEvents == nullptr) {
    ESP_LOGE(kTag, "could not allocate network event group");
    esp_restart();
  }
  if (configured) {
    ESP_ERROR_CHECK(startWifi(wifiSsid, wifiPassword));
    ESP_LOGI(kTag, "private-LAN station configured; awaiting address");
  } else {
    ESP_LOGW(kTag,
             "safe unconfigured mode: LEDs off; Wi-Fi, mDNS, and WebSocket disabled");
  }

  const esp_err_t watchdog = esp_task_wdt_add(nullptr);
  if (watchdog != ESP_OK && watchdog != ESP_ERR_INVALID_STATE) {
    ESP_LOGW(kTag, "could not subscribe main task to watchdog: %s",
             esp_err_to_name(watchdog));
  }

  bool servicesRunning = false;
  std::uint64_t nextRenderMs = 0;
  std::uint64_t nextAmbientMs = 5000;
  std::uint64_t nextMetricsMs = 60000;
  std::size_t minimumFreeHeap = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
  constexpr TickType_t kMainLoopDelayTicks = 1;  // 10 ms at the frozen 100 Hz tick.
  while (true) {
    const std::uint64_t currentMs = nowMs();
    sessions.tick(currentMs);
    const bool networkReady = configured &&
        (xEventGroupGetBits(gNetworkEvents) & kNetworkReady) != 0;
    if (networkReady && !servicesRunning) {
      if (startMdns(deviceId) == ESP_OK && sessions.start() == ESP_OK) {
        servicesRunning = true;
        ESP_LOGI(kTag, "LAN services ready for authenticated controller");
      } else {
        sessions.stop();
        mdns_free();
        ESP_LOGE(kTag, "LAN service start failed; retrying after reconnect");
      }
    } else if (!networkReady && servicesRunning) {
      sessions.stop();
      mdns_free();
      servicesRunning = false;
      ESP_LOGW(kTag, "network lost; scene lease continues toward all-off expiry");
    }

    if (currentMs >= nextRenderMs) {
      device.write(sessions.render(currentMs));
      nextRenderMs = currentMs + peri6::kRenderTickMs;
    }
    const peri6::ButtonGesture button = device.pollButton(currentMs);
    if (button.available) sessions.emitButton(button.name, button.durationMs);

    if (device.ambientEnabled() && currentMs >= nextAmbientMs) {
      std::uint16_t level = 0;
      if (device.sampleAmbient(level)) sessions.emitAmbient(level);
      nextAmbientMs = currentMs + 5000;
    }

    minimumFreeHeap = std::min(
        minimumFreeHeap, heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
    if (currentMs >= nextMetricsMs) {
      ESP_LOGI(kTag,
               "metrics min_heap=%u largest_block=%u max_frame=%u max_body=%u "
               "worst_led_us=%u",
               static_cast<unsigned>(minimumFreeHeap),
               static_cast<unsigned>(
                   heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL)),
               static_cast<unsigned>(sessions.largestFrameSeen()),
               static_cast<unsigned>(sessions.largestBodySeen()),
               static_cast<unsigned>(device.worstWriteUs()));
      nextMetricsMs = currentMs + 60000;
    }

    esp_task_wdt_reset();
    vTaskDelay(kMainLoopDelayTicks);
  }
}
