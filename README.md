# Wi-Fi Stationary Human-Presence Sensing

Academic research prototype investigating whether a Realtek RTL8821CE 1T1R adapter can distinguish a stationary person from an empty room using Wi-Fi CSI. The intended product states are `PRESENT`, `ABSENT`, and `UNKNOWN` / `INSUFFICIENT_CSI` when acquisition or evidence is inadequate.

## Current verdict (2026-11-22)

**The acquisition pipeline is qualified for the tested setup, but the collected development data does not establish reliable stationary-presence detection.** Do not report a working detector or accuracy claim.

Three interleaved sessions have been collected. Sessions 1 and 2 are development data; Session 3 is reserved as held-out and has not been used for model selection. Sessions 1 and 2 contain 999 valid strict CSI profiles from 1,000 attempts, with all 20 batches passing acquisition gates. A grouped batch-median nearest-centroid diagnostic gives 0.80 balanced accuracy but only 0.60 sensitivity. Cross-session transfer in both directions gives 0.50 balanced accuracy and 0.00 sensitivity, predicting every batch as ABSENT. This is not useful generalization.

A simple nearest-centroid benchmark has now been frozen from Sessions 1 and 2 for a one-time Session 3 evaluation; it is not a deployment candidate. The live tool `tools/live_presence_detector.py` remains a **channel-anomaly monitor only**. It reports `UNKNOWN_UNVALIDATED` for occupancy and displays anomaly diagnostics without translating them into PRESENT/ABSENT. It also enforces the strict tone/source/CSI/RX-idle gates and refuses to overwrite an existing baseline unless `--replace-baseline` is explicitly supplied. The saved baseline is not changed by this release.

## Clone and build

```bash
git clone https://github.com/Dishant402955/iot-project.git
cd iot-project
./tools/setup_devourer_env.sh
./tools/build_devourer_pcie.sh
```

The isolated Devourer setup downloads build dependencies under `vendor/.local-deps` and creates `vendor/.venv`. Hardware capture is a separate deliberate physical-console action.

## Evidence and reports

- [Final project report](docs/FINAL_PROJECT_REPORT.md): research question, acquisition method, results, limitations, and final conclusion.
- [Frozen benchmark model](docs/BASELINE_MODEL_FREEZE.md): fixed Session 1/2 centroid model and held-out evaluation protocol.
- [Development analysis](docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.md): Sessions 1 and 2 only, with grouped and cross-session evaluation.
- [Live detector status](docs/LIVE_DETECTOR_STATUS.md): acquisition evidence, detector semantics, and next milestones.
- [Project execution plan](docs/PROJECT_EXECUTION_PLAN.md): authoritative milestones and integrity constraints.
- [Physical capture runbook](docs/presence-sensing-runbook.md): hardware collection procedure.
- [Cross-chat handoff](docs/HANDOFF.md): exact project state and responsibilities.
- [L-LTF alignment correction](docs/LTF_ALIGNMENT_RECOVERY_20261122.md).
- [Live acquisition qualification](docs/LIVE_ACQUISITION_QUALIFICATION_20261122.md).
- [CSI drift investigation](docs/CSI_DRIFT_INVESTIGATION_20261122.md).

Anonymized feature datasets for Sessions 1, 2 and 3 are published under `data/public_dataset/`. Original labelled JSONL and raw IQ archives remain local-only and need a private encrypted off-device backup. Never publish them.

## Hardware and acquisition

- Ubuntu 22.04, RTL8821CE PCIe adapter (`10ec:c821`), driver `rtw_8821ce`, interface commonly `wlp1s0`.
- 1T1R, 20 MHz, 20 Msps, 8192 complex samples per capture, legacy L-LTF with 52 active tones.
- Dedicated Galaxy M14 hotspot used in the experiment: 5 GHz, channel 149.
- Capture temporarily detaches the Wi-Fi adapter through VFIO. **Run physical capture only from the laptop's physical console**, never through SSH or a remote coding agent.
- CCA is the early-frame trigger. The `t<us>` setting controls the MAC LA trigger-time register, not IQ sample count or buffer duration.
- AP attribution is a post-arm RX-callback heuristic, not hardware source-MAC filtering or proof of exact packet-to-IQ correspondence.

Strict CSI gates: exactly 52 finite active tones; repeated L-LTF correlation >= 0.85; STF16 correlation <= 0.50; L-LTF symbol relative error <= 0.25; target-source audit match; RX-idle barrier. Do not lower them. Insufficient CSI is never ABSENT.

## Remaining physical data collection

Collect two additional independent development sessions (Sessions 4 and 5), preferably on separate days/time blocks, using the same frozen physical setup:

```bash
cd ~/projects/iot-project
sudo vendor/.venv/bin/python tools/collect_presence_interleaved.py
```

Each run performs five paired rounds (10 batches, 500 attempts), alternating ABSENT/PRESENT order, with 30-second settling per batch. Keep the laptop, AP, room layout, hotspot settings, and person position/orientation fixed. Preserve the labelled JSONL and matching raw archive.

After Sessions 4 and 5, analyze Sessions 1, 2, 4 and 5 only:

```bash
vendor/.venv/bin/python tools/analyze_presence_development.py \
  --session data/presence_dataset/interleaved_20261122_180724.jsonl \
  --session data/presence_dataset/interleaved_20261122_183204.jsonl \
  --session data/presence_dataset/interleaved_SESSION4.jsonl \
  --session data/presence_dataset/interleaved_SESSION5.jsonl
```

The analysis tool rejects the reserved Session 3 by its SHA-256 even if the file is renamed. Session 3 must remain untouched until a complete detector is frozen. If independent-session validation still fails, the scientifically correct outcome is that this hardware/setup did not demonstrate reliable stationary-presence detection.

## Reproducible checks

```bash
vendor/.venv/bin/python -m unittest discover -s tests -v
vendor/.venv/bin/python tools/analyze_presence_development.py
vendor/.venv/bin/python vendor/devourer/tools/la_csi.py --selftest
vendor/.venv/bin/python vendor/devourer/tests/la_csi_series_selftest.py
python3 -m compileall -q tools vendor/devourer/tools tests
bash -n tools/rtl8821ce_pcie_la_capture.sh
git diff --check
```

## Scope and limitations

This is an academic experimental system, not a safety/security alarm or production occupancy product. The adapter is 1T1R and acquisition rate is limited by roughly 130 ms readback time per 8192-sample buffer. It is not an exact reproduction of RF-DS or other multi-antenna, wideband, high-rate CSI systems. A negative/inconclusive experimental result is acceptable; unsupported accuracy claims are not.
