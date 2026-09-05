"""
Array_Design Step-2-follow-up (Fix 2): a CONTINUOUS ghosting risk, replacing the binary
A/B/C classification's reliance on the alignment MINIMUM for a question it answers
wrong.

ANALYSIS.md F2, found while reading photometry/ and ghosting/ together: Regime A
declares "no second hole simultaneously active" when the MINIMUM N_eff over pupil
alignments is <=1. Minimum is the correct worst case for BRIGHTNESS (fewest holes =
darkest) but the wrong one for GHOSTING (most holes = worst ghosting): a pitch with
N_eff_worst=1 can still have 2+ holes in the pupil at 82% of alignments
(alignment_fractions.csv, pitch=2500um) and still gets labelled ghost-free.

This module does not delete or edit that classification -- ghosting_regime.py and
corrected_regime.classify() are unchanged and importable exactly as before. It adds a
second number computed alongside it:

    risk(a, s, M) = P(N_eff(alignment) >= 2) * perceptual_margin(a, s, M)

P(N_eff>=2) comes from joint_design_space.alignment_fractions() (already verified there
against array_photometry's own sweep, verify_alignment_counts()), at n_offsets>=61 (the
resolution ANALYSIS.md F3 found necessary -- 15/25 miss the worst alignment and report a
pitch as "never dark"/"never multi-hole" when a finer grid shows otherwise).

perceptual_margin comes from corrected_regime.margin_detail() -- the SAME Eq. (5)
harmonic-margin computation classify() uses, pulled out so it can be evaluated
independent of classify()'s own N_eff<=1 early return (margin_detail() docstring: no
new physics, split out of the pre-existing classify() and checked identical to it by
corrected_regime.self_check(), which still passes unchanged).

The binary classification is kept alongside risk() in every output here, not replaced
by it -- both are reported side by side so the difference between them is visible,
per the task's explicit instruction not to delete the A/B/C rule.
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ghosting"))
sys.path.insert(0, os.path.join(HERE, "photometry"))

import corrected_regime as cr  # noqa: E402
import ghost_separation as gs  # noqa: E402  (used only by verify_defect2_wiring below)
import joint_design_space as jds  # noqa: E402  (alignment_fractions, N_OFFSETS=61)

D_PUPIL_UM = jds.D_PUPIL_UM
N_OFFSETS_DEFAULT = jds.N_OFFSETS  # 61 -- the F3-resolved alignment grid, not the 15 default


def ghosting_risk(a_hole_um, pitch_um, M_diopters, packing="square",
                   n_offsets=N_OFFSETS_DEFAULT, separation_model="corrected",
                   D_pupil_um=D_PUPIL_UM, wavelength_nm=550.0, d_gap_mm=12.0, P0=60.0,
                   n_prime=1.336, grid_N=2048, window_L_mm=6.0,
                   scene_luminance_cdm2=10000.0, field_deg=10.0):
    """
    Returns a dict with the continuous risk AND the binary classification, side by side:
      risk                    = P(N_eff>=2) * worst-harmonic margin  (this module's answer)
      regime_binary            = classify()'s regime_harmonic (A/B/C, unchanged)
      P_ghost_capable          = P(N_eff>=2) over pupil alignment (the number Regime A
                                  does not use, and F2 found this matters)
      margin_if_ghosting       = the harmonic margin AT this (a,s,M), independent of
                                  N_eff (i.e. "how bad would it be, given 2+ holes")
      N_eff_worst/_mean/_best  = for direct comparison against regime_binary's own basis
    """
    frac_dark, frac_single, frac_multi = jds.alignment_fractions(
        pitch_um, D_pupil_um, packing, n_offsets)
    n_min, n_mean, n_max = jds.n_eff_triple(pitch_um, D_pupil_um, packing, n_offsets)

    detail = cr.margin_detail(a_hole_um, pitch_um, M_diopters, separation_model,
                              wavelength_nm, d_gap_mm, D_pupil_um, P0, n_prime, grid_N,
                              window_L_mm, scene_luminance_cdm2, field_deg)
    margin = 0.0 if (not detail["ok"] or detail["worst_margin"] is None) else detail["worst_margin"]

    classification = cr.classify(a_hole_um, pitch_um, M_diopters, separation_model,
                                 wavelength_nm, d_gap_mm, D_pupil_um, P0, n_prime,
                                 grid_N, window_L_mm, packing, n_offsets,
                                 scene_luminance_cdm2, field_deg)

    return {
        "a_hole_um": a_hole_um, "pitch_um": pitch_um, "M_diopters": M_diopters,
        "packing": packing, "n_offsets": n_offsets,
        "risk": frac_multi * margin,
        "P_ghost_capable": frac_multi, "P_dark": frac_dark, "P_single_hole": frac_single,
        "margin_if_ghosting": margin,
        "psf_ok": detail["ok"], "psf_reason": detail.get("reason"),
        "N_eff_worst": n_min, "N_eff_mean": n_mean, "N_eff_best": n_max,
        "regime_binary": classification["regime_harmonic"],
        "regime_binary_reason": classification["reason"],
    }


def risk_sweep(apertures_um, pitches_um, M_values, packing="square",
               n_offsets=N_OFFSETS_DEFAULT, separation_model="corrected"):
    rows = []
    for M in M_values:
        for a_um in apertures_um:
            for s_um in pitches_um:
                if s_um <= a_um:
                    continue
                rows.append(ghosting_risk(a_um, s_um, M, packing=packing, n_offsets=n_offsets,
                                          separation_model=separation_model))
    return pd.DataFrame(rows)


def demonstrate_f2_disagreement():
    """The concrete case ANALYSIS.md F2 flagged: pitch=2500um, D_pupil=4mm, square --
    classified Regime A (N_eff_worst<=1) while P(N_eff>=2)=0.82. Shows risk() does NOT
    collapse to ~0 there the way the binary label implies, for a representative
    aperture/myopia."""
    rows = []
    print(f"{'a(um)':>6} {'s(um)':>6} {'M(D)':>5} | {'regime_binary':>13} {'N_eff_worst':>11} | "
          f"{'P(>=2 holes)':>12} {'margin_if_ghost':>15} {'risk':>10}")
    for a_um in (400.0, 700.0):
        for M in (2.0, 4.0, 8.0):
            for s_um in (2100.0, 2500.0, 2800.0, 3200.0, 4000.0):
                r = ghosting_risk(a_um, s_um, M)
                rows.append(r)
                print(f"{a_um:6.0f} {s_um:6.0f} {M:5.1f} | {r['regime_binary']:>13} "
                      f"{r['N_eff_worst']:11d} | {r['P_ghost_capable']:12.3f} "
                      f"{r['margin_if_ghosting']:15.2f} {r['risk']:10.3f}")
    return pd.DataFrame(rows)


def verify_defect2_wiring(points=((400.0, 900.0, 4.0), (400.0, 700.0, 2.0),
                                   (400.0, 1200.0, 3.0), (400.0, 2000.0, 6.0)),
                          stage0_csv=None, verbose=True):
    """
    Defect 2 unit test (Array_Design array_optimization audit, 2026-08-14): confirms
    ghosting_risk.py's ACTUAL runtime delta_r -- not the formula's NAME, its live
    numeric value -- matches (a) an independent recomputation of
    ghost_separation.delta_r_corrected_um for the same inputs, (b) the closed
    algebraic form s*M/(P0-M), and, if stage0's measured CSV is available, (c) the
    independently-measured ground truth from array_optimization/stage0_ghost_validation
    /validate_ghost_formula.py's two-hole propagation (not the same code path at all --
    a genuine wave-optics measurement, not another formula evaluation). This exists
    because a prior audit explicitly required NOT assuming correct wiring just because
    a parameter is named "corrected" (a previous separation_model="legacy" default
    would look identical to a casual read of call sites that don't pass it
    explicitly).
    """
    if stage0_csv is None:
        stage0_csv = os.path.join(HERE, "array_optimization", "stage0_ghost_validation",
                                  "ghost_formula_validation.csv")
    stage0_df = pd.read_csv(stage0_csv) if os.path.exists(stage0_csv) else None

    all_pass = True
    for a_um, s_um, M in points:
        detail = cr.margin_detail(a_um, s_um, M, separation_model="corrected")
        wired = detail["delta_r_um"]

        psf = cr.psf_for(a_um, M)
        independent = gs.delta_r_corrected_um(s_um, psf["v_r_um"], psf["v_f_um"])
        algebraic = gs.delta_r_corrected_from_M_um(s_um, M, P0=60.0)

        ok = abs(wired - independent) < 1e-9 and abs(wired - algebraic) < 1e-6
        msg = (f"  a={a_um:.0f} s={s_um:.0f} M={M}: wired={wired:.6f}um  "
              f"independent_recompute={independent:.6f}um  s*M/(P0-M)={algebraic:.6f}um")

        if stage0_df is not None:
            match = stage0_df[(stage0_df.pitch_um == s_um) & (stage0_df.M_diopters == M)]
            if len(match):
                measured = match.delta_r_measured_incoherent_um.iloc[0]
                pct = abs(wired - measured) / measured * 100 if measured > 0 else float("nan")
                msg += f"  measured(stage0)={measured:.3f}um (diff {pct:.1f}%)"

        all_pass = all_pass and ok
        if verbose:
            print(msg + ("  MATCH" if ok else "  *** MISMATCH ***"))

    assert all_pass, "ghosting_risk.py's wired delta_r does not match the validated formula"
    if verbose:
        print("  Defect 2 wiring: VERIFIED (exact match to the validated formula, "
              "not just name-matched)" + (" -- also cross-checked against stage0's "
              "independently-measured wave-optics ground truth" if stage0_df is not None else ""))
    return all_pass


def main():
    print(f"phase2_retina in use: {cr.assert_corrected_optics()}")
    print("verifying corrected_regime's margin_detail/classify split is regression-free:")
    cr.self_check()

    print("\nverifying Defect 2's validated formula is what ghosting_risk.py actually runs "
          "(unit test, not name-matching):")
    verify_defect2_wiring()

    print("\n=== F2 disagreement, made concrete: binary regime vs continuous risk ===")
    df_demo = demonstrate_f2_disagreement()
    demo_out = os.path.join(HERE, "ghosting_risk_regime_a_disagreement.csv")
    df_demo.to_csv(demo_out, index=False)
    print(f"wrote {demo_out}")

    print("\n=== full risk surface: 36-point Pass-4 grid, both packings ===")
    apertures = [300.0, 400.0, 700.0, 1000.0]
    pitches = [700.0, 900.0, 1200.0, 1500.0, 2000.0, 2500.0, 2800.0, 3200.0, 4000.0, 4800.0]
    m_values = [1.0, 2.0, 4.0, 6.0, 8.0]
    for packing in ["square", "hex"]:
        df = risk_sweep(apertures, pitches, m_values, packing=packing)
        out = os.path.join(HERE, f"ghosting_risk_sweep_{packing}.csv")
        df.to_csv(out, index=False)
        n_disagree = int(((df.regime_binary == "A") & (df.risk > 1.0)).sum())
        print(f"{packing}: wrote {out} ({len(df)} rows). Regime-A-but-risk>1 rows: "
              f"{n_disagree}/{len(df)} -- points the binary rule calls safe that the "
              f"continuous risk calls dangerous.")


if __name__ == "__main__":
    main()
