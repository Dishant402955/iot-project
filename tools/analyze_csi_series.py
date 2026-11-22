#!/usr/bin/env python3
"""Offline quality analysis for Devourer per-tone CSI JSONL series.

This tool summarizes extraction quality and packet-to-packet channel variation.
It does NOT infer human presence or count people; that requires labelled,
controlled empty/occupied measurements.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover - environment diagnostic
    raise SystemExit("NumPy is required; use the project's vendor/.venv Python") from exc


def load_series(path: Path):
    groups = defaultdict(list)
    malformed = 0
    with path.open(errors="replace") as stream:
        for line in stream:
            try:
                row = json.loads(line)
                groups[int(row["capture_index"])].append(row)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                malformed += 1
    return groups, malformed


def summarize(groups):
    captures = []
    vectors = []
    for index, rows in sorted(groups.items()):
        rows = sorted(rows, key=lambda r: int(r["tone"]))
        tones = np.asarray([int(r["tone"]) for r in rows], dtype=float)
        mag_db = np.asarray([float(r["mag_db"]) for r in rows], dtype=float)
        mag = np.asarray([float(r["mag"]) for r in rows], dtype=float)
        phase = np.unwrap(np.asarray([float(r["phase_rad"]) for r in rows], dtype=float))
        if len(rows) < 2 or not np.all(np.isfinite(mag_db)) or not np.all(np.isfinite(phase)):
            continue
        slope, intercept = np.polyfit(tones, phase, 1)
        phase_residual = phase - (slope * tones + intercept)
        h = mag * np.exp(1j * phase)
        h_sanitized = h * np.exp(-1j * (slope * tones + intercept))
        h_sanitized /= np.linalg.norm(h_sanitized) + 1e-12
        first = rows[0]
        captures.append({
            "capture_index": index,
            "event_uptime_ms": first.get("event_uptime_ms"),
            "tone_count": len(rows),
            "mean_mag_db": float(np.mean(mag_db)),
            "median_mag_db": float(np.median(mag_db)),
            "tone_spread_db": float(np.std(mag_db)),
            "mag_p10_db": float(np.percentile(mag_db, 10)),
            "mag_p90_db": float(np.percentile(mag_db, 90)),
            "phase_residual_std_rad": float(np.std(phase_residual)),
            "phase_slope_rad_per_tone": float(slope),
            "cfo_hz": float(first.get("cfo_hz", math.nan)),
            "lltf_start_sample": int(first.get("lltf_start_sample", -1)),
        })
        vectors.append((index, mag_db, h_sanitized))

    adjacent_mag_corr = []
    adjacent_phase_sanitized_similarity = []
    adjacent_gaps = []
    for (ia, ma, ha), (ib, mb, hb) in zip(vectors, vectors[1:]):
        if len(ma) == len(mb) and np.std(ma) > 0 and np.std(mb) > 0:
            adjacent_mag_corr.append(float(np.corrcoef(ma, mb)[0, 1]))
        adjacent_phase_sanitized_similarity.append(float(abs(np.vdot(ha, hb))))
        adjacent_gaps.append(ib - ia)

    return captures, adjacent_mag_corr, adjacent_phase_sanitized_similarity, adjacent_gaps


def finite_stats(values):
    vals = [float(v) for v in values if math.isfinite(float(v))]
    if not vals:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None, "std": None}
    return {
        "count": len(vals), "min": min(vals), "median": statistics.median(vals),
        "mean": statistics.fmean(vals), "max": max(vals),
        "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("series", type=Path, help="la_csi_series.py JSONL output")
    ap.add_argument("--output-prefix", type=Path, help="default: <series stem>_analysis")
    args = ap.parse_args()
    if not args.series.is_file():
        ap.error(f"CSI series file does not exist: {args.series}")

    prefix = args.output_prefix or args.series.with_suffix("").with_name(args.series.stem + "_analysis")
    groups, malformed = load_series(args.series)
    captures, mag_corr, phase_sim, gaps = summarize(groups)
    if not captures:
        raise SystemExit("No usable CSI captures found in the input series")

    csv_path = Path(str(prefix) + ".csv")
    json_path = Path(str(prefix) + ".json")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(captures[0]))
        writer.writeheader()
        writer.writerows(captures)

    times = [c["event_uptime_ms"] for c in captures if c["event_uptime_ms"] is not None]
    cadence = [b - a for a, b in zip(times, times[1:])]
    summary = {
        "input": str(args.series.resolve()),
        "captures_with_csi": len(captures),
        "capture_indices_in_series": len(groups),
        "malformed_rows": malformed,
        "tones_per_capture": sorted({c["tone_count"] for c in captures}),
        "event_cadence_ms": finite_stats(cadence),
        "mean_magnitude_db_across_captures": finite_stats([c["mean_mag_db"] for c in captures]),
        "within_capture_tone_spread_db": finite_stats([c["tone_spread_db"] for c in captures]),
        "per_capture_phase_residual_std_rad": finite_stats([c["phase_residual_std_rad"] for c in captures]),
        "adjacent_magnitude_profile_correlation": finite_stats(mag_corr),
        "adjacent_phase_sanitized_complex_similarity": finite_stats(phase_sim),
        "adjacent_capture_index_gap": finite_stats(gaps),
        "interpretation_limit": "Unlabelled CSI variation cannot be attributed to human presence; collect controlled empty-room and occupied-room data before fitting or evaluating a detector.",
    }
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"CSI_ANALYSIS_PASS: captures={len(captures)} rows={sum(c['tone_count'] for c in captures)}")
    print(f"event cadence median={summary['event_cadence_ms']['median']} ms")
    print(f"mean magnitude across captures={summary['mean_magnitude_db_across_captures']['mean']:.2f} dB "
          f"(std={summary['mean_magnitude_db_across_captures']['std']:.2f} dB)")
    print(f"median within-capture tone spread={summary['within_capture_tone_spread_db']['median']:.2f} dB")
    print(f"adjacent magnitude-profile correlation median={summary['adjacent_magnitude_profile_correlation']['median']:.3f}")
    print(f"adjacent phase-sanitized complex similarity median={summary['adjacent_phase_sanitized_complex_similarity']['median']:.3f}")
    print(f"CSV: {csv_path}\nJSON: {json_path}")
    print("NOTE: this is signal-quality analysis, not a human-presence result.")


if __name__ == "__main__":
    main()
