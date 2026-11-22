#!/usr/bin/env python3
"""Offline CSI drift/SNR diagnostic. Does not infer occupancy."""
from __future__ import annotations
import argparse, csv, json, math, statistics, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'vendor/devourer/tools')]
import la_decode
import live_presence_detector as detector

def linear_detrend_profile(profile, tones):
    """Remove best-fit linear magnitude slope; diagnostic only."""
    x=np.asarray(profile,dtype=float); t=np.asarray(tones,dtype=float)
    if x.ndim!=1 or x.shape!=t.shape or not np.all(np.isfinite(x)) or not np.all(np.isfinite(t)):
        raise ValueError('profile and tones must be equal-length finite vectors')
    x=x-float(np.median(x))
    slope,intercept=np.polyfit(t,x,1); residual=x-(slope*t+intercept)
    residual=residual-float(np.median(residual))
    return residual,float(slope)

def iq_level_metrics(path,start):
    """Uncalibrated pre-LTF noise vs L-LTF signal RMS proxy."""
    empty={'iq_full_rms':None,'iq_pre_ltf_rms':None,'iq_ltf_rms':None,'iq_ltf_to_pre_db':None,'iq_clip_fraction':None}
    if not path.is_file() or start<300: return empty
    _,words=la_decode.read_dump(str(path)); iq=la_decode.LAYOUTS['qi12_l'][1](words)
    pre=iq[max(0,start-900):max(0,start-200)]; ltf=iq[start:start+128]
    if len(pre)<100 or len(ltf)!=128: return empty
    rms=lambda z:float(np.sqrt(np.mean(np.abs(z)**2)))
    nr,sr=rms(pre),rms(ltf)
    return {'iq_full_rms':rms(iq),'iq_pre_ltf_rms':nr,'iq_ltf_rms':sr,
            'iq_ltf_to_pre_db':20*math.log10((sr+1e-12)/(nr+1e-12)),
            'iq_clip_fraction':float(np.mean((np.abs(iq.real)>=2047)|(np.abs(iq.imag)>=2047)))}

def read_frames(run):
    frames=[]; p=run/'rxdemo.log'
    if not p.is_file(): return frames
    for line in p.open(errors='replace'):
        if '"ev":"rx.presence_frame"' not in line: continue
        try: frames.append(json.loads(line[line.index('{'):]))
        except (ValueError,json.JSONDecodeError): pass
    return frames

def optional_float(value):
    try:
        x=float(value); return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def load_run(run,baseline):
    sp,ap,mp=[run/n for n in ('csi_series.jsonl','presence_audit.csv','run_manifest.json')]
    if not all(p.is_file() for p in (sp,ap,mp)): raise RuntimeError(f'incomplete run: {run}')
    manifest=json.loads(mp.read_text())
    with ap.open(newline='') as f: audit={int(r['capture_index']):r for r in csv.DictReader(f)}
    grouped=defaultdict(list)
    for line in sp.open(errors='replace'):
        try:
            r=json.loads(line); grouped[int(r['capture_index'])].append(r)
        except (ValueError,TypeError,KeyError,json.JSONDecodeError): pass
    tones=np.asarray(baseline['tones'],float); center=np.asarray(baseline['profile_db_centered'],float)
    base_resid,_=linear_detrend_profile(center,tones); frames=read_frames(run); rows=[]
    for idx,rs in sorted(grouped.items()):
        if len(rs)!=52: continue
        rs=sorted(rs,key=lambda r:int(r['tone']))
        if [int(r['tone']) for r in rs]!=[int(t) for t in tones]: continue
        first=rs[0]; a=audit.get(idx,{})
        try:
            repeat=float(first['lltf_repeat_corr']); stf=float(first['lltf_stf16_corr']); err=float(first['lltf_symbol_relerr'])
            mag=np.asarray([float(r['mag_db']) for r in rs]); phase=np.asarray([float(r['phase_rad']) for r in rs])
        except (KeyError,TypeError,ValueError): continue
        if (not np.all(np.isfinite(mag)) or not np.all(np.isfinite(phase)) or
            repeat<detector.QUALITY['repeat'] or stf>detector.QUALITY['stf16'] or err>detector.QUALITY['symbol_err'] or
            a.get('target_source_match','').lower()!='true'): continue
        profile=mag-np.median(mag); residual,slope=linear_detrend_profile(profile,tones)
        raw=float(np.sqrt(np.mean((profile-center)**2)))
        detr=float(np.sqrt(np.mean((residual-base_resid)**2)))
        start=int(first.get('lltf_start_sample',-1)); armed=a.get('armed_steady_us'); done=a.get('done_steady_us')
        frame=None
        if armed and done:
            try:
                candidates=[f for f in frames if int(armed)<=int(f.get('steady_us',-1))<=int(done) and f.get('crc',1)==0 and f.get('icv',1)==0]
                if candidates: frame=min(candidates,key=lambda f:int(f['steady_us']))
            except (TypeError,ValueError): pass
        rows.append({'run':run.name,'capture_index':idx,'rssi_index':optional_float(a.get('first_frame_rssi')),
            'csi_mean_mag_db':optional_float(a.get('csi_mean_mag_db')),'csi_tone_spread_db':optional_float(a.get('csi_tone_spread_db')),
            'spectral_slope_db_per_tone':slope,'raw_anomaly_db':raw,'detrended_anomaly_db':detr,
            'cfo_hz':optional_float(first.get('cfo_hz')),'lltf_start_sample':start,
            'lltf_repeat_corr':repeat,'lltf_stf16_corr':stf,'lltf_symbol_relerr':err,
            'first_rx_frame_len':frame.get('len') if frame else None,'first_rx_frame_rate':frame.get('rate') if frame else None,
            **iq_level_metrics(run/f'capture.{idx:04d}.bin',start)})
    return manifest,rows,len(grouped),len(audit)

def stats(values):
    x=[float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not x: return {'count':0,'median':None,'p10':None,'p90':None}
    return {'count':len(x),'median':statistics.median(x),'p10':float(np.percentile(x,10)),'p90':float(np.percentile(x,90))}

def run_summary(manifest,rows,seen,audit_count):
    fields=['rssi_index','csi_mean_mag_db','csi_tone_spread_db','spectral_slope_db_per_tone',
            'raw_anomaly_db','detrended_anomaly_db','cfo_hz','lltf_start_sample',
            'iq_pre_ltf_rms','iq_ltf_rms','iq_ltf_to_pre_db','iq_clip_fraction']
    lengths=defaultdict(int)
    for r in rows:
        if r['first_rx_frame_len'] is not None: lengths[str(r['first_rx_frame_len'])]+=1
    return {'run':rows[0]['run'] if rows else 'unknown','ap_bssid':manifest.get('connected_bssid'),
        'channel':manifest.get('channel'),'trigger_time_us':manifest.get('trigger_time_us'),
        'captures_seen_in_series':seen,'captures_in_audit':audit_count,'strict_target_attributed_profiles':len(rows),
        'strict_profile_yield':len(rows)/audit_count if audit_count else None,
        'metrics':{k:stats([r[k] for r in rows]) for k in fields},'rx_frame_lengths':dict(sorted(lengths.items()))}

def analyze_runs(run_dirs,baseline_path,prefix):
    baseline=json.loads(baseline_path.read_text()); tones=baseline['tones']; all_rows=[]; summaries=[]; medians={}
    for run in run_dirs:
        manifest,rows,seen,audit_count=load_run(run,baseline)
        if not rows: raise RuntimeError(f'no strict target-attributed profiles: {run}')
        summaries.append(run_summary(manifest,rows,seen,audit_count)); all_rows.extend(rows)
        by=defaultdict(list)
        for line in (run/'csi_series.jsonl').open(errors='replace'):
            try:
                z=json.loads(line); by[int(z['capture_index'])].append(z)
            except (ValueError,TypeError,KeyError,json.JSONDecodeError): pass
        profiles=[]
        for idx in sorted(r['capture_index'] for r in rows):
            group=sorted(by[idx],key=lambda z:int(z['tone'])); v=np.array([float(z['mag_db']) for z in group]); profiles.append(v-np.median(v))
        medians[run.name]=np.median(np.vstack(profiles),axis=0)
    pairs=[]; names=list(medians)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            raw=float(np.sqrt(np.mean((medians[a]-medians[b])**2)))
            ar,_=linear_detrend_profile(medians[a],tones); br,_=linear_detrend_profile(medians[b],tones)
            pairs.append({'run_a':a,'run_b':b,'median_profile_distance_db':raw,
                          'detrended_median_profile_distance_db':float(np.sqrt(np.mean((ar-br)**2)))})
    prefix.parent.mkdir(parents=True,exist_ok=True); csv_path=prefix.with_suffix('.csv'); json_path=prefix.with_suffix('.json')
    with csv_path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(all_rows[0])); writer.writeheader(); writer.writerows(all_rows)
    corr={}
    for a,b in [('rssi_index','csi_mean_mag_db'),('rssi_index','csi_tone_spread_db'),
                ('rssi_index','spectral_slope_db_per_tone'),('csi_tone_spread_db','spectral_slope_db_per_tone'),
                ('raw_anomaly_db','csi_tone_spread_db'),('raw_anomaly_db','spectral_slope_db_per_tone'),
                ('iq_ltf_to_pre_db','raw_anomaly_db')]:
        xy=[(r[a],r[b]) for r in all_rows if r[a] is not None and r[b] is not None]
        if len(xy)>=3 and np.std([x for x,y in xy])>0 and np.std([y for x,y in xy])>0:
            corr[a+'__'+b]={'n':len(xy),'pearson_r':float(np.corrcoef([x for x,y in xy],[y for x,y in xy])[0,1])}
    result={'baseline':str(baseline_path),'baseline_sample_count':baseline.get('sample_count'),
        'baseline_anomaly_threshold_db':baseline.get('anomaly_threshold_db'),
        'baseline_spectral_slope_db_per_tone':linear_detrend_profile(baseline['profile_db_centered'],tones)[1],
        'run_summaries':summaries,'pairwise_run_median_profile_distances':pairs,
        'cross_capture_correlations_descriptive_only':corr,
        'interpretation_limit':'Observational correlations may be confounded by run order. Detrended anomaly is diagnostic only, not a validated presence feature or threshold.',
        'csv':str(csv_path)}
    json_path.write_text(json.dumps(result,indent=2)+'\n')
    return result,csv_path,json_path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,default=ROOT/'data/live_presence_baseline.json')
    p.add_argument('--runs',nargs='+',type=Path,required=True)
    p.add_argument('--output-prefix',type=Path,required=True)
    a=p.parse_args()
    if not a.baseline.is_file(): p.error(f'baseline not found: {a.baseline}')
    for run in a.runs:
        if not run.is_dir(): p.error(f'run directory not found: {run}')
    result,csv_path,json_path=analyze_runs(a.runs,a.baseline,a.output_prefix)
    print(f"DRIFT_ANALYSIS_PASS: runs={len(result['run_summaries'])} profiles={sum(x['strict_target_attributed_profiles'] for x in result['run_summaries'])}")
    for s in result['run_summaries']:
        m=s['metrics']; val=lambda k:'n/a' if m[k]['median'] is None else f"{m[k]['median']:.4f}"
        print(f"{s['run']}: n={s['strict_target_attributed_profiles']} RSSI={val('rssi_index')} CSImean={val('csi_mean_mag_db')} spread={val('csi_tone_spread_db')} slope={val('spectral_slope_db_per_tone')} raw={val('raw_anomaly_db')} detrended={val('detrended_anomaly_db')} IQ_SNR_proxy={val('iq_ltf_to_pre_db')}")
    print(f'CSV: {csv_path}\nJSON: {json_path}')
    print('NOTE: diagnostics only; no occupancy classification is performed.')

if __name__=='__main__': main()
