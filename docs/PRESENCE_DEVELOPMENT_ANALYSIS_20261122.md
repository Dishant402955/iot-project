# Development analysis: interleaved Wi-Fi CSI sessions

**Date:** 2026-11-22
**Default scope:** Development Sessions 1 and 2. Session 3 is reserved held-out data and was not opened or analyzed by this procedure.

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

All retained profiles have 52 finite active-tone values. The session files are local-only and remain excluded from Git. The analysis script checks five-round condition order, batch counts, profile dimensions, finite values, acquisition gates, RX-idle, and within-session AP/channel consistency.

## Exploratory batch-level evaluation

The analysis aggregates each batch to its per-tone median profile, standardizes using training batches only, and classifies held-out paired rounds using nearest class centroids. Each held-out fold contains both conditions from one session-round, preventing paired batches from being split across training and test.

| Evaluation | Batches | Accuracy | Sensitivity | Specificity | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| Leave one session-round pair out | 20 | 0.80 | 0.60 | 1.00 | 0.80 |
| Train Session 1, test Session 2 | 10 | 0.50 | 0.00 | 1.00 | 0.50 |
| Train Session 2, test Session 1 | 10 | 0.50 | 0.00 | 1.00 | 0.50 |

The leave-pair-out result corresponds to TP=6, TN=10, FP=0, FN=4. Both cross-session transfer directions predicted every held-out batch as ABSENT. The apparent within-development result does not transfer between sessions.

## Verdict

**No final occupancy classifier is justified by these development sessions.** The 0.80 grouped balanced accuracy is based on only ten paired rounds and has weak sensitivity. More importantly, session-transfer balanced accuracy is 0.50 with zero sensitivity in both directions. This is consistent with session-dependent CSI structure rather than a robust stationary-occupancy signature.

The live tool has consequently been made diagnostic-only: it reports channel anomaly but always emits `UNKNOWN_UNVALIDATED` for occupancy. It also fails closed on incomplete CSI/source/RX-idle audit and refuses baseline overwrite by default.

## Future development sessions and held-out protection

The analysis script defaults to Sessions 1 and 2. Sessions 4 and 5 are now collected. The next grouped analysis should supply all four development JSONL files explicitly:

```bash
vendor/.venv/bin/python tools/analyze_presence_development.py \
  --session data/presence_dataset/interleaved_20261122_180724.jsonl \
  --session data/presence_dataset/interleaved_20261122_183204.jsonl \
  --session data/presence_dataset/interleaved_20261122_200618.jsonl \
  --session data/presence_dataset/interleaved_20261122_202430.jsonl
```

The tool rejects the reserved Session 3 source by SHA-256 `9c2bfa791fbb67c511330aef9207dad74be32e388056930cd17522310ee1af57`, even if renamed, and also rejects paths containing its known session identifier. It requires at least two session files inside the repository. Session 3 must not be used for feature/threshold/model selection.

## Reproduction

```bash
vendor/.venv/bin/python tools/analyze_presence_development.py
vendor/.venv/bin/python -m unittest tests.test_presence_development_analysis -v
```

The machine-readable JSON report is `PRESENCE_DEVELOPMENT_ANALYSIS_20261122.json`. The script requires NumPy only.

## Integrity

- Empty-room baseline unchanged.
- No capture or VFIO operation performed by offline analysis.
- Session 3 not used for analysis or tuning.
- Original labelled data and raw IQ remain local-only.
