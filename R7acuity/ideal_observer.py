"""
Core ideal-observer pipeline: real optical PSF -> neural (NTF) filtering ->
additive Gaussian noise -> template cross-correlation -> single-trial decision.

Reuses stage2_fixed/phase2_retina.py directly for the real, validated retinal PSF
(literature.get('watson_ahumada_2008_wfa_metric')'s own OTF-generation step,
substituted with this project's ACTUAL simulated optics rather than a Zernike-
synthesized one) and this folder's own ntf.py for the neural transfer function.
Does NOT import, call, or duplicate logic from stage4_human_vision/acuity.py.
"""
import functools
import os
import sys

import numpy as np

_STAGE2_FIXED_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage2_fixed"))
if _STAGE2_FIXED_DIR not in sys.path:
    sys.path.insert(0, _STAGE2_FIXED_DIR)
import phase2_retina  # noqa: E402

from .ntf import compute_ntf
from .optotype import render_all_orientations, ORIENTATIONS

DEFAULT_GRID_N = 2048
DEFAULT_WINDOW_L_MM = 6.0


@functools.lru_cache(maxsize=128)
def get_real_psf(a_hole_um, wavelength_nm, M_diopters, d_gap_mm,
                  grid_N=DEFAULT_GRID_N, window_L_mm=DEFAULT_WINDOW_L_MM,
                  P0=60.0, n_prime=1.336, D_pupil_um=4000.0, refractive_index_correction=True):
    """This is where this project's real, validated optics enters the model
    (stage2_fixed/phase2_retina.py's run_pipeline_point, unchanged, imported
    directly -- not reimplemented). Returns (I_retina, dx_m, v_r_m).

    Memoized: the PSF depends only on the optical condition (aperture,
    wavelength, defocus, gap, grid/window/pupil settings), never on letter
    size (mar_arcmin) -- but callers (threshold.py's mar-value sweep and
    calibrate_noise_sigma's sigma bisection) invoke this repeatedly for the
    SAME optical condition across many mar values and sigma guesses. Each
    call is an expensive full wave-optics propagation (~4.6s measured), so
    caching is a pure performance fix (deterministic function, identical
    return value) -- it changes no result, only avoids redundant recomputation."""
    result = phase2_retina.run_pipeline_point(
        a_hole=a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9, d_gap=d_gap_mm * 1e-3,
        grid_N=grid_N, window_L_mm=window_L_mm, M_diopters=M_diopters, P0=P0,
        n_prime=n_prime, D_pupil_um=D_pupil_um,
        refractive_index_correction=refractive_index_correction,
    )
    if not result["junction_check_passed"]:
        raise ValueError(f"junction check failed: {result['junction_fail_reason']}")
    return result["I_retina"], result["cornea_result"]["dx"], result["myopia"]["L_ax"]


def _radial_freq_grid_cpd(grid_N, arcmin_per_pixel):
    freqs_per_pixel = np.fft.fftfreq(grid_N)
    fx, fy = np.meshgrid(freqs_per_pixel, freqs_per_pixel)
    pixels_per_degree = 60.0 / arcmin_per_pixel
    return np.sqrt(fx ** 2 + fy ** 2) * pixels_per_degree


@functools.lru_cache(maxsize=128)
def _compute_ttf_cached(a_hole_um, wavelength_nm, M_diopters, d_gap_mm,
                         scene_luminance_cdm2, field_diameter_deg,
                         grid_N, window_L_mm, optics_kwargs_frozen):
    """
    Phase A (cacheable): everything the neural image depends on that is NOT
    a function of letter size (mar_arcmin) -- the real PSF, the derived pixel
    scale, and the combined optical+neural transfer function ttf = OTF*NTF.
    threshold.py's mar-value sweep and calibrate_noise_sigma's sigma bisection
    call compute_neural_images repeatedly for the SAME optical condition across
    many mar values and sigma guesses, and this Phase A/B split (the same
    memoization principle as get_real_psf above) avoids redoing the ~2048x2048
    FFTs and CSF/NTF evaluation on every one of those calls -- a pure
    performance fix, identical output, since ttf never depends on mar_arcmin.
    """
    optics_kwargs = dict(optics_kwargs_frozen)
    I_retina, dx_m, v_r_m = get_real_psf(
        a_hole_um, wavelength_nm, M_diopters, d_gap_mm, grid_N, window_L_mm, **optics_kwargs)
    psf = I_retina / I_retina.sum()

    arcmin_per_pixel = (dx_m / v_r_m) * (180.0 / np.pi) * 60.0

    freq_grid_cpd = _radial_freq_grid_cpd(grid_N, arcmin_per_pixel)
    a_hole_m = a_hole_um * 1e-6
    wavelength_m = wavelength_nm * 1e-9
    ntf = compute_ntf(freq_grid_cpd, scene_luminance_cdm2, field_diameter_deg,
                       a_hole_m, wavelength_m, v_r_m)

    # PSF is centered in array-index space (peak at grid center, this project's
    # standard convention -- see e.g. stage_v1_simulator's own PSF display code).
    # ifftshift moves it to the FFT's expected "kernel at the origin" position
    # before transforming, so the convolution result stays centered on the
    # letter's own (unshifted) position rather than wrapping to a corner.
    otf_real = np.fft.fft2(np.fft.ifftshift(psf))
    ttf = otf_real * ntf
    return psf, arcmin_per_pixel, dx_m, v_r_m, ttf


def compute_neural_images(a_hole_um, wavelength_nm, M_diopters, d_gap_mm, mar_arcmin,
                           scene_luminance_cdm2, field_diameter_deg,
                           grid_N=DEFAULT_GRID_N, window_L_mm=DEFAULT_WINDOW_L_MM,
                           **optics_kwargs):
    """
    Builds the 4 orientations' neurally-filtered "signal" images S_k and their
    clean, unit-norm templates, per literature.get('watson_ahumada_2008_wfa_metric')
    Section 8.a-d, with T_k = clean unblurred O_k (literature.get(
    'leroux_2024_real_observer')'s "real observer", not the patent's own default
    T_k=S_k), per the task brief.

    Returns dict: S (per-orientation neurally-filtered image), templates
    (per-orientation clean unit-norm template), arcmin_per_pixel, dx_m, v_r_m, psf.
    """
    optics_kwargs_frozen = tuple(sorted(optics_kwargs.items()))
    psf, arcmin_per_pixel, dx_m, v_r_m, ttf = _compute_ttf_cached(
        a_hole_um, wavelength_nm, M_diopters, d_gap_mm,
        scene_luminance_cdm2, field_diameter_deg, grid_N, window_L_mm, optics_kwargs_frozen)

    letters = render_all_orientations(mar_arcmin, arcmin_per_pixel, grid_N)

    S, templates = {}, {}
    for o in ORIENTATIONS:
        O_k = letters[o]
        S[o] = np.real(np.fft.ifft2(np.fft.fft2(O_k) * ttf))
        norm = float(np.sqrt(np.sum(O_k ** 2)))
        templates[o] = O_k / norm if norm > 0 else O_k

    # Crop to a small window around the letter before returning. The letter (plus
    # its optical/neural blur spread) occupies a small fraction of the full
    # grid_N x grid_N simulation grid needed for correct FFT-based convolution --
    # the rest is empty background that contributes nothing to the
    # cross-correlation decision but costs real time to generate noise over and
    # sum across on every Monte Carlo trial (measured: ~110ms/trial for a full
    # 2048x2048 Gaussian draw vs <1ms for a small crop -- this is what made the
    # reference-condition calibration run for 50+ minutes before this fix).
    # Margin is generous (letter size x6, floor 96px) to safely contain PSF blur
    # spread; run_trial's result is unaffected since cropped-out pixels are ~0 in
    # both S and templates and contribute ~0 to every cross-correlation anyway.
    letter_size_px = (5.0 * mar_arcmin) / arcmin_per_pixel
    crop = int(np.clip(letter_size_px * 6.0, 96, grid_N))
    center = grid_N // 2
    lo, hi = max(center - crop // 2, 0), min(center + crop // 2, grid_N)
    S = {o: img[lo:hi, lo:hi] for o, img in S.items()}
    templates = {o: img[lo:hi, lo:hi] for o, img in templates.items()}

    return {"S": S, "templates": templates, "arcmin_per_pixel": arcmin_per_pixel,
            "dx_m": dx_m, "v_r_m": v_r_m, "psf": psf, "crop_px": hi - lo}


def run_trial(neural_images, true_orientation, sigma, rng):
    """
    Single Monte Carlo trial: additive zero-mean Gaussian noise (sigma) on the
    true orientation's neurally-filtered image, then nearest-template decision
    via maximum cross-correlation against the 4 CLEAN templates. Returns
    (decided_orientation, correct: bool).
    """
    S = neural_images["S"]
    templates = neural_images["templates"]
    true_signal = S[true_orientation]
    stimulus = true_signal + rng.normal(0.0, sigma, size=true_signal.shape)
    correlations = {o: float(np.sum(stimulus * templates[o])) for o in ORIENTATIONS}
    decided = max(correlations, key=correlations.get)
    return decided, decided == true_orientation
