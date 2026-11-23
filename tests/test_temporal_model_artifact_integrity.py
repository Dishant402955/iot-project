import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / 'models/presence_temporal_extra_trees_dev_v1.joblib'
METADATA_PATH = ROOT / 'models/presence_temporal_extra_trees_dev_v1.json'
EXPECTED_MODEL_SHA256 = 'ca09ee5d22f70ea64da8c72c727c17f3d5075b0e8fef75a2ac098857614867b6'


class TemporalModelArtifactIntegrityTests(unittest.TestCase):
    def test_saved_model_checksum_matches_frozen_expected_value(self):
        digest = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, EXPECTED_MODEL_SHA256)

    def test_model_metadata_matches_artifact_and_training_scope(self):
        metadata = json.loads(METADATA_PATH.read_text())
        digest = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
        self.assertEqual(metadata['artifact_sha256'], digest)
        self.assertEqual(metadata['model_id'], 'temporal_extra_trees_all_development_sessions_v1')
        self.assertEqual(
            [item['session'] for item in metadata['training_sessions']],
            [1, 2, 4, 5],
        )
        self.assertEqual(metadata['training_examples'], 40)
        self.assertEqual(metadata['class_counts'], {'ABSENT': 20, 'PRESENT': 20})


if __name__ == '__main__':
    unittest.main()
