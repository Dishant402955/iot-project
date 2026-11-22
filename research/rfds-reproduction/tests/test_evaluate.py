import sys
from pathlib import Path
import unittest
import pandas as pd
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluate_labels import label_to_state, states_at_timestamps

class EvaluationTests(unittest.TestCase):
    def test_zone_mapping(self):
        self.assertEqual(label_to_state('sit'), 'PRESENT')
        self.assertEqual(label_to_state('stand_up'), 'PRESENT')
        self.assertEqual(label_to_state('1'), 'PRESENT')
        self.assertEqual(label_to_state('2'), 'APPROACH_LEAVE')
        self.assertEqual(label_to_state('5'), 'APPROACH_LEAVE')
        self.assertEqual(label_to_state('6'), 'ABSENT')
        self.assertEqual(label_to_state('out'), 'ABSENT')

    def test_epoch_time_alignment_uses_half_open_intervals(self):
        labels = pd.DataFrame([
            {'Label':'sit','Start Time':10000,'End Time':20000},
            {'Label':'3','Start Time':20000,'End Time':30000},
        ])
        got = states_at_timestamps(labels, np.array([9.999, 10.0, 19.999, 20.0, 29.999, 30.0]))
        self.assertEqual(got.tolist(), ['UNKNOWN','PRESENT','PRESENT','APPROACH_LEAVE','APPROACH_LEAVE','UNKNOWN'])

if __name__ == '__main__': unittest.main()
