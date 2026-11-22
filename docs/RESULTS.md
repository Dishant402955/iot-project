# Results

## Development evaluation

The selected temporal Extra Trees model achieved the following results on development-data evaluation:

| Evaluation | Balanced accuracy | Sensitivity | Specificity |
|---|---:|---:|---:|
| Grouped round-based | 87.5% | 75.0% | 100.0% |
| Leave-one-development-session-out | 87.5% | 75.0% | 100.0% |

These results come from a small set of 40 batch-level examples. They are useful for describing the experiment and comparing approaches, but should not be presented as independently established real-world accuracy.

## Live demonstration

A controlled live run produced four predictions matching the known conditions:

| Batch | Room condition | Model prediction |
|---:|---|---|
| 1 | Empty | `ABSENT` |
| 2 | Empty | `ABSENT` |
| 3 | Empty | `ABSENT` |
| 4 | Stationary person present | `PRESENT` |

Each batch contained 50 capture attempts. This confirms that the checked-in model ran end to end in that demonstration; four batches are not an independent accuracy evaluation.
