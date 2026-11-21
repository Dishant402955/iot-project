#!/usr/bin/env python3
"""Extract a time series of per-tone CSI from repeated DVLA captures.

Each output JSONL row is one subcarrier measurement and includes the capture
index, wall-clock file timestamp, and Devourer monotonic event timestamp.
This preserves the distinction between tones within one capture and captures
across time. At least two valid captures are required.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import la_csi
import la_decode


def load_events(path):
    events = {}
    if not path:
        return events
    with open(path, errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("ev") == "la.capture" and event.get("ok") == 1:
                events[event.get("file")] = event.get("t")
    return events


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("captures", nargs="+", help="DVLA files or shell-expanded glob")
    ap.add_argument("--output", required=True, help="combined CSI JSONL output")
    ap.add_argument("--events-log", help="rxdemo JSONL log for monotonic capture times")
    ap.add_argument("--layout", default=None)
    ap.add_argument("--min-captures", type=int, default=2)
    args = ap.parse_args()

    paths = []
    for item in args.captures:
        matches = glob.glob(item)
        paths.extend(matches if matches else [item])
    paths = sorted(set(os.path.abspath(p) for p in paths))
    events = load_events(args.events_log)
    rows_written = 0
    valid_captures = 0
    failures = []
    with open(args.output, "w") as out:
        for index, path in enumerate(paths, 1):
            try:
                meta, words = la_decode.read_dump(path)
                layout = args.layout or la_decode.DEFAULT_LAYOUT
                x = la_decode.LAYOUTS[layout][1](words)
                x = x - la_csi.np.mean(x)
                start, cfo = la_csi.locate_lltf(x)
                if start is None:
                    raise ValueError("no L-LTF found")
                h = la_csi.estimate_h(x, start, cfo)
                stat = os.stat(path)
                event_ms = events.get(path)
                for tone, hv, seq in zip(la_csi.TONES, h, la_csi.LTF_SEQ):
                    if seq == 0:
                        continue
                    out.write(json.dumps({
                        "capture_index": index,
                        "capture_file": path,
                        "capture_mtime_ns": stat.st_mtime_ns,
                        "event_uptime_ms": event_ms,
                        "tone": int(tone),
                        "mag": float(abs(hv)),
                        "mag_db": float(20 * la_csi.np.log10(abs(hv) + 1e-12)),
                        "phase_rad": float(la_csi.np.angle(hv)),
                        "lltf_start_sample": int(start),
                        "cfo_hz": float(cfo * 20e6),
                        "sample_rate_mhz": float(meta["fs_mhz"]),
                    }) + "\n")
                    rows_written += 1
                valid_captures += 1
                print(f"CSI_SERIES_CAPTURE_PASS: {os.path.basename(path)} "
                      f"L-LTF@{start} CFO={cfo * 20e6 / 1e3:+.1f} kHz")
            except (Exception, SystemExit) as exc:
                failures.append((path, str(exc)))
                print(f"CSI_SERIES_CAPTURE_FAIL: {path}: {exc}", file=sys.stderr)

    if valid_captures < args.min_captures:
        try:
            os.unlink(args.output)
        except OSError:
            pass
        print(f"FAIL: only {valid_captures} valid CSI captures; "
              f"need at least {args.min_captures}", file=sys.stderr)
        return 1
    print(f"CSI_SERIES_PASS: captures={valid_captures}, tones_per_capture=52, "
          f"rows={rows_written}, output={args.output}")
    if failures:
        print(f"WARNING: {len(failures)} capture(s) lacked usable L-LTF", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
