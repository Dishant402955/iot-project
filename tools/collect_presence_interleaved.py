#!/usr/bin/env python3
"""Collect five paired, interleaved ABSENT/PRESENT CSI rounds.

Run only at the laptop's physical console. The phone/AP and laptop remain fixed.
This records labelled measurements but does not train, tune, or validate a detector.
"""
from __future__ import annotations
import csv
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import live_presence_detector as detector  # noqa: E402

ROUNDS = 5
CAPTURES_PER_BATCH = 50
SETTLE_SECONDS = 30
MIN_CSI_FRACTION = 0.80
MIN_TARGET_FRACTION = 0.90
SESSION_ID = f"interleaved_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"
OUTPUT = ROOT / 'data' / 'presence_dataset' / f'{SESSION_ID}.jsonl'
RAW_ARCHIVE = ROOT / 'data' / 'presence_dataset_raw' / SESSION_ID


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def condition_order(round_no: int) -> list[str]:
    return ['ABSENT', 'PRESENT'] if round_no % 2 == 1 else ['PRESENT', 'ABSENT']


def countdown(seconds: int, label: str) -> None:
    print(f'\n{label}: settling for {seconds}s. Keep both devices fixed.', flush=True)
    for remaining in range(seconds, 0, -1):
        print(f'  Capture starts in {remaining:2d}s', end='\r', flush=True)
        import time
        time.sleep(1)
    print('  Capture starts now.                 ', flush=True)


def audit_counts(run_dir: Path) -> dict:
    path = run_dir / 'presence_audit.csv'
    if not path.is_file():
        raise RuntimeError(f'Missing source/quality audit: {path}')
    with path.open(newline='') as f:
        rows = list(csv.DictReader(f))
    n = len(rows)
    idle = sum(r.get('rx_idle_satisfied', '').lower() == 'true' for r in rows)
    target = sum(r.get('target_source_match', '').lower() == 'true' for r in rows)
    csi = sum(r.get('csi_structurally_valid', '').lower() == 'true' for r in rows)
    joint = sum(r.get('csi_structurally_valid', '').lower() == 'true' and r.get('target_source_match', '').lower() == 'true' for r in rows)
    def median_numeric(field):
        values=[]
        for row in rows:
            try:
                value=float(row.get(field, ''))
                if value == value and abs(value) != float('inf'):
                    values.append(value)
            except (TypeError, ValueError):
                pass
        values.sort()
        if not values: return None
        mid=len(values)//2
        return values[mid] if len(values)%2 else (values[mid-1]+values[mid])/2
    return {
        'capture_attempts_audited': n,
        'rx_idle_count': idle,
        'rx_idle_fraction': idle / n if n else 0.0,
        'target_source_match_count': target,
        'target_source_match_fraction': target / n if n else 0.0,
        'strict_csi_count': csi,
        'strict_csi_fraction': csi / n if n else 0.0,
        'target_attributed_strict_csi_count': joint,
        'target_attributed_strict_csi_fraction': joint / n if n else 0.0,
        'median_target_frame_rssi': median_numeric('first_frame_rssi'),
        'median_csi_tone_spread_db': median_numeric('csi_tone_spread_db'),
        'median_csi_cfo_hz': median_numeric('csi_cfo_hz'),
    }


def collect_one(out, round_no: int, condition: str, expected_bssid=None, expected_channel=None):
    print(f'\n===== ROUND {round_no}/{ROUNDS}: {condition} =====', flush=True)
    if condition == 'ABSENT':
        print('Leave the monitored room. Go at least 5 m from BOTH devices, preferably behind a closed door.', flush=True)
        print('Keep all people out of the monitored room. The phone hotspot stays in its marked position.', flush=True)
    else:
        print('Enter the room and take the same marked stationary position used in every PRESENT round.', flush=True)
        print('Remain still and do not touch either device until capture completes.', flush=True)
    input(f'When the {condition} condition is established, press Enter... ')
    countdown(SETTLE_SECONDS, f'{condition} round {round_no}')
    started = stamp()
    profiles, bssid, channel, run_dir = detector.capture_batch(CAPTURES_PER_BATCH)
    if not bssid:
        raise RuntimeError(f'No connected AP identity recorded for {run_dir}; stopping session.')
    if expected_bssid is not None and (bssid != expected_bssid or channel != expected_channel):
        raise RuntimeError(
            f'AP changed during collection: expected {expected_bssid}/channel {expected_channel}, '
            f'got {bssid}/channel {channel}; stopping session.'
        )
    audit = audit_counts(run_dir)
    if audit['capture_attempts_audited'] != CAPTURES_PER_BATCH:
        raise RuntimeError(f'Expected {CAPTURES_PER_BATCH} audited attempts, got {audit["capture_attempts_audited"]}; stopping.')
    archive_dir = RAW_ARCHIVE / f'round_{round_no}_{condition.lower()}'
    archive_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run_dir, archive_dir)
    record = {
        'record_type': 'interleaved_presence_batch',
        'experiment': 'five_round_interleaved_v1',
        'round_number': round_no,
        'condition': condition,
        'label': condition.lower(),
        'started_at_utc': started,
        'completed_at_utc': stamp(),
        'bssid': bssid,
        'channel': channel,
        'captures_requested': CAPTURES_PER_BATCH,
        'valid_csi_profiles': len(profiles),
        'csi_yield_gate_pass': audit['target_attributed_strict_csi_fraction'] >= MIN_CSI_FRACTION,
        'target_attribution_gate_pass': audit['target_source_match_fraction'] >= MIN_TARGET_FRACTION,
        **audit,
        'capture_run_dir': str(run_dir),
        'raw_archive_dir': str(archive_dir),
        'profiles_db_centered': [p.tolist() for p in profiles],
    }
    out.write(json.dumps(record, separators=(',', ':')) + '\n')
    out.flush()
    print(
        f'{condition} round {round_no}: strict CSI={len(profiles)}/{CAPTURES_PER_BATCH}; '
        f'attributed strict CSI={audit["target_attributed_strict_csi_fraction"]:.1%}; '
        f'target attribution={audit["target_source_match_fraction"]:.1%}; '
        f'RX-idle={audit["rx_idle_fraction"]:.1%}', flush=True)
    if not record['csi_yield_gate_pass'] or not record['target_attribution_gate_pass']:
        print('QUALITY WARNING: batch retained for audit, but it fails the acquisition gate. Do not treat it as clean evidence.', flush=True)
    print(f'Artifacts: {run_dir}', flush=True)
    return bssid, channel, record


def main() -> int:
    if os.geteuid() != 0:
        raise SystemExit('Run at the laptop physical console: sudo vendor/.venv/bin/python tools/collect_presence_interleaved.py')
    if not sys.stdin.isatty():
        raise SystemExit('This guided collection requires an interactive terminal.')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    print('FIVE-ROUND INTERLEAVED CSI PRESENCE EXPERIMENT')
    print(f'Plan: {ROUNDS} rounds x 2 conditions x {CAPTURES_PER_BATCH} attempts = {ROUNDS * 2 * CAPTURES_PER_BATCH} attempts.')
    print(f'Each condition gets {SETTLE_SECONDS}s settling; each batch targets >= {MIN_CSI_FRACTION:.0%} target-attributed strict CSI and >= {MIN_TARGET_FRACTION:.0%} AP attribution.')
    print('Order alternates to reduce time/order confounding: ABSENT-PRESENT, PRESENT-ABSENT, repeated.')
    print('Do not change hotspot settings, phone power state, laptop power state, room layout, doors/windows, or device positions. Keep doors/windows closed for every batch.')
    print('No streaming/downloads or deliberate network traffic. Ordinary nearby RF activity is recorded as part of the environment, not assumed absent.')
    print('Keep other people out of the monitored room throughout. During ABSENT, leave the room and stay >=5 m away, preferably behind a closed door.')
    print('During PRESENT, use one marked position and orientation and remain still for the full capture.')
    print('This does not overwrite or readjust the saved baseline and does not make an accuracy claim.')
    print(f'Labelled JSONL: {OUTPUT}')
    print(f'Raw capture archive: {RAW_ARCHIVE}')
    bssid = channel = None
    records = []
    with OUTPUT.open('x', encoding='utf-8') as out:
        meta = {
            'record_type': 'session_metadata',
            'experiment': 'five_round_interleaved_v1',
            'created_at_utc': stamp(),
            'rounds': ROUNDS,
            'captures_per_batch': CAPTURES_PER_BATCH,
            'settle_seconds': SETTLE_SECONDS,
            'condition_order_by_round': [condition_order(i) for i in range(1, ROUNDS + 1)],
            'minimum_strict_csi_fraction': MIN_CSI_FRACTION,
            'minimum_target_attribution_fraction': MIN_TARGET_FRACTION,
            'physical_protocol': {
                'absent': 'No person in monitored room; operator >=5 m from laptop and phone, preferably in another room behind a closed door; all doors/windows remain closed; phone/AP remains fixed.',
                'present': 'One person stationary at same marked position and orientation in each present block.',
                'environment': 'All doors/windows closed throughout; no deliberate traffic; ordinary RF background retained; all room/device/environment settings fixed.'
            },
            'baseline_modified': False,
            'raw_capture_archive_root': str(RAW_ARCHIVE),
        }
        out.write(json.dumps(meta, separators=(',', ':')) + '\n')
        out.flush()
        for round_no in range(1, ROUNDS + 1):
            order = condition_order(round_no)
            for condition in order:
                bssid, channel, record = collect_one(out, round_no, condition, bssid, channel)
                records.append(record)
    print('\nCOLLECTION FINISHED')
    print(f'AP: {bssid}, channel {channel}; batches: {len(records)}/10')
    print(f'Batches passing both acquisition gates: {sum(r["csi_yield_gate_pass"] and r["target_attribution_gate_pass"] for r in records)}/10')
    print(f'Dataset: {OUTPUT}')
    print('Next: run tools/analyze_interleaved_presence.py on this file. This dataset is not detector validation.')
    return 0 if len(records) == ROUNDS * 2 else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nInterrupted. Current capture cleanup restores the Wi-Fi driver; partial JSONL is preserved.', flush=True)
        raise SystemExit(130)
