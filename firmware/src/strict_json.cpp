#include "peri6/strict_json.h"

#include <cctype>
#include <cstdint>
#include <cstring>

namespace peri6 {
namespace {

bool validUtf8(const char* input, std::size_t length) {
  std::size_t index = 0;
  while (index < length) {
    const std::uint8_t first = static_cast<std::uint8_t>(input[index++]);
    if (first <= 0x7f) continue;
    std::uint32_t codepoint = 0;
    std::uint8_t continuation = 0;
    std::uint32_t minimum = 0;
    if (first >= 0xc2 && first <= 0xdf) {
      codepoint = first & 0x1f;
      continuation = 1;
      minimum = 0x80;
    } else if (first >= 0xe0 && first <= 0xef) {
      codepoint = first & 0x0f;
      continuation = 2;
      minimum = 0x800;
    } else if (first >= 0xf0 && first <= 0xf4) {
      codepoint = first & 0x07;
      continuation = 3;
      minimum = 0x10000;
    } else {
      return false;
    }
    if (index + continuation > length) return false;
    for (std::uint8_t i = 0; i < continuation; ++i) {
      const std::uint8_t next = static_cast<std::uint8_t>(input[index++]);
      if ((next & 0xc0) != 0x80) return false;
      codepoint = (codepoint << 6) | (next & 0x3f);
    }
    if (codepoint < minimum || codepoint > 0x10ffff ||
        (codepoint >= 0xd800 && codepoint <= 0xdfff))
      return false;
  }
  return true;
}

class Parser {
 public:
  Parser(const char* input, std::size_t length)
      : input_(input), length_(length) {}

  bool rootObject() {
    space();
    if (!object(0)) return false;
    space();
    return index_ == length_;
  }

 private:
  static constexpr std::uint8_t kMaxDepth = 12;
  static constexpr std::uint8_t kMaxKeys = 24;
  static constexpr std::uint8_t kMaxKeyBytes = 39;

  const char* input_;
  std::size_t length_;
  std::size_t index_ = 0;

  void space() {
    while (index_ < length_ &&
           (input_[index_] == ' ' || input_[index_] == '\t' ||
            input_[index_] == '\r' || input_[index_] == '\n')) {
      ++index_;
    }
  }

  bool take(char expected) {
    if (index_ >= length_ || input_[index_] != expected) return false;
    ++index_;
    return true;
  }

  static int hex(char value) {
    if (value >= '0' && value <= '9') return value - '0';
    if (value >= 'a' && value <= 'f') return value - 'a' + 10;
    if (value >= 'A' && value <= 'F') return value - 'A' + 10;
    return -1;
  }

  bool string(char* decoded, std::size_t capacity) {
    if (!take('"')) return false;
    std::size_t written = 0;
    while (index_ < length_) {
      std::uint8_t output = static_cast<std::uint8_t>(input_[index_++]);
      if (output == '"') {
        if (decoded != nullptr) decoded[written] = '\0';
        return true;
      }
      if (output < 0x20) return false;
      if (output == '\\') {
        if (index_ >= length_) return false;
        switch (input_[index_++]) {
          case '"': output = '"'; break;
          case '\\': output = '\\'; break;
          case '/': output = '/'; break;
          case 'b': output = '\b'; break;
          case 'f': output = '\f'; break;
          case 'n': output = '\n'; break;
          case 'r': output = '\r'; break;
          case 't': output = '\t'; break;
          case 'u': {
            if (index_ + 4 > length_) return false;
            std::uint16_t codepoint = 0;
            for (std::uint8_t i = 0; i < 4; ++i) {
              const int nibble = hex(input_[index_++]);
              if (nibble < 0) return false;
              codepoint = static_cast<std::uint16_t>((codepoint << 4) | nibble);
            }
            output = codepoint <= 0x7f ? static_cast<std::uint8_t>(codepoint)
                                       : 0xff;
            break;
          }
          default: return false;
        }
      }
      if (decoded != nullptr) {
        if (written + 1 >= capacity) return false;
        decoded[written++] = static_cast<char>(output);
      }
    }
    return false;
  }

  bool number() {
    if (index_ < length_ && input_[index_] == '-') ++index_;
    if (index_ >= length_) return false;
    if (input_[index_] == '0') {
      ++index_;
      if (index_ < length_ &&
          std::isdigit(static_cast<unsigned char>(input_[index_])))
        return false;
    } else if (input_[index_] >= '1' && input_[index_] <= '9') {
      while (index_ < length_ &&
             std::isdigit(static_cast<unsigned char>(input_[index_])))
        ++index_;
    } else {
      return false;
    }
    if (index_ < length_ && input_[index_] == '.') {
      ++index_;
      if (index_ >= length_ ||
          !std::isdigit(static_cast<unsigned char>(input_[index_])))
        return false;
      while (index_ < length_ &&
             std::isdigit(static_cast<unsigned char>(input_[index_])))
        ++index_;
    }
    if (index_ < length_ && (input_[index_] == 'e' || input_[index_] == 'E')) {
      ++index_;
      if (index_ < length_ && (input_[index_] == '+' || input_[index_] == '-'))
        ++index_;
      if (index_ >= length_ ||
          !std::isdigit(static_cast<unsigned char>(input_[index_])))
        return false;
      while (index_ < length_ &&
             std::isdigit(static_cast<unsigned char>(input_[index_])))
        ++index_;
    }
    return true;
  }

  bool literal(const char* expected) {
    const std::size_t size = std::strlen(expected);
    if (index_ + size > length_ ||
        std::memcmp(input_ + index_, expected, size) != 0)
      return false;
    index_ += size;
    return true;
  }

  bool array(std::uint8_t depth) {
    if (depth >= kMaxDepth || !take('[')) return false;
    space();
    if (take(']')) return true;
    while (true) {
      if (!value(depth + 1)) return false;
      space();
      if (take(']')) return true;
      if (!take(',')) return false;
      space();
    }
  }

  bool object(std::uint8_t depth) {
    if (depth >= kMaxDepth || !take('{')) return false;
    char keys[kMaxKeys][kMaxKeyBytes + 1]{};
    std::uint8_t keyCount = 0;
    space();
    if (take('}')) return true;
    while (true) {
      if (keyCount >= kMaxKeys ||
          !string(keys[keyCount], sizeof(keys[keyCount])))
        return false;
      for (std::uint8_t i = 0; i < keyCount; ++i) {
        if (std::strcmp(keys[i], keys[keyCount]) == 0) return false;
      }
      ++keyCount;
      space();
      if (!take(':')) return false;
      space();
      if (!value(depth + 1)) return false;
      space();
      if (take('}')) return true;
      if (!take(',')) return false;
      space();
    }
  }

  bool value(std::uint8_t depth) {
    space();
    if (index_ >= length_) return false;
    switch (input_[index_]) {
      case '{': return object(depth);
      case '[': return array(depth);
      case '"': return string(nullptr, 0);
      case 't': return literal("true");
      case 'f': return literal("false");
      case 'n': return literal("null");
      default: return number();
    }
  }
};

}  // namespace

bool strictJsonObject(const char* json, std::size_t length) {
  return json != nullptr && length >= 2 && validUtf8(json, length) &&
         Parser(json, length).rootObject();
}

}  // namespace peri6
