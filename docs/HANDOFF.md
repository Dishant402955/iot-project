# Project handoff

## Current state

- The live demo uses the temporal Extra Trees model in `models/presence_temporal_extra_trees_dev_v1.joblib`.
- The model was trained on 40 batches × 50 capture attempts = 2,000 attempts, with 20 `ABSENT` and 20 `PRESENT` batch-level examples.
- The live demo command is `./tools/presence_demo.sh`.
- A controlled four-batch live run matched all four known room conditions.
- Public-facing documentation is intentionally kept at project level. Detailed hardware bring-up notes and engineering investigation logs are not part of the public docs.

## Key files

- `README.md`: project overview and quick start.
- `docs/DATA_COLLECTION.md`: collection approach and sample counts.
- `docs/MODEL.md`: model and feature summary.
- `docs/RESULTS.md`: development and live-demo results.
- `docs/LIVE_DEMO.md`: how to run the demo.
- `models/`: selected model weights and metadata.
- `tools/presence_demo.sh`: live demo launcher.
