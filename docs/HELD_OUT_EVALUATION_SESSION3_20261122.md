# One-time held-out evaluation: Session 3

**Date:** 2026-11-22
**Model:** `profile_median_nearest_centroid_sessions_1_2_v1`
**Status:** Research benchmark only; not a deployable occupancy detector.

## Integrity

- Frozen model was trained only on Sessions 1 and 2.
- Session 3 source hash was verified before evaluation.
- No training, feature selection, threshold selection, or tuning was performed on Session 3.
- The evaluator refuses to overwrite this result. This is the one permitted evaluation.

## Acquisition availability

- Strict CSI profiles: 497/500 (99.4%).
- Batches passing acquisition gates: 10/10.
- Insufficient-CSI batches: 0.

## Batch-level classification

| TP | TN | FP | FN | Accuracy | Sensitivity | Specificity | Balanced accuracy | Precision | F1 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 4 | 1 | 2 | 0.700 | 0.600 | 0.800 | 0.700 | 0.750 | 0.667 |

## Per-batch predictions

| Round | Ground truth | Prediction | Valid CSI |
|---:|---|---|---:|
| 1 | ABSENT | ABSENT | 50/50 |
| 1 | PRESENT | PRESENT | 50/50 |
| 2 | PRESENT | PRESENT | 50/50 |
| 2 | ABSENT | ABSENT | 50/50 |
| 3 | ABSENT | ABSENT | 50/50 |
| 3 | PRESENT | ABSENT | 49/50 |
| 4 | PRESENT | PRESENT | 49/50 |
| 4 | ABSENT | PRESENT | 50/50 |
| 5 | ABSENT | ABSENT | 49/50 |
| 5 | PRESENT | ABSENT | 50/50 |

## Interpretation

This is a single held-out session with ten batch-level observations. Do not infer generalization across rooms, people, devices, or APs. Do not tune the frozen model using these results. The model remains a research benchmark and must not drive occupancy decisions. A revised model requires new development data and a new untouched held-out session.
