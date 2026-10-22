#pragma once

#include <array>
#include <cstdint>

#include "peri6/config.h"

namespace peri6 {

struct Rgb {
  std::uint8_t r = 0;
  std::uint8_t g = 0;
  std::uint8_t b = 0;

  bool operator==(const Rgb& other) const {
    return r == other.r && g == other.g && b == other.b;
  }
};

using Cells = std::array<Rgb, kCellCount>;

enum class TransitionKind : std::uint8_t { Step, Linear };
enum class PlaybackMode : std::uint8_t { Loop, OnceHold, OnceOff };

struct Keyframe {
  TransitionKind transition = TransitionKind::Step;
  std::uint32_t transitionMs = 0;
  std::uint32_t holdMs = 0;
  Cells cells{};
};

struct Scene {
  std::array<char, 23> id{};
  std::uint32_t leaseMs = kDefaultLeaseMs;
  std::uint8_t brightness = 0;
  PlaybackMode playback = PlaybackMode::Loop;
  std::uint8_t keyframeCount = 0;
  std::uint32_t cycleMs = 0;
  std::array<Keyframe, kMaxKeyframes> keyframes{};
};

enum class ValidationCode : std::uint8_t {
  Ok,
  InvalidFields,
  InvalidNumber,
  OutOfRange,
  InvalidSceneId,
  InvalidPlayback,
  InvalidKeyframeCount,
  InvalidTransition,
  UnsupportedTransition,
  InvalidCells,
  InvalidRgb,
  SceneTooLong,
  SceneTooFast,
  BodyTooLarge,
  SceneMismatch,
  UnsupportedType,
};

struct ValidationResult {
  ValidationCode code = ValidationCode::Ok;
  const char* detail = "accepted";

  explicit operator bool() const { return code == ValidationCode::Ok; }
};

ValidationResult validateScene(Scene& scene);
const char* validationCodeName(ValidationCode code);
bool isCanonicalSceneId(const char* value);

}  // namespace peri6
