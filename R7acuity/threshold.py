"""
Monte Carlo threshold-finding: proportion-correct vs letter size, psychometric
function fit, threshold extraction, MAR/logMAR/Snellen conversion, and the noise-
sigma reference-condition calibration (done ONCE, BEFORE any clinical validation,
per the task brief -- see calibrate_noise_sigma()'s own docstring).

Also computes two closed-form approximations (given by the task brief; see
literature.get('closed_form_approximations_unverified_coefficients') for the
honest fidelity note on their coefficients) as an internal cross-check, reusing
this project's already-validated Strehl/VSOTF machinery (stage3_human_vision/
metrics.py, stage4_human_vision/optical_quality.py, csf.py, visual_strehl.py --
NOT acuity.py).
"""
import math
import os
import sys

import numpy as np
from scipy.optimize import curve_fit

from .ideal_observer import compute_neural_images, run_trial, get_real_psf, DEFAULT_GRID_N, DEFAULT_WINDOW_L_MM
from .optotype import ORIENTATIONS

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_STAGE3HV_DIR = os.path.join(_ROOT, "stage3_human_vision")
for _d in (_ROOT, _STAGE3HV_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)
import metrics as stage3_metrics  # noqa: E402
from stage4_human_vision.optical_quality import compute_optical_quality  # noqa: E402
from stage4_human_vision.csf import evaluate_csf_models  # noqa: E402
from stage4_human_vision.visual_strehl import compute_vsotf  # noqa: E402
from stage4_human_vision.config import load_default_config  # noqa: E402

CHANCE = 0.25  # 4-alternative forced choice (4 tumbling-E orientations)
CRITERION = 0.625  # halfway between chance (0.25) and ceiling (1.0), per the task brief

# ---------------------------------------------------------------------------
# MAR / logMAR / Snellen conversion -- derived explicitly, not imported from
# stage4_human_vision/acuity.py or stage3_human_vision/visual_acuity.py, per the
# task brief's instruction to "derive the angular-size-to-MAR conversion
# correctly and explicitly, show the derivation."
# ---------------------------------------------------------------------------
#
# This model's threshold-finding procedure directly outputs a threshold optotype
# SIZE, parametrized as MAR (minimum angle of resolution) in arcmin -- literature.
# get('watson_ahumada_2008_wfa_metric')'s own convention: MAR is the STROKE WIDTH
# of a standard 5x5-unit optotype (overall letter height/width = 5*MAR). This is
# already exactly the clinical MAR definition (e.g. a 20/20 Snellen letter's
# critical stroke detail subtends 1 arcmin, with the whole letter subtending 5
# arcmin) -- so no cutoff-frequency-based conversion (e.g. "MAR=30/f_cutoff",
# used elsewhere in this project for MTF-cutoff-based predictors) is needed or
# appropriate here: this model's threshold size IS the MAR directly.
#
#   logMAR = log10(MAR_arcmin)                          (standard identity)
#   decimal Snellen fraction = 1/MAR_arcmin              (by definition of MAR)
#   Snellen denominator (20/X notation) = 20 * MAR_arcmin
#     (a MAR-arcmin observer resolves at MAR_arcmin times the reference distance
#     of a 1-arcmin/20-20 observer, so if a normal eye needs "20 feet" to resolve
#     the reference detail, this eye needs "20*MAR_arcmin feet" for the same,
#     i.e. sees at 20 feet what a normal eye sees at 20*MAR_arcmin feet: 20/(20*MAR))


def mar_to_logmar(mar_arcmin):
    return math.log10(max(mar_arcmin, 1e-6))


def mar_to_snellen_denominator(mar_arcmin):
    return 20.0 * mar_arcmin


# ---------------------------------------------------------------------------
# Psychometric function fit
# ---------------------------------------------------------------------------

def _psychometric(log_mar, threshold_log_mar, slope):
    """Logistic between chance (0.25) and ceiling (1.0). At log_mar=threshold_log_mar
    this evaluates to exactly (0.25+1.0)/2 = 0.625 = CRITERION -- so the fitted
    threshold_log_mar parameter directly IS the threshold at the required
    criterion, no separate root-finding needed."""
    return CHANCE + (1.0 - CHANCE) / (1.0 + np.exp(-slope * (log_mar - threshold_log_mar)))


def fit_psychometric_threshold(mar_values_arcmin, proportion_correct):
    log_mar = np.log10(mar_values_arcmin)
    p0 = [np.median(log_mar), 2.0]
    bounds = ([log_mar.min() - 1.0, 1e-3], [log_mar.max() + 1.0, 50.0])
    popt, _ = curve_fit(_psychometric, log_mar, proportion_correct, p0=p0, bounds=bounds, maxfev=5000)
    threshold_log_mar, slope = popt
    return 10.0 ** threshold_log_mar, slope


# ---------------------------------------------------------------------------
# Monte Carlo proportion-correct + threshold sweep
# ---------------------------------------------------------------------------

def proportion_correct_at_size(condition, mar_arcmin, sigma, n_trials, rng):
    neural_images = compute_neural_images(mar_arcmin=mar_arcmin, **condition)
    correct = 0
    for _ in range(n_trials):
        true_o = ORIENTATIONS[rng.integers(4)]
        _, is_correct = run_trial(neural_images, true_o, sigma, rng)
        correct += is_correct
    return correct / n_trials


def find_threshold_mar(condition, sigma, mar_values_arcmin, n_trials=300, rng=None):
    """Sweeps mar_values_arcmin (should span below and above the expected
    threshold), runs n_trials Monte Carlo trials at each, fits the psychometric
    function, returns (threshold_mar_arcmin, slope, raw_proportions)."""
    rng = rng or np.random.default_rng()
    mar_values_arcmin = np.asarray(mar_values_arcmin, dtype=float)
    proportions = np.array([
        proportion_correct_at_size(condition, mar, sigma, n_trials, rng)
        for mar in mar_values_arcmin
    ])
    threshold_mar, slope = fit_psychometric_threshold(mar_values_arcmin, proportions)
    return threshold_mar, slope, proportions


# ---------------------------------------------------------------------------
# Noise-sigma calibration against the reference condition. THIS MUST HAPPEN
# ONCE, BEFORE any Wang 2009 validation, and never be re-tuned afterward -- see
# RESULTS.md and CHANGES-equivalent discussion in README.md.
# ---------------------------------------------------------------------------

REFERENCE_CONDITION = dict(
    a_hole_um=3000.0,  # 3mm aperture standing in for a 3mm natural pupil: at
                       # M_diopters=0 (emmetropic) this project's optics model has
                       # no other aberration source, so this genuinely gives a
                       # diffraction-limited 3mm-pupil PSF via the SAME validated
                       # optics used for every other condition (not a separately
                       # fabricated Airy-disk formula).
    wavelength_nm=550.0,
    M_diopters=0.0,
    d_gap_mm=12.0,
    scene_luminance_cdm2=10000.0,
    field_diameter_deg=20.0,
)
REFERENCE_TARGET_MAR_ARCMIN = 1.0  # 20/20


def calibrate_noise_sigma(n_trials=300, size_range_arcmin=None, rng=None, verbose=True):
    """
    Bisects noise sigma so the reference condition's (diffraction-limited,
    emmetropic, 3mm aperture) Monte Carlo threshold is approximately 1 arcmin MAR
    (20/20). Must be run ONCE, before any clinical validation -- calibrating
    against Wang 2009 or any other clinical dataset instead would repeat the
    exact overfitting error stage4_human_vision/RESULTS.md's leave-one-out
    discussion already caught and avoided.

    Returns (sigma, achieved_threshold_mar, iterations_log).
    """
    rng = rng or np.random.default_rng(12345)
    size_range_arcmin = size_range_arcmin or np.logspace(-0.6, 0.6, 9)  # ~0.25 to ~4 arcmin

    def threshold_for_sigma(sigma):
        threshold_mar, _, _ = find_threshold_mar(
            REFERENCE_CONDITION, sigma, size_range_arcmin, n_trials=n_trials, rng=rng)
        return threshold_mar

    # Exploratory bracket: threshold increases monotonically with sigma (more
    # noise -> harder task -> need a bigger letter to hit the same criterion).
    lo, hi = 1e-4, 1.0
    t_lo, t_hi = threshold_for_sigma(lo), threshold_for_sigma(hi)
    log = [(lo, t_lo), (hi, t_hi)]
    if verbose:
        print(f"bracket search: sigma={lo:.6f} -> threshold={t_lo:.4f} arcmin")
        print(f"bracket search: sigma={hi:.6f} -> threshold={t_hi:.4f} arcmin")
    assert t_lo < REFERENCE_TARGET_MAR_ARCMIN < t_hi, (
        f"target {REFERENCE_TARGET_MAR_ARCMIN} not bracketed by [{t_lo}, {t_hi}] "
        f"at sigma in [{lo}, {hi}] -- widen the search bracket")

    for _ in range(12):
        mid = math.sqrt(lo * hi)  # bisect in log-space, since sigma spans orders of magnitude
        t_mid = threshold_for_sigma(mid)
        log.append((mid, t_mid))
        if verbose:
            print(f"bisect: sigma={mid:.6f} -> threshold={t_mid:.4f} arcmin")
        if t_mid < REFERENCE_TARGET_MAR_ARCMIN:
            lo = mid
        else:
            hi = mid
    sigma_final = math.sqrt(lo * hi)
    threshold_final = threshold_for_sigma(sigma_final)
    if verbose:
        print(f"CALIBRATED sigma={sigma_final:.6f} -> reference threshold={threshold_final:.4f} arcmin "
              f"(target {REFERENCE_TARGET_MAR_ARCMIN})")
    return sigma_final, threshold_final, log


# ---------------------------------------------------------------------------
# Closed-form approximations (internal cross-check only) -- see
# literature.get('closed_form_approximations_unverified_coefficients').
# ---------------------------------------------------------------------------

def closed_form_approximations(a_hole_um, wavelength_nm, M_diopters, d_gap_mm,
                                D_pupil_um, scene_luminance_cdm2, field_diameter_deg,
                                grid_N=DEFAULT_GRID_N, window_L_mm=DEFAULT_WINDOW_L_MM,
                                P0=60.0, n_prime=1.336, refractive_index_correction=True):
    """logMAR ~= 25*log10(M) [M = Strehl ratio] and logMAR ~= (50/3)*log10(VSOTF),
    both as specified in the task brief. Reuses this project's own already-
    validated Strehl and VSOTF machinery (stage3_human_vision/metrics.py,
    stage4_human_vision/optical_quality.py, csf.py, visual_strehl.py) -- NOT
    stage4_human_vision/acuity.py."""
    config = load_default_config()
    I_retina, dx_m, v_r_m = get_real_psf(
        a_hole_um, wavelength_nm, M_diopters, d_gap_mm, grid_N, window_L_mm,
        P0=P0, n_prime=n_prime, D_pupil_um=D_pupil_um,
        refractive_index_correction=refractive_index_correction)

    a_hole_m = a_hole_um * 1e-6
    wavelength_m = wavelength_nm * 1e-9
    d_gap_m = d_gap_mm * 1e-3
    I_dl = stage3_metrics.get_diffraction_limited_reference(
        a_hole=a_hole_m, wavelength=wavelength_m, d_gap=d_gap_m, D_pupil_um=D_pupil_um,
        P0=P0, n_prime=n_prime, refractive_index_correction=refractive_index_correction,
        grid_N=grid_N, window_L_mm=window_L_mm)

    M_strehl = stage3_metrics.strehl_ratio(I_retina, I_dl)

    optical = compute_optical_quality(I_retina, dx_m, v_r_m, diffraction_reference_psf=I_dl)
    optical_dl = compute_optical_quality(I_dl, dx_m, v_r_m)
    csf_summary = evaluate_csf_models(optical["mtf_frequency_cpd"], scene_luminance_cdm2, field_diameter_deg, config)
    neural_weights = csf_summary[config.csf.default_model]["values"]
    vsotf = compute_vsotf(
        freq_cpd=optical["mtf_frequency_cpd"], otf_real=optical["otf_real"],
        ref_freq_cpd=optical["mtf_frequency_cpd"], ref_otf_real=optical_dl["otf_real"],
        neural_weights=neural_weights)["vsotf"]

    logmar_strehl = 25.0 * math.log10(max(M_strehl, 1e-6))
    logmar_vsotf = (50.0 / 3.0) * math.log10(max(abs(vsotf), 1e-6))
    return {
        "strehl_ratio": M_strehl, "vsotf": vsotf,
        "logmar_from_strehl": logmar_strehl, "logmar_from_vsotf": logmar_vsotf,
    }
