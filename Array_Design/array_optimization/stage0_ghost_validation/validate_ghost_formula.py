"""
Defect 2 validation harness: does either candidate ghost-separation formula match a
retinal intensity pattern actually computed by this project's own propagator, measured
by peak detection rather than assumed from either formula?

    (a) legacy:     delta_r = s * v_r / d_gap                    [prior work, wrong at M=0]
    (b) corrected:  delta_r = s * M / (P0 - M)                   [prior work, unconfirmed for M!=0]
    (c) free fit:   delta_r = A * s * M/(P0-M) + B                [this script]

TWO physically distinct calculations are built, both reusing ONLY existing low-level
primitives (junction.asm_propagate, phase2_retina.pupil_clip/lens_phase/
propagate_to_retina) -- no new propagator is written anywhere in this file:

  1. JOINT COHERENT propagation: a single aperture-plane field with TWO circular
     openings (a real two-hole mask, not one hole shifted), propagated through the
     SAME gap-then-retina chain as one coherent complex field. This is the literal
     "propagate the full multi-aperture mask once" alternative Part B's Stage 1 asks
     to be proven equivalent (or not) to array_psf_envelope.py's per-hole-shift-and-
     sum shortcut. It is NOT the physically correct model for real, incoherent
     daylight viewing (see point 2) -- it is the independent ground truth this script
     checks the shortcut against, and its own retinal intensity will show interference
     fringes a real incoherently-lit scene would not.

  2. INCOHERENT SUM: two SEPARATE single-hole propagations (one hole only, at each of
     the two positions), each measured as |U|^2, then ADDED as intensities. This is
     the model THEORY.md's Eq. (2) already cites as [EXACT] for macroscopically-
     separated apertures under ordinary daylight illumination (Goodman, Statistical
     Optics: mutual coherence between such paths is negligible). This is also
     mathematically what array_psf_envelope.array_psf() computes via roll-and-sum of
     a single on-axis PSF (shift-invariance already checked there,
     q1_copies_are_shifted_replicas). Delta_r is measured from THIS pattern, not the
     coherent one, because it is the physically appropriate model for the ghosting
     question this project actually asks (a real wearer in daylight, not a laser).

Comparing 1 and 2's peak positions (not their fine structure -- coherent fringes are
expected and irrelevant here) is what actually answers Part B's equivalence question,
using the same computation this script needed anyway for point 2 above.

M SIGN CONVENTION, stated explicitly because the two conventions in circulation
disagree: myopia_axial.py (this project's own module, used everywhere else in
Array_Design/) takes M_diopters >= 0 as the MAGNITUDE of myopia (axial elongation;
L_ax = n_prime/(P0-M) grows with M). The task that requested this script listed its
sweep as negative diopters (0, -0.5, -1, ..., -6D), which is the common CLINICAL
shorthand for a myopia correction's lens power, not this project's internal
convention. Interpreted here as MAGNITUDES of myopia (0, 0.5, 1, ..., 6D), i.e. sign
stripped and fed to myopia_axial.py unchanged -- passing the negative numbers through
literally would model HYPEROPIA (a shorter, not longer, eye) in this project's axial
model, the opposite of what a ghost-separation-vs-myopia sweep is for. Stated here so
the choice is auditable, not silently made.

Run:  python3 validate_ghost_formula.py [--help for all CLI params]
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ARRAY_DESIGN = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "ghosting"))
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "..", "stage2_fixed"))

import myopia_axial  # noqa: E402
import pipeline_junction as junction  # noqa: E402
import phase2_retina as p2  # noqa: E402
import ghost_separation as gs  # noqa: E402


def assert_corrected_optics():
    f = os.path.abspath(sys.modules["phase2_retina"].__file__)
    assert os.path.basename(os.path.dirname(f)) == "stage2_fixed", f"wrong phase2_retina: {f}"
    src = open(f).read()
    assert "field = lens_phase(field, dx, effective_wavelength, f_eye)" in src, \
        f"{f} is the PRE-lens-wavelength-fix code"
    return f


def two_hole_aperture(N, L, s_um, a_hole_um):
    """A single field with TWO circular openings at (-s/2, 0) and (+s/2, 0). Built from
    junction.make_grid directly -- no propagator logic here, just a mask, matching how
    stage1_v2.circular_aperture builds a one-hole mask."""
    X, Y, _, dx = junction.make_grid(N, L)
    half_s = (s_um * 1e-6) / 2.0
    r_hole = (a_hole_um * 1e-6) / 2.0
    R_left = np.sqrt((X + half_s) ** 2 + Y ** 2)
    R_right = np.sqrt((X - half_s) ** 2 + Y ** 2)
    U0 = ((R_left <= r_hole) | (R_right <= r_hole)).astype(np.complex128)
    return U0, dx


def one_hole_aperture(N, L, x_um, a_hole_um):
    X, Y, _, dx = junction.make_grid(N, L)
    r_hole = (a_hole_um * 1e-6) / 2.0
    R = np.sqrt((X - x_um * 1e-6) ** 2 + Y ** 2)
    U0 = (R <= r_hole).astype(np.complex128)
    return U0, dx


def propagate_to_retina_intensity(U0, dx, wavelength_nm, d_gap_mm, D_pupil_um, M,
                                   P0, n_prime, refractive_index_correction=True):
    """Gap (ASM) -> pupil clip -> lens phase -> retina (ASM). Reuses
    junction.asm_propagate and phase2_retina's own pupil_clip/lens_phase/
    propagate_to_retina -- the SAME functions run_gap_to_cornea and run_pipeline_point
    call elsewhere in this project, invoked directly here only because those wrappers
    build a single-hole aperture internally and this needs a two-hole one."""
    wavelength = wavelength_nm * 1e-9
    d_gap = d_gap_mm * 1e-3
    myopia = myopia_axial.axial_length_for_myopia(M, P0=P0, n_prime=n_prime)
    v_r, f_eye = myopia["L_ax"], myopia["f_eye"]
    eff_wl = (wavelength / n_prime) if refractive_index_correction else wavelength

    U_cornea, _ = junction.asm_propagate(U0, dx, wavelength, d_gap, L=U0.shape[0] * dx,
                                          band_limit=True)
    field = p2.pupil_clip(U_cornea, dx, D_pupil_um)
    field = p2.lens_phase(field, dx, eff_wl, f_eye)
    U_ret, _ = p2.propagate_to_retina(field, dx, eff_wl, v_r,
                                       refractive_index_correction=False, n_prime=n_prime)
    return np.abs(U_ret) ** 2, dx, v_r, f_eye


def two_peak_positions_um(I, dx):
    """Peak detection, not formula lookup: finds the intensity-weighted peak in the
    LEFT half (x<0) and RIGHT half (x>0) of the retinal image independently, valid
    because the two holes are built symmetric about x=0 by construction. Returns
    (x_left_um, x_right_um, separation_um). Uses the argmax cell directly (grid-limited
    precision, dx per step) -- sufficient given the M=0 tolerance is itself stated in
    grid pixels, not sub-pixel units."""
    N = I.shape[0]
    x = (np.arange(N) - N // 2) * dx * 1e6
    mid = N // 2
    left = I[:, :mid]
    right = I[:, mid:]
    xl = x[:mid][np.argmax(left.sum(axis=0))] if left.sum() > 0 else np.nan
    xr = x[mid:][np.argmax(right.sum(axis=0))] if right.sum() > 0 else np.nan
    return xl, xr, (xr - xl if np.isfinite(xl) and np.isfinite(xr) else np.nan)


def run_point(s_um, M, args):
    """Returns dict with coherent-joint and incoherent-sum peak separations, plus the
    two candidate formulas' predictions, for one (pitch, M) combination."""
    N, L = args.grid_N, args.window_L_mm * 1e-3

    # 1. Joint coherent two-hole propagation (independent ground truth for the
    #    shift-and-sum equivalence question).
    U0_joint, dx = two_hole_aperture(N, L, s_um, args.a_hole_um)
    I_joint, dx, v_r, f_eye = propagate_to_retina_intensity(
        U0_joint, dx, args.wavelength_nm, args.d_gap_mm, args.D_pupil_um, M,
        args.P0, args.n_prime)
    xl_c, xr_c, sep_coherent = two_peak_positions_um(I_joint, dx)

    # 2. Incoherent sum of two separate single-hole propagations (the physically
    #    correct model for real daylight viewing -- what delta_r is measured from).
    U0_l, dx = one_hole_aperture(N, L, -s_um / 2.0, args.a_hole_um)
    I_l, dx, _, _ = propagate_to_retina_intensity(
        U0_l, dx, args.wavelength_nm, args.d_gap_mm, args.D_pupil_um, M, args.P0, args.n_prime)
    U0_r, dx = one_hole_aperture(N, L, s_um / 2.0, args.a_hole_um)
    I_r, dx, _, _ = propagate_to_retina_intensity(
        U0_r, dx, args.wavelength_nm, args.d_gap_mm, args.D_pupil_um, M, args.P0, args.n_prime)
    I_incoherent = I_l + I_r
    xl_i, xr_i, sep_incoherent = two_peak_positions_um(I_incoherent, dx)

    pred_legacy = gs.delta_r_legacy_um(s_um, v_r * 1e6, args.d_gap_mm * 1e3)
    pred_corrected = gs.delta_r_corrected_um(s_um, v_r * 1e6, f_eye * 1e6)

    return {
        "pitch_um": s_um, "M_diopters": M, "v_r_um": v_r * 1e6, "f_eye_um": f_eye * 1e6,
        "dx_um": dx * 1e6,
        "delta_r_measured_coherent_um": sep_coherent,
        "delta_r_measured_incoherent_um": sep_incoherent,
        "coherent_vs_incoherent_diff_um": (
            abs(sep_coherent - sep_incoherent) if np.isfinite(sep_coherent) and
            np.isfinite(sep_incoherent) else np.nan),
        "pred_legacy_um": pred_legacy, "pred_corrected_um": pred_corrected,
    }


def fit_and_report(df, P0):
    """Fits the free empirical model delta_r = A*s*M/(P0-M) + B against the MEASURED
    (incoherent) delta_r, alongside the two fixed-form candidates, and reports R^2 for
    each -- an unbiased comparison, not a predetermined pick."""
    y = df.delta_r_measured_incoherent_um.values
    valid = np.isfinite(y)
    y = y[valid]

    def r2(pred):
        pred = pred[valid]
        ss_res = np.sum((y - pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    r2_legacy = r2(df.pred_legacy_um.values)
    r2_corrected = r2(df.pred_corrected_um.values)

    x_fit = (df.pitch_um * df.M_diopters / (P0 - df.M_diopters)).values[valid]
    A, B = np.polyfit(x_fit, y, 1)
    pred_free = A * (df.pitch_um * df.M_diopters / (P0 - df.M_diopters)).values + B
    r2_free = r2(pred_free)

    print(f"\n=== formula fit report (against {valid.sum()} measured points) ===")
    print(f"  (a) legacy    delta_r = s*v_r/d_gap                R^2 = {r2_legacy:.6f}")
    print(f"  (b) corrected delta_r = s*M/(P0-M)                 R^2 = {r2_corrected:.6f}")
    print(f"  (c) free fit  delta_r = {A:.5f}*[s*M/(P0-M)] + {B:.4f}   R^2 = {r2_free:.6f}")
    print(f"      free fit's slope A={A:.5f} (corrected formula implies A=1, B=0) -- "
          f"{'consistent with' if abs(A-1.0)<0.05 and abs(B)<max(1.0,0.05*y.mean()) else 'DIVERGES from'} "
          f"the corrected formula within a 5% band")
    return {"r2_legacy": r2_legacy, "r2_corrected": r2_corrected, "r2_free": r2_free,
            "free_fit_A": A, "free_fit_B": B}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--P0", type=float, default=60.0)
    ap.add_argument("--n_prime", type=float, default=1.336)
    ap.add_argument("--D_pupil_um", type=float, default=4000.0)
    ap.add_argument("--wavelength_nm", type=float, default=550.0)
    ap.add_argument("--d_gap_mm", type=float, default=12.0)
    ap.add_argument("--a_hole_um", type=float, default=400.0,
                    help="hole diameter for both apertures in the two-hole test")
    ap.add_argument("--grid_N", type=int, default=4096)
    ap.add_argument("--window_L_mm", type=float, default=6.0)
    ap.add_argument("--M_list", type=str, default="0,0.5,1,2,3,4,5,6",
                    help="myopia MAGNITUDES in diopters (see module docstring's M "
                         "sign-convention note for why this is not the negative list "
                         "as literally given in the requesting task)")
    ap.add_argument("--pitch_list_um", type=str, default="700,1200,2000,3200")
    args = ap.parse_args()

    M_values = [float(x) for x in args.M_list.split(",")]
    pitch_values = [float(x) for x in args.pitch_list_um.split(",")]

    print(f"phase2_retina in use: {assert_corrected_optics()}")
    print(f"grid_N={args.grid_N} window_L_mm={args.window_L_mm} a_hole_um={args.a_hole_um} "
          f"d_gap_mm={args.d_gap_mm} D_pupil_um={args.D_pupil_um} P0={args.P0} "
          f"n_prime={args.n_prime} wavelength_nm={args.wavelength_nm}")
    print(f"M sweep (magnitudes, see docstring): {M_values}")
    print(f"pitch sweep (um): {pitch_values}")

    rows = []
    for M in M_values:
        for s_um in pitch_values:
            r = run_point(s_um, M, args)
            rows.append(r)
            print(f"  M={M:4.1f}D s={s_um:6.0f}um: measured(incoherent)={r['delta_r_measured_incoherent_um']:8.3f}um  "
                  f"measured(coherent)={r['delta_r_measured_coherent_um']:8.3f}um  "
                  f"pred_legacy={r['pred_legacy_um']:9.2f}um  pred_corrected={r['pred_corrected_um']:8.3f}um  "
                  f"dx={r['dx_um']:.3f}um")

    df = pd.DataFrame(rows)
    out = os.path.join(HERE, "ghost_formula_validation.csv")
    df.to_csv(out, index=False)
    print(f"\nwrote {out}")

    # --- M=0 gate: this is the whole point of the exercise ---
    m0 = df[df.M_diopters == 0.0]
    dx0 = m0.dx_um.iloc[0]
    tol_um = 2.0 * dx0  # 2 grid pixels -- a peak-detection method resolves position to
                        # about +-1 pixel per peak, so +-2 pixels for a two-peak
                        # separation is the natural, grid-justified tolerance; not an
                        # arbitrarily chosen round number.
    max_m0 = m0.delta_r_measured_incoherent_um.abs().max()
    print(f"\n=== M=0 gate ===")
    print(f"grid pixel size dx={dx0:.4f}um -> tolerance = 2*dx = {tol_um:.4f}um")
    print(f"measured |delta_r| at M=0, across {len(m0)} pitches: max={max_m0:.4f}um")
    m0_pass = bool(max_m0 <= tol_um)
    print(f"M=0 -> delta_r~0 check: {'PASS' if m0_pass else 'FAIL'}")

    if not m0_pass:
        print("\n*** M=0 GATE FAILED. This is a pipeline bug, not a formula question. ***")
        print("Full diagnostic state:")
        print(f"  grid_N={args.grid_N}, window_L_mm={args.window_L_mm}, dx_um={dx0:.4f}")
        print(m0.to_string(index=False))
        print("\nSTOPPING before formula fitting -- see module docstring: an M=0 "
              "failure means the propagator or peak-detector itself is wrong, and "
              "fitting formulas to unreliable measurements would not be meaningful.")
        return

    print("\nM=0 gate passed. Proceeding to formula comparison.")

    coh_diff = df.coherent_vs_incoherent_diff_um.dropna()
    print(f"\n=== coherent-joint-propagation vs incoherent-sum peak agreement "
          f"(Part B Stage-1 equivalence check) ===")
    print(f"  max |coherent peak sep - incoherent peak sep| across {len(coh_diff)} points: "
          f"{coh_diff.max():.3f}um ({coh_diff.max()/dx0:.2f} grid pixels)")
    print(f"  mean: {coh_diff.mean():.3f}um")

    fit = fit_and_report(df, args.P0)

    # --- overlay plot ---
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    for M in M_values:
        sub = df[df.M_diopters == M].sort_values("pitch_um")
        axes[0].plot(sub.pitch_um, sub.delta_r_measured_incoherent_um, "o-", label=f"M={M:g}D")
    axes[0].set_xlabel("pitch s (um)"); axes[0].set_ylabel("measured delta_r (um, incoherent)")
    axes[0].set_title("Measured ghost separation vs pitch, by myopia")
    axes[0].legend(fontsize=7, ncol=2)
    axes[0].grid(alpha=0.3)

    all_x = df.pitch_um * df.M_diopters / (args.P0 - df.M_diopters)
    axes[1].scatter(all_x, df.delta_r_measured_incoherent_um, s=18, label="measured (incoherent)", zorder=3)
    xs = np.linspace(0, all_x.max(), 50)
    axes[1].plot(xs, xs, "k--", label="corrected: delta_r = s*M/(P0-M)")
    axes[1].plot(xs, fit["free_fit_A"] * xs + fit["free_fit_B"], "r:",
                 label=f"free fit (A={fit['free_fit_A']:.3f}, B={fit['free_fit_B']:.2f})")
    axes[1].set_xlabel("s * M/(P0-M)  (um)"); axes[1].set_ylabel("measured delta_r (um)")
    axes[1].set_title(f"R2: corrected={fit['r2_corrected']:.4f}, legacy={fit['r2_legacy']:.4f}, "
                      f"free={fit['r2_free']:.4f}")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)
    fig.suptitle(f"Ghost-separation formula validation (grid_N={args.grid_N}, "
                f"a_hole={args.a_hole_um:.0f}um, d_gap={args.d_gap_mm:.0f}mm)")
    fig.tight_layout()
    plot_out = os.path.join(HERE, "ghost_formula_validation.png")
    fig.savefig(plot_out, dpi=160, facecolor="white")
    print(f"wrote {plot_out}")


if __name__ == "__main__":
    main()
