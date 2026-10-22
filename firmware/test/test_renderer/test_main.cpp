#include <cstring>

#include <unity.h>

#include "peri6/renderer_core.h"
#include "peri6/strict_json.h"

using namespace peri6;

void setUp() {}
void tearDown() {}

namespace {

Scene scene(const char* id = "ABEiM0RVZneImaq7zN3u_w") {
  Scene value{};
  std::strncpy(value.id.data(), id, value.id.size() - 1);
  value.leaseMs = 3000;
  value.brightness = 96;
  value.playback = PlaybackMode::Loop;
  value.keyframeCount = 1;
  value.keyframes[0].transition = TransitionKind::Linear;
  value.keyframes[0].transitionMs = 100;
  value.keyframes[0].holdMs = 100;
  value.keyframes[0].cells.fill({255, 0, 0});
  return value;
}

void test_scene_validation_profile_limits() {
  Scene value = scene();
  TEST_ASSERT_TRUE(validateScene(value));
  TEST_ASSERT_EQUAL_UINT32(200, value.cycleMs);
  value.brightness = 97;
  TEST_ASSERT_EQUAL(ValidationCode::OutOfRange, validateScene(value).code);
}

void test_atomic_rejection_preserves_old_scene_and_deadline() {
  RendererCore renderer;
  TEST_ASSERT_TRUE(renderer.load(scene(), 0));
  Scene invalid = scene("zBEiM0RVZneImaq7zN3u_w");
  invalid.keyframeCount = 0;
  TEST_ASSERT_FALSE(renderer.load(invalid, 1000));
  TEST_ASSERT_EQUAL_STRING("ABEiM0RVZneImaq7zN3u_w",
                           renderer.activeSceneId(1000));
  TEST_ASSERT_EQUAL_UINT32(2000, renderer.leaseRemainingMs(1000));
}

void test_expiry_is_exact_and_black() {
  RendererCore renderer;
  TEST_ASSERT_TRUE(renderer.load(scene(), 0));
  TEST_ASSERT_TRUE(renderer.active(2999));
  TEST_ASSERT_FALSE(renderer.active(3000));
  for (const Rgb& cell : renderer.renderScaled(3000)) {
    TEST_ASSERT_EQUAL_UINT8(0, cell.r);
    TEST_ASSERT_EQUAL_UINT8(0, cell.g);
    TEST_ASSERT_EQUAL_UINT8(0, cell.b);
  }
}

void test_linear_interpolation_uses_floor_when_fading_down() {
  RendererCore renderer;
  Scene first = scene();
  first.keyframes[0].transition = TransitionKind::Step;
  first.keyframes[0].transitionMs = 0;
  first.keyframes[0].holdMs = 100;
  first.keyframes[0].cells.fill({255, 0, 0});
  TEST_ASSERT_TRUE(renderer.load(first, 0));
  Scene second = scene("zBEiM0RVZneImaq7zN3u_w");
  second.keyframes[0].cells.fill({0, 0, 0});
  TEST_ASSERT_TRUE(renderer.load(second, 1));
  TEST_ASSERT_EQUAL_UINT8(127, renderer.renderUnscaled(51)[0].r);
}

void test_keepalive_extends_without_restarting_animation() {
  RendererCore renderer;
  TEST_ASSERT_TRUE(renderer.load(scene(), 0));
  const Cells before = renderer.renderUnscaled(125);
  TEST_ASSERT_TRUE(renderer.keepalive("ABEiM0RVZneImaq7zN3u_w", 125));
  TEST_ASSERT_TRUE(before == renderer.renderUnscaled(125));
  TEST_ASSERT_EQUAL_UINT32(3000, renderer.leaseRemainingMs(125));
}

void test_once_hold_and_once_off_differ() {
  RendererCore renderer;
  Scene hold = scene();
  hold.playback = PlaybackMode::OnceHold;
  TEST_ASSERT_TRUE(renderer.load(hold, 0));
  TEST_ASSERT_EQUAL_UINT8(255, renderer.renderUnscaled(250)[0].r);

  Scene off = scene("zBEiM0RVZneImaq7zN3u_w");
  off.playback = PlaybackMode::OnceOff;
  TEST_ASSERT_TRUE(renderer.load(off, 300));
  TEST_ASSERT_EQUAL_UINT8(0, renderer.renderUnscaled(550)[0].r);
}

void test_strict_json_rejects_duplicate_and_escaped_duplicate_keys() {
  constexpr char valid[] = "{\"v\":1,\"type\":\"STATUS\"}";
  constexpr char duplicate[] = "{\"v\":1,\"v\":1}";
  constexpr char escaped[] = "{\"v\":1,\"\\u0076\":1}";
  TEST_ASSERT_TRUE(strictJsonObject(valid, sizeof(valid) - 1));
  TEST_ASSERT_FALSE(strictJsonObject(duplicate, sizeof(duplicate) - 1));
  TEST_ASSERT_FALSE(strictJsonObject(escaped, sizeof(escaped) - 1));
}

}  // namespace

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_scene_validation_profile_limits);
  RUN_TEST(test_atomic_rejection_preserves_old_scene_and_deadline);
  RUN_TEST(test_expiry_is_exact_and_black);
  RUN_TEST(test_linear_interpolation_uses_floor_when_fading_down);
  RUN_TEST(test_keepalive_extends_without_restarting_animation);
  RUN_TEST(test_once_hold_and_once_off_differ);
  RUN_TEST(test_strict_json_rejects_duplicate_and_escaped_duplicate_keys);
  return UNITY_END();
}
