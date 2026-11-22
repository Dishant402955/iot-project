---
license: cc-by-4.0
task_categories:
- time-series-forecasting
language:
- en
tags:
- wifi-csi
- human-sensing, monostatic, intel, signal-processing, 6g, horizon-europe
pretty_name: Wi-Fi Monostatic Human Sensing (Intel)
size_categories:
- 100M<n<1B
---
# Human Presence Detection via Wi-Fi Range-Filtered Doppler Spectrum — Sample Dataset

**Paper:** [Human Presence Detection via Wi-Fi Range-Filtered Doppler Spectrum on Commodity Laptops](https://zenodo.org/records/18594750)
**Authors:** Jessica Bartholdy Sanson, Rahul C. Shah, Valerio Frascolla
**Year:** 2026
**Venue:** IEEE PerCom 2026 — WiSense Workshop (Workshop on Wireless Sensing for Smart Spaces and Beyond)

---

## License

Creative Commons Attribution 4.0 — Copyright (c) 2026 Intel Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy of this dataset and associated documentation, to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies, subject to the above copyright notice and this permission notice appearing in all copies.

---

## Dataset Overview

> **Scope notice:** This is a **sample dataset** released to accompany the paper and enable reproducibility of the reported results. It contains a small number of recordings (3 sessions, 2 subjects, 2 devices). For algorithm validation, signal processing research, or replication of the paper's Range-Filtered Doppler Spectrum method, the data is sufficient as-is.

This dataset contains **Channel State Information (CSI)** recordings for Human Presence Detection (HPD) — capturing macro-level human movement (walking, approach/leave, breathing at rest).

The data is collected using **monostatic full-duplex Wi-Fi sensing** on **commercial off-the-shelf (COTS) laptops** — no external sensors, no dedicated transmitter, no hardware modification of any kind. Unlike bistatic datasets that require a separate transmitter (e.g., a router) and receiver, here a single unmodified laptop simultaneously transmits and receives by sharing the Local Oscillator and baseband processing, using the device's own self-interference as the sensing signal. CSI is read directly from the built-in NIC.

---

## Measurement Scenarios

### Approach-Leave Cycles (two recordings, one per laptop)
A user walks toward and away from the laptop across the range 0.5 m to 8 m and back, at a natural pace. Two full approach-leave sequences were recorded — one on the HP laptop and one on the Lenovo ThinkPad.

### Static Breathing (HP laptop only)
One user sits still at ~3 m from the HP laptop and breathes normally. No macro-movement; only micro-Doppler from respiration.

### Zone Labels
Distance zones are annotated in 1 m steps (0–8 m), synchronized to a ground-truth video recording captured simultaneously. Labels identify the user's distance zone at each time frame.

---

## Hardware & Capture Parameters

| Parameter              | Value                                             |
|------------------------|---------------------------------------------------|
| Hardware               | HP laptop (Wi-Fi 7) + Lenovo ThinkPad (Wi-Fi 6E)  |
| Bandwidth              | 160 MHz                                           |
| Frame rate             | ~100 Hz                                           |
| Channel                | 79 (Fc ≈ 6.3 GHz)                                 |
| Subcarriers            | 512 (CSI subcarriers only, pilots removed)        |
| LTF frames             | 2 (csi1, csi2) - 1 RX antenn                      |

---

## CSI Data Format

### Calibration State
The CSI samples in `csi.csv` are **frequency-domain measurements** that have already been pre-processed:

- **Pilot subcarriers removed** — only the 512  subcarriers are retained ( included zero data subcarriers).
- **Phase and delay calibrated** — phase alignment / synchronization has been applied compensating for carrier frequency offset and timing offset.
- **Two LTF frames averaged per measurement frame** (Ltf1 and Ltf2 from the raw stream are combined into the `csi1`/`csi2` columns).

The data is **ready for direct 2D DFT processing** to produce range-Doppler maps. No additional calibration or pilot removal is required.

### CSV Columns

Each row in `csi.csv` is one measurement frame (~10 ms interval at 100 Hz). Columns:

| Column | Description |
|--------|-------------|
| `event_timeStamp` | Device event timestamp (integer, ms) |
| `unix_timestamp` | Unix time in seconds (float) |
| `channel` | Wi-Fi channel number |
| `bandwidth_MHz` | Capture bandwidth in MHz |
| `measurement_time_repetition_ms` | Target frame interval in ms |
| `frequency_carrier_MHz` | Carrier frequency in MHz |
| `subcarrier_number` | Number of data subcarriers (512) |
| `csi1-{i}-real` | LTF 1, subcarrier i, real part (i = 0..511) |
| `csi1-{i}-imag` | LTF 1, subcarrier i, imaginary part (i = 0..511) |
| `csi2-{i}-real` | LTF 2, subcarrier i, real part (i = 0..511) |
| `csi2-{i}-imag` | LTF 2, subcarrier i, imaginary part (i = 0..511) |




### Ground Truth Labels (`labels/labels.csv`)

| Column | Description |
|--------|-------------|
| `Label ID` | Sequential label index |
| `Label` | Activity label (e.g., `sit`, `stand_up`, `walk`, distance zone) |
| `Start Time` | Start timestamp (device ms) |
| `End Time` | End timestamp (device ms) |
| `Start Frame` | Start frame index in `csi.csv` |
| `End Frame` | End frame index in `csi.csv` |

---

## File Structure

```
.data/
├── README.md                  ← this file
├── walking_HP/                ← HP laptop (Wi-Fi 7) — approach-leave walk
│   ├── csi.csv                ← calibrated CSI
│   └── labels/
│       ├── labels.csv         ← zone labels aligned to CSI frames
├── walking_LENOVO/            ← Lenovo ThinkPad (Wi-Fi 6E) — approach-leave walk
│   ├── csi.csv
│   └── labels/
│       ├── labels.csv
└── breathing_HP/              ← HP laptop (Wi-Fi 7) — static breathing
    ├── csi.csv

```

This work was supported by the Horizon Europe SNS JU projects 6G-SENSES (grant 101139282) and MULTIX (grant 101192521).
Ethics and Privacy
Informed consent obtained from all participants
Full GDPR compliance
Anonymized participant IDs
No PII, video, or audio recordings


## Citation

If you use this dataset, please cite:

```
 Sanson J., Shah R., Frascolla V. (2026).
Human Presence Detection via Wi-Fi Range-Filtered Doppler Spectrum on Commodity Laptops.
IEEE PerCom 2026 — WiSense Workshop.
DOI: https://zenodo.org/records/18594750
```
