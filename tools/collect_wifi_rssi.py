#!/usr/bin/env python3
"""Collect normal-driver Wi-Fi signal samples with manually interleaved labels.

No sudo, VFIO, monitor mode, or connection interruption is required. Prefer
`iw link`; fall back to /proc/net/wireless when iw is not installed.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PHASES = ("ABSENT", "PRESENT", "ABSENT", "PRESENT", "ABSENT")


def parse_iw_link(output: str) -> dict:
    def match(pattern):
        found = re.search(pattern, output, re.MULTILINE | re.IGNORECASE)
        return found.group(1).strip() if found else ""
    signal = match(r"^\s*signal:\s*(-?\d+(?:\.\d+)?)\s*dBm")
    signal_avg = match(r"^\s*signal avg:\s*(-?\d+(?:\.\d+)?)\s*dBm")
    freq = match(r"^\s*freq:\s*(\d+)")
    rx_bitrate = match(r"^\s*rx bitrate:\s*(.+)$")
    tx_bitrate = match(r"^\s*tx bitrate:\s*(.+)$")
    bssid = match(r"^\s*Connected to\s+([0-9a-f:]{17})")
    if not signal:
        raise ValueError("iw link output has no signal reading (is the interface connected?)")
    value = float(signal)
    # Some drivers return 0 as an invalid RSSI sentinel. Preserve the row but
    # don't treat that value as a real 0 dBm measurement.
    return {"signal_dbm": value if -110 <= value < 0 else "",
            "signal_avg_dbm": float(signal_avg) if signal_avg and -110 <= float(signal_avg) < 0 else "",
            "beacon_signal_avg_dbm": "", "frequency_mhz": int(freq) if freq else "",
            "rx_bitrate": rx_bitrate, "tx_bitrate": tx_bitrate,
            "bssid": bssid, "link_quality": "", "source": "iw_link"}


def parse_iw_station(output: str) -> dict:
    def match(pattern):
        found = re.search(pattern, output, re.MULTILINE | re.IGNORECASE)
        return found.group(1).strip() if found else ""
    signal = match(r"^\s*signal:\s*(-?\d+(?:\.\d+)?)\s*dBm")
    signal_avg = match(r"^\s*signal avg:\s*(-?\d+(?:\.\d+)?)\s*(?:\[.*?\]\s*)?dBm")
    beacon_avg = match(r"^\s*beacon signal avg:\s*(-?\d+(?:\.\d+)?)\s*dBm")
    def valid(value):
        return float(value) if value and -110 <= float(value) < 0 else ""
    return {"station_signal_dbm": valid(signal),
            "station_signal_avg_dbm": valid(signal_avg),
            "beacon_signal_avg_dbm": valid(beacon_avg)}


def parse_proc_wireless(output: str, interface: str) -> dict:
    for line in output.splitlines():
        if not line.strip().startswith(interface + ":"):
            continue
        fields = line.split(":", 1)[1].split()
        if len(fields) < 3:
            break
        # /proc/net/wireless: status, link quality, signal level, noise.
        quality = float(fields[1].rstrip("."))
        level = float(fields[2].rstrip("."))
        if level <= -200:
            raise ValueError("/proc/net/wireless reports an invalid signal sentinel")
        return {"signal_dbm": level, "signal_avg_dbm": "", "signal_percent": "",
                "bssid": "", "link_quality": quality, "source": "proc_net_wireless"}
    raise ValueError(f"no wireless statistics for {interface} in /proc/net/wireless")


def parse_nmcli_wifi(output: str) -> dict:
    for line in output.splitlines():
        # nmcli escapes the colons inside BSSIDs in terse mode.
        normalized = line.strip().replace(r"\:", ":")
        match = re.match(r"^\*:([0-9a-fA-F:]{17}):(\d+)$", normalized)
        if match:
            return {"signal_dbm": "", "signal_avg_dbm": "",
                    "signal_percent": int(match.group(2)),
                    "bssid": match.group(1).upper(),
                    "link_quality": "", "source": "nmcli"}
    raise ValueError("nmcli has no in-use AP in its cached Wi-Fi list")


def sample_signal(interface: str) -> dict:
    iw = shutil.which("iw")
    if iw:
        result = subprocess.run([iw, "dev", interface, "link"], text=True,
                                capture_output=True, timeout=3, check=False)
        if result.returncode == 0:
            try:
                parsed = parse_iw_link(result.stdout)
                parsed["signal_percent"] = ""
                station = subprocess.run([iw, "dev", interface, "station", "dump"],
                                         text=True, capture_output=True, timeout=3, check=False)
                if station.returncode == 0:
                    parsed.update(parse_iw_station(station.stdout))
                return parsed
            except ValueError:
                pass
    try:
        parsed = parse_proc_wireless(Path("/proc/net/wireless").read_text(), interface)
        parsed["signal_percent"] = ""
        parsed.update({"beacon_signal_avg_dbm": "", "frequency_mhz": "",
                       "rx_bitrate": "", "tx_bitrate": ""})
        return parsed
    except (OSError, ValueError):
        nmcli = shutil.which("nmcli")
        if not nmcli:
            raise
        result = subprocess.run([nmcli, "-t", "--escape", "yes", "-f",
                                 "IN-USE,BSSID,SIGNAL", "dev", "wifi", "list",
                                 "--rescan", "no"], text=True, capture_output=True,
                                timeout=5, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "nmcli failed")
        return parse_nmcli_wifi(result.stdout)


def collect(interface: str, output: Path, interval: float, duration: int,
            settle: int, phases=PHASES) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp_utc", "elapsed_seconds", "phase", "interface",
              "signal_dbm", "signal_avg_dbm", "station_signal_dbm", "station_signal_avg_dbm",
              "beacon_signal_avg_dbm", "signal_percent", "link_quality", "frequency_mhz",
              "rx_bitrate", "tx_bitrate", "bssid", "source", "error"]
    with output.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        print(f"Interface: {interface}\nOutput: {output}\nPlan: {' -> '.join(phases)}")
        print("Keep the laptop and AP fixed. The laptop stays inside the monitored room.")
        for index, phase in enumerate(phases, 1):
            if phase == "ABSENT":
                input(f"\nBlock {index}/{len(phases)} ABSENT: leave the room empty, then press Enter... ")
            else:
                input(f"\nBlock {index}/{len(phases)} PRESENT: enter and stand in the chosen position, then press Enter... ")
            print(f"Settling for {settle}s; do not move the laptop/AP...")
            time.sleep(settle)
            print(f"Sampling {duration}s of {phase}...")
            start = time.monotonic()
            next_sample = start
            while time.monotonic() - start < duration:
                now = time.monotonic()
                row = {key: "" for key in fields}
                row.update({"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "elapsed_seconds": round(now - start, 3),
                            "phase": phase, "interface": interface})
                try:
                    row.update(sample_signal(interface))
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    row["error"] = str(exc)
                writer.writerow(row)
                stream.flush()
                next_sample += interval
                time.sleep(max(0.0, next_sample - time.monotonic()))
            print(f"Block {index} complete.")
    print(f"\nCollection complete: {output}")
    print("This is labelled measurement data, not a validated detector. Keep the raw CSV.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", default="wlp1s0")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--duration", type=int, default=30,
                        help="seconds sampled per phase after settling (default: 30)")
    parser.add_argument("--settle", type=int, default=8,
                        help="seconds to wait after each room transition (default: 8)")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.interval <= 0 or args.duration < 5 or args.settle < 0:
        parser.error("interval must be >0, duration >=5, settle >=0")
    if not sys.stdin.isatty():
        parser.error("run interactively so phase labels are assigned at each transition")
    output = args.output or Path("data/presence_dataset_rssi") / (
        "rssi_" + datetime.now().astimezone().strftime("%Y%m%d_%H%M%S") + ".csv")
    try:
        collect(args.interface, output, args.interval, args.duration, args.settle)
    except KeyboardInterrupt:
        print("\nInterrupted; partial CSV retained.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
