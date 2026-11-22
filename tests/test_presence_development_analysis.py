import sys
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_presence_development as analysis


class PresenceDevelopmentAnalysisTests(unittest.TestCase):
    def test_metrics_include_sensitivity_specificity_and_balanced_accuracy(self):
        result = analysis.classification_metrics(
            np.asarray([0, 0, 1, 1]), np.asarray([0, 1, 1, 0])
        )
        self.assertEqual(result['tp'], 1)
        self.assertEqual(result['tn'], 1)
        self.assertEqual(result['fp'], 1)
        self.assertEqual(result['fn'], 1)
        self.assertEqual(result['balanced_accuracy'], 0.5)

    def test_centroid_uses_training_statistics_only_and_predicts_separated_batches(self):
        train = [
            {'label': 0, 'median_profile': np.asarray([0.0, 0.0, 0.0])},
            {'label': 0, 'median_profile': np.asarray([0.1, 0.0, 0.0])},
            {'label': 1, 'median_profile': np.asarray([4.0, 4.0, 4.0])},
            {'label': 1, 'median_profile': np.asarray([4.1, 4.0, 4.0])},
        ]
        test = [
            {'label': 0, 'median_profile': np.asarray([0.05, 0.0, 0.0])},
            {'label': 1, 'median_profile': np.asarray([4.05, 4.0, 4.0])},
        ]
        labels, predictions = analysis.nearest_centroid_scores(train, test)
        np.testing.assert_array_equal(labels, [0, 1])
        np.testing.assert_array_equal(predictions, [0, 1])

    def test_default_analysis_is_explicitly_limited_to_development_sessions(self):
        self.assertIn('interleaved_20261122_180724.jsonl', str(analysis.DEFAULT_SESSIONS[0]))
        self.assertIn('interleaved_20261122_183204.jsonl', str(analysis.DEFAULT_SESSIONS[1]))
        self.assertEqual(len(analysis.DEFAULT_SESSIONS), 4)
        self.assertNotIn('185040', ' '.join(map(str, analysis.DEFAULT_SESSIONS)))
        self.assertEqual(len(analysis.HELD_OUT_SESSION_3_SHA256), 64)

    def test_allowlist_uses_real_acquisition_session_ids(self):
        self.assertEqual(analysis.session_id_for_path(ROOT / 'data/presence_dataset/interleaved_20261122_180724.jsonl'), 1)
        self.assertEqual(analysis.session_id_for_path(ROOT / 'data/presence_dataset/interleaved_20261122_183204.jsonl'), 2)
        self.assertEqual(analysis.session_id_for_path(ROOT / 'data/presence_dataset/interleaved_20261122_200618.jsonl'), 4)
        self.assertEqual(analysis.session_id_for_path(ROOT / 'data/presence_dataset/interleaved_20261122_202430.jsonl'), 5)

    def test_consumed_session_three_filename_is_rejected_before_file_access(self):
        candidate = ROOT / 'data/presence_dataset/interleaved_20261122_185040.jsonl'
        with self.assertRaisesRegex(ValueError, 'non-allowlisted'):
            analysis.validate_development_sessions((candidate, ROOT / 'data/presence_dataset/interleaved_20261122_180724.jsonl'))

    def test_non_allowlisted_copy_inside_repo_is_rejected(self):
        candidate = ROOT / 'tmp/interleaved_20261122_180724.jsonl'
        with self.assertRaisesRegex(ValueError, 'non-allowlisted'):
            analysis.session_id_for_path(candidate)

    def test_source_hash_allowlist_covers_only_development_sessions(self):
        self.assertEqual(set(analysis.ALLOWED_SESSION_SHA256), set(analysis.ALLOWED_SESSION_FILES))
        self.assertNotIn(analysis.HELD_OUT_SESSION_3_SHA256, set(analysis.ALLOWED_SESSION_SHA256.values()))
        self.assertEqual(len(analysis.HELD_OUT_SESSION_3_SHA256), 64)


if __name__ == '__main__':
    unittest.main()
