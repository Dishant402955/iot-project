import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools' / 'collect_presence_interleaved.py'
spec = importlib.util.spec_from_file_location('collect_presence_interleaved', SCRIPT)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

class InterleavedCollectorTest(unittest.TestCase):
    def test_five_round_order_is_balanced_and_alternating(self):
        self.assertEqual(
            [collector.condition_order(i) for i in range(1, 6)],
            [['ABSENT', 'PRESENT'], ['PRESENT', 'ABSENT'], ['ABSENT', 'PRESENT'],
             ['PRESENT', 'ABSENT'], ['ABSENT', 'PRESENT']],
        )
        self.assertEqual(collector.CAPTURES_PER_BATCH, 50)
        self.assertEqual(collector.SETTLE_SECONDS, 30)

    def test_audit_counts_require_joint_target_attributed_csi(self):
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / 'presence_audit.csv'
            fields = ['rx_idle_satisfied', 'target_source_match', 'csi_structurally_valid',
                      'first_frame_rssi', 'csi_tone_spread_db', 'csi_cfo_hz']
            rows = []
            for i in range(10):
                rows.append({
                    'rx_idle_satisfied': 'True',
                    'target_source_match': 'True' if i < 9 else 'False',
                    'csi_structurally_valid': 'True' if i < 8 else 'False',
                    'first_frame_rssi': str(-40 - i),
                    'csi_tone_spread_db': str(0.2 + i / 100),
                    'csi_cfo_hz': str(100 + i),
                })
            with audit.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader(); writer.writerows(rows)
            result = collector.audit_counts(audit.parent)
            self.assertEqual(result['target_source_match_count'], 9)
            self.assertEqual(result['strict_csi_count'], 8)
            self.assertEqual(result['target_attributed_strict_csi_count'], 8)
            self.assertAlmostEqual(result['target_attributed_strict_csi_fraction'], 0.8)
            self.assertEqual(result['median_target_frame_rssi'], -44.5)
            self.assertIsNotNone(result['median_csi_tone_spread_db'])
            self.assertIsNotNone(result['median_csi_cfo_hz'])

if __name__ == '__main__': unittest.main()
