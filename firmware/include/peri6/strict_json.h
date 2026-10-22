#pragma once

#include <cstddef>

namespace peri6 {

// Bounded syntax pass used before allocating a JSON DOM. Requires an object
// root and rejects duplicate members, excessive depth/key count, and malformed
// grammar. ASCII \u escapes in member names are normalized for duplicate checks.
bool strictJsonObject(const char* json, std::size_t length);

}  // namespace peri6

