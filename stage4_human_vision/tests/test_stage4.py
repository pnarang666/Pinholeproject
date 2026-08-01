import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from stage4_human_vision.acuity import mar_from_cutoff_cpd
from stage4_human_vision.config import load_default_config
from stage4_human_vision.csf import barten_simplified_csf, mannos_sakrison_csf
from stage4_human_vision.illuminance import retinal_illuminance_trolands, solve_pupil_and_retinal_illuminance
from stage4_human_vision.pupil import watson_yellott_pupil_mm
from stage4_human_vision.validation import regression_stats
from stage4_human_vision.visual_strehl import compute_vsotf


class Stage4UnitTests(unittest.TestCase):
    def test_watson_yellott_shrinks_with_luminance(self):
        dim = watson_yellott_pupil_mm(1.0, 20.0, 30.0, 2)
        bright = watson_yellott_pupil_mm(1000.0, 20.0, 30.0, 2)
        self.assertGreater(dim, bright)

    def test_troland_definition(self):
        td = retinal_illuminance_trolands(100.0, 2.0)
        self.assertAlmostEqual(td, 100.0 * 3.141592653589793, places=6)

    def test_pupil_iteration_respects_stop(self):
        result = solve_pupil_and_retinal_illuminance(1000.0, 1.0, 20.0, 30.0, 2)
        self.assertLessEqual(result["effective_stop_diameter_mm"], result["natural_pupil_diameter_mm"])
        self.assertGreater(result["iterations"], 0)

    def test_csf_models_positive(self):
        config = load_default_config()
        values_barten = barten_simplified_csf([1.0, 4.0, 8.0], 100.0, 20.0, config)
        values_mannos = mannos_sakrison_csf([1.0, 4.0, 8.0], config)
        self.assertTrue(all(v >= 0 for v in values_barten))
        self.assertTrue(all(v >= 0 for v in values_mannos))

    def test_vsotf_reference_is_one(self):
        result = compute_vsotf([1, 2, 3], [1, 0.5, 0.25], [1, 2, 3], [1, 0.5, 0.25], [1, 1, 1])
        self.assertAlmostEqual(result["vsotf"], 1.0, places=6)

    def test_acuity_identity(self):
        self.assertAlmostEqual(mar_from_cutoff_cpd(30.0), 1.0, places=6)

    def test_regression_stats_identity(self):
        stats = regression_stats([1, 2, 3], [1, 2, 3])
        self.assertAlmostEqual(stats["rmse"], 0.0, places=6)
        self.assertAlmostEqual(stats["mae"], 0.0, places=6)
        self.assertAlmostEqual(stats["r2"], 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
