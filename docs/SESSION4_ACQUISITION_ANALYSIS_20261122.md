# Session 4 acquisition and descriptive analysis

**Collected:** 2026-11-22 20:06 local time (session identifier `interleaved_20261122_200618`)
**Role:** Development data; not held-out evaluation.

## Acquisition result

The five-round interleaved collector completed all ten batches: five ABSENT and five PRESENT, with 50 attempts per batch (500 attempts total). All ten batches passed both configured acquisition gates. RX-idle was satisfied for all 500 attempts.

| Measure | Result |
|---|---:|
| Attempts | 500 |
| Strict CSI profiles | 498/500 (99.6%) |
| ABSENT strict profiles | 248/250 |
| PRESENT strict profiles | 250/250 |
| Target-attributed strict CSI | 498/500 (99.6%) |
| RX-idle barrier | 500/500 (100%) |
| Batches passing both acquisition gates | 10/10 |
| Channel / bandwidth | 149 / 20 MHz |

ABSENT rounds 1 and 5 each produced 49/50 strict CSI profiles. Both batches passed the configured gates. The two missing profiles were not imputed. The collector restored the adapter to the `rtw_8821ce` kernel driver after each batch. The session did not modify the saved empty-room baseline.

## Descriptive profile comparison

The session analyzer reported 248 ABSENT and 250 PRESENT feature profiles. The RMS distance between the two aggregate per-tone median profiles was **0.1707 dB**. Per-round median-profile distances were:

| Round | ABSENT profiles | PRESENT profiles | Median-profile distance (dB RMS) |
|---:|---:|---:|---:|
| 1 | 49 | 50 | 0.4479 |
| 2 | 50 | 50 | 0.2268 |
| 3 | 50 | 50 | 0.2255 |
| 4 | 50 | 50 | 0.2315 |
| 5 | 49 | 50 | 0.0938 |

These are descriptive feature-space comparisons only. Their variation across rounds is a reminder that a single-session distance does not establish a stable occupancy signal, detector accuracy, or cross-session generalization. Do not tune a threshold from this summary. Session 4 should be combined with Sessions 1, 2 and 5 in grouped development analysis, while Session 3 remains excluded from all further development.

## Data integrity and publication

- Original labelled JSONL: `data/presence_dataset/interleaved_20261122_200618.jsonl`
- Original JSONL SHA-256: `15fb6d54295d945ab7e64cb5dd64009d33be9afac74f701e8e70713f76d44eca`
- Anonymized public copy: `data/public_dataset/interleaved_session_4_anonymized.jsonl`
- Public copy SHA-256: `fb479cf36cdf83d4a12f9b8db1b97a68bcb90935fa69076b4601b32b205eb3eb`
- The public copy passed a scan for the AP BSSID, local home/tmp paths, and exact wall-clock timestamps.
- Raw archive directory exists at `data/presence_dataset_raw/interleaved_20261122_200618`; its protected contents and off-device backup have not been verified by this software pass.

The anonymized feature copy excludes BSSID, exact wall-clock timestamps and local paths. Raw IQ and original labelled JSONL remain private and must not be committed.
