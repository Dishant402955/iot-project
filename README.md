# Wi-Fi Stationary Human-Presence Sensing

Academic research prototype investigating whether a Realtek RTL8821CE 1T1R adapter can distinguish a stationary person from an empty room using Wi-Fi CSI. The intended product states are `PRESENT`, `ABSENT`, and `UNKNOWN` / `INSUFFICIENT_CSI` when acquisition or evidence is inadequate.

## Current verdict (2026-11-22)

**The acquisition pipeline is qualified for the tested setup, but the collected development data does not establish reliable stationary-presence detection.** Do not report a working detector or accuracy claim.

Five interleaved sessions have been collected. Sessions 1, 2, 4 and 5 are development data. Session 3 was kept out of model selection and evaluated exactly once after freezing the benchmark model. The four development sessions contain: 2,000 attempts, 1,989 retained strict CSI profiles and 40/40 batches passing acquisition gates. Grouped nearest-centroid balanced accuracy is 0.80 (sensitivity 0.65). Eight lightweight models were compared: a small MLP reached 0.850 grouped balanced accuracy, and 0.800 pooled leave-one-session-out balanced accuracy (sensitivity 0.60); Random Forest reached 0.80 / 0.65. Per-session performance varies substantially. No model is selected for deployment.

The frozen nearest-centroid benchmark was evaluated once on Session 3: accuracy 0.70, sensitivity 0.60, specificity 0.80, and balanced accuracy 0.70 (TP=3, TN=4, FP=1, FN=2). It missed two of five occupied batches. This is not sufficient for reliable occupancy detection or deployment. The live tool `tools/live_presence_detector.py` remains a **channel-anomaly monitor only**. It reports `UNKNOWN_UNVALIDATED` for occupancy and displays anomaly diagnostics without translating them into PRESENT/ABSENT. It also enforces the strict tone/source/CSI/RX-idle gates and refuses to overwrite an existing baseline unless `--replace-baseline` is explicitly supplied. The saved baseline is not changed by this release.

## Clone and build

```bash
git clone https://github.com/Dishant402955/iot-project.git
cd iot-project
./tools/setup_devourer_env.sh
./tools/build_devourer_pcie.sh
```

The isolated Devourer setup downloads build dependencies under `vendor/.local-deps` and creates `vendor/.venv`. For model comparison, install the pinned analysis dependency with `uv pip install --python vendor/.venv/bin/python -r tools/requirements-presence-analysis.txt`. Hardware capture is a separate deliberate physical-console action.

## Evidence and reports

- [Final project report](docs/FINAL_PROJECT_REPORT.md): research question, acquisition method, results, limitations, and final conclusion.
- [Frozen benchmark model](docs/BASELINE_MODEL_FREEZE.md): fixed Session 1/2 centroid model and held-out evaluation protocol.
- [One-time held-out result](docs/HELD_OUT_EVALUATION_SESSION3_20261122.md): Session 3 metrics and per-batch predictions.
- [Combined development analysis](docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.md): Sessions 1, 2, 4 and 5 with grouped and leave-one-session-out evaluation.
- [Model comparison](docs/PRESENCE_MODEL_COMPARISON_20261122.md): nearest centroid, logistic regression, SVMs, tree ensembles and small MLP.
- [Live detector status](docs/LIVE_DETECTOR_STATUS.md): acquisition evidence, detector semantics, and next milestones.
- [Project execution plan](docs/PROJECT_EXECUTION_PLAN.md): authoritative milestones and integrity constraints.
- [Physical capture runbook](docs/presence-sensing-runbook.md): hardware collection procedure.
- [Cross-chat handoff](docs/HANDOFF.md): exact project state and responsibilities.
- [L-LTF alignment correction](docs/LTF_ALIGNMENT_RECOVERY_20261122.md).
- [Live acquisition qualification](docs/LIVE_ACQUISITION_QUALIFICATION_20261122.md).
- [CSI drift investigation](docs/CSI_DRIFT_INVESTIGATION_20261122.md).

Anonymized feature datasets for Sessions 1, 2, 3, 4 and 5 are published under `data/public_dataset/`. Original labelled JSONL and raw IQ archives remain local-only and need a private encrypted off-device backup. Never publish them.

## Hardware and acquisition

- Ubuntu 22.04, RTL8821CE PCIe adapter (`10ec:c821`), driver `rtw_8821ce`, interface commonly `wlp1s0`.
- 1T1R, 20 MHz, 20 Msps, 8192 complex samples per capture, legacy L-LTF with 52 active tones.
- Dedicated Galaxy M14 hotspot used in the experiment: 5 GHz, channel 149.
- Capture temporarily detaches the Wi-Fi adapter through VFIO. **Run physical capture only from the laptop's physical console**, never through SSH or a remote coding agent.
- CCA is the early-frame trigger. The `t<us>` setting controls the MAC LA trigger-time register, not IQ sample count or buffer duration.
- AP attribution is a post-arm RX-callback heuristic, not hardware source-MAC filtering or proof of exact packet-to-IQ correspondence.

Strict CSI gates: exactly 52 finite active tones; repeated L-LTF correlation >= 0.85; STF16 correlation <= 0.50; L-LTF symbol relative error <= 0.25; target-source audit match; RX-idle barrier. Do not lower them. Insufficient CSI is never ABSENT.

## Development data collected

Session 5 is now collected and anonymized. It contains 500 attempts, 498 strict structural CSI profiles, 492 target-attributed strict CSI profiles retained (246 ABSENT and 246 PRESENT), 500/500 RX-idle checks, and 10/10 batches passing both acquisition gates. Its aggregate descriptive median-profile distance is 0.2137 dB RMS. See `docs/SESSION5_ACQUISITION_ANALYSIS_20261122.md`. This distance is not a detector-accuracy metric.

The completed combined analysis uses Sessions 1, 2, 4 and 5 only:

```bash
vendor/.venv/bin/python tools/analyze_presence_development.py
```

Both analysis tools enforce an exact allowlist of the four development source paths before opening files. The consumed Session 3 is not read or used. It must never be used for further tuning. Any revised model requires additional independent development sessions and a new untouched held-out session.

## Reproducible checks

```bash
vendor/.venv/bin/python -m unittest discover -s tests -v
vendor/.venv/bin/python tools/analyze_presence_development.py
vendor/.venv/bin/python tools/compare_presence_models.py
vendor/.venv/bin/python vendor/devourer/tools/la_csi.py --selftest
vendor/.venv/bin/python vendor/devourer/tests/la_csi_series_selftest.py
python3 -m compileall -q tools vendor/devourer/tools tests
bash -n tools/rtl8821ce_pcie_la_capture.sh
git diff --check
```

## Scope and limitations

This is an academic experimental system, not a safety/security alarm or production occupancy product. The adapter is 1T1R and acquisition rate is limited by roughly 130 ms readback time per 8192-sample buffer. It is not an exact reproduction of RF-DS or other multi-antenna, wideband, high-rate CSI systems. A negative/inconclusive experimental result is acceptable; unsupported accuracy claims are not.
