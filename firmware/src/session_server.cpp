#include "peri6/session_server.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "cJSON.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "lwip/sockets.h"
#include "mbedtls/platform_util.h"
#include "peri6/config.h"
#include "peri6/strict_json.h"

namespace peri6 {
namespace {

constexpr char kTag[] = "peri6_session";
constexpr std::uint8_t kMaxAuthFailures = 5;
constexpr std::uint64_t kAuthWindowMs = 60000;

struct EventWork {
  SessionServer* server = nullptr;
  char type[16]{};
  char body[192]{};
};

std::uint64_t nowMs() {
  return static_cast<std::uint64_t>(esp_timer_get_time() / 1000);
}

bool semver(const char* value) {
  if (value == nullptr || *value == '\0') return false;
  const char* cursor = value;
  for (std::uint8_t part = 0; part < 3; ++part) {
    if (*cursor < '0' || *cursor > '9') return false;
    if (*cursor == '0' && cursor[1] >= '0' && cursor[1] <= '9') return false;
    while (*cursor >= '0' && *cursor <= '9') ++cursor;
    if (part < 2) {
      if (*cursor++ != '.') return false;
    } else if (*cursor != '\0') {
      return false;
    }
  }
  return true;
}

bool jsonUint(const cJSON* value, std::uint32_t min, std::uint32_t max,
              std::uint32_t& output) {
  return jsonUint32(value, min, max, output);
}

const char* jsonString(const cJSON* object, const char* name) {
  const cJSON* value = cJSON_GetObjectItemCaseSensitive(object, name);
  return cJSON_IsString(value) ? value->valuestring : nullptr;
}

void safeDetail(const char* input, char output[161]) {
  std::size_t written = 0;
  if (input != nullptr) {
    while (*input != '\0' && written < 160) {
      const unsigned char c = static_cast<unsigned char>(*input++);
      output[written++] = (c >= 0x20 && c <= 0x7e && c != '"' && c != '\\')
                              ? static_cast<char>(c)
                              : '?';
    }
  }
  output[written] = '\0';
}

}  // namespace

SessionServer::SessionServer() { mutex_ = xSemaphoreCreateMutex(); }

SessionServer::~SessionServer() {
  stop();
  if (mutex_ != nullptr) vSemaphoreDelete(mutex_);
  mbedtls_platform_zeroize(secret_, sizeof(secret_));
}

bool SessionServer::configure(const std::uint8_t secret[32],
                              const char* deviceId, const char* bootId,
                              bool ambientEnabled) {
  if (mutex_ == nullptr || secret == nullptr || deviceId == nullptr ||
      bootId == nullptr ||
      std::strlen(deviceId) >= sizeof(deviceId_) || !validHexId(bootId))
    return false;
  std::memcpy(secret_, secret, sizeof(secret_));
  std::strncpy(deviceId_, deviceId, sizeof(deviceId_) - 1);
  std::strncpy(bootId_, bootId, sizeof(bootId_) - 1);
  ambientEnabled_ = ambientEnabled;
  configured_ = true;
  return true;
}

esp_err_t SessionServer::start() {
  if (!configured_) return ESP_ERR_INVALID_STATE;
  if (server_ != nullptr) return ESP_OK;

  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = kWebSocketPort;
  config.ctrl_port = kWebSocketPort + 1;
  config.stack_size = 12288;
  config.max_open_sockets = 3;
  config.max_uri_handlers = 1;
  config.max_resp_headers = 4;
  config.backlog_conn = 2;
  config.lru_purge_enable = true;
  config.recv_wait_timeout = 5;
  config.send_wait_timeout = 5;
  config.global_user_ctx = this;
  config.global_user_ctx_free_fn = nullptr;
  config.close_fn = &SessionServer::socketClosed;
  const esp_err_t result = httpd_start(&server_, &config);
  if (result != ESP_OK) return result;

  httpd_uri_t websocket{};
  websocket.uri = kWebSocketPath;
  websocket.method = HTTP_GET;
  websocket.handler = &SessionServer::websocketHandler;
  websocket.user_ctx = this;
  websocket.is_websocket = true;
  websocket.handle_ws_control_frames = false;
  websocket.supported_subprotocol = kWebSocketProtocol;
  const esp_err_t registered = httpd_register_uri_handler(server_, &websocket);
  if (registered != ESP_OK) {
    httpd_stop(server_);
    server_ = nullptr;
    return registered;
  }
  ESP_LOGI(kTag, "authenticated WebSocket endpoint started on port %u",
           kWebSocketPort);
  return ESP_OK;
}

void SessionServer::stop() {
  if (server_ == nullptr) return;
  httpd_stop(server_);
  server_ = nullptr;
  closeSession(false);
  for (Challenge& challenge : challenges_) clearChallenge(challenge);
}

void SessionServer::tick(std::uint64_t currentMs) {
  if (mutex_ != nullptr && xSemaphoreTake(mutex_, pdMS_TO_TICKS(20)) == pdTRUE) {
    renderer_.active(currentMs);
    xSemaphoreGive(mutex_);
  }
}

Cells SessionServer::render(std::uint64_t currentMs) {
  Cells output{};
  if (mutex_ != nullptr && xSemaphoreTake(mutex_, pdMS_TO_TICKS(20)) == pdTRUE) {
    output = renderer_.renderScaled(currentMs);
    xSemaphoreGive(mutex_);
  }
  return output;
}

void SessionServer::emitButton(const char* gesture, std::uint32_t durationMs) {
  if (gesture == nullptr ||
      (std::strcmp(gesture, "tap") != 0 && std::strcmp(gesture, "press") != 0 &&
       std::strcmp(gesture, "long_press") != 0))
    return;
  char eventId[33]{};
  randomHexId(eventId);
  char body[160]{};
  std::snprintf(body, sizeof(body),
                "{\"duration_ms\":%lu,\"event_id\":\"%s\",\"gesture\":\"%s\"}",
                static_cast<unsigned long>(durationMs), eventId, gesture);
  emitEvent("BUTTON_EVENT", body);
}

void SessionServer::emitAmbient(std::uint16_t level) {
  if (!ambientEnabled_) return;
  char eventId[33]{};
  randomHexId(eventId);
  char body[160]{};
  std::snprintf(body, sizeof(body),
                "{\"event_id\":\"%s\",\"level_u16\":%u,\"sensor\":\"ambient\"}",
                eventId, level);
  emitEvent("SENSOR_EVENT", body);
}

esp_err_t SessionServer::websocketHandler(httpd_req_t* request) {
  auto* self = static_cast<SessionServer*>(request->user_ctx);
  return self == nullptr ? ESP_FAIL : self->handleWebsocket(request);
}

void SessionServer::socketClosed(httpd_handle_t server, int socket) {
  auto* self = static_cast<SessionServer*>(httpd_get_global_user_ctx(server));
  if (self != nullptr) self->handleClosedSocket(socket);
  ::close(socket);
}

esp_err_t SessionServer::handleWebsocket(httpd_req_t* request) {
  if (request->method == HTTP_GET) return ESP_OK;

  httpd_ws_frame_t frame{};
  esp_err_t result = httpd_ws_recv_frame(request, &frame, 0);
  if (result != ESP_OK) return result;
  largestFrameSeen_ = std::max(largestFrameSeen_, frame.len);
  const int socket = httpd_req_to_sockfd(request);
  if (frame.len > kMaxWebSocketBytes) {
    closeSocket(socket, 1009);
    return ESP_OK;
  }
  if (!frame.final || frame.fragmented || frame.type != HTTPD_WS_TYPE_TEXT) {
    closeSocket(socket, frame.type == HTTPD_WS_TYPE_BINARY ? 1003 : 1008);
    return ESP_OK;
  }

  char* payload = static_cast<char*>(
      heap_caps_malloc(frame.len + 1, MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL));
  if (payload == nullptr) {
    closeSocket(socket, 1011);
    return ESP_ERR_NO_MEM;
  }
  frame.payload = reinterpret_cast<std::uint8_t*>(payload);
  result = httpd_ws_recv_frame(request, &frame, frame.len);
  if (result == ESP_OK) {
    payload[frame.len] = '\0';
    handleText(request, payload, frame.len);
  }
  heap_caps_free(payload);
  return result;
}

void SessionServer::handleClosedSocket(int socket) {
  for (Challenge& challenge : challenges_) {
    if (challenge.present && challenge.socket == socket) clearChallenge(challenge);
  }
  if (session_.open && session_.socket == socket) closeSession(false);
}

void SessionServer::handleText(httpd_req_t* request, const char* text,
                               std::size_t length) {
  if (!strictJsonObject(text, length)) {
    closeSocket(httpd_req_to_sockfd(request), 1008);
    return;
  }
  cJSON* root = cJSON_ParseWithLength(text, length);
  if (root == nullptr || !cJSON_IsObject(root)) {
    cJSON_Delete(root);
    closeSocket(httpd_req_to_sockfd(request), 1008);
    return;
  }
  const char* type = jsonString(root, "type");
  const int socket = httpd_req_to_sockfd(request);
  if (type != nullptr && std::strcmp(type, "HELLO") == 0 &&
      (!session_.open || session_.socket != socket)) {
    handleHello(request, root);
  } else if (type != nullptr && std::strcmp(type, "AUTH") == 0 &&
             (!session_.open || session_.socket != socket)) {
    handleAuth(request, root);
  } else if (session_.open && session_.socket == socket) {
    handleEnvelope(request, root);
  } else {
    closeSocket(socket, 1008);
  }
  cJSON_Delete(root);
}

void SessionServer::handleHello(httpd_req_t* request, const cJSON* root) {
  static const char* fields[] = {"v",          "type",       "request_id",
                                 "client_name", "client_version", "client_nonce"};
  std::uint32_t version = 0;
  const char* requestId = jsonString(root, "request_id");
  const char* clientName = jsonString(root, "client_name");
  const char* clientVersion = jsonString(root, "client_version");
  const char* nonceText = jsonString(root, "client_nonce");
  const int socket = httpd_req_to_sockfd(request);
  if (!exactFields(root, fields, 6) ||
      !jsonUint(cJSON_GetObjectItemCaseSensitive(root, "v"), 1, 1, version) ||
      !validHexId(requestId) || clientName == nullptr ||
      std::strlen(clientName) < 1 || std::strlen(clientName) > 64 ||
      !semver(clientVersion) || nonceText == nullptr || !authAllowed(nowMs())) {
    authFailed(request);
    return;
  }
  Challenge* challenge = challengeFor(socket, true);
  if (challenge == nullptr) {
    closeSocket(socket, 1013);
    return;
  }
  std::size_t nonceSize = 0;
  if (!base64UrlDecode(nonceText, challenge->clientNonce,
                       sizeof(challenge->clientNonce), nonceSize) ||
      nonceSize != sizeof(challenge->clientNonce)) {
    authFailed(request);
    return;
  }
  challenge->present = true;
  challenge->socket = socket;
  std::strncpy(challenge->requestId, requestId,
               sizeof(challenge->requestId) - 1);
  randomHexId(challenge->sid);
  esp_fill_random(challenge->deviceNonce, sizeof(challenge->deviceNonce));
  challenge->expiresMs = nowMs() + kChallengeLifetimeMs;

  std::uint8_t proof[32]{};
  char proofText[44]{};
  char nonceEncoded[23]{};
  if (!authenticationProof(secret_, "device", challenge->requestId,
                           challenge->sid, challenge->clientNonce,
                           challenge->deviceNonce, proof) ||
      !base64UrlEncode(proof, sizeof(proof), proofText, sizeof(proofText)) ||
      !base64UrlEncode(challenge->deviceNonce, sizeof(challenge->deviceNonce),
                       nonceEncoded, sizeof(nonceEncoded))) {
    mbedtls_platform_zeroize(proof, sizeof(proof));
    authFailed(request);
    return;
  }
  char response[384]{};
  std::snprintf(
      response, sizeof(response),
      "{\"v\":1,\"type\":\"CHALLENGE\",\"request_id\":\"%s\",\"sid\":\"%s\","
      "\"device_id\":\"%s\",\"device_nonce\":\"%s\",\"auth\":\"hmac-sha256-v1\","
      "\"device_proof\":\"%s\"}",
      challenge->requestId, challenge->sid, deviceId_, nonceEncoded, proofText);
  sendRaw(request, response);
  mbedtls_platform_zeroize(proof, sizeof(proof));
}

void SessionServer::handleAuth(httpd_req_t* request, const cJSON* root) {
  const int socket = httpd_req_to_sockfd(request);
  Challenge* stored = challengeFor(socket, false);
  if (stored == nullptr) {
    authFailed(request);
    return;
  }
  Challenge challenge = *stored;
  clearChallenge(*stored);  // AUTH always consumes the single-use challenge.

  static const char* fields[] = {"v", "type", "request_id", "sid",
                                 "client_proof"};
  std::uint32_t version = 0;
  const char* requestId = jsonString(root, "request_id");
  const char* sid = jsonString(root, "sid");
  const char* proofText = jsonString(root, "client_proof");
  std::uint8_t supplied[32]{};
  std::uint8_t expected[32]{};
  std::size_t proofSize = 0;
  const bool valid =
      exactFields(root, fields, 5) &&
      jsonUint(cJSON_GetObjectItemCaseSensitive(root, "v"), 1, 1, version) &&
      nowMs() < challenge.expiresMs && requestId != nullptr && sid != nullptr &&
      std::strcmp(requestId, challenge.requestId) == 0 &&
      std::strcmp(sid, challenge.sid) == 0 && proofText != nullptr &&
      base64UrlDecode(proofText, supplied, sizeof(supplied), proofSize) &&
      proofSize == sizeof(supplied) &&
      authenticationProof(secret_, "client", challenge.requestId, challenge.sid,
                           challenge.clientNonce, challenge.deviceNonce,
                           expected) &&
      constantTimeEqual(supplied, expected, sizeof(expected));
  mbedtls_platform_zeroize(supplied, sizeof(supplied));
  mbedtls_platform_zeroize(expected, sizeof(expected));
  if (!valid) {
    mbedtls_platform_zeroize(&challenge, sizeof(challenge));
    authFailed(request);
    return;
  }

  SessionKeys keys{};
  std::uint8_t serverProof[32]{};
  char serverProofText[44]{};
  if (!deriveSessionKeys(secret_, challenge.requestId, challenge.sid,
                         challenge.clientNonce, challenge.deviceNonce, keys) ||
      !authenticationProof(secret_, "server", challenge.requestId,
                           challenge.sid, challenge.clientNonce,
                           challenge.deviceNonce, serverProof) ||
      !base64UrlEncode(serverProof, sizeof(serverProof), serverProofText,
                       sizeof(serverProofText))) {
    mbedtls_platform_zeroize(&keys, sizeof(keys));
    mbedtls_platform_zeroize(serverProof, sizeof(serverProof));
    mbedtls_platform_zeroize(&challenge, sizeof(challenge));
    authFailed(request);
    return;
  }

  if (session_.open && session_.socket != socket) closeSocket(session_.socket, 1008);
  closeSession(false);
  session_.open = true;
  session_.socket = socket;
  std::strncpy(session_.sid, challenge.sid, sizeof(session_.sid) - 1);
  session_.keys = keys;
  session_.expectedClientSequence = 1;
  session_.nextDeviceSequence = 1;

  char response[256]{};
  std::snprintf(response, sizeof(response),
                "{\"v\":1,\"type\":\"AUTHENTICATED\",\"request_id\":\"%s\","
                "\"sid\":\"%s\",\"server_proof\":\"%s\"}",
                challenge.requestId, challenge.sid, serverProofText);
  if (!sendRaw(request, response)) {
    ESP_LOGE(kTag, "AUTHENTICATED response send failed; closing session");
    closeSocket(socket, 1011);
  } else if (!sendCapabilities()) {
    // sendSigned() logs the failure and closes the broken session.
  }
  mbedtls_platform_zeroize(&keys, sizeof(keys));
  mbedtls_platform_zeroize(serverProof, sizeof(serverProof));
  mbedtls_platform_zeroize(&challenge, sizeof(challenge));
}

void SessionServer::handleEnvelope(httpd_req_t* request, const cJSON* root) {
  static const char* fields[] = {"v", "type", "sid", "seq", "body", "mac"};
  std::uint32_t version = 0;
  std::uint32_t sequence = 0;
  const char* type = jsonString(root, "type");
  const char* sid = jsonString(root, "sid");
  const char* encodedBody = jsonString(root, "body");
  const char* encodedMac = jsonString(root, "mac");
  if (!exactFields(root, fields, 6) ||
      !jsonUint(cJSON_GetObjectItemCaseSensitive(root, "v"), 1, 1, version) ||
      !validMessageType(type) || !validHexId(sid) || encodedBody == nullptr ||
      encodedMac == nullptr) {
    closeSocket(session_.socket, 1008);
    return;
  }
  if (std::strcmp(sid, session_.sid) != 0) {
    closeSocket(httpd_req_to_sockfd(request), 1008);
    return;
  }
  if (!jsonUint(cJSON_GetObjectItemCaseSensitive(root, "seq"), 1, UINT32_MAX,
                sequence)) {
    closeSocket(session_.socket, 1008);
    return;
  }

  std::uint8_t suppliedMac[32]{};
  std::uint8_t expectedMac[32]{};
  std::size_t macSize = 0;
  if (!base64UrlDecode(encodedMac, suppliedMac, sizeof(suppliedMac), macSize) ||
      macSize != sizeof(suppliedMac) ||
      !messageMac(session_.keys.clientToDevice, type, sid, sequence, encodedBody,
                  expectedMac) ||
      !constantTimeEqual(suppliedMac, expectedMac, sizeof(expectedMac))) {
    mbedtls_platform_zeroize(suppliedMac, sizeof(suppliedMac));
    mbedtls_platform_zeroize(expectedMac, sizeof(expectedMac));
    closeSocket(session_.socket, 1008);
    return;
  }
  mbedtls_platform_zeroize(suppliedMac, sizeof(suppliedMac));
  mbedtls_platform_zeroize(expectedMac, sizeof(expectedMac));

  if (sequence != session_.expectedClientSequence) {
    char detail[96]{};
    std::snprintf(detail, sizeof(detail), "expected seq %lu, received %lu",
                  static_cast<unsigned long>(session_.expectedClientSequence),
                  static_cast<unsigned long>(sequence));
    if (!sendError(sequence, "SEQUENCE_ERROR", detail)) return;
    closeSocket(session_.socket, 1008);
    return;
  }

  const std::size_t encodedBodySize = std::strlen(encodedBody);
  if (encodedBodySize > ((kMaxBodyBytes * 8 + 5) / 6)) {
    closeSocket(session_.socket, 1009);
    return;
  }
  std::uint8_t decoded[kMaxBodyBytes + 1]{};
  std::size_t decodedSize = 0;
  if (!base64UrlDecode(encodedBody, decoded, kMaxBodyBytes, decodedSize)) {
    closeSocket(session_.socket, 1008);
    return;
  }
  largestBodySeen_ = std::max(largestBodySeen_, decodedSize);
  decoded[decodedSize] = 0;
  if (!strictJsonObject(reinterpret_cast<const char*>(decoded), decodedSize)) {
    closeSocket(session_.socket, 1008);
    return;
  }
  cJSON* body = cJSON_ParseWithLength(reinterpret_cast<const char*>(decoded),
                                      decodedSize);
  if (body == nullptr || !cJSON_IsObject(body)) {
    cJSON_Delete(body);
    closeSocket(session_.socket, 1008);
    return;
  }

  ++session_.expectedClientSequence;
  ValidationResult validation{};
  bool responseSent = true;
  if (std::strcmp(type, "LOAD_SCENE") == 0) {
    Scene candidate{};
    validation = parseSceneBody(body, candidate);
    if (validation) {
      if (!lockRendererOrClose(type)) {
        cJSON_Delete(body);
        return;
      }
      validation = renderer_.load(candidate, nowMs());
      xSemaphoreGive(mutex_);
    }
    if (validation) responseSent = sendAck(sequence, candidate.id.data());
  } else if (std::strcmp(type, "KEEPALIVE") == 0 ||
             std::strcmp(type, "CLEAR") == 0) {
    char sceneId[23]{};
    validation = parseSceneIdBody(body, sceneId);
    bool accepted = false;
    if (validation) {
      if (!lockRendererOrClose(type)) {
        cJSON_Delete(body);
        return;
      }
      accepted = std::strcmp(type, "KEEPALIVE") == 0
                     ? renderer_.keepalive(sceneId, nowMs())
                     : renderer_.clear(sceneId, nowMs());
      xSemaphoreGive(mutex_);
    }
    if (validation && !accepted)
      validation = {ValidationCode::SceneMismatch,
                    "scene_id does not match the active scene"};
    if (validation) responseSent = sendAck(sequence, sceneId);
  } else if (std::strcmp(type, "STATUS") == 0) {
    if (body->child != nullptr)
      validation = {ValidationCode::InvalidFields,
                    "STATUS request body must be empty"};
    else
      responseSent = sendStatus(sequence);
  } else {
    validation = {ValidationCode::UnsupportedType,
                  "unsupported controller message type"};
  }
  if (!validation) {
    responseSent =
        sendError(sequence, validationCodeName(validation.code), validation.detail);
  }
  cJSON_Delete(body);
  if (!responseSent) return;
  if (sequence == UINT32_MAX) closeSocket(session_.socket, 1008);
}

SessionServer::Challenge* SessionServer::challengeFor(int socket, bool create) {
  const std::uint64_t currentMs = nowMs();
  for (Challenge& challenge : challenges_) {
    if (challenge.present && currentMs >= challenge.expiresMs)
      clearChallenge(challenge);
  }
  for (Challenge& challenge : challenges_) {
    if (challenge.present && challenge.socket == socket) return &challenge;
  }
  if (!create) return nullptr;
  for (Challenge& challenge : challenges_) {
    if (!challenge.present) return &challenge;
  }
  return nullptr;
}

void SessionServer::clearChallenge(Challenge& challenge) {
  mbedtls_platform_zeroize(&challenge, sizeof(challenge));
  challenge.socket = -1;
}

bool SessionServer::authAllowed(std::uint64_t currentMs) {
  if (authWindowStartMs_ == 0 || currentMs - authWindowStartMs_ >= kAuthWindowMs) {
    authWindowStartMs_ = currentMs;
    authFailures_ = 0;
  }
  return authFailures_ < kMaxAuthFailures;
}

void SessionServer::authFailed(httpd_req_t* request) {
  const std::uint64_t currentMs = nowMs();
  if (authWindowStartMs_ == 0 || currentMs - authWindowStartMs_ >= kAuthWindowMs) {
    authWindowStartMs_ = currentMs;
    authFailures_ = 0;
  }
  if (authFailures_ < UINT8_MAX) ++authFailures_;
  const int socket = httpd_req_to_sockfd(request);
  Challenge* challenge = challengeFor(socket, false);
  if (challenge != nullptr) clearChallenge(*challenge);
  closeSocket(socket, 1008);
}

void SessionServer::closeSession(bool closeSocketFlag) {
  const int socket = session_.socket;
  mbedtls_platform_zeroize(&session_, sizeof(session_));
  session_.socket = -1;
  session_.expectedClientSequence = 1;
  session_.nextDeviceSequence = 1;
  if (closeSocketFlag && socket >= 0) closeSocket(socket, 1008);
}

void SessionServer::closeSocket(int socket, std::uint16_t code) {
  if (server_ == nullptr || socket < 0) return;
  std::uint8_t payload[2] = {static_cast<std::uint8_t>(code >> 8),
                             static_cast<std::uint8_t>(code & 0xff)};
  httpd_ws_frame_t frame{};
  frame.final = true;
  frame.type = HTTPD_WS_TYPE_CLOSE;
  frame.payload = payload;
  frame.len = sizeof(payload);
  httpd_ws_send_frame_async(server_, socket, &frame);
  httpd_sess_trigger_close(server_, socket);
}

bool SessionServer::lockRendererOrClose(const char* operation) {
  if (mutex_ != nullptr &&
      xSemaphoreTake(mutex_, pdMS_TO_TICKS(50)) == pdTRUE) {
    return true;
  }
  ESP_LOGE(kTag, "renderer lock timed out during %s; closing session",
           operation == nullptr ? "command" : operation);
  if (session_.open && session_.socket >= 0) closeSocket(session_.socket, 1011);
  return false;
}

bool SessionServer::sendRaw(httpd_req_t* request, const char* text) {
  if (request == nullptr || text == nullptr) return false;
  httpd_ws_frame_t frame{};
  frame.final = true;
  frame.type = HTTPD_WS_TYPE_TEXT;
  frame.payload = reinterpret_cast<std::uint8_t*>(const_cast<char*>(text));
  frame.len = std::strlen(text);
  return httpd_ws_send_frame(request, &frame) == ESP_OK;
}

bool SessionServer::sendRawSocket(int socket, const char* text) {
  if (server_ == nullptr || socket < 0 || text == nullptr) return false;
  httpd_ws_frame_t frame{};
  frame.final = true;
  frame.type = HTTPD_WS_TYPE_TEXT;
  frame.payload = reinterpret_cast<std::uint8_t*>(const_cast<char*>(text));
  frame.len = std::strlen(text);
  return httpd_ws_send_frame_async(server_, socket, &frame) == ESP_OK;
}

bool SessionServer::sendSigned(const char* type, const char* canonicalBody) {
  if (!session_.open || type == nullptr || canonicalBody == nullptr) return false;

  char* encodedBody = nullptr;
  char* envelope = nullptr;
  const auto release = [&]() {
    heap_caps_free(envelope);
    heap_caps_free(encodedBody);
    envelope = nullptr;
    encodedBody = nullptr;
  };
  const auto fail = [&](const char* stage) {
    release();
    ESP_LOGE(kTag, "signed %s response failed during %s; closing session", type,
             stage);
    if (session_.open && session_.socket >= 0) closeSocket(session_.socket, 1011);
    return false;
  };

  const std::size_t bodySize = std::strlen(canonicalBody);
  if (bodySize > kMaxBodyBytes) return fail("body bounds check");
  const std::size_t encodedSize = (bodySize * 8 + 5) / 6;
  const std::size_t encodedCapacity = encodedSize + 1;
  encodedBody = static_cast<char*>(heap_caps_malloc(
      encodedCapacity, MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL));
  if (encodedBody == nullptr) return fail("body buffer allocation");
  if (!base64UrlEncode(reinterpret_cast<const std::uint8_t*>(canonicalBody),
                       bodySize, encodedBody, encodedCapacity))
    return fail("body encoding");

  std::uint8_t mac[32]{};
  char encodedMac[44]{};
  const std::uint32_t sequence = session_.nextDeviceSequence;
  if (!messageMac(session_.keys.deviceToClient, type, session_.sid, sequence,
                  encodedBody, mac) ||
      !base64UrlEncode(mac, sizeof(mac), encodedMac, sizeof(encodedMac))) {
    mbedtls_platform_zeroize(mac, sizeof(mac));
    return fail("message authentication");
  }

  constexpr char kEnvelopeFormat[] =
      "{\"v\":1,\"type\":\"%s\",\"sid\":\"%s\",\"seq\":%lu,\"body\":\"%s\",\"mac\":\"%s\"}";
  const int required = std::snprintf(
      nullptr, 0, kEnvelopeFormat, type, session_.sid,
      static_cast<unsigned long>(sequence), encodedBody, encodedMac);
  if (required < 0 || static_cast<std::size_t>(required) > kMaxWebSocketBytes) {
    mbedtls_platform_zeroize(mac, sizeof(mac));
    return fail("envelope sizing");
  }
  const std::size_t envelopeCapacity = static_cast<std::size_t>(required) + 1;
  envelope = static_cast<char*>(heap_caps_malloc(
      envelopeCapacity, MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL));
  if (envelope == nullptr) {
    mbedtls_platform_zeroize(mac, sizeof(mac));
    return fail("envelope buffer allocation");
  }
  const int size = std::snprintf(
      envelope, envelopeCapacity, kEnvelopeFormat, type, session_.sid,
      static_cast<unsigned long>(sequence), encodedBody, encodedMac);
  mbedtls_platform_zeroize(mac, sizeof(mac));
  if (size != required) return fail("envelope formatting");

  const bool sent = sendRawSocket(session_.socket, envelope);
  release();
  if (!sent) return fail("socket send");
  if (session_.nextDeviceSequence == UINT32_MAX) {
    closeSocket(session_.socket, 1008);
  } else {
    ++session_.nextDeviceSequence;
  }
  return true;
}

bool SessionServer::sendCapabilities() {
  char body[1024]{};
  std::snprintf(
      body, sizeof(body),
      "{\"brightness\":{\"max\":96,\"min\":0},\"cell_count\":6,\"color_format\":\"rgb888\","
      "\"device_id\":\"%s\",\"events\":{\"ambient\":%s,\"button\":true},\"fallback\":\"off\","
      "\"firmware_version\":\"%s\",\"lease\":{\"default_ms\":3000,\"keepalive_interval_ms\":1000,"
      "\"max_ms\":5000,\"min_ms\":3000},\"max_body_bytes\":3072,\"max_keyframes\":16,"
      "\"max_websocket_bytes\":6144,\"timing\":{\"max_cycle_ms\":120000,\"max_hold_ms\":60000,"
      "\"max_transition_ms\":30000,\"min_loop_cycle_ms\":100,\"render_tick_ms\":20},"
      "\"transitions\":[\"step\",\"linear\"]}",
      deviceId_, ambientEnabled_ ? "true" : "false", kFirmwareVersion);
  return sendSigned("CAPABILITIES", body);
}

bool SessionServer::sendAck(std::uint32_t replyTo, const char* sceneId) {
  char body[128]{};
  std::snprintf(body, sizeof(body),
                "{\"reply_to\":%lu,\"result\":\"accepted\",\"scene_id\":\"%s\"}",
                static_cast<unsigned long>(replyTo), sceneId);
  return sendSigned("ACK", body);
}

bool SessionServer::sendError(std::uint32_t replyTo, const char* code,
                              const char* detail) {
  char boundedDetail[161]{};
  safeDetail(detail, boundedDetail);
  char body[320]{};
  std::snprintf(body, sizeof(body),
                "{\"code\":\"%s\",\"detail\":\"%s\",\"reply_to\":%lu}",
                code, boundedDetail, static_cast<unsigned long>(replyTo));
  return sendSigned("ERROR", body);
}

bool SessionServer::sendStatus(std::uint32_t replyTo) {
  bool active = false;
  char sceneId[23]{};
  int frameIndex = -1;
  std::uint32_t leaseRemaining = 0;
  const std::uint64_t currentMs = nowMs();
  if (!lockRendererOrClose("STATUS")) return false;
  active = renderer_.active(currentMs);
  if (active) {
    std::strncpy(sceneId, renderer_.activeSceneId(currentMs), sizeof(sceneId) - 1);
    frameIndex = renderer_.frameIndex(currentMs);
    leaseRemaining = renderer_.leaseRemainingMs(currentMs);
  }
  xSemaphoreGive(mutex_);
  char body[384]{};
  if (active) {
    std::snprintf(
        body, sizeof(body),
        "{\"active_scene_id\":\"%s\",\"boot_id\":\"%s\",\"frame_index\":%d,"
        "\"lease_remaining_ms\":%lu,\"reply_to\":%lu,\"scene_state\":\"active\",\"uptime_ms\":%llu}",
        sceneId, bootId_, frameIndex, static_cast<unsigned long>(leaseRemaining),
        static_cast<unsigned long>(replyTo),
        static_cast<unsigned long long>(currentMs));
  } else {
    std::snprintf(
        body, sizeof(body),
        "{\"active_scene_id\":null,\"boot_id\":\"%s\",\"frame_index\":null,"
        "\"lease_remaining_ms\":0,\"reply_to\":%lu,\"scene_state\":\"off\",\"uptime_ms\":%llu}",
        bootId_, static_cast<unsigned long>(replyTo),
        static_cast<unsigned long long>(currentMs));
  }
  return sendSigned("STATUS", body);
}

void SessionServer::emitEvent(const char* type, const char* canonicalBody) {
  if (server_ == nullptr || type == nullptr || canonicalBody == nullptr ||
      std::strlen(type) >= 16 || std::strlen(canonicalBody) >= 192)
    return;
  auto* work = static_cast<EventWork*>(std::calloc(1, sizeof(EventWork)));
  if (work == nullptr) return;
  work->server = this;
  std::strncpy(work->type, type, sizeof(work->type) - 1);
  std::strncpy(work->body, canonicalBody, sizeof(work->body) - 1);
  const esp_err_t queued = httpd_queue_work(
      server_,
      [](void* argument) {
        auto* queuedWork = static_cast<EventWork*>(argument);
        if (queuedWork != nullptr && queuedWork->server != nullptr &&
            queuedWork->server->session_.open) {
          queuedWork->server->sendSigned(queuedWork->type, queuedWork->body);
        }
        std::free(queuedWork);
      },
      work);
  if (queued != ESP_OK) std::free(work);
}

}  // namespace peri6
