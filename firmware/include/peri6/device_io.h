#pragma once

#include <cstdint>

#include "driver/rmt_tx.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_err.h"
#include "peri6/model.h"

namespace peri6 {

struct ButtonGesture {
  bool available = false;
  const char* name = nullptr;
  std::uint32_t durationMs = 0;
};

class DeviceIo {
 public:
  esp_err_t begin(bool ambientEnabled);
  void off();
  bool write(const Cells& cells);
  ButtonGesture pollButton(std::uint64_t nowMs);
  bool sampleAmbient(std::uint16_t& level);

  std::uint32_t worstWriteUs() const { return worstWriteUs_; }
  bool ambientEnabled() const { return ambientEnabled_; }

 private:
  rmt_channel_handle_t ledChannel_ = nullptr;
  rmt_encoder_handle_t ledEncoder_ = nullptr;
  adc_oneshot_unit_handle_t adcUnit_ = nullptr;
  bool ambientEnabled_ = false;
  bool rawButtonPressed_ = false;
  bool stableButtonPressed_ = false;
  std::uint64_t rawButtonChangedMs_ = 0;
  std::uint64_t pressedMs_ = 0;
  std::uint32_t worstWriteUs_ = 0;
};

}  // namespace peri6
