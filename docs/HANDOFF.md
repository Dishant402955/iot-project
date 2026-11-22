# Project handoff: Wi-Fi stationary human-presence sensing

**Updated:** 2026-11-22
**Repository:** /home/user/projects/iot-project
**Branch:** main
**Goal:** research an experimental stationary-room occupancy detector using RTL8821CE CSI. Intended states are PRESENT, ABSENT, and UNKNOWN / INSUFFICIENT_CSI when evidence or capture quality is inadequate.

## Current verdict

**CSI acquisition works for the tested configuration; a reliable occupancy detector has not been demonstrated.** Do not deploy or claim presence-detection accuracy yet.

Three five-round interleaved physical sessions were collected. Sessions 1 and 2 are development data. Session 3 was reserved as held-out, was excluded from development analysis/model selection, and was evaluated exactly once after freezing the benchmark model. Anonymized public feature copies of all three sessions and their README are published on GitHub. Original labelled JSONL and raw IQ are local-only.

The development analysis found 999 valid strict CSI profiles from 1,000 attempts across Sessions 1 and 2. All 20 batches passed both acquisition gates. A batch-median nearest-centroid grouped evaluation produced 0.80 balanced accuracy but only 0.60 sensitivity. More importantly, cross-session transfer in both directions produced 0.50 balanced accuracy and 0.00 sensitivity, predicting every batch as ABSENT. This is a failure to establish robust session-independent occupancy information, not a usable detector.

## Latest completed work

- Fixed repeated-L-LTF pair alignment in vendor/devourer/tools/la_csi.py by testing candidate pair starts at matched-filter peak offsets -64, 0, +64. Strict quality gates were unchanged.
- Qualified live acquisition: 50/50 strict CSI, 50/50 RX-idle, 50/50 target-source heuristic; driver restored and baseline hash unchanged.
- Collected three five-round interleaved sessions (500 attempts each):
  - Session 1: 500/500 valid strict CSI; source data/presence_dataset/interleaved_20261122_180724.jsonl.
  - Session 2: 499/500 valid strict CSI; source data/presence_dataset/interleaved_20261122_183204.jsonl.
  - Session 3: 497/500 valid strict CSI; source data/presence_dataset/interleaved_20261122_185040.jsonl; reserved held-out.
- Published anonymized feature copies:
  - data/public_dataset/interleaved_session_1_anonymized.jsonl
  - data/public_dataset/interleaved_session_2_anonymized.jsonl
  - data/public_dataset/interleaved_session_3_anonymized.jsonl
  - data/public_dataset/README.md
- Added tools/analyze_presence_development.py, pinned to Sessions 1 and 2, plus unit tests and development analysis report. It accepts explicit development sessions but rejects Session 3 by SHA-256 to protect it from tuning.

## Latest development analysis

Report: docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.md
Machine-readable output: docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.json

| Evaluation | Accuracy | Sensitivity | Specificity | Balanced accuracy |
|---|---:|---:|---:|---:|
| Leave one session-round pair out | 0.80 | 0.60 | 1.00 | 0.80 |
| Train S1 / test S2 | 0.50 | 0.00 | 1.00 | 0.50 |
| Train S2 / test S1 | 0.50 | 0.00 | 1.00 | 0.50 |

Do not deploy a classifier from this result. The cross-session test is the key failure. Session 3 was subsequently evaluated once with a frozen baseline benchmark, without tuning.

## Hardware and capture constraints

- Ubuntu 22.04.5, RTL8821CE PCI 10ec:c821, BDF 0000:01:00.0, driver rtw_8821ce, interface wlp1s0.
- 1T1R, 20 MHz, 20 Msps, 8192 complex samples, 52 active tones.
- Qualified AP: Galaxy M14 hotspot, 5 GHz channel 149. Keep this exact setup for future physical sessions; another Wi-Fi connection is fine for offline software work only.
- CCA is the early-frame trigger. t<us> sets Realtek's MAC LA trigger-time register, not sample count or IQ-buffer duration.
- Capture temporarily detaches the Wi-Fi adapter using VFIO and interrupts connectivity. **Only the user may run physical capture from the laptop console. Never run capture remotely or over SSH.**
- AP attribution is heuristic, not hardware source-MAC filtering.

Strict CSI gates remain: exactly 52 finite tones; repeated L-LTF correlation >=0.85; STF16 correlation <=0.50; L-LTF symbol relative error <=0.25; target-source audit match; RX-idle barrier. Do not relax.

## What remains and who does it

### User actions

1. Verify raw IQ archive contents and create an encrypted private/off-device backup of the original labelled JSONL and raw IQ. Public GitHub contains only anonymized feature datasets; do not publish raw IQ or private labelled sources.
2. Collect at least two more independent development sessions (Sessions 4 and 5), ideally on separate days/time blocks, using the same physical setup and collector. Run only at the laptop console:

   ```bash
   cd ~/projects/iot-project
   sudo vendor/.venv/bin/python tools/collect_presence_interleaved.py
   ```

3. After a detector is justified, perform live physical entry/exit/empty/occupied/poor-CSI tests at the laptop console.

### Assistant/offline work

- Extend development analysis to Sessions 1, 2, 4 and 5 only.
- Select features/model only if cross-session validation supports it.
- Implement confidence, abstention, temporal logic and strict quality handling.
- Freeze source, features, preprocessing, model and thresholds before any held-out evaluation. Session 3 has now been evaluated once; any revised model needs a new held-out session.
- Produce held-out report, live integration, tests and final documentation if the evidence supports proceeding.

## Data integrity and backup caveat

- Empty-room baseline: data/live_presence_baseline.json; SHA-256 2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74. Never overwrite without explicit approval.
- Original labelled session JSONL and raw IQ archives are ignored by Git and remain local-only.
- Public anonymized datasets are backed up on GitHub. Raw IQ archive directory existence was previously confirmed, but contents and off-device backup have not been fully verified because root-owned directories were inaccessible to the unprivileged remote agent.
- .gitignore protects /data/presence_dataset/ and /data/presence_dataset_raw/.
- No destructive Git operations, cleanup, reset, or force-push.

## Key files

- tools/collect_presence_interleaved.py — physical five-round collector.
- tools/reprocess_presence_archives.py — offline corrected CSI extraction/reprocessing.
- tools/analyze_presence_development.py — development-only grouped analysis pinned to Sessions 1 and 2.
- tools/live_presence_detector.py — experimental baseline-relative channel-anomaly indicator, not a validated occupancy classifier.
- tools/analyze_presence_run.py — strict capture/source audit.
- vendor/devourer/tools/la_csi.py — strict L-LTF CSI extraction.
- data/live_presence_baseline.json — local empty-room baseline; do not overwrite.
- docs/PROJECT_EXECUTION_PLAN.md — authoritative remaining milestones.
- docs/presence-sensing-runbook.md — physical capture protocol.

## Reproducibility checks

```bash
vendor/.venv/bin/python tools/analyze_presence_development.py
vendor/.venv/bin/python -m unittest tests.test_presence_development_analysis -v
vendor/.venv/bin/python -m unittest discover -s tests -v
vendor/.venv/bin/python vendor/devourer/tools/la_csi.py --selftest
vendor/.venv/bin/python vendor/devourer/tests/la_csi_series_selftest.py
python3 -m compileall -q tools vendor/devourer/tools tests
cmake --build build -j2
ctest --test-dir build --output-on-failure
bash -n tools/rtl8821ce_pcie_la_capture.sh
```

## Latest software validation (2026-11-22)

- Python unit suite: 31 tests passed.
- L-LTF extractor self-test: passed, including noise rejection and repeated-symbol alignment regression.
- CSI-series self-test: passed.
- Python compileall: passed.
- Capture shell syntax check: passed.
- Existing C++ test executable `build/wifi_tests`: passed.
- A fresh CMake rebuild/CTest invocation could not run in the remote workspace: the `cmake` command is absent from PATH, and the repository-bundled CMake binary cannot load `libjsoncpp.so.25`. The existing C++ test binary was run separately and passed; this is not a fresh build verification.
- `git diff --check`: passed.
- Privacy scan of the new analysis report: passed (no BSSID, `/home/user/`, raw capture paths, or UTC timestamp fields).


## Additional hardening completed (2026-11-22)

- The live script was changed from an unvalidated PRESENT/ABSENT anomaly heuristic to a diagnostic-only monitor. It always reports `UNKNOWN_UNVALIDATED` for occupancy and reports `ANOMALY` / `NO_ANOMALY` separately. There is no longer an occupancy state smoother in the live path.
- Live CSI admission now requires the exact 52 active-tone set, `csi_structurally_valid=true`, `target_source_match=true`, and `rx_idle_satisfied=true`, in addition to the L-LTF correlation checks. Missing audit fields fail closed.
- Existing baseline overwrite is refused by default. `--replace-baseline` is an explicit override; do not use it without approval and a verified backup. The existing baseline was not changed.
- Development analysis now accepts repeated `--session` arguments, supports future Sessions 4 and 5, and rejects reserved Session 3 using its exact source SHA-256 even if renamed. It requires at least two sessions inside the repository.
- README and physical runbook now describe Sessions 1/2 as development, Session 3 as evaluated once with a frozen benchmark, and Sessions 4/5 as next development collection. Historical smoke-test docs are labelled as superseded.


## Final report and latest verification

- Added `docs/FINAL_PROJECT_REPORT.md` covering the research question, hardware/method, three sessions, development metrics, limitations, safety hardening, reproducibility, and the negative detector conclusion.
- Current offline test suite before the held-out evaluation: 37 Python tests passed; L-LTF self-test, CSI-series self-test, Python compilation, shell syntax, and existing C++ test executable passed.
- Empty-room baseline SHA-256 remains `2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74`.
- No physical capture was run during this software-only pass. Sessions 4 and 5, private raw-data backup, and live hardware transition checks remain user-console dependencies.


## Frozen baseline benchmark (2026-11-22)

- Froze `profile_median_nearest_centroid_sessions_1_2_v1` using exactly 20 batch medians (10 ABSENT, 10 PRESENT) from Sessions 1 and 2.
- Model artifact: `models/presence_centroid_baseline_s1_s2_v1.json`; SHA-256 `43560a6e2c5f9ca67c81c07e732fb990fd1fff49c792565df04ea448a2a25b02`.
- Freeze script verifies exact source hashes for Sessions 1 and 2 and refuses alternate training inputs. Session 3 was not used.
- Model is explicitly `NOT_VALIDATED_NOT_FOR_OCCUPANCY_DECISIONS`. It was frozen only as a benchmark for a one-time independent Session 3 evaluation.
- Freeze specification: `docs/BASELINE_MODEL_FREEZE.md`. The one-time evaluator `tools/evaluate_presence_heldout.py` is implemented with a strict source/model hash check and refuses to overwrite existing results. It is being committed separately before execution.


## One-time held-out evaluation completed (2026-11-22)

- Evaluated frozen model `profile_median_nearest_centroid_sessions_1_2_v1` exactly once on Session 3 after verifying both immutable source/model hashes.
- Results: TP=3, TN=4, FP=1, FN=2; accuracy 0.70, sensitivity 0.60, specificity 0.80, balanced accuracy 0.70, precision 0.75, F1 0.667.
- CSI availability: 497/500 (99.4%); acquisition gates passed 10/10 batches; zero insufficient-CSI batches.
- It missed 2/5 PRESENT batches and falsely marked 1/5 ABSENT batches PRESENT. This is not reliable occupancy detection. Do not tune on Session 3 or rerun the evaluator.
- Reports: `docs/HELD_OUT_EVALUATION_SESSION3_20261122.md` and `.json`. The evaluator refuses to overwrite existing outputs.
- Any revised model requires new development data and a new untouched held-out session.
