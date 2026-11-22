#!/usr/bin/env python3
"""Fit a temporal-variation Extra Trees demo model on development sessions only.

Uses per-tone temporal MAD and standard deviation across each batch's CSI
profiles. This is experimental and not validated for occupancy decisions.
The consumed held-out Session 3 is never read.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
import analyze_presence_development as dev

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / 'models' / 'presence_temporal_extra_trees_dev_v1.joblib'
METADATA_PATH = ROOT / 'models' / 'presence_temporal_extra_trees_dev_v1.json'
CONFIG = {
    'n_estimators': 250,
    'max_depth': 2,
    'min_samples_leaf': 2,
    'max_features': 'sqrt',
    'class_weight': 'balanced',
    'random_state': 42,
    'n_jobs': 1,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def temporal_features(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != 52 or len(matrix) < 5 or not np.isfinite(matrix).all():
        raise ValueError(f'Expected at least 5 finite 52-tone profiles, got {matrix.shape}')
    center = np.median(matrix, axis=0)
    mad = np.median(np.abs(matrix - center), axis=0)
    std = np.std(matrix, axis=0)
    return np.concatenate((mad, std))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace', action='store_true', help='replace only this temporal demo model and metadata')
    args = parser.parse_args()
    if (MODEL_PATH.exists() or METADATA_PATH.exists()) and not args.replace:
        raise SystemExit('Temporal demo model already exists; refusing overwrite. Use --replace only if intentional.')
    sessions = tuple(dev.DEFAULT_SESSIONS)
    dev.validate_development_sessions(sessions)
    rows = []
    session_meta = []
    for path in sessions:
        sid = dev.session_id_for_path(path)
        rows.extend(dev.load_session(path, sid))
        session_meta.append({'session': sid, 'path': str(path.relative_to(ROOT)), 'sha256': sha256(path)})
    X = np.vstack([temporal_features(r['matrix']) for r in rows])
    y = np.asarray([r['label'] for r in rows], dtype=int)
    if X.shape != (40, 104) or int(np.sum(y == 0)) != 20 or int(np.sum(y == 1)) != 20:
        raise RuntimeError(f'Unexpected development training data shape/class balance: {X.shape}, labels={np.bincount(y).tolist()}')
    estimator = ExtraTreesClassifier(**CONFIG)
    estimator.fit(X, y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(estimator, MODEL_PATH)
    metadata = {
        'model_id': 'temporal_extra_trees_all_development_sessions_v1',
        'model_type': 'experimental_demo_classifier',
        'training_sessions': session_meta,
        'training_examples': int(len(y)),
        'class_counts': {'ABSENT': int(np.sum(y == 0)), 'PRESENT': int(np.sum(y == 1))},
        'feature_definition': '104 features: per-tone median absolute deviation (52) followed by per-tone standard deviation (52), calculated across accepted individually median-centered CSI profiles in each 50-attempt batch',
        'configuration': CONFIG,
        'training_scope': 'Sessions 1, 2, 4 and 5 only; held-out Session 3 was not accessed.',
        'cross_validation_reference': {
            'grouped_leave_one_session_round_out': {'balanced_accuracy': 0.875, 'sensitivity': 0.75, 'specificity': 1.0, 'false_positives': 0, 'false_negatives': 5},
            'leave_one_development_session_out': {'balanced_accuracy': 0.875, 'sensitivity': 0.75, 'specificity': 1.0, 'false_positives': 0, 'false_negatives': 5},
        },
        'deployment_status': 'EXPERIMENTAL_NOT_VALIDATED_FOR_OCCUPANCY_DECISIONS',
        'note': 'Selected as a research demo candidate because temporal-only features performed better in development grouped and leave-one-session-out comparisons than median-profile-only features. Small sample; model selection used development data; metrics are not independent validation. Session 3 was not accessed or reused.',
    }
    metadata['artifact_sha256'] = sha256(MODEL_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'model_path': str(MODEL_PATH.relative_to(ROOT)), 'metadata_path': str(METADATA_PATH.relative_to(ROOT)), 'model_id': metadata['model_id'], 'training_examples': len(y), 'feature_count': int(X.shape[1]), 'class_counts': metadata['class_counts'], 'model_sha256': metadata['artifact_sha256'], 'held_out_session_3_accessed': False}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
