import math
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
from stage4_human_vision.photon_noise import retinal_irradiance_w_m2
from stage4_human_vision.pupil import watson_yellott_pupil_mm
from stage4_human_vision.validation import regression_stats
from stage4_human_vision.visual_strehl import compute_vsotf

# Winn, Whitaker, Elliott & Phillips (1994), "Factors affecting light-adapted pupil
# size in normal human subjects", Invest Ophthalmol Vis Sci 35(3):1132-1137 -- N=91
# subjects, monocular adaptation, 10-degree diameter field. Values below are Table 1
# of Watson & Yellott (2012) verbatim (slope [mm/year], intercept [mm] of Winn et
# al.'s own linear fit of pupil diameter vs age, at each of their 5 tested
# luminances) -- real published empirical data, not re-derived from the Watson-
# Yellott formula (their formula's age term was FIT to approximate this table, so a
# close match mainly confirms this project's code implements their equations
# correctly without transcription bugs; see MODULE10_VALIDATION.md for the honest
# distinction between that and independent physiological validation).
WINN_1994_TABLE1 = {
    9.0: (-0.043, 8.046),
    44.0: (-0.04, 7.413),
    220.0: (-0.032, 6.275),
    1100.0: (-0.02, 4.854),
    4400.0: (-0.015, 4.07),
}


class Stage4UnitTests(unittest.TestCase):
    def test_watson_yellott_shrinks_with_luminance(self):
        dim = watson_yellott_pupil_mm(1.0, 20.0, 30.0, 2)
        bright = watson_yellott_pupil_mm(1000.0, 20.0, 30.0, 2)
        self.assertGreater(dim, bright)

    def test_watson_yellott_matches_winn_1994_reference_table(self):
        """Quantitative match against Winn et al. (1994)'s real measured data, as
        tabulated in Watson & Yellott (2012) Table 1 -- not a directional check.
        Threshold (RMSE<0.2mm, max<0.4mm) set with margin above the measured
        0.115mm/0.237mm from a 25-point (5 luminance x 5 age) sweep; see
        MODULE10_VALIDATION.md for the full sweep and honest discussion of what
        this test does and does not establish."""
        config = load_default_config()
        errors = []
        for luminance_cdm2, (slope, intercept) in WINN_1994_TABLE1.items():
            for age_years in (20, 30, 50, 70, 83):
                winn_reference_mm = slope * age_years + intercept
                predicted_mm = watson_yellott_pupil_mm(
                    luminance_cdm2=luminance_cdm2, field_diameter_deg=10.0,
                    age_years=age_years, eyes=1, config=config)
                errors.append(predicted_mm - winn_reference_mm)
        rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
        max_abs_error = max(abs(e) for e in errors)
        self.assertLess(rmse, 0.2, f"RMSE {rmse:.4f}mm vs Winn et al. (1994) exceeds 0.2mm")
        self.assertLess(max_abs_error, 0.4, f"max error {max_abs_error:.4f}mm vs Winn et al. (1994) exceeds 0.4mm")

    def test_watson_yellott_matches_figure17_demonstration(self):
        """Exact-value check against Watson & Yellott (2012)'s own Figure 17
        interactive demonstration (arrow-annotated value at L=1 cd/m^2, field
        diameter=60deg, age=40, eyes=2: 'Unified' curve = 4.839mm). This is a
        formula-fidelity check (does this code reproduce their own worked example),
        not an independent empirical validation -- see MODULE10_VALIDATION.md,
        including why the OTHER demo widget in the same paper (Figure 18's
        calculator, age=30, reads 3.828mm) was investigated and excluded as
        internally inconsistent with the paper's own linear-in-age formula."""
        config = load_default_config()
        predicted_mm = watson_yellott_pupil_mm(
            luminance_cdm2=1.0, field_diameter_deg=60.0, age_years=40.0, eyes=2, config=config)
        self.assertAlmostEqual(predicted_mm, 4.839, places=2)

    def test_troland_definition(self):
        td = retinal_illuminance_trolands(100.0, 2.0)
        self.assertAlmostEqual(td, 100.0 * 3.141592653589793, places=6)

    def test_photometric_td_matches_radiometric_retinal_irradiance_at_555nm(self):
        """DESIGN.md Module 1's validation calls for a 'cross-check photometric Td
        against radiometric retinal irradiance conversion at 555nm', beyond
        test_troland_definition's internal self-consistency check above. This
        cross-checks TWO INDEPENDENT existing code paths -- illuminance.py's
        photometric troland computation and photon_noise.py's radiometric W/m^2
        computation -- against the standard photometric<->radiometric identity:

            E_retina(W/m^2) = Td / (Km * 1e6 * v_r_m^2), Km = 683 lm/W

        Km=683 lm/W is the CIE/SI-defined peak photopic luminous efficacy, exact
        AT 555nm by definition (V(555nm)=1.0). The geometric form of this identity
        (radiance * pupilArea / eyeLength^2) was confirmed directly against
        Psychtoolbox's RadianceAndPupilAreaEyeLengthToRetIrradiance.m source (the
        exact 'Wyszecki and Stiles conventions as referenced by Psychtoolbox
        radiometric conversions' DESIGN.md's Module 1 names as its primary source)
        -- see MODULE10_VALIDATION.md. ocular_transmission=1.0 here to match
        Psychtoolbox's own convention of excluding ocular absorption from this
        specific geometric conversion (folded in separately, as their docs state)."""
        KM_LM_PER_W = 683.0
        L_cdm2 = 1000.0
        stop_diameter_mm = 3.0
        v_r_m = 0.017

        td = retinal_illuminance_trolands(L_cdm2, stop_diameter_mm)
        e_retina_ours = retinal_irradiance_w_m2(
            L_cdm2, stop_diameter_mm * 1e-3, v_r_m, ocular_transmission=1.0, wavelength_m=555e-9)
        e_retina_expected = td / (KM_LM_PER_W * 1e6 * v_r_m ** 2)
        self.assertAlmostEqual(e_retina_ours / e_retina_expected, 1.0, places=9)

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

    def test_mannos_sakrison_matches_published_formula_and_peak(self):
        """mannos_sakrison_csf() must equal H(f)=2.6(0.0192+0.114f)exp[-(0.114f)^1.1]
        exactly (this project's config IS that formula's coefficients) -- verified
        via multiple independent, mutually-consistent secondary reproductions in the
        image-quality-metrics literature (Mannos & Sakrison (1974), 'The effects of a
        visual fidelity criterion on the encoding of images', IEEE Trans. Inf. Theory
        20(4):525-536 -- the 1974 primary paper itself was not directly accessible;
        see MODULE10_VALIDATION.md). Also checks the resulting peak frequency lands
        at the commonly-cited ~8 cpd figure for this specific model."""
        config = load_default_config()
        freqs = [x * 0.1 for x in range(1, 601)]  # 0.1 to 60.0 cpd
        ours = mannos_sakrison_csf(freqs, config)
        manual = [2.6 * (0.0192 + 0.114 * f) * math.exp(-((0.114 * f) ** 1.1)) for f in freqs]
        for o, m in zip(ours, manual):
            self.assertAlmostEqual(o, m, places=6)
        peak_freq = freqs[max(range(len(ours)), key=lambda i: ours[i])]
        self.assertAlmostEqual(peak_freq, 8.0, delta=0.5)

    def test_barten_simplified_peak_and_cutoff_in_known_photopic_ranges(self):
        """barten_simplified_csf() is explicitly a simplified engineering form, NOT
        the full Barten (1999) model (confirmed: several 'barten_*' config fields --
        k, temporal integration, x0/xmax/nmax, sigma0 -- are declared but unused by
        this function; see MODULE10_VALIDATION.md). Checked here against
        commonly-cited photopic CSF ranges (peak ~2-6 cpd, cutoff ~30-70 cpd) rather
        than an exact-match, since it is not claiming to be the literal Barten
        formula. A full numeric comparison against a verified reimplementation of
        the actual Barten (1999) model (cross-checked against the colour-science
        library's own doctested reference value) is in MODULE10_VALIDATION.md,
        showing normalized-shape correlation r=0.98-0.99 but a real, honestly-
        reported ~1 cpd peak-frequency offset between the two."""
        config = load_default_config()
        freqs = [x * 0.1 for x in range(2, 801)]  # 0.2 to 80.0 cpd
        values = barten_simplified_csf(freqs, 100.0, 20.0, config)
        peak_idx = max(range(len(values)), key=lambda i: values[i])
        peak_freq = freqs[peak_idx]
        self.assertTrue(2.0 <= peak_freq <= 6.0, f"peak {peak_freq} cpd outside commonly-cited 2-6 cpd photopic range")
        above_peak = [(f, v) for f, v in zip(freqs, values) if f > peak_freq]
        below_one = [f for f, v in above_peak if v < 1.0]
        self.assertTrue(below_one, "CSF never drops below sensitivity=1 in the tested range")
        cutoff_freq = below_one[0]
        self.assertTrue(30.0 <= cutoff_freq <= 70.0, f"cutoff {cutoff_freq} cpd outside commonly-cited 30-70 cpd photopic range")

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
