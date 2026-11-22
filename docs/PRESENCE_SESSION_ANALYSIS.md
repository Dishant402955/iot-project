# Controlled Presence Session Analysis

- Session: data/presence_dataset/session_20261122_111025.jsonl
- Collection date: 2026-11-22
- AP: 36:9f:61:c1:00:9f, channel 149
- Labels: ABSENT -> PRESENT -> ABSENT
- Dataset: 9 labelled batches, 450 capture attempts, 116 accepted CSI profiles (25.8%).
- All 116 stored profiles have shape 52 tones and finite values. All nine raw capture directories and their audit/series files were present at analysis time and archived under data/presence_dataset_raw/session_20261122_111025 (34 MB, 504 files).

## Acquisition summary

| Phase | Accepted CSI | Attempts | Yield |
|---|---:|---:|---:|
| First ABSENT | 38 | 150 | 25.3% |
| PRESENT | 45 | 150 | 30.0% |
| Final ABSENT | 33 | 150 | 22.0% |
| Total | 116 | 450 | 25.8% |

RX-idle barrier was satisfied for 450/450 captures. The post-arm target-source heuristic matched 448/450 captures (one mismatch in final ABSENT batch 2). This remains a software heuristic, not hardware BSSID filtering. Every batch failed the predeclared 80% CSI-yield gate. Do not treat the dataset as acquisition-qualified.

## Preliminary signal comparison

Each accepted profile is a 52-tone per-profile centered dB magnitude vector. The following distances are RMS distances between phase-wise per-tone median profiles:

| Comparison | RMS distance |
|---|---:|
| PRESENT vs first ABSENT | 0.4578 dB |
| PRESENT vs final ABSENT | 0.0599 dB |
| First ABSENT vs final ABSENT | 0.4161 dB |

Within-phase batch-centroid distances are much smaller (roughly 0.05-0.12 dB for most pairs) than the large first-ABSENT to later-phase shift. The occupied phase is close to final ABSENT, not clearly separated from it. This is strong evidence of temporal/environmental or measurement drift confounding the apparent first-ABSENT/PRESENT difference. It is NOT evidence that presence has no effect; it means this single ordered session cannot isolate a presence effect.

Per-phase profile RMS medians: first ABSENT 0.6008 dB, PRESENT 0.7487 dB, final ABSENT 0.7130 dB. These are descriptive only, not classifier metrics.

## Verdict

- Dataset collection completed and labels/order are present.
- Acquisition yield is poor: 25.8% overall vs 80% predeclared gate.
- No presence detector has been validated.
- The main experimental issue is confounding drift: the first and final empty-room phases differ substantially, while PRESENT is close to final ABSENT.
- Do not train or tune a detector on this session as though labels cleanly represent a presence-only effect. Do not overwrite data/live_presence_baseline.json.

## Next engineering work

1. Inspect per-capture diagnostics and acquisition timing to identify why strict L-LTF yield is only 22-40% per batch; preserve strict quality gates.
2. Investigate time-varying CSI shape and nuisance variables (CFO, L-LTF start offset, AP traffic, capture spacing) without assuming any one is causal.
3. Design a repeat experiment that reduces time/order confounding: interleave short ABSENT/PRESENT intervals or repeat ABBA/BAAB blocks, with the laptop/AP fixed and clearly recorded labels. Capture repeated sessions, not just more batches in one session.
4. Only after stable acquisition and repeatable occupied-vs-empty separation, build a detector and evaluate on held-out sessions.

## Batch evidence

Accepted profiles by batch: ABSENT 9/50, 12/50, 17/50; PRESENT 20/50, 15/50, 10/50; final ABSENT 13/50, 8/50, 12/50. Original run directories are recorded in the JSONL; preserved copies are under data/presence_dataset_raw/session_20261122_111025.

## Strict-L-LTF rejection diagnostics

The archived per-capture diagnostics cover all 450 attempts: 117 were accepted by the CSI series extractor (the JSONL collector stores 116 labelled profiles; the audit/series-level count differs by one in a single final-ABSENT batch, which is retained as an audit discrepancy). Across all captures, the median best candidate repeated-symbol correlation was 0.6515; only 117/450 passed the full strict L-LTF path. The fallback's median best repeated-symbol correlation was 0.5077 among captures where fallback ran. Most failures were rejected at the repeated-symbol check, before STF16 and symbol-error checks could be meaningful.

The capture script used CCA with the MAC LA trigger-time register set to 20 us. The `t<us>` field does not set the sample count: archived `t20` and `t200` captures both contain 8192 complex samples (409.6 us at 20 Msps). The exact timing relationship between this register and the CCA event was not established before the `t200` experiment. Do not relax repeat/STF/symbol quality gates.

There is a minor count discrepancy to reconcile in code/data audit: collector JSONL stores 116 accepted profiles, while archived CSI diagnostics report 117 successful per-capture extractions across nine runs. Keep both source records; do not silently rewrite the labelled dataset.

## 200 us MAC trigger-time acquisition diagnostic (2026-11-22)

A hardware-only follow-up used the same RTL8821CE, AP BSSID `36:9f:61:c1:00:9f`, channel 149 / 20 MHz, CCA trigger, 20 Msps, 50 captures, zero configured inter-capture delay, and `t200`. The run completed all 50 captures and all 50 IQ files passed structural/varying-sample checks. RX-idle was confirmed 50/50 and the post-arm target-source heuristic matched 50/50. The adapter was restored to `rtw_8821ce`.

However, strict CSI extraction was **0/50 (0%)**, versus 117/450 (~26%) in the preceding t20 labelled acquisition session. All 50 failed with `no L-LTF passed strict quality gates`. The fallback detector ran on all captures (42-50 candidates per capture; median 47.5) and rejected every candidate at repeated-symbol coherence. Fallback best repeat correlation had min 0.1914, median **0.2674**, max 0.3321, far below the 0.85 threshold. Median fallback symbol relative error was **0.6055**, above the 0.25 maximum; median fallback STF16 correlation was 0.0879. No accepted CSI profiles were produced.

The `t200` setting produced substantially worse repeated-symbol coherence than the `t20` session, but this was not a longer sample window: both settings returned 8192 samples. The result shows that changing the MAC trigger-time register from 20 to 200 us coincided with poorer L-LTF coherence. Do not switch the default to t200 on this evidence and do not weaken strict quality gates. The IQ capture path and AP/RX audit work, but these captures do not contain a sufficiently coherent L-LTF according to the current extractor. CCA may be triggering on channel activity that is not a suitable legacy OFDM L-LTF frame, or the captured region/alignment may not preserve the repeated symbols. These are hypotheses, not established causes.

The historical run manifest incorrectly called the field `capture_duration_us: 200`; the DVLA headers correctly store it as `trigger_time_us: 200`. Each capture returned 8192 samples and `wrap: 1`. This is a trigger-time setting, not a 200 us sample window.

Raw run artifacts are archived under `data/presence_dataset_raw/session_20261122_t200/rtl8821ce-la.802JPo/` (IQ, CSI series, diagnostics, audit, manifest, and RX log). This was an acquisition-only diagnostic, not a labelled presence experiment; do not add it to the labelled JSONL or update `data/live_presence_baseline.json`.

### Decision after the t200 trigger-time setting

1. Reject the hypothesis that changing the MAC trigger-time setting from 20 to 200 us improves strict CSI yield in the tested setup.
2. Keep the strict repeat/STF/symbol quality gates unchanged.
3. Next inspect capture alignment/trigger semantics and the raw IQ versus RX frame timing to determine whether CCA captures are aligned to an OFDM preamble/L-LTF at all. Prefer a targeted diagnostic using known frame timing or a controlled AP traffic pattern over another blind duration sweep.
4. Do not run another labelled presence session until acquisition produces a useful, repeatable strict-CSI yield.


## Auxiliary AP RSSI evidence and simpler fallback (2026-11-22)

The existing `rxdemo.log` files also contain decoded AP RX-frame RSSI metadata, independent of whether an LA capture yielded CSI. A new offline report (`tools/analyze_presence_rssi.py`) summarizes these values by manually labelled batch:

| Phase / batch | RX frames | RSSI median | Mean | Std. dev. |
|---|---:|---:|---:|---:|
| First ABSENT 1 | 85 | 79 | 78.79 | 1.95 |
| First ABSENT 2 | 87 | 79 | 78.56 | 1.98 |
| First ABSENT 3 | 87 | 79 | 78.62 | 2.42 |
| PRESENT 1 | 85 | 76 | 75.98 | 0.22 |
| PRESENT 2 | 87 | 76 | 75.98 | 0.15 |
| PRESENT 3 | 88 | 76 | 75.95 | 0.21 |
| Final ABSENT 1 | 85 | 76 | 76.27 | 0.44 |
| Final ABSENT 2 | 83 | 76 | 76.40 | 0.49 |
| Final ABSENT 3 | 87 | 76 | 76.31 | 0.46 |

The first empty-room block differs by about 3 RSSI units from both the occupied and final empty-room blocks. Thus this side channel exhibits the same order/time confound as CSI: the apparent change on entering the room does not reverse when the room becomes empty again. It is not evidence of a validated RSSI detector. The separate run with the MAC trigger-time setting at t200 had RSSI median 72, so do not compare its absolute RSSI with the earlier session as if receiver gain and setup were calibrated.

For a semester-project MVP, normal-driver AP RSSI is worth testing as a much simpler sensing path before more CSI hardware work. `tools/collect_wifi_rssi.py` records signal from `iw link`, `/proc/net/wireless`, or a clearly marked NetworkManager cached-scan fallback, without VFIO or Wi-Fi disconnection. Its default experiment interleaves ABSENT/PRESENT/ABSENT/PRESENT/ABSENT blocks to expose drift. The CSV records the source and whether signal is dBm, link quality, or NetworkManager percent; do not mix those units. This remains an experiment, not a detector, until repeated interleaved sessions show reversible, held-out separation.


## Normal-driver RSSI interleaved experiment 1 (2026-11-22)

Raw file: `data/presence_dataset_rssi/rssi_20261122_113921.csv`.

The collector completed all five 30-second blocks and wrote 150 one-second samples. All 150 used `iw` and the same AP BSSID `36:9f:61:c1:00:9f`; there were no command errors. Block summaries for the `iw link` instantaneous `signal` field:

| Block | Label | Samples | Median dBm | Mean dBm | Std. dev. | Range dBm |
|---:|---|---:|---:|---:|---:|---:|
| 1 | ABSENT | 30 | -50 | -50.30 | 0.46 | -51 to -50 |
| 2 | PRESENT | 30 | -51 | -51.43 | 0.92 | -53 to -50 |
| 3 | ABSENT | 30 | -50 | -50.00* | 0.85* | -53 to -50* |
| 4 | PRESENT | 30 | -49 | -48.70 | 0.82 | -51 to -48 |
| 5 | ABSENT | 30 | -38 | -38.20 | 0.65 | -41 to -38 |

*Block 3 has one invalid `0 dBm` sample at elapsed 18 seconds; excluding it gives median -50, mean -50.00, standard deviation about 0.85, range -53 to -50. The raw CSV is unchanged. The `iw`/driver can report 0 dBm as an invalid RSSI sentinel; it must not be interpreted as a real received signal.

Interpretation: blocks 1-4 show only small, inconsistent changes (PRESENT is 1 dB weaker in block 2, then 1 dB stronger in block 4). The final ABSENT block shifts abruptly by roughly +11 to +12 dB, which is much larger than the apparent occupancy differences. The BSSID stayed the same, but BSSID alone does not rule out AP radio/firmware behavior, rate/traffic changes, roaming details, or measurement reporting changes. This experiment does not establish a presence signal and must not be used to train or claim detector accuracy.

A further driver inspection found that `iw dev wlp1s0 link` reports instantaneous `signal`, while `iw dev wlp1s0 station dump` also exposes `signal avg` and `beacon signal avg`. At inspection time the instantaneous field was 0 dBm (invalid), station signal average was -29 dBm, and beacon signal average was -55 dBm. This confirms that the instantaneous field can be unreliable and that the beacon-specific average is a potentially better stable metric to record. It does not retroactively repair the first CSV because those beacon averages were not recorded then.

The collector now records, when available, instantaneous/average station RSSI, beacon RSSI average, AP frequency, and RX/TX bitrate; it filters invalid 0 dBm instantaneous/average values instead of treating them as measurements. This metadata should help distinguish presence effects from AP/radio/link changes in the next run.
