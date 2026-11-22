#!/usr/bin/env python3
"""Validate the downloaded RF-DS sample dataset before running experiments."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED = {
    'walking_HP': ('csi.csv', 'labels.csv'),
    'walking_LENOVO': ('csi.csv', 'labels.csv'),
    'Breathing_HP': ('csi.csv',),
}
CSI_RE = re.compile(r'^csi[12]-(\d+)-(real|imag)$')

def validate_session(root: Path, name: str, files: tuple[str, ...]) -> dict:
    folder = root / name
    missing = [f for f in files if not (folder / f).is_file()]
    if missing:
        raise ValueError(f'{name}: missing files: {missing}')
    csi_path = folder / 'csi.csv'
    header = pd.read_csv(csi_path, nrows=0).columns.tolist()
    tones = sorted({int(m.group(1)) for col in header if (m := CSI_RE.match(col))})
    if len(tones) != 512 or tones != list(range(512)):
        raise ValueError(f'{name}: expected CSI tone indexes 0..511, found {len(tones)}')
    for stream in ('csi1', 'csi2'):
        for part in ('real', 'imag'):
            have = {int(m.group(1)) for col in header if (m := re.match(rf'^{stream}-(\d+)-{part}$', col))}
            if have != set(range(512)):
                raise ValueError(f'{name}: {stream} {part} fields incomplete')
    metadata_cols = ['unix_timestamp','channel','bandwidth_MHz','measurement_time_repetition_ms','frequency_carrier_MHz','subcarrier_number']
    meta = pd.read_csv(csi_path, usecols=[c for c in metadata_cols if c in header])
    if len(meta) < 100:
        raise ValueError(f'{name}: too few CSI rows ({len(meta)})')
    if not np.isfinite(meta['unix_timestamp']).all():
        raise ValueError(f'{name}: non-finite timestamps')
    dt = np.diff(meta['unix_timestamp'].to_numpy(dtype=np.float64))
    if np.any(dt < 0):
        raise ValueError(f'{name}: timestamps move backwards')
    rate = 1.0 / np.median(dt[dt > 0]) if np.any(dt > 0) else float('nan')
    if 'bandwidth_MHz' in meta and not np.allclose(meta.bandwidth_MHz, 160):
        raise ValueError(f'{name}: expected 160 MHz, got {meta.bandwidth_MHz.unique()}')
    if 'subcarrier_number' in meta and not np.all(meta.subcarrier_number == 512):
        raise ValueError(f'{name}: unexpected subcarrier_number values')
    report = {
        'name': name, 'rows': int(len(meta)), 'tones_per_ltf': 512,
        'channel': sorted(meta.channel.unique().tolist()) if 'channel' in meta else None,
        'bandwidth_MHz': sorted(meta.bandwidth_MHz.unique().tolist()) if 'bandwidth_MHz' in meta else None,
        'carrier_MHz': sorted(meta.frequency_carrier_MHz.unique().tolist()) if 'frequency_carrier_MHz' in meta else None,
        'nominal_repetition_ms': sorted(meta.measurement_time_repetition_ms.unique().tolist()) if 'measurement_time_repetition_ms' in meta else None,
        'median_positive_interval_ms': float(np.median(dt[dt > 0]) * 1000) if np.any(dt > 0) else None,
        'zero_interval_rows': int(np.sum(dt == 0)),
        'negative_interval_rows': int(np.sum(dt < 0)),
        'effective_median_rate_hz': float(rate) if np.isfinite(rate) else None,
        'duration_s': float(meta.unix_timestamp.iloc[-1] - meta.unix_timestamp.iloc[0]),
        'files': {f: {'bytes': (folder/f).stat().st_size} for f in files},
    }
    if 'labels.csv' in files:
        labels = pd.read_csv(folder/'labels.csv')
        required = {'Label','Start Time','End Time','Start Frame','End Frame'}
        if not required.issubset(labels.columns):
            raise ValueError(f'{name}: label columns missing {sorted(required-set(labels.columns))}')
        if np.any(labels['End Time'].to_numpy() <= labels['Start Time'].to_numpy()):
            raise ValueError(f'{name}: invalid label interval')
        report['labels'] = int(len(labels))
        report['label_values'] = labels.Label.astype(str).value_counts().to_dict()
        # Report frame-index and timestamp agreement without assuming exact 1:1
        # indexing: packet timestamps can repeat and video labels are intervals.
        report['label_coverage_s'] = float((labels['End Time'] - labels['Start Time']).sum()/1000)
    return report

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); p.add_argument('--output',type=Path); a=p.parse_args()
    root=a.root.resolve()
    readme=root/'README.md'
    if not readme.is_file(): raise SystemExit(f'Missing dataset README: {readme}')
    reports=[validate_session(root,n,files) for n,files in REQUIRED.items()]
    result={'dataset_root':str(root),'sessions':reports,'status':'PASS','notes':['This validates files and metadata, not signal correctness or model performance.','Breathing_HP has no labels.csv in the published sample package.']}
    out=json.dumps(result,indent=2); print(out)
    if a.output: a.output.write_text(out+'\n')
if __name__=='__main__': main()
