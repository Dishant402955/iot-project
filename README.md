# Wi-Fi Stationary Human-Presence Sensing

An experimental Wi-Fi-based room-presence project. It uses changes in wireless signals to distinguish an empty room from a room containing a stationary person. The repository includes the trained model and a live demonstration.

## Run the live demo

```bash
./tools/presence_demo.sh
```

Run this from the project root on the laptop's physical console. The demo uses the included temporal Extra Trees model; it does not train or calibrate a model when launched. Each prediction is based on a fresh batch of 50 capture attempts. Use `once` for one batch or `step` to pause between batches:

```bash
./tools/presence_demo.sh once
./tools/presence_demo.sh step
```

The capture process briefly interrupts the laptop's Wi-Fi connection while collecting each batch. Do not run it over SSH or through a remote session. Press `Ctrl+C` to stop.

## How we collected the data

We collected the data ourselves through repeated, controlled room experiments. Each batch represented one of two conditions: an empty room (`ABSENT`) or a stationary person in the room (`PRESENT`). We alternated these conditions across rounds and repeated the experiments over multiple sessions.

The development set contains **40 batches × 50 capture attempts = 2,000 capture attempts**. Each 50-attempt batch produces one training example, giving **40 training examples** in total: 20 `ABSENT` and 20 `PRESENT`. Four development sessions contributed these examples. A separate session was kept out of this model's training and selection.

## Model

The live demo uses an **Extra Trees** classifier with temporal features. For each 50-attempt batch, the feature builder summarizes how the wireless measurements vary over time, producing 104 features. The model was trained on all 40 development examples.

The checked-in model and metadata are:

- `models/presence_temporal_extra_trees_dev_v1.joblib`
- `models/presence_temporal_extra_trees_dev_v1.json`

The demo verifies the model file's SHA-256 checksum and its recorded identity before inference.

## Results

Development evaluation reported **87.5% balanced accuracy** in both grouped round-based evaluation and leave-one-development-session-out evaluation. Sensitivity was 75% and specificity was 100% in those evaluations. These figures describe the small development dataset, not an independent real-world accuracy guarantee.

In the controlled live demonstration, four consecutive batches matched the known room condition: three `ABSENT` batches followed by one `PRESENT` batch. This is a successful demonstration run, not a large-scale accuracy study.

## Repository guide

- [Data collection](docs/DATA_COLLECTION.md)
- [Model](docs/MODEL.md)
- [Results](docs/RESULTS.md)
- [Development analysis reproducibility](docs/REPRODUCIBILITY.md)
- [Live demo](docs/LIVE_DEMO.md)
- [Public dataset notes](data/public_dataset/README.md)

The original labelled collection files and raw capture archives are local research data and are not included in the public repository. The anonymized dataset files under `data/public_dataset/` are the shareable copies.
