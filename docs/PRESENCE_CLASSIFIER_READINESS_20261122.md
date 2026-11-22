# Presence classifier readiness: 2026-11-22

## Corrected labelled dataset

The original five-round interleaved session was reprocessed from all 500 archived IQ captures using the corrected L-LTF alignment search. The source JSONL, raw captures, and saved empty-room baseline were not modified.

Corrected output: `data/presence_dataset/interleaved_20261122_160950_reprocessed.jsonl`

| Measurement | Result |
|---|---:|
| Capture attempts | 500 |
| Strict-quality CSI | 497/500 (99.4%) |
| Target-attributed strict CSI | 495/500 (99.0%) |
| RX-idle barriers | 500/500 |
| AP source heuristic matches | 498/500 |
| Batches passing both acquisition gates | 10/10 |
| ABSENT profiles | 247 |
| PRESENT profiles | 248 |

The acquisition gates are >=80% target-attributed strict CSI and >=90% target source attribution. Every batch passed both. The strict CSI gates were not relaxed.

## Grouped-by-round exploratory classification

A leave-one-round-out evaluation was run on all 495 target-attributed profiles. In each fold, four complete rounds were used for training and the fifth complete round was held out. This is preferable to random profile splitting because profiles in one capture batch share environmental conditions. It remains a single physical session with only five temporal groups, so results are preliminary and do not estimate performance on new days/rooms.

| Features / model | Accuracy | Balanced accuracy | Sensitivity | Specificity | ROC AUC |
|---|---:|---:|---:|---:|---:|
| Raw centered + logistic regression | 0.335 | 0.336 | 0.190 | 0.482 | 0.198 |
| Raw centered + linear SVM | 0.343 | 0.344 | 0.113 | 0.575 | 0.162 |
| Raw centered + RBF SVM | 0.675 | 0.675 | 0.565 | 0.785 | 0.716 |
| Raw centered + extra trees | 0.570 | 0.570 | 0.609 | 0.530 | 0.613 |
| Raw centered + random forest | 0.554 | 0.553 | 0.617 | 0.490 | 0.634 |
| Linear detrending + RBF SVM | 0.616 | 0.617 | 0.444 | 0.789 | 0.632 |
| First differences + random forest | 0.461 | 0.461 | 0.335 | 0.587 | 0.460 |

The best exploratory model is the raw-profile RBF SVM, but its held-out-round accuracies were `[0.939, 0.670, 0.531, 0.735, 0.500]`. Sensitivity is only 0.565, and performance changes sharply with the held-out round. This is not suitable for deployment. No model or decision threshold has been selected.

Linear detrending did not solve the issue. It reduced the RBF SVM balanced accuracy to 0.617 and sensitivity to 0.444. First differences also performed poorly. Do not assume these transformations remove nuisance drift without removing potentially useful occupancy signal.

## Round-level consistency

The ABSENT/PRESENT median profile distances were:

| Round | Distance (dB RMS) |
|---|---:|
| 1 | 0.5405 |
| 2 | 0.1071 |
| 3 | 0.2568 |
| 4 | 0.2173 |
| 5 | 0.3346 |

The overall ABSENT-vs-PRESENT median profile distance is 0.0429 dB RMS. The large differences between the per-round distances and the aggregate distance indicate substantial temporal/condition variation. The batch-level spectral slope and tone spread do not move consistently in one direction between ABSENT and PRESENT across the five rounds. CFO also drifts over the experiment, but this observation alone does not establish its cause or prove that it explains the class overlap.

The analysis is descriptive, not a statistical proof that no classifier can work. It does show that this one session is not sufficient to validate a stable stationary-person detector.

## Decision and next work

1. Do not deploy the exploratory SVM or any other model from this dataset.
2. Validate the corrected CSI extractor on a fresh physical 50-capture run. The 497/500 result above is offline replay, not a fresh live result.
3. Design additional independent sessions/days with repeated ABSENT/PRESENT blocks and stable device geometry. Include multiple stationary positions/orientations if the product is expected to detect people anywhere in the room.
4. Keep all transforms, model choices, and thresholds frozen before final held-out session evaluation.
5. Evaluate sensitivity, specificity, balanced accuracy, false transitions/hour, valid-measurement availability, and entry/exit latency.

Acquisition recovery and occupancy classification are separate milestones. The corrected extractor has passed the current offline acquisition gates; live classification remains unvalidated.
