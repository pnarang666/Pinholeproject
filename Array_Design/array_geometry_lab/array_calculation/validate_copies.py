"""
Part 1's validation gate: confirms engine/ghost_formula.py and engine/vignetting_overlap.py
reproduce the ORIGINAL validated modules' outputs on the ORIGINAL validation datasets,
bit-identical or floating-point-tolerance-identical. Catches transcription errors from the
copy-not-import. Must PASS before any generator/evaluation code in this folder is trusted.

Run:  python3 validate_copies.py
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "engine"))

import ghost_formula as gf  # noqa: E402
import vignetting_overlap as vo  # noqa: E402

ARRAY_DESIGN = os.path.abspath(os.path.join(HERE, "..", ".."))  # HERE is now
                          # array_calculation/, one level deeper than before the
                          # calculation/evaluation/data split -- see README.md
GHOST_CSV = os.path.join(ARRAY_DESIGN, "array_optimization", "stage0_ghost_validation",
                         "ghost_formula_validation.csv")
VIGNETTING_CSV = os.path.join(ARRAY_DESIGN, "array_optimization", "vignetting_validation.csv")


def validate_ghost_formula():
    df = pd.read_csv(GHOST_CSV)
    copied_vr_vf = df.apply(
        lambda r: gf.delta_r_corrected_um(r.pitch_um, r.v_r_um, r.f_eye_um), axis=1)
    copied_M = df.apply(
        lambda r: gf.delta_r_corrected_from_M_um(r.pitch_um, r.M_diopters, P0=60.0), axis=1)
    original = df.pred_corrected_um

    diff_vr_vf = (copied_vr_vf - original).abs()
    diff_M = (copied_M - original).abs()
    max_diff_vr_vf = float(diff_vr_vf.max())
    max_diff_M = float(diff_M.max())
    n = len(df)
    tol = 1e-9
    ok = max_diff_vr_vf < tol and max_diff_M < tol
    return {
        "n_points": n, "max_abs_diff_vr_vf_form_um": max_diff_vr_vf,
        "max_abs_diff_M_form_um": max_diff_M, "tolerance_um": tol, "pass": ok,
    }


def validate_vignetting_overlap():
    df = pd.read_csv(VIGNETTING_CSV)
    copied = df.apply(
        lambda r: float(vo.overlap_area_um2(r.delta_um, r.R_p_um, r.R_h_um)), axis=1)
    original = df.A_overlap_closed_form_um2

    diff = (copied - original).abs()
    max_diff = float(diff.max())
    n = len(df)
    tol = 1e-6  # um^2, generous relative to areas up to ~3.1e6 um^2
    ok = max_diff < tol
    n_negative_copied = int((copied < 0).sum())
    return {
        "n_points": n, "max_abs_diff_um2": max_diff, "tolerance_um2": tol,
        "n_negative_in_copy": n_negative_copied, "pass": ok and n_negative_copied == 0,
    }


def main():
    print("=== Validating engine/ghost_formula.py against ghost_formula_validation.csv ===")
    g = validate_ghost_formula()
    print(f"  {g['n_points']} points; max |copied(v_r,v_f form) - original| = "
          f"{g['max_abs_diff_vr_vf_form_um']:.3e} um; max |copied(M form) - original| = "
          f"{g['max_abs_diff_M_form_um']:.3e} um (tolerance {g['tolerance_um']:.0e} um)")
    print(f"  RESULT: {'PASS' if g['pass'] else 'FAIL'}")

    print("\n=== Validating engine/vignetting_overlap.py against vignetting_validation.csv ===")
    v = validate_vignetting_overlap()
    print(f"  {v['n_points']} points; max |copied - original| = {v['max_abs_diff_um2']:.3e} um^2 "
          f"(tolerance {v['tolerance_um2']:.0e} um^2); negative values in copy: {v['n_negative_in_copy']}")
    print(f"  RESULT: {'PASS' if v['pass'] else 'FAIL'}")

    overall = g["pass"] and v["pass"]
    print(f"\n=== OVERALL VALIDATION GATE: {'PASS' if overall else 'FAIL'} ===")
    if not overall:
        print("STOPPING -- do not proceed to Part 2 generators until this passes.")
        sys.exit(1)
    return g, v


if __name__ == "__main__":
    main()
