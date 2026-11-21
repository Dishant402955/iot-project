#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

#include "LaCaptureSequence.h"

static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { \
  std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
  ++failures; } } while (0)

int main() {
  using devourer::demo::la_capture_output_path;
  using devourer::demo::run_la_capture_sequence;

  CHECK(la_capture_output_path("/tmp/capture.bin", 1, 0) ==
        "/tmp/capture.bin");
  CHECK(la_capture_output_path("/tmp/capture.bin", 12, 0) ==
        "/tmp/capture.0001.bin");
  CHECK(la_capture_output_path("/tmp/capture.bin", 12, 11) ==
        "/tmp/capture.0012.bin");
  CHECK(la_capture_output_path("capture", 2, 1) == "capture.0002");
  CHECK(la_capture_output_path("/tmp/a.b/capture", 2, 0) ==
        "/tmp/a.b/capture.0001");

  std::vector<uint32_t> calls;
  std::vector<uint32_t> sleeps;
  uint32_t done = run_la_capture_sequence(
      3, 120,
      [&](uint32_t i) { calls.push_back(i); return true; },
      [] { return false; },
      [&](uint32_t ms) { sleeps.push_back(ms); });
  CHECK(done == 3);
  CHECK((calls == std::vector<uint32_t>{0, 1, 2}));
  CHECK((sleeps == std::vector<uint32_t>{50, 50, 20, 50, 50, 20}));

  calls.clear();
  done = run_la_capture_sequence(
      5, 0,
      [&](uint32_t i) { calls.push_back(i); return i == 0; },
      [] { return false; }, [](uint32_t) {});
  CHECK(done == 1);
  CHECK((calls == std::vector<uint32_t>{0, 1}));

  calls.clear();
  done = run_la_capture_sequence(
      5, 100,
      [&](uint32_t i) { calls.push_back(i); return true; },
      [] { return true; }, [](uint32_t) {});
  CHECK(done == 0);
  CHECK(calls.empty());

  calls.clear();
  bool stop_after_wait = false;
  done = run_la_capture_sequence(
      5, 100,
      [&](uint32_t i) { calls.push_back(i); return true; },
      [&] { return stop_after_wait; },
      [&](uint32_t) { stop_after_wait = true; });
  CHECK(done == 1);
  CHECK((calls == std::vector<uint32_t>{0}));

  if (failures) {
    std::fprintf(stderr, "la_capture_sequence: %d failure(s)\n", failures);
    return 1;
  }
  std::puts("la_capture_sequence: PASS");
  return 0;
}
