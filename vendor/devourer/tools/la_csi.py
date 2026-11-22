#!/usr/bin/env python3
"""Per-tone channel estimate H(k) from an LA-mode capture (issue #150).

Locates an 802.11 L-LTF (legacy long training field) in the complex
baseband stream of a DVLA capture (tools/la_decode.py unpacking, default
layout qi12_l), corrects CFO from the two LTF repetitions, FFTs both
64-sample symbols, and divides by the known ±26-tone sequence — the full
per-subcarrier channel estimate no Jaguar chip exports through a normal
host path.

    la_csi.py cap.bin [--layout qi12_l] [--json out.jsonl] [--plot h.png]
    la_csi.py --selftest        # synthetic L-LTF through a 2-tap channel

Requires a capture at 20 Msps of a 20 MHz channel (the standard L-LTF
sample grid). Prefer a true CCA-triggered capture at 20 Msps. The `t<us>`
CLI field configures Realtek's MAC LA trigger-time register; it does not set
the number of samples in the IQ buffer. The RTL8821C MAC selector encoding is 0=CCA,
1=first CRC-OK, 2=first CRC-error; keep these values aligned with LaMacSig.
A CRC-OK trigger fires at frame end and can exclude the preamble of long
frames.

Detection: 64-lag autocorrelation plateau (the LTF's two identical
periods), refined by cross-correlation against the reference symbol.
Output: one JSON line per tone {tone, mag, mag_db, phase_rad} plus a
summary. Selftest: 2-tap channel + AWGN, asserts |H(k)| correlation
against the analytic channel > 0.99 (exits nonzero on failure — wired as
the la_csi_math ctest).
"""

import argparse
import json
import os
import sys

try:
    import numpy as np
except ImportError:
    # ctest SKIP_RETURN_CODE — CI runners without numpy skip, not fail.
    print("numpy not available — skipping", file=sys.stderr)
    sys.exit(77)

# L_{-26..-1}, 0 (DC), L_{+1..+26} — IEEE 802.11-2016 19.3.10.10.
LTF_SEQ = np.array(
    [1, 1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, 1, 1, 1, -1, -1, 1, 1, -1,
     1, -1, 1, 1, 1, 1,
     0,
     1, -1, -1, 1, 1, -1, 1, -1, 1, -1, -1, -1, -1, -1, 1, 1, -1, -1, 1,
     -1, 1, -1, 1, 1, 1, 1], dtype=float)
TONES = np.arange(-26, 27)  # tone indices matching LTF_SEQ (incl. DC)


def ltf_freq64():
    """The L-LTF mapped onto a 64-bin FFT grid (bin = tone mod 64)."""
    f = np.zeros(64, dtype=complex)
    for k, v in zip(TONES, LTF_SEQ):
        f[k % 64] = v
    return f


def ltf_ref_time():
    """One 64-sample time-domain LTF period at 20 Msps."""
    return np.fft.ifft(ltf_freq64())


def lltf_quality(x, start, cfo_norm):
    """Return independent repeated-LTF quality checks for one candidate.

    The two L-LTF symbols are identical after CFO correction. A candidate
    that merely resembles a 64-sample repetition is not sufficient: we also
    reject the 16-sample L-STF periodicity and compare the two LTF FFTs on the
    52 active subcarriers. Thresholds are deliberately conservative.
    """
    if start < 0 or start + 128 > len(x):
        return {"repeat_corr": 0.0, "stf16_corr": 1.0, "symbol_relerr": 1.0}
    raw = x[start:start + 128]
    a_raw, b_raw = raw[:64], raw[64:128]
    repeat_corr = float(abs(np.vdot(a_raw, b_raw)) / (
        np.linalg.norm(a_raw) * np.linalg.norm(b_raw) + 1e-12))
    r16 = float(abs(np.vdot(raw[:-16], raw[16:])) / (
        np.linalg.norm(raw[:-16]) * np.linalg.norm(raw[16:]) + 1e-12))
    n = np.arange(start, start + 128)
    corrected = raw * np.exp(-2j * np.pi * cfo_norm * n)
    f1 = np.fft.fft(corrected[:64])
    f2 = np.fft.fft(corrected[64:128])
    active = np.asarray([k % 64 for k, v in zip(TONES, LTF_SEQ) if v != 0])
    symbol_relerr = float(np.linalg.norm((f1 - f2)[active]) / (
        np.linalg.norm(f1[active]) + np.linalg.norm(f2[active]) + 1e-12))
    return {"repeat_corr": repeat_corr, "stf16_corr": r16,
            "symbol_relerr": symbol_relerr}


def locate_lltf(x, min_metric=0.6, diagnostics=None):
    """Find a high-confidence L-LTF in the complex baseband stream.

    Returns (start_index, cfo_norm) or (None, 0.0). In addition to the
    64-lag plateau and reference correlation, a candidate must pass three
    independent checks: >=0.85 repeated-symbol coherence, <=0.50 16-lag
    STF coherence, and <=0.25 relative mismatch between CFO-corrected LTF
    FFTs. These conservative gates prevent weak periodic noise from being
    reported as CSI.
    """
    n = len(x)
    if n < 192:
        return None, 0.0
    lag = 64
    c = x[:n - lag] * np.conj(x[lag:])
    p = np.abs(x[lag:]) ** 2
    win = 64
    ker = np.ones(win)
    num = np.convolve(c, ker, "valid")
    den = np.convolve(p, ker, "valid") + 1e-12
    metric = np.abs(num) / den
    ref = ltf_ref_time()
    best = None
    best_score = -1.0
    diag = diagnostics if diagnostics is not None else None
    if diag is not None:
        diag.update({"lag_candidates": 0, "repeat_reject": 0,
                     "stf16_reject": 0, "symbol_reject": 0,
                     "fallback_candidates": 0, "fallback_repeat_reject": 0,
                     "fallback_stf16_reject": 0, "fallback_symbol_reject": 0,
                     "best_repeat_corr": None, "best_stf16_corr": None,
                     "best_symbol_relerr": None,
                     "fallback_best_repeat_corr": None,
                     "fallback_best_stf16_corr": None,
                     "fallback_best_symbol_relerr": None,
                     "fallback_best_start": None,
                     "reason": "no_lag_candidate"})
    seen_lag_starts = set()
    for idx in np.argsort(metric)[::-1][:2000]:
        if metric[idx] < min_metric:
            break
        lo = max(0, idx - 96)
        hi = min(n - 128, idx + 96)
        if hi <= lo:
            continue
        seg = x[lo:hi + 128]
        cc = np.abs(np.correlate(seg, ref, "valid"))
        peak_start = lo + int(np.argmax(cc))

        # The two L-LTF symbols are identical. A single-symbol matched filter
        # therefore has two nearly equal peaks, one at the true pair start and
        # one 64 samples later. Choosing only argmax can select the SECOND
        # symbol, causing the following SIGNAL field to be tested as symbol 2
        # and rejecting a perfectly valid L-LTF. Test both alignments (plus
        # the adjacent period for timing-edge cases) and let the independent
        # two-symbol quality gates decide which is the real pair.
        for start in (peak_start - 64, peak_start, peak_start + 64):
            if start < 0 or start + 128 > n or start in seen_lag_starts:
                continue
            seen_lag_starts.add(start)
            a, b = x[start:start + 64], x[start + 64:start + 128]
            acc = np.vdot(a, b)
            cfo_norm = np.angle(acc) / (2 * np.pi * 64)
            quality = lltf_quality(x, start, cfo_norm)
            if diag is not None:
                diag["lag_candidates"] += 1
                if (diag["best_repeat_corr"] is None or
                        quality["repeat_corr"] > diag["best_repeat_corr"]):
                    diag["best_repeat_corr"] = quality["repeat_corr"]
                    diag["best_stf16_corr"] = quality["stf16_corr"]
                    diag["best_symbol_relerr"] = quality["symbol_relerr"]
            if quality["repeat_corr"] < 0.85:
                if diag is not None: diag["repeat_reject"] += 1
                continue
            if quality["stf16_corr"] > 0.50:
                if diag is not None: diag["stf16_reject"] += 1
                continue
            if quality["symbol_relerr"] > 0.25:
                if diag is not None: diag["symbol_reject"] += 1
                continue
            if diag is not None: diag["reason"] = "accepted_lag_candidate"
            score = (quality["repeat_corr"] - quality["stf16_corr"] -
                     quality["symbol_relerr"])
            if score > best_score:
                best = (start, cfo_norm)
                best_score = score
    if best is not None:
        return best

    # Fallback: the lag-metric shortlist above can miss a real L-LTF when a
    # strong neighbouring periodic component dominates its top-2000 indices.
    # Search the full capture with a normalized matched filter, then apply
    # exactly the same three independent quality gates. This is not a relaxed
    # detector: candidates still need repeated-symbol coherence, L-STF
    # rejection, and agreement between the two CFO-corrected LTF FFTs.
    if diag is not None:
        diag["reason"] = "lag_candidates_rejected"
    ref_energy = float(np.vdot(ref, ref).real)
    matched = np.abs(np.correlate(x, ref, "valid"))
    local_energy = np.convolve(np.abs(x) ** 2, np.ones(64), "valid")
    scores = matched / (np.sqrt(local_energy * ref_energy) + 1e-12)
    order = np.argsort(scores)[::-1]
    tried_peaks = []
    seen_fallback_starts = set()
    for raw_idx in order:
        idx = int(raw_idx)
        if len(tried_peaks) >= 300:
            break
        # Peaks 64 samples apart can be the two copies of the same L-LTF.
        # Do not collapse them before checking both possible pair alignments.
        if any(abs(idx - previous) < 16 for previous in tried_peaks):
            continue
        tried_peaks.append(idx)
        for start in (idx - 64, idx, idx + 64):
            if start < 0 or start + 128 > n or start in seen_fallback_starts:
                continue
            seen_fallback_starts.add(start)
            a, b = x[start:start + 64], x[start + 64:start + 128]
            acc = np.vdot(a, b)
            cfo_norm = np.angle(acc) / (2 * np.pi * 64)
            quality = lltf_quality(x, start, cfo_norm)
            if diag is not None:
                diag["fallback_candidates"] += 1
                if (diag["fallback_best_repeat_corr"] is None or
                        quality["repeat_corr"] > diag["fallback_best_repeat_corr"]):
                    diag["fallback_best_repeat_corr"] = quality["repeat_corr"]
                    diag["fallback_best_stf16_corr"] = quality["stf16_corr"]
                    diag["fallback_best_symbol_relerr"] = quality["symbol_relerr"]
                    diag["fallback_best_start"] = start
            if quality["repeat_corr"] < 0.85:
                if diag is not None: diag["fallback_repeat_reject"] += 1
                continue
            if quality["stf16_corr"] > 0.50:
                if diag is not None: diag["fallback_stf16_reject"] += 1
                continue
            if quality["symbol_relerr"] > 0.25:
                if diag is not None: diag["fallback_symbol_reject"] += 1
                continue
            if diag is not None: diag["reason"] = "accepted_fallback_candidate"
            return start, cfo_norm
    if diag is not None and diag["reason"] != "lag_candidates_rejected":
        diag["reason"] = "no_matched_filter_candidate"
    return None, 0.0


def refine_cfo(x, start, max_periods=8, min_rep=0.5):
    """Re-estimate CFO over as many consecutive 64-sample repetitions as
    the signal provides (LTF-train captures carry ~10) — the 2-symbol
    estimate's few-kHz noise leaks measurably into adjacent tones."""
    acc = 0.0 + 0.0j
    used = 0
    for k in range(max_periods):
        a = x[start + 64 * k:start + 64 * (k + 1)]
        b = x[start + 64 * (k + 1):start + 64 * (k + 2)]
        if len(b) < 64:
            break
        rep = np.abs(np.vdot(a, b)) / (np.linalg.norm(a) * np.linalg.norm(b)
                                       + 1e-12)
        if rep < min_rep:
            break
        acc += np.vdot(a, b)
        used += 1
    if used == 0:
        return None
    return np.angle(acc) / (2 * np.pi * 64)


def estimate_h(x, start, cfo_norm, backoff=4):
    """CFO-correct, FFT both LTF symbols, average, divide by the tones.

    The FFT window is pulled `backoff` samples INTO the guard interval:
    the GI2 is a cyclic prefix of the same symbol, so the shift is a pure
    linear phase across tones (harmless for |H|) while absorbing channel
    delay spread that would otherwise leak inter-symbol energy into deep
    nulls (measured on the notch-validation protocol)."""
    start = max(0, start - backoff)
    n = np.arange(start, start + 128)
    seg = x[start:start + 128] * np.exp(-2j * np.pi * cfo_norm * n)
    s1 = np.fft.fft(seg[:64])
    s2 = np.fft.fft(seg[64:128])
    avg = (s1 + s2) / 2
    h = np.zeros(len(TONES), dtype=complex)
    for i, (k, v) in enumerate(zip(TONES, LTF_SEQ)):
        if v != 0:
            h[i] = avg[k % 64] / v
    return h


def run(x, args):
    start, cfo = locate_lltf(x)
    if start is None:
        print("no L-LTF found in capture", file=sys.stderr)
        return 1
    h = estimate_h(x, start, cfo)
    nz = LTF_SEQ != 0
    mag = np.abs(h[nz])
    print(f"# L-LTF at sample {start}, CFO {cfo * 20e6 / 1e3:+.1f} kHz, "
          f"|H| mean {mag.mean():.1f} spread "
          f"{20 * np.log10(mag.max() / max(mag.min(), 1e-9)):.1f} dB",
          file=sys.stderr)
    out = open(args.json, "w") if args.json else sys.stdout
    for k, hv, seq in zip(TONES, h, LTF_SEQ):
        if seq == 0:
            continue
        out.write(json.dumps({
            "tone": int(k),
            "mag": float(np.abs(hv)),
            "mag_db": float(20 * np.log10(np.abs(hv) + 1e-12)),
            "phase_rad": float(np.angle(hv)),
        }) + "\n")
    if args.json:
        out.close()
    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
        a1.stem(TONES[nz], 20 * np.log10(np.abs(h[nz]) + 1e-12))
        a1.set_ylabel("|H(k)| dB")
        a1.grid(True, alpha=0.3)
        a2.stem(TONES[nz], np.angle(h[nz]))
        a2.set_ylabel("arg H(k) rad")
        a2.set_xlabel("subcarrier")
        a2.grid(True, alpha=0.3)
        fig.savefig(args.plot, dpi=100, bbox_inches="tight")
        print(f"wrote {args.plot}", file=sys.stderr)
    return 0


def selftest():
    """Synthetic L-LTF through a known 2-tap channel + AWGN."""
    rng = np.random.default_rng(7)
    ref = ltf_ref_time()
    # GI2 (32 samples) + two periods, embedded in noise padding.
    ltf = np.concatenate([ref[-32:], ref, ref])
    x = np.concatenate([
        0.05 * (rng.standard_normal(700) + 1j * rng.standard_normal(700)),
        ltf,
        0.05 * (rng.standard_normal(700) + 1j * rng.standard_normal(700)),
    ])
    taps = np.array([1.0, 0.55 * np.exp(1j * 1.1)])
    y = np.convolve(x, taps, "full")[:len(x)]
    cfo_true = 45e3 / 20e6  # 45 kHz at 20 Msps
    y = y * np.exp(2j * np.pi * cfo_true * np.arange(len(y)))
    y += 0.01 * (rng.standard_normal(len(y)) + 1j * rng.standard_normal(len(y)))

    start, cfo = locate_lltf(y)
    assert start is not None, "selftest: L-LTF not found"
    cfo_err_khz = abs(cfo - cfo_true) * 20e3
    assert cfo_err_khz < 2.0, f"selftest: CFO error {cfo_err_khz:.2f} kHz"
    h = estimate_h(y, start, cfo)

    h_true64 = np.fft.fft(np.concatenate([taps, np.zeros(62)]))
    nz = LTF_SEQ != 0
    h_true = np.array([h_true64[k % 64] for k in TONES])[nz]
    corr = np.corrcoef(np.abs(h[nz]), np.abs(h_true))[0, 1]
    print(f"selftest: LTF@{start} cfo_err={cfo_err_khz:.2f} kHz "
          f"|H| corr={corr:.4f}")
    assert corr > 0.99, f"selftest: |H(k)| correlation {corr:.4f} <= 0.99"
    # A noise-only capture must not be promoted to CSI by either detector.
    noise = 0.2 * (rng.standard_normal(8192) + 1j * rng.standard_normal(8192))
    noise_start, _ = locate_lltf(noise)
    assert noise_start is None, f"selftest: noise falsely detected as L-LTF@{noise_start}"
    print("selftest: noise rejection PASS")

    # Regression: the matched-filter peaks at both identical L-LTF symbols.
    # Make the second symbol's single-symbol peak slightly stronger so a
    # single-argmax implementation locks 64 samples late and compares the
    # second LTF symbol with SIGNAL instead of comparing the LTF pair.
    alignment_ltf = np.concatenate([ref[-32:], ref.copy(), ref.copy()])
    alignment_ltf[32:96] += 0.008 * (
        rng.standard_normal(64) + 1j * rng.standard_normal(64))
    alignment_offset = 1000
    alignment_x = np.zeros(8192, dtype=complex)
    alignment_signal = alignment_ltf * np.exp(
        2j * np.pi * cfo_true * np.arange(len(alignment_ltf)))
    alignment_x[alignment_offset:alignment_offset + len(alignment_signal)] = alignment_signal
    matched = np.abs(np.correlate(alignment_x, ref, "valid"))
    expected_start = alignment_offset + 32
    assert matched[expected_start + 64] > matched[expected_start], (
        "selftest: regression fixture did not make the second LTF peak stronger")
    aligned_start, aligned_cfo = locate_lltf(alignment_x)
    assert aligned_start == expected_start, (
        f"selftest: repeated-symbol alignment selected {aligned_start}, "
        f"expected {expected_start}")
    aligned_quality = lltf_quality(alignment_x, aligned_start, aligned_cfo)
    assert (aligned_quality["repeat_corr"] >= 0.85 and
            aligned_quality["stf16_corr"] <= 0.50 and
            aligned_quality["symbol_relerr"] <= 0.25), (
        f"selftest: recovered alignment failed strict gates: {aligned_quality}")
    print("selftest: repeated-symbol alignment regression PASS")
    print("selftest: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump", nargs="?")
    ap.add_argument("--layout", default=None)
    ap.add_argument("--json", help="write per-tone JSONL here (default stdout)")
    ap.add_argument("--plot", help="write |H|/phase PNG here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.dump:
        ap.error("dump file required (or --selftest)")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import la_decode
    meta, words = la_decode.read_dump(args.dump)
    if abs(meta["fs_mhz"] - 20.0) > 0.01:
        print(f"WARNING: capture at {meta['fs_mhz']} Msps — L-LTF math "
              "assumes the standard 20 Msps grid", file=sys.stderr)
    layout = args.layout or la_decode.DEFAULT_LAYOUT
    x = la_decode.LAYOUTS[layout][1](words)
    x = x - np.mean(x)
    sys.exit(run(x, args))


if __name__ == "__main__":
    main()
