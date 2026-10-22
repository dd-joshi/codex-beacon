#pragma once

#include <cstddef>
#include <cstdint>

#include "peri6/model.h"

struct cJSON;

namespace peri6 {

struct SessionKeys {
  std::uint8_t clientToDevice[32]{};
  std::uint8_t deviceToClient[32]{};
};

bool base64UrlDecode(const char* encoded, std::uint8_t* output,
                     std::size_t outputCapacity, std::size_t& outputSize);
bool base64UrlEncode(const std::uint8_t* input, std::size_t inputSize,
                     char* output, std::size_t outputCapacity);
bool hexIdDecode(const char* encoded, std::uint8_t output[16]);
void randomHexId(char output[33]);
bool validHexId(const char* value);
bool validMessageType(const char* value);
bool constantTimeEqual(const std::uint8_t* left, const std::uint8_t* right,
                       std::size_t size);

bool authenticationProof(const std::uint8_t secret[32], const char* role,
                         const char* requestId, const char* sessionId,
                         const std::uint8_t clientNonce[16],
                         const std::uint8_t deviceNonce[16],
                         std::uint8_t proof[32]);
bool deriveSessionKeys(const std::uint8_t secret[32], const char* requestId,
                       const char* sessionId,
                       const std::uint8_t clientNonce[16],
                       const std::uint8_t deviceNonce[16], SessionKeys& keys);
bool messageMac(const std::uint8_t key[32], const char* type, const char* sid,
                std::uint32_t sequence, const char* encodedBody,
                std::uint8_t output[32]);

bool exactFields(const cJSON* object, const char* const* expected,
                 std::size_t expectedCount);
bool jsonUint32(const cJSON* value, std::uint32_t minimum,
                std::uint32_t maximum, std::uint32_t& output);
ValidationResult parseSceneBody(const cJSON* body, Scene& candidate);
ValidationResult parseSceneIdBody(const cJSON* body, char output[23]);

}  // namespace peri6
