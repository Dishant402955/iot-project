# Live presence smoke test analysis - 2026-11-22

## Scope

A controlled two-point smoke test used the existing 40-profile empty-room baseline in `data/live_presence_baseline.json`. The user confirmed the physical setup was unchanged and was stationary near the laptop for the occupied batch. Both runs used `--skip-calibration --once`; neither recalibrated or overwrote the baseline.

This is a diagnostic comparison, not an accuracy evaluation. It contains one empty batch and one occupied batch, with unequal CSI yields.

## Batch-level results

| Metric | Empty room | User stationary near laptop |
|---|---:|---:|
| Capture attempts | 50 | 50 |
| Strict AP-attributed CSI profiles | 25 (50%) | 15 (30%) |
| CSI qualification target | 80% | 80% |
| Median per-profile anomaly | 0.8314 dB | 0.8842 dB |
| Detector anomaly threshold | 0.80 dB | 0.80 dB |
| Peak per-profile anomaly | 0.8900 dB | 0.9694 dB |
| Motion p90 | 0.27 dB | 0.24 dB |
| Motion threshold | 0.61 dB | 0.61 dB |
| Raw threshold result | TRIGGER | TRIGGER |

Both batches crossed the raw anomaly threshold, and neither crossed the motion threshold. Both failed the predeclared 80% CSI-yield qualification gate. The occupied batch had fewer than two-thirds as many valid profiles as the empty batch, so its score estimate is less stable.

## Offline profile comparison

Re-scoring the preserved CSI series against the unchanged baseline produced:

| Profile statistic | Empty room | Occupied |
|---|---:|---:|
| Median-profile RMS distance from baseline | 0.8268 dB | 0.8709 dB |
| Median within-batch per-tone MAD | 0.0862 dB | 0.0932 dB |
| 90th percentile within-batch per-tone MAD | 0.1421 dB | 0.1406 dB |
| Median adjacent-profile RMS | 0.1771 dB | 0.1315 dB |
| 90th percentile adjacent-profile RMS | 0.2726 dB | 0.2425 dB |

The RMS distance between the empty and occupied batch median CSI profiles is only **0.0802 dB**. Their baseline-relative per-tone shift vectors have cosine similarity **0.9969** (per-tone correlation **0.9968**). In other words, both batches show almost the same frequency-shaped displacement from the old baseline. The occupied batch is slightly farther from baseline, but the shape of the shift is overwhelmingly shared with the empty-room batch.

The occupied batch does not show greater adjacent-profile variation: its median and 90th-percentile adjacent-profile RMS are both lower than the empty batch's. This does not support a movement/micro-motion signal in this measurement window.

## One-shot reporting bug and correction

The old CLI printed `ABSENT` for both runs because `--once` starts a fresh `PresenceState`, which has only one vote. The smoother confirms presence only after at least two positive batches in a rolling three-batch window. That output concealed the fact that each batch had crossed the raw anomaly threshold.

The detector now prints:
- `raw_signal=TRIGGER|CLEAR` for the current batch's anomaly/motion threshold result;
- `smoothed=PRESENT|NOT_PRESENT` for the hysteresis/hold state;
- leading `PENDING` when the raw signal triggers but temporal smoothing has not confirmed presence.

This correction changes reporting only. It does not alter the threshold, smoothing rule, CSI acceptance gates, minimum CSI count, or baseline.

## Engineering conclusion

1. The previous `ABSENT` labels from these one-shot runs were misleading. Both runs actually generated a raw threshold trigger, now correctly represented as `PENDING` in one-shot mode.
2. The raw trigger is **not occupancy-specific** in this test: the empty and occupied profile shifts are almost collinear and differ by only 0.0802 dB RMS between batch medians.
3. The 0.05 dB difference between the printed anomaly medians is not convincing evidence of presence detection. The empty-room batch itself already exceeded the anomaly threshold.
4. CSI yield remains poor and variable (50% empty, 30% occupied), below the 80% acquisition gate.
5. Do not lower thresholds, raise/lower smoothing requirements, retrain on this pair, or overwrite the empty-room baseline. No sensitivity, specificity, false-alarm rate, or detection latency can be claimed.

## Next engineering direction

Do not spend another physical capture run merely to repeat this result. First investigate why the same large per-tone displacement appears in both conditions. Compare baseline and current CSI acquisition metadata (CFO, L-LTF start, channel/AP state, and timing) and inspect the historical labelled session's drift. Only propose another controlled physical experiment once a specific, falsifiable cause or feature hypothesis is identified. Keep strict CSI gates unchanged.

## Artifacts

- Empty batch: `/tmp/rtl8821ce-la.yfEH1O/`
- Occupied batch: `/tmp/rtl8821ce-la.3nNS7t/`
- Baseline: `data/live_presence_baseline.json` (unchanged)
- Detector: `tools/live_presence_detector.py`
- Regression tests: `tests/test_live_presence_detector.py`
