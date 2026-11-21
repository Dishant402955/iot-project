# RTL8821CE repeated CSI acquisition

## Status

- Confirmed once on target hardware: 8,192 raw IQ samples at 20 Msps, RTL8821C cut 4 (UMC), L-LTF detection, 52 active-subcarrier H(k) magnitude/phase estimates.
- Implemented: sequential capture/re-arm in one `rxdemo` process; each capture gets a distinct DVLA file; successful capture events include monotonic process uptime; graceful stop after the configured count; per-capture CSI extraction into a combined JSONL.
- Software validation: `rxdemo` builds; `LaCaptureSequenceSelftest` passes; `la_csi_math` passes.
- Hardware repeated-capture run (2026-11-21): 10/10 distinct 8,192-sample raw IQ captures succeeded and the driver restored. Only 1/10 contained a detectable L-LTF. The run used a CRC-OK (frame-end) trigger with a 409.6 us ring and 20 us post-trigger; this can omit the preamble of longer frames.
- CCA-triggered hardware run (2026-11-21): 10/10 captures completed, but 3/10 IQ buffers were constant and only 1/10 contained a detectable L-LTF. The channel was 2.4 GHz channel 2. CCA can trigger on channel activity that is not an OFDM frame with an L-LTF (for example, legacy CCK traffic), so a successful CCA capture is not necessarily a usable CSI sample.
- Next acquisition keeps the documented CCA `/t200` settings and increases the sequence to 30 captures. This tests whether a longer sample yields enough OFDM/L-LTF frames; it does not assume CCA itself guarantees an L-LTF.

## Run

From the project root, at the physical console of the laptop:

```bash
sudo bash tools/rtl8821ce_pcie_la_capture.sh
```

The current channel is auto-detected from `wlp1s0` before binding. Defaults are CCA-triggered capture with 200 us post-trigger, 30 captures, 1,000 ms between captures, and a 120-second overall deadline. The adapter is temporarily detached from `rtw_8821ce` while VFIO owns it, so Wi-Fi is unavailable during the run. The script does not restart NetworkManager or reboot. Its exit trap restores `rtw_8821ce` and, when invoked through sudo, transfers the result directory back to the invoking user.

Optional environment settings:

- `WIFI_PRESENCE_CAPTURE_COUNT`: 2–50 captures (default 30).
- `WIFI_PRESENCE_CAPTURE_INTERVAL_MS`: 100–10,000 ms (default 1,000).
- `WIFI_PRESENCE_CAPTURE_TIMEOUT_SEC`: overall acquisition deadline (default 120).
- `WIFI_PRESENCE_LA_TRIGGER`: `cca` (default), `crcok`, or `crcfail`.
- `WIFI_PRESENCE_LA_POST_TRIGGER_US`: post-trigger time in microseconds (20–380, default 200).

## Outputs

The script creates `/tmp/rtl8821ce-la.*` containing:

- `capture.NNNN.bin`: distinct DVLA raw IQ capture per successful acquisition.
- `rxdemo.log`: JSON event log; each successful `la.capture` event has a monotonic `t` timestamp and the corresponding output path.
- `csi_series.jsonl`: one record per active subcarrier per valid capture, including capture index, file timestamp, monotonic event time, tone, magnitude, dB magnitude, phase, L-LTF offset, CFO, and sample rate.

A CSI series is accepted only if at least two captures yield an L-LTF and finite H(k) values. A raw IQ capture with constant samples or without an L-LTF is retained but does not count as a valid CSI time point. Constant captures are warned about rather than aborting analysis of the other captures.

## Interpretation boundary

The first hardware capture proves that H(k) can be extracted from this adapter. A repeated dataset will establish whether sequential estimates are stable enough for temporal features. It will not, by itself, prove presence detection or people counting. RTL8821CE is 1T1R; multi-person counting remains a separate, difficult validation problem.
