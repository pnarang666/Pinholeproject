"""
Phase 2: cornea -> pupil -> eye lens -> retina.

Only imports stage1_v2 primitives through pipeline_junction, never directly. The lens
focal length is always the emmetropic value from myopia_axial (fixed regardless of M);
only the propagation distance to the retina (v_r = L_ax) changes with myopia, per the
axial-length model in myopia_axial.py.

PHYSICS_AUDIT.md item E1 -- reduced-eye geometry, stated explicitly (a defensible
modeling choice, not a bug -- the problem is a reader otherwise can't tell it was
deliberate): pupil_clip, lens_phase, and the start of the retinal propagation all occur
at ONE plane (cornea_result's plane). A real eye has a physical anterior chamber
(cornea to iris/pupil, ~3.6mm) and the crystalline lens sits behind that, with the
cornea itself contributing roughly 2/3 of the eye's total refractive power and the lens
the rest -- neither of those anatomical distances or the power split is represented
here. This is the standard "reduced eye" schematic simplification (a single lumped
refracting plane of power P0, matching e.g. the Gullstrand-Emsley reduced eye), and it
is what makes P0=60D a meaningful single number in the first place -- but it means every
pupil-plane / lens-plane distance in this module is a modeling convenience, not an
anatomical one.

PHYSICS_AUDIT.md item E4 -- effects deliberately not modeled, listed in one place: (1)
longitudinal chromatic aberration (the eye's refractive power is wavelength-dependent,
~2D of variation across the visible band; this module uses one fixed P0 per run,
independent of the wavelength argument -- running at several wavelengths separately, as
some later stages do, is not the same as modeling dispersion within one field); (2)
higher-order aberrations (lens_phase is a pure quadratic/defocus term -- no astigmatism,
coma, spherical aberration, etc.); (3) Stiles-Crawford apodization (pupil_clip is a
binary hard-edged mask; no directional falloff toward the pupil edge -- a different,
independent Stiles-Crawford term IS applied elsewhere in stage4_human_vision/csf.py's
own retinal-illuminance calculation, but not here, in the core PSF); (4) finite aperture
thickness / vignetting (stage1_v2.circular_aperture is an infinitely-thin binary 0/1
mask -- no membrane-thickness diffraction or oblique-angle vignetting).
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
    plane is evaluated short of the (wrongly shifted) focus. See PHYSICS_AUDIT.md item A
    for the full derivation and why the zero-defocus Airy validation gate, run at exact
    focus, did not surface it (item D)."""
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


def validate_lens_sampling(dx, wavelength, f_eye, D_pupil_um, cornea_result):
    """
    Item C (PHYSICS_AUDIT.md): checks whether the lens's quadratic phase
    exp(-i k r^2/(2 f_eye)) is adequately sampled on the simulation grid, out to the
    pupil radius. No existing check tests this -- junction.validate_junction()'s
    Matsushima band-limit test guards aliasing in the ASM PROPAGATION kernel, not in
    a multiplicative phase screen applied before it, so this is a genuinely separate
    numerical concern.

    Derivation: the lens phase's local spatial frequency grows linearly with radius,
    d(phase)/dr = -k*r/f_eye (k=2*pi/wavelength). Requiring the phase to change by
    less than pi radians between adjacent grid samples (a pixel-to-pixel Nyquist
    criterion for a smoothly-varying phase ramp -- 2 samples per local cycle) gives
    the radius beyond which the sampled lens phase aliases:

        r_max_lens = wavelength * f_eye / (2 * dx)

    `wavelength` here MUST be the same effective wavelength actually used for the
    lens phase (see lens_phase()'s docstring) -- using the vacuum wavelength here
    would understate r_max_lens by a factor of n_prime, the same class of error as
    item A.

    Does NOT gate the pipeline (junction_check_passed is unaffected by this check):
    at this project's own tested range (a_hole=300um and 2000um, grid_N=2048,
    window_L_mm=6.0, D_pupil_um=4000), r_max_lens (~1.56mm) is smaller than the
    pupil radius (2.0mm) at EVERY point in EVERY sweep, since r_max_lens depends
    only on wavelength/f_eye/dx, not on a_hole -- making this a hard gate would
    reject every point, not just the ones where it matters. But the fraction of
    cornea-plane energy actually lying beyond r_max_lens is quantified directly
    (not assumed) to be small there: 0.005% at a=300um, 0.05% at a=2000um (see
    PHYSICS_AUDIT.md item C for the full sweep). Reported as a diagnostic -- not
    silently assumed negligible -- so a future, more extreme configuration (larger
    aperture, larger pupil, or coarser grid) can be checked rather than assumed fine.
    """
    r_max_lens = wavelength * f_eye / (2.0 * dx)
    pupil_radius = (D_pupil_um * 1e-6) / 2.0

    I = np.abs(cornea_result["U_cornea"]) ** 2
    N = I.shape[0]
    L = N * dx
    _, _, R, _ = junction.make_grid(N, L)
    total_power = float(np.sum(I) * dx ** 2)
    power_within_rmax = float(np.sum(I[R <= r_max_lens]) * dx ** 2)
    fraction_energy_beyond_r_max_lens = (
        1.0 - power_within_rmax / total_power if total_power > 0 else 0.0
    )

    ok = r_max_lens >= pupil_radius
    suggested_grid_N = None
    if not ok:
        # r_max_lens = wavelength*f_eye/(2*dx) = wavelength*f_eye*N/(2*L), so at fixed
        # L (window_L_mm), r_max_lens scales linearly with N -- solve for the N that
        # brings r_max_lens up to the pupil radius.
        suggested_grid_N = int(np.ceil(N * pupil_radius / r_max_lens))

    return {
        "name": "Lens-phase Nyquist sampling (gates: no -- informational)",
        "ok": ok,
        "r_max_lens_um": r_max_lens * 1e6,
        "pupil_radius_um": pupil_radius * 1e6,
        "fraction_cornea_energy_beyond_r_max_lens": fraction_energy_beyond_r_max_lens,
        "suggested_grid_N": suggested_grid_N,
        "detail": (
            f"lens phase well-sampled out to r_max_lens={r_max_lens * 1e6:.1f}um; "
            f"pupil radius={pupil_radius * 1e6:.1f}um "
            f"({'within' if ok else 'EXCEEDS'} the well-sampled region); "
            f"{fraction_energy_beyond_r_max_lens * 100:.4f}% of cornea-plane energy "
            f"lies beyond r_max_lens. Informational only -- does not gate the pipeline."
        ),
    }


def energy_escape_estimate(a_hole, cornea_result, I_retina, dx):
    """
    Item E2 (PHYSICS_AUDIT.md): an INTEGRATED energy-escape estimate, complementing
    encircled_energy()'s own normalization (which measures P% of whatever power
    remains captured on the grid, not P% of what was originally emitted -- see that
    function's docstring in stage1_v2/physics.py) and the existing wraparound check
    (peak-relative, not an energy integral -- see pipeline_junction.validate_junction).

    Compares the analytically-known input power at the aperture plane (a uniform
    circular aperture of amplitude 1, so power = pi*(a_hole/2)^2 exactly, no grid
    quadrature needed) against the grid-captured power at the cornea plane (after the
    first ASM propagation) and at the retina plane (after pupil clip + lens + second ASM
    propagation), reporting the escaped fraction at each stage. A large escaped fraction
    already at the cornea stage flags gap-propagation energy loss (band-limit
    suppression or genuine window truncation); a large ADDITIONAL escaped fraction by
    the retina stage flags loss specific to the pupil clip / lens / retina propagation
    -- including the pupil clipping away real energy when a_hole's diffracted spread
    exceeds D_pupil, which is physically correct energy removal, not a numerical
    artifact. This function reports the number either way and leaves the
    interpretation (physical clipping vs. numerical loss) to the caller.
    """
    input_power = float(np.pi * (a_hole / 2.0) ** 2)

    dx_c = cornea_result["dx"]
    I_cornea = np.abs(cornea_result["U_cornea"]) ** 2
    cornea_power = float(np.sum(I_cornea) * dx_c ** 2)

    retina_power = float(np.sum(I_retina) * dx ** 2)

    frac_escaped_at_cornea = (1.0 - cornea_power / input_power) if input_power > 0 else 0.0
    frac_escaped_at_retina = (1.0 - retina_power / input_power) if input_power > 0 else 0.0

    return {
        "input_power_aperture": input_power,
        "captured_power_cornea": cornea_power,
        "captured_power_retina": retina_power,
        "fraction_escaped_by_cornea": frac_escaped_at_cornea,
        "fraction_escaped_by_retina": frac_escaped_at_retina,
        "detail": (
            f"{frac_escaped_at_cornea * 100:.4f}% of the aperture's analytic input "
            f"power is not captured in the cornea-plane grid; "
            f"{frac_escaped_at_retina * 100:.4f}% is not captured in the retina-plane "
            f"grid (cumulative -- includes pupil clipping if a_hole's diffracted "
            f"spread exceeds D_pupil, see docstring)."
        ),
    }


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
    threaded through both lens_phase and propagate_to_retina -- see lens_phase's
    docstring for why the lens phase screen needs the same effective wavelength as the
    retina propagation, not the vacuum one (this was previously not the case -- see
    PHYSICS_AUDIT.md item A). propagate_to_retina is called below with
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
    # Item B (PHYSICS_AUDIT.md): validate_junction's own diagnostic re-propagation to
    # v_r_target must use the SAME wavelength the real retina propagation will actually
    # use (effective_wavelength), not the raw vacuum wavelength -- otherwise its
    # Matsushima band-limit check (f_limit ~ 1/wavelength) and its divergence estimate
    # (~ wavelength/w) are evaluated at the wrong wavelength, over-predicting suppression
    # / divergence at the true (smaller, n_prime-reduced) effective wavelength. This is
    # conservative, not corrupting (it can only make the gate too strict, never too
    # lenient), but it hides real headroom -- see PHYSICS_AUDIT.md item B.
    check = junction.validate_junction(cornea_result, v_r, effective_wavelength)

    result = {
        "cornea_result": cornea_result,
        "myopia": myopia,
        "junction_check_passed": check["ok"],
        "junction_fail_reason": check["reason"],
        "suggested_grid_N": check["suggested_grid_N"],
        "retina_EE": None,
        "retina_band_info": None,
        "I_retina": None,
        "lens_sampling_check": None,
        "energy_escape_estimate": None,
    }
    if not check["ok"]:
        return result

    dx = cornea_result["dx"]
    result["lens_sampling_check"] = validate_lens_sampling(
        dx, effective_wavelength, f_eye, D_pupil_um, cornea_result)
    field = pupil_clip(cornea_result["U_cornea"], dx, D_pupil_um)
    field = lens_phase(field, dx, effective_wavelength, f_eye)
    U_retina, retina_band_info = propagate_to_retina(
        field, dx, effective_wavelength, v_r, refractive_index_correction=False, n_prime=n_prime)
    I_retina = np.abs(U_retina) ** 2

    result["retina_EE"] = retinal_encircled_energy(I_retina, dx)
    result["retina_band_info"] = retina_band_info
    result["I_retina"] = I_retina
    result["energy_escape_estimate"] = energy_escape_estimate(a_hole, cornea_result, I_retina, dx)
    return result
