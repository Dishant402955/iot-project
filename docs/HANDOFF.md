# Project handoff: Wi-Fi stationary human-presence sensing

**Updated:** 2026-11-22
**Repository:** `/home/user/projects/iot-project`
**Branch:** `main`
**Goal:** evaluate a binary `PRESENT` / `ABSENT` stationary-room detector using RTL8821CE CSI. Use `UNKNOWN` / `INSUFFICIENT_CSI` whenever acquisition or evidence is inadequate.

## Current verdict

The acquisition pipeline is in substantially better shape than the classifier. A fresh physical 50-capture qualification run produced 50/50 strict CSI profiles. The five-round interleaved labelled dataset produced 497/500 strict CSI profiles after reprocessing with the corrected L-LTF alignment. However, leave-one-round-out classification is unstable: the best RBF SVM had 0.675 balanced accuracy and 0.565 sensitivity, with fold accuracy ranging from 0.500 to 0.939. **There is no validated stationary-presence detector yet. Do not deploy or claim accuracy.**

## Latest data and reports

- Development session: `data/presence_dataset/interleaved_20261122_160950.jsonl`.
- Corrected reprocessed output: `data/presence_dataset/interleaved_20261122_160950_reprocessed.jsonl`.
- Raw archive: `data/presence_dataset_raw/interleaved_20261122_160950/`.
- Strict CSI: 497/500 (99.4%); target-attributed strict CSI: 495/500 (99.0%); RX-idle: 500/500; AP heuristic matches: 498/500; 10/10 batches passed acquisition gates.
- Labels: 247 ABSENT and 248 PRESENT profiles.
- Fresh live qualification: 50/50 strict CSI, 50/50 RX-idle, 50/50 target-source heuristic; baseline SHA-256 unchanged: `2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74`.
- Key reports: `docs/LIVE_ACQUISITION_QUALIFICATION_20261122.md`, `docs/LTF_ALIGNMENT_RECOVERY_20261122.md`, `docs/PRESENCE_CLASSIFIER_READINESS_20261122.md`, `docs/CSI_DRIFT_INVESTIGATION_20261122.md`.

## Important extraction fix

`vendor/devourer/tools/la_csi.py` previously selected one matched-filter peak and could choose the second of the two repeated 64-sample L-LTF symbols, then compare it with SIGNAL. It now evaluates candidate pair starts at `peak - 64`, `peak`, and `peak + 64`, including fallback candidates. Strict gates are unchanged. Regression coverage includes the stronger-second-symbol case. Reprocessing improved the five-round session to 497/500 strict CSI. The reprocessor writes a separate `_reprocessed.jsonl`, preserves labels, and refuses overwrite.

## Hardware / physical-capture constraints

- Ubuntu 22.04.5, RTL8821CE PCI `10ec:c821`, BDF `0000:01:00.0`, driver `rtw_8821ce`, interface `wlp1s0`.
- 1T1R, 20 MHz, 20 Msps, 8192 complex samples, 52 active tones.
- Dedicated Galaxy M14 hotspot used in recent runs: 5 GHz channel 149.
- CCA is the early-frame trigger. `t<us>` sets Realtek's MAC LA trigger-time register, not sample count or IQ-buffer duration.
- Capture temporarily detaches the Wi-Fi adapter using VFIO and interrupts connectivity. **Only the user may run physical capture from the laptop console. Never run capture remotely or over SSH.**
- AP attribution is heuristic: first good post-arm RX callback plus address checks and RX-idle barrier. It is not hardware source-MAC filtering or proof that the exact callback frame caused the IQ trigger.

Strict CSI gates: exactly 52 finite tones; repeated L-LTF correlation >=0.85; STF16 correlation <=0.50; L-LTF symbol relative error <=0.25; target-source audit match; RX-idle barrier. Do not relax.

## Three remaining milestones and exact user actions

### First: freeze hotspot configuration

Before another capture, confirm that Galaxy M14 battery saver, hotspot power-saving, and hotspot/network settings have not changed during the experiments. Keep the current known-good configuration fixed. Also keep laptop/AP placement, channel, room layout, doors/windows, and person position/orientation fixed. Do not change trigger timing or thresholds.

### Second: collect three independent physical sessions

Use the same command for each session, ideally on separate days/time blocks. Each run performs five paired rounds (10 batches, 500 attempts), alternating ABSENT/PRESENT order, with 30-second settling per batch.

```bash
cd ~/projects/iot-project
sudo vendor/.venv/bin/python tools/collect_presence_interleaved.py
```

Follow every on-screen prompt. For ABSENT, leave the monitored room and stay at least 5 m from both laptop and AP, preferably behind a closed door; keep other people out. For PRESENT, occupy the same marked position, posture, and orientation for every round and remain still. Keep doors/windows/furniture and phone/laptop positions unchanged. No streaming/downloads or deliberate traffic.

At the end, copy the printed JSONL path and summary. The matching raw capture archive is created under `data/presence_dataset_raw/`. Do not rename, delete, or overwrite either. Repeat for sessions 2 and 3.

Dataset split: existing 2026-11-22 interleaved session + new sessions 1 and 2 are development data. New session 3 is the untouched final held-out test. Do not inspect/tune against session 3 before the detector is frozen.

### Third: assistant completes offline work

After each capture is returned, inspect the exact JSONL and corresponding raw archive. Validate labels, round order, capture counts, BSSID/channel, dimensions, finite values, source audit, RX-idle, CSI yield, and drift. Then use development sessions only to select robust features and thresholds, implement explicit unknown/link-health handling, add tests, and freeze the complete detector. Evaluate once on the untouched third session and report sensitivity, specificity, balanced accuracy, false alarms/hour, missed detections, availability, unknown rate, and entry/exit latency.

No honest held-out evaluation can be completed before the physical sessions exist. Coding, tests, and offline analysis can be completed in a consolidated pass after the data is available.

## Key files

- `tools/collect_presence_interleaved.py` — physical five-round collector.
- `tools/reprocess_presence_archives.py` — offline corrected CSI extraction/reprocessing.
- `tools/analyze_interleaved_presence.py` — round-level analysis.
- `tools/live_presence_detector.py` — experimental baseline-relative live indicator, not validated classifier.
- `tools/analyze_presence_run.py` — strict capture/source audit.
- `vendor/devourer/tools/la_csi.py` — strict L-LTF CSI extraction.
- `data/live_presence_baseline.json` — local empty-room baseline; never overwrite.
- `docs/PROJECT_EXECUTION_PLAN.md` — authoritative remaining milestones.
- `docs/presence-sensing-runbook.md` — physical operator protocol.

## Tests / checks

Run offline from repository root:

```bash
vendor/.venv/bin/python -m unittest discover -s tests -v
vendor/.venv/bin/python vendor/devourer/tools/la_csi.py --selftest
vendor/.venv/bin/python vendor/devourer/tests/la_csi_series_selftest.py
python3 -m compileall -q tools vendor/devourer/tools tests
bash -n tools/rtl8821ce_pcie_la_capture.sh
git diff --check
```

## Data and Git integrity

Room-specific baseline, labelled JSONL, raw IQ archives, RSSI CSVs, and derived private analyses are local-only and ignored by Git. Commit source, tests, research notes, and documentation only. Never reset, clean, force-push, or overwrite baseline/data.
