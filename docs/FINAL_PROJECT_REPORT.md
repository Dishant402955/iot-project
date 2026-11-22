# Wi-Fi CSI stationary-presence sensing: project report

**Report date:** 2026-11-22
**Repository:** `Dishant402955/iot-project`
**Project outcome:** Acquisition pipeline qualified for one fixed setup; reliable stationary-presence classification not demonstrated.

## 1. Abstract

This project investigated whether a Realtek RTL8821CE 1T1R Wi-Fi adapter could provide channel-state information (CSI) suitable for distinguishing a stationary person from an empty room. A PCIe/VFIO-based raw-IQ capture path, strict legacy L-LTF CSI extraction, acquisition-quality checks, an interleaved labelled collection protocol, offline analysis, and an anonymized feature-data release were implemented.

The tested acquisition setup produced high-yield strict CSI. However, grouped development analysis across two independent interleaved sessions showed poor cross-session transfer: the nearest-centroid diagnostic achieved 0.50 balanced accuracy and 0.00 sensitivity in both transfer directions. The system therefore does not demonstrate a reliable occupancy signal. The live utility has been hardened to report channel anomalies only and always return `UNKNOWN_UNVALIDATED` for occupancy. The reserved third session has not been used for tuning or evaluation.

## 2. Research question and scope

**Question:** Under a fixed room, AP, channel, adapter, and subject-position setup, can 52-tone CSI profiles distinguish one stationary person in the room from an empty room across independent collection sessions?

This is a constrained academic experiment. It does not establish generalization across rooms, people, APs, devices, channels, or furniture layouts. It is not a safety/security alarm, intrusion detector, or production occupancy product. The adapter is 1T1R and cannot support claims about reliable multi-person counting.

## 3. Hardware and acquisition method

- Host: Ubuntu 22.04.5 LTS, x86_64.
- Adapter: Realtek RTL8821CE, PCI `10ec:c821`, 1T1R, driver `rtw_8821ce`.
- Capture: PCIe/VFIO logic-analyzer path, 20 MHz, 20 Msps, 8192 complex samples, legacy L-LTF.
- AP: dedicated Galaxy M14 hotspot, 5 GHz channel 149.
- CSI: exactly 52 active tones.
- Trigger: CCA early-frame trigger. Realtek `t<us>` sets the MAC LA trigger-time register, not sample count or IQ-buffer duration.

The strict CSI gates were kept fixed:

1. Exactly 52 finite active tones.
2. Repeated L-LTF correlation >= 0.85.
3. STF16 correlation <= 0.50.
4. L-LTF symbol relative error <= 0.25.
5. Target-source audit match.
6. RX-idle barrier.

The target AP attribution is a post-arm RX callback/address-audit heuristic. It is not hardware source-MAC filtering and does not prove an exact packet-to-IQ-buffer join. Physical capture temporarily detaches the adapter through VFIO and must only be run from the laptop's physical console.

## 4. Acquisition engineering outcome

A matched-filter alignment issue was found: the extractor could choose the second of the repeated 64-sample L-LTF symbols as the pair start and compare it against SIGNAL. The fix tests candidate pair starts at offsets -64, 0, and +64 from the detected peak, including fallback candidates. Strict CSI gates were not relaxed. Regression tests include a stronger second-symbol peak and noise rejection.

A fresh live qualification achieved:

- Strict CSI: 50/50.
- RX-idle barrier: 50/50.
- Post-arm target AP source heuristic: 50/50.
- All accepted profiles: 52 finite active tones.
- Kernel driver restored to `rtw_8821ce`.
- Empty-room baseline SHA-256 unchanged: `2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74`.

These results qualify acquisition for the tested setup; they do not establish occupancy detection.

## 5. Interleaved datasets

Each session used five rounds, ten batches, and 50 attempts per batch (500 attempts total). Condition order alternated between ABSENT/PRESENT and PRESENT/ABSENT. Each condition had 30 seconds settling. Room geometry, device positions, AP/channel, and subject position/orientation were held fixed.

| Session | Role | Attempts | Valid strict CSI | Acquisition gates |
|---|---|---:|---:|---:|
| 1 | Development | 500 | 500 | 10/10 batches pass |
| 2 | Development | 500 | 499 | 10/10 batches pass |
| 3 | Reserved held-out | 500 | 497 | 10/10 batches pass |

Sessions 1 and 2 are the only data used by the current development analysis. Session 3 remains reserved and must not be opened for feature selection, threshold tuning, or model selection. Its source SHA-256 is `9c2bfa791fbb67c511330aef9207dad74be32e388056930cd17522310ee1af57`.

Anonymized feature copies of all three sessions and a dataset README are published under `data/public_dataset/`. They omit BSSID, exact wall-clock timestamps, and local filesystem paths. Raw IQ and original labelled JSONL are excluded from the public repository and still require private encrypted off-device backup.

## 6. Development analysis

Sessions 1 and 2 provide 1,000 attempts and 999 valid profiles (500 ABSENT, 499 PRESENT). All 20 batches passed both acquisition gates and had 100% RX-idle.

The reproducible batch-level diagnostic:

1. Takes the per-tone median profile for each batch.
2. Standardizes using training batches only.
3. Fits two class centroids.
4. Holds out both conditions from one session-round together.
5. Separately evaluates transfer between sessions.

### 6.1 Grouped leave-one-session-round-pair-out

| TP | TN | FP | FN | Accuracy | Sensitivity | Specificity | Balanced accuracy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | 10 | 0 | 4 | 0.80 | 0.60 | 1.00 | 0.80 |

This result uses only ten paired rounds and has weak sensitivity. It is exploratory and not a performance claim.

### 6.2 Cross-session transfer

| Training | Test | TP | TN | FP | FN | Accuracy | Sensitivity | Specificity | Balanced accuracy |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Session 1 | Session 2 | 0 | 5 | 0 | 5 | 0.50 | 0.00 | 1.00 | 0.50 |
| Session 2 | Session 1 | 0 | 5 | 0 | 5 | 0.50 | 0.00 | 1.00 | 0.50 |

Both transfer tests predicted every test batch as ABSENT. This is a decisive failure of this simple profile-centroid approach to generalize between the two development sessions. It is consistent with session-dependent CSI structure and does not support a stable stationary-occupancy feature.

No ROC AUC or confidence interval is reported: the current diagnostic produces hard batch decisions and only ten paired rounds are available. Reporting a misleadingly precise statistic would add decoration, not evidence.

## 7. Frozen research benchmark

A fixed batch-median nearest-centroid benchmark was frozen using exactly 20 batch examples from Sessions 1 and 2 (ten per class). It uses the per-tone batch median, training-only standardization, and two class centroids with squared Euclidean distance. The frozen artifact is `models/presence_centroid_baseline_s1_s2_v1.json` (SHA-256 `43560a6e2c5f9ca67c81c07e732fb990fd1fff49c792565df04ea448a2a25b02`). Session 3 was not used. This model is frozen only to obtain one independent benchmark result; it is explicitly not a deployment candidate. The freeze protocol is documented in `docs/BASELINE_MODEL_FREEZE.md`. The one-time evaluator is `tools/evaluate_presence_heldout.py`; it verifies the model and Session 3 hashes and refuses to rerun if either evaluation output already exists.

## 8. Live tool safety hardening

Because channel anomalies and spectral drift are not occupancy-specific, `tools/live_presence_detector.py` is now a channel-anomaly monitor only:

- It always reports `UNKNOWN_UNVALIDATED` for occupancy.
- It reports `ANOMALY` / `NO_ANOMALY` separately as diagnostics.
- It does not convert anomaly thresholds or temporal smoothing into PRESENT/ABSENT.
- It requires the exact 52 active-tone set, structural CSI validity, target-source match, RX-idle, and L-LTF quality gates.
- Missing audit fields fail closed.
- It refuses to overwrite an existing baseline unless `--replace-baseline` is explicitly supplied.

The existing empty-room baseline was not modified. `INSUFFICIENT_CSI` remains distinct from ABSENT and must never be treated as evidence that the room is empty.

## 9. Reproducibility and tests

From the repository root:

```bash
vendor/.venv/bin/python tools/analyze_presence_development.py
vendor/.venv/bin/python tools/freeze_presence_baseline_model.py
vendor/.venv/bin/python -m unittest discover -s tests -v
vendor/.venv/bin/python vendor/devourer/tools/la_csi.py --selftest
vendor/.venv/bin/python vendor/devourer/tests/la_csi_series_selftest.py
python3 -m compileall -q tools vendor/devourer/tools tests
bash -n tools/rtl8821ce_pcie_la_capture.sh
git diff --check
```

Latest offline verification: 33 Python unit tests passed; L-LTF self-test passed; CSI-series self-test passed; Python compilation passed; capture shell syntax passed; existing C++ test executable passed; baseline hash unchanged. A fresh CMake rebuild/CTest could not be verified in the remote workspace because a working CMake installation was unavailable (the bundled binary could not load `libjsoncpp.so.25`).

## 10. Limitations and remaining physical work

1. Only two sessions are currently available for development analysis; Session 3 is reserved held-out.
2. Cross-session sensitivity is zero in both transfer directions for the current diagnostic.
3. The AP-source audit is heuristic rather than hardware source filtering.
4. CSI response is sensitive to link state, spectral slope, signal level, multipath, and environmental drift.
5. The current setup is one room, one adapter, one AP, one channel, and one marked subject position.
6. Original labelled data and raw IQ archives have not been verified as backed up off-device.
7. Physical entry/exit testing and driver restoration after repeated live monitor operation still require local console execution.

Two additional independent development sessions (Sessions 4 and 5) are needed, preferably on separate days/time blocks. Analyze Sessions 1, 2, 4, and 5 only. The analysis tool accepts repeated `--session` arguments and rejects Session 3 by its source SHA-256 even if renamed. If cross-session validation remains weak, the appropriate project conclusion is that this hardware/setup did not demonstrate reliable stationary-presence detection. A new untouched held-out session would then be required for any revised detector.

## 11. Final conclusion

The project successfully delivered a repeatable CSI acquisition path, strict extraction and quality gates, interleaved labelled datasets, anonymized public feature releases, reproducible development analysis, safety-oriented live-tool behavior, and project documentation.

**It did not deliver a validated stationary-presence classifier.** The available development evidence does not support one. The correct engineering result is an acquisition-qualified research prototype with occupancy output deliberately abstained, pending additional independent physical data and a successful held-out evaluation.
