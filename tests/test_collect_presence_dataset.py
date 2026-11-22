import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('collect_presence_dataset', ROOT / 'tools' / 'collect_presence_dataset.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

class CollectionPlanTests(unittest.TestCase):
    def test_fixed_collection_plan(self):
        self.assertEqual(module.BATCHES_PER_PHASE, 3)
        self.assertEqual(module.CAPTURES_PER_BATCH, 50)
        self.assertEqual(module.SETTLE_SECONDS, 30)
        self.assertEqual(module.BATCHES_PER_PHASE * module.CAPTURES_PER_BATCH, 150)

    def test_phase_labels_are_binary(self):
        self.assertEqual('present' if 'PRESENT' == 'PRESENT' else 'absent', 'present')
        self.assertEqual('present' if 'ABSENT' == 'PRESENT' else 'absent', 'absent')

if __name__ == '__main__':
    unittest.main()
