#pragma once

#include <cstddef>
#include <cstdint>

#include "esp_http_server.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "peri6/protocol_codec.h"
#include "peri6/renderer_core.h"

namespace peri6 {

class SessionServer {
 public:
  SessionServer();
  ~SessionServer();

  bool configure(const std::uint8_t secret[32], const char* deviceId,
                 const char* bootId, bool ambientEnabled);
  esp_err_t start();
  void stop();
  void tick(std::uint64_t nowMs);

  Cells render(std::uint64_t nowMs);
  void emitButton(const char* gesture, std::uint32_t durationMs);
  void emitAmbient(std::uint16_t level);

  std::size_t largestFrameSeen() const { return largestFrameSeen_; }
  std::size_t largestBodySeen() const { return largestBodySeen_; }

 private:
  static constexpr std::uint8_t kChallengeSlots = 2;

  struct Challenge {
    bool present = false;
    int socket = -1;
    char requestId[33]{};
    char sid[33]{};
    std::uint8_t clientNonce[16]{};
    std::uint8_t deviceNonce[16]{};
    std::uint64_t expiresMs = 0;
  };

  struct Session {
    bool open = false;
    int socket = -1;
    char sid[33]{};
    SessionKeys keys{};
    std::uint32_t expectedClientSequence = 1;
    std::uint32_t nextDeviceSequence = 1;
  };

  httpd_handle_t server_ = nullptr;
  SemaphoreHandle_t mutex_ = nullptr;
  RendererCore renderer_{};
  std::uint8_t secret_[32]{};
  char deviceId_[36]{};
  char bootId_[33]{};
  bool configured_ = false;
  bool ambientEnabled_ = false;
  Challenge challenges_[kChallengeSlots]{};
  Session session_{};
  std::uint64_t authWindowStartMs_ = 0;
  std::uint8_t authFailures_ = 0;
  std::size_t largestFrameSeen_ = 0;
  std::size_t largestBodySeen_ = 0;

  static esp_err_t websocketHandler(httpd_req_t* request);
  static void socketClosed(httpd_handle_t server, int socket);
  esp_err_t handleWebsocket(httpd_req_t* request);
  void handleClosedSocket(int socket);
  void handleText(httpd_req_t* request, const char* text, std::size_t length);
  void handleHello(httpd_req_t* request, const cJSON* root);
  void handleAuth(httpd_req_t* request, const cJSON* root);
  void handleEnvelope(httpd_req_t* request, const cJSON* root);

  Challenge* challengeFor(int socket, bool create);
  void clearChallenge(Challenge& challenge);
  bool authAllowed(std::uint64_t nowMs);
  void authFailed(httpd_req_t* request);
  void closeSession(bool closeSocket);
  void closeSocket(int socket, std::uint16_t code);
  bool lockRendererOrClose(const char* operation);

  bool sendRaw(httpd_req_t* request, const char* text);
  bool sendRawSocket(int socket, const char* text);
  bool sendSigned(const char* type, const char* canonicalBody);
  bool sendCapabilities();
  bool sendAck(std::uint32_t replyTo, const char* sceneId);
  bool sendError(std::uint32_t replyTo, const char* code, const char* detail);
  bool sendStatus(std::uint32_t replyTo);
  void emitEvent(const char* type, const char* canonicalBody);
};

}  // namespace peri6
