"""
Validation against the same Wang (2009) 'Ideal Pinhole' dataset used elsewhere in
this project, with the same leave-one-out cross-validation procedure established
as the correct method for a sample this small (stage4_human_vision/RESULTS.md
Section 4c). Reuses stage4_human_vision/validation.py's regression_stats()
directly -- does not reimplement it.
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_STAGE3HV_DIR = os.path.join(_ROOT, "stage3_human_vision")
for _d in (_ROOT, _STAGE3HV_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from stage4_human_vision.validation import regression_stats  # noqa: E402
import literature as stage3_literature  # noqa: E402

from .threshold import find_threshold_mar, mar_to_logmar, closed_form_approximations, REFERENCE_CONDITION  # noqa: E402


def wang_2009_dataset():
    """literature.get('ideal_pinhole_wang_2009') from stage3_human_vision/
    literature.py -- imported directly, never copied, same discipline used
    throughout this project (stage4_human_vision/literature.py does the same)."""
    data = stage3_literature.get("ideal_pinhole_wang_2009")["data"]
    return data["aperture_um"], data["logmar"]


def predict_logmar_r7(a_hole_um, sigma, mar_search_range_arcmin, n_trials=300,
                       M_diopters=0.0, wavelength_nm=550.0, d_gap_mm=12.0,
                       D_pupil_um=4000.0, scene_luminance_cdm2=None, field_diameter_deg=None,
                       grid_N=None, window_L_mm=None, rng=None):
    """One Monte Carlo threshold prediction for one (aperture, M) condition."""
    scene_luminance_cdm2 = scene_luminance_cdm2 or REFERENCE_CONDITION["scene_luminance_cdm2"]
    field_diameter_deg = field_diameter_deg or REFERENCE_CONDITION["field_diameter_deg"]
    from .ideal_observer import DEFAULT_GRID_N, DEFAULT_WINDOW_L_MM
    grid_N = grid_N or DEFAULT_GRID_N
    window_L_mm = window_L_mm or DEFAULT_WINDOW_L_MM

    condition = dict(
        a_hole_um=a_hole_um, wavelength_nm=wavelength_nm, M_diopters=M_diopters,
        d_gap_mm=d_gap_mm, scene_luminance_cdm2=scene_luminance_cdm2,
        field_diameter_deg=field_diameter_deg, grid_N=grid_N, window_L_mm=window_L_mm,
        D_pupil_um=D_pupil_um,
    )
    threshold_mar, slope, proportions = find_threshold_mar(
        condition, sigma, mar_search_range_arcmin, n_trials=n_trials, rng=rng)
    return mar_to_logmar(threshold_mar), threshold_mar, slope


def in_sample_equals_leave_one_out_here():
    """
    IMPORTANT, stated explicitly rather than silently assumed: for R7acuity,
    in-sample and leave-one-out regression stats are the SAME NUMBERS, and this
    is not a shortcut -- it is a structural consequence of what this model is.

    stage4_human_vision's calibration.py fit a linear correction (a,b) TO the
    Wang 2009 data itself, which is exactly why in-sample stats there were
    optimistic (overfit) and leave-one-out was needed to get an honest number
    (stage4_human_vision/RESULTS.md Section 4c).

    R7acuity's noise sigma is locked via calibrate_noise_sigma() against an
    INDEPENDENT reference condition (diffraction-limited, 3mm pupil, 20/20)
    BEFORE this validation ever runs, and nothing else in the model is fit to
    Wang 2009 at all -- each aperture's predicted threshold depends only on that
    aperture's own simulated optics, never on any OTHER aperture's observed
    clinical value. So holding out any one point and refitting changes nothing
    (there is no fit to change), and the leave-one-out predictions are
    identically equal to the in-sample predictions, point for point.

    run_validation.py reports both labels explicitly (rather than only one) so
    this equality is visible and demonstrated, not asserted -- see RESULTS.md.
    """
    return True
