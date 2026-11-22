#!/usr/bin/env python3
"""Reference implementation of the paper's Range-Filtered Doppler Spectrum HPD core.

Input CSI must be calibrated frequency-domain complex CSI with shape [frames, tones].
The released Intel dataset is already phase/delay calibrated. Raw Devourer L-LTF
estimates are NOT yet equivalent and must pass a separate calibration/adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy import signal

C = 299_792_458.0

@dataclass(frozen=True)
class RFDSConfig:
    bandwidth_hz: float = 160e6
    carrier_hz: float = 6.3e9  # dataset README: channel 79, approx 6.3 GHz
    frame_rate_hz: float = 100.0
    frames_per_window: int = 32
    range_gates_m: tuple[float, ...] | None = None
    fir_taps: int = 64
    # Paper does not publish the FIR cutoff or clipping offset in the supplied text.
    # These are explicit tunables, not claimed paper-exact constants.
    fir_cutoff_nyquist: float = 0.04
    clip_delta_db: float = 6.0
    snr_threshold_db: float = 12.0
    detection_window_frames: int = 3
    snr_window_windows: int = 20
    majority_frames: int = 3
    range_zone_near_m: float = 2.0
    range_zone_far_m: float = 5.0
    hop_frames: int = 1

    @property
    def range_resolution_m(self) -> float:
        return C / (2.0 * self.bandwidth_hz)


def _frequency_bins(n: int, bandwidth_hz: float) -> np.ndarray:
    """Centered, equally spaced subcarrier frequencies.

    The paper's dataset README describes 512 retained CSI tones but does not
    publish the exact per-tone frequency index vector. This is the nominal
    contiguous-grid assumption and must be checked against the raw NIC mapping.
    """
    df = bandwidth_hz / n
    return (np.arange(n, dtype=np.float64) - n // 2) * df


def get_range_gates(cfg: RFDSConfig) -> np.ndarray:
    if cfg.range_gates_m is not None:
        return np.asarray(cfg.range_gates_m, dtype=np.float64)
    # Nine consecutive nominal range-resolution gates, as in Table I.
    return np.arange(9, dtype=np.float64) * cfg.range_resolution_m

def make_range_filters(n_tones: int, cfg: RFDSConfig) -> np.ndarray:
    f = _frequency_bins(n_tones, cfg.bandwidth_hz)
    ranges = get_range_gates(cfg)
    # Equation (4): phase-compensated frequency-domain single-point DFT.
    return np.exp(-1j * 2.0 * np.pi * (2.0 * ranges[:, None] / C) * f[None, :])


def range_gate_series(csi: np.ndarray, cfg: RFDSConfig) -> np.ndarray:
    """Matched-filter calibrated CSI into complex range-gate time series."""
    x = np.asarray(csi, dtype=np.complex128)
    if x.ndim != 2 or x.shape[0] < cfg.frames_per_window or x.shape[1] < 8:
        raise ValueError("CSI must be [frames, tones] with enough frames and tones")
    if not np.isfinite(x.real).all() or not np.isfinite(x.imag).all():
        raise ValueError("CSI contains NaN or infinite values")
    filters = make_range_filters(x.shape[1], cfg)
    # Normalize by tone count so scale does not grow with bandwidth/tones.
    return (x @ filters.T) / x.shape[1]


def design_mti_fir(cfg: RFDSConfig) -> np.ndarray:
    """High-pass MTI FIR with a cosine window.

    The paper specifies a 64-step cosine-window FIR, but does not publish its
    cutoff. A 64th-order Type-I design therefore has 65 coefficients. The
    cutoff remains a tunable normalized-to-Nyquist assumption.
    """
    if cfg.fir_taps < 4 or not 0 < cfg.fir_cutoff_nyquist < 1:
        raise ValueError("invalid FIR design parameters")
    order = int(cfg.fir_taps)
    cutoff_hz = cfg.fir_cutoff_nyquist * (cfg.frame_rate_hz / 2.0)
    b = signal.firwin(order + 1, cutoff_hz, fs=cfg.frame_rate_hz,
                      pass_zero=False, window="cosine")
    # Enforce exact DC rejection after finite-window truncation.
    b -= b.sum() / len(b)
    return b


def mti_filter_ranges(ranges: np.ndarray, cfg: RFDSConfig) -> np.ndarray:
    b = design_mti_fir(cfg)
    # Causal filtering matches streaming use; initial FIR transient is retained
    # but first full window is naturally suppressed by windowed processing.
    return signal.lfilter(b, [1.0], ranges, axis=0)


def doppler_windows(filtered_ranges: np.ndarray, cfg: RFDSConfig) -> tuple[np.ndarray, np.ndarray]:
    """Return [windows, range_gates, doppler_bins] power and Doppler velocity."""
    x = np.asarray(filtered_ranges)
    m = cfg.frames_per_window
    if x.ndim != 2 or x.shape[0] < m:
        raise ValueError("not enough filtered frames")
    starts = range(0, x.shape[0] - m + 1, cfg.hop_frames)
    win = signal.windows.hann(m, sym=False)
    spectra = []
    for start in starts:
        block = x[start:start + m] * win[:, None]
        spec = np.fft.fftshift(np.fft.fft(block, axis=0), axes=0)
        spectra.append(np.abs(spec.T) ** 2)
    power = np.stack(spectra, axis=0)
    fd = np.fft.fftshift(np.fft.fftfreq(m, d=1.0 / cfg.frame_rate_hz))
    velocity = fd * C / (2.0 * cfg.carrier_hz)
    return power, velocity


def _window_detection_power(power: np.ndarray, cfg: RFDSConfig) -> np.ndarray:
    """Average Doppler power over Wdet consecutive processing windows."""
    w = cfg.detection_window_frames
    if power.shape[0] < w:
        return np.empty((0, power.shape[1], power.shape[2]), dtype=np.float64)
    # Each Wdet cell is averaged in linear power before SNR calculation.
    return np.stack([power[i:i + w].mean(axis=0)
                     for i in range(power.shape[0] - w + 1)], axis=0)


def estimate_snr_db(det_power: np.ndarray, cfg: RFDSConfig) -> tuple[np.ndarray, np.ndarray]:
    """Adaptive clipped noise-floor SNR per [decision, range gate].

    The paper writes SNR_i = P_i - mu_noise,i and clips P_i at
    mu_raw,i + DeltaP_clip. Since the threshold and clipping offset are
    expressed in dB in the paper's prose, this implementation performs the
    averaging and clipping in dB. The paper does not state the clipping
    offset explicitly; cfg.clip_delta_db is a tunable assumption.
    """
    if det_power.size == 0:
        shape = (0, det_power.shape[1])
        return np.empty(shape, dtype=np.float64), np.empty(shape, dtype=np.float64)
    peak_power = np.maximum(det_power.max(axis=2), 1e-24)
    peak_db = 10.0 * np.log10(peak_power)
    noise_db = np.empty_like(peak_db, dtype=np.float64)
    width = max(1, int(cfg.snr_window_windows))
    for i in range(len(peak_db)):
        local = peak_db[max(0, i - width + 1):i + 1]
        mu_raw = local.mean(axis=0)
        clipped = np.minimum(local, mu_raw[None, :] + cfg.clip_delta_db)
        noise_db[i] = clipped.mean(axis=0)
    return peak_db - noise_db, peak_db


def detect_presence(csi: np.ndarray, cfg: RFDSConfig = RFDSConfig()) -> dict:
    """Run RF-DS and return time-aligned per-window estimates and binary HPD."""
    ranges = range_gate_series(csi, cfg)
    filtered = mti_filter_ranges(ranges, cfg)
    doppler_power, velocity = doppler_windows(filtered, cfg)
    det_power = _window_detection_power(doppler_power, cfg)
    snr_db, peak_db = estimate_snr_db(det_power, cfg)
    if snr_db.shape[0] == 0:
        raise ValueError("not enough frames for Doppler and detection windows")

    best_gate = np.argmax(snr_db, axis=1)
    gates = get_range_gates(cfg)
    # Standard three-point parabolic interpolation around the strongest range gate.
    # The paper specifies quadratic interpolation but does not give its exact fit equation.
    best_range = gates[best_gate].astype(np.float64).copy()
    range_step = float(np.median(np.diff(gates))) if len(gates) > 1 else 1.0
    magnitude = np.sqrt(np.maximum(det_power.max(axis=2), 0.0))
    for row, idx in enumerate(best_gate):
        if 0 < idx < len(gates) - 1:
            y0, y1, y2 = magnitude[row, idx - 1:idx + 2]
            denom = y0 - 2.0*y1 + y2
            if abs(denom) > 1e-12:
                offset = 0.5 * (y0 - y2) / denom
                best_range[row] += float(np.clip(offset, -1.0, 1.0)) * range_step
    best_snr = snr_db[np.arange(len(best_gate)), best_gate]
    # Paper's table gives 12 dB; later prose gives 10 dB. Default follows Table I.
    valid = best_snr >= cfg.snr_threshold_db
    state = np.where(valid & (best_range < cfg.range_zone_near_m), "PRESENT",
             np.where(valid & (best_range < cfg.range_zone_far_m), "APPROACH_LEAVE", "ABSENT"))
    # Three-state majority vote over the most recent M_maj decisions.
    # If all classes differ (a tie for an even/partial startup window), retain
    # the newest estimate. This makes the state output itself majority-filtered.
    voted_state = state.copy()
    k = max(1, int(cfg.majority_frames))
    for i in range(len(state)):
        lo = max(0, i - k + 1)
        history = state[lo:i + 1]
        values, counts = np.unique(history, return_counts=True)
        winners = values[counts == counts.max()]
        voted_state[i] = state[i] if state[i] in winners else winners[0]
    binary = voted_state == "PRESENT"
    return {
        "range_gate_series": ranges,
        "filtered_range_series": filtered,
        "doppler_power": doppler_power,
        "doppler_velocity_m_s": velocity,
        "snr_db": snr_db,
        "peak_power_db": peak_db,
        "best_range_m": best_range,
        "best_snr_db": best_snr,
        "state_raw": state,
        "state": voted_state,
        "present_raw": state == "PRESENT",
        "present": binary,
        "range_resolution_m": cfg.range_resolution_m,
        "config": cfg,
    }
