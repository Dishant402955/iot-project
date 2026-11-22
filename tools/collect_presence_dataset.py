#!/usr/bin/env python3
"""Guided, manually labelled empty/present/empty CSI dataset collection.

Run at the laptop's physical console with sudo. The capture path temporarily
unbinds the Wi-Fi adapter for each batch and restores its normal driver.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import live_presence_detector as detector  # noqa: E402

BATCHES_PER_PHASE = 3
CAPTURES_PER_BATCH = 50
SETTLE_SECONDS = 30
MIN_VALID_CSI_WARNING = 10
OUTPUT = ROOT / 'data' / 'presence_dataset' / f"session_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}.jsonl"


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def countdown(seconds: int, label: str) -> None:
    print(f'\n{label}: {seconds} seconds. Keep the laptop and AP stationary.', flush=True)
    for remaining in range(seconds, 0, -1):
        print(f'  Starting capture in {remaining:2d}s', end='\r', flush=True)
        time.sleep(1)
    print('  Starting capture now.                 ', flush=True)


def collect_phase(out, label: str, bssid_expected=None, channel_expected=None):
    print(f'\n===== {label} PHASE: {BATCHES_PER_PHASE} batches x {CAPTURES_PER_BATCH} captures =====', flush=True)
    countdown(SETTLE_SECONDS, f'{label} settling period')
    total_valid = 0
    for batch_no in range(1, BATCHES_PER_PHASE + 1):
        print(f'\n[{label}] Batch {batch_no}/{BATCHES_PER_PHASE}', flush=True)
        started = stamp()
        profiles, bssid, channel, run_dir = detector.capture_batch(CAPTURES_PER_BATCH)
        if not bssid:
            raise RuntimeError(f'No connected AP identity recorded for {run_dir}; stopping without relabelling data.')
        if bssid_expected is not None and (bssid != bssid_expected or channel != channel_expected):
            raise RuntimeError(
                f'AP changed during collection: expected {bssid_expected}/channel {channel_expected}, '
                f'got {bssid}/channel {channel}; stopping session.'
            )
        if bssid_expected is None:
            bssid_expected, channel_expected = bssid, channel
        total_valid += len(profiles)
        record = {
            'record_type': 'labelled_capture_batch',
            'label': 'present' if label == 'PRESENT' else 'absent',
            'phase': label,
            'batch_number': batch_no,
            'batches_in_phase': BATCHES_PER_PHASE,
            'captures_requested': CAPTURES_PER_BATCH,
            'valid_csi_profiles': len(profiles),
            'started_at_utc': started,
            'completed_at_utc': stamp(),
            'bssid': bssid,
            'channel': channel,
            'capture_run_dir': str(run_dir),
            'profiles_db_centered': [p.tolist() for p in profiles],
        }
        out.write(json.dumps(record, separators=(',', ':')) + '\n')
        out.flush()
        print(f'[{label}] Saved {len(profiles)}/{CAPTURES_PER_BATCH} valid CSI profiles from {run_dir}', flush=True)
        if len(profiles) < MIN_VALID_CSI_WARNING:
            print(f'WARNING: only {len(profiles)} valid profiles. Kept for audit, but this batch is weak.', flush=True)
    print(f'\n[{label}] Complete: {total_valid} valid CSI profiles across {BATCHES_PER_PHASE} batches.', flush=True)
    return bssid_expected, channel_expected, total_valid


def main() -> int:
    if os.geteuid() != 0:
        raise SystemExit('Run at the laptop physical console: sudo vendor/.venv/bin/python tools/collect_presence_dataset.py')
    if not sys.stdin.isatty():
        raise SystemExit('This guided collection needs an interactive terminal for the Enter transitions.')

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    print('CONTROLLED PRESENCE DATASET COLLECTION')
    print('Total plan: 9 batches, 50 capture attempts per batch (450 attempts maximum).')
    print('Expected settling: 30 seconds in each phase (90 seconds total).')
    print('Capture and Wi-Fi reconnect time is additional; expect roughly 3-6 minutes overall.')
    print('Do not move the laptop or AP, change the Wi-Fi network, or use the room during ABSENT phases.')
    print(f'Output: {OUTPUT}')
    input('\nPHASE 1: Leave the monitored room completely empty. When you are outside, press Enter... ')

    with OUTPUT.open('x', encoding='utf-8') as out:
        metadata = {
            'record_type': 'session_metadata',
            'created_at_utc': stamp(),
            'batches_per_phase': BATCHES_PER_PHASE,
            'captures_per_batch': CAPTURES_PER_BATCH,
            'settle_seconds': SETTLE_SECONDS,
            'phase_order': ['absent', 'present', 'absent'],
            'device_note': 'Labels are manually assigned from the guided physical protocol.',
        }
        out.write(json.dumps(metadata) + '\n')
        out.flush()
        bssid, channel, absent_first = collect_phase(out, 'ABSENT')

        input('\nPHASE 2: Enter the monitored room, take your intended stationary position, then press Enter... ')
        bssid, channel, present_count = collect_phase(out, 'PRESENT', bssid, channel)

        input('\nPHASE 3: Leave the monitored room completely empty again, then press Enter... ')
        bssid, channel, absent_second = collect_phase(out, 'ABSENT', bssid, channel)

    print('\nCOLLECTION FINISHED')
    print(f'AP: {bssid}, channel {channel}')
    print(f'Valid CSI profiles: absent-first={absent_first}, present={present_count}, absent-final={absent_second}')
    print(f'Dataset: {OUTPUT}')
    print('The dataset is labelled, not yet a validated detector. Do not overwrite the existing baseline.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nInterrupted. The current capture batch handles cleanup and restores the Wi-Fi driver.', flush=True)
        raise SystemExit(130)
