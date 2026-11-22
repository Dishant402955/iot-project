import csv
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import reprocess_presence_archives as r


def make_dump(path: Path) -> None:
    rng = np.random.default_rng(812)
    ref = r.la_csi.ltf_ref_time()
    ltf = np.concatenate([ref[-32:], ref.copy(), ref.copy()])
    # Make the second symbol's matched-filter peak stronger, reproducing the
    # alignment bug that the corrected extractor must handle.
    ltf[32:96] += 0.008 * (rng.standard_normal(64) + 1j * rng.standard_normal(64))
    cfo = 45e3 / 20e6
    signal = ltf * np.exp(2j * np.pi * cfo * np.arange(len(ltf)))
    samples = np.zeros(8192, dtype=complex)
    samples[1000:1000 + len(signal)] = signal
    i = np.clip(np.rint(samples.real * 850), -2048, 2047).astype(np.int32)
    q = np.clip(np.rint(samples.imag * 850), -2048, 2047).astype(np.int32)
    words = ((i & 0xFFF) | ((q & 0xFFF) << 12)).astype('<u8')
    header = bytearray(32)
    header[:5] = b'DVLA\x01'
    header[7] = 2
    struct.pack_into('<I', header, 12, len(words))
    with path.open('wb') as stream:
        stream.write(header)
        words.tofile(stream)


class ReprocessPresenceArchiveTests(unittest.TestCase):
    def test_capture_index(self):
        self.assertEqual(r.capture_index(Path('capture.0042.bin')), 42)
        with self.assertRaises(ValueError):
            r.capture_index(Path('other.bin'))

    def test_extract_profile_recovers_second_peak_alignment(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'capture.0001.bin'
            make_dump(path)
            profile, metrics, index = r.extract_profile(path)
            self.assertEqual(index, 1)
            self.assertEqual(profile.shape, (52,))
            self.assertTrue(np.all(np.isfinite(profile)))
            self.assertGreaterEqual(metrics['repeat_corr'], 0.85)
            self.assertLessEqual(metrics['stf16_corr'], 0.50)
            self.assertLessEqual(metrics['symbol_relerr'], 0.25)
            self.assertAlmostEqual(metrics['lltf_start_sample'], 1032, delta=1)

    def test_batch_reprocessing_requires_target_attribution(self):
        with tempfile.TemporaryDirectory() as td:
            archive = Path(td)
            make_dump(archive / 'capture.0001.bin')
            make_dump(archive / 'capture.0002.bin')
            (archive / 'run_manifest.json').write_text(json.dumps({
                'connected_bssid': 'aa:bb:cc:dd:ee:ff', 'channel': 149,
            }))
            with (archive / 'presence_audit.csv').open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    'capture_index', 'target_source_match', 'rx_idle_satisfied'])
                writer.writeheader()
                writer.writerow({'capture_index': 1, 'target_source_match': 'True', 'rx_idle_satisfied': 'True'})
                writer.writerow({'capture_index': 2, 'target_source_match': 'False', 'rx_idle_satisfied': 'True'})
            result = r.reprocess_batch({
                'record_type': 'interleaved_presence_batch',
                'round_number': 1, 'condition': 'ABSENT',
                'raw_archive_dir': str(archive), 'valid_csi_profiles': 0,
                'bssid': 'aa:bb:cc:dd:ee:ff', 'channel': 149,
                'captures_requested': 2,
            })
            self.assertEqual(result['captures_reprocessed'], 2)
            self.assertEqual(result['strict_csi_count'], 2)
            self.assertEqual(result['target_attributed_strict_csi_count'], 1)
            self.assertEqual(len(result['profiles_db_centered']), 1)
            self.assertEqual(result['rx_idle_count'], 2)


if __name__ == '__main__':
    unittest.main()
