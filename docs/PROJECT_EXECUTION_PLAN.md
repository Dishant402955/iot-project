# Project execution plan: stationary Wi-Fi presence sensing

**Updated: 2026-11-22**

## Objective and scope

Build and evaluate an academic binary stationary-room occupancy prototype using RTL8821CE CSI. Output must distinguish `PRESENT` / `ABSENT` only when evidence is sufficient; otherwise report `UNKNOWN` / `INSUFFICIENT_CSI`. This is not a safety/security alarm and is not an exact RF-DS reproduction.

## Current evidence-based status

| Area | Status | Evidence / interpretation |
|---|---|---|
| Raw IQ capture | Qualified in latest physical run | 50/50 structurally valid captures; RX-idle 50/50 |
| Strict CSI extraction | Qualified in latest run | 50/50 strict CSI; 52 finite active tones |
| Target AP attribution | Heuristic pass | 50/50 latest run; post-arm RX callback, not hardware BSSID filtering |
| Interleaved labelled acquisition | Strong acquisition pass | 497/500 strict CSI; 495/500 target-attributed; 10/10 batches pass |
| Presence separability | Not established | Grouped-by-round classifier unstable; best RBF sensitivity 0.565 |
| Final detector | Not ready | Needs independent sessions, dev-only tuning, frozen held-out test |

## Completed engineering

- RTL8821CE PCIe/VFIO LA raw-IQ capture and restoration workflow.
- Correct Realtek LA selector mapping: CCA=0, CRCOK=1, CRCFAIL=2. CCA is the early-frame trigger.
- Correct understanding of `t<us>` as the MAC LA trigger-time register, not sample count or IQ-buffer duration.
- Strict 52-tone L-LTF extraction and diagnostics.
- Corrected repeated-L-LTF pair alignment by evaluating candidate starts at peak offsets -64, 0, +64. Regression test covers stronger second-symbol peak.
- RX-idle barrier and post-arm AP-source audit heuristic.
- Empty-room baseline-relative live anomaly indicator with separate raw/smoothed states and `INSUFFICIENT_CSI` handling.
- Five-round interleaved collector, raw archive preservation, offline reprocessor, round-level analysis, drift diagnostics, and classifier-readiness report.

## Existing experimental data

The five-round session from 2026-11-22 is development data, not a final test. Its reprocessed form contains 247 ABSENT and 248 PRESENT profiles from 500 attempts. Acquisition yield is high, but classifier generalization across the five temporal rounds is unstable. The best RBF SVM achieved 0.675 balanced accuracy and 0.565 sensitivity; fold accuracy ranged 0.500-0.939. Do not deploy.

The older sequential ABSENT/PRESENT/ABSENT session and RSSI experiments were confounded by drift and remain diagnostic only. See `docs/PRESENCE_SESSION_ANALYSIS.md`, `docs/RSSI_EXPERIMENT_ANALYSIS.md`, and `docs/CSI_DRIFT_INVESTIGATION_20261122.md`.

## Three remaining milestones

### 1. Independent physical sessions

Collect **three new sessions**, each using the same five-round interleaved collector (10 batches, 500 attempts, 30-second settling per batch). Ideally use separate days/time blocks. Existing 2026-11-22 interleaved data plus new sessions 1 and 2 are development data. New session 3 is reserved as the untouched final test.

Before starting, confirm Galaxy M14 battery saver, hotspot power-saving, and hotspot/network settings have not changed since the qualified run. Freeze the current setup. Keep laptop/AP position, channel, room layout, doors/windows, person position, posture, and orientation fixed. Do not introduce traffic or alter capture settings.

Run each session at the physical laptop console only:

```bash
cd ~/projects/iot-project
sudo vendor/.venv/bin/python tools/collect_presence_interleaved.py
```

The collector prints a unique output JSONL path and archives the raw IQ/audit/manifest/CSI series. Do not overwrite or delete these. Provide the output path and terminal summary after each run.

### 2. Final detection algorithm

After sessions 1 and 2 are available, perform offline audits and development-only analysis. Compare within-condition variability, between-condition effect sizes, per-tone shape, common gain, spectral slope, tone spread, CFO/RSSI diagnostics, and round/session consistency. Prefer robust, explainable statistics and temporal smoothing over a heavyweight model. Keep strict CSI gates. Add explicit unknown state for insufficient data and link-health anomalies.

No feature or threshold is final until it is selected using development sessions only. Do not modify the empty-room baseline to make labelled data fit.

### 3. Held-out evaluation

Freeze the complete algorithm, thresholds, preprocessing, and smoothing before opening the labels/results for new session 3. Evaluate once on that entire independent session. Do not randomly split adjacent packets or batches across train/test. Report sensitivity, specificity, balanced accuracy, confusion matrix, false alarms/hour, missed detections, valid-CSI availability, unknown rate, and entry/exit latency. Include per-round results and uncertainty.

If the held-out result is weak or unstable, the correct conclusion is that this hardware/setup did not demonstrate reliable stationary presence detection. Preserve that result rather than tuning against the test session.

## Work split

**User must do:** confirm/freeze phone hotspot and power settings; run the three physical capture sessions at the laptop console; keep the room protocol consistent; return each session path and terminal summary. VFIO temporarily detaches the Wi-Fi adapter, so no remote agent should execute these captures.

**Assistant can do offline:** validate session files and raw archives; inspect diagnostics; implement/refine robust detector and `UNKNOWN` behavior; add tests; tune only on development sessions; freeze the detector; evaluate the untouched held-out session; update reports and handoff.

## Non-negotiable integrity constraints

- Never lower strict CSI gates merely to increase yield.
- Never interpret insufficient CSI as `ABSENT`.
- Never overwrite `data/live_presence_baseline.json` without explicit approval.
- Keep room-specific baseline, labelled data, raw IQ, and derived private session files out of GitHub.
- Never claim accuracy or deployment readiness from the existing single session.
- No VFIO binding, driver reload, or physical capture through SSH/remote coding agent.
- No destructive Git operations or cleanup of user data.

## Current authoritative documents

- `docs/LIVE_DETECTOR_STATUS.md` — technical verdict and latest evidence.
- `docs/HANDOFF.md` — cross-chat state and exact next actions.
- `docs/presence-sensing-runbook.md` — physical capture protocol.
- `docs/PRESENCE_CLASSIFIER_READINESS_20261122.md` — classifier evaluation.
- `docs/LTF_ALIGNMENT_RECOVERY_20261122.md` — extraction bug and fix.
- `docs/LIVE_ACQUISITION_QUALIFICATION_20261122.md` — latest live acquisition metrics.
