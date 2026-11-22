#!/usr/bin/env python3
"""Re-extract strict CSI from archived labelled presence-session IQ captures.

This is an offline replay tool. It never captures radio data, changes the saved
baseline, or overwrites the source session. It recomputes L-LTF quality with the
current extractor and retains only strict-quality profiles with a matching AP
source-audit record.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEVOURER_TOOLS = ROOT / 'vendor' / 'devourer' / 'tools'
sys.path.insert(0, str(DEVOURER_TOOLS))
import la_csi  # noqa: E402
import la_decode  # noqa: E402

QUALITY = {'repeat': 0.85, 'stf16': 0.50, 'symbol_err': 0.25}
CAPTURE_RE = re.compile(r'^capture\.(\d+)\.bin$')
TONES = [int(k) for k, value in zip(la_csi.TONES, la_csi.LTF_SEQ) if value != 0]


def capture_index(path: Path) -> int:
    match = CAPTURE_RE.match(path.name)
    if not match:
        raise ValueError(f'Unexpected capture filename: {path.name}')
    return int(match.group(1))


def load_audit(path: Path) -> dict[int, dict[str, str]]:
    with path.open(newline='') as stream:
        return {int(row['capture_index']): row for row in csv.DictReader(stream)}


def extract_profile(path: Path) -> tuple[np.ndarray, dict[str, float], int]:
    meta, words = la_decode.read_dump(str(path))
    if abs(float(meta['fs_mhz']) - 20.0) > 0.01:
        raise ValueError(f'Expected 20 Msps, got {meta["fs_mhz"]} Msps')
    x = la_decode.LAYOUTS[la_decode.DEFAULT_LAYOUT][1](words)
    x = x - np.mean(x)
    start, cfo = la_csi.locate_lltf(x)
    if start is None:
        raise ValueError('no L-LTF passed strict quality gates')
    quality = la_csi.lltf_quality(x, start, cfo)
    if (quality['repeat_corr'] < QUALITY['repeat'] or
            quality['stf16_corr'] > QUALITY['stf16'] or
            quality['symbol_relerr'] > QUALITY['symbol_err']):
        raise ValueError(f'candidate failed strict quality gates: {quality}')
    h = la_csi.estimate_h(x, start, cfo)
    mag_db = np.asarray([
        20.0 * np.log10(abs(value) + 1e-12)
        for value, seq in zip(h, la_csi.LTF_SEQ) if seq != 0
    ], dtype=float)
    if mag_db.shape != (52,) or not np.all(np.isfinite(mag_db)):
        raise ValueError('CSI did not contain exactly 52 finite active tones')
    profile = mag_db - np.median(mag_db)
    metrics = {
        'repeat_corr': float(quality['repeat_corr']),
        'stf16_corr': float(quality['stf16_corr']),
        'symbol_relerr': float(quality['symbol_relerr']),
        'cfo_hz': float(cfo * 20e6),
        'lltf_start_sample': int(start),
        'tone_spread_db': float(np.std(profile)),
    }
    return profile, metrics, capture_index(path)


def reprocess_batch(batch: dict[str, Any]) -> dict[str, Any]:
    archive = Path(batch['raw_archive_dir']).expanduser()
    if not archive.is_dir():
        raise FileNotFoundError(
            f'Cannot read raw archive directory: {archive}. Grant read/execute access to it and retry.')
    audit_path = archive / 'presence_audit.csv'
    if not audit_path.is_file():
        raise FileNotFoundError(f'Missing audit file: {audit_path}')
    audit = load_audit(audit_path)
    manifest_path = archive / 'run_manifest.json'
    if not manifest_path.is_file():
        raise FileNotFoundError(f'Missing capture manifest: {manifest_path}')
    manifest = json.loads(manifest_path.read_text())
    if batch.get('bssid') and str(manifest.get('connected_bssid', '')).lower() != str(batch['bssid']).lower():
        raise ValueError(f'AP BSSID mismatch between labelled batch and archive: {archive}')
    if batch.get('channel') is not None and int(manifest.get('channel', -1)) != int(batch['channel']):
        raise ValueError(f'AP channel mismatch between labelled batch and archive: {archive}')
    captures = sorted(archive.glob('capture.*.bin'))
    if not captures:
        raise FileNotFoundError(f'No capture.*.bin files in {archive}')
    expected = int(batch.get('captures_requested', len(captures)))
    if len(captures) != expected or len(audit) != expected:
        raise ValueError(
            f'Incomplete archive {archive}: captures={len(captures)}, audit_rows={len(audit)}, expected={expected}')

    profiles: list[list[float]] = []
    accepted_metrics: list[dict[str, float]] = []
    strict_count = 0
    target_count = 0
    rx_idle_count = 0
    failures: list[dict[str, str]] = []
    for path in captures:
        index = capture_index(path)
        row = audit.get(index, {})
        if row.get('target_source_match', '').lower() == 'true':
            target_count += 1
        if row.get('rx_idle_satisfied', '').lower() == 'true':
            rx_idle_count += 1
        try:
            profile, metrics, _ = extract_profile(path)
            strict_count += 1
            if row.get('target_source_match', '').lower() == 'true':
                profiles.append(profile.tolist())
                accepted_metrics.append(metrics)
        except (ValueError, OSError, KeyError, SystemExit) as exc:
            failures.append({'capture': path.name, 'reason': str(exc)})

    n = len(captures)
    result = dict(batch)
    result['legacy_valid_csi_profiles'] = batch.get('valid_csi_profiles')
    result['legacy_strict_csi_count'] = batch.get('strict_csi_count')
    result['legacy_strict_csi_fraction'] = batch.get('strict_csi_fraction')
    result['reprocessed_with'] = 'current_la_csi_ltf_alignment'
    result['captures_reprocessed'] = n
    result['valid_csi_profiles'] = len(profiles)
    result['strict_csi_count'] = strict_count
    result['strict_csi_fraction'] = strict_count / n if n else 0.0
    result['target_source_match_count'] = target_count
    result['target_source_match_fraction'] = target_count / n if n else 0.0
    result['rx_idle_count'] = rx_idle_count
    result['rx_idle_fraction'] = rx_idle_count / n if n else 0.0
    result['target_attributed_strict_csi_count'] = len(profiles)
    result['target_attributed_strict_csi_fraction'] = len(profiles) / n if n else 0.0
    result['csi_yield_gate_pass'] = (len(profiles) / n if n else 0.0) >= 0.80
    result['target_attribution_gate_pass'] = (target_count / n if n else 0.0) >= 0.90
    result['profiles_db_centered'] = profiles
    result['median_csi_tone_spread_db'] = (
        float(np.median([x['tone_spread_db'] for x in accepted_metrics])) if accepted_metrics else None)
    result['median_csi_cfo_hz'] = (
        float(np.median([x['cfo_hz'] for x in accepted_metrics])) if accepted_metrics else None)
    result['reprocessed_quality_summary'] = {
        'repeat_corr_median': float(np.median([x['repeat_corr'] for x in accepted_metrics])) if accepted_metrics else None,
        'stf16_corr_median': float(np.median([x['stf16_corr'] for x in accepted_metrics])) if accepted_metrics else None,
        'symbol_relerr_median': float(np.median([x['symbol_relerr'] for x in accepted_metrics])) if accepted_metrics else None,
        'lltf_start_sample_median': float(np.median([x['lltf_start_sample'] for x in accepted_metrics])) if accepted_metrics else None,
        'tone_spread_db_median': result['median_csi_tone_spread_db'],
        'cfo_hz_median': result['median_csi_cfo_hz'],
    }
    result['reprocessing_failures'] = failures
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path, help='original labelled session JSONL')
    parser.add_argument('--output', type=Path, help='new output JSONL; default adds _reprocessed')
    args = parser.parse_args()
    source = args.session.expanduser().resolve()
    output = args.output.expanduser().resolve() if args.output else source.with_name(source.stem + '_reprocessed.jsonl')
    if output.exists():
        raise SystemExit(f'Refusing to overwrite existing output: {output}')

    records = []
    metadata = None
    with source.open() as stream:
        for line in stream:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get('record_type') == 'session_metadata':
                metadata = dict(item)
            elif item.get('record_type') == 'interleaved_presence_batch':
                records.append(item)
    if len(records) != 10:
        raise SystemExit(f'Expected 10 complete interleaved batches, found {len(records)}')
    if not metadata:
        raise SystemExit('Session metadata missing')
    metadata['reprocessed_from'] = str(source)
    from datetime import datetime, timezone
    metadata['reprocessed_at'] = datetime.now(timezone.utc).isoformat()
    metadata['reprocessing_method'] = 'offline raw-IQ replay with current strict L-LTF alignment search'
    metadata['baseline_modified'] = False

    results = []
    for i, batch in enumerate(records, 1):
        updated = reprocess_batch(batch)
        results.append(updated)
        print(f"{i}/10 round={updated['round_number']} {updated['condition']}: "
              f"strict={updated['strict_csi_count']}/{updated['captures_reprocessed']} "
              f"target-attributed={updated['target_attributed_strict_csi_count']}/"
              f"{updated['captures_reprocessed']} RX-idle={updated['rx_idle_count']}/"
              f"{updated['captures_reprocessed']}", flush=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + '.tmp')
    with tmp.open('x') as stream:
        stream.write(json.dumps(metadata, separators=(',', ':')) + '\n')
        for item in results:
            stream.write(json.dumps(item, separators=(',', ':')) + '\n')
    os.replace(tmp, output)
    passed = sum(x['csi_yield_gate_pass'] and x['target_attribution_gate_pass'] for x in results)
    print(f'Batches passing both acquisition gates: {passed}/10')
    print(f"Recovered strict CSI profiles: ABSENT={sum(x['valid_csi_profiles'] for x in results if x['condition']=='ABSENT')}, "
          f"PRESENT={sum(x['valid_csi_profiles'] for x in results if x['condition']=='PRESENT')}")
    print(f'Wrote new dataset: {output}')
    print('Original session and saved baseline were not modified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
