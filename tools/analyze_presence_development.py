#!/usr/bin/env python3
"""Development-only grouped analysis of interleaved CSI sessions.

Defaults to development Sessions 1 and 2. Additional development sessions
may be supplied explicitly. The reserved held-out Session 3 is rejected by
its SHA-256 even if renamed. Requires NumPy from vendor/.venv.
"""
from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSIONS = (
    ROOT / 'data/presence_dataset/interleaved_20261122_180724.jsonl',
    ROOT / 'data/presence_dataset/interleaved_20261122_183204.jsonl',
)
HELD_OUT_SESSION_3_SHA256 = '9c2bfa791fbb67c511330aef9207dad74be32e388056930cd17522310ee1af57'
EXPECTED_ORDER = (
    ('ABSENT', 'PRESENT'),
    ('PRESENT', 'ABSENT'),
    ('ABSENT', 'PRESENT'),
    ('PRESENT', 'ABSENT'),
    ('ABSENT', 'PRESENT'),
)


def validate_development_sessions(sessions: tuple[Path, ...]) -> None:
    if len(sessions) < 2:
        raise ValueError('At least two development sessions are required.')
    if len(set(sessions)) != len(sessions):
        raise ValueError('Duplicate development session paths are not allowed.')
    for path in sessions:
        try:
            path.relative_to(ROOT)
        except ValueError as exc:
            raise ValueError(f'Development sessions must be inside the repository: {path}') from exc
        if not path.is_file():
            raise ValueError(f'Development session does not exist: {path}')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest == HELD_OUT_SESSION_3_SHA256 or '185040' in path.name or 'session_3' in path.name.lower():
            raise ValueError(f'Refusing reserved held-out Session 3: {path}')


def load_session(path: Path, session_number: int) -> list[dict]:
    metadata = None
    batches = []
    with path.open() as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f'{path}: invalid JSON line') from exc
            if item.get('record_type') == 'session_metadata':
                metadata = item
            elif item.get('record_type') == 'interleaved_presence_batch':
                batches.append(item)
    if not metadata or metadata.get('experiment') != 'five_round_interleaved_v1':
        raise ValueError(f'{path}: unsupported or missing session metadata')
    if len(batches) != 10:
        raise ValueError(f'{path}: expected 10 batches, found {len(batches)}')
    observed = {}
    for batch in batches:
        round_number = int(batch['round_number'])
        condition = str(batch['condition']).upper()
        if not 1 <= round_number <= 5 or condition not in ('ABSENT', 'PRESENT'):
            raise ValueError(f'{path}: invalid round/condition')
        key = (round_number, condition)
        if key in observed:
            raise ValueError(f'{path}: duplicate batch {key}')
        observed[key] = batch
        profiles = np.asarray(batch.get('profiles_db_centered', []), dtype=float)
        if profiles.ndim != 2 or profiles.shape[1] != 52 or not np.isfinite(profiles).all():
            raise ValueError(f'{path}: invalid 52-tone profile matrix in {key}')
        if len(profiles) != int(batch.get('valid_csi_profiles', -1)):
            raise ValueError(f'{path}: profile count mismatch in {key}')
        if int(batch.get('capture_attempts_audited', 0)) != 50:
            raise ValueError(f'{path}: expected 50 audited attempts in {key}')
        if not batch.get('csi_yield_gate_pass') or not batch.get('target_attribution_gate_pass'):
            raise ValueError(f'{path}: acquisition gate failed in {key}')
        if float(batch.get('rx_idle_fraction', 0)) != 1.0:
            raise ValueError(f'{path}: RX-idle gate not complete in {key}')
    for round_number, expected in enumerate(EXPECTED_ORDER, 1):
        actual = tuple(
            condition for condition in ('ABSENT', 'PRESENT')
            if (round_number, condition) in observed
        )
        if set(actual) != {'ABSENT', 'PRESENT'}:
            raise ValueError(f'{path}: round {round_number} lacks a paired condition')
        # Collector records order in started_at_utc; preserve the protocol order.
        ordered = sorted(
            (observed[(round_number, c)] for c in ('ABSENT', 'PRESENT')),
            key=lambda b: str(b.get('started_at_utc', '')),
        )
        if tuple(str(b['condition']).upper() for b in ordered) != expected:
            raise ValueError(f'{path}: round {round_number} order differs from protocol')
    ap_config = {(b.get('bssid'), b.get('channel')) for b in batches}
    if len(ap_config) != 1:
        raise ValueError(f'{path}: AP/channel changed within session')
    result = []
    for batch in batches:
        matrix = np.asarray(batch['profiles_db_centered'], dtype=float)
        result.append({
            'session': session_number,
            'round': int(batch['round_number']),
            'label': 1 if str(batch['condition']).upper() == 'PRESENT' else 0,
            'condition': str(batch['condition']).upper(),
            'matrix': matrix,
            'median_profile': np.median(matrix, axis=0),
            'median_tone_spread_db': float(np.median(np.std(matrix, axis=1))),
            'valid_profiles': int(len(matrix)),
            'attempts': int(batch['capture_attempts_audited']),
            'strict_csi_fraction': float(batch['strict_csi_fraction']),
            'target_attributed_fraction': float(batch['target_attributed_strict_csi_fraction']),
            'bssid': batch.get('bssid'),
            'channel': batch.get('channel'),
        })
    return result


def classification_metrics(labels: np.ndarray, predictions: np.ndarray) -> dict:
    tp = int(np.sum((labels == 1) & (predictions == 1)))
    tn = int(np.sum((labels == 0) & (predictions == 0)))
    fp = int(np.sum((labels == 0) & (predictions == 1)))
    fn = int(np.sum((labels == 1) & (predictions == 0)))
    sensitivity = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return {
        'n_batches': int(len(labels)),
        'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
        'accuracy': (tp + tn) / len(labels) if len(labels) else 0.0,
        'sensitivity': sensitivity,
        'specificity': specificity,
        'balanced_accuracy': (sensitivity + specificity) / 2,
    }


def nearest_centroid_scores(train: list[dict], test: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    x_train = np.vstack([row['median_profile'] for row in train])
    y_train = np.asarray([row['label'] for row in train], dtype=int)
    x_test = np.vstack([row['median_profile'] for row in test])
    y_test = np.asarray([row['label'] for row in test], dtype=int)
    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale < 1e-8] = 1.0
    x_train = (x_train - mean) / scale
    x_test = (x_test - mean) / scale
    centers = {label: x_train[y_train == label].mean(axis=0) for label in (0, 1)}
    # Positive score means closer to the PRESENT centroid.
    scores = np.sum((x_test - centers[0]) ** 2, axis=1) - np.sum((x_test - centers[1]) ** 2, axis=1)
    return y_test, (scores >= 0).astype(int)


def run_analysis(sessions: tuple[Path, ...]) -> dict:
    validate_development_sessions(sessions)
    rows = []
    for session_number, path in enumerate(sessions, 1):
        rows.extend(load_session(path, session_number))
    y_true, y_pred = [], []
    fold_results = []
    groups = sorted({(r['session'], r['round']) for r in rows})
    for held_session, held_round in groups:
        train = [r for r in rows if (r['session'], r['round']) != (held_session, held_round)]
        test = [r for r in rows if (r['session'], r['round']) == (held_session, held_round)]
        y, pred = nearest_centroid_scores(train, test)
        y_true.extend(y.tolist())
        y_pred.extend(pred.tolist())
        fold_results.append({
            'held_out_session': held_session,
            'held_out_round': held_round,
            **classification_metrics(y, pred),
        })
    grouped = classification_metrics(np.asarray(y_true), np.asarray(y_pred))

    transfer = {}
    session_numbers = sorted({r['session'] for r in rows})
    for test_session in session_numbers:
        train = [r for r in rows if r['session'] != test_session]
        test = [r for r in rows if r['session'] == test_session]
        y, pred = nearest_centroid_scores(train, test)
        train_sessions = [n for n in session_numbers if n != test_session]
        transfer[f'train_sessions_{train_sessions}_test_session_{test_session}'] = classification_metrics(y, pred)

    paired_rounds = []
    for session_number in sorted({r['session'] for r in rows}):
        for round_number in range(1, 6):
            absent = next(r for r in rows if r['session'] == session_number and r['round'] == round_number and r['label'] == 0)
            present = next(r for r in rows if r['session'] == session_number and r['round'] == round_number and r['label'] == 1)
            distance = float(np.sqrt(np.mean((absent['median_profile'] - present['median_profile']) ** 2)))
            spread_delta = present['median_tone_spread_db'] - absent['median_tone_spread_db']
            paired_rounds.append({
                'session': session_number, 'round': round_number,
                'absent_profiles': absent['valid_profiles'],
                'present_profiles': present['valid_profiles'],
                'median_profile_distance_db_rms': distance,
                'present_minus_absent_tone_spread_db': spread_delta,
            })

    counts = {
        'attempts': sum(r['attempts'] for r in rows),
        'valid_profiles': sum(r['valid_profiles'] for r in rows),
        'absent_profiles': sum(r['valid_profiles'] for r in rows if r['label'] == 0),
        'present_profiles': sum(r['valid_profiles'] for r in rows if r['label'] == 1),
        'batches': len(rows),
        'batches_passing_acquisition_gates': len(rows),
    }
    return {
        'analysis_scope': f'{len(sessions)} explicitly supplied development sessions; held-out Session 3 rejected by source hash and filename',
        'sessions': [str(p.relative_to(ROOT)) for p in sessions],
        'counts': counts,
        'grouped_leave_one_session_round_out_batch_metrics': grouped,
        'session_transfer_metrics': transfer,
        'paired_rounds': paired_rounds,
        'method': 'For each batch, take the per-tone median across valid CSI profiles. Standardize using training batches only, fit two class centroids, and classify the held-out paired round by nearest centroid. The two batches in a held-out session-round are kept together.',
        'interpretation': 'Exploratory batch-level diagnostic only. Paired-round count and cross-session transfer results must be considered; no occupancy detector is justified unless performance is stable across independent development sessions.',
        'detector_frozen': False,
        'held_out_session_3_touched': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, action='append', help='development session JSONL; repeat for each session. Defaults to Sessions 1 and 2. Reserved Session 3 is rejected.')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs' / 'PRESENCE_DEVELOPMENT_ANALYSIS_20261122.json')
    args = parser.parse_args()
    sessions = tuple(p.resolve() for p in (args.session or DEFAULT_SESSIONS))
    try:
        validate_development_sessions(sessions)
    except ValueError as exc:
        parser.error(str(exc))
    report = run_analysis(sessions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({
        'counts': report['counts'],
        'grouped_leave_one_session_round_out_batch_metrics': report['grouped_leave_one_session_round_out_batch_metrics'],
        'session_transfer_metrics': report['session_transfer_metrics'],
        'output': str(args.output),
        'held_out_session_3_touched': False,
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
