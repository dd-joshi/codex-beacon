#include "peri6/renderer_core.h"

#include <cstring>

namespace peri6 {
namespace {

std::int64_t floorDivide(std::int64_t numerator, std::int64_t denominator) {
  if (numerator >= 0) return numerator / denominator;
  return -((-numerator + denominator - 1) / denominator);
}

std::uint8_t interpolate(std::uint8_t from, std::uint8_t to,
                         std::uint64_t elapsed, std::uint32_t duration) {
  if (duration == 0) return to;
  const std::int64_t delta = static_cast<std::int64_t>(to) - from;
  const std::int64_t change =
      floorDivide(delta * static_cast<std::int64_t>(elapsed), duration);
  return static_cast<std::uint8_t>(static_cast<std::int64_t>(from) + change);
}

}  // namespace

void RendererCore::reset() {
  scene_ = {};
  startCells_ = {};
  active_ = false;
  loadedMs_ = 0;
  expiresMs_ = 0;
}

ValidationResult RendererCore::load(Scene candidate, std::uint64_t nowMs) {
  const ValidationResult validation = validateScene(candidate);
  if (!validation) return validation;

  const Cells instantaneous = renderUnscaled(nowMs);
  scene_ = candidate;
  startCells_ = instantaneous;
  loadedMs_ = nowMs;
  expiresMs_ = nowMs + scene_.leaseMs;
  active_ = true;
  return {};
}

bool RendererCore::keepalive(const char* sceneId, std::uint64_t nowMs) {
  expireIfNeeded(nowMs);
  if (!active_ || sceneId == nullptr ||
      std::strcmp(scene_.id.data(), sceneId) != 0) {
    return false;
  }
  expiresMs_ = nowMs + scene_.leaseMs;
  return true;
}

bool RendererCore::clear(const char* sceneId, std::uint64_t nowMs) {
  expireIfNeeded(nowMs);
  if (!active_ || sceneId == nullptr ||
      std::strcmp(scene_.id.data(), sceneId) != 0) {
    return false;
  }
  reset();
  return true;
}

bool RendererCore::active(std::uint64_t nowMs) {
  expireIfNeeded(nowMs);
  return active_;
}

const char* RendererCore::activeSceneId(std::uint64_t nowMs) {
  expireIfNeeded(nowMs);
  return active_ ? scene_.id.data() : nullptr;
}

std::uint32_t RendererCore::leaseRemainingMs(std::uint64_t nowMs) {
  expireIfNeeded(nowMs);
  if (!active_) return 0;
  return static_cast<std::uint32_t>(expiresMs_ - nowMs);
}

int RendererCore::frameIndex(std::uint64_t nowMs) {
  expireIfNeeded(nowMs);
  if (!active_) return -1;
  std::uint64_t elapsed = nowMs - loadedMs_;
  if (scene_.playback == PlaybackMode::Loop) {
    elapsed %= scene_.cycleMs;
  } else if (elapsed >= scene_.cycleMs) {
    return scene_.keyframeCount - 1;
  }
  std::uint64_t cursor = 0;
  for (std::uint8_t i = 0; i < scene_.keyframeCount; ++i) {
    cursor += scene_.keyframes[i].transitionMs + scene_.keyframes[i].holdMs;
    if (elapsed < cursor) return i;
  }
  return scene_.keyframeCount - 1;
}

Cells RendererCore::renderUnscaled(std::uint64_t nowMs) {
  expireIfNeeded(nowMs);
  return calculate(nowMs);
}

Cells RendererCore::renderScaled(std::uint64_t nowMs) {
  Cells output = renderUnscaled(nowMs);
  if (!active_) return output;
  for (Rgb& cell : output) {
    cell.r = static_cast<std::uint16_t>(cell.r) * scene_.brightness / 255;
    cell.g = static_cast<std::uint16_t>(cell.g) * scene_.brightness / 255;
    cell.b = static_cast<std::uint16_t>(cell.b) * scene_.brightness / 255;
  }
  return output;
}

void RendererCore::expireIfNeeded(std::uint64_t nowMs) {
  if (active_ && nowMs >= expiresMs_) reset();
}

Cells RendererCore::calculate(std::uint64_t nowMs) {
  Cells output{};
  if (!active_) return output;

  std::uint64_t elapsed = nowMs - loadedMs_;
  const Cells* source = &startCells_;
  if (scene_.playback == PlaybackMode::Loop && elapsed >= scene_.cycleMs) {
    elapsed %= scene_.cycleMs;
    source = &scene_.keyframes[scene_.keyframeCount - 1].cells;
  } else if (scene_.playback != PlaybackMode::Loop &&
             elapsed >= scene_.cycleMs) {
    if (scene_.playback == PlaybackMode::OnceHold) {
      return scene_.keyframes[scene_.keyframeCount - 1].cells;
    }
    return output;
  }

  std::uint64_t cursor = 0;
  for (std::uint8_t i = 0; i < scene_.keyframeCount; ++i) {
    const Keyframe& frame = scene_.keyframes[i];
    const std::uint64_t transitionEnd = cursor + frame.transitionMs;
    if (elapsed < transitionEnd) {
      const std::uint64_t within = elapsed - cursor;
      for (std::uint8_t cell = 0; cell < kCellCount; ++cell) {
        output[cell].r = interpolate((*source)[cell].r, frame.cells[cell].r,
                                     within, frame.transitionMs);
        output[cell].g = interpolate((*source)[cell].g, frame.cells[cell].g,
                                     within, frame.transitionMs);
        output[cell].b = interpolate((*source)[cell].b, frame.cells[cell].b,
                                     within, frame.transitionMs);
      }
      return output;
    }
    cursor = transitionEnd;
    const std::uint64_t holdEnd = cursor + frame.holdMs;
    if (elapsed < holdEnd) return frame.cells;
    cursor = holdEnd;
    source = &frame.cells;
  }
  return scene_.keyframes[scene_.keyframeCount - 1].cells;
}

}  // namespace peri6
