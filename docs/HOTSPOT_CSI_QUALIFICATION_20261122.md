# Galaxy M14 5G hotspot CSI qualification run

**Date:** 2026-11-22
**Run:** `data/presence_dataset_raw/session_20261122_hotspot_t20_1523/`
**AP:** Galaxy M14 5G hotspot, BSSID `36:9f:61:c1:00:9f`
**Channel:** 149, 5745 MHz, 20 MHz capture configuration
**Trigger:** CCA, `trigger_time_us=20` (t20)
**Purpose:** acquisition-only diagnostic; no occupancy labels and no baseline update.

## Result

| Metric | Result | Gate / interpretation |
|---|---:|---|
| Successful LA captures | 50/50 | PASS |
| Structurally valid, varying IQ buffers | 50/50 | PASS |
| RX-idle barrier | 50/50 (100%) | PASS |
| Post-arm target AP attribution heuristic | 49/50 (98%) | PASS, heuristic only |
| Strict 52-tone CSI | 31/50 (62%) | FAIL, predeclared gate is 80% |
| Target-attributed strict CSI | 30/50 (60%) | Descriptive |
| Median capture start spacing | 131.549 ms | About 7.6 attempts/s |
| Median LA readback time | 131 ms | Hardware readback dominates cadence |

The normal `rtw_8821ce` driver was restored by the script. No baseline was changed.

## CSI quality and rejection reason

Of 50 captures, 31 passed and 19 failed. All 19 failures reported `lag_candidates_rejected`; the repeated-LTF coherence gate was the decisive rejection stage. Accepted captures had:

- median repeated-LTF correlation: 0.99844 (minimum 0.85);
- median STF16 correlation: 0.06755 (maximum 0.50);
- median L-LTF symbol relative error: 0.02123 (maximum 0.25).

This indicates that accepted CSI estimates are strong, while usable L-LTF recovery is intermittent. It does not justify relaxing quality thresholds.

## RX traffic observed

The RX log contained 81 metadata events: 80 beacon frames (`fc0=0x80`) and one other/control-like frame (`fc0=0xe4`). All 81 used rate code 4 (legacy OFDM 6 Mbps) and transmitter address `36:9f:61:c1:00:9f`. Beacon lengths were 227 bytes for 61 frames and 235 bytes for 19 frames. No sustained data-frame traffic was observed in this capture log.

Thus this run did not establish that phone-side YouTube playback created downlink data traffic to the laptop. It primarily repeated beacon-triggered capture, like the earlier runs.

## Interesting alignment observation

Accepted candidate L-LTF start positions cluster in two groups:

- captures 1-32: mostly around sample 1,300;
- captures 33-50: mostly around sample 1,067.

The RX beacon length also changes from 227 to 235 bytes at approximately this boundary. This temporal coincidence is worth investigating, but the RX callback is not a hardware CCA timestamp and the capture-to-frame association is heuristic. Therefore it is not evidence that beacon length caused the shift. Capture 46 also contains an outlying accepted candidate near sample 6,972.

## Comparison and decision

The new 62% CSI yield is better than the earlier 50-capture 56% run documented in the live-feasibility notes, and substantially better than the 18-40% range across the nine batches in the first labelled session. It still misses the 80% qualification gate.

For the practical MVP, the existing live detector requires at least five strict, AP-attributed CSI profiles in a 50-attempt batch. A 62% acquisition yield should normally provide enough valid profiles to run a prototype smoke test, without claiming that acquisition qualification or detection accuracy has been achieved. Keep the strict L-LTF checks, keep `data/live_presence_baseline.json` unchanged, and do not train a classifier from this acquisition-only run.

Next practical action: test the existing room-calibrated live anomaly indicator against the preserved empty-room baseline, with a clearly controlled empty/occupied sequence. If the baseline no longer represents the same AP placement and room state, recalibrate only after recording that the old baseline is being replaced; never overwrite it silently.

## Raw artifacts

This archive preserves all 50 IQ buffers, `rxdemo.log`, `csi_series.jsonl`, its diagnostics, `presence_audit.csv/json`, and `run_manifest.json`.


## Follow-up: live smoke test completed

The controlled empty/occupied live-detector smoke test was subsequently completed using the preserved baseline. It did not demonstrate occupancy separation: both batches crossed the raw anomaly threshold, and their median CSI profiles were only 0.0802 dB RMS apart. A follow-up investigation found strong correlation between the raw anomaly, spectral slope, tone spread, and received signal level. See `docs/LIVE_SMOKE_TEST_ANALYSIS_20261122.md` and `docs/CSI_DRIFT_INVESTIGATION_20261122.md`. No baseline update or CSI quality-gate change was made.


## Subsequent parser correction

The original 31/50 result above was produced by an extractor that could select the second of the two identical L-LTF symbols. After correcting the alignment search, the same archived raw IQ was not yet reprocessed in this report; the 150-capture replay across the three later detector runs reached 150/150. Re-run this 50-capture archive through the corrected extractor before treating its original 31/50 yield as the final acquisition result. The thresholds remain unchanged. See `docs/LTF_ALIGNMENT_RECOVERY_20261122.md`.
