import sys
import unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import analyze_live_presence_drift as a

class LivePresenceDriftTests(unittest.TestCase):
    def test_linear_detrend_removes_spectral_tilt(self):
        tones=np.asarray(list(range(-26,0))+list(range(1,27)),float)
        residual=np.cos(tones/5)*0.1; residual=residual-np.median(residual); profile=residual+0.04*tones+7
        original=profile.copy(); result,slope=a.linear_detrend_profile(profile,tones)
        self.assertAlmostEqual(slope,0.04,places=8)
        np.testing.assert_allclose(result,residual-np.median(residual),atol=1e-8)
        np.testing.assert_array_equal(profile,original)

    def test_detrended_distance_ignores_linear_tilt_and_gain(self):
        tones=np.asarray(list(range(-26,0))+list(range(1,27)),float)
        base=np.cos(tones/7); shifted=base+0.05*tones+2
        x,_=a.linear_detrend_profile(base,tones); y,_=a.linear_detrend_profile(shifted,tones)
        self.assertGreater(float(np.sqrt(np.mean((shifted-base)**2))),1.0)
        self.assertLess(float(np.sqrt(np.mean((x-y)**2))),1e-8)

    def test_missing_raw_capture_returns_unavailable_iq_metrics(self):
        result=a.iq_level_metrics(ROOT/'missing-capture.bin',1300)
        self.assertIsNone(result['iq_ltf_to_pre_db'])

if __name__=='__main__': unittest.main()
