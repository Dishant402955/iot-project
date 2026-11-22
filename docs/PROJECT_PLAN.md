# Wi-Fi presence-sensing project plan

**Current as of 2026-11-22.** This file is the short project overview. For the authoritative status, gates, user actions, and remaining milestones, see [`PROJECT_EXECUTION_PLAN.md`](PROJECT_EXECUTION_PLAN.md). The cross-chat handoff is [`HANDOFF.md`](HANDOFF.md).

## Goal

Evaluate whether the RTL8821CE 1T1R adapter can support a stationary-room binary `PRESENT` / `ABSENT` detector using 52-tone CSI. The system must report `UNKNOWN` / `INSUFFICIENT_CSI` when acquisition or evidence is inadequate. This is an academic prototype, not a safety/security product and not an exact RF-DS reproduction.

## Current result

- Latest physical acquisition qualification: 50/50 strict CSI, 50/50 RX-idle, and 50/50 target-source heuristic matches.
- Five-round interleaved labelled session: 497/500 strict CSI after corrected L-LTF pair alignment; 495/500 target-attributed strict CSI; 10/10 batches passed acquisition gates.
- Classifier readiness: not sufficient. Best grouped-by-round RBF SVM balanced accuracy 0.675 and sensitivity 0.565, with unstable folds. No validated detector claim.
- Strict CSI gates remain unchanged. The empty-room baseline remains local and unchanged.

## Remaining work

1. Confirm and freeze Galaxy M14 battery-saver, hotspot power-saving, and network settings.
2. Collect three independent interleaved physical sessions using `sudo vendor/.venv/bin/python tools/collect_presence_interleaved.py` at the laptop console. Existing session and first two new sessions are development data; third new session is untouched held-out data.
3. Tune a robust detector only on development sessions, with explicit unknown handling and no relaxation of CSI gates.
4. Freeze the full detector, then evaluate once on the held-out session. Report sensitivity, specificity, balanced accuracy, false alarms/hour, missed detections, CSI availability, unknown rate, and entry/exit latency.

Physical capture must never be run remotely because VFIO temporarily detaches the Wi-Fi adapter. Keep room-specific data and baseline out of Git. Never map insufficient CSI to absence. A negative/inconclusive result is preferable to unsupported accuracy claims.
