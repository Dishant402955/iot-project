#!/usr/bin/env python3
"""Audit one RTL8821CE LA/CSI run without inferring human presence.

Joins each LA capture's monotonic arm window to the first decoded RX frame,
checks target-BSSID beacon attribution, validates CSI row structure, and emits
an auditable CSV/JSON report. A CRCOK trigger is not transmitter-filtered in
hardware; source attribution is therefore a required post-capture gate.
"""
from __future__ import annotations
import argparse, csv, json, math, re, statistics
from collections import defaultdict
from pathlib import Path


def load_events(path: Path):
    events=[]
    with path.open(errors='replace') as f:
        for line in f:
            try:
                e=json.loads(line)
                if isinstance(e,dict) and 'ev' in e: events.append(e)
            except json.JSONDecodeError: pass
    return events


def norm_mac(value):
    if not value: return None
    value=value.lower().replace('-', ':')
    if re.fullmatch(r'[0-9a-f]{12}', value):
        value=':'.join(value[i:i+2] for i in range(0,12,2))
    return value if re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', value) else None


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--log',required=True,type=Path)
    ap.add_argument('--series',required=True,type=Path)
    ap.add_argument('--manifest',required=True,type=Path)
    ap.add_argument('--output-prefix',type=Path)
    ap.add_argument('--min-target-fraction',type=float,default=0.90)
    ap.add_argument('--min-csi-fraction',type=float,default=0.80)
    a=ap.parse_args()
    manifest=json.loads(a.manifest.read_text())
    target=norm_mac(manifest.get('connected_bssid'))
    trigger=str(manifest.get('trigger') or 'crcok').lower()
    source_attribution_available = trigger in ('cca', 'crcok')
    events=load_events(a.log)
    captures=[e for e in events if e.get('ev')=='la.capture' and e.get('ok')==1]
    frames=[e for e in events if e.get('ev')=='rx.presence_frame' and isinstance(e.get('steady_us'),(int,float))]
    csi=defaultdict(list)
    with a.series.open(errors='replace') as f:
        for line in f:
            try:
                r=json.loads(line)
                idx=int(Path(r['capture_file']).stem.split('.')[-1])
                csi[idx].append(r)
            except (ValueError,KeyError,TypeError,json.JSONDecodeError):
                continue
    rows=[]
    for cap in captures:
        path=Path(cap.get('file',''))
        m=re.search(r'capture\.(\d+)\.bin$',path.name)
        if not m: continue
        idx=int(m.group(1))
        begin=cap.get('arm_begin_steady_us'); armed=cap.get('armed_steady_us'); done=cap.get('done_steady_us')
        candidates=[]
        rx_idle_satisfied=cap.get('rx_idle')==1
        if rx_idle_satisfied and all(isinstance(x,(int,float)) for x in (begin,armed,done)):
            # Only frames observed after the MAC trigger is fully armed can
            # have caused this CRCOK capture. Frames during arm setup are excluded.
            candidates=[f for f in frames if armed <= f['steady_us'] <= done and f.get('crc',1)==0 and f.get('icv',1)==0]
            candidates.sort(key=lambda f:f['steady_us'])
        first=candidates[0] if candidates else None
        fc0=first.get('fc0') if first else None
        addr2=norm_mac(first.get('addr2')) if first else None
        addr3=norm_mac(first.get('addr3')) if first else None
        is_beacon=fc0==0x80
        # For AP-originated management/data frames, addr2 is the transmitter.
        # Beacons additionally require addr3=BSSID, which validates our parsing.
        frame_type=(fc0 & 0x0c) if isinstance(fc0,int) else None
        target_match=bool(source_attribution_available and target and first and first.get('crc',1)==0 and
                          first.get('icv',1)==0 and frame_type in (0x00,0x08) and
                          addr2==target and (not is_beacon or addr3==target) and
                          cap.get('rx_idle',0)==1)
        tones=csi.get(idx,[])
        tone_ids=sorted({int(x['tone']) for x in tones if 'tone' in x})
        finite=all(math.isfinite(float(x.get('mag_db',float('nan')))) and math.isfinite(float(x.get('phase_rad',float('nan')))) for x in tones)
        quality = tones[0] if tones else {}
        ltf_repeat=float(quality.get('lltf_repeat_corr',0.0)) if tones else 0.0
        ltf_stf16=float(quality.get('lltf_stf16_corr',1.0)) if tones else 1.0
        ltf_symbol_err=float(quality.get('lltf_symbol_relerr',1.0)) if tones else 1.0
        csi_valid=(len(tones)==52 and len(tone_ids)==52 and finite and
                   ltf_repeat>=0.85 and ltf_stf16<=0.50 and ltf_symbol_err<=0.25)
        rows.append({
          'capture_index':idx,'capture_ms':cap.get('ms'),'arm_begin_steady_us':begin,
          'armed_steady_us':armed,'done_steady_us':done,'rx_idle_satisfied':rx_idle_satisfied,
          'rx_frames_in_window':len(candidates),
          'first_frame_fc0':f'0x{fc0:02x}' if isinstance(fc0,int) else '',
          'first_frame_addr2':addr2 or '', 'first_frame_addr3':addr3 or '',
          'first_frame_rssi':first.get('rssi') if first else '',
          'target_source_match':target_match,
          'target_source_match_status':('heuristic_match' if target_match else
              'heuristic_mismatch' if source_attribution_available and first else
              ('unavailable_for_cca' if trigger == 'cca' and not source_attribution_available else
               'unavailable_for_manual' if trigger == 'manual' else 'no_candidate_frame')),'rx_idle':cap.get('rx_idle',0),'csi_tones':len(tones),
          'csi_structurally_valid':csi_valid,
          'csi_mean_mag_db':statistics.fmean(float(x['mag_db']) for x in tones) if csi_valid else '',
          'csi_tone_spread_db':statistics.pstdev(float(x['mag_db']) for x in tones) if csi_valid else '',
          'csi_cfo_hz':tones[0].get('cfo_hz') if csi_valid else '',
          'lltf_start_sample':tones[0].get('lltf_start_sample') if csi_valid else '',
        })
    n=len(rows)
    target_n=sum(r['target_source_match'] for r in rows)
    csi_n=sum(r['csi_structurally_valid'] for r in rows)
    joint_n=sum(r['target_source_match'] and r['csi_structurally_valid'] for r in rows)
    target_fraction=(target_n/n if n else 0) if source_attribution_available else None
    csi_fraction=csi_n/n if n else 0
    joint_fraction=(joint_n/n if n else 0) if source_attribution_available else None
    idle_n=sum(r['rx_idle_satisfied'] for r in rows)
    idle_fraction=idle_n/n if n else 0
    # A run is ready for controlled occupancy data only if target association
    # and extraction yield are high; this is a pipeline gate, not a detector claim.
    target_ok=bool(source_attribution_available and target and n>=10 and idle_fraction>=0.90 and target_fraction>=a.min_target_fraction)
    csi_ok=bool(n>=10 and csi_fraction>=a.min_csi_fraction)
    cadence=[]
    t=[r['arm_begin_steady_us'] for r in rows if isinstance(r['arm_begin_steady_us'],(int,float))]
    cadence=[(b-x)/1000 for x,b in zip(t,t[1:])]
    prefix=a.output_prefix or a.series.with_suffix('').with_name('presence_audit')
    csv_path=Path(str(prefix)+'.csv'); json_path=Path(str(prefix)+'.json')
    csv_path.parent.mkdir(parents=True,exist_ok=True)
    with csv_path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['capture_index']); w.writeheader(); w.writerows(rows)
    summary={
      'run_manifest':str(a.manifest),'target_bssid':target,'captures':n,
      'rx_frame_metadata_events':len(frames),'trigger':trigger,
      'target_source_attribution_available':source_attribution_available,
      'target_source_matches':target_n if source_attribution_available else None,
      'target_source_fraction':target_fraction,'rx_idle_captures':idle_n,
      'rx_idle_fraction':idle_fraction,'csi_valid_captures':csi_n,
      'csi_valid_fraction':csi_fraction,'target_and_csi_captures':joint_n,
      'target_and_csi_fraction':joint_fraction,'median_capture_start_spacing_ms':statistics.median(cadence) if cadence else None,
      'target_attribution_gate':target_ok,'csi_yield_gate':csi_ok,
      'ready_for_controlled_presence_dataset':target_ok and csi_ok,
      'limitations':(['Manual-trigger runs validate LA capture mechanics only; they cannot attribute a capture to an AP frame or support presence-data collection.'] if trigger == 'manual' else []) +
        ['CCA/CRCOK hardware triggers are not source-MAC filtered; the audit associates the first decoded good frame observed after the MAC trigger-arm timestamp. RX callback timing can still differ slightly from over-the-air trigger timing.',
        'Target attribution is a first-good-RX-callback-after-arm heuristic, not a hardware source-filtered trigger. It requires an RX-idle-confirmed management/data frame with addr2 equal to the connected AP BSSID; beacons also require addr3 to match.',
        'CSI validity requires 52 finite tones plus repeated-LTF coherence checks; it is not a human-presence validity test.',
        'No human-presence inference is made from this run.'],
      'csv':str(csv_path)}
    json_path.write_text(json.dumps(summary,indent=2)+'\n')
    print(f"PRESENCE_AUDIT: captures={n} rx_metadata={len(frames)}")
    print(f"RX idle barrier satisfied={idle_n}/{n} ({idle_fraction:.1%})")
    if source_attribution_available:
        print(f"post-arm target-source heuristic={target_n}/{n} ({target_fraction:.1%}) target_bssid={target or 'unknown'}")
        print(f"heuristic-matched high-confidence CSI={joint_n}/{n} ({joint_fraction:.1%})")
    elif trigger == "manual":
        print("target source attribution=UNAVAILABLE for manual trigger (diagnostic only)")
    else:
        print("target source attribution=UNAVAILABLE for CCA/CRC-error trigger (not source-filtered for the target AP)")
    print(f"high-confidence CSI={csi_n}/{n} ({csi_fraction:.1%})")
    print(f"idle + target attribution gate={'PASS' if target_ok else 'FAIL'} (idle >= 90%, target >= {a.min_target_fraction:.0%})")
    print(f"CSI yield gate={'PASS' if csi_ok else 'FAIL'} (>= {a.min_csi_fraction:.0%})")
    print(f"ready for controlled presence dataset={'YES' if target_ok and csi_ok else 'NO'}")
    print(f"CSV: {csv_path}\nJSON: {json_path}")
    return 0 if target_ok and csi_ok else 3

if __name__=='__main__':
    raise SystemExit(main())
