# RTL8821CE Wi-Fi Presence Sensing: Physical Capture Runbook

**Updated: 2026-11-22**

## Purpose

Collect independent, labelled, interleaved CSI sessions to test whether stationary human presence produces a repeatable signal distinguishable from empty-room variation and link drift. Acquisition quality is now qualified; presence classification is not.

## Hardware and capture facts

- Adapter: Realtek RTL8821CE, 1T1R, PCI `10ec:c821`, driver `rtw_8821ce`, commonly `wlp1s0`.
- Capture: PCIe/VFIO LA mode, 20 MHz, 20 Msps, 8192 complex samples (409.6 us), legacy L-LTF, 52 active tones.
- Current trigger: CCA, the early-frame trigger. Realtek selector mapping: CCA=0, CRCOK=1, CRCFAIL=2.
- `t<us>` configures the MAC LA trigger-time register. It does not set IQ sample count or buffer duration.
- VFIO temporarily detaches the Wi-Fi adapter and interrupts connectivity. **Run all physical capture only at the laptop's physical console. Never run through SSH or a remote coding agent.**
- AP source attribution is a post-arm RX-callback heuristic with address checks and RX-idle barrier, not hardware source-MAC filtering or an exact packet-to-IQ join.

## Strict CSI acceptance gates

- Exactly 52 finite active tones.
- Repeated L-LTF correlation >= 0.85.
- STF16 correlation <= 0.50.
- L-LTF symbol relative error <= 0.25.
- Target-source audit match.
- RX-idle barrier.

Do not relax these gates. Insufficient CSI is `UNKNOWN` / `INSUFFICIENT_CSI`, never `ABSENT`.

## Before the next collection

1. Confirm Galaxy M14 battery saver, hotspot power-saving, and hotspot/network settings are unchanged from the qualified setup. Freeze them for all remaining sessions.
2. Keep laptop and phone in the same marked positions and orientations. Keep the channel, room layout, furniture, doors, and windows unchanged.
3. Use the same stationary person position, posture, and orientation in every PRESENT block.
4. Do not stream, download, or deliberately generate traffic. Keep other people out of the monitored room.
5. Capture sessions on separate days/time blocks where practical.

## Collect one session

From the laptop's physical console:

```bash
cd ~/projects/iot-project
sudo vendor/.venv/bin/python tools/collect_presence_interleaved.py
```

The collector runs five paired rounds, alternating condition order:

- Round 1: ABSENT, PRESENT
- Round 2: PRESENT, ABSENT
- Round 3: ABSENT, PRESENT
- Round 4: PRESENT, ABSENT
- Round 5: ABSENT, PRESENT

Each condition is one batch of 50 capture attempts with 30 seconds settling. Total: 10 batches, 500 attempts, 300 seconds of settling, plus capture/reconnection time.

**ABSENT:** no person in the monitored room. Stay at least 5 m from both laptop and AP, preferably behind a closed door. Keep other people out too.

**PRESENT:** one person at the same marked position, posture, and orientation for all five rounds. Remain still during settling and capture.

Follow each prompt exactly. At completion, save the printed JSONL path and terminal summary. Raw IQ, RX logs, CSI series, audits, manifests, and diagnostics are archived under the matching `data/presence_dataset_raw/interleaved_.../` directory. Do not delete, rename, or overwrite the original or raw archive.

Repeat for three new independent sessions, ideally on separate days/time blocks. Existing 2026-11-22 session plus new sessions 1 and 2 are development data. New session 3 is reserved untouched for the final held-out evaluation.

## Offline analysis

No VFIO or adapter disruption is needed for analysis:

```bash
vendor/.venv/bin/python tools/analyze_interleaved_presence.py \
  data/presence_dataset/interleaved_YYYYMMDD_HHMMSS.jsonl
```

The offline reprocessor, if needed, writes a separate output and refuses to overwrite:

```bash
vendor/.venv/bin/python tools/reprocess_presence_archives.py --help
```

Return the exact JSONL path and terminal summary after each session. Preserve the matching raw archive.

## Existing evidence and interpretation

The 2026-11-22 five-round session yielded 497/500 strict CSI after the L-LTF alignment correction, 495/500 target-attributed strict CSI, RX-idle 500/500, and 10/10 acquisition-gate-passing batches. However, grouped-by-round classification was unstable: best RBF SVM balanced accuracy 0.675 and sensitivity 0.565. This is not deployable or independently validated. See `LIVE_ACQUISITION_QUALIFICATION_20261122.md`, `LTF_ALIGNMENT_RECOVERY_20261122.md`, and `PRESENCE_CLASSIFIER_READINESS_20261122.md`.

## Integrity and safety

- Never overwrite `data/live_presence_baseline.json`.
- Keep baseline, labelled data, raw IQ archives, and private analysis outputs out of GitHub.
- Never lower strict CSI gates to increase yield.
- Never interpret insufficient CSI as absence.
- Do not claim accuracy until the complete algorithm is frozen and evaluated on the untouched independent session.
- This academic prototype must not be used as a safety/security alarm.
