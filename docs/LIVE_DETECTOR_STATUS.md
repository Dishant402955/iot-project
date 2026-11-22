# Live detector and validation status

**Updated: 2026-11-22**

## Verdict

The RTL8821CE acquisition and strict CSI extraction path is qualified for the tested physical setup. Four interleaved sessions have been collected and anonymized public feature copies have been released. However, the available development data does **not** support a reliable stationary-presence classifier. The project does not yet have a validated working occupancy detector.

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

### Four interleaved sessions

| Session | Purpose | Attempts | Valid strict CSI | Notes |
|---|---|---:|---:|---|
| 1 | Development | 500 | 500 | 10/10 batches pass both acquisition gates |
| 2 | Development | 500 | 499 | 10/10 batches pass both acquisition gates |
| 3 | Reserved held-out | 500 | 497 | 10/10 batches pass both acquisition gates; evaluated once after model freeze |
| 4 | Development | 500 | 498 | 10/10 batches pass both acquisition gates; 248 ABSENT + 250 PRESENT profiles |

All four sessions have 500 attempts, five paired rounds and ten batches. Every retained profile has 52 active tones. Anonymized feature datasets for Sessions 1-3 are already published; Session 4 has been anonymized and privacy-scanned and is included in the pending repository release. Original labelled JSONL and raw IQ remain local-only.

### Development analysis: Sessions 1 and 2 (Session 4 pending inclusion)

- 1,000 attempts; 999 valid strict CSI profiles (500 ABSENT, 499 PRESENT).
- 20/20 batches pass both acquisition gates; RX-idle is 100% in every batch.
- Grouped leave-one-session-round-pair-out batch-median nearest-centroid diagnostic: accuracy 0.80, sensitivity 0.60, specificity 1.00, balanced accuracy 0.80 (TP=6, TN=10, FP=0, FN=4).
- Train Session 1/test Session 2: accuracy 0.50, sensitivity 0.00, specificity 1.00, balanced accuracy 0.50.
- Train Session 2/test Session 1: same result. Both transfer tests predicted all batches ABSENT.

The cross-session result fails. The within-development result is based on only ten paired rounds and has poor sensitivity. No model should be frozen or deployed from these data. Full details and reproducible script: docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.md, tools/analyze_presence_development.py.

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
2. Collect one more independent development session (Session 5), preferably in a separate day/time block, with the same qualified physical setup.
3. After Session 5, extend grouped/session-transfer analysis to Sessions 1, 2, 4 and 5 only. Session 4 acquisition summary: 498/500 strict CSI, 10/10 batches passed both gates, RX-idle 500/500; descriptive aggregate median-profile distance 0.1707 dB RMS. See docs/SESSION4_ACQUISITION_ANALYSIS_20261122.md. Session 3 has already been used for its one-time benchmark evaluation and must not be reused for tuning.
4. If new development evidence supports a revised model, implement explicit confidence/abstention and quality handling, freeze it, and obtain a new untouched held-out session.
5. Integrate live inference and validate physical occupancy transitions only if a new independent held-out result supports it.

If additional development data still fails cross-session validation, report that this hardware/setup did not demonstrate reliable stationary-presence detection. Do not tune against the held-out session. The development analysis accepts repeated --session arguments for Sessions 4 and 5 and rejects the held-out Session 3 by its SHA-256, even if renamed.
