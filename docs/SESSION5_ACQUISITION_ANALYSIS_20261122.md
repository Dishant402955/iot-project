# Session 5 acquisition and descriptive analysis

**Collected:** 2026-11-22 20:24 local time (session identifier `interleaved_20261122_202430`)
**Role:** Development data; not held-out evaluation.

## Acquisition result

The five-round interleaved collector completed all ten batches: five ABSENT and five PRESENT, with 50 attempts per batch (500 attempts total). All ten batches passed both configured acquisition gates. RX-idle was satisfied for all 500 attempts.

| Measure | Result |
|---|---:|
| Capture attempts | 500 |
| Strict structural CSI profiles | 498/500 (99.6%) |
| Target-attributed strict CSI profiles retained in dataset | 492/500 (98.4%) |
| ABSENT retained profiles | 246/250 |
| PRESENT retained profiles | 246/250 |
| Post-arm target-source matches | 494/500 (98.8%) |
| RX-idle barrier | 500/500 (100%) |
| Batches passing both acquisition gates | 10/10 |
| Channel / bandwidth | 149 / 20 MHz |

The distinction between structural CSI and target-attributed CSI matters: six attempts had strict structural CSI but were not retained as target-attributed profiles. The 492 retained feature profiles comprise 246 ABSENT and 246 PRESENT. The shortfalls occurred in PRESENT rounds 1, 4 and 5 (49, 49 and 48 profiles) and ABSENT rounds 2 and 3 (48 profiles each). All affected batches still passed the configured acquisition gates. No profiles were fabricated or imputed. The RX-idle barrier passed in every attempt. The collector restored the adapter to the `rtw_8821ce` kernel driver after every batch. The saved empty-room baseline was not modified.

### Per-round profile counts and descriptive distance

| Round | ABSENT profiles | PRESENT profiles | Median-profile distance (dB RMS) |
|---:|---:|---:|---:|
| 1 | 50 | 49 | 0.2185 |
| 2 | 48 | 50 | 0.2948 |
| 3 | 48 | 50 | 0.2981 |
| 4 | 50 | 49 | 0.2189 |
| 5 | 50 | 48 | 0.2118 |

## Descriptive profile comparison

The analyzer reported an aggregate ABSENT/PRESENT median feature-profile distance of **0.2137 dB RMS** across 246 profiles per condition. This is a descriptive within-session feature-space comparison only. It is not classification accuracy, evidence of stable occupancy separability, or cross-session generalization. The per-round distances vary, so do not derive or tune a decision threshold from this one session.

## Data integrity and publication

- Original labelled JSONL: `data/presence_dataset/interleaved_20261122_202430.jsonl`
- Original JSONL SHA-256: `43dce1a015e5291de578d1c9128f51bf130a74ef9c0c9fbba81fa3419e5156db`
- Anonymized public copy: `data/public_dataset/interleaved_session_5_anonymized.jsonl`
- Public copy SHA-256: `829f7050794d24a27fffd6f0e0c332989ea1e6fccb46040e522c29f7a9a045e1`
- The public copy passed scans for the actual AP BSSID, local home/tmp paths, exact wall-clock timestamps, raw archive paths and capture-run paths. JSONL schema validation passed.
- Raw archive directory exists at `data/presence_dataset_raw/interleaved_20261122_202430`; its protected contents and off-device backup have not been verified by this software pass.

The anonymized feature copy excludes BSSID, exact wall-clock timestamps and local paths. Raw IQ and original labelled JSONL remain private and must not be committed. Session 5 joins Sessions 1, 2 and 4 as development data. Session 3 remains the already-consumed one-time held-out evaluation and must not be used for further development or tuning.
