import sys, tempfile
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dataset import load_csi_csv

class DatasetLoaderTests(unittest.TestCase):
    def test_loads_and_averages_two_ltf_streams(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'tiny.csv'
            row = {'event_timeStamp': 100, 'unix_timestamp': 1.0,
                   'channel': 79, 'bandwidth_MHz': 160,
                   'measurement_time_repetition_ms': 10,
                   'frequency_carrier_MHz': 6300}
            for i in range(512):
                row[f'csi1-{i}-real'] = 2.0
                row[f'csi1-{i}-imag'] = 4.0
                row[f'csi2-{i}-real'] = 4.0
                row[f'csi2-{i}-imag'] = 8.0
            pd.DataFrame([row, row]).to_csv(path, index=False)
            csi, meta = load_csi_csv(path, chunksize=1)
            self.assertEqual(csi.shape, (2, 512))
            self.assertTrue(np.allclose(csi, 3.0 + 6.0j))
            self.assertEqual(len(meta), 2)

if __name__ == '__main__':
    unittest.main()
