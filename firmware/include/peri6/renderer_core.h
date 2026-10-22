#pragma once

#include <cstdint>

#include "peri6/model.h"

namespace peri6 {

class RendererCore {
 public:
  RendererCore() = default;

  void reset();
  ValidationResult load(Scene candidate, std::uint64_t nowMs);
  bool keepalive(const char* sceneId, std::uint64_t nowMs);
  bool clear(const char* sceneId, std::uint64_t nowMs);

  bool active(std::uint64_t nowMs);
  const char* activeSceneId(std::uint64_t nowMs);
  std::uint32_t leaseRemainingMs(std::uint64_t nowMs);
  int frameIndex(std::uint64_t nowMs);
  Cells renderUnscaled(std::uint64_t nowMs);
  Cells renderScaled(std::uint64_t nowMs);

 private:
  Scene scene_{};
  Cells startCells_{};
  bool active_ = false;
  std::uint64_t loadedMs_ = 0;
  std::uint64_t expiresMs_ = 0;

  void expireIfNeeded(std::uint64_t nowMs);
  Cells calculate(std::uint64_t nowMs);
};

}  // namespace peri6
