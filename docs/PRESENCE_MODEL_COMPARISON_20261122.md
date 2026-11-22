# Development-only model comparison

**Date:** 2026-11-22
**Scope:** Sessions 1, 2, 4 and 5 only. The consumed held-out Session 3 was not accessed.

## Data and protocol

- 2,000 audited capture attempts and 1,989 retained strict CSI profiles.
- 40 batch-level examples, each represented by one 52-tone per-tone median profile.
- 20 paired session-round groups. Each grouped fold holds out both ABSENT and PRESENT batches from one round together.
- Individual CSI frames are not treated as independent examples.
- Scaling is fitted inside each training-fold pipeline. Fixed conservative model configurations were used; no outer-fold hyperparameter tuning was performed.
- Candidates: standardized nearest centroid, regularized logistic regression, linear SVM, RBF SVM, constrained Random Forest, constrained ExtraTrees, shallow Gradient Boosting, and an 8-unit MLP.

## Grouped leave-one-session-round-out results

| Model | Accuracy | Balanced accuracy | Sensitivity | Specificity | TP/TN/FP/FN |
|---|---:|---:|---:|---:|---:|
| Nearest centroid | 0.800 | 0.800 | 0.650 | 0.950 | 13/19/1/7 |
| Logistic regression | 0.825 | 0.825 | 0.750 | 0.900 | 15/18/2/5 |
| Linear SVM | 0.825 | 0.825 | 0.750 | 0.900 | 15/18/2/5 |
| RBF SVM | 0.750 | 0.750 | 0.500 | 1.000 | 10/20/0/10 |
| Random Forest | 0.850 | 0.850 | 0.800 | 0.900 | 16/18/2/4 |
| ExtraTrees | 0.825 | 0.825 | 0.650 | 1.000 | 13/20/0/7 |
| Gradient Boosting | 0.775 | 0.775 | 0.700 | 0.850 | 14/17/3/6 |
| Small MLP | 0.850 | 0.850 | 0.800 | 0.900 | 16/18/2/4 |

The small MLP and Random Forest tie for the highest pooled grouped balanced accuracy. The MLP converged without convergence warnings in all 24 evaluation folds. These are 20 paired-round folds from only four physical acquisition sessions, not 40 independent sessions. This grouped result is exploratory and may reward session-specific structure.

## Leave-one-development-session-out transfer

| Model | Pooled accuracy | Pooled balanced accuracy | Sensitivity | Specificity |
|---|---:|---:|---:|---:|
| Nearest centroid | 0.700 | 0.700 | 0.650 | 0.750 |
| Logistic regression | 0.750 | 0.750 | 0.600 | 0.900 |
| Linear SVM | 0.750 | 0.750 | 0.550 | 0.950 |
| RBF SVM | 0.750 | 0.750 | 0.650 | 0.850 |
| Random Forest | 0.800 | 0.800 | 0.650 | 0.950 |
| ExtraTrees | 0.800 | 0.800 | 0.650 | 0.950 |
| Gradient Boosting | 0.750 | 0.750 | 0.650 | 0.850 |
| Small MLP | 0.800 | 0.800 | 0.600 | 1.000 |

### Per-session transfer balanced accuracy

| Model | Test S1 | Test S2 | Test S4 | Test S5 |
|---|---:|---:|---:|---:|
| Nearest centroid | 0.60 | 0.50 | 0.90 | 0.80 |
| Logistic regression | 0.50 | 0.80 | 0.90 | 0.80 |
| Linear SVM | 0.60 | 0.70 | 0.90 | 0.80 |
| RBF SVM | 0.60 | 0.70 | 0.90 | 0.80 |
| Random Forest | 0.60 | 0.90 | 0.90 | 0.80 |
| ExtraTrees | 0.60 | 0.90 | 0.90 | 0.80 |
| Gradient Boosting | 0.60 | 0.70 | 0.90 | 0.80 |
| Small MLP | 0.60 | 0.80 | 0.90 | 0.90 |

Every model shows session dependence. The MLP and Random Forest tie for best grouped balanced accuracy (0.850); both reach 0.800 pooled balanced accuracy under leave-one-session-out transfer, with only 0.60 and 0.65 sensitivity respectively. Random Forest reaches 0.80 pooled balanced accuracy and 0.65 sensitivity, but only 0.60 balanced accuracy when Session 1 is held out. The nearest-centroid model collapses to 0.50 balanced accuracy on Session 2. This is not enough evidence for reliable occupancy detection.

## Model decision

**No model is selected for deployment.** The MLP and Random Forest improve the grouped result over nearest centroid, but the gains do not establish robust generalization across sessions. There are only 40 batch examples and four acquisition sessions; all models remain vulnerable to session/device/environment drift. The correct system behavior remains `UNKNOWN_UNVALIDATED` for occupancy, with channel anomaly reported separately.

Session 3 was not read, evaluated, or used for selection. Its prior one-time frozen-benchmark result remains consumed and unchanged. A new model would require additional independent development sessions and a new untouched held-out session.

## Reproduction

```bash
uv pip install --python vendor/.venv/bin/python -r tools/requirements-presence-analysis.txt
vendor/.venv/bin/python tools/analyze_presence_development.py
vendor/.venv/bin/python tools/compare_presence_models.py
```

## Source integrity

- Session 1: SHA-256 `c18489c749c1b7e55effbe2c42a3a4c9a88cd39110419264d1c6f43b93c70836`
- Session 2: SHA-256 `4faca4b438b6bba0bfb2572fa5c4f4cf59558c780d815762f78fb18f51e5f553`
- Session 4: SHA-256 `15fb6d54295d945ab7e64cb5dd64009d33be9afac74f701e8e70713f76d44eca`
- Session 5: SHA-256 `43dce1a015e5291de578d1c9128f51bf130a74ef9c0c9fbba81fa3419e5156db`

NumPy 2.2.6; scikit-learn 1.7.2. No raw IQ, labelled public data, AP BSSID, or exact capture timestamps are included in this report. The live baseline and frozen benchmark artifacts were not modified.
