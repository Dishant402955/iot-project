"""Supervised, per-device CSI baseline for the released labelled sessions.

This is deliberately separate from the paper's RF-DS detector. It provides a
measurable fallback for dataset replay and quantifies cross-device generalization.
It is not a validated live RTL8821CE model.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, classification_report
from sklearn.model_selection import GroupShuffleSplit
from dataset import load_csi_csv
from evaluate_labels import states_at_timestamps
from rfds import RFDSConfig, range_gate_series

CLASSES = ['PRESENT', 'APPROACH_LEAVE', 'ABSENT']


def extract_features(csv_path: str | Path, window: int = 32, hop: int = 8):
    csi, meta = load_csi_csv(csv_path, chunksize=128)
    labels_path = Path(csv_path).parent / 'labels.csv'
    labels = pd.read_csv(labels_path)
    timestamps = meta['unix_timestamp'].to_numpy(dtype=np.float64)
    amplitudes = np.abs(csi)
    rows, targets, groups, centers = [], [], [], []
    for start in range(0, len(csi) - window + 1, hop):
        # Keep every feature window wholly inside one temporal group. This
        # prevents overlapping CSI frames from leaking across train/test groups.
        if (start % 320) > (320 - window):
            continue
        center = start + (window - 1) / 2.0
        timestamp = float(np.interp(center, np.arange(len(timestamps)), timestamps))
        target = states_at_timestamps(labels, np.asarray([timestamp]))[0]
        if target == 'UNKNOWN':
            continue
        amp = amplitudes[start:start + window]
        # Normalize locally within this window, never using held-out session
        # statistics. This removes per-tone gain without test-set leakage.
        tone_median = np.median(amp, axis=0)
        tone_mad = np.median(np.abs(amp - tone_median), axis=0) * 1.4826 + 1.0
        norm = (amp - tone_median) / tone_mad
        z = csi[start:start + window]
        d_amp = np.diff(amp, axis=0)
        d_phase = np.angle(z[1:] * np.conj(z[:-1]))
        features = []
        for block in (np.log1p(amp), norm, d_amp, d_phase):
            features.extend((np.mean(block, axis=0), np.std(block, axis=0),
                             np.percentile(block, 90, axis=0) - np.percentile(block, 10, axis=0)))
        # Range-gate temporal features add a compact range-aware representation.
        rg = range_gate_series(z, RFDSConfig())
        rg_amp = np.abs(rg)
        rg_delta = np.abs(np.diff(rg, axis=0))
        for block in (rg_amp, rg_delta):
            features.extend((np.mean(block, axis=0), np.std(block, axis=0), np.max(block, axis=0)))
        rows.append(np.concatenate([np.asarray(f).ravel() for f in features]).astype(np.float32))
        targets.append(target)
        groups.append(int(start // 320))  # keep contiguous 3.2 s regions together
        centers.append(timestamp)
    return np.vstack(rows), np.asarray(targets), np.asarray(groups), np.asarray(centers)


def make_model():
    return ExtraTreesClassifier(n_estimators=400, min_samples_leaf=3, max_features='sqrt',
                                class_weight='balanced', n_jobs=-1, random_state=42)


def evaluate_grouped(csv_path: str | Path, output: str | Path | None = None):
    X, y, groups, _ = extract_features(csv_path)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=42)
    train, test = next(splitter.split(X, y, groups))
    model = make_model().fit(X[train], y[train])
    predicted = model.predict(X[test])
    report = {
        'source': str(csv_path), 'method': 'ExtraTrees per-device supervised baseline (not RF-DS)',
        'split': '70/30 contiguous-group holdout; groups are 3.2-second segments',
        'samples': int(len(y)), 'train_samples': int(len(train)), 'test_samples': int(len(test)),
        'accuracy': float(accuracy_score(y[test], predicted)),
        'balanced_accuracy': float(balanced_accuracy_score(y[test], predicted)),
        'classes': CLASSES,
        'confusion_matrix': confusion_matrix(y[test], predicted, labels=CLASSES).tolist(),
        'classification_report': classification_report(y[test], predicted, labels=CLASSES, output_dict=True, zero_division=0),
        'limitation': 'Only two labelled sessions exist. This result is within-session validation and does not establish cross-device or live RTL8821CE performance.'
    }
    if output:
        Path(output).write_text(json.dumps(report, indent=2))
    return report, model


def train_full(csv_path: str | Path, model_path: str | Path):
    X, y, _, _ = extract_features(csv_path)
    model = make_model().fit(X, y)
    payload = {'model': model, 'feature_version': 1, 'source': str(csv_path),
               'classes': CLASSES, 'window_frames': 32, 'hop_frames': 8}
    joblib.dump(payload, model_path)
    return len(y), X.shape[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('csv', type=Path)
    p.add_argument('--report', type=Path)
    p.add_argument('--train-model', type=Path)
    a = p.parse_args()
    report, _ = evaluate_grouped(a.csv, a.report)
    print(json.dumps(report, indent=2))
    if a.train_model:
        count, dimensions = train_full(a.csv, a.train_model)
        print(f'Trained full-session model: {count} windows, {dimensions} features -> {a.train_model}')

if __name__ == '__main__':
    main()
