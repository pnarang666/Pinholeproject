"""
New optical metrics computed from Stage 2's retinal PSF: RMS spot radius, Strehl
ratio, MTF (with MTF50/MTF10), Airy diameter, F-number, and throughput.

Imports stage1_v2/stage2 for primitives (make_grid, second_moment_radius,
run_pipeline_point) -- never reimplements the ASM propagator or mask generator, per
the same rule stage2/pipeline_junction.py already follows. Every formula here is keyed
to a literature.py citation.
"""

import os
import sys

import numpy as np

_STAGE1_V2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage1_v2"))
_STAGE2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage2"))
for _d in (_STAGE1_V2_DIR, _STAGE2_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import physics as _v2_physics  # noqa: E402
import phase2_retina as _p2  # noqa: E402
import pipeline_junction as junction  # noqa: E402

import literature

make_grid = _v2_physics.make_grid
second_moment_radius = _v2_physics.second_moment_radius  # literature.get("rms_spot_radius")


def rms_spot_radius(I, dx):
    """literature.get('rms_spot_radius')"""
    N = I.shape[0]
    _, _, R, _ = make_grid(N, N * dx)
    return second_moment_radius(I, R, dx)


def fwhm_radius(I, dx):
    """
    literature.get('fwhm_core_width'). Full-width-half-max radius, promoted here as
    a first-class metric -- previously only computed ad hoc in
    model_comparison/acuity_check.py and stage3_integrated/run_full_theory_sweep.py.
    Reuses stage1_v2/physics.py::radial_profile + locate_threshold_crossing exactly
    as those two call sites already do (no new physics).

    KNOWN LIMITATION, not hidden: in this Fresnel near-field regime, the profile's
    peak/crossing can hop between rings for adjacent aperture values a few um apart
    (see stage3_integrated/README.md "Does Stage 1's cornea-plane FWHM ring-hopping
    also occur at the retina plane?" -- yes, and worse). Returns the full detail
    dict (radius, mode, crossing_count) rather than just a radius, so callers can
    see when a result landed on an unstable ring instead of trusting a lone number.
    """
    r_centers, I_radial = _v2_physics.radial_profile(I, None, dx)
    I_peak = I_radial.max()
    return _v2_physics.locate_threshold_crossing(r_centers, I_radial, 0.5, I_peak=I_peak)


def airy_diameter(a_hole, wavelength, v_r):
    """literature.get('airy_diameter')"""
    return 2 * 1.22 * wavelength * v_r / a_hole


def f_number(a_hole, v_r):
    """literature.get('f_number')"""
    return v_r / a_hole


def throughput_area_ratio(a_hole, D_pupil):
    """literature.get('throughput_area_ratio')"""
    return (a_hole / D_pupil) ** 2


def strehl_ratio(I_actual, I_diffraction_limited):
    """
    literature.get('strehl_ratio'). Both PSFs are normalized to the SAME total power
    before comparing peaks (Strehl compares peak CONCENTRATION, not total energy,
    which the ASM propagator conserves exactly regardless).

    Reference convention used everywhere in this module: I_diffraction_limited is
    THIS SYSTEM's own M=0 (zero-defocus, emmetropic) PSF at the same (a_hole,
    wavelength, d_gap) -- a single, fixed, reproducible definition.

    IMPORTANT, CONFIRMED BY DIRECT NUMERICAL TEST (see README.md "Finding: Strehl
    ratio is ill-posed in this regime"): peak retinal intensity vs. propagation
    distance is NOT single-peaked/monotonic in this system -- it is oscillatory,
    the same near-field Fresnel behavior as Stage 1's own on-axis oscillation formula
    I(0,z) = 4*I0*sin^2(pi*N_F/2). A direct v_r scan at a_hole=750um found a peak of
    1239 (a.u.) at v_r=29mm against only ~76-77 at v_r=23-25mm (where M=4-5D actually
    places the retina) -- meaning M=0 is demonstrably NOT always the true best-focus
    condition. Consequently Strehl computed against the M=0 reference CAN legitimately
    exceed 1.0 for some (a_hole, M) combinations. This is not a code bug; it is a
    property of operating in the Fresnel near-field regime (N_F > ~1), where the
    classical Strehl ratio -- built for mildly-aberrated, near-diffraction-limited
    systems with a single well-defined focus -- is not a well-posed metric. Callers
    (see compute_all_metrics) should check the returned 'strehl_exceeds_unity' flag
    and prefer RMS radius or r_EE(P) (which integrate over structure rather than
    reading a single, possibly-lucky peak) as the more robust metric for this system.
    """
    power_actual = np.sum(I_actual)
    power_dl = np.sum(I_diffraction_limited)
    peak_actual = I_actual.max() / power_actual if power_actual > 0 else 0.0
    peak_dl = I_diffraction_limited.max() / power_dl if power_dl > 0 else 0.0
    return peak_actual / peak_dl if peak_dl > 0 else 0.0


def find_best_focus_v_r(a_hole, wavelength, d_gap, D_pupil_um, f_eye, n_prime,
                         refractive_index_correction, grid_N, window_L_mm,
                         v_r_bounds=(10e-3, 80e-3)):
    """
    Diagnostic utility (NOT used in the main per-point sweep, since it costs ~8x a
    single propagation): numerically finds the v_r that maximizes peak retinal
    intensity for a given aperture, via bounded golden-section search. Used only to
    investigate the "Strehl ratio ill-posedness" finding above -- see README.md and
    comparison.py. Returns (best_v_r, best_peak, hit_boundary: bool).
    """
    from scipy import optimize

    cornea = junction.run_gap_to_cornea(a_hole, wavelength, d_gap, grid_N, window_L_mm)
    dx = cornea["dx"]

    def neg_peak(v_r):
        field = _p2.pupil_clip(cornea["U_cornea"], dx, D_pupil_um)
        field = _p2.lens_phase(field, dx, wavelength, f_eye)
        U, _ = _p2.propagate_to_retina(field, dx, wavelength, v_r, refractive_index_correction, n_prime)
        return -np.abs(U).max() ** 2

    res = optimize.minimize_scalar(neg_peak, bounds=v_r_bounds, method="bounded",
                                    options={"xatol": v_r_bounds[1] * 1e-4})
    hit_boundary = (abs(res.x - v_r_bounds[0]) < 1e-6) or (abs(res.x - v_r_bounds[1]) < 1e-6)
    return res.x, -res.fun, hit_boundary


def mtf_radial(I, dx):
    """
    literature.get('mtf_from_psf'). Returns (freq_cycles_per_um, mtf) -- 1D radially
    averaged MTF from the 2D PSF via FFT. freq is in cycles/um at the retina plane;
    convert to cycles/degree via metrics_cpd() below when comparing to CSF/acuity
    literature (which is always reported in cycles/degree of visual angle).

    NOTE: kept as its own independent implementation (NOT refactored to call
    otf_radial() below and take np.abs()), even though the two share the same FFT
    setup. Averaging |OTF| per radial bin (done here) and taking |average of the
    complex OTF per bin| (what otf_radial does) are not the same operation in general
    -- every previously-computed number in this project's CSVs/README depends on
    THIS function's exact behavior, so it is left unchanged rather than silently
    re-derived from a different averaging order.
    """
    N = I.shape[0]
    otf = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(I)))
    mtf2d = np.abs(otf)
    center = N // 2
    mtf2d = mtf2d / mtf2d[center, center]

    # fftfreq(N, d=dx) with dx in METERS returns cycles/meter -- convert to cycles/um
    # (1 cycle/meter = 1e-6 cycles/um) so the returned axis matches the function's own
    # documented units and downstream cycles_per_um_to_cycles_per_degree() is correct.
    freqs = np.fft.fftshift(np.fft.fftfreq(N, d=dx)) * 1e-6
    FX, FY = np.meshgrid(freqs, freqs, indexing="xy")
    Frad = np.sqrt(FX ** 2 + FY ** 2)

    n_bins = N // 2
    f_max = freqs.max()
    bins = np.linspace(0, f_max, n_bins + 1)
    idx = np.clip(np.digitize(Frad.ravel(), bins) - 1, 0, n_bins - 1)
    sums = np.bincount(idx, weights=mtf2d.ravel(), minlength=n_bins)
    counts = np.bincount(idx, minlength=n_bins)
    counts[counts == 0] = 1
    mtf_1d = sums / counts
    f_centers = 0.5 * (bins[:-1] + bins[1:])
    return f_centers, mtf_1d


def otf_radial(I, dx):
    """
    literature.get('otf_from_psf'). The full COMPLEX radially-averaged OTF -- the
    quantity mtf_radial() above computes internally and then discards (it only ever
    returns |OTF|). Returns (freq_cycles_per_um, otf_complex_1d).

    Same FFT/normalization/frequency-axis setup as mtf_radial(), but bins the
    complex value directly (real and imaginary parts averaged per radial bin,
    then recombined) instead of binning |OTF|. This is an ADDITIVE function --
    mtf_radial() is not changed or rewired to use it (see that function's
    docstring for why).

    Needed for: (1) exposing OTF as its own quantity, distinct from MTF, per the
    project's optics pipeline (Wave Optics -> Image Quality: OTF, MTF, MTF50);
    (2) visual_acuity.visual_strehl_approx()'s VSOTF definition, which weights
    Re(OTF) rather than |OTF| -- see that function's docstring.
    """
    N = I.shape[0]
    otf2d = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(I)))
    center = N // 2
    otf2d = otf2d / otf2d[center, center]

    freqs = np.fft.fftshift(np.fft.fftfreq(N, d=dx)) * 1e-6
    FX, FY = np.meshgrid(freqs, freqs, indexing="xy")
    Frad = np.sqrt(FX ** 2 + FY ** 2)

    n_bins = N // 2
    f_max = freqs.max()
    bins = np.linspace(0, f_max, n_bins + 1)
    idx = np.clip(np.digitize(Frad.ravel(), bins) - 1, 0, n_bins - 1)
    counts = np.bincount(idx, minlength=n_bins)
    counts_safe = np.where(counts == 0, 1, counts)
    real_sums = np.bincount(idx, weights=otf2d.real.ravel(), minlength=n_bins)
    imag_sums = np.bincount(idx, weights=otf2d.imag.ravel(), minlength=n_bins)
    otf_1d = (real_sums + 1j * imag_sums) / counts_safe
    f_centers = 0.5 * (bins[:-1] + bins[1:])
    return f_centers, otf_1d


def ptf_radial(I, dx):
    """
    literature.get('otf_from_psf'). Phase transfer function: angle(OTF), radially
    averaged -- essentially free once otf_radial() exists. In this near-field
    (Fresnel-regime, defocused) system the PTF can show phase reversals ("spurious
    resolution": contrast reappearing inverted past a null) that a magnitude-only
    MTF plot cannot show at all. Returns (freq_cycles_per_um, phase_radians).
    """
    f_centers, otf_1d = otf_radial(I, dx)
    return f_centers, np.angle(otf_1d)


def _interp_crossing(f_centers, mtf_1d, level):
    """Frequency where mtf_1d first drops to `level`, linearly interpolated."""
    below = mtf_1d < level
    if not below.any():
        return f_centers[-1]
    idx = int(np.argmax(below))
    if idx == 0:
        return f_centers[0]
    f0, f1 = f_centers[idx - 1], f_centers[idx]
    m0, m1 = mtf_1d[idx - 1], mtf_1d[idx]
    if m0 == m1:
        return f0
    frac = (m0 - level) / (m0 - m1)
    return f0 + frac * (f1 - f0)


def mtf50_mtf10(I, dx):
    f_centers, mtf_1d = mtf_radial(I, dx)
    return _interp_crossing(f_centers, mtf_1d, 0.5), _interp_crossing(f_centers, mtf_1d, 0.1)


def cycles_per_um_to_cycles_per_degree(f_cpum, v_r):
    """
    Converts a spatial frequency at the retina (cycles/um) to cycles/degree of visual
    angle, via the eye's own posterior nodal distance v_r (small-angle approximation):
    1 degree of visual angle subtends v_r*tan(1 deg) ~= v_r*(pi/180) at the retina.
    """
    um_per_degree = v_r * (np.pi / 180.0) * 1e6
    return f_cpum * um_per_degree


def get_diffraction_limited_reference(a_hole, wavelength, d_gap, D_pupil_um,
                                       P0=60.0, n_prime=1.336, refractive_index_correction=True,
                                       grid_N=2048, window_L_mm=6.0):
    """M=0 (zero-defocus) I_retina for the given aperture -- compute once, pass to
    compute_all_metrics(precomputed_I_dl=...) for every M at that same aperture."""
    ref = _p2.run_pipeline_point(
        a_hole=a_hole, wavelength=wavelength, d_gap=d_gap, grid_N=grid_N, window_L_mm=window_L_mm,
        M_diopters=0.0, P0=P0, n_prime=n_prime, D_pupil_um=D_pupil_um,
        refractive_index_correction=refractive_index_correction,
    )
    return ref["I_retina"]


def compute_all_metrics(a_hole, wavelength, d_gap, M_diopters, D_pupil_um,
                         P0=60.0, n_prime=1.336, refractive_index_correction=True,
                         grid_N=2048, window_L_mm=6.0, precomputed_I_dl=None):
    """
    Runs stage2's exact pipeline at (a_hole, M) to get the actual PSF, and compares
    against a diffraction-limited reference (M=0, same aperture -- zero defocus) for
    the Strehl ratio. Pass `precomputed_I_dl` (the M=0 I_retina array for this exact
    a_hole/wavelength/d_gap/D_pupil) to skip recomputing that reference when sweeping
    several M values at the same aperture -- see run_metrics_sweep.py, which caches it
    per-aperture rather than recomputing it for every M (an ~2x sweep-cost saving).
    Returns a flat dict of all metrics plus a 'junction_check_passed' flag.
    """
    result = _p2.run_pipeline_point(
        a_hole=a_hole, wavelength=wavelength, d_gap=d_gap, grid_N=grid_N, window_L_mm=window_L_mm,
        M_diopters=M_diopters, P0=P0, n_prime=n_prime, D_pupil_um=D_pupil_um,
        refractive_index_correction=refractive_index_correction,
    )
    out = {
        "a_hole_um": a_hole * 1e6, "wavelength_nm": wavelength * 1e9, "z_gap_mm": d_gap * 1e3,
        "M_diopters": M_diopters, "D_pupil_um": D_pupil_um,
        "junction_check_passed": result["junction_check_passed"],
    }
    if not result["junction_check_passed"]:
        return out

    I = result["I_retina"]
    dx = result["cornea_result"]["dx"]
    v_r = result["myopia"]["L_ax"]

    if precomputed_I_dl is not None:
        I_dl = precomputed_I_dl
    else:
        ref = _p2.run_pipeline_point(
            a_hole=a_hole, wavelength=wavelength, d_gap=d_gap, grid_N=grid_N, window_L_mm=window_L_mm,
            M_diopters=0.0, P0=P0, n_prime=n_prime, D_pupil_um=D_pupil_um,
            refractive_index_correction=refractive_index_correction,
        )
        I_dl = ref["I_retina"]

    mtf50_cpum, mtf10_cpum = mtf50_mtf10(I, dx)
    strehl = strehl_ratio(I, I_dl)
    fwhm = fwhm_radius(I, dx)

    out.update({
        "v_r_mm": v_r * 1e3,
        "rms_spot_radius_um": rms_spot_radius(I, dx) * 1e6,
        # See fwhm_radius()'s docstring: FWHM is a known-unstable metric in this
        # near-field regime (ring-hopping) -- mode/crossing_count are carried
        # alongside the radius so that instability is visible, not hidden.
        "fwhm_radius_um": fwhm["radius"] * 1e6,
        "fwhm_mode": fwhm["mode"],
        "fwhm_crossing_count": fwhm["crossing_count"],
        "strehl_ratio": strehl,
        # See strehl_ratio()'s docstring / README.md "Strehl ratio is ill-posed in this
        # regime": M=0 is not always the true best-focus condition in the Fresnel
        # near-field regime, so this CAN legitimately exceed 1.0 -- flagged, not hidden.
        "strehl_exceeds_unity": bool(strehl > 1.0),
        "mtf50_cpd": cycles_per_um_to_cycles_per_degree(mtf50_cpum, v_r),
        "mtf10_cpd": cycles_per_um_to_cycles_per_degree(mtf10_cpum, v_r),
        "airy_diameter_um": airy_diameter(a_hole, wavelength, v_r) * 1e6,
        "f_number": f_number(a_hole, v_r),
        "throughput_area_ratio": throughput_area_ratio(a_hole, D_pupil_um * 1e-6),
        "peak_intensity": float(I.max()),
        "total_power": float(np.sum(I) * dx ** 2),
        "r_EE_50_um": result["retina_EE"]["r_EE_50"] * 1e6,
        "r_EE_80_um": result["retina_EE"]["r_EE_80"] * 1e6,
        "r_EE_90_um": result["retina_EE"]["r_EE_90"] * 1e6,
    })
    return out
