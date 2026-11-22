# Development analysis: interleaved Sessions 1 and 2

**Date:** 2026-11-22
**Scope:** Development Sessions 1 and 2 only. Held-out Session 3 was not opened or analyzed by this procedure.

## Dataset audit

| Measure | Result |
|---|---:|
| Sessions | 2 |
| Batches | 20/20 |
| Attempts | 1,000 |
| Valid strict CSI profiles | 999/1,000 |
| ABSENT profiles | 500 |
| PRESENT profiles | 499 |
| Batches passing both acquisition gates | 20/20 |
| RX-idle | 20/20 batches at 100% |

All retained profiles have 52 finite active-tone values. The session files are local-only and remain excluded from Git. The analysis script checks the five-round condition order, batch counts, profile dimensions, finite values, acquisition gates, RX-idle, and within-session AP/channel consistency.

## Exploratory batch-level evaluation

The analysis aggregates each batch to its per-tone median profile, standardizes using training batches only, and classifies held-out paired rounds using nearest class centroids. Each held-out fold contains both conditions from one session-round, preventing the two paired batches from being split across training and test.

| Evaluation | Batches | Accuracy | Sensitivity | Specificity | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| Leave one session-round pair out | 20 | 0.80 | 0.60 | 1.00 | 0.80 |
| Train Session 1, test Session 2 | 10 | 0.50 | 0.00 | 1.00 | 0.50 |
| Train Session 2, test Session 1 | 10 | 0.50 | 0.00 | 1.00 | 0.50 |

The leave-pair-out result corresponds to TP=6, TN=10, FP=0, FN=4. Both cross-session transfer directions predicted every held-out batch as ABSENT. This demonstrates that the apparent within-development result does not transfer across sessions.

## Per-round observations

The ABSENT/PRESENT median CSI profile distance and tone-spread difference vary across rounds. The tone-spread difference changes sign across rounds and sessions. A single stable occupancy direction is not established. See `PRESENCE_DEVELOPMENT_ANALYSIS_20261122.json` for the machine-readable values and fold results.

## Verdict

**No final occupancy classifier is justified by these development sessions.** The 0.80 grouped balanced accuracy is based on only ten paired rounds and has weak sensitivity. More importantly, session-transfer balanced accuracy is 0.50 with zero sensitivity in both directions. This is consistent with session-dependent CSI structure rather than a robust stationary-occupancy signature.

Do not freeze or deploy a PRESENT/ABSENT classifier from these data. Do not use Session 3 to choose features, thresholds, or model settings. The reserved held-out Session 3 remains untouched. A future detector requires additional independent development sessions and a new held-out session after a detector is frozen.

## Reproduction

From the repository root:

```bash
vendor/.venv/bin/python tools/analyze_presence_development.py
vendor/.venv/bin/python -m unittest tests.test_presence_development_analysis -v
```

The script is pinned to the two development session paths and refuses alternate paths, including the reserved held-out session. It requires NumPy only; no machine-learning package is required.

## Integrity

- The empty-room baseline was not modified.
- No capture or VFIO operation was run.
- Session 3 was not used for analysis or tuning.
- Original labelled data and raw IQ remain local-only.
