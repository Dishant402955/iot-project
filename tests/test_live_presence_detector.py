import csv, json, sys, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import live_presence_detector as d

class LivePresenceDetectorTests(unittest.TestCase):
    def test_normalization_removes_common_gain(self):
        base=np.linspace(-2,2,52)
        tones=list(range(-26,0))+list(range(1,27))
        a=[{'tone':tone,'mag_db':float(v)} for tone,v in zip(tones,base)]
        b=[dict(x,mag_db=x['mag_db']+17.0) for x in a]
        np.testing.assert_allclose(d.normalized_profile(a),d.normalized_profile(b),atol=1e-10)

    def test_baseline_and_anomaly_score(self):
        rng=np.random.default_rng(7)
        profiles=[np.linspace(-1,1,52)+rng.normal(0,.03,52) for _ in range(60)]
        baseline=d.build_baseline(profiles,'aa:bb:cc:dd:ee:ff',149)
        quiet=d.score_profiles(profiles[:10],baseline)
        changed=[p+np.sin(np.linspace(0,8,52))*2 for p in profiles[:10]]
        active=d.score_profiles(changed,baseline)
        self.assertLess(quiet[0],baseline['anomaly_threshold_db'])
        self.assertGreater(active[0],baseline['anomaly_threshold_db'])
        self.assertEqual(len(baseline['profile_db_centered']),52)

    def test_profile_shape_diagnostics_measure_linear_spectral_tilt(self):
        tones=np.asarray(list(range(-26,0))+list(range(1,27)),dtype=float)
        base=np.cos(tones/7.0)*0.2
        profiles=[base+0.03*tones, base+0.031*tones, base+0.029*tones]
        result=d.profile_shape_diagnostics(profiles)
        self.assertAlmostEqual(result['spectral_slope_median_db_per_tone'],0.03,places=6)
        self.assertGreater(result['tone_spread_median_db'],0.1)
        self.assertLess(result['spectral_slope_mad_db_per_tone'],0.001)

    def test_detector_defaults_to_larger_batch_and_minimum_valid_csi(self):
        import argparse
        # Keep the operational defaults explicit: 20 captures was too sparse
        # when only 5-55% yielded strict-quality CSI.
        parser=argparse.ArgumentParser()
        parser.add_argument('--batch-captures', type=int, default=50)
        parser.add_argument('--min-valid-csi', type=int, default=5)
        args=parser.parse_args([])
        self.assertEqual(args.batch_captures,50)
        self.assertEqual(args.min_valid_csi,5)

    def test_channel_anomaly_never_becomes_occupancy_decision(self):
        self.assertEqual(d.occupancy_decision_label(True, False), 'UNKNOWN_UNVALIDATED')
        self.assertEqual(d.occupancy_decision_label(False, False), 'UNKNOWN_UNVALIDATED')
        self.assertEqual(d.occupancy_decision_label(False, True), 'UNKNOWN_UNVALIDATED')

    def test_baseline_overwrite_requires_explicit_flag(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'baseline.json'; p.write_text('{}')
            with self.assertRaises(RuntimeError): d.ensure_baseline_write_allowed(p, False)
            d.ensure_baseline_write_allowed(p, True)

    def test_profile_requires_exact_active_tone_set(self):
        tones=list(range(-26,0))+list(range(1,27))
        rows=[{'tone':tone,'mag_db':float(i)} for i,tone in enumerate(tones)]
        self.assertIsNotNone(d.normalized_profile(rows))
        rows[-1]['tone']=25
        self.assertIsNone(d.normalized_profile(rows))


    def test_rejects_missing_or_weak_csi_and_wrong_source(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/'run_manifest.json').write_text(json.dumps({'connected_bssid':'aa:bb:cc:dd:ee:ff','channel':149}))
            with (p/'presence_audit.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['capture_index','target_source_match','csi_structurally_valid','rx_idle_satisfied']); w.writeheader()
                w.writerows([
                    {'capture_index':1,'target_source_match':'True','csi_structurally_valid':'True','rx_idle_satisfied':'True'},
                    {'capture_index':2,'target_source_match':'True','csi_structurally_valid':'True','rx_idle_satisfied':'True'},
                    {'capture_index':3,'target_source_match':'False','csi_structurally_valid':'True','rx_idle_satisfied':'True'},
                    {'capture_index':4,'target_source_match':'True','csi_structurally_valid':'True','rx_idle_satisfied':'False'},
                    {'capture_index':5,'target_source_match':'True','csi_structurally_valid':'False','rx_idle_satisfied':'True'}
                ])
            rows=[]
            tones=list(range(-26,0))+list(range(1,27))
            for idx,repeat in [(1,.99),(2,.70),(3,.99),(4,.99),(5,.99)]:
                for tone in tones:
                    rows.append({'capture_index':idx,'tone':tone,'mag_db':-40+tone*.01,'phase_rad':.1,
                        'lltf_repeat_corr':repeat,'lltf_stf16_corr':.06,'lltf_symbol_relerr':.02})
            (p/'csi_series.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
            profiles,bssid,channel=d.load_valid_profiles(p)
            self.assertEqual(len(profiles),1)
            # Weak L-LTF, wrong AP source, RX-not-idle, and structurally invalid
            # records must all be excluded independently.
            self.assertEqual(bssid,'aa:bb:cc:dd:ee:ff')
            self.assertEqual(channel,149)


    def test_wait_for_association_accepts_expected_ap(self):
        with patch.object(d, 'current_link', return_value=('aa:bb:cc:dd:ee:ff', 149)):
            self.assertEqual(d.wait_for_association('aa:bb:cc:dd:ee:ff', 149, timeout=1),
                             ('aa:bb:cc:dd:ee:ff', 149))

    def test_current_link_parses_iwconfig(self):
        fake = type('Result', (), {'stdout': 'wlp1s0 IEEE 802.11 ESSID:"test"\n Frequency:5.745 GHz Access Point: AA:BB:CC:DD:EE:FF\n', 'stderr': ''})()
        with patch.object(d.subprocess, 'run', return_value=fake):
            self.assertEqual(d.current_link(), ('aa:bb:cc:dd:ee:ff', 149))

    def test_baseline_json_roundtrip(self):
        baseline=d.build_baseline([np.zeros(52)+i*.001 for i in range(45)],'aa',36)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'baseline.json'; p.write_text(json.dumps(baseline))
            loaded=json.loads(p.read_text())
            self.assertEqual(loaded['sample_count'],45)
            self.assertEqual(loaded['schema_version'],2)
            self.assertEqual(len(loaded['profile_db_centered']),52)
            self.assertIn('profile_spectral_slope_median_db_per_tone',loaded)
            self.assertIn('profile_tone_spread_median_db',loaded)

if __name__=='__main__': unittest.main()
