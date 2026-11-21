# RTL8821CE repeated CSI acquisition

## Status

- Confirmed once on target hardware: 8,192 raw IQ samples at 20 Msps, RTL8821C cut 4 (UMC), L-LTF detection, 52 active-subcarrier H(k) magnitude/phase estimates.
- Implemented: sequential capture/re-arm in one `rxdemo` process; each capture gets a distinct DVLA file; successful capture events include monotonic process uptime; graceful stop after the configured count; per-capture CSI extraction into a combined JSONL.
- Software validation: `rxdemo` builds; `LaCaptureSequenceSelftest` passes; `la_csi_math` passes.
- Pending: one local hardware run of the repeated sequence. No remote VFIO bind or Wi-Fi disruption has been performed for this stage.

## Run

From the project root, at the physical console of the laptop:

```bash
sudo bash tools/rtl8821ce_pcie_la_capture.sh
```

The current channel is auto-detected from `wlp1s0` before binding. Defaults are 10 captures, 1,000 ms between captures, and a 120-second overall deadline. The adapter is temporarily detached from `rtw_8821ce` while VFIO owns it, so Wi-Fi is unavailable during the run. The script does not restart NetworkManager or reboot. Its exit trap restores `rtw_8821ce` and, when invoked through sudo, transfers the result directory back to the invoking user.

Optional environment settings:

- `WIFI_PRESENCE_CAPTURE_COUNT`: 2–50 captures (default 10).
- `WIFI_PRESENCE_CAPTURE_INTERVAL_MS`: 100–10,000 ms (default 1,000).
- `WIFI_PRESENCE_CAPTURE_TIMEOUT_SEC`: overall acquisition deadline (default 120).

## Outputs

The script creates `/tmp/rtl8821ce-la.*` containing:

- `capture.NNNN.bin`: distinct DVLA raw IQ capture per successful acquisition.
- `rxdemo.log`: JSON event log; each successful `la.capture` event has a monotonic `t` timestamp and the corresponding output path.
- `csi_series.jsonl`: one record per active subcarrier per valid capture, including capture index, file timestamp, monotonic event time, tone, magnitude, dB magnitude, phase, L-LTF offset, CFO, and sample rate.

A CSI series is accepted only if at least two captures yield an L-LTF and finite H(k) values. A raw IQ capture without an L-LTF is retained but does not count as a valid CSI time point.

## Interpretation boundary

The first hardware capture proves that H(k) can be extracted from this adapter. A repeated dataset will establish whether sequential estimates are stable enough for temporal features. It will not, by itself, prove presence detection or people counting. RTL8821CE is 1T1R; multi-person counting remains a separate, difficult validation problem.
