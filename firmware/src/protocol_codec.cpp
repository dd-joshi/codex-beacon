#include "peri6/protocol_codec.h"

#include <cmath>
#include <cstdio>
#include <cstring>

#include "cJSON.h"
#include "esp_random.h"
#include "mbedtls/md.h"

namespace peri6 {
namespace {

constexpr char kBase64Alphabet[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

int base64Value(char value) {
  if (value >= 'A' && value <= 'Z') return value - 'A';
  if (value >= 'a' && value <= 'z') return value - 'a' + 26;
  if (value >= '0' && value <= '9') return value - '0' + 52;
  if (value == '-') return 62;
  if (value == '_') return 63;
  return -1;
}

int hexValue(char value) {
  if (value >= '0' && value <= '9') return value - '0';
  if (value >= 'a' && value <= 'f') return value - 'a' + 10;
  return -1;
}

bool hmac(const std::uint8_t* key, std::size_t keySize,
          const std::uint8_t* data, std::size_t dataSize,
          std::uint8_t output[32]) {
  const mbedtls_md_info_t* info =
      mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  return info != nullptr &&
         mbedtls_md_hmac(info, key, keySize, data, dataSize, output) == 0;
}

bool transcript(const char* requestId, const char* sessionId,
                const std::uint8_t clientNonce[16],
                const std::uint8_t deviceNonce[16], std::uint8_t* output,
                std::size_t& size) {
  constexpr char prefix[] = "PERI6-AUTH-V1";
  std::uint8_t request[16]{};
  std::uint8_t session[16]{};
  if (!hexIdDecode(requestId, request) || !hexIdDecode(sessionId, session))
    return false;
  size = 0;
  std::memcpy(output + size, prefix, sizeof(prefix) - 1);
  size += sizeof(prefix) - 1;
  output[size++] = 0;
  std::memcpy(output + size, request, sizeof(request));
  size += sizeof(request);
  std::memcpy(output + size, session, sizeof(session));
  size += sizeof(session);
  std::memcpy(output + size, clientNonce, 16);
  size += 16;
  std::memcpy(output + size, deviceNonce, 16);
  size += 16;
  return true;
}

ValidationResult fail(ValidationCode code, const char* detail) {
  return {code, detail};
}

bool jsonString(const cJSON* value, const char*& output) {
  if (!cJSON_IsString(value) || value->valuestring == nullptr) return false;
  output = value->valuestring;
  return true;
}

}  // namespace

bool base64UrlDecode(const char* encoded, std::uint8_t* output,
                     std::size_t outputCapacity, std::size_t& outputSize) {
  outputSize = 0;
  if (encoded == nullptr || output == nullptr) return false;
  const std::size_t length = std::strlen(encoded);
  if (length % 4 == 1) return false;
  std::uint32_t accumulator = 0;
  std::uint8_t bits = 0;
  for (std::size_t i = 0; i < length; ++i) {
    const int value = base64Value(encoded[i]);
    if (value < 0) return false;
    accumulator = (accumulator << 6) | static_cast<std::uint32_t>(value);
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      if (outputSize >= outputCapacity) return false;
      output[outputSize++] = static_cast<std::uint8_t>(accumulator >> bits);
      accumulator &= bits == 0 ? 0 : ((1u << bits) - 1u);
    }
  }
  if (accumulator != 0) return false;
  const std::size_t expectedLength = (outputSize * 8 + 5) / 6;
  return expectedLength == length;
}

bool base64UrlEncode(const std::uint8_t* input, std::size_t inputSize,
                     char* output, std::size_t outputCapacity) {
  if (input == nullptr || output == nullptr) return false;
  const std::size_t required = (inputSize * 8 + 5) / 6;
  if (outputCapacity <= required) return false;
  std::uint32_t accumulator = 0;
  std::uint8_t bits = 0;
  std::size_t written = 0;
  for (std::size_t i = 0; i < inputSize; ++i) {
    accumulator = (accumulator << 8) | input[i];
    bits += 8;
    while (bits >= 6) {
      bits -= 6;
      output[written++] = kBase64Alphabet[(accumulator >> bits) & 0x3f];
      accumulator &= bits == 0 ? 0 : ((1u << bits) - 1u);
    }
  }
  if (bits != 0) output[written++] = kBase64Alphabet[accumulator << (6 - bits)];
  output[written] = '\0';
  return written == required;
}

bool hexIdDecode(const char* encoded, std::uint8_t output[16]) {
  if (!validHexId(encoded)) return false;
  for (std::uint8_t i = 0; i < 16; ++i) {
    output[i] = static_cast<std::uint8_t>((hexValue(encoded[i * 2]) << 4) |
                                          hexValue(encoded[i * 2 + 1]));
  }
  return true;
}

void randomHexId(char output[33]) {
  std::uint8_t random[16]{};
  esp_fill_random(random, sizeof(random));
  constexpr char hex[] = "0123456789abcdef";
  for (std::uint8_t i = 0; i < 16; ++i) {
    output[i * 2] = hex[random[i] >> 4];
    output[i * 2 + 1] = hex[random[i] & 0x0f];
  }
  output[32] = '\0';
}

bool validHexId(const char* value) {
  if (value == nullptr || std::strlen(value) != 32) return false;
  for (std::uint8_t i = 0; i < 32; ++i) {
    if (hexValue(value[i]) < 0) return false;
  }
  return true;
}

bool validMessageType(const char* value) {
  if (value == nullptr) return false;
  const std::size_t size = std::strlen(value);
  if (size < 2 || size > 32 || value[0] < 'A' || value[0] > 'Z') return false;
  for (std::size_t i = 1; i < size; ++i) {
    const char c = value[i];
    if (!((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_'))
      return false;
  }
  return true;
}

bool constantTimeEqual(const std::uint8_t* left, const std::uint8_t* right,
                       std::size_t size) {
  std::uint8_t difference = 0;
  for (std::size_t i = 0; i < size; ++i) difference |= left[i] ^ right[i];
  return difference == 0;
}

bool authenticationProof(const std::uint8_t secret[32], const char* role,
                         const char* requestId, const char* sessionId,
                         const std::uint8_t clientNonce[16],
                         const std::uint8_t deviceNonce[16],
                         std::uint8_t proof[32]) {
  if (secret == nullptr || role == nullptr || std::strlen(role) > 7) return false;
  std::uint8_t authTranscript[80]{};
  std::size_t transcriptSize = 0;
  if (!transcript(requestId, sessionId, clientNonce, deviceNonce,
                  authTranscript, transcriptSize))
    return false;
  std::uint8_t input[96]{};
  const std::size_t roleSize = std::strlen(role);
  std::memcpy(input, role, roleSize);
  input[roleSize] = 0;
  std::memcpy(input + roleSize + 1, authTranscript, transcriptSize);
  return hmac(secret, 32, input, roleSize + 1 + transcriptSize, proof);
}

bool deriveSessionKeys(const std::uint8_t secret[32], const char* requestId,
                       const char* sessionId,
                       const std::uint8_t clientNonce[16],
                       const std::uint8_t deviceNonce[16], SessionKeys& keys) {
  std::uint8_t authTranscript[80]{};
  std::size_t transcriptSize = 0;
  if (!transcript(requestId, sessionId, clientNonce, deviceNonce,
                  authTranscript, transcriptSize))
    return false;
  std::uint8_t sessionInput[88]{};
  constexpr char sessionLabel[] = "session";
  std::memcpy(sessionInput, sessionLabel, sizeof(sessionLabel) - 1);
  sessionInput[sizeof(sessionLabel) - 1] = 0;
  std::memcpy(sessionInput + sizeof(sessionLabel), authTranscript,
              transcriptSize);
  std::uint8_t prk[32]{};
  if (!hmac(secret, 32, sessionInput, sizeof(sessionLabel) + transcriptSize,
            prk))
    return false;
  constexpr char c2d[] = "PERI6-C2D-V1";
  constexpr char d2c[] = "PERI6-D2C-V1";
  return hmac(prk, sizeof(prk), reinterpret_cast<const std::uint8_t*>(c2d),
              sizeof(c2d) - 1, keys.clientToDevice) &&
         hmac(prk, sizeof(prk), reinterpret_cast<const std::uint8_t*>(d2c),
              sizeof(d2c) - 1, keys.deviceToClient);
}

bool messageMac(const std::uint8_t key[32], const char* type, const char* sid,
                std::uint32_t sequence, const char* encodedBody,
                std::uint8_t output[32]) {
  if (!validMessageType(type) || !validHexId(sid) || encodedBody == nullptr)
    return false;
  const mbedtls_md_info_t* info =
      mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  if (info == nullptr) return false;
  mbedtls_md_context_t context;
  mbedtls_md_init(&context);
  bool ok = mbedtls_md_setup(&context, info, 1) == 0 &&
            mbedtls_md_hmac_starts(&context, key, 32) == 0;
  const auto update = [&context, &ok](const char* value) {
    if (ok) {
      ok = mbedtls_md_hmac_update(
               &context, reinterpret_cast<const std::uint8_t*>(value),
               std::strlen(value)) == 0;
    }
  };
  char sequenceText[16]{};
  std::snprintf(sequenceText, sizeof(sequenceText), "%lu",
                static_cast<unsigned long>(sequence));
  update("PERI6-MSG-V1\n1\n");
  update(type);
  update("\n");
  update(sid);
  update("\n");
  update(sequenceText);
  update("\n");
  update(encodedBody);
  if (ok) ok = mbedtls_md_hmac_finish(&context, output) == 0;
  mbedtls_md_free(&context);
  return ok;
}

bool exactFields(const cJSON* object, const char* const* expected,
                 std::size_t expectedCount) {
  if (!cJSON_IsObject(object)) return false;
  std::size_t actualCount = 0;
  for (const cJSON* child = object->child; child != nullptr; child = child->next) {
    ++actualCount;
    bool found = false;
    for (std::size_t i = 0; i < expectedCount; ++i) {
      if (child->string != nullptr && std::strcmp(child->string, expected[i]) == 0) {
        found = true;
        break;
      }
    }
    if (!found) return false;
  }
  if (actualCount != expectedCount) return false;
  for (std::size_t i = 0; i < expectedCount; ++i) {
    if (cJSON_GetObjectItemCaseSensitive(object, expected[i]) == nullptr)
      return false;
  }
  return true;
}

bool jsonUint32(const cJSON* value, std::uint32_t minimum,
                std::uint32_t maximum, std::uint32_t& output) {
  if (!cJSON_IsNumber(value) || !std::isfinite(value->valuedouble) ||
      std::floor(value->valuedouble) != value->valuedouble ||
      value->valuedouble < minimum || value->valuedouble > maximum)
    return false;
  output = static_cast<std::uint32_t>(value->valuedouble);
  return true;
}

ValidationResult parseSceneBody(const cJSON* body, Scene& candidate) {
  static const char* fields[] = {"scene_id", "lease_ms", "brightness",
                                 "playback", "keyframes"};
  if (!exactFields(body, fields, 5))
    return fail(ValidationCode::InvalidFields, "LOAD_SCENE fields are not exact");

  const char* sceneId = nullptr;
  if (!jsonString(cJSON_GetObjectItemCaseSensitive(body, "scene_id"), sceneId) ||
      !isCanonicalSceneId(sceneId))
    return fail(ValidationCode::InvalidSceneId, "invalid scene_id");
  std::strncpy(candidate.id.data(), sceneId, candidate.id.size() - 1);

  std::uint32_t lease = 0;
  if (!jsonUint32(cJSON_GetObjectItemCaseSensitive(body, "lease_ms"),
                  kMinLeaseMs, kMaxLeaseMs, lease))
    return fail(ValidationCode::OutOfRange, "lease_ms is outside capability");
  candidate.leaseMs = lease;
  std::uint32_t brightness = 0;
  if (!jsonUint32(cJSON_GetObjectItemCaseSensitive(body, "brightness"), 0,
                  kMaxBrightness, brightness))
    return fail(ValidationCode::OutOfRange, "brightness is outside capability");
  candidate.brightness = static_cast<std::uint8_t>(brightness);

  const cJSON* playback = cJSON_GetObjectItemCaseSensitive(body, "playback");
  const cJSON* modeValue =
      cJSON_IsObject(playback) ? cJSON_GetObjectItemCaseSensitive(playback, "mode")
                               : nullptr;
  const char* mode = nullptr;
  if (!jsonString(modeValue, mode))
    return fail(ValidationCode::InvalidPlayback, "invalid playback object");
  if (std::strcmp(mode, "loop") == 0) {
    static const char* loopFields[] = {"mode"};
    if (!exactFields(playback, loopFields, 1))
      return fail(ValidationCode::InvalidPlayback, "loop fields are not exact");
    candidate.playback = PlaybackMode::Loop;
  } else if (std::strcmp(mode, "once") == 0) {
    static const char* onceFields[] = {"mode", "on_complete"};
    if (!exactFields(playback, onceFields, 2))
      return fail(ValidationCode::InvalidPlayback, "once fields are not exact");
    const char* completion = nullptr;
    if (!jsonString(cJSON_GetObjectItemCaseSensitive(playback, "on_complete"),
                    completion))
      return fail(ValidationCode::InvalidPlayback, "invalid on_complete");
    if (std::strcmp(completion, "hold") == 0)
      candidate.playback = PlaybackMode::OnceHold;
    else if (std::strcmp(completion, "off") == 0)
      candidate.playback = PlaybackMode::OnceOff;
    else
      return fail(ValidationCode::InvalidPlayback, "invalid on_complete");
  } else {
    return fail(ValidationCode::InvalidPlayback, "invalid playback mode");
  }

  const cJSON* frames = cJSON_GetObjectItemCaseSensitive(body, "keyframes");
  const int frameCount = cJSON_IsArray(frames) ? cJSON_GetArraySize(frames) : 0;
  if (frameCount < 1 || frameCount > kMaxKeyframes)
    return fail(ValidationCode::InvalidKeyframeCount,
                "keyframes must contain 1-16 items");
  candidate.keyframeCount = static_cast<std::uint8_t>(frameCount);

  for (int index = 0; index < frameCount; ++index) {
    const cJSON* frame = cJSON_GetArrayItem(frames, index);
    static const char* frameFields[] = {"transition", "hold_ms", "cells"};
    if (!exactFields(frame, frameFields, 3))
      return fail(ValidationCode::InvalidFields, "keyframe fields are not exact");
    const cJSON* transition =
        cJSON_GetObjectItemCaseSensitive(frame, "transition");
    static const char* transitionFields[] = {"kind", "duration_ms"};
    if (!exactFields(transition, transitionFields, 2))
      return fail(ValidationCode::InvalidTransition,
                  "transition fields are not exact");
    const char* kind = nullptr;
    if (!jsonString(cJSON_GetObjectItemCaseSensitive(transition, "kind"), kind))
      return fail(ValidationCode::InvalidTransition, "invalid transition kind");
    if (std::strcmp(kind, "step") == 0)
      candidate.keyframes[index].transition = TransitionKind::Step;
    else if (std::strcmp(kind, "linear") == 0)
      candidate.keyframes[index].transition = TransitionKind::Linear;
    else
      return fail(ValidationCode::UnsupportedTransition,
                  "transition is not supported");
    std::uint32_t transitionMs = 0;
    if (!jsonUint32(cJSON_GetObjectItemCaseSensitive(transition, "duration_ms"),
                    0, kMaxTransitionMs, transitionMs))
      return fail(ValidationCode::OutOfRange,
                  "transition duration is outside capability");
    candidate.keyframes[index].transitionMs = transitionMs;
    std::uint32_t holdMs = 0;
    if (!jsonUint32(cJSON_GetObjectItemCaseSensitive(frame, "hold_ms"), 0,
                    kMaxHoldMs, holdMs))
      return fail(ValidationCode::OutOfRange, "hold is outside capability");
    candidate.keyframes[index].holdMs = holdMs;

    const cJSON* cells = cJSON_GetObjectItemCaseSensitive(frame, "cells");
    if (!cJSON_IsArray(cells) || cJSON_GetArraySize(cells) != kCellCount)
      return fail(ValidationCode::InvalidCells,
                  "keyframe must contain exactly six cells");
    for (std::uint8_t cell = 0; cell < kCellCount; ++cell) {
      const cJSON* rgb = cJSON_GetArrayItem(cells, cell);
      if (!cJSON_IsArray(rgb) || cJSON_GetArraySize(rgb) != 3)
        return fail(ValidationCode::InvalidCells,
                    "cell must contain exactly three channels");
      std::uint32_t channels[3]{};
      for (std::uint8_t channel = 0; channel < 3; ++channel) {
        if (!jsonUint32(cJSON_GetArrayItem(rgb, channel), 0, 255,
                        channels[channel]))
          return fail(ValidationCode::InvalidRgb,
                      "RGB channel must be an integer from 0 to 255");
      }
      candidate.keyframes[index].cells[cell] = {
          static_cast<std::uint8_t>(channels[0]),
          static_cast<std::uint8_t>(channels[1]),
          static_cast<std::uint8_t>(channels[2])};
    }
  }
  return validateScene(candidate);
}

ValidationResult parseSceneIdBody(const cJSON* body, char output[23]) {
  static const char* fields[] = {"scene_id"};
  if (!exactFields(body, fields, 1))
    return fail(ValidationCode::InvalidFields, "body fields are not exact");
  const char* id = nullptr;
  if (!jsonString(cJSON_GetObjectItemCaseSensitive(body, "scene_id"), id) ||
      !isCanonicalSceneId(id))
    return fail(ValidationCode::InvalidSceneId, "invalid scene_id");
  std::strncpy(output, id, 22);
  output[22] = '\0';
  return {};
}

}  // namespace peri6
