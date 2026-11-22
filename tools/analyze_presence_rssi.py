#!/usr/bin/env python3
"""Summarize AP RX RSSI metadata for manually labelled presence batches.

This is a diagnostic side channel, not a validated presence classifier. It
uses the rxdemo.log retained beside each raw capture run and the batch labels
in the collector JSONL. Missing logs/frames are reported, never imputed.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path


def load_events(path: Path) -> list[dict]:
    events = []
    with path.open(errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("ev") == "rx.presence_frame":
                events.append(event)
    return events


def summarize(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "stdev": statistics.pstdev(values),
        "min": min(values),
        "max": max(values),
    }


def analyze(dataset: Path, archive: Path) -> dict:
    batches = []
    with dataset.open() as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("record_type") != "labelled_capture_batch":
                continue
            run_name = Path(record["capture_run_dir"]).name
            log = archive / run_name / "rxdemo.log"
            if not log.is_file():
                batches.append({"phase": record.get("phase"),
                                "batch_number": record.get("batch_number"),
                                "run": run_name, "error": "missing rxdemo.log"})
                continue
            events = load_events(log)
            rssis = [float(e["rssi"]) for e in events
                     if isinstance(e.get("rssi"), (int, float))
                     and math.isfinite(float(e["rssi"]))]
            batches.append({
                "phase": record.get("phase"),
                "label": record.get("label"),
                "batch_number": record.get("batch_number"),
                "run": run_name,
                "rssi": summarize(rssis),
            })
    phases = {}
    for phase in ("ABSENT", "PRESENT"):
        vals = [b["rssi"]["median"] for b in batches
                if b.get("phase") == phase and b.get("rssi", {}).get("count", 0)]
        phases[phase] = summarize(vals)
    return {"dataset": str(dataset), "archive": str(archive),
            "batches": batches, "phase_batch_median_summary": phases,
            "warning": "RSSI is an auxiliary diagnostic. Phase/order drift and AP/receiver gain changes can mimic occupancy; this report is not a detector evaluation."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--archive", type=Path, required=True,
                        help="directory containing archived rtl8821ce-la.* run folders")
    parser.add_argument("--json", type=Path, help="optional JSON output path")
    args = parser.parse_args()
    report = analyze(args.dataset, args.archive)
    print("phase batch run frames median mean stdev min max")
    for b in report["batches"]:
        if "error" in b:
            print(b["phase"], b["batch_number"], b["run"], b["error"])
            continue
        r = b["rssi"]
        print(f"{b['phase']:7} {b['batch_number']:>2} {b['run']} "
              f"{r['count']:>4} {r['median']:>6.1f} {r['mean']:>6.2f} "
              f"{r['stdev']:>5.2f} {r['min']:>3.0f} {r['max']:>3.0f}")
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n")
        print(f"JSON: {args.json}")
    print(report["warning"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
