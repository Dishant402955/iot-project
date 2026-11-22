#!/usr/bin/env python3
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ANALYZER=ROOT/'tools/analyze_presence_run.py'

class PresenceAuditTest(unittest.TestCase):
    def run_case(self, wrong_source=False, idle_failure=False, weak_csi=False, trigger='crcok'):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); log=d/'run.jsonl'; series=d/'series.jsonl'; manifest=d/'manifest.json'
            target='aa:bb:cc:dd:ee:ff'
            manifest.write_text(json.dumps({'connected_bssid':target, 'trigger':trigger}))
            events=[]; rows=[]
            for i in range(1,11):
                begin=i*1000000; armed=begin+100; done=begin+500000
                events.append({'ev':'la.capture','ok':1,'file':f'/tmp/capture.{i:04d}.bin',
                    'arm_begin_steady_us':begin,'armed_steady_us':armed,'done_steady_us':done,'rx_idle':0 if idle_failure and i<=2 else 1,'ms':130})
                # A pre-arm frame from another AP must not be selected.
                events.append({'ev':'rx.presence_frame','steady_us':begin+50,'fc0':128,
                    'addr2':'001122334455','addr3':'001122334455','crc':0,'icv':0,'rssi':70})
                addr='001122334455' if wrong_source and i<=2 else 'aabbccddeeff'
                events.append({'ev':'rx.presence_frame','steady_us':begin+200,'fc0':128,
                    'addr2':addr,'addr3':addr,'crc':0,'icv':0,'rssi':70})
                for tone in range(-26,27):
                    if tone==0: continue
                    rows.append({'capture_file':f'/tmp/capture.{i:04d}.bin','tone':tone,
                        'mag_db':-40.0+tone*0.01,'phase_rad':0.1,
                        'lltf_repeat_corr':0.70 if weak_csi and i<=3 else 0.99,'lltf_stf16_corr':0.06,
                        'lltf_symbol_relerr':0.02,'cfo_hz':44000,'lltf_start_sample':1300})
            log.write_text(''.join(json.dumps(e)+'\n' for e in events))
            series.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            proc=subprocess.run([sys.executable,str(ANALYZER),'--log',str(log),'--series',str(series),
                '--manifest',str(manifest),'--output-prefix',str(d/'audit')],capture_output=True,text=True)
            return proc, json.loads((d/'audit.json').read_text())

    def test_target_frames_after_arm_and_joint_gate(self):
        proc, report=self.run_case()
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        self.assertTrue(report['ready_for_controlled_presence_dataset'])
        self.assertEqual(report['target_source_matches'],10)
        self.assertEqual(report['target_and_csi_captures'],10)

    def test_wrong_source_blocks_gate(self):
        proc, report=self.run_case(wrong_source=True)
        self.assertEqual(proc.returncode,3,proc.stdout+proc.stderr)
        self.assertFalse(report['ready_for_controlled_presence_dataset'])
        self.assertEqual(report['target_source_matches'],8)

    def test_rx_idle_failure_blocks_attribution_gate(self):
        proc, report=self.run_case(idle_failure=True)
        self.assertEqual(proc.returncode,3,proc.stdout+proc.stderr)
        self.assertFalse(report['ready_for_controlled_presence_dataset'])
        self.assertEqual(report['rx_idle_captures'],8)

    def test_weak_ltf_blocks_joint_csi_gate(self):
        proc, report=self.run_case(weak_csi=True)
        self.assertEqual(proc.returncode,3,proc.stdout+proc.stderr)
        self.assertFalse(report['ready_for_controlled_presence_dataset'])
        self.assertEqual(report['target_and_csi_captures'],7)

    def test_cca_uses_post_arm_rx_frame_heuristic(self):
        proc, report=self.run_case(trigger='cca')
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        self.assertTrue(report['target_source_attribution_available'])
        self.assertEqual(report['target_source_matches'],10)
        self.assertTrue(report['ready_for_controlled_presence_dataset'])

    def test_manual_trigger_never_claims_source_attribution(self):
        proc, report=self.run_case(trigger='manual')
        self.assertEqual(proc.returncode,3,proc.stdout+proc.stderr)
        self.assertFalse(report['target_source_attribution_available'])
        self.assertIsNone(report['target_source_fraction'])
        self.assertIsNone(report['target_source_matches'])
        self.assertFalse(report['ready_for_controlled_presence_dataset'])

if __name__=='__main__': unittest.main()
