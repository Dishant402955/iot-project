#!/usr/bin/env python3
"""Freeze the fixed nearest-centroid research benchmark from Sessions 1 and 2.

This is a baseline experiment, not a validated or deployable occupancy model.
It intentionally uses no held-out data and refuses to overwrite an existing
frozen model artifact.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import analyze_presence_development as dev

ROOT = Path(__file__).resolve().parents[1]
SESSION_PATHS = (
    ROOT / 'data/presence_dataset/interleaved_20261122_180724.jsonl',
    ROOT / 'data/presence_dataset/interleaved_20261122_183204.jsonl',
)
EXPECTED_HASHES = (
    'c18489c749c1b7e55effbe2c42a3a4c9a88cd39110419264d1c6f43b93c70836',
    '4faca4b438b6bba0bfb2572fa5c4f4cf59558c780d815762f78fb18f51e5f553',
)
DEFAULT_OUTPUT = ROOT / 'models' / 'presence_centroid_baseline_s1_s2_v1.json'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_model(sessions: tuple[Path, ...] = SESSION_PATHS) -> dict:
    if tuple(sessions) != tuple(SESSION_PATHS):
        raise ValueError('The frozen benchmark must use exactly development Sessions 1 and 2.')
    hashes = tuple(sha256(p) for p in sessions)
    if hashes != EXPECTED_HASHES:
        raise ValueError('Development source hashes differ from the reviewed Sessions 1 and 2.')
    dev.validate_development_sessions(sessions)
    rows = []
    for number, path in enumerate(sessions, 1):
        rows.extend(dev.load_session(path, number))
    if len(rows) != 20 or sum(r['label'] == 0 for r in rows) != 10 or sum(r['label'] == 1 for r in rows) != 10:
        raise ValueError('Expected exactly 20 development batches, 10 per class.')
    x = np.vstack([r['median_profile'] for r in rows])
    y = np.asarray([r['label'] for r in rows], dtype=int)
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-8] = 1.0
    z = (x - mean) / scale
    centers = {label: z[y == label].mean(axis=0) for label in (0, 1)}
    return {
        'schema_version': 1,
        'model_id': 'profile_median_nearest_centroid_sessions_1_2_v1',
        'model_type': 'research_baseline_only',
        'frozen_date': '2026-11-22',
        'feature_definition': '52-dimensional per-batch median of accepted per-capture centered CSI magnitude profiles, ordered tones -26..-1,+1..+26',
        'preprocessing': 'Standardize each tone using mean and population standard deviation across the 20 training batch profiles. Replace scales below 1e-8 with 1.0.',
        'decision_rule': 'Compute squared Euclidean distance to the ABSENT and PRESENT centroids in standardized space. Predict PRESENT when distance_absent - distance_present >= 0; otherwise ABSENT.',
        'training_sessions': [
            {'session': 1, 'path': str(sessions[0].relative_to(ROOT)), 'sha256': hashes[0]},
            {'session': 2, 'path': str(sessions[1].relative_to(ROOT)), 'sha256': hashes[1]},
        ],
        'training_batch_counts': {'total': 20, 'absent': 10, 'present': 10},
        'scaler_mean': mean.tolist(),
        'scaler_scale': scale.tolist(),
        'centroid_absent': centers[0].tolist(),
        'centroid_present': centers[1].tolist(),
        'held_out_session_3_used': False,
        'deployment_status': 'NOT_VALIDATED_NOT_FOR_OCCUPANCY_DECISIONS',
        'known_development_limitations': 'Grouped leave-one-session-round-pair-out sensitivity 0.60; cross-session transfer sensitivity 0.00 in both directions. Frozen only to obtain a one-time independent benchmark result, not because development performance is acceptable.',
    }


def main() -> int:
    output = DEFAULT_OUTPUT
    if output.exists():
        raise SystemExit(f'Refusing to overwrite frozen model: {output}')
    model = build_model()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(model, indent=2) + '\n')
    print(json.dumps({'model_path': str(output.relative_to(ROOT)), 'model_id': model['model_id'],
                      'training_batch_counts': model['training_batch_counts'],
                      'held_out_session_3_used': model['held_out_session_3_used'],
                      'model_sha256': sha256(output)}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
