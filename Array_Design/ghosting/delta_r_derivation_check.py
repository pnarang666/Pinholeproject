"""
Settles the delta_r formula question NUMERICALLY, three independent ways, before any
consolidated analysis is trusted (Array_Design Step 2). Prints one table; writes
delta_r_derivation_check.csv.

Test 1 -- paraxial ray transfer, no formula assumed. Refraction at a single plane of
    power P0 into a medium of index n' (n'u' = nu - y*P0, the standard paraxial
    refraction equation), then a drift of v_r. Starts from a ray parallel to the axis
    at height h (a distant on-axis object point) and reports where it lands. Nothing
    about |v_r-v_f|/v_f or v_r/d_gap is assumed anywhere in this computation.

Test 2 -- WAVE optics, using this project's own unmodified pipeline. Propagates a
    laterally DISPLACED hole through stage2_fixed's real chain (run_gap_to_cornea ->
    pupil_clip -> lens_phase -> propagate_to_retina, all imported, none rewritten) and
    measures the intensity centroid of the resulting retinal spot. The displacement is
    applied by rolling the cornea-plane field: ASM propagation is a convolution and is
    therefore exactly shift-invariant, so rolling the propagated field equals
    propagating a rolled aperture (checked directly by test 2b below), which lets the
    displaced case reuse run_gap_to_cornea() with no modification at all.

Test 2b -- verifies that shift-invariance claim rather than asserting it: propagates a
    genuinely displaced aperture built at the array plane and compares against the
    rolled-field shortcut.

Test 3 -- the M = 0 limit, which is what actually decides the question. A perfectly
    focused eye must image a distant point to ONE point regardless of how many holes
    admit light. Whichever formula does not give delta_r = 0 there is wrong.

Run:  python3 delta_r_derivation_check.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "stage2_fixed"))

import myopia_axial  # noqa: E402
import pipeline_junction as junction  # noqa: E402
import phase2_retina as p2  # noqa: E402

from ghost_separation import delta_r_legacy_um, delta_r_corrected_um, delta_r_corrected_from_M_um  # noqa: E402

P0 = 60.0
N_PRIME = 1.336
WAVELENGTH_NM = 550.0
D_GAP_MM = 12.0
D_PUPIL_UM = 4000.0
GRID_N = 2048
WINDOW_L_MM = 6.0


def assert_corrected_optics():
    """Fail loudly if anything but stage2_fixed's post-lens-wavelength-fix module is
    loaded (the same provenance check every optics-touching task in this project uses)."""
    f = os.path.abspath(sys.modules["phase2_retina"].__file__)
    assert os.path.basename(os.path.dirname(f)) == "stage2_fixed", f"wrong phase2_retina: {f}"
    src = open(f).read()
    assert "effective_wavelength = (wavelength / n_prime)" in src, \
        "phase2_retina.py does not resolve an effective wavelength -- not the post-fix file"
    assert "field = lens_phase(field, dx, effective_wavelength, f_eye)" in src, \
        "phase2_retina.py's lens_phase is not called with the effective wavelength -- pre-fix file"
    return f


# ---------------------------------------------------------------------------------
# Test 1: paraxial ray transfer -- no formula assumed
# ---------------------------------------------------------------------------------

def ray_trace_landing_height_um(h_um, M_diopters, P0=P0, n_prime=N_PRIME):
    """
    Ray parallel to the axis at height h (distant on-axis object), refracted once at a
    plane of power P0 into a medium of index n_prime, then drifted to the retina.

        refraction:  n' * u' = n * u - y * P0,  with n = 1, u = 0  =>  u' = -h*P0/n'
        drift:       y(z) = h + z * u'

    v_r comes from myopia_axial.axial_length_for_myopia() -- the project's own axial
    model, not a value re-derived here.
    """
    v_r_um = myopia_axial.axial_length_for_myopia(M_diopters, P0=P0, n_prime=n_prime)["L_ax"] * 1e6
    u_prime = -h_um * P0 / n_prime  # radians per metre of height... see units note below
    # P0 is in diopters (1/m) and h in um; u' as written is in um/m. Converting the
    # drift v_r to metres keeps the product in um:  y = h + (v_r[m]) * (-h*P0/n')[um/m].
    y_um = h_um + (v_r_um * 1e-6) * u_prime
    return y_um, v_r_um


# ---------------------------------------------------------------------------------
# Test 2: wave optics through the real, unmodified pipeline
# ---------------------------------------------------------------------------------

def retinal_centroid_of_displaced_hole(a_hole_um, h_um, M_diopters, build_shifted_aperture=False):
    """
    Returns (centroid_x_um, peak_x_um, h_actual_um) of the retinal intensity produced by
    a single hole displaced h_um off axis in the array plane.

    build_shifted_aperture=False: displace by rolling the cornea-plane field (reuses
      junction.run_gap_to_cornea unmodified).
    build_shifted_aperture=True:  build the displaced aperture at the array plane and
      propagate it with junction.asm_propagate directly (test 2b's cross-check).
    """
    wavelength = WAVELENGTH_NM * 1e-9
    d_gap = D_GAP_MM * 1e-3
    myopia = myopia_axial.axial_length_for_myopia(M_diopters, P0=P0, n_prime=N_PRIME)
    v_r, f_eye = myopia["L_ax"], myopia["f_eye"]
    eff_wl = wavelength / N_PRIME  # phase2_retina's own convention (refractive_index_correction=True)

    L = WINDOW_L_MM * 1e-3
    dx = L / GRID_N
    n_pix = int(round((h_um * 1e-6) / dx))
    h_actual_um = n_pix * dx * 1e6

    if build_shifted_aperture:
        Xg, Yg, _, dx_g = junction.make_grid(GRID_N, L)
        R_shifted = np.sqrt((Xg - n_pix * dx_g) ** 2 + Yg ** 2)
        U0 = (R_shifted <= (a_hole_um * 1e-6) / 2.0).astype(np.complex128)
        U_cornea, _ = junction.asm_propagate(U0, dx_g, wavelength, d_gap, L=L, band_limit=True)
        dx = dx_g
    else:
        cornea = junction.run_gap_to_cornea(a_hole_um * 1e-6, wavelength, d_gap, GRID_N, WINDOW_L_MM)
        dx = cornea["dx"]
        U_cornea = np.roll(cornea["U_cornea"], n_pix, axis=1)  # axis=1 is +x (make_grid: indexing='xy')

    field = p2.pupil_clip(U_cornea, dx, D_PUPIL_UM)
    field = p2.lens_phase(field, dx, eff_wl, f_eye)
    U_ret, _ = p2.propagate_to_retina(field, dx, eff_wl, v_r, refractive_index_correction=False,
                                       n_prime=N_PRIME)
    I = np.abs(U_ret) ** 2

    X, _, _, _ = junction.make_grid(GRID_N, L)
    total = I.sum()
    centroid_x_um = float((I * X).sum() / total) * 1e6 if total > 0 else np.nan
    peak_x_um = float(X.ravel()[int(np.argmax(I))]) * 1e6
    return centroid_x_um, peak_x_um, h_actual_um


def main():
    print(f"phase2_retina in use: {assert_corrected_optics()}")
    print(f"grid_N={GRID_N}, window={WINDOW_L_MM}mm, lambda={WAVELENGTH_NM}nm, "
          f"d_gap={D_GAP_MM}mm, D_pupil={D_PUPIL_UM}um, P0={P0}D, n'={N_PRIME}\n")

    a_hole_um = 400.0
    h_um = 450.0  # one hole of a pitch-900um pair, displaced +s/2 off axis
    rows = []

    header = (f"{'M(D)':>5} {'v_r(um)':>9} {'v_f(um)':>9} | {'ray y(um)':>10} "
              f"{'wave centroid':>14} {'wave peak':>10} | {'pred (C)':>9} {'pred (L)':>10}")
    print(header)
    print("-" * len(header))
    for M in [0.0, 1.0, 2.0, 4.0, 6.0, 8.0]:
        y_ray, v_r_um = ray_trace_landing_height_um(h_um, M)
        v_f_um = myopia_axial.axial_length_for_myopia(M, P0=P0, n_prime=N_PRIME)["f_eye"] * 1e6
        c_x, p_x, h_act = retinal_centroid_of_displaced_hole(a_hole_um, h_um, M)
        # Both candidate formulas, evaluated for a single hole displaced h (a pitch-h
        # pair's separation is the same expression with s -> h; signs dropped by both).
        pred_C = delta_r_corrected_um(h_act, v_r_um, v_f_um)
        pred_L = delta_r_legacy_um(h_act, v_r_um, D_GAP_MM * 1e3)
        pred_C_fromM = delta_r_corrected_from_M_um(h_act, M, P0)
        print(f"{M:5.1f} {v_r_um:9.1f} {v_f_um:9.1f} | {y_ray:10.2f} "
              f"{c_x:14.2f} {p_x:10.2f} | {pred_C:9.2f} {pred_L:10.1f}")
        rows.append({
            "M_diopters": M, "h_um": h_act, "v_r_um": v_r_um, "v_f_um": v_f_um,
            "ray_trace_y_um": y_ray, "wave_centroid_x_um": c_x, "wave_peak_x_um": p_x,
            "pred_corrected_C_um": pred_C, "pred_corrected_C_fromM_um": pred_C_fromM,
            "pred_legacy_L_um": pred_L,
            "abs_err_corrected_um": abs(abs(c_x) - pred_C),
            "abs_err_legacy_um": abs(abs(c_x) - pred_L),
        })

    print("\n(ray y and wave centroid are signed -- negative = image inverted about the "
          "axis, as Eq. (2) predicts; predictions are magnitudes.)")

    # ---- Test 2b: is the rolled-field shortcut really equivalent? ----
    c_roll, _, h_act = retinal_centroid_of_displaced_hole(a_hole_um, h_um, 4.0)
    c_build, _, _ = retinal_centroid_of_displaced_hole(a_hole_um, h_um, 4.0, build_shifted_aperture=True)
    print(f"\nTest 2b shift-invariance check @M=4D: rolled-field centroid {c_roll:.3f}um vs "
          f"displaced-aperture centroid {c_build:.3f}um "
          f"(difference {abs(c_roll - c_build):.4f}um = {abs(c_roll-c_build)/max(abs(c_build),1e-9)*100:.3f}%)")

    # ---- Test 3: the M=0 limit ----
    c0, p0_, _ = retinal_centroid_of_displaced_hole(a_hole_um, h_um, 0.0)
    v_r0 = myopia_axial.axial_length_for_myopia(0.0, P0=P0, n_prime=N_PRIME)["L_ax"] * 1e6
    print(f"\nTest 3 (M=0, emmetropic): measured retinal centroid {c0:.3f} um for a hole "
          f"displaced {h_act:.1f} um off axis.")
    print(f"   corrected (C) predicts {delta_r_corrected_um(h_act, v_r0, v_r0):.3f} um; "
          f"legacy (L) predicts {delta_r_legacy_um(h_act, v_r0, D_GAP_MM*1e3):.1f} um.")

    import pandas as pd
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "delta_r_derivation_check.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
