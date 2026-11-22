#!/usr/bin/env python3
"""Summarize a five-round interleaved CSI session without classifying presence."""
from __future__ import annotations
import argparse, csv, json, math, statistics
from pathlib import Path
import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('session', type=Path)
    ap.add_argument('--output-prefix', type=Path)
    args = ap.parse_args()
    metadata = None
    batches = []
    with args.session.open() as f:
        for line in f:
            try: item = json.loads(line)
            except json.JSONDecodeError: continue
            if item.get('record_type') == 'session_metadata': metadata = item
            elif item.get('record_type') == 'interleaved_presence_batch': batches.append(item)
    if metadata is None or metadata.get('experiment') != 'five_round_interleaved_v1':
        raise SystemExit('Not a five_round_interleaved_v1 session.')
    if len(batches) != 10:
        raise SystemExit(f'Expected 10 complete batches, found {len(batches)}. Partial session retained; no phase comparison generated.')
    rows=[]
    profiles_by_condition={'absent': [], 'present': []}
    profiles_by_round={}
    for b in batches:
        condition=b.get('condition','').lower()
        if condition not in profiles_by_condition: raise SystemExit(f'Invalid condition: {condition}')
        arr=np.asarray(b.get('profiles_db_centered', []), dtype=float)
        if arr.ndim != 2 or arr.shape[1] != 52 or not np.all(np.isfinite(arr)):
            raise SystemExit(f'Invalid profile matrix in round {b.get("round_number")} {condition}')
        if len(arr) != int(b.get('valid_csi_profiles', -1)):
            raise SystemExit('Profile count does not match valid_csi_profiles metadata.')
        profiles_by_condition[condition].extend(arr)
        profiles_by_round.setdefault(int(b['round_number']), {})[condition]=arr
        rows.append({k:b.get(k) for k in ('round_number','condition','started_at_utc','valid_csi_profiles','capture_attempts_audited','strict_csi_fraction','target_attributed_strict_csi_fraction','target_source_match_fraction','rx_idle_fraction','median_target_frame_rssi','median_csi_tone_spread_db','median_csi_cfo_hz','csi_yield_gate_pass','target_attribution_gate_pass','bssid','channel','capture_run_dir','raw_archive_dir')})
    if any(len(profiles_by_round.get(i,{})) != 2 for i in range(1,6)):
        raise SystemExit('Each of five rounds must contain one ABSENT and one PRESENT batch.')
    absent=np.vstack(profiles_by_condition['absent']); present=np.vstack(profiles_by_condition['present'])
    absent_center=np.median(absent,axis=0); present_center=np.median(present,axis=0)
    pair_distance=float(np.sqrt(np.mean((absent_center-present_center)**2)))
    per_round=[]
    for i in range(1,6):
        a=np.asarray(profiles_by_round[i]['absent']); p=np.asarray(profiles_by_round[i]['present'])
        d=float(np.sqrt(np.mean((np.median(a,axis=0)-np.median(p,axis=0))**2)))
        per_round.append({'round':i,'absent_profiles':len(a),'present_profiles':len(p),'median_profile_distance_db':d})
    quality_pass=sum(bool(b.get('csi_yield_gate_pass')) and bool(b.get('target_attribution_gate_pass')) for b in batches)
    same_ap=len({(b.get('bssid'),b.get('channel')) for b in batches}) == 1
    all_quality=quality_pass == 10 and same_ap
    prefix=args.output_prefix or args.session.with_suffix('')
    csv_path=Path(str(prefix)+'_batches.csv'); json_path=Path(str(prefix)+'_analysis.json')
    csv_path.parent.mkdir(parents=True,exist_ok=True)
    with csv_path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    result={
      'session':str(args.session),'experiment':metadata['experiment'],'batches':10,'rounds':5,
      'absent_valid_profiles':len(absent),'present_valid_profiles':len(present),
      'batches_passing_both_acquisition_gates':quality_pass,'all_batches_pass_acquisition_gates':all_quality,
      'same_bssid_and_channel_all_batches':same_ap,
      'absent_vs_present_median_profile_distance_db':pair_distance,
      'per_round':per_round,
      'interpretation':'Descriptive acquisition and profile comparison only. A small or large distance does not establish detector accuracy. Inspect per-round consistency and empty-room drift; do not tune thresholds from this one session.',
      'baseline_modified':False,'batch_csv':str(csv_path)}
    json_path.write_text(json.dumps(result,indent=2)+'\n')
    print(f'Batches: 10/10; acquisition gates: {quality_pass}/10; same AP/channel: {same_ap}')
    print(f'Strict CSI profiles: ABSENT={len(absent)}, PRESENT={len(present)}')
    print(f'ABSENT vs PRESENT median profile distance: {pair_distance:.4f} dB RMS')
    for r in per_round: print(f"Round {r['round']}: absent={r['absent_profiles']} present={r['present_profiles']} distance={r['median_profile_distance_db']:.4f} dB")
    print(f'Analysis: {json_path}')
    if not all_quality: print('WARNING: one or more batches failed the acquisition gate; interpret comparisons as degraded/diagnostic only.')
    return 0 if same_ap else 3

if __name__ == '__main__': raise SystemExit(main())
