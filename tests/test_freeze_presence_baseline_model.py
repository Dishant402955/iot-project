import sys
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import freeze_presence_baseline_model as freeze

class FreezePresenceBaselineTests(unittest.TestCase):
    def test_model_is_fixed_to_sessions_one_and_two_and_excludes_heldout(self):
        model = freeze.build_model()
        self.assertEqual(model['training_batch_counts'], {'total': 20, 'absent': 10, 'present': 10})
        self.assertFalse(model['held_out_session_3_used'])
        self.assertEqual(model['deployment_status'], 'NOT_VALIDATED_NOT_FOR_OCCUPANCY_DECISIONS')
        self.assertEqual(len(model['scaler_mean']), 52)
        self.assertEqual(len(model['scaler_scale']), 52)
        self.assertEqual(len(model['centroid_absent']), 52)
        self.assertEqual(len(model['centroid_present']), 52)

    def test_model_cannot_be_built_from_an_alternate_or_heldout_path(self):
        with self.assertRaises(ValueError):
            freeze.build_model((freeze.ROOT / 'data/public_dataset/interleaved_session_3_anonymized.jsonl',))

if __name__ == '__main__':
    unittest.main()
