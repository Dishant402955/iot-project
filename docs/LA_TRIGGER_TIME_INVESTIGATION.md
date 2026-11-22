# RTL8821CE LA trigger-time investigation

**Date:** 2026-11-22
**Status:** Source-level semantics corrected; exact timing relative to CCA still requires hardware confirmation.

## Critical correction

The project previously described the `t<us>` argument as the length of the IQ capture window. That description was wrong.

The argument is parsed into `LaParams::trigger_time_us`. `LaCapture::setup_trigger_time()` passes it to the Realtek MAC LA trigger-time register configuration:

- It selects the time-unit field in register `0x7cc`.
- It writes the count into bits `0x7f00` of register `0x7c0`.
- The Realtek HAL structure names the corresponding field `la_trigger_time` and documents its unit as microseconds.
- The upstream Realtek function is named `phydm_la_mode_set_trigger_time()` and logs it as `Trig_Time`.

This field is therefore a MAC LA **trigger-time setting**, not the requested number of IQ samples. The available source establishes how the register is configured, but does not fully establish the exact timing relationship between this value and a CCA event on this RTL8821CE revision. Treat it as a hardware timing/offset control until that relationship is verified. Do not call it a capture duration or assume a value of 200 means 200 us of samples.

## Actual buffer evidence

The IQ sample count is determined by the LA buffer geometry/readback path, not by `trigger_time_us`. The two archived hardware runs prove this directly:

| Run | Trigger-time setting | Sample rate | DVLA sample count | Sample duration |
|---|---:|---:|---:|---:|
| `session_20261122_111025` | 20 us | 20 Msps | 8,192 | 409.6 us |
| `session_20261122_t200` | 200 us | 20 Msps | 8,192 | 409.6 us |

The DVLA header stores the field at offset 20 as `trigger_time_us`; `la_decode.py` already decodes it under that name. The historical run manifests used the misleading key `capture_duration_us`; those existing artifacts are preserved unchanged, but new manifests use `trigger_time_us`.

## What the two hardware runs actually establish

| Metric | t20 session | t200 diagnostic |
|---|---:|---:|
| Attempts | 450 | 50 |
| Strict CSI accepted | 117 | 0 |
| Strict CSI yield | 26.0% | 0% |
| Fallback best repeat-correlation median on failed captures | 0.508 | 0.2674 |
| Fallback best symbol relative-error median | about 0.497 | 0.6055 |

The labelled JSONL stores 116 CSI profiles while the archived per-capture extractor diagnostics report 117 successes. Keep this one-profile discrepancy visible; do not silently rewrite the dataset.

The t200 setting coincided with much worse L-LTF coherence. It does **not** demonstrate that a longer capture window harms CSI, because the returned sample count and duration were the same in both runs. It demonstrates that changing the MAC trigger-time register from 20 to 200 us coincided with a sharp quality drop.

The fallback candidate start index also shifted: failed t20 captures had a median best-candidate start around sample 1,244, while t200 captures had a median around sample 3,970. These are indices in the reordered IQ buffer, not hardware timestamps. They support investigating capture alignment, but do not by themselves prove the physical timing of the trigger.

## What traffic was actually present

The archived RX metadata shows that the acquisition environment was almost beacon-only:

| Run | RX frames logged | Beacon frames (`fc0=0x80`) | Other frames | RX rate code |
|---|---:|---:|---:|---:|
| t20 labelled session | 774 | 771 | 3 | 4 for all frames |
| t200 diagnostic | 92 | 92 | 0 | 4 for all frames |

In the vendored rate definitions, RX rate code 4 is `DESC_RATE6M` (legacy OFDM 6 Mbps). The laptop therefore mostly observed periodic AP beacons, not a traffic-rich mixture of downlink data frames. This is a useful limitation to test next: CCA may be seeing a narrow set of packet types and low traffic diversity. It does not prove that beacon-only traffic caused the L-LTF failures.

## RX-frame timing limitation

The archived `rxdemo.log` records `armed_steady_us`, `done_steady_us`, and software RX-callback timestamps. The AP emits beacon-like management frames roughly every 102.4 ms in the inspected run. The nearest target RX callback to the arm timestamp has a median absolute difference of about 25.8 ms in the t200 run.

These callback timestamps are not hardware CCA-trigger timestamps. The CCA trigger is not BSSID-filtered, and the software callback occurs after frame reception. Therefore a nearest RX callback cannot be treated as an exact capture-to-frame join. The current first-good-RX-frame-after-arm audit remains a source-attribution heuristic only.

## Engineering consequences

1. Do not interpret t20 and t200 as 20-us and 200-us sample windows.
2. Keep the current default at t20 until a controlled timing experiment justifies a change.
3. Preserve all raw IQ and strict quality gates; do not lower thresholds to make t200 pass.
4. Before another blind sweep, determine the register's timing semantics for RTL8821CE and relate IQ sample positions to known AP frame timing.
5. The next practical hardware experiment should keep the current t20 setting and create sustained AP downlink traffic from a second Wi-Fi client connected to the same AP (for example, a continuous download/video stream). The previous runs were almost entirely 6 Mbps AP beacons. Keep the laptop/AP fixed, collect 50 CCA captures, and compare frame-type/rate diversity plus strict CSI yield. This isolates traffic diversity without changing trigger timing. It must remain acquisition-only, not presence-labelled data, and must not update the empty-room baseline. If a second client is unavailable, do not substitute an uncontrolled sweep.

## Code/documentation correction

The capture script now exposes `WIFI_PRESENCE_LA_TRIGGER_TIME_US`. The previous `WIFI_PRESENCE_LA_CAPTURE_DURATION_US` and `WIFI_PRESENCE_LA_POST_TRIGGER_US` names remain compatibility aliases only. New run manifests record `trigger_time_us`. The `t<us>` token remains in Devourer's capture grammar for compatibility with the Realtek tool convention.

The authoritative source references are the vendored Realtek field declaration in `vendor/devourer/hal/halbb/g6/vendor/halbb_la_mode.h`, the register setup in `vendor/devourer/src/LaCapture.cpp`, and the upstream Realtek `phydm_la_mode_set_trigger_time()` implementation. The latter writes the trigger-time unit and count registers; it does not size the IQ sample buffer.
