# Live detector and validation status

**Updated: 2026-11-22**

## Verdict

The RTL8821CE acquisition and strict CSI extraction path is qualified for the tested physical setup. Five interleaved sessions have been collected and anonymized public feature copies have been released. However, the available development data does **not** support a reliable stationary-presence classifier. The project does not yet have a validated working occupancy detector.

The live tool tools/live_presence_detector.py is now a baseline-relative channel-anomaly monitor only. It always reports UNKNOWN_UNVALIDATED for occupancy and separately reports ANOMALY / NO_ANOMALY as channel diagnostics. It never emits PRESENT/ABSENT from anomaly thresholds. Its capture acceptance path requires the exact 52-tone set, structural CSI validity, target-source match, and RX-idle audit. It refuses to overwrite an existing baseline unless --replace-baseline is explicitly supplied.

## Acquisition evidence

### Fresh live qualification

- 50/50 strict CSI profiles; all 52 active tones finite.
- RX-idle barrier 50/50.
- Post-arm target AP source heuristic 50/50.
- Repeat L-LTF correlation: min 0.99589, median 0.99736, max 0.99907.
- STF16 correlation: min 0.05995, median 0.06428, max 0.07191.
- L-LTF symbol relative error: min 0.01959, median 0.02322, max 0.03072.
- Driver restored to rtw_8821ce; empty-room baseline SHA-256 unchanged: 2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74.

This is an acquisition-quality pass, not proof of presence detection. AP attribution remains a post-arm callback heuristic because CCA is not source-MAC-filtered.

### Five interleaved sessions

| Session | Purpose | Attempts | Valid strict CSI | Notes |
|---|---|---:|---:|---|
| 1 | Development | 500 | 500 | 10/10 batches pass both acquisition gates |
| 2 | Development | 500 | 499 | 10/10 batches pass both acquisition gates |
| 3 | Reserved held-out | 500 | 497 | 10/10 batches pass both acquisition gates; evaluated once after model freeze |
| 4 | Development | 500 | 498 | 10/10 batches pass both acquisition gates; 248 ABSENT + 250 PRESENT profiles |
| 5 | Development | 500 | 492 retained target-attributed strict CSI (498 structural strict CSI) | 10/10 batches pass both acquisition gates; 246 ABSENT + 246 PRESENT retained profiles |

All five sessions have 500 attempts, five paired rounds and ten batches. Every retained profile has 52 active tones. Anonymized feature datasets for Sessions 1-5 are published under data/public_dataset/. Session 3 remains reserved as the already-consumed one-time held-out evaluation; Sessions 1, 2, 4 and 5 are development data. Original labelled JSONL and raw IQ remain local-only.

### Combined development analysis: Sessions 1, 2, 4 and 5

- 2,000 attempts; 1,989 retained strict CSI profiles (994 ABSENT, 995 PRESENT).
- 40/40 batches pass both acquisition gates; each retained feature row has 52 active tones.
- Grouped nearest-centroid: accuracy 0.80, sensitivity 0.65, specificity 0.95, balanced accuracy 0.80 (TP=13, TN=19, FP=1, FN=7).
- Eight candidates were compared using 20 paired-round folds and four leave-one-session-out folds. Small MLP and Random Forest both scored 0.850 grouped balanced accuracy and 0.800 pooled leave-one-session-out balanced accuracy; sensitivity was 0.60 and 0.65 respectively.
- Leave-one-session-out performance varies: the MLP balanced accuracy is 0.60 on Session 1 and 0.80 on Sessions 2, 4 and 5; Random Forest is 0.60, 0.90, 0.90 and 0.80 respectively.

No candidate demonstrates dependable generalization. Do not deploy a classifier. Full details: `docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.md`, `docs/PRESENCE_MODEL_COMPARISON_20261122.md`, and their JSON reports. Session 3 was not accessed by these analyses.

## L-LTF extraction correction

The matched-filter extractor could select the second of the two repeated 64-sample L-LTF symbols as the pair start, then compare it against SIGNAL. The fix tests candidate pair starts at peak - 64, peak, and peak + 64, including fallback candidates. Strict CSI thresholds were not changed. Regression coverage includes the case where the second-symbol peak is stronger. Details: docs/LTF_ALIGNMENT_RECOVERY_20261122.md.

## Detector semantics and safety

- Intended final outputs: PRESENT, ABSENT, UNKNOWN / INSUFFICIENT_CSI.
- INSUFFICIENT_CSI means the batch lacks enough accepted measurements to score. It must not update occupancy state and must never be mapped to ABSENT.
- Drift indicators (common gain, spectral slope, tone spread, RSSI, CFO) remain diagnostics/nuisance variables until validated as features.
- The empty-room baseline is unchanged and must not be overwritten without explicit approval.

## One-time held-out benchmark: Session 3

The frozen Sessions 1/2 nearest-centroid benchmark was evaluated once on Session 3. Confusion matrix: TP=3, TN=4, FP=1, FN=2. Accuracy=0.70, sensitivity=0.60, specificity=0.80, balanced accuracy=0.70. CSI availability was 497/500 (99.4%); all 10 batches passed acquisition gates. This is insufficient for reliable occupancy detection. Two of five PRESENT batches were missed and one of five ABSENT batches was falsely marked PRESENT. Do not tune on Session 3. Full result: `docs/HELD_OUT_EVALUATION_SESSION3_20261122.md`.

## Frozen benchmark model

A non-deployable batch-median nearest-centroid benchmark is frozen from Sessions 1 and 2 solely for a one-time Session 3 evaluation. It has no calibrated confidence/abstention and must not drive occupancy decisions. Specification: `docs/BASELINE_MODEL_FREEZE.md`.

## Final project report

See `docs/FINAL_PROJECT_REPORT.md` for the complete research report, acquisition method, session results, validation metrics, limitations, and reproducibility commands.

## Remaining work

1. Verify and privately back up original labelled JSONL and raw IQ archives; the raw archive contents have not been fully verified or backed up off-device.
2. Obtain additional independent development data and a new untouched held-out session if a revised detector is pursued. The combined Sessions 1, 2, 4 and 5 analysis is complete. Session 4 analysis: `docs/SESSION4_ACQUISITION_ANALYSIS_20261122.md`. Session 5 analysis: `docs/SESSION5_ACQUISITION_ANALYSIS_20261122.md`. Session 5 had 498/500 strict structural CSI profiles, 492/500 target-attributed strict CSI profiles retained, 10/10 batches passed both gates, and RX-idle 500/500. Session 3 has already been used for its one-time benchmark evaluation and must not be reused for tuning.
4. If new development evidence supports a revised model, implement explicit confidence/abstention and quality handling, freeze it, and obtain a new untouched held-out session.
5. Integrate live inference and validate physical occupancy transitions only if a new independent held-out result supports it.

If additional development data still fails cross-session validation, report that this hardware/setup did not demonstrate reliable stationary-presence detection. Do not tune against the held-out session. The development analysis accepts repeated --session arguments for Sessions 4 and 5 and rejects the held-out Session 3 by its SHA-256, even if renamed.
