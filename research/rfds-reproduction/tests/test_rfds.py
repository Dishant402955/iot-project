import sys
from pathlib import Path
import unittest
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rfds import RFDSConfig, make_range_filters, design_mti_fir, detect_presence

class RFDSTests(unittest.TestCase):
    def test_range_resolution_matches_paper_160mhz(self):
        cfg = RFDSConfig()
        self.assertAlmostEqual(cfg.range_resolution_m, 0.93685, places=4)

    def test_range_filter_shape_and_unit_magnitude(self):
        f = make_range_filters(512, RFDSConfig())
        self.assertEqual(f.shape, (9, 512))
        self.assertAlmostEqual(RFDSConfig().range_gates_m is None, True)
        self.assertAlmostEqual((8 * RFDSConfig().range_resolution_m), 7.4948, places=3)
        self.assertTrue(np.allclose(np.abs(f), 1.0))

    def test_fir_is_64th_order_cosine_highpass(self):
        b = design_mti_fir(RFDSConfig())
        self.assertEqual(len(b), 65)
        self.assertTrue(np.isfinite(b).all())
        self.assertLess(abs(np.sum(b)), 0.1)
        from scipy import signal
        freq, response = signal.freqz(b, worN=4096, fs=100.0)
        dc = abs(response[0])
        high = abs(response[np.argmin(abs(freq - 20.0))])
        self.assertLess(dc, 1e-6)
        self.assertGreater(high, 0.8)

    def test_end_to_end_produces_binary_decisions(self):
        rng = np.random.default_rng(7)
        n, tones = 180, 512
        t = np.arange(n) / 100.0
        f = (np.arange(tones) - (tones - 1) / 2) * (160e6 / tones)
        # Synthetic moving reflector at ~1 m with slow phase modulation.
        delay_phase = np.exp(-1j * 2 * np.pi * (2.0 / 299792458.0) * f)
        motion = np.exp(1j * 2 * np.pi * 2.0 * t)
        x = 0.02 * (rng.normal(size=(n, tones)) + 1j*rng.normal(size=(n, tones)))
        x += (1.0 + 0.3 * motion[:, None]) * delay_phase[None, :]
        result = detect_presence(x, RFDSConfig())
        self.assertGreater(len(result['present']), 0)
        self.assertEqual(result['present'].dtype, np.bool_)
        self.assertTrue(np.isfinite(result['snr_db']).all())

if __name__ == '__main__':
    unittest.main()
