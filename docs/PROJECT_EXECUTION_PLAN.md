# Project execution plan: stationary Wi-Fi presence sensing

**Updated:** 2026-11-22

## Objective and verdict

Academic evaluation of stationary room-presence sensing from RTL8821CE CSI. The live system must return `UNKNOWN` / `INSUFFICIENT_CSI` whenever capture quality or model evidence is inadequate. This is not a safety/security alarm.

**Current conclusion: acquisition is qualified for one fixed setup, but no reliable occupancy detector has been demonstrated.** Eight lightweight model families have been compared on all development data. None generalizes consistently enough to deploy. The live tool remains diagnostic-only and always reports `UNKNOWN_UNVALIDATED` for occupancy.

## Data status

| Session | Role | Attempts | Retained strict CSI profiles | Notes |
|---|---|---:|---:|---|
| 1 | Development | 500 | 500 | 10/10 batches pass acquisition gates |
| 2 | Development | 500 | 499 | 10/10 batches pass acquisition gates |
| 3 | Consumed held-out | 500 | 497 | Frozen benchmark evaluated exactly once; never use for tuning |
| 4 | Development | 500 | 498 | 10/10 batches pass acquisition gates |
| 5 | Development | 500 | 492 target-attributed (498 structural) | 10/10 batches pass; 246 ABSENT + 246 PRESENT retained |

Sessions 1, 2, 4 and 5 contain 2,000 capture attempts and 1,989 retained strict CSI profiles. All 40 batches passed both configured acquisition gates. Session 3 is excluded from every new analysis and model comparison. Both analysis tools enforce an exact allowlist of the four development source paths before opening files.

## Development validation and model comparison

One example per batch is used: the per-tone median across valid CSI profiles (52 features). Individual frames are not treated as independent samples. Grouped folds hold out both conditions from a session-round together. Scaling is fitted only on each training fold. Fixed, conservative model configurations are used without outer-fold tuning.

| Model | Grouped balanced accuracy | Leave-one-session-out balanced accuracy | Leave-one-session-out sensitivity |
|---|---:|---:|---:|
| Nearest centroid | 0.800 | 0.700 | 0.650 |
| Logistic regression | 0.825 | 0.750 | 0.600 |
| Linear SVM | 0.825 | 0.750 | 0.550 |
| RBF SVM | 0.750 | 0.750 | 0.650 |
| Random Forest | 0.850 | 0.800 | 0.650 |
| ExtraTrees | 0.825 | 0.800 | 0.650 |
| Gradient Boosting | 0.775 | 0.750 | 0.650 |
| Small MLP | 0.850 | 0.800 | 0.600 |

The small MLP ties Random Forest for the best grouped result but reaches only 0.800 balanced accuracy and 0.60 sensitivity when an entire acquisition session is held out. Random Forest has 0.80 session-transfer balanced accuracy but only 0.65 sensitivity and varies by session (0.60 on Session 1). This is not robust evidence. **No model is selected or frozen for occupancy decisions.**

Reports and machine-readable outputs:
- `docs/PRESENCE_DEVELOPMENT_ANALYSIS_20261122.md` / `.json`
- `docs/PRESENCE_MODEL_COMPARISON_20261122.md` / `.json`
- `tools/analyze_presence_development.py`
- `tools/compare_presence_models.py`

The older frozen nearest-centroid model from Sessions 1/2 remains a benchmark artifact only. Its one-time Session 3 result (balanced accuracy 0.70, sensitivity 0.60) is consumed and unchanged. Never rerun the held-out evaluator or tune on Session 3.

## Acquisition and safety engineering completed

- RTL8821CE PCIe/VFIO raw-IQ capture and driver-restoration workflow.
- Correct CCA trigger interpretation and Realtek trigger-time register documentation.
- Strict 52-tone L-LTF CSI extraction and quality checks.
- Repeated-L-LTF alignment correction with regression coverage; strict gates unchanged.
- RX-idle barrier and post-arm target-source audit heuristic (not hardware source-MAC filtering).
- Five-round interleaved collector, offline reprocessor, acquisition reports and anonymized public feature datasets.
- Live detector hardening: occupancy always `UNKNOWN_UNVALIDATED`; channel anomaly is separate; missing CSI/source/RX-idle audit fails closed; baseline overwrite requires explicit override.
- Development allowlist and grouped/session-transfer validation; multiple classical ML models and a small MLP compared.

## Non-negotiable integrity constraints

- Never open or use Session 3 source data for further analysis, tuning or evaluation.
- Never lower strict CSI gates to improve yield.
- Insufficient CSI must never be interpreted as ABSENT.
- Do not overwrite `data/live_presence_baseline.json`; expected SHA-256: `2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74`.
- Frozen benchmark SHA-256 must remain `43560a6e2c5f9ca67c81c07e732fb990fd1fff49c792565df04ea448a2a25b02`.
- Keep original labelled JSONL and raw IQ out of public GitHub.
- Never run VFIO, driver reload, or physical capture through SSH or the remote coding agent.

## Remaining owner-side tasks

1. On the physical machine, inspect raw IQ archive contents and create/verify an encrypted private off-device backup of raw IQ and original labelled JSONL. The remote agent cannot read root-owned archives and must not use sudo or copy private data.
2. On the physical laptop console, verify live empty/occupied/entry/exit/poor-CSI transitions, driver restoration, Ctrl+C cleanup, and baseline integrity. Do not interpret these as deployment validation; the current detector deliberately abstains.
3. If pursuing a revised detector, collect additional independent development sessions under controlled but varied conditions, then collect a new untouched held-out session. Session 3 is permanently consumed.
4. Only if future independent validation is convincing should a new model be frozen and a live occupancy state machine implemented.

## Reproducible software checks

```bash
uv pip install --python vendor/.venv/bin/python -r tools/requirements-presence-analysis.txt
vendor/.venv/bin/python tools/analyze_presence_development.py
vendor/.venv/bin/python tools/compare_presence_models.py
vendor/.venv/bin/python -m unittest discover -s tests -v
vendor/.venv/bin/python vendor/devourer/tools/la_csi.py --selftest
vendor/.venv/bin/python vendor/devourer/tests/la_csi_series_selftest.py
python3 -m compileall -q tools vendor/devourer/tools tests
bash -n tools/rtl8821ce_pcie_la_capture.sh
git diff --check
```

A fresh CMake/CTest build may remain unavailable in the remote environment because the bundled CMake runtime previously lacked `libjsoncpp.so.25`; report this separately from existing C++ binary tests.
