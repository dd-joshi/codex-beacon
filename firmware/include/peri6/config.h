#pragma once

#include <cstddef>
#include <cstdint>

namespace peri6 {

constexpr char kFirmwareVersion[] = "0.1.0";
constexpr std::uint8_t kCellCount = 6;
constexpr std::uint8_t kMaxKeyframes = 16;
constexpr std::size_t kMaxBodyBytes = 3072;
constexpr std::size_t kMaxWebSocketBytes = 6144;
constexpr std::uint8_t kMaxBrightness = 96;

constexpr std::uint32_t kMaxTransitionMs = 30000;
constexpr std::uint32_t kMaxHoldMs = 60000;
constexpr std::uint32_t kMaxCycleMs = 120000;
constexpr std::uint32_t kMinLoopCycleMs = 100;
constexpr std::uint32_t kMinLeaseMs = 3000;
constexpr std::uint32_t kMaxLeaseMs = 5000;
constexpr std::uint32_t kDefaultLeaseMs = 3000;
constexpr std::uint32_t kKeepaliveIntervalMs = 1000;
constexpr std::uint32_t kRenderTickMs = 20;

constexpr std::uint8_t kLedPin = 3;
constexpr std::uint8_t kAmbientPin = 0;
constexpr std::uint8_t kButtonPin = 10;
constexpr std::uint16_t kWebSocketPort = 8765;
constexpr char kWebSocketPath[] = "/ws/v1";
constexpr char kWebSocketProtocol[] = "peri6.scene.v1";
constexpr std::uint32_t kButtonDebounceMs = 30;
constexpr std::uint32_t kButtonTapMaxMs = 400;
constexpr std::uint32_t kButtonLongPressMs = 1500;
constexpr std::uint32_t kChallengeLifetimeMs = 10000;

}  // namespace peri6
