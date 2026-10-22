#include "peri6/device_io.h"

#include <algorithm>

#include "driver/gpio.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "peri6/config.h"

namespace peri6 {
namespace {

constexpr char kTag[] = "peri6_io";
constexpr std::uint32_t kRmtResolutionHz = 10'000'000;

}  // namespace

esp_err_t DeviceIo::begin(bool ambientEnabled) {
  // The frozen safety order is explicit: drive GPIO3 low before creating RMT.
  gpio_config_t ledGpio{};
  ledGpio.pin_bit_mask = 1ULL << kLedPin;
  ledGpio.mode = GPIO_MODE_OUTPUT;
  ledGpio.pull_up_en = GPIO_PULLUP_DISABLE;
  ledGpio.pull_down_en = GPIO_PULLDOWN_ENABLE;
  ledGpio.intr_type = GPIO_INTR_DISABLE;
  ESP_RETURN_ON_ERROR(gpio_config(&ledGpio), kTag, "configure LED GPIO");
  ESP_RETURN_ON_ERROR(gpio_set_level(static_cast<gpio_num_t>(kLedPin), 0), kTag,
                      "initialize LED GPIO low");

  rmt_tx_channel_config_t channelConfig{};
  channelConfig.clk_src = RMT_CLK_SRC_DEFAULT;
  channelConfig.gpio_num = static_cast<gpio_num_t>(kLedPin);
  channelConfig.mem_block_symbols = 64;
  channelConfig.resolution_hz = kRmtResolutionHz;
  channelConfig.trans_queue_depth = 2;
  ESP_RETURN_ON_ERROR(rmt_new_tx_channel(&channelConfig, &ledChannel_), kTag,
                      "create LED RMT channel");

  rmt_bytes_encoder_config_t encoderConfig{};
  encoderConfig.bit0.level0 = 1;
  encoderConfig.bit0.duration0 = 3;   // 0.3 us high
  encoderConfig.bit0.level1 = 0;
  encoderConfig.bit0.duration1 = 9;   // 0.9 us low
  encoderConfig.bit1.level0 = 1;
  encoderConfig.bit1.duration0 = 9;   // 0.9 us high
  encoderConfig.bit1.level1 = 0;
  encoderConfig.bit1.duration1 = 3;   // 0.3 us low
  encoderConfig.flags.msb_first = 1;
  ESP_RETURN_ON_ERROR(rmt_new_bytes_encoder(&encoderConfig, &ledEncoder_), kTag,
                      "create WS2812 encoder");
  ESP_RETURN_ON_ERROR(rmt_enable(ledChannel_), kTag, "enable LED RMT");

  gpio_config_t buttonGpio{};
  buttonGpio.pin_bit_mask = 1ULL << kButtonPin;
  buttonGpio.mode = GPIO_MODE_INPUT;
  buttonGpio.pull_up_en = GPIO_PULLUP_ENABLE;
  buttonGpio.pull_down_en = GPIO_PULLDOWN_DISABLE;
  buttonGpio.intr_type = GPIO_INTR_DISABLE;
  ESP_RETURN_ON_ERROR(gpio_config(&buttonGpio), kTag, "configure button GPIO");
  rawButtonPressed_ = gpio_get_level(static_cast<gpio_num_t>(kButtonPin)) == 0;
  stableButtonPressed_ = rawButtonPressed_;

  ambientEnabled_ = ambientEnabled;
  if (ambientEnabled_) {
    adc_oneshot_unit_init_cfg_t unitConfig{};
    unitConfig.unit_id = ADC_UNIT_1;
    unitConfig.ulp_mode = ADC_ULP_MODE_DISABLE;
    ESP_RETURN_ON_ERROR(adc_oneshot_new_unit(&unitConfig, &adcUnit_), kTag,
                        "create ADC1 unit");
    adc_oneshot_chan_cfg_t channel{};
    channel.atten = ADC_ATTEN_DB_12;
    channel.bitwidth = ADC_BITWIDTH_12;
    ESP_RETURN_ON_ERROR(adc_oneshot_config_channel(adcUnit_, ADC_CHANNEL_0,
                                                   &channel),
                        kTag, "configure GPIO0 ambient input");
  }

  // GPIO1 is intentionally never configured or referenced by this module.
  off();
  return ESP_OK;
}

void DeviceIo::off() {
  Cells cells{};
  write(cells);
}

bool DeviceIo::write(const Cells& cells) {
  if (ledChannel_ == nullptr || ledEncoder_ == nullptr) return false;
  std::uint8_t bytes[kCellCount * 3]{};
  for (std::uint8_t i = 0; i < kCellCount; ++i) {
    bytes[i * 3] = cells[i].g;
    bytes[i * 3 + 1] = cells[i].r;
    bytes[i * 3 + 2] = cells[i].b;
  }
  rmt_transmit_config_t transmit{};
  transmit.loop_count = 0;
  const std::int64_t startedUs = esp_timer_get_time();
  if (rmt_transmit(ledChannel_, ledEncoder_, bytes, sizeof(bytes), &transmit) !=
          ESP_OK ||
      rmt_tx_wait_all_done(ledChannel_, 20) != ESP_OK) {
    return false;
  }
  esp_rom_delay_us(80);  // WS2812 reset/latch interval while output stays low.
  const std::uint32_t elapsedUs =
      static_cast<std::uint32_t>(esp_timer_get_time() - startedUs);
  worstWriteUs_ = std::max(worstWriteUs_, elapsedUs);
  return true;
}

ButtonGesture DeviceIo::pollButton(std::uint64_t nowMs) {
  const bool sampled =
      gpio_get_level(static_cast<gpio_num_t>(kButtonPin)) == 0;
  if (sampled != rawButtonPressed_) {
    rawButtonPressed_ = sampled;
    rawButtonChangedMs_ = nowMs;
  }
  if (sampled == stableButtonPressed_ ||
      nowMs - rawButtonChangedMs_ < kButtonDebounceMs) {
    return {};
  }

  stableButtonPressed_ = sampled;
  if (stableButtonPressed_) {
    pressedMs_ = nowMs;
    return {};
  }

  const std::uint64_t duration = nowMs - pressedMs_;
  ButtonGesture event{};
  event.available = true;
  event.durationMs = duration > UINT32_MAX ? UINT32_MAX
                                           : static_cast<std::uint32_t>(duration);
  if (duration <= kButtonTapMaxMs)
    event.name = "tap";
  else if (duration >= kButtonLongPressMs)
    event.name = "long_press";
  else
    event.name = "press";
  return event;
}

bool DeviceIo::sampleAmbient(std::uint16_t& level) {
  if (!ambientEnabled_ || adcUnit_ == nullptr) return false;
  int raw = 0;
  if (adc_oneshot_read(adcUnit_, ADC_CHANNEL_0, &raw) != ESP_OK) return false;
  raw = std::max(0, std::min(4095, raw));
  level = static_cast<std::uint16_t>(static_cast<std::uint32_t>(raw) * 65535 /
                                     4095);
  return true;
}

}  // namespace peri6
