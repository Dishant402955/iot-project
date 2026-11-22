# RF-DS paper reproduction and dataset replay

Selected paper: **Human Presence Detection via Wi-Fi Range-Filtered Doppler Spectrum on Commodity Laptops**, arXiv:2603.10845v3, PerCom 2026. Paper: https://arxiv.org/abs/2603.10845

This directory contains (1) an RF-DS implementation attempt, (2) timestamp-aligned evaluation against the two released approach/leave label files, and (3) a separate supervised per-session baseline. These are separate experiments. The supervised baseline is not RF-DS and is not evidence of a live detector.

## Reproducible setup

Requirements: Ubuntu/Linux x86_64, Python 3.12, `uv`, and about 2 GB free disk space for the environment and working data. The sample dataset occupies roughly 933 MB. No sudo is needed for this offline workflow.

```bash
research/rfds-reproduction/bootstrap.sh
research/rfds-reproduction/verify_environment.sh
```

Download the paper dataset if it is not present:

```bash
research/rfds-reproduction/download_dataset.sh
```

Run the complete analysis and regenerate reports/models:

```bash
research/rfds-reproduction/reproduce_all.sh
```

All generated reports, plots, NPZs and model files are written to `outputs/` and ignored by Git. The raw dataset is also ignored by Git. The dataset README and its CC BY 4.0 terms are retained under `data/rfds-reference/README.md`.

## Dataset facts verified locally

- Three CSI recordings: `walking_HP`, `walking_LENOVO`, `Breathing_HP`.
- 512 indexed CSI tones in each LTF field (`csi1` and `csi2`); metadata reports channel 79, 160 MHz, carrier 6345 MHz, nominal 10 ms repetition.
- Walking HP: 8,227 rows, 21 label intervals, 81.8 s; Lenovo: 8,443 rows, 21 intervals, 84.9 s; breathing: 11,971 rows, 117.2 s.
- There are repeated timestamps in the files (543 HP and 510 Lenovo zero intervals). Median positive interval is about 10 ms, but the stream is not perfectly uniform. The current implementation does not yet have a fully validated irregular-sampling correction.
- Only the two walking recordings include label CSVs. The breathing sample has no released label file, so its analysis is qualitative only.
- The loader averages `csi1` and `csi2` per tone. The dataset README describes two LTF fields; the fields have high measured complex correlation in the supplied samples. This choice is explicit and should be checked against author clarification if exact reproduction is required.

## Run individual experiments

RF-DS for a single recording:

```bash
.venv-rfds/bin/python research/rfds-reproduction/run_dataset.py \
  data/rfds-reference/walking_HP/csi.csv \
  --output-dir research/rfds-reproduction/outputs

.venv-rfds/bin/python research/rfds-reproduction/evaluate_labels.py \
  --labels data/rfds-reference/walking_HP/labels.csv \
  --decisions research/rfds-reproduction/outputs/walking_HP_decisions.csv
```

Supervised per-session baseline:

```bash
.venv-rfds/bin/python research/rfds-reproduction/baseline.py \
  data/rfds-reference/walking_HP/csi.csv \
  --report research/rfds-reproduction/outputs/walking_HP_baseline_metrics.json \
  --train-model research/rfds-reproduction/outputs/walking_HP_baseline.joblib
```

## Interpretation and limitations

- The paper specifies 160 MHz, 512 CSI tones, 100 Hz detection / 10 Hz idle, 32-frame Doppler windows, 9 range gates, 20-frame SNR history, 3-frame detection window, 12 dB threshold, and 3-frame majority voting.
- The paper's text does not fully specify the FIR cutoff, clipping parameter units, tone-frequency index vector, or all implementation details. Our defaults are explicit tunables, not asserted paper-exact values.
- Current RF-DS metrics are poor (roughly 18-20% three-state accuracy, with most outputs ABSENT) and do not reproduce the paper's reported 94% / 96.5%. Parameter sweeps of the unspecified FIR cutoff and 6-12 dB thresholds did not resolve this. Do not claim successful reproduction.
- The supervised baseline is a separate diagnostic experiment. Its features are normalized inside each 32-frame window and windows crossing temporal split boundaries are purged to reduce leakage. `cross_device.py` evaluates strict train-one-device/test-the-other transfer. No result from these two recordings establishes population-level generalization or a live model.
- The sample dataset is only three sessions and two subjects/devices. It is inadequate for a robust deployment claim.
- Dataset replay must be visibly identified as `DATASET REPLAY`, never as live Wi-Fi sensing.

## Live hardware feasibility

See `docs/PROJECT_EXECUTION_PLAN.md` and `research/rfds-reproduction/HARDWARE_GAP.md`. The current RTL8821CE is 1T1R, 20 MHz, and the Devourer path is external-AP/bistatic with 52-tone CSI and roughly 130 ms readback. Exact monostatic RF-DS reproduction is not supported by the demonstrated hardware path. A separate live bistatic experiment remains unvalidated; current CSI acceptance is too low and no live labelled empty/occupied dataset exists.
