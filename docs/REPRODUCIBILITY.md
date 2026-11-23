# Development analysis reproducibility

This workflow reproduces a **separate exploratory CSI batch diagnostic** from the
selected temporal Extra Trees model. It does not train, tune, recalibrate, or replace
the live model. The diagnostic uses per-tone median CSI profiles and a nearest-centroid
comparison; its metrics must not be confused with the temporal Extra Trees results in
`docs/RESULTS.md`.

## Data scope and safeguards

The analysis accepts only these exact local source files:

| Acquisition session | Source file |
|---:|---|
| 1 | `data/presence_dataset/interleaved_20261122_180724.jsonl` |
| 2 | `data/presence_dataset/interleaved_20261122_183204.jsonl` |
| 4 | `data/presence_dataset/interleaved_20261122_200618.jsonl` |
| 5 | `data/presence_dataset/interleaved_20261122_202430.jsonl` |

The consumed held-out Session 3 (`interleaved_20261122_185040.jsonl`) is not in the
allowlist. The script rejects any non-allowlisted path before checking file existence,
opening, hashing, or parsing it. Each permitted source is SHA-256 pinned, so modified
or substituted data is rejected. The analysis also validates the five-round paired
protocol, 50 audited attempts per batch, 52-tone finite profile matrices, capture gates,
and stable AP/channel within each session.

The source collection files are local research data and are not committed to the
repository. Run the workflow on the machine that contains those exact files. The script
will fail closed if a source is absent or its hash differs.

## Run the analysis

From the repository root, with the project NumPy environment installed:

```bash
vendor/.venv/bin/python tools/analyze_presence_development.py \
  --output /tmp/presence-development-analysis.json
```

By default, the script uses the four allowlisted development sessions (1, 2, 4, and 5).
You can pass one or more `--session PATH` arguments to select a subset, but every path
must still be on the exact allowlist and at least two sessions are required. The JSON
output records source hashes, batch/profile counts, grouped leave-one-session-round-out
metrics, session-transfer metrics, method, and the explicit Session 3 access flag.

## Recorded run

The recorded reproducibility run processed 40 batches and 2,000 audited capture
attempts. It contained 1,989 accepted profiles (994 from ABSENT batches and 995 from
PRESENT batches); all 40 batches passed the acquisition gates.

This diagnostic's grouped leave-one-session-round-out nearest-centroid result was
80.0% balanced accuracy (65.0% sensitivity, 95.0% specificity). Per-session transfer
balanced accuracy varied from 50.0% to 90.0%. This variation is a useful warning about
session dependence. These numbers are **not** the selected temporal Extra Trees model's
reported 87.5% balanced accuracy and must not be substituted for it.

## Tests and verification

Run the Python unit tests:

```bash
vendor/.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Run the RX process supervisor shell test and syntax checks:

```bash
bash tests/test_rx_process_supervisor.sh
bash -n tools/presence_demo.sh tools/lib/rx_process_supervisor.sh
```

The unit tests cover metric calculations, fold grouping, the development-session
allowlist, rejection of Session 3 before file I/O, source-hash mismatch, and existing
collection, parsing, and detector behavior. The live demo itself is not launched by the
test suite because capture reconfigures the physical Wi-Fi interface.

## Model and demo protection

This workflow does not import the model-training script or write to `models/`,
`tools/live_presence_model_demo.py`, or `tools/presence_demo.sh`. The selected model
weights remain pinned by the SHA-256 in `models/presence_temporal_extra_trees_dev_v1.json`.
The live demo continues to load the existing saved model and perform inference only.
