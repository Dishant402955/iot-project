#!/usr/bin/env python3
"""Live inference using the final-fit development temporal Extra Trees model.

The model predicts PRESENT/ABSENT from a fresh strict-quality CSI batch. This
is an experimental research demo, not a validated or deployable occupancy
system. The saved empty-room anomaly baseline is not used for classification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

import joblib
import numpy as np

import live_presence_detector as live

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / 'models' / 'presence_temporal_extra_trees_dev_v1.joblib'
METADATA_PATH = ROOT / 'models' / 'presence_temporal_extra_trees_dev_v1.json'
BATCH_CAPTURES = 50
MIN_VALID_CSI = 5
EXPECTED_BSSID = '36:9f:61:c1:00:9f'
EXPECTED_CHANNEL = 149


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_model():
    if not MODEL_PATH.is_file() or not METADATA_PATH.is_file():
        raise RuntimeError('Temporal Extra Trees demo model or its metadata is missing. Run tools/train_presence_demo_model.py first.')
    metadata = json.loads(METADATA_PATH.read_text())
    digest = sha256(MODEL_PATH)
    if digest != metadata.get('artifact_sha256'):
        raise RuntimeError('Demo model SHA256 mismatch; refusing inference.')
    if metadata.get('model_id') != 'temporal_extra_trees_all_development_sessions_v1':
        raise RuntimeError('Unexpected temporal Extra Trees demo model ID; refusing inference.')
    if 'held-out Session 3 was not accessed' not in metadata.get('training_scope', ''):
        raise RuntimeError('Model provenance check failed.')
    model = joblib.load(MODEL_PATH)
    if model.__class__.__name__ != 'ExtraTreesClassifier' or not hasattr(model, 'predict') or list(model.classes_) != [0, 1]:
        raise RuntimeError('Loaded artifact is not the expected temporal Extra Trees binary classifier.')
    return model, metadata


def infer(profiles: list[np.ndarray], model) -> dict:
    if len(profiles) < MIN_VALID_CSI:
        raise RuntimeError(f'INSUFFICIENT_CSI: {len(profiles)}/{BATCH_CAPTURES}; refusing to predict.')
    matrix = np.asarray(profiles, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != 52 or not np.isfinite(matrix).all():
        raise RuntimeError('Invalid CSI feature matrix; refusing to predict.')
    # Match training: temporal variation across the batch, not the static
    # per-tone median profile. Order is 52 MAD values followed by 52 std values.
    center = np.median(matrix, axis=0)
    temporal_mad = np.median(np.abs(matrix - center), axis=0)
    temporal_std = np.std(matrix, axis=0)
    feature = np.concatenate((temporal_mad, temporal_std)).reshape(1, -1)
    prediction = int(model.predict(feature)[0])
    votes = model.predict_proba(feature)[0]
    return {
        'prediction': 'PRESENT' if prediction == 1 else 'ABSENT',
        'absent_vote_fraction': float(votes[list(model.classes_).index(0)]),
        'present_vote_fraction': float(votes[list(model.classes_).index(1)]),
        'valid_profiles': len(profiles),
        'median_temporal_mad_db': float(np.median(temporal_mad)),
        'median_temporal_std_db': float(np.median(temporal_std)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true', help='capture one batch and exit; default is continuous demo')
    parser.add_argument('--step', action='store_true', help='wait for Enter after each batch before capturing the next')
    args = parser.parse_args()
    if args.once and args.step:
        parser.error('--once and --step cannot be used together')
    if os.geteuid() != 0:
        raise SystemExit('Run at the physical laptop console with sudo.')
    model, metadata = load_model()
    print('LIVE MODEL DEMO: temporal Extra Trees trained on all development sessions', flush=True)
    print(f"model={metadata['model_id']} training_examples={metadata['training_examples']} classes={metadata['class_counts']}", flush=True)
    print('PRESENT/ABSENT is an experimental model prediction, NOT a validated occupancy decision.', flush=True)
    print('Each inference uses one fresh 50-attempt CSI batch. Ctrl+C to stop.', flush=True)
    if args.step:
        print('Step mode: press Enter to capture the next batch.', flush=True)
    while True:
        profiles, bssid, channel, run_dir = live.capture_batch(BATCH_CAPTURES)
        if bssid != EXPECTED_BSSID or channel is None or int(channel) != EXPECTED_CHANNEL:
            raise RuntimeError(f'AP mismatch: expected {EXPECTED_BSSID} channel {EXPECTED_CHANNEL}, got {bssid} channel {channel}; refusing inference.')
        if len(profiles) < MIN_VALID_CSI:
            print(f'INSUFFICIENT_CSI valid={len(profiles)}/{BATCH_CAPTURES}; MODEL NOT RUN; latest={run_dir}', flush=True)
        else:
            result = infer(profiles, model)
            print(
                f"MODEL_PREDICTION={result['prediction']} (EXPERIMENTAL_UNVALIDATED) "
                f"valid_CSI={result['valid_profiles']}/{BATCH_CAPTURES} "
                f"model_vote_absent={result['absent_vote_fraction']:.3f} "
                f"model_vote_present={result['present_vote_fraction']:.3f} "
                f"temporal_MAD={result['median_temporal_mad_db']:.3f}dB "
                f"temporal_STD={result['median_temporal_std_db']:.3f}dB latest={run_dir}",
                flush=True,
            )
        if args.once:
            return 0 if len(profiles) >= MIN_VALID_CSI else 2
        if args.step:
            try:
                input('Press Enter for the next batch, or Ctrl+C to stop... ')
            except EOFError:
                print('Input closed; stopping step mode.', flush=True)
                return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nStopped. Capture cleanup restores the Wi-Fi driver after each batch.', flush=True)
