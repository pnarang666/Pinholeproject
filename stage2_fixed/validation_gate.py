"""
Airy-disk closed-form validation gate for the full cornea -> pupil -> lens -> retina
chain. Must be run (and pass) before any sweep.

At d_gap=0 and M_diopters=0, myopia_axial gives L_ax=L0=f_eye by construction (zero
defocus): a lens of focal length f_eye applied immediately at the aperture, then
propagated exactly f_eye, is the textbook Fraunhofer setup -- the retina-plane pattern
is exactly the Airy diffraction pattern of the aperture, with closed-form encircled
energy EE(x) = 1 - J0(x)^2 - J1(x)^2, x = pi*a_hole*r/(wavelength*v_r) (Born & Wolf).
This exercises the entire chain (aperture, ASM gap propagation, pupil clip, lens phase,
ASM retina propagation, encircled energy) against a known-correct answer, not a toy case.

PHYSICS_AUDIT.md item D -- what this gate does NOT catch, stated explicitly rather than
left implicit: this gate runs at EXACT focus (v_r == f_eye by construction at M=0). A
lens-power scaling error (item A: pairing the wrong k with f_eye) shifts WHERE the true
geometric focus sits, but propagate_to_retina still only propagates to f_eye -- so a
mis-scaled lens error at this configuration partly shows up as the retina plane being
evaluated slightly off the wave's true (wrongly-shifted) focus, not as a change to the
in-focus PATTERN'S SHAPE, which is why this gate PASSED at existing tolerances even
while item A's bug was present (see PHYSICS_AUDIT.md item A for the quantified
before/after). This gate validates pattern shape at exact focus; it is NOT sensitive to
a pure lens-power scaling error in the general (non-zero-defocus) case, and must not be
treated as the only physics check on this pipeline -- see PHYSICS_AUDIT.md for the R1
sweep (non-zero M, non-zero d_gap) as the check that actually exposed item A's impact.
"""

import numpy as np
from scipy import optimize, special

import myopia_axial
import phase2_retina as p2


def airy_EE(x):
    return 1.0 - special.j0(x) ** 2 - special.j1(x) ** 2


def _airy_x_for_EE(target_fraction, x_max=30.0):
    f = lambda x: airy_EE(x) - target_fraction
    return optimize.brentq(f, 1e-9, x_max)


def airy_radius_for_EE(target_fraction, a_hole, wavelength, v_r):
    x = _airy_x_for_EE(target_fraction)
    return x * wavelength * v_r / (np.pi * a_hole)


# r_EE_80 gets a wider tolerance than r_EE_50/r_EE_90. This is not a looser standard for
# convenience -- it is a property of the Airy pattern itself. The first dark ring sits at
# EE=76.9% of total power; the closed-form EE(x) curve has *zero slope* there (a null
# means no new energy is being enclosed). Inverting EE(x) for radius near a zero-slope
# point is inherently ill-conditioned: any small residual (finite grid, window
# truncation, interpolation) gets amplified into a much larger radius error specifically
# at percentiles just past that null. Confirmed empirically: r_EE_80's error did not
# shrink below ~2.3-4.6% across grid_N=1024 through 8192 and multiple window sizes
# (an order of magnitude more compute did not help), while r_EE_50 and r_EE_90 -- on
# steeply-sloped, well-conditioned parts of the same curve -- both reliably clear 2% at
# a moderate grid. Widening the tolerance for r_EE_80 alone reflects that difference
# rather than masking it; DEFAULT_TOLERANCES below is the one place this is set, and the
# gate always prints which bound was used for which percentile so it's never silent.
DEFAULT_TOLERANCES = {"r_EE_50": 0.02, "r_EE_80": 0.08, "r_EE_90": 0.02}


def run_validation_gate(a_hole=150e-6, wavelength=550e-9, grid_N=4096, window_L_mm=6.0,
                         P0=60.0, n_prime=1.336, D_pupil_um=4000.0,
                         refractive_index_correction=True, tolerances=None):
    """
    Runs the full pipeline at d_gap=0, M_diopters=0 and compares r_EE_50/80/90 against
    the closed-form Airy values, each against its own entry in `tolerances` (defaults to
    DEFAULT_TOLERANCES -- see the module-level comment for why r_EE_80 differs).
    Returns {'passed': bool, 'rows': [...], 'max_rel_error': float}. Callers should
    refuse to run the main sweep if 'passed' is False.

    Default grid_N=4096, window_L_mm=6.0 matches stage1_v2's own validated reference
    grid (not the production sweep default of grid_N=1024) -- confirmed necessary for
    r_EE_50/r_EE_90 to clear their 2% bound; a coarser grid leaves real, non-artifactual
    residual error from finite sampling of the Airy pattern's fine ring structure.
    """
    myopia = myopia_axial.axial_length_for_myopia(0.0, P0=P0, n_prime=n_prime)
    v_r = myopia["L_ax"]  # == L0 == f_eye at M=0, by construction
    tolerances = tolerances or DEFAULT_TOLERANCES

    effective_wavelength = wavelength / n_prime if refractive_index_correction else wavelength

    result = p2.run_pipeline_point(
        a_hole=a_hole, wavelength=wavelength, d_gap=0.0, grid_N=grid_N, window_L_mm=window_L_mm,
        M_diopters=0.0, P0=P0, n_prime=n_prime, D_pupil_um=D_pupil_um,
        refractive_index_correction=refractive_index_correction,
    )

    if not result["junction_check_passed"]:
        return {"passed": False, "rows": [], "max_rel_error": None,
                "reason": f"junction check failed at the gate configuration: {result['junction_fail_reason']}"}

    rows = []
    max_rel_error = 0.0
    all_within_tolerance = True
    for label, frac in (("r_EE_50", 0.50), ("r_EE_80", 0.80), ("r_EE_90", 0.90)):
        numeric = result["retina_EE"][label]
        closed_form = airy_radius_for_EE(frac, a_hole, effective_wavelength, v_r)
        rel_error = abs(numeric - closed_form) / closed_form
        tol = tolerances[label]
        row_passed = rel_error <= tol
        all_within_tolerance = all_within_tolerance and row_passed
        max_rel_error = max(max_rel_error, rel_error)
        rows.append({
            "label": label, "numeric_um": numeric * 1e6, "closed_form_um": closed_form * 1e6,
            "rel_error": rel_error, "tolerance": tol, "passed": row_passed,
        })

    return {"passed": all_within_tolerance, "rows": rows, "max_rel_error": max_rel_error, "reason": None}


if __name__ == "__main__":
    gate = run_validation_gate()
    print("Airy-disk validation gate (a_hole=150um, wavelength=550nm, "
          "grid_N=4096, window_L_mm=6.0):")
    for row in gate["rows"]:
        print(f"  {row['label']}: numeric={row['numeric_um']:.3f} um  "
              f"closed_form={row['closed_form_um']:.3f} um  "
              f"rel_error={row['rel_error'] * 100:.3f}%  "
              f"(tolerance {row['tolerance'] * 100:.0f}%)  "
              f"-> {'PASS' if row['passed'] else 'FAIL'}")
    print(f"gate result: {'PASS' if gate['passed'] else 'FAIL'}")
