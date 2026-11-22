# Live detector and validation status

**Updated: 2026-11-22**

## Verdict

The RTL8821CE acquisition and strict CSI extraction path is now qualified on a fresh 50-capture physical run, and the five-round interleaved dataset has been reprocessed successfully after fixing an L-LTF pair-alignment bug. However, the current presence classifier is **not validated**. Grouped-by-round evaluation is unstable and sensitivity is inadequate. The live baseline-relative anomaly detector remains experimental.

## Acquisition evidence

### Fresh live qualification

- 50/50 strict CSI profiles; all 52 active tones finite.
- RX-idle barrier 50/50.
- Post-arm target AP source heuristic 50/50.
- Repeat L-LTF correlation: min 0.99589, median 0.99736, max 0.99907.
- STF16 correlation: min 0.05995, median 0.06428, max 0.07191.
- L-LTF symbol relative error: min 0.01959, median 0.02322, max 0.03072.
- Driver restored to `rtw_8821ce`; empty-room baseline SHA-256 unchanged: `2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74`.

This is an acquisition-quality pass, not proof of presence detection. AP attribution remains a post-arm callback heuristic because CCA is not source-MAC-filtered.

### Five-round interleaved dataset

Original session: `data/presence_dataset/interleaved_20261122_160950.jsonl`
Reprocessed session: `data/presence_dataset/interleaved_20261122_160950_reprocessed.jsonl`
Raw archive: `data/presence_dataset_raw/interleaved_20261122_160950/`

- 500 attempts across 10 batches and five paired rounds.
- 497/500 strict CSI (99.4%).
- 495/500 target-attributed strict CSI (99.0%).
- RX-idle 500/500; AP heuristic matches 498/500.
- All 10 batches passed acquisition gates.
- ABSENT: 247 profiles; PRESENT: 248 profiles.

The reprocessor preserves original labels and raw files, writes a separate output, and refuses to overwrite.

## L-LTF extraction correction

The matched-filter extractor could select the second of the two repeated 64-sample L-LTF symbols as the pair start, then compare it against SIGNAL. The fix tests candidate pair starts at `peak - 64`, `peak`, and `peak + 64`, including fallback candidates. The strict CSI thresholds were not changed. Regression coverage includes the case where the second-symbol peak is stronger. Synthetic noise/interference tests did not falsely pass. Details: `docs/LTF_ALIGNMENT_RECOVERY_20261122.md`.

## Classifier evaluation

Leave-one-round-out evaluation on the single physical session is unstable. Best RBF SVM: accuracy 0.675, balanced accuracy 0.675, sensitivity 0.565, specificity 0.785, ROC AUC 0.716. Fold accuracy ranged from 0.500 to 0.939. Other models performed worse or showed poor sensitivity. This is insufficient for deployment and is not independent-session validation. Details: `docs/PRESENCE_CLASSIFIER_READINESS_20261122.md`.

## Detector semantics and safety

- `PRESENT` / `ABSENT` are experimental states relative to a calibrated empty-room baseline.
- `PENDING` indicates a raw trigger that has not met temporal smoothing criteria.
- `INSUFFICIENT_CSI` means the batch lacks enough accepted measurements to score. It must not update the state and must never be mapped to `ABSENT`.
- Baseline must not be overwritten during labelled data collection or classifier evaluation.
- Drift indicators (common gain, spectral slope, tone spread, RSSI, CFO) are diagnostics/nuisance variables until validated as features.

## Remaining work

1. Collect three additional independent five-round interleaved sessions. Keep configuration and environment fixed; ideally collect on separate days/time blocks.
2. Use the existing 2026-11-22 session and the first two new sessions for development only. Reserve the third new session untouched as the final held-out test.
3. Audit labels, capture provenance, acquisition gates, drift, and session-level separation.
4. Tune a simple robust detector on development sessions only, retaining strict CSI gates and explicit unknown handling. Freeze features, thresholds, and smoothing before evaluating the held-out session.
5. Report sensitivity, specificity, balanced accuracy, false alarms/hour, missed detections, CSI availability, unknown rate, and entry/exit latency with session-level uncertainty.

Do not claim success unless independent held-out performance supports it. If it does not, report the hardware/configuration limitation honestly.
