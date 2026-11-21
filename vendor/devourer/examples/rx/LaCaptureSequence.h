#ifndef DEVOURER_LA_CAPTURE_SEQUENCE_H
#define DEVOURER_LA_CAPTURE_SEQUENCE_H

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <string>
#include <thread>

namespace devourer::demo {

/* A pure orchestration helper: the capture callback owns the actual device
 * operation. A failed capture stops the sequence; no blind re-arm after a
 * timeout, unsupported block, or wedged device. */
template <typename CaptureFn, typename StopFn, typename SleepFn>
uint32_t run_la_capture_sequence(uint32_t count, uint32_t interval_ms,
                                 CaptureFn capture, StopFn stop,
                                 SleepFn sleep) {
  uint32_t completed = 0;
  for (uint32_t i = 0; i < count; ++i) {
    if (stop() || !capture(i))
      break;
    ++completed;
    if (i + 1 == count)
      break;

    uint32_t remaining = interval_ms;
    while (remaining && !stop()) {
      const uint32_t slice = std::min<uint32_t>(remaining, 50);
      sleep(slice);
      remaining -= slice;
    }
  }
  return completed;
}

inline std::string la_capture_output_path(const std::string &base,
                                          uint32_t count, uint32_t index) {
  if (count <= 1)
    return base;
  const auto slash = base.find_last_of('/');
  const auto dot = base.find_last_of('.');
  const auto insert = (dot != std::string::npos &&
                       (slash == std::string::npos || dot > slash))
                          ? dot
                          : base.size();
  std::string suffix = ".0000";
  uint32_t n = index + 1;
  for (int pos = 4; pos >= 1; --pos) {
    suffix[static_cast<size_t>(pos)] = static_cast<char>('0' + (n % 10));
    n /= 10;
  }
  return base.substr(0, insert) + suffix + base.substr(insert);
}

}  // namespace devourer::demo

#endif
