#!/usr/bin/env python3
"""Run RF-DS against one of the paper's calibrated CSI recordings."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dataset import load_csi_csv
from rfds import RFDSConfig, detect_presence, get_range_gates

p = argparse.ArgumentParser()
p.add_argument('csv', type=Path)
p.add_argument('--output-dir', type=Path, default=Path('research/rfds-reproduction/outputs'))
p.add_argument('--max-frames', type=int)
p.add_argument('--threshold-db', type=float, default=12.0)
p.add_argument('--fir-cutoff-nyquist', type=float, default=0.04)
p.add_argument('--clip-delta-db', type=float, default=6.0)
p.add_argument('--hop-frames', type=int, default=1)
a = p.parse_args()
a.output_dir.mkdir(parents=True, exist_ok=True)
csi, meta = load_csi_csv(a.csv, max_frames=a.max_frames)
bw = float(meta['bandwidth_MHz'].median()) * 1e6 if 'bandwidth_MHz' in meta else 160e6
fc = float(meta['frequency_carrier_MHz'].median()) * 1e6 if 'frequency_carrier_MHz' in meta else 6300e6
interval = float(meta['measurement_time_repetition_ms'].median()) if 'measurement_time_repetition_ms' in meta else 10.0
cfg = RFDSConfig(bandwidth_hz=bw, carrier_hz=fc, frame_rate_hz=1000.0 / interval,
                 snr_threshold_db=a.threshold_db, fir_cutoff_nyquist=a.fir_cutoff_nyquist,
                 clip_delta_db=a.clip_delta_db, hop_frames=a.hop_frames)
result = detect_presence(csi, cfg)
summary = {
    'source_csv': str(a.csv), 'frames': int(csi.shape[0]), 'tones': int(csi.shape[1]),
    'bandwidth_hz': bw, 'carrier_hz': fc, 'frame_rate_hz': cfg.frame_rate_hz,
    'range_resolution_m': result['range_resolution_m'],
    'range_gates_m': get_range_gates(cfg).tolist(),
    'config': {k: v for k, v in cfg.__dict__.items()},
    'decision_windows': int(len(result['present'])),
    'present_fraction': float(np.mean(result['present'])),
    'state_counts': {str(k): int(v) for k, v in zip(*np.unique(result['state'], return_counts=True))},
    'mean_best_snr_db': float(np.mean(result['best_snr_db'])),
    'median_best_range_m': float(np.median(result['best_range_m'])),
    'warning': 'Dataset results are not live RTL8821CE results. FIR cutoff, clipping offset, Doppler window type, and exact tone-frequency mapping are not fully specified in paper text; defaults are tunable/nominal.'
}
prefix = a.output_dir / a.csv.parent.name
np.savez_compressed(str(prefix) + '_rfds.npz', snr_db=result['snr_db'],
                    best_range_m=result['best_range_m'], best_snr_db=result['best_snr_db'],
                    state=result['state'], present=result['present'],
                    doppler_velocity_m_s=result['doppler_velocity_m_s'])
centers = (np.arange(len(result['present'])) * cfg.hop_frames +
           (cfg.detection_window_frames - 1) * cfg.hop_frames / 2.0 +
           (cfg.frames_per_window - 1) / 2.0)
center_times = np.interp(centers, np.arange(len(meta)), meta['unix_timestamp'].to_numpy(dtype=np.float64))
pd.DataFrame({'center_frame_index': centers, 'center_unix_timestamp': center_times,
              'state': result['state'], 'present': result['present'],
              'best_range_m': result['best_range_m'], 'best_snr_db': result['best_snr_db']}).to_csv(
                  str(prefix) + '_decisions.csv', index=False)
Path(str(prefix) + '_summary.json').write_text(json.dumps(summary, indent=2))

# RF-DS time-Doppler view for the range gate with the highest mean SNR.
selected_gate = int(np.argmax(result['snr_db'].mean(axis=0)))
map_db = 10.0 * np.log10(np.maximum(result['doppler_power'][:, selected_gate, :], 1e-24))
time_s = np.arange(map_db.shape[0]) * cfg.hop_frames / cfg.frame_rate_hz
velocity = result['doppler_velocity_m_s']
fig, axes = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)
image = axes[0].imshow(map_db.T, origin='lower', aspect='auto', cmap='viridis',
    extent=[time_s[0], time_s[-1] if len(time_s) > 1 else time_s[0] + 1/cfg.frame_rate_hz,
            velocity[0], velocity[-1]])
axes[0].set_title(f'RF-DS time-Doppler spectrum at range gate {selected_gate} ({get_range_gates(cfg)[selected_gate]:.2f} m)')
axes[0].set_xlabel('Time (s)')
axes[0].set_ylabel('Radial velocity (m/s)')
fig.colorbar(image, ax=axes[0], label='Power (dB)')
axes[1].plot(np.arange(len(result['best_range_m'])) / cfg.frame_rate_hz,
             result['best_range_m'], label='Estimated range')
axes[1].axhline(cfg.range_zone_near_m, linestyle='--', label='Near-zone boundary')
axes[1].axhline(cfg.range_zone_far_m, linestyle=':', label='Far-zone boundary')
axes[1].set_xlabel('Time (s)')
axes[1].set_ylabel('Range (m)')
axes[1].legend(loc='upper right')
fig.savefig(str(prefix) + '_rfds.png', dpi=140)
plt.close(fig)
print(json.dumps(summary, indent=2))
