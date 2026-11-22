import sys
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import evaluate_presence_heldout as heldout

class HeldoutEvaluationTests(unittest.TestCase):
    def test_frozen_centroid_classifier_uses_only_serialized_parameters(self):
        model = {
            'scaler_mean': [0.0] * 52,
            'scaler_scale': [1.0] * 52,
            'centroid_absent': [0.0] * 52,
            'centroid_present': [2.0] * 52,
        }
        prediction, d0, d1 = heldout.classify_batch(np.ones(52), model)
        self.assertEqual(prediction, 1)  # exact tie is deterministically PRESENT
        self.assertAlmostEqual(d0, d1)

    def test_metrics_confusion_matrix(self):
        rows = [
            {'truth': 0, 'prediction': 0},
            {'truth': 0, 'prediction': 1},
            {'truth': 1, 'prediction': 1},
            {'truth': 1, 'prediction': 0},
        ]
        metrics = heldout.confusion_metrics(rows)
        self.assertEqual((metrics['tp'], metrics['tn'], metrics['fp'], metrics['fn']), (1, 1, 1, 1))
        self.assertEqual(metrics['balanced_accuracy'], 0.5)

if __name__ == '__main__':
    unittest.main()
