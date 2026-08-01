"""Visual acuity prediction utilities."""

import math

from .config import load_default_config


def mar_from_cutoff_cpd(cutoff_cpd, config=None):
    config = config or load_default_config()
    cutoff_cpd = max(float(cutoff_cpd), 1e-6)
    return config.acuity.cycles_per_degree_at_20_20 / cutoff_cpd


def logmar_from_mar(mar_arcmin):
    return math.log10(max(mar_arcmin, 1e-6))


def snellen_from_mar(mar_arcmin):
    return 20.0 * mar_arcmin


def brightness_logmar_correction(retinal_illuminance_td, config=None):
    """
    Additive logMAR penalty for retinal illuminance below the Weber-law knee.

    Cited (see stage4_human_vision/literature.py for full verification notes):
    - knee at 300 td: Van Nes & Bouman (1967) -- verified directly against the
      primary abstract. Threshold modulation is illuminance-independent
      (Weber-Fechner) above 300 td, and increases as td^-0.5 (de Vries-Rose)
      below it.
    - slope 0.060 logMAR per log10-unit: Tidbury, Czanner & Newsham (2016) --
      verified directly against full text (their Table 3, p<0.001). Cross-
      checked against Sheedy, Bailey & Raasch (1984)'s independently-derived
      ~0.0664 (see literature.py; that one could not be verified past a
      secondary summary, so Tidbury's directly-verified value is what's wired
      in here).

    Zero at or above the knee: Rabin (1994) found VA far more resistant to
    reduced luminance than contrast sensitivity is in the photopic range
    (116->0.23 cd/m^2 gave 3x VA loss vs 17x contrast-sensitivity loss) --
    consistent with a near-plateau for VA specifically above some knee, though
    the exact knee value used here comes from Van Nes & Bouman, not Rabin,
    since that citation is natively in trolands and was verified directly.
    """
    config = config or load_default_config()
    knee_td = config.brightness_acuity.weber_knee_td
    slope = config.brightness_acuity.logmar_per_log10_illuminance
    td = max(retinal_illuminance_td, 1e-6)
    if td >= knee_td:
        return 0.0
    return slope * math.log10(knee_td / td)


def predict_acuity(mtf10_cpd, mtf50_cpd, vsotf=None, snr=None,
                    retinal_illuminance_td=None, config=None):
    config = config or load_default_config()
    mar10 = mar_from_cutoff_cpd(mtf10_cpd, config)
    mar50 = mar_from_cutoff_cpd(mtf50_cpd, config)

    vsotf_adjusted_mar = mar10
    if vsotf is not None and vsotf > 0:
        vsotf_adjusted_mar = mar10 / max(min(vsotf, 2.0), 0.25) ** 0.1

    # Recommended: VSOTF adjustment (unchanged) + cited additive brightness
    # correction in the log domain, in place of the old uncited SNR**0.05 term.
    # See CHANGES.md for why this replaced the old term.
    recommended_logmar = logmar_from_mar(vsotf_adjusted_mar)
    if retinal_illuminance_td is not None:
        recommended_logmar += brightness_logmar_correction(retinal_illuminance_td, config)
    recommended_mar = 10.0 ** recommended_logmar

    # Legacy: the ORIGINAL uncited SNR**0.05 exponent term, kept unchanged and
    # available for direct comparison rather than silently replaced (DESIGN.md's
    # own "keep alternative models for comparison" pattern).
    legacy_mar = vsotf_adjusted_mar
    if snr is not None and snr > 0:
        legacy_mar = legacy_mar / max(min(math.sqrt(snr) / 10.0, 2.0), 0.5) ** 0.05

    interval = sorted([mar10, mar50, recommended_mar])
    return {
        "recommended_model": "mtf10_vsotf_brightness_adjusted",
        "mar_arcmin": recommended_mar,
        "logmar": recommended_logmar,
        "snellen_denominator": snellen_from_mar(recommended_mar),
        "models": {
            "mtf10": {
                "mar_arcmin": mar10,
                "logmar": logmar_from_mar(mar10),
                "snellen_denominator": snellen_from_mar(mar10)
            },
            "mtf50": {
                "mar_arcmin": mar50,
                "logmar": logmar_from_mar(mar50),
                "snellen_denominator": snellen_from_mar(mar50)
            },
            "vsotf_snr_legacy": {
                "mar_arcmin": legacy_mar,
                "logmar": logmar_from_mar(legacy_mar),
                "snellen_denominator": snellen_from_mar(legacy_mar)
            }
        },
        "approximate_ci_95_mar_arcmin": [interval[0], interval[-1]]
    }
