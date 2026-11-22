#!/usr/bin/env python3
"""Evaluate the frozen Sessions 1/2 benchmark exactly once on held-out Session 3.

The evaluator verifies immutable source/model hashes and refuses to overwrite
its JSON or Markdown result. It performs no tuning, training, or threshold
selection. The result is a research benchmark, never a deployment decision.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import analyze_presence_development as dev

ROOT = Path(__file__).resolve().parents[1]
SESSION_3 = ROOT / 'data/presence_dataset/interleaved_20261122_185040.jsonl'
MODEL_PATH = ROOT / 'models/presence_centroid_baseline_s1_s2_v1.json'
EXPECTED_SESSION_3_SHA256 = '9c2bfa791fbb67c511330aef9207dad74be32e388056930cd17522310ee1af57'
EXPECTED_MODEL_SHA256 = '43560a6e2c5f9ca67c81c07e732fb990fd1fff49c792565df04ea448a2a25b02'
JSON_OUTPUT = ROOT / 'docs' / 'HELD_OUT_EVALUATION_SESSION3_20261122.json'
MD_OUTPUT = ROOT / 'docs' / 'HELD_OUT_EVALUATION_SESSION3_20261122.md'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify_batch(profile: np.ndarray, model: dict) -> tuple[int, float, float]:
    mean = np.asarray(model['scaler_mean'], dtype=float)
    scale = np.asarray(model['scaler_scale'], dtype=float)
    absent = np.asarray(model['centroid_absent'], dtype=float)
    present = np.asarray(model['centroid_present'], dtype=float)
    if any(v.shape != (52,) or not np.isfinite(v).all() for v in (mean, scale, absent, present)):
        raise ValueError('Frozen model contains invalid 52-tone parameters.')
    if np.any(scale <= 0):
        raise ValueError('Frozen model contains non-positive scaling values.')
    z = (profile - mean) / scale
    d_absent = float(np.sum((z - absent) ** 2))
    d_present = float(np.sum((z - present) ** 2))
    score = d_absent - d_present
    return (1 if score >= 0 else 0), d_absent, d_present


def confusion_metrics(rows: list[dict]) -> dict:
    tp = sum(r['truth'] == 1 and r['prediction'] == 1 for r in rows)
    tn = sum(r['truth'] == 0 and r['prediction'] == 0 for r in rows)
    fp = sum(r['truth'] == 0 and r['prediction'] == 1 for r in rows)
    fn = sum(r['truth'] == 1 and r['prediction'] == 0 for r in rows)
    sensitivity = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    return {
        'n_batches': len(rows), 'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
        'accuracy': (tp + tn) / len(rows) if rows else 0.0,
        'sensitivity': sensitivity, 'specificity': specificity,
        'balanced_accuracy': (sensitivity + specificity) / 2,
        'precision': precision,
        'f1': 2 * precision * sensitivity / (precision + sensitivity) if precision + sensitivity else 0.0,
    }


def evaluate(model: dict, rows: list[dict]) -> dict:
    predictions = []
    for row in rows:
        pred, d0, d1 = classify_batch(row['median_profile'], model)
        predictions.append({
            'session': row['session'], 'round': row['round'],
            'condition': row['condition'], 'truth': row['label'],
            'prediction': pred, 'prediction_label': 'PRESENT' if pred else 'ABSENT',
            'distance_absent': d0, 'distance_present': d1,
            'valid_profiles': row['valid_profiles'], 'attempts': row['attempts'],
        })
    return {
        'metrics': confusion_metrics(predictions),
        'predictions_by_batch': predictions,
        'valid_profiles': sum(r['valid_profiles'] for r in rows),
        'attempts': sum(r['attempts'] for r in rows),
        'acquisition_batches': len(rows),
        'acquisition_batches_passing_gates': len(rows),
        'insufficient_csi_batches': 0,
    }


def render_markdown(result: dict) -> str:
    m = result['metrics']
    lines = [
        '# One-time held-out evaluation: Session 3', '',
        '**Date:** 2026-11-22  ',
        '**Model:** `profile_median_nearest_centroid_sessions_1_2_v1`  ',
        '**Status:** Research benchmark only; not a deployable occupancy detector.', '',
        '## Integrity', '',
        '- Frozen model was trained only on Sessions 1 and 2.',
        '- Session 3 source hash was verified before evaluation.',
        '- No training, feature selection, threshold selection, or tuning was performed on Session 3.',
        '- The evaluator refuses to overwrite this result. This is the one permitted evaluation.', '',
        '## Acquisition availability', '',
        f"- Strict CSI profiles: {result['valid_profiles']}/{result['attempts']} ({result['valid_profiles']/result['attempts']:.1%}).",
        f"- Batches passing acquisition gates: {result['acquisition_batches_passing_gates']}/{result['acquisition_batches']}.",
        f"- Insufficient-CSI batches: {result['insufficient_csi_batches']}.", '',
        '## Batch-level classification', '',
        '| TP | TN | FP | FN | Accuracy | Sensitivity | Specificity | Balanced accuracy | Precision | F1 |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
        f"| {m['tp']} | {m['tn']} | {m['fp']} | {m['fn']} | {m['accuracy']:.3f} | {m['sensitivity']:.3f} | {m['specificity']:.3f} | {m['balanced_accuracy']:.3f} | {m['precision']:.3f} | {m['f1']:.3f} |", '',
        '## Per-batch predictions', '',
        '| Round | Ground truth | Prediction | Valid CSI |',
        '|---:|---|---|---:|',
    ]
    for r in result['predictions_by_batch']:
        lines.append(f"| {r['round']} | {r['condition']} | {r['prediction_label']} | {r['valid_profiles']}/{r['attempts']} |")
    lines += ['', '## Interpretation', '',
              'This is a single held-out session with ten batch-level observations. Do not infer generalization across rooms, people, devices, or APs. Do not tune the frozen model using these results. The model remains a research benchmark and must not drive occupancy decisions. A revised model requires new development data and a new untouched held-out session.', '']
    return '\n'.join(lines)


def main() -> int:
    if JSON_OUTPUT.exists() or MD_OUTPUT.exists():
        raise SystemExit('Held-out evaluation output already exists. Refusing to rerun or overwrite Session 3 evaluation.')
    if sha256(MODEL_PATH) != EXPECTED_MODEL_SHA256:
        raise SystemExit('Frozen model hash mismatch. Refusing evaluation.')
    if sha256(SESSION_3) != EXPECTED_SESSION_3_SHA256:
        raise SystemExit('Held-out Session 3 hash mismatch. Refusing evaluation.')
    model = json.loads(MODEL_PATH.read_text())
    if model.get('held_out_session_3_used') is not False or model.get('deployment_status') != 'NOT_VALIDATED_NOT_FOR_OCCUPANCY_DECISIONS':
        raise SystemExit('Model metadata does not match the reviewed frozen benchmark.')
    rows = dev.load_session(SESSION_3, 3)
    if len(rows) != 10 or sum(r['valid_profiles'] for r in rows) != 497:
        raise SystemExit('Held-out Session 3 shape/count differs from the reviewed collection record.')
    result = evaluate(model, rows)
    payload = {
        'evaluation_scope': 'one-time held-out evaluation of frozen Sessions 1/2 centroid benchmark',
        'held_out_session_3_sha256': EXPECTED_SESSION_3_SHA256,
        'frozen_model_sha256': EXPECTED_MODEL_SHA256,
        'model_id': model['model_id'],
        'held_out_session_3_touched': True,
        'training_sessions': model['training_sessions'],
        **result,
        'interpretation': 'One-session, ten-batch research benchmark only. No tuning or retraining is permitted using this result. This model is not a validated occupancy detector.',
    }
    markdown = render_markdown(payload)
    JSON_OUTPUT.write_text(json.dumps(payload, indent=2) + '\n')
    MD_OUTPUT.write_text(markdown)
    print(json.dumps({'metrics': payload['metrics'], 'valid_profiles': payload['valid_profiles'],
                      'attempts': payload['attempts'], 'json_output': str(JSON_OUTPUT.relative_to(ROOT)),
                      'markdown_output': str(MD_OUTPUT.relative_to(ROOT)),
                      'held_out_session_3_touched': True}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
