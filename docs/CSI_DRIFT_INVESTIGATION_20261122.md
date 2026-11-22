# CSI drift and received-signal-level investigation - 2026-11-22

## Verdict

The live detector's current anomaly score is dominated by a large, nearly linear magnitude slope across subcarriers. That slope changed sharply between consecutive capture runs and is strongly associated with received beacon level and estimated L-LTF signal-to-pre-LTF-noise ratio. The empty and occupied smoke-test batches share the same slope and almost the same CSI profile. The evidence supports a radio/link-state or channel-response drift confound, not an occupancy-specific response. The physical cause is not established.

**Do not change the presence threshold, claim detection, or replace the saved baseline based on this analysis.**

## Data used

The saved baseline has 40 profiles and was created at `2026-11-22T04:25:10Z` for AP `36:9f:61:c1:00:9f`, channel 149. Its original per-capture CSI and RX metadata were not retained, so its historical RSSI, CFO, L-LTF start, and signal/noise levels cannot be reconstructed. Its stored median profile has a linear spectral slope of **+0.00961 dB/tone**.

Four subsequent runs supplied 90 strict, AP-attributed profiles in total. All used the same BSSID, channel 149, CCA/t20, and 20 Msps / 8192-sample configuration:

| Run | Ground-truth label | Strict AP-attributed CSI | Median RX RSSI index | Median CSI mean (dB) | Median tone spread (dB) | Median spectral slope (dB/tone) | Raw anomaly (dB) | Detrended anomaly (dB) | L-LTF/pre-LTF RMS proxy (dB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `session_20261122_hotspot_t20_1523` | Unlabelled acquisition run | 30/50 | 68 | 67.214 | 0.560 | +0.0053 | 0.264 | 0.257 | 11.31 |
| `rtl8821ce-la.Ziz8ZT` | Unlabelled intermediate run | 20/50 | 66.5 | 65.961 | 0.924 | -0.0463 | 0.894 | 0.220 | 9.86 |
| `rtl8821ce-la.yfEH1O` | Empty room | 25/50 | 66 | 65.387 | 0.882 | -0.0425 | 0.831 | 0.195 | 9.59 |
| `rtl8821ce-la.3nNS7t` | Occupied, user stationary | 15/50 | 65 | 64.733 | 0.914 | -0.0458 | 0.884 | 0.199 | 8.96 |

The first run is the same capture data preserved in `data/presence_dataset_raw/session_20261122_hotspot_t20_1523/`; it is not counted twice. The intermediate run has no reliable occupancy label. The empty/occupied labels apply only to the final two runs.

All 90 accepted profiles were associated by the existing post-arm RX-frame heuristic. The matched frames were AP beacons (`fc0=0x80`) at rate code 4. The first run contained both 227-byte and 235-byte beacon frames; the later runs contained 227-byte beacons. The first run's mixed beacon lengths do not explain its low anomaly by themselves: the two lengths occurred within that same low-anomaly run.

## Received signal and noise proxy

Raw IQ was decoded using the existing `qi12_l` layout. For each accepted capture, the pre-LTF RMS window ends 200 samples before the detected L-LTF start, leaving a margin before the expected 160-sample L-STF. The L-LTF signal RMS uses the 128 samples covering the two L-LTF symbols.

| Run | Pre-LTF RMS median | L-LTF RMS median | L-LTF / pre-LTF ratio |
|---|---:|---:|---:|
| Earlier unlabelled run | 70.80 | 259.87 | 11.31 dB |
| Intermediate unlabelled run | 69.72 | 226.46 | 9.86 dB |
| Empty smoke test | 69.97 | 211.87 | 9.59 dB |
| Occupied smoke test | 69.88 | 197.27 | 8.96 dB |

The pre-LTF level remains near 70 RMS while L-LTF signal RMS falls from about 260 to 197. There was no observed IQ clipping. This is an uncalibrated signal-to-noise proxy, not a calibrated RF SNR measurement. Together with the falling RX RSSI index and CSI mean magnitude, it shows that the received signal weakened while the pre-LTF floor remained broadly stable. It does not identify why: AP transmit-power behavior, propagation changes, multipath, device state, or other environmental factors remain possible.

## Why the anomaly score fires

Across the 90 strict profiles, descriptive correlations were:

| Pair | Pearson r |
|---|---:|
| RX RSSI index vs CSI mean magnitude | +0.965 |
| RX RSSI index vs per-tone spread | -0.806 |
| RX RSSI index vs spectral slope | +0.810 |
| Per-tone spread vs spectral slope | -0.984 |
| Raw anomaly vs per-tone spread | +0.989 |
| Raw anomaly vs spectral slope | -0.996 |
| L-LTF/pre-LTF RMS proxy vs raw anomaly | -0.793 |

These are run-order-confounded observations, not causal estimates. Nevertheless, the raw anomaly is almost perfectly correlated with the magnitude slope/tone spread in these captures. The detector subtracts each profile's median gain, but it does not remove a frequency-dependent linear tilt. A change in received level and resulting CSI shape therefore appears as a large anomaly even when the room is empty.

The raw median-profile distance between the empty and occupied smoke-test batches is 0.0802 dB RMS. After removing a linear slope from each profile, their median-profile distance is still only 0.0765 dB RMS. Both batches have almost the same slope and the same frequency-shaped shift. There is no useful empty/occupied separation in this pair.

## Linear detrending experiment

Linear magnitude detrending was applied offline only. It removes the best-fit straight-line slope across the 52 active tones and re-centers the residual. It does not change stored data or the live detector's state decision.

The empty and occupied batches' median anomaly distances from the saved baseline fall from 0.831 / 0.884 dB to 0.195 / 0.199 dB. This shows that most of the current threshold crossing is carried by the spectral slope. It does **not** validate detrending as a presence feature or justify using the old 0.80 dB threshold on detrended profiles.

The historical labelled session gives a strong warning against treating slope as presence:

| Phase | Profiles | Median per-profile slope (dB/tone) |
|---|---:|---:|
| Initial ABSENT | 38 | -0.00113 |
| PRESENT | 45 | -0.02964 |
| Final ABSENT | 33 | -0.02697 |

The slope changed between initial ABSENT and PRESENT, but remained shifted after the user left. The phase-median profile distances were:

| Comparison | Raw | After linear detrending |
|---|---:|---:|
| PRESENT vs initial ABSENT | 0.4578 dB | 0.1233 dB |
| PRESENT vs final ABSENT | 0.0599 dB | 0.0432 dB |
| Initial vs final ABSENT | 0.4161 dB | 0.1184 dB |

Using the initial-ABSENT residual median as a reference, the scalar detrended residual-distance AUC for PRESENT vs final ABSENT is **0.565** in this one ordered session. This is descriptive only and not a held-out evaluation. It indicates that removing the slope also removes most of the apparent separation between PRESENT and the final empty-room phase.

Therefore, linear detrending is currently a useful nuisance diagnostic, not a proven replacement feature. It could suppress false triggers, but it could also suppress a real presence effect if that effect appears as a similar spectral tilt.

## Engineering changes made

1. Added `tools/analyze_live_presence_drift.py`. It replays strict CSI gates and reports per-capture spectral slope, raw and detrended anomaly, RX RSSI index, CSI level/spread, CFO, L-LTF start, RX frame length/rate, and raw-IQ signal/noise proxies. It emits CSV and JSON. It explicitly does not classify occupancy.
2. Saved analysis outputs under `data/presence_analysis/live_drift_20261122.csv` and `.json`.
3. Added `profile_shape_diagnostics()` to `tools/live_presence_detector.py`. Live output includes current spectral slope and tone spread alongside channel-anomaly diagnostics. After development-session cross-validation failed, the live tool was hardened to always report `UNKNOWN_UNVALIDATED` for occupancy; no anomaly score affects a PRESENT/ABSENT state.
4. New baselines created by future explicit calibration will record schema version 2 and calibration distributions for spectral slope and tone spread. The existing baseline file was not edited or replaced; its slope reference is derived from its stored median profile because its original per-capture calibration profiles are unavailable.
5. Added unit tests for the analysis functions and live shape diagnostics.

## Current next step

No immediate hardware capture is justified. The next experiment should first establish whether the signal-level change can be reproduced or controlled independently of occupancy. Before designing that test, verify the hotspot's power-management/battery-saver state and whether any hotspot/network setting changed during the capture period. Keep the phone, laptop, channel, and room geometry fixed; do not recalibrate or overwrite the saved baseline until a new baseline is deliberately collected and archived.

Keep strict CSI quality gates unchanged. Do not claim sensitivity, specificity, false alarms/hour, or detection latency. The prototype is not a safety/security detector.

## Reproduction

```bash
vendor/.venv/bin/python tools/analyze_live_presence_drift.py \
  --runs data/presence_dataset_raw/session_20261122_hotspot_t20_1523 \
        /path/to/intermediate-run /path/to/empty-run /path/to/occupied-run \
  --output-prefix data/presence_analysis/live_drift_20261122
```

The tool requires each run directory to contain `csi_series.jsonl`, `presence_audit.csv`, `run_manifest.json`, `rxdemo.log`, and the corresponding `capture.NNNN.bin` files. Missing IQ files leave the IQ metrics unavailable but do not relax CSI validation.
