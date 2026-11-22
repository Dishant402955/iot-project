import sys
from pathlib import Path
import unittest
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baseline import make_model

class BaselineTests(unittest.TestCase):
    def test_model_supports_three_states(self):
        x = np.random.default_rng(1).normal(size=(30, 12))
        y = np.array(['PRESENT']*10 + ['APPROACH_LEAVE']*10 + ['ABSENT']*10)
        model = make_model().fit(x, y)
        self.assertEqual(set(model.predict(x)), set(y))

if __name__ == '__main__': unittest.main()
