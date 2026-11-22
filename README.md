# Wi-Fi Stationary Human-Presence Sensing

Academic prototype investigating whether a Realtek RTL8821CE 1T1R adapter can distinguish a stationary person from an empty room using Wi-Fi CSI. The target output is `PRESENT` / `ABSENT`, with `UNKNOWN` / `INSUFFICIENT_CSI` whenever acquisition quality or evidence is inadequate.

**Current verdict (2026-11-22): acquisition is now repeatable in a fresh 50-capture qualification batch, but stationary-presence detection is not validated.** A five-round interleaved dataset has been collected and reprocessed with the corrected L-LTF alignment logic. The acquisition pipeline passed strongly; grouped-by-round classifier results remain unstable and are not suitable for deployment. Independent sessions and an untouched held-out session are still required.

## Clone and build

```bash
git clone https://github.com/Dishant402955/iot-project.git
cd iot-project
./tools/setup_devourer_env.sh
./tools/build_devourer_pcie.sh
```

The isolated Devourer setup downloads build dependencies under `vendor/.local-deps` and creates `vendor/.venv`. It does not install system packages or require sudo. Hardware capture is a separate deliberate physical-console action.

## Latest evidence

- Fresh physical acquisition qualification: 50/50 strict CSI profiles, 50/50 RX-idle barriers, and 50/50 post-arm AP-source heuristic matches. All accepted profiles had 52 finite active tones.
- Five-round interleaved dataset: 500 attempts, 497 strict CSI profiles (99.4%), 495 target-attributed strict CSI profiles (99.0%), 500/500 RX-idle passes, and 10/10 batches passed acquisition gates.
- Corrected L-LTF extraction tests both repeated-symbol pair alignments, fixing a matched-filter peak-selection bug without relaxing the strict signal-quality gates.
- Despite good acquisition, leave-one-round-out evaluation remains unstable. Best reported RBF-SVM balanced accuracy was 0.675 with only 0.565 sensitivity; fold accuracy ranged from 0.500 to 0.939. **Do not deploy or claim validated presence detection.**
- The current live anomaly detector is an experimental indicator relative to an empty-room baseline, not a validated classifier. Insufficient CSI must never be interpreted as `ABSENT`.

Detailed reports: [live acquisition qualification](docs/LIVE_ACQUISITION_QUALIFICATION_20261122.md), [L-LTF alignment recovery](docs/LTF_ALIGNMENT_RECOVERY_20261122.md), [classifier readiness](docs/PRESENCE_CLASSIFIER_READINESS_20261122.md), and [CSI drift investigation](docs/CSI_DRIFT_INVESTIGATION_20261122.md).

## Hardware and acquisition

- Ubuntu 22.04, RTL8821CE PCIe adapter (`10ec:c821`), driver `rtw_8821ce`, interface commonly `wlp1s0`.
- 1T1R, 20 MHz, 20 Msps, 8192 complex samples per capture, legacy L-LTF with 52 active tones.
- Dedicated Galaxy M14 hotspot used in the latest experiment: 5 GHz, channel 149. Tools read current AP identity rather than relying on a hardcoded BSSID.
- Capture temporarily detaches the Wi-Fi adapter through VFIO. **Run hardware capture only from the laptop's physical console**, never through SSH or a remote coding agent.
- CCA is the early-frame trigger. The `t<us>` setting controls the MAC LA trigger-time register, not IQ sample count or buffer duration.
- AP attribution is a post-arm RX-callback heuristic, not hardware source-MAC filtering or proof of exact packet-to-IQ correspondence.

## Strict CSI quality gates

- Exactly 52 finite active tones.
- Repeated L-LTF correlation >= 0.85.
- STF16 correlation <= 0.50.
- L-LTF symbol relative error <= 0.25.
- Target-source audit match and RX-idle barrier.

Do not lower these gates to increase yield. Bad or insufficient CSI maps to unknown/insufficient evidence, never to absence.

## Next milestone

Collect three new independent interleaved sessions with the frozen physical setup. Use the same command for each session, ideally on separate days/time blocks:

```bash
cd ~/projects/iot-project
sudo vendor/.venv/bin/python tools/collect_presence_interleaved.py
```

Each run performs five paired rounds (10 batches, 500 attempts), alternating ABSENT/PRESENT order, with 30-second settling per batch. Keep the laptop, AP, room layout, hotspot settings, and person position/orientation fixed. Record the generated JSONL path and preserve its matching raw archive. The first two new sessions join development data; the third is reserved untouched for final held-out evaluation. The existing 2026-11-22 session is development data.

Before collecting, confirm Galaxy M14 battery saver, hotspot power-saving, and hotspot/network settings are unchanged from the qualified setup. Do not alter the baseline or CSI gates.

After each session, run offline analysis (no VFIO required):

```bash
vendor/.venv/bin/python tools/analyze_interleaved_presence.py data/presence_dataset/interleaved_YYYYMMDD_HHMMSS.jsonl
```

Then provide the exact session JSONL path and terminal summary. The full protocol and current milestones are in [the execution plan](docs/PROJECT_EXECUTION_PLAN.md), [the physical runbook](docs/presence-sensing-runbook.md), and [the handoff](docs/HANDOFF.md).

## Reproducible checks

```bash
cd ~/projects/iot-project
vendor/.venv/bin/python -m unittest discover -s tests -v
vendor/.venv/bin/python vendor/devourer/tools/la_csi.py --selftest
vendor/.venv/bin/python vendor/devourer/tests/la_csi_series_selftest.py
python3 -m compileall -q tools vendor/devourer/tools tests
bash -n tools/rtl8821ce_pcie_la_capture.sh
git diff --check
```

## Scope and limitations

This is an academic experimental system, not a safety/security alarm or production occupancy product. The adapter is 1T1R and the acquisition rate is limited by roughly 130 ms readback time per 8192-sample buffer. It is not an exact reproduction of RF-DS or other multi-antenna, wideband, high-rate CSI systems. A negative/inconclusive experimental result is acceptable; unsupported accuracy claims are not.
