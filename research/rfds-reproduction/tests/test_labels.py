import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluate_labels import states_at_timestamps

class TimestampLabelTests(unittest.TestCase):
    def test_timestamp_alignment_does_not_assume_video_frame_index_is_csi_index(self):
        labels = pd.DataFrame([{'Label':'sit','Start Time':10000,'End Time':20000}])
        # Sparse CSI times across a 100-second recording. Only the 10s-20s window is labelled.
        times = np.array([0.0, 10.0, 15.0, 20.0, 99.0])
        self.assertEqual(states_at_timestamps(labels, times).tolist(),
                         ['UNKNOWN','PRESENT','PRESENT','UNKNOWN','UNKNOWN'])

if __name__ == '__main__': unittest.main()
