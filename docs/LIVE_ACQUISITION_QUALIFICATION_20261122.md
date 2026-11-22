# Live CSI acquisition qualification - 2026-11-22 16:51 IST

## Verdict

**PASS: the corrected L-LTF extractor achieved 50/50 strict-quality CSI on a fresh physical RTL8821CE capture run.** This validates live CSI acquisition for this particular adapter/AP/channel/configuration. It does not validate human-presence classification.

## Capture configuration

- Adapter: Realtek RTL8821CE 1T1R, PCI `0000:01:00.0`
- Interface: `wlp1s0`
- AP: Galaxy M14 hotspot, BSSID `36:9f:61:c1:00:9f`
- Channel: 149, 20 MHz, 5745 MHz
- Trigger: CCA, trigger-time 20 us
- Sample rate: 20 Msps; 8192 samples per capture
- Requested captures: 50
- Capture interval configured: 0 ms
- Artifact directory: `/tmp/rtl8821ce-la.OyG1b1`

## Acquisition results

| Metric | Result | Gate | Outcome |
|---|---:|---:|---|
| Structurally captured IQ buffers | 50/50 | 50 requested | PASS |
| Strict CSI captures | 50/50 (100%) | >=80% | PASS |
| Finite active tones | 52 per capture | exactly 52 | PASS |
| RX-idle barriers | 50/50 (100%) | >=90% | PASS |
| Post-arm target-source heuristic matches | 50/50 (100%) | >=90% | PASS |
| High-confidence target-attributed CSI | 50/50 (100%) | >=80% | PASS |
| Failed CSI captures | 0 | 0 preferred | PASS |

Quality metrics across the 50 accepted captures:

| Metric | Minimum | Median | Maximum | Required |
|---|---:|---:|---:|---:|
| Repeated L-LTF correlation | 0.99589 | 0.99736 | 0.99907 | >=0.85 |
| STF16 correlation | 0.05995 | 0.06428 | 0.07191 | <=0.50 |
| L-LTF symbol relative error | 0.01959 | 0.02322 | 0.03072 | <=0.25 |

All 50 captures were accepted through the lag-candidate path. Median capture-start spacing was 131.001 ms. The detector reported `ABSENT`, `raw_signal=CLEAR`, anomaly `0.16/0.80 dB`, and 50/50 valid CSI in this one-shot batch. This is only the detector's output relative to its existing baseline; no independently recorded room-occupancy ground truth was attached to this acquisition run.

## Attribution limitation

The 50/50 AP matches are from the existing post-arm first-good-RX-callback heuristic. CCA/CRCOK triggers are not hardware source-MAC filtered, and RX callback timing can differ slightly from over-the-air trigger timing. Treat this as strong audit evidence, not hardware-level packet identity.

## Baseline and safety

The command used `--skip-calibration`; the saved baseline was not rewritten. Its SHA-256 after the run is:

`2c00f530172d3849dcf7f54a3cf557821845742a7e7b1d2f2b4982cde5084d74`

The capture script restored PCI device `0000:01:00.0` to `rtw_8821ce` successfully.

## Interpretation and next work

This fresh physical result confirms the offline L-LTF alignment correction works on live hardware and clears the acquisition-yield blocker for this setup. It does **not** establish that CSI distinguishes a stationary person from an empty room. The previous five-round labelled experiment still has poor, unstable held-out-round classification, and the single-session data remain vulnerable to temporal/link drift.

Next, preserve this run as an acquisition qualification reference. Do not train/deploy the exploratory classifier or change CSI thresholds. The next experiment should collect independently repeated, interleaved ABSENT/PRESENT sessions on separate time blocks/days with fixed AP/laptop placement and unchanged hotspot/power settings. Keep each whole session held out during evaluation. First verify the existing dataset analysis and session protocol, then collect one additional controlled session; do not treat acquisition-only captures as labelled occupancy data.

## Artifacts

- `/tmp/rtl8821ce-la.OyG1b1/run_manifest.json`
- `/tmp/rtl8821ce-la.OyG1b1/presence_audit.json`
- `/tmp/rtl8821ce-la.OyG1b1/presence_audit.csv`
- `/tmp/rtl8821ce-la.OyG1b1/csi_series.jsonl.diagnostics.json`
- `/tmp/rtl8821ce-la.OyG1b1/csi_series.jsonl`
- `/tmp/rtl8821ce-la.OyG1b1/rxdemo.log`
