# Frozen research benchmark model

**Frozen:** 2026-11-22
**Model:** `profile_median_nearest_centroid_sessions_1_2_v1`
**Status:** Research benchmark only; not a validated occupancy detector.

## Why this model was frozen

The Sessions 1/2 development diagnostic is weak (grouped sensitivity 0.60) and cross-session transfer fails (sensitivity 0.00 in both directions). No model is justified for deployment. To complete an auditable independent benchmark, the simple nearest-centroid procedure already evaluated during development was frozen without tuning and evaluated once on Session 3. The result cannot be used to tune this model.

## Training data integrity

Exactly 20 batch-level training examples were used: ten ABSENT and ten PRESENT, five paired rounds from each development session.

| Session | Role | Source SHA-256 |
|---|---|---|
| 1 | Development training | `c18489c749c1b7e55effbe2c42a3a4c9a88cd39110419264d1c6f43b93c70836` |
| 2 | Development training | `4faca4b438b6bba0bfb2572fa5c4f4cf59558c780d815762f78fb18f51e5f553` |
| 3 | Reserved one-time test | `9c2bfa791fbb67c511330aef9207dad74be32e388056930cd17522310ee1af57` |

Session 3 was not read or used to create the model. The freeze script checks the exact Session 1/2 source hashes and refuses alternate training paths.

## Fixed model definition

1. For each batch, take the per-tone median across its accepted 52-tone CSI profiles.
2. Compute per-tone mean and population standard deviation across the 20 training batch profiles only.
3. Standardize each training and test batch using those fixed training statistics. Replace scales below `1e-8` with `1.0`.
4. Compute the mean standardized profile for each class (ABSENT and PRESENT).
5. Assign the class with the smaller squared Euclidean distance. A tie is assigned PRESENT.

No features, thresholds, hyperparameters, or preprocessing are selected using Session 3. The model has no confidence calibration or abstention threshold; it is a deliberately simple research benchmark and must not drive occupancy decisions.

## Artifact and integrity

- Model JSON: `models/presence_centroid_baseline_s1_s2_v1.json`
- Model SHA-256: `43560a6e2c5f9ca67c81c07e732fb990fd1fff49c792565df04ea448a2a25b02`
- Freeze script: `tools/freeze_presence_baseline_model.py`
- Tests: `tests/test_freeze_presence_baseline_model.py`
- `held_out_session_3_used` is false in the artifact.
- Model deployment status is `NOT_VALIDATED_NOT_FOR_OCCUPANCY_DECISIONS`.

## One-time evaluation result

The one-time evaluation has been completed and is recorded in `docs/HELD_OUT_EVALUATION_SESSION3_20261122.md` and `.json`. It produced TP=3, TN=4, FP=1, FN=2; accuracy 0.70, sensitivity 0.60, specificity 0.80, and balanced accuracy 0.70. Do not run `tools/evaluate_presence_heldout.py` again. It refuses to overwrite the existing result. The evaluator verified the exact Session 3 source SHA-256 and frozen model hash and loaded only the frozen model. Its synthetic unit tests do not access Session 3. Do not tune or retrain after seeing the held-out result. If a model change is later made, it requires a new untouched held-out session.
