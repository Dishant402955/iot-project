#!/usr/bin/env python3
"""Synthetic end-to-end test for repeated DVLA -> temporal CSI JSONL."""
import json
import os
import struct
import subprocess
import sys
import tempfile

try:
    import numpy as np
except ImportError:
    print("numpy not available — skipping", file=sys.stderr)
    raise SystemExit(77)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import la_csi


def make_dump(path, samples):
    i = np.clip(np.rint(samples.real * 850), -2048, 2047).astype(np.int32)
    q = np.clip(np.rint(samples.imag * 850), -2048, 2047).astype(np.int32)
    words = ((i & 0xFFF) | ((q & 0xFFF) << 12)).astype("<u8")
    header = bytearray(32)
    header[:5] = b"DVLA\x01"
    header[7] = 2  # 20 Msps
    struct.pack_into("<I", header, 12, len(words))
    with open(path, "wb") as stream:
        stream.write(header)
        words.tofile(stream)


def main():
    rng = np.random.default_rng(123)
    ref = la_csi.ltf_ref_time()
    ltf = np.concatenate([ref[-32:], ref, ref])
    taps = np.array([1.0, 0.4 * np.exp(1j * 0.7)])
    signal = np.convolve(ltf, taps, "full")[:len(ltf)]
    signal *= np.exp(2j * np.pi * (31e3 / 20e6) * np.arange(len(signal)))
    signal += 0.002 * (rng.standard_normal(len(signal)) +
                       1j * rng.standard_normal(len(signal)))
    samples = np.zeros(8192, dtype=complex)
    samples[1000:1000 + len(signal)] = signal

    with tempfile.TemporaryDirectory(prefix="la-csi-series-") as tmp:
        captures = []
        for index in range(2):
            path = os.path.join(tmp, f"capture.{index + 1:04d}.bin")
            make_dump(path, samples)
            captures.append(path)
        events = os.path.join(tmp, "rxdemo.jsonl")
        with open(events, "w") as stream:
            for index, path in enumerate(captures):
                stream.write(json.dumps({
                    "ev": "la.capture", "ok": 1,
                    "t": 500 + index * 1000, "file": path,
                }) + "\n")
        output = os.path.join(tmp, "series.jsonl")
        command = [sys.executable, os.path.join(TOOLS, "la_csi_series.py"),
                   *captures, "--events-log", events, "--output", output]
        result = subprocess.run(command, text=True, capture_output=True)
        if result.returncode:
            print(result.stdout, end="")
            print(result.stderr, file=sys.stderr, end="")
            raise SystemExit(result.returncode)
        rows = [json.loads(line) for line in open(output)]
        assert len(rows) == 104, f"expected 104 rows, got {len(rows)}"
        assert {row["capture_index"] for row in rows} == {1, 2}
        assert {row["event_uptime_ms"] for row in rows} == {500, 1500}
        assert all(len([r for r in rows if r["capture_index"] == i]) == 52
                   for i in (1, 2))
        assert all(np.isfinite(row["mag"]) and np.isfinite(row["phase_rad"])
                   for row in rows)
        print("la_csi_series_selftest: PASS (2 captures, 104 tone rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
