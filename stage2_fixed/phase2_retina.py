"""
Phase 2: cornea -> pupil -> eye lens -> retina.

Only imports stage1_v2 primitives through pipeline_junction, never directly. The lens
focal length is always the emmetropic value from myopia_axial (fixed regardless of M);
only the propagation distance to the retina (v_r = L_ax) changes with myopia, per the
axial-length model in myopia_axial.py.
"""

import numpy as np

import myopia_axial
import pipeline_junction as junction


def pupil_clip(field, dx, D_pupil_um):
    """Binary circular clip at the pupil plane, diameter D_pupil_um, centered on axis."""
    N = field.shape[0]
    L = N * dx
    _, _, R, _ = junction.make_grid(N, L)
    mask = R <= (D_pupil_um * 1e-6) / 2.0
    return field * mask


def lens_phase(field, dx, wavelength, f_eye):
    """Thin-lens phase transmittance exp(-i k (x^2+y^2) / (2 f_eye)) -- converging lens,
    consistent with the ASM propagator's +i k z forward-propagation sign convention.

    `wavelength` here MUST be the image-space effective wavelength (wavelength/n_prime
    when refractive_index_correction is honored -- identical to what propagate_to_retina
    below is given), never the raw vacuum wavelength. f_eye = n_prime/P0 (myopia_axial.py)
    is already a vergence-equation distance measured through the vitreous -- i.e. it
    implicitly assumes the lens phase is applied at the vitreous's own wavenumber
    k' = 2*pi*n_prime/lambda_vacuum. Pairing that f_eye with the vacuum k instead
    under-applies the lens's converging phase by a factor of n_prime, which shifts the
    wave's true geometric focus to f_eye*n_prime instead of f_eye -- while
    propagate_to_retina still only propagates to f_eye at zero defocus, so the retina
    plane is evaluated short of the (wrongly shifted) focus. See LENS_WAVELENGTH_FIX.md
    for the full derivation and why the zero-defocus Airy validation gate, run at a
    small aperture where diffraction spread dominates over this defocus blur, did not
    surface it."""
    N = field.shape[0]
    L = N * dx
    X, Y, _, _ = junction.make_grid(N, L)
    k = 2 * np.pi / wavelength
    phase = np.exp(-1j * k * (X ** 2 + Y ** 2) / (2.0 * f_eye))
    return field * phase


def propagate_to_retina(field, dx, wavelength, v_r, refractive_index_correction, n_prime):
    """
    Calls the same ASM function stage1_v2 uses for the gap stage (via pipeline_junction),
    z=v_r -- not a bare FFT shortcut. Returns (U_retina, band_info), mirroring
    junction.asm_propagate's own (field, band_info) return shape.

    If refractive_index_correction: propagates at wavelength/n_prime, the vitreous's own
    reduced wavelength (REFRACTIVE_INDEX_CORRECTION convention in myopia_axial.py).
    """
    N = field.shape[0]
    L = N * dx
    effective_wavelength = (wavelength / n_prime) if refractive_index_correction else wavelength
    U_retina, band_info = junction.asm_propagate(field, dx, effective_wavelength, v_r, L=L, band_limit=True)
    return U_retina, band_info


def retinal_encircled_energy(I_retina, dx):
    N = I_retina.shape[0]
    L = N * dx
    _, _, R, _ = junction.make_grid(N, L)
    r_edges, EE, total_power = junction.encircled_energy(I_retina, R, dx)
    return {
        "r_EE_50": junction.r_for_EE(r_edges, EE, 0.50),
        "r_EE_80": junction.r_for_EE(r_edges, EE, 0.80),
        "r_EE_90": junction.r_for_EE(r_edges, EE, 0.90),
    }


def run_pipeline_point(a_hole, wavelength, d_gap, grid_N, window_L_mm, M_diopters,
                        P0, n_prime, D_pupil_um, refractive_index_correction):
    """
    Full chain: junction.run_gap_to_cornea -> junction.validate_junction -> [if ok] ->
    pupil_clip -> lens_phase -> propagate_to_retina -> |U|^2 -> retinal_encircled_energy.

    Never drops a failing point silently: junction_check_passed=False rows carry
    junction_fail_reason and retina_EE=None for the caller (the sweep) to log as-is.

    The image-space effective wavelength (wavelength/n_prime when
    refractive_index_correction, else wavelength unchanged) is resolved ONCE here and
    threaded through BOTH lens_phase and propagate_to_retina -- see lens_phase's
    docstring for why the lens phase screen needs the same effective wavelength as the
    retina propagation, not the vacuum one (this was previously not the case -- see
    LENS_WAVELENGTH_FIX.md). propagate_to_retina is called below with
    refractive_index_correction=False because the correction has already been applied
    to the wavelength it receives; this keeps propagate_to_retina's own (unchanged)
    ternary a documented no-op from this call site rather than re-deriving the same
    correction a second time from raw inputs -- one evaluation, not two that could
    silently drift apart.
    """
    myopia = myopia_axial.axial_length_for_myopia(M_diopters, P0=P0, n_prime=n_prime)
    v_r = myopia["L_ax"]
    f_eye = myopia["f_eye"]
    effective_wavelength = (wavelength / n_prime) if refractive_index_correction else wavelength

    cornea_result = junction.run_gap_to_cornea(a_hole, wavelength, d_gap, grid_N, window_L_mm)
    check = junction.validate_junction(cornea_result, v_r, wavelength)

    result = {
        "cornea_result": cornea_result,
        "myopia": myopia,
        "junction_check_passed": check["ok"],
        "junction_fail_reason": check["reason"],
        "suggested_grid_N": check["suggested_grid_N"],
        "retina_EE": None,
        "retina_band_info": None,
        "I_retina": None,
    }
    if not check["ok"]:
        return result

    dx = cornea_result["dx"]
    field = pupil_clip(cornea_result["U_cornea"], dx, D_pupil_um)
    field = lens_phase(field, dx, effective_wavelength, f_eye)
    U_retina, retina_band_info = propagate_to_retina(
        field, dx, effective_wavelength, v_r, refractive_index_correction=False, n_prime=n_prime)
    I_retina = np.abs(U_retina) ** 2

    result["retina_EE"] = retinal_encircled_energy(I_retina, dx)
    result["retina_band_info"] = retina_band_info
    result["I_retina"] = I_retina
    return result
