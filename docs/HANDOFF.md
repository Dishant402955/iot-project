# Project handoff: Wi-Fi stationary human-presence sensing

**Updated:** 2026-11-22
**Repository:** `Dishant402955/iot-project`
**Branch:** main
**Goal:** research an experimental stationary-room occupancy detector using RTL8821CE CSI. Intended states are PRESENT, ABSENT, and UNKNOWN / INSUFFICIENT_CSI when evidence or capture quality is inadequate.

## Current verdict

**CSI acquisition works for the tested configuration; a reliable occupancy detector has not been demonstrated.** Do not deploy or claim presence-detection accuracy yet.

Five five-round interleaved physical sessions have now been collected. Sessions 1, 2, 4 and 5 are development data. Session 3 was reserved as held-out, excluded from development analysis/model selection, and evaluated exactly once after freezing the benchmark model. Anonymized public feature copies of Sessions 1-5 are published on GitHub and privacy-scanned. Original labelled JSONL and raw IQ are local-only.

The combined development analysis covers 2,000 attempts and 1,989 strict CSI profiles across Sessions 1, 2, 4 and 5; all 40 batches passed both acquisition gates. Eight model families were compared. The small MLP reached 0.850 grouped balanced accuracy and 0.800 pooled leave-one-session-out balanced accuracy and 0.60 sensitivity. Random Forest reached 0.80 / 0.65. Session-specific performance remains inconsistent, so no candidate is deployable.

## Latest completed work

- Fixed repeated-L-LTF pair alignment in vendor/devourer/tools/la_csi.py by testing candidate pair starts at matched-filter peak offsets -64, 0, +64. Strict quality gates were unchanged.
- Qualified live acquisition: 50/50 strict CSI, 50/50 RX-idle, 50/50 target-source heuristic; driver restored and baseline hash unchanged.
- Collected five five-round interleaved sessions (500 attempts each):
  - Session 1: 500/500 valid strict CSI.
  - Session 2: 499/500 valid strict CSI.
  - Session 3: 497/500 valid strict CSI; reserved held-out and evaluated once.
  - Session 4: 498/500 valid strict CSI (248 ABSENT, 250 PRESENT); all 10 batches passed both acquisition gates; RX-idle 500/500.
  - Session 5: 498/500 strict structural CSI; 492/500 target-attributed strict CSI retained (246 ABSENT, 246 PRESENT); 494/500 target-source matches; RX-idle 500/500; all 10 batches passed both acquisition gates.
- Published anonymized feature copies:
  - data/public_dataset/interleaved_session_1_anonymized.jsonl
  - data/public_dataset/interleaved_session_2_anonymized.jsonl
  - data/public_dataset/interleaved_session_3_anonymized.jsonl
  - data/public_dataset/interleaved_session_4_anonymized.jsonl
  - data/public_dataset/interleaved_session_5_anonymized.jsonl
  - data/public_dataset/README.md
- Extended tools/analyze_presence_development.py to enforce exact allowlisted source paths and real acquisition session IDs (1, 2, 4, 5). Added tools/compare_presence_models.py and a pinned scikit-learn analysis dependency. Combined grouped and leave-one-session-out analysis is complete; consumed Session 3 was not accessed.

## Latest development analysis

Reports: `docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.md` and `docs/PRESENCE_MODEL_COMPARISON_20261122.md`, with matching JSON outputs. Forty batch examples from Sessions 1, 2, 4 and 5 were evaluated using 20 paired-round folds and four leave-one-session-out folds. The best grouped result was tied by the small MLP and Random Forest (0.850 balanced accuracy); the MLP reached 0.800 pooled leave-one-session-out balanced accuracy and 0.60 sensitivity. Random Forest reached 0.80 and 0.65 respectively. No candidate is deployable.

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
2. Perform physical-console live empty/occupied/entry/exit/poor-CSI tests, driver restoration and Ctrl+C cleanup checks. These are hardware integration checks, not validation of an occupancy classifier.

### Assistant/offline work

- Combined grouped/session-transfer analysis and model comparison on Sessions 1, 2, 4 and 5 are complete. Session 3 is permanently excluded from further development. Session reports: `docs/SESSION4_ACQUISITION_ANALYSIS_20261122.md` and `docs/SESSION5_ACQUISITION_ANALYSIS_20261122.md`.
- No model passed the current generalization bar; do not deploy or freeze a new occupancy model.
- A revised detector requires additional development sessions and a new untouched held-out session. Session 3 is consumed and must never be reused.
- Live occupancy inference remains deliberately disabled; only diagnostic anomaly output is available.

## Data integrity and backup caveat

- Empty-room baseline: data/live_presence_baseline.json; SHA-256 2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74. Never overwrite without explicit approval.
- Original labelled session JSONL and raw IQ archives are ignored by Git and remain local-only.
- Public anonymized datasets are backed up on GitHub. Raw IQ archive directory existence was previously confirmed, but contents and off-device backup have not been fully verified because root-owned directories were inaccessible to the unprivileged remote agent.
- .gitignore protects /data/presence_dataset/ and /data/presence_dataset_raw/.
- No destructive Git operations, cleanup, reset, or force-push.

## Key files

- tools/collect_presence_interleaved.py — physical five-round collector.
- tools/reprocess_presence_archives.py — offline corrected CSI extraction/reprocessing.
- tools/analyze_presence_development.py — grouped development analysis with exact allowlist for Sessions 1, 2, 4 and 5.
- tools/compare_presence_models.py — classical ML and small MLP comparison with grouped and leave-one-session-out evaluation.
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

- Python unit suite: 42 tests passed, including the new allowlist and model-fold tests.
- L-LTF extractor self-test: passed, including noise rejection and repeated-symbol alignment regression.
- CSI-series self-test: passed.
- Python compileall: passed.
- Capture shell syntax check: passed.
- Existing C++ test executable `build/wifi_tests`: passed.
- A fresh CMake rebuild/CTest invocation could not run in the remote workspace: the `cmake` command is absent from PATH, and the repository-bundled CMake binary cannot load `libjsoncpp.so.25`. The existing C++ test binary was run separately and passed; this is not a fresh build verification.
- `git diff --check`: passed.
- Privacy scan of the published anonymized feature datasets and new session analysis reports: passed (no BSSID, `/home/user/`, raw capture paths, or exact UTC timestamp fields).


## Additional hardening completed (2026-11-22)

- The live script was changed from an unvalidated PRESENT/ABSENT anomaly heuristic to a diagnostic-only monitor. It always reports `UNKNOWN_UNVALIDATED` for occupancy and reports `ANOMALY` / `NO_ANOMALY` separately. There is no longer an occupancy state smoother in the live path.
- Live CSI admission now requires the exact 52 active-tone set, `csi_structurally_valid=true`, `target_source_match=true`, and `rx_idle_satisfied=true`, in addition to the L-LTF correlation checks. Missing audit fields fail closed.
- Existing baseline overwrite is refused by default. `--replace-baseline` is an explicit override; do not use it without approval and a verified backup. The existing baseline was not changed.
- Development analysis now defaults to all four development sessions and enforces exact source-path and SHA-256 allowlists before loading data. The consumed Session 3 path is rejected before file access.
- README and physical runbook now describe Sessions 1/2/4/5 as development, and Session 3 as evaluated once with a frozen benchmark. Historical smoke-test docs are labelled as superseded.


## Final report and latest verification

- Added `docs/FINAL_PROJECT_REPORT.md` covering the research question, hardware/method, collected sessions, development metrics, limitations, safety hardening, reproducibility, and the negative detector conclusion.
- Current software test suite after the model comparison: 42 Python tests passed; L-LTF self-test, CSI-series self-test, Python compilation, shell syntax, and existing C++ test executable passed.
- Empty-room baseline SHA-256 remains `2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74`.
- No physical capture was run during this software-only pass. Sessions 1-5 were collected in prior physical-console runs. Private raw-data backup and live hardware transition checks remain user-console dependencies.


## Frozen baseline benchmark (2026-11-22)

- Froze `profile_median_nearest_centroid_sessions_1_2_v1` using exactly 20 batch medians (10 ABSENT, 10 PRESENT) from Sessions 1 and 2.
- Model artifact: `models/presence_centroid_baseline_s1_s2_v1.json`; SHA-256 `43560a6e2c5f9ca67c81c07e732fb990fd1fff49c792565df04ea448a2a25b02`.
- Freeze script verifies exact source hashes for Sessions 1 and 2 and refuses alternate training inputs. Session 3 was not used.
- Model is explicitly `NOT_VALIDATED_NOT_FOR_OCCUPANCY_DECISIONS`. It was frozen only as a benchmark for a one-time independent Session 3 evaluation.
- Freeze specification: `docs/BASELINE_MODEL_FREEZE.md`. The one-time evaluator `tools/evaluate_presence_heldout.py` completed its single Session 3 evaluation and refuses to overwrite the existing result. Never rerun it.


## One-time held-out evaluation completed (2026-11-22)

- Evaluated frozen model `profile_median_nearest_centroid_sessions_1_2_v1` exactly once on Session 3 after verifying both immutable source/model hashes.
- Results: TP=3, TN=4, FP=1, FN=2; accuracy 0.70, sensitivity 0.60, specificity 0.80, balanced accuracy 0.70, precision 0.75, F1 0.667.
- CSI availability: 497/500 (99.4%); acquisition gates passed 10/10 batches; zero insufficient-CSI batches.
- It missed 2/5 PRESENT batches and falsely marked 1/5 ABSENT batches PRESENT. This is not reliable occupancy detection. Do not tune on Session 3 or rerun the evaluator.
- Reports: `docs/HELD_OUT_EVALUATION_SESSION3_20261122.md` and `.json`. The evaluator refuses to overwrite existing outputs.
- Any revised model requires new development data and a new untouched held-out session.


## Final software pass: combined development analysis and model comparison (2026-11-22)

### Results

- Combined development sources: Sessions 1, 2, 4 and 5 only; 2,000 attempts, 1,989 strict profiles, 40 batch examples, 20 paired session-round groups, 40/40 batches passing acquisition gates.
- Nearest-centroid grouped validation: 0.80 balanced accuracy, 0.65 sensitivity, 0.95 specificity.
- Model comparison: small MLP 0.850 grouped / 0.800 leave-one-session-out balanced accuracy (sensitivity 0.60); Random Forest 0.850 / 0.800 (sensitivity 0.65); other candidates and per-session metrics are in `docs/PRESENCE_MODEL_COMPARISON_20261122.md`.
- No candidate generalizes reliably. The MLP and tree models are exploratory only. No occupancy classifier is selected or deployed. Live detector remains `UNKNOWN_UNVALIDATED` for occupancy.
- Corrected analysis session identity mapping: actual Session 4 is no longer mislabeled as the third supplied session. Both analysis tools enforce an exact allowlist before opening source data. Session 3 was not accessed.

### Software changes

- `tools/analyze_presence_development.py`: exact path allowlist, actual session IDs, combined source hashes and updated analysis output.
- `tools/compare_presence_models.py`: fixed-configuration nearest centroid, logistic regression, linear/RBF SVM, Random Forest, ExtraTrees, Gradient Boosting and small MLP comparison.
- `tools/requirements-presence-analysis.txt`: pinned scikit-learn analysis dependency.
- Added tests for allowlist protection and paired/session fold integrity.
- Updated README, project plan, live status, final report and this handoff.

### Owner-side blockers

1. Inspect root-owned raw IQ archives and create/verify encrypted off-device backup of private raw data and labelled JSONL. This remote session did not use sudo, read private IQ contents, or claim backup completion.
2. Run physical-console empty/occupied/entry/exit/poor-CSI and driver-restoration/Ctrl+C checks. No physical capture was performed remotely.
3. If research continues, collect more independent development data and a new untouched held-out session. The existing Session 3 is permanently consumed.
