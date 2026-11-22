#!/usr/bin/env python3
"""Room-calibrated, low-rate CSI channel-anomaly presence indicator.

This is an experimental binary occupancy indicator, not RF-DS reproduction or
an accuracy-validated detector. Run with sudo because the capture script
briefly binds the Wi-Fi adapter to VFIO and restores its normal driver.
"""
from __future__ import annotations
import argparse, csv, json, math, os, re, signal, statistics, subprocess, sys, tempfile, time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
except ImportError as exc:
    raise SystemExit('NumPy is required. Use vendor/.venv/bin/python.') from exc

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'tools' / 'rtl8821ce_pcie_la_capture.sh'
DEFAULT_BASELINE = ROOT / 'data' / 'live_presence_baseline.json'
WIFI_IFACE = os.environ.get('WIFI_PRESENCE_IFACE', 'wlp1s0')
QUALITY = {'repeat': 0.85, 'stf16': 0.50, 'symbol_err': 0.25}


def normalized_profile(rows):
    rows = sorted(rows, key=lambda r: int(r['tone']))
    tones = [int(r['tone']) for r in rows]
    values = np.asarray([float(r['mag_db']) for r in rows], dtype=float)
    if len(rows) != 52 or len(set(tones)) != 52 or not np.all(np.isfinite(values)):
        return None
    return values - np.median(values)


def load_valid_profiles(run_dir: Path):
    series_path = run_dir / 'csi_series.jsonl'
    audit_path = run_dir / 'presence_audit.csv'
    manifest_path = run_dir / 'run_manifest.json'
    if not all(p.is_file() for p in (series_path, audit_path, manifest_path)):
        raise RuntimeError(f'Capture artifacts incomplete in {run_dir}')
    with manifest_path.open() as f: manifest = json.load(f)
    audit = {}
    with audit_path.open(newline='') as f:
        for row in csv.DictReader(f): audit[int(row['capture_index'])] = row
    groups = {}
    with series_path.open(errors='replace') as f:
        for line in f:
            try:
                row = json.loads(line)
                groups.setdefault(int(row['capture_index']), []).append(row)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue
    profiles = []
    for index, rows in sorted(groups.items()):
        if len(rows) != 52: continue
        first = rows[0]
        try:
            if float(first['lltf_repeat_corr']) < QUALITY['repeat']: continue
            if float(first['lltf_stf16_corr']) > QUALITY['stf16']: continue
            if float(first['lltf_symbol_relerr']) > QUALITY['symbol_err']: continue
        except (KeyError, TypeError, ValueError): continue
        a = audit.get(index, {})
        if a.get('target_source_match', '').lower() != 'true': continue
        profile = normalized_profile(rows)
        if profile is not None: profiles.append(profile)
    bssid = str(manifest.get('connected_bssid', '')).lower()
    channel = manifest.get('channel', manifest.get('connected_channel'))
    return profiles, bssid, channel


def current_link():
    """Return (BSSID, channel) from the restored Wi-Fi interface, if associated."""
    try:
        result = subprocess.run(['iwconfig', WIFI_IFACE], capture_output=True,
                                text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    output = result.stdout + result.stderr
    match = re.search(r'Access Point:\s*([0-9A-Fa-f:]{17})', output)
    bssid = match.group(1).lower() if match else None
    channel_match = re.search(r'\bChannel[:=](\d+)', output)
    channel = int(channel_match.group(1)) if channel_match else None
    if channel is None:
        freq_match = re.search(r'Frequency[:=]([0-9.]+)\s*GHz', output)
        if freq_match:
            freq = float(freq_match.group(1))
            if 2.3 <= freq < 2.5:
                channel = round((freq - 2.407) / 0.005)
            elif 4.9 <= freq < 6.0:
                channel = round((freq - 5.0) / 0.005)
    if not bssid or bssid == '00:00:00:00:00:00':
        return None, channel
    return bssid, channel


def wait_for_association(expected_bssid=None, expected_channel=None, timeout=60):
    """Wait for NetworkManager to reassociate after VFIO driver restoration."""
    deadline = time.monotonic() + timeout
    next_reconnect_attempt = 0.0
    while time.monotonic() < deadline:
        bssid, channel = current_link()
        if bssid and (expected_bssid is None or bssid == expected_bssid):
            if expected_channel is None or channel is None or channel == int(expected_channel):
                return bssid, channel
        now = time.monotonic()
        if now >= next_reconnect_attempt and now + 5 < deadline:
            # The interface can appear a little after the driver is restored.
            # Retry periodically because an early nmcli call may race udev.
            try:
                subprocess.run(['nmcli', 'device', 'connect', WIFI_IFACE],
                               capture_output=True, text=True, timeout=12)
            except (OSError, subprocess.TimeoutExpired):
                pass
            next_reconnect_attempt = now + 10
        time.sleep(2)
    bssid, channel = current_link()
    raise RuntimeError(
        f'Wi-Fi did not reassociate to {expected_bssid or "the AP"} within {timeout}s '
        f'(current BSSID={bssid or "disconnected"}, channel={channel}). '
        f'Check the saved NetworkManager profile and reconnect {WIFI_IFACE} manually.'
    )


def capture_batch(count: int, timeout: int = 180):
    env = os.environ.copy()
    env['WIFI_PRESENCE_CAPTURE_COUNT'] = str(count)
    env['WIFI_PRESENCE_CAPTURE_INTERVAL_MS'] = '0'
    proc = subprocess.Popen(['bash', str(CAPTURE)], cwd=ROOT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)
    try:
        output, _ = proc.communicate(timeout=timeout)
    except KeyboardInterrupt:
        try:
            os.killpg(proc.pid, signal.SIGINT)
            output, _ = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            output, _ = proc.communicate()
        raise
    except subprocess.TimeoutExpired:
        try: os.killpg(proc.pid, signal.SIGINT)
        except ProcessLookupError: pass
        try: output, _ = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            output, _ = proc.communicate()
        raise RuntimeError('Capture batch timed out; capture process was stopped.\n' + (output or '')[-5000:])
    print((output or '')[-5000:], flush=True)
    if proc.returncode != 0:
        raise RuntimeError(f'Capture script exited {proc.returncode}; see capture output above.')
    match = re.search(r'^Artifacts:\s*(\S+)\s*$', output or '', re.M)
    if not match: raise RuntimeError('Could not locate capture artifact directory in script output.')
    run_dir = Path(match.group(1))
    profiles, bssid, channel = load_valid_profiles(run_dir)
    # The capture script intentionally restores the kernel driver but does not
    # restart NetworkManager. Wait for (and request) reconnection before the
    # next capture batch, otherwise the next batch races the association.
    wait_for_association(bssid, channel, timeout=60)
    return profiles, bssid, channel, run_dir


def robust_threshold(values, floor=0.8):
    x = np.asarray(values, dtype=float)
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med)))
    return max(float(floor), med + 6.0 * 1.4826 * mad), med, mad


def profile_shape_diagnostics(profiles):
    """Summarize linear spectral tilt and per-profile tone spread, without classifying."""
    matrix = np.vstack(profiles)
    tones = np.asarray(list(range(-26, 0)) + list(range(1, 27)), dtype=float)
    centered_tones = tones - np.mean(tones)
    centered_profiles = matrix - np.mean(matrix, axis=1, keepdims=True)
    slopes = centered_profiles @ centered_tones / float(np.dot(centered_tones, centered_tones))
    spreads = np.std(matrix, axis=1)
    slope_median = float(np.median(slopes))
    spread_median = float(np.median(spreads))
    return {
        'spectral_slope_median_db_per_tone': slope_median,
        'spectral_slope_mad_db_per_tone': float(np.median(np.abs(slopes - slope_median))),
        'tone_spread_median_db': spread_median,
        'tone_spread_mad_db': float(np.median(np.abs(spreads - spread_median))),
    }


def build_baseline(profiles, bssid, channel):
    matrix = np.vstack(profiles)
    shape = profile_shape_diagnostics(profiles)
    center = np.median(matrix, axis=0)
    residual = matrix - center
    per_tone_mad = np.median(np.abs(residual), axis=0)
    distances = np.sqrt(np.mean(residual ** 2, axis=1))
    anomaly_threshold, dist_med, dist_mad = robust_threshold(distances, 0.8)
    adjacent = np.sqrt(np.mean(np.diff(matrix, axis=0) ** 2, axis=1)) if len(matrix) > 1 else np.array([0.0])
    motion_threshold, motion_med, motion_mad = robust_threshold(adjacent, 0.5)
    return {
        'schema_version': 2,
        'created_at': datetime.now(timezone.utc).isoformat(), 'connected_bssid': bssid,
        'channel': channel, 'tones': list(range(-26, 0)) + list(range(1, 27)),
        'profile_db_centered': center.tolist(), 'per_tone_mad_db': per_tone_mad.tolist(),
        'anomaly_threshold_db': anomaly_threshold, 'baseline_distance_median_db': dist_med,
        'baseline_distance_mad_db': dist_mad, 'motion_threshold_db': motion_threshold,
        'baseline_motion_median_db': motion_med, 'baseline_motion_mad_db': motion_mad,
        'sample_count': int(len(matrix)),
        'profile_spectral_slope_median_db_per_tone': shape['spectral_slope_median_db_per_tone'],
        'profile_spectral_slope_mad_db_per_tone': shape['spectral_slope_mad_db_per_tone'],
        'profile_tone_spread_median_db': shape['tone_spread_median_db'],
        'profile_tone_spread_mad_db': shape['tone_spread_mad_db'],
        'interpretation': 'Empty-room CSI channel-anomaly baseline; shape diagnostics are nuisance monitors, not presence features.'}


class PresenceState:
    def __init__(self, hold_seconds=15):
        self.hold_seconds = float(hold_seconds)
        self.recent = deque(maxlen=3)
        self.present_until = 0.0

    def update(self, positive, now=None):
        now = time.monotonic() if now is None else float(now)
        self.recent.append(bool(positive))
        if sum(self.recent) >= 2:
            self.present_until = max(self.present_until, now + self.hold_seconds)
        return now < self.present_until, max(0.0, self.present_until - now)


def score_profiles(profiles, baseline):
    if not profiles: return None
    center = np.asarray(baseline['profile_db_centered'], dtype=float)
    matrix = np.vstack(profiles)
    anomaly = np.sqrt(np.mean((matrix - center) ** 2, axis=1))
    motion = np.sqrt(np.mean(np.diff(matrix, axis=0) ** 2, axis=1)) if len(matrix) > 1 else np.array([0.0])
    return float(np.median(anomaly)), float(np.percentile(motion, 90)), float(np.max(anomaly))


def presence_state_label(raw_positive, smoothed_present):
    """Keep a one-batch raw trigger distinct from confirmed smoothed presence."""
    if smoothed_present:
        return 'PRESENT'
    return 'PENDING' if raw_positive else 'ABSENT'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--calibration-seconds', type=float, default=30)
    ap.add_argument('--batch-captures', type=int, default=50, help='captures per batch; larger batches improve the chance of collecting enough valid CSI')
    ap.add_argument('--min-valid-csi', type=int, default=5, help='minimum strict-quality CSI profiles required before scoring a batch')
    ap.add_argument('--hold-seconds', type=float, default=15)
    ap.add_argument('--baseline', type=Path, default=DEFAULT_BASELINE)
    ap.add_argument('--skip-calibration', action='store_true')
    ap.add_argument('--once', action='store_true', help='score one capture batch using an existing baseline; reports raw trigger separately because smoothing needs multiple batches')
    ap.add_argument('--yes', action='store_true', help='do not wait for Enter before empty-room calibration')
    args = ap.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run at the laptop console with sudo: sudo vendor/.venv/bin/python tools/live_presence_detector.py')
    if not 10 <= args.batch_captures <= 200: ap.error('--batch-captures must be 10..200')
    if not 3 <= args.min_valid_csi <= args.batch_captures: ap.error('--min-valid-csi must be 3..batch-captures')
    if args.calibration_seconds < 10: ap.error('--calibration-seconds must be at least 10')
    if not args.skip_calibration:
        print('\nEMPTY-ROOM CALIBRATION: leave the monitored room/area empty. Keep the laptop and AP fixed.', flush=True)
        print('The Wi-Fi adapter is temporarily used for CSI capture; the detector waits for NetworkManager to reconnect after every batch.', flush=True)
        if not args.yes: input('Clear the area, then press Enter to calibrate... ')
        collected=[]; first_bssid=None; first_channel=None; batches=0
        deadline=time.monotonic()+args.calibration_seconds
        while (time.monotonic() < deadline or len(collected) < 40) and batches < 20:
            profiles, bssid, channel, run_dir = capture_batch(args.batch_captures)
            batches += 1
            if not bssid: raise RuntimeError('Capture manifest has no connected AP BSSID.')
            if first_bssid is None: first_bssid, first_channel = bssid, channel
            if bssid != first_bssid or channel != first_channel:
                raise RuntimeError('AP identity/channel changed during calibration; restart with a stable AP.')
            collected.extend(profiles)
            print(f'CALIBRATION: valid CSI {len(collected)} (latest batch {len(profiles)}/{args.batch_captures}) from {run_dir}', flush=True)
            if len(collected) >= 40 and time.monotonic() >= deadline: break
            if len(collected) >= 120: break
        if len(collected) < 30:
            raise RuntimeError(f'Only {len(collected)} valid CSI captures collected after {batches} bounded batches. Check 5 GHz AP/channel and rerun; no baseline saved.')
        baseline=build_baseline(collected, first_bssid, first_channel)
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(baseline, indent=2)+'\n')
        print(f'BASELINE_SAVED: {args.baseline} using {len(collected)} valid CSI profiles.', flush=True)
    else:
        if not args.baseline.is_file(): raise SystemExit(f'Baseline not found: {args.baseline}; run without --skip-calibration first.')
        baseline=json.loads(args.baseline.read_text())
    if not args.baseline.is_file(): raise RuntimeError('Baseline file was not created.')
    state=PresenceState(args.hold_seconds)
    print(f"MONITORING: AP={baseline.get('connected_bssid')} channel={baseline.get('channel')}; Ctrl+C to stop.", flush=True)
    while True:
        profiles,bssid,channel,run_dir=capture_batch(args.batch_captures)
        if bssid != baseline.get('connected_bssid') or channel != baseline.get('channel'):
            raise RuntimeError('Connected AP/channel differs from calibration baseline. Recalibrate.')
        if len(profiles) < args.min_valid_csi:
            print(f'{datetime.now().astimezone().isoformat(timespec="seconds")} INSUFFICIENT_CSI '
                  f'valid={len(profiles)}/{args.batch_captures} required={args.min_valid_csi}; '
                  f'no presence decision made latest={run_dir}', flush=True)
            if args.once: return 2
            continue
        scored=score_profiles(profiles,baseline)
        if scored is None:
            print(f'{datetime.now().astimezone().isoformat(timespec="seconds")} INSUFFICIENT_CSI '
                  f'valid={len(profiles)}/{args.batch_captures}; no presence decision made latest={run_dir}', flush=True)
            if args.once: return 2
            continue
        anomaly,motion,peak=scored
        shape=profile_shape_diagnostics(profiles)
        baseline_slope=baseline.get('profile_spectral_slope_median_db_per_tone')
        if baseline_slope is None:
            tones=np.asarray(list(range(-26,0))+list(range(1,27)),dtype=float)
            baseline_slope=float(np.polyfit(tones,np.asarray(baseline['profile_db_centered'],dtype=float),1)[0])
        positive=(anomaly >= float(baseline['anomaly_threshold_db']) or motion >= float(baseline['motion_threshold_db']))
        present,remaining=state.update(positive)
        label=presence_state_label(positive, present)
        raw_label='TRIGGER' if positive else 'CLEAR'
        print(f'{datetime.now().astimezone().isoformat(timespec="seconds")} {label} '
              f'raw_signal={raw_label} smoothed={"PRESENT" if present else "NOT_PRESENT"} '
              f'anomaly={anomaly:.2f}/{baseline["anomaly_threshold_db"]:.2f}dB '
              f'peak={peak:.2f}dB motion_p90={motion:.2f}/{baseline["motion_threshold_db"]:.2f}dB '
              f'spectral_slope={shape["spectral_slope_median_db_per_tone"]:.4f}/{baseline_slope:.4f}dB_per_tone '
              f'tone_spread={shape["tone_spread_median_db"]:.3f}dB '
              f'valid_CSI={len(profiles)}/{args.batch_captures} hold={remaining:.1f}s latest={run_dir}', flush=True)
        if args.once: return 0

if __name__ == '__main__':
    try: raise SystemExit(main())
    except KeyboardInterrupt: print('\nStopped. Capture script restores the Wi-Fi driver after each batch.', flush=True)
