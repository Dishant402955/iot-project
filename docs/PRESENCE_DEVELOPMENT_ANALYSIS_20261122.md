# Development analysis: interleaved Wi-Fi CSI sessions

**Date:** 2026-11-22
**Current scope:** Development Sessions 1, 2, 4 and 5 only. The consumed held-out Session 3 was not accessed by this analysis.

## Dataset audit

| Measure | Result |
|---|---:|
| Development sessions | 4 (1, 2, 4, 5) |
| Batch examples | 40/40 |
| Capture attempts | 2,000 |
| Retained strict CSI profiles | 1,989 |
| ABSENT profiles | 994 |
| PRESENT profiles | 995 |
| Batches passing both acquisition gates | 40/40 |

Each example is one batch-level 52-tone median profile. The analysis keeps both conditions from each session-round together during grouped evaluation. It uses real acquisition IDs (1, 2, 4, 5), not input order. The source allowlist rejects any other file before opening it.

## Grouped nearest-centroid diagnostic

| Evaluation | Batches | Accuracy | Sensitivity | Specificity | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| Leave one session-round pair out | 40 | 0.80 | 0.65 | 0.95 | 0.80 |

Confusion counts: TP=13, TN=19, FP=1, FN=7.

## Leave-one-development-session-out transfer

| Test session | Accuracy | Sensitivity | Specificity | Balanced accuracy |
|---|---:|---:|---:|---:|
| Session 1 | 0.60 | 0.20 | 1.00 | 0.60 |
| Session 2 | 0.50 | 1.00 | 0.00 | 0.50 |
| Session 4 | 0.90 | 0.80 | 1.00 | 0.90 |
| Session 5 | 0.80 | 0.60 | 1.00 | 0.80 |

The model behavior varies substantially by acquisition session. This is not robust generalization. The expanded model comparison evaluates regularized linear models, SVMs, tree ensembles and a small MLP; see `PRESENCE_MODEL_COMPARISON_20261122.md` and `.json`. The MLP reaches 0.850 grouped balanced accuracy and 0.800 pooled leave-one-session-out balanced accuracy, with 0.60 sensitivity. No candidate is suitable for deployment.

## Verdict

**No reliable occupancy classifier is justified.** The live tool remains diagnostic-only: it always reports `UNKNOWN_UNVALIDATED` for occupancy and keeps channel anomaly separate. It fails closed on incomplete CSI/source/RX-idle audit.

Session 3 was not opened or used by these development analyses. Its earlier one-time frozen-model evaluation is consumed and must not be repeated or used for tuning. Any future detector requires additional independent development sessions and a new untouched held-out session.

## Reproduction

```bash
vendor/.venv/bin/python tools/analyze_presence_development.py
vendor/.venv/bin/python tools/compare_presence_models.py
```

The machine-readable combined report is `PRESENCE_DEVELOPMENT_ANALYSIS_20261122.json`. Original labelled data and raw IQ remain local-only.
