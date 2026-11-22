"""Evaluate RF-DS states against timestamp-aligned distance annotations."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd


def label_to_state(label: str) -> str:
    label = str(label).strip().lower()
    if label in {'sit', 'stand_up', 'stand_down', '1'}:
        return 'PRESENT'
    if label in {'2', '3', '4', '5'}:
        return 'APPROACH_LEAVE'
    if label in {'6', '7', '8', 'out'}:
        return 'ABSENT'
    return 'UNKNOWN'


def states_at_timestamps(labels: pd.DataFrame, timestamps_s: np.ndarray) -> np.ndarray:
    """Assign labels by their epoch-millisecond intervals, not video frame IDs."""
    truth = np.full(len(timestamps_s), 'UNKNOWN', dtype=object)
    for _, row in labels.iterrows():
        start_s = float(row['Start Time']) / 1000.0
        end_s = float(row['End Time']) / 1000.0
        if end_s <= start_s:
            continue
        mask = (timestamps_s >= start_s) & (timestamps_s < end_s)
        truth[mask] = label_to_state(row['Label'])
    return truth


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--labels', required=True, type=Path)
    p.add_argument('--decisions', required=True, type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    pred = pd.read_csv(a.decisions)
    labels = pd.read_csv(a.labels)
    if 'center_unix_timestamp' not in pred:
        raise SystemExit('Decision CSV has no center_unix_timestamp. Re-run run_dataset.py to regenerate timestamp-aligned decisions.')
    timestamps = pred['center_unix_timestamp'].to_numpy(dtype=np.float64)
    truth_all = states_at_timestamps(labels, timestamps)
    valid = truth_all != 'UNKNOWN'
    truth = truth_all[valid]
    predicted = pred['state'].astype(str).to_numpy()[valid]
    classes = ['PRESENT', 'APPROACH_LEAVE', 'ABSENT']
    matrix = {t: {q: int(np.sum((truth == t) & (predicted == q))) for q in classes} for t in classes}
    accuracy = float(np.mean(truth == predicted)) if len(truth) else float('nan')
    # Binary HPD metrics, with transitional 2-5 m zones counted as occupied/approaching.
    truth_present = truth != 'ABSENT'
    pred_present = predicted != 'ABSENT'
    tp = int(np.sum(truth_present & pred_present))
    tn = int(np.sum(~truth_present & ~pred_present))
    fp = int(np.sum(~truth_present & pred_present))
    fn = int(np.sum(truth_present & ~pred_present))
    binary_accuracy = float((tp + tn) / len(truth)) if len(truth) else float('nan')
    report = {
        'evaluated_decisions': int(len(truth)),
        'unlabelled_decisions': int(np.sum(~valid)),
        'three_state_accuracy': accuracy,
        'binary_presence_accuracy': binary_accuracy,
        'binary_confusion': {'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn},
        'three_state_confusion': matrix,
        'alignment': 'decision center timestamps compared against [Start Time, End Time) epoch-millisecond label intervals',
        'warning': 'This is a local implementation result, not paper-reported accuracy. Confirm all signal-processing parameters and the label interpretation before comparing to the paper.'
    }
    output = json.dumps(report, indent=2)
    print(output)
    if a.output:
        a.output.write_text(output)

if __name__ == '__main__':
    main()
