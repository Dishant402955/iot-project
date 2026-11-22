import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / 'tools' / 'analyze_interleaved_presence.py'

class InterleavedAnalysisTest(unittest.TestCase):
    def test_five_rounds_are_summarized_without_presence_claim(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            session = d / 'session.jsonl'
            records = [{'record_type': 'session_metadata', 'experiment': 'five_round_interleaved_v1'}]
            for round_no in range(1, 6):
                for condition, offset in [('ABSENT', 0.0), ('PRESENT', 0.1)]:
                    profiles = [[offset + tone * 0.001 for tone in range(52)] for _ in range(8)]
                    records.append({
                        'record_type': 'interleaved_presence_batch', 'round_number': round_no,
                        'condition': condition, 'profiles_db_centered': profiles,
                        'valid_csi_profiles': len(profiles), 'csi_yield_gate_pass': True,
                        'target_attribution_gate_pass': True, 'bssid': 'aa:bb:cc:dd:ee:ff',
                        'channel': 149, 'strict_csi_fraction': 0.9,
                        'target_source_match_fraction': 1.0, 'rx_idle_fraction': 1.0,
                        'capture_attempts_audited': 50,
                    })
            session.write_text(''.join(json.dumps(x) + '\n' for x in records))
            proc = subprocess.run([sys.executable, str(ANALYZER), str(session)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads((d / 'session_analysis.json').read_text())
            self.assertEqual(report['rounds'], 5)
            self.assertEqual(report['batches_passing_both_acquisition_gates'], 10)
            self.assertTrue(report['same_bssid_and_channel_all_batches'])
            self.assertAlmostEqual(report['absent_vs_present_median_profile_distance_db'], 0.1, places=5)
            self.assertFalse(report['baseline_modified'])

    def test_incomplete_session_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            session = Path(td) / 'partial.jsonl'
            session.write_text(json.dumps({'record_type':'session_metadata','experiment':'five_round_interleaved_v1'}) + '\n')
            proc = subprocess.run([sys.executable, str(ANALYZER), str(session)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('Expected 10 complete batches', proc.stderr)

if __name__ == '__main__': unittest.main()
