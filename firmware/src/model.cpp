#include "peri6/model.h"

#include <cstring>

namespace peri6 {
namespace {

ValidationResult fail(ValidationCode code, const char* detail) {
  return {code, detail};
}

bool base64UrlCharacter(char value) {
  return (value >= 'A' && value <= 'Z') ||
         (value >= 'a' && value <= 'z') ||
         (value >= '0' && value <= '9') || value == '_' || value == '-';
}

}  // namespace

bool isCanonicalSceneId(const char* value) {
  if (value == nullptr || std::strlen(value) != 22) return false;
  for (std::uint8_t i = 0; i < 22; ++i) {
    if (!base64UrlCharacter(value[i])) return false;
  }
  const char last = value[21];
  return last == 'A' || last == 'Q' || last == 'g' || last == 'w';
}

ValidationResult validateScene(Scene& scene) {
  if (!isCanonicalSceneId(scene.id.data())) {
    return fail(ValidationCode::InvalidSceneId,
                "scene_id must canonically encode 16 bytes");
  }
  if (scene.leaseMs < kMinLeaseMs || scene.leaseMs > kMaxLeaseMs) {
    return fail(ValidationCode::OutOfRange,
                "lease_ms must be between 3000 and 5000");
  }
  if (scene.brightness > kMaxBrightness) {
    return fail(ValidationCode::OutOfRange,
                "brightness must be between 0 and 96");
  }
  if (scene.keyframeCount == 0 || scene.keyframeCount > kMaxKeyframes) {
    return fail(ValidationCode::InvalidKeyframeCount,
                "keyframes must contain 1-16 items");
  }

  std::uint64_t cycle = 0;
  for (std::uint8_t i = 0; i < scene.keyframeCount; ++i) {
    const Keyframe& frame = scene.keyframes[i];
    if (frame.transitionMs > kMaxTransitionMs) {
      return fail(ValidationCode::OutOfRange,
                  "transition duration exceeds 30000 ms");
    }
    if (frame.holdMs > kMaxHoldMs) {
      return fail(ValidationCode::OutOfRange, "hold exceeds 60000 ms");
    }
    if (frame.transition == TransitionKind::Step && frame.transitionMs != 0) {
      return fail(ValidationCode::InvalidTransition,
                  "step transition duration must be zero");
    }
    if (frame.transition == TransitionKind::Linear &&
        frame.transitionMs != 0 && frame.transitionMs < kRenderTickMs) {
      return fail(ValidationCode::InvalidTransition,
                  "linear transition must be zero or at least one render tick");
    }
    cycle += frame.transitionMs;
    cycle += frame.holdMs;
  }
  if (cycle > kMaxCycleMs) {
    return fail(ValidationCode::SceneTooLong,
                "scene cycle exceeds 120000 ms");
  }
  if (scene.playback == PlaybackMode::Loop && cycle < kMinLoopCycleMs) {
    return fail(ValidationCode::SceneTooFast,
                "loop cycle must be at least 100 ms");
  }
  scene.cycleMs = static_cast<std::uint32_t>(cycle);
  return {};
}

const char* validationCodeName(ValidationCode code) {
  switch (code) {
    case ValidationCode::Ok: return "OK";
    case ValidationCode::InvalidFields: return "INVALID_FIELDS";
    case ValidationCode::InvalidNumber: return "INVALID_NUMBER";
    case ValidationCode::OutOfRange: return "OUT_OF_RANGE";
    case ValidationCode::InvalidSceneId: return "INVALID_SCENE_ID";
    case ValidationCode::InvalidPlayback: return "INVALID_PLAYBACK";
    case ValidationCode::InvalidKeyframeCount: return "INVALID_KEYFRAME_COUNT";
    case ValidationCode::InvalidTransition: return "INVALID_TRANSITION";
    case ValidationCode::UnsupportedTransition: return "UNSUPPORTED_TRANSITION";
    case ValidationCode::InvalidCells: return "INVALID_CELLS";
    case ValidationCode::InvalidRgb: return "INVALID_RGB";
    case ValidationCode::SceneTooLong: return "SCENE_TOO_LONG";
    case ValidationCode::SceneTooFast: return "SCENE_TOO_FAST";
    case ValidationCode::BodyTooLarge: return "BODY_TOO_LARGE";
    case ValidationCode::SceneMismatch: return "SCENE_MISMATCH";
    case ValidationCode::UnsupportedType: return "UNSUPPORTED_TYPE";
  }
  return "INVALID_SCENE";
}

}  // namespace peri6
