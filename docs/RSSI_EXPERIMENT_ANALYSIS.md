# Normal-driver Wi-Fi RSSI experiment analysis

**Date:** 2026-11-22
**Purpose:** Evaluate whether connected-AP RSSI metadata can distinguish a stationary occupied room from an empty room in the current laptop/AP setup.

## Datasets

| Dataset | Samples | Blocks | Source | BSSID | Frequency |
|---|---:|---:|---|---|---|
| `data/presence_dataset_rssi/rssi_20261122_113921.csv` | 150 | 5 x 30 s | `iw` | `36:9f:61:c1:00:9f` | not recorded |
| `data/presence_dataset_rssi/rssi_20261122_115530.csv` | 150 | 5 x 30 s | `iw_link` | `36:9f:61:c1:00:9f` | 5745 MHz |

Both sessions used the sequence ABSENT -> PRESENT -> ABSENT -> PRESENT -> ABSENT. Both have 150 rows, no recorded sampling errors, and the same BSSID. Experiment 1 contains one invalid `0 dBm` sentinel; it is excluded from numerical summaries. Experiment 2 has no invalid instantaneous RSSI values. Do not assume the two runs have comparable calibration: their RSSI baselines differ by about 16 dB, and the first run did not record frequency.

## Experiment 1: instantaneous RSSI

| Block | Label | Median RSSI |
|---:|---|---:|
| 1 | ABSENT | -50 dBm |
| 2 | PRESENT | -51 dBm |
| 3 | ABSENT | -50 dBm |
| 4 | PRESENT | -49 dBm |
| 5 | ABSENT | -38 dBm |

The final empty-room block shifted approximately 12 dB above the first empty-room block. The occupied blocks do not show a consistent separation from the first two empty blocks. The final empty block demonstrates substantial time/order drift or a measurement-condition change. This session does not establish an occupancy effect.

## Experiment 2: enhanced normal-driver metadata

Block medians (dBm):

| Block | Label | Instant RSSI (`signal_dbm`) | Station average (`station_signal_avg_dbm`) | Beacon average (`beacon_signal_avg_dbm`) |
|---:|---|---:|---:|---:|
| 1 | ABSENT | -34 | -34 | -34 |
| 2 | PRESENT | -34 | -33.5 | -33 |
| 3 | ABSENT | -34 | -33 | -33 |
| 4 | PRESENT | -34 | -33 | -33 |
| 5 | ABSENT | -34 | -34 | -33 |

Across all rows, instantaneous RSSI median was -34 dBm for both labels. Station-average median was -33.0 dBm for PRESENT and -34.0 dBm for ABSENT, but the block sequence is not a repeatable occupancy signature: the third ABSENT block has the same median as the PRESENT blocks, and the beacon average is -33 dBm in four of the five blocks. Beacon average was -33 dBm for all 60 PRESENT samples and for 60 of 90 ABSENT samples; the remaining 30 ABSENT samples were -34 dBm. The one-dB quantization and overlap make this unsuitable as a reliable threshold.

Experiment 2's all-row summaries:

| Metric | ABSENT median (n=90) | PRESENT median (n=60) | Interpretation |
|---|---:|---:|---|
| Instant RSSI | -34 dBm | -34 dBm | No separation |
| Station signal average | -34 dBm | -33 dBm | Small shift, but overlaps and does not track each transition reliably |
| Beacon signal average | -33 dBm | -33 dBm | No median separation |

## Engineering conclusion

**Do not implement or train an RSSI-only presence classifier from these data.** The first run is confounded by a large final-block drift. The second run is more stable but its instantaneous and beacon RSSI measurements do not separate occupied and empty states. Station-average RSSI has a small one-dB difference in pooled medians, but the block sequence and overlap do not support a robust detector. In addition, the approximately 16 dB baseline change between runs means that a fixed threshold would be especially brittle.

The RSSI collector remains useful as a lightweight diagnostic and can be retained. Do not spend more project time tuning a threshold against these two sessions. Return priority to the existing CSI/raw-IQ path, where channel-response features may be more sensitive to multipath changes than the driver's quantized link RSSI. Preserve all original CSVs.

## Limitations

- Only one room, laptop position, AP, and date were tested.
- Each state block contains 30 seconds; samples within a block are temporally correlated, not 30 independent room trials.
- The same BSSID was used, but Experiment 1 did not record frequency and the run-to-run RSSI baseline changed substantially.
- The stationary subject position and exact environment were not independently instrumented.
- These experiments reject this simple RSSI approach for the current setup; they do not prove that all Wi-Fi sensing or all RSSI-based setups are impossible.
- This is not a validated detector and must not be used for safety/security monitoring.
