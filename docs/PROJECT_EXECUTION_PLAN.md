# Project execution plan: stationary Wi-Fi presence sensing

**Updated: 2026-11-22**

## Objective and scope

Build and evaluate an academic stationary-room occupancy prototype using RTL8821CE CSI. The intended outputs are PRESENT and ABSENT only when supported by validated evidence; otherwise the system must return UNKNOWN / INSUFFICIENT_CSI. This is not a safety/security alarm or an exact RF-DS reproduction.

## Current evidence-based status

| Area | Status | Evidence / interpretation |
|---|---|---|
| RTL8821CE raw-IQ acquisition | Qualified | Dedicated physical qualification; capture/driver restoration completed |
| Strict CSI extraction | Qualified | 52 finite active tones; repeated-L-LTF alignment fix; strict gates unchanged |
| Target AP attribution | Heuristic only | Post-arm RX callback and address audit; not hardware source-MAC filtering |
| Interleaved Sessions 1 and 2 | Development data audited | 1,000 attempts, 999 valid strict CSI profiles, all 20 batches pass acquisition gates |
| Interleaved Session 3 | Reserved held-out data | 500 attempts, 497 valid strict CSI profiles; evaluated once after benchmark freeze; no further tuning |
| Occupancy separability | Not established | Development grouped batch evaluation has 0.80 balanced accuracy but 0.60 sensitivity; cross-session transfer has 0.50 balanced accuracy and 0 sensitivity |
| Final occupancy detector | Not available | Existing live script is a baseline-relative anomaly indicator, not a validated occupancy classifier |
| Private original-data backup | Not verified | Public anonymized feature datasets are on GitHub; labelled originals/raw IQ need private off-device backup |

## Completed engineering and data collection

- RTL8821CE PCIe/VFIO LA raw-IQ capture and restoration workflow.
- Correct Realtek LA selector mapping: CCA=0, CRCOK=1, CRCFAIL=2. CCA is the early-frame trigger.
- Correct understanding of t<us> as the MAC LA trigger-time register, not sample count or IQ-buffer duration.
- Strict 52-tone L-LTF extraction and diagnostics.
- Corrected repeated-L-LTF pair alignment by evaluating candidate starts at peak offsets -64, 0, +64. Regression test covers stronger second-symbol peak.
- RX-idle barrier and post-arm AP-source audit heuristic.
- Five-round interleaved collector, raw archive preservation, offline reprocessor, round-level analysis, and drift diagnostics.
- Three physical interleaved sessions collected and anonymized public copies published under data/public_dataset/.
- Development-only grouped analysis implemented in tools/analyze_presence_development.py; it defaults to Sessions 1 and 2, accepts Sessions 4 and 5 via repeated --session flags, and rejects Session 3 by source SHA-256.

## Development analysis result

Sessions 1 and 2 contain 1,000 attempts and 999 valid profiles (500 ABSENT, 499 PRESENT). All 20 batches passed both acquisition gates and RX-idle was 100% in every batch.

A batch-median, nearest-centroid diagnostic with leave-one-session-round-pair-out validation produced 0.80 accuracy / 0.80 balanced accuracy, 0.60 sensitivity and 1.00 specificity (TP=6, TN=10, FP=0, FN=4). However, training on Session 1 and testing Session 2, and vice versa, both produced 0.50 accuracy / balanced accuracy, 0.00 sensitivity and 1.00 specificity. The classifier predicted every held-out batch as ABSENT in both transfer directions. This is not reliable occupancy detection; the within-development score is not sufficient evidence to deploy or freeze a detector.

See docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.md and its machine-readable JSON result.

## Frozen benchmark model

A simple batch-median nearest-centroid benchmark was frozen from Sessions 1 and 2 in `models/presence_centroid_baseline_s1_s2_v1.json` and evaluated exactly once on Session 3. Result: TP=3, TN=4, FP=1, FN=2; accuracy 0.70, sensitivity 0.60, specificity 0.80, balanced accuracy 0.70. CSI availability was 497/500 and all 10 batches passed acquisition gates. This is not a deployment candidate. Do not tune on Session 3. See `docs/BASELINE_MODEL_FREEZE.md` and `docs/HELD_OUT_EVALUATION_SESSION3_20261122.md`.

## Remaining milestones

### 1. Secure original data

The anonymized public feature datasets are committed to GitHub. Original labelled JSONL files and raw IQ archives remain local-only. Verify raw archive file counts and sizes with sudo, then create and verify an encrypted private/off-device backup. Never upload raw IQ or private labelled source data to the public repository. Do not overwrite the empty-room baseline.

### 2. Obtain more development evidence

Collect at least two additional independent interleaved sessions (Sessions 4 and 5), preferably on separate days/time blocks, using the same qualified physical setup and protocol. These join Sessions 1 and 2 as development data. Session 3 has already been evaluated once with the frozen benchmark and cannot be reused for tuning.

Physical capture must run from the laptop's physical console only:

```bash
cd ~/projects/iot-project
sudo vendor/.venv/bin/python tools/collect_presence_interleaved.py
```

Do not run capture, VFIO binding, or driver reload through SSH or the remote coding agent. Keep the Galaxy M14 AP, channel, bandwidth, laptop/AP positions, room layout, and subject position/orientation fixed. Do not relax strict CSI gates.

### 3. Reassess separability on development sessions only

Extend the development analysis to Sessions 1, 2, 4 and 5. Compare within-condition variability, between-condition effect sizes, per-tone shape, common gain, spectral slope, tone spread, temporal features, and round/session consistency. Keep batch/session grouping intact. Do not select a model using random packet-level splits. If the added sessions still fail cross-session validation, conclude that this hardware/setup has not demonstrated a usable stationary-presence signal.

### 4. Implement and freeze a detector only if justified

A valid future detector needs a reproducible feature pipeline, trained model or statistical rule, confidence/abstention behavior, temporal state logic, and explicit quality/link-health checks. Insufficient CSI must never become ABSENT. The frozen benchmark has already failed to establish adequate held-out performance; a revised model needs new development data and a new untouched held-out session.

The live tool tools/live_presence_detector.py is a channel-anomaly monitor only. It always reports UNKNOWN_UNVALIDATED for occupancy, separately prints channel-anomaly diagnostics, enforces exact tones/structural CSI/target-source/RX-idle gates, and refuses to overwrite an existing baseline without the explicit --replace-baseline flag. The development analysis accepts multiple development sessions via repeated --session flags and rejects held-out Session 3 by SHA-256.

### 5. One-time held-out evaluation

Completed: Session 3 was evaluated once after the benchmark freeze. It produced TP=3, TN=4, FP=1, FN=2; balanced accuracy 0.70 and sensitivity 0.60. No tuning was performed. Any subsequent model change requires a new untouched held-out session.

### 6. Live hardware integration and final release

Only after offline evidence justifies the detector, integrate it into continuous live capture. Validate empty-to-occupied, stationary occupied, occupied-to-empty, poor-CSI UNKNOWN, and CSI recovery transitions on the physical laptop. Verify graceful Ctrl+C shutdown, driver restoration, no leaked processes/locks, logging, and baseline integrity. Complete final architecture, reproducibility, evaluation, installation, and troubleshooting documentation.

## Non-negotiable integrity constraints

- Never lower strict CSI gates merely to increase yield.
- Never interpret insufficient CSI as ABSENT.
- Never overwrite data/live_presence_baseline.json without explicit approval.
- Keep room-specific baseline, labelled data, raw IQ, and derived private session files out of GitHub.
- Never claim accuracy or deployment readiness from development-only or within-session results.
- Session 3 was evaluated once after benchmark freeze. Never use it for further feature/model/threshold tuning.
- No VFIO binding, driver reload, or physical capture through SSH/remote coding agent.
- No destructive Git operations or cleanup of user data.

## One-time held-out result

Session 3 was evaluated once with the frozen model. It missed two of five PRESENT batches and generated one false positive among five ABSENT batches. No further tuning on Session 3 is permitted. A revised model requires new development sessions and a new untouched held-out session.

## Final project report

`docs/FINAL_PROJECT_REPORT.md` records the completed software/research work and the negative detector result. The project is not an operational occupancy detector. Remaining work is physical data collection, private raw-data backup, and a new untouched held-out evaluation only if a revised detector is justified.

## Authoritative documents

- docs/LIVE_DETECTOR_STATUS.md — technical verdict and latest evidence.
- docs/HANDOFF.md — cross-chat state and exact next actions.
- docs/presence-sensing-runbook.md — physical capture protocol.
- docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.md — Sessions 1 and 2 analysis.
- docs/PRESENCE_CLASSIFIER_READINESS_20261122.md — earlier single-session classifier evaluation.
- docs/LTF_ALIGNMENT_RECOVERY_20261122.md — extraction bug and fix.
- docs/LIVE_ACQUISITION_QUALIFICATION_20261122.md — live acquisition qualification.
