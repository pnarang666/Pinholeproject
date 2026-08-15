"""
Recomputes noghost_constraint.csv with both corrections found in the Array_Design
consolidation. The original CSV is kept unchanged next to this file as the record of
what was previously believed; this writes noghost_constraint_corrected.csv alongside it.

Two independent things were wrong with the original file:

  1. OPTICS. Its r_EE_50/r_EE_80 columns came from the pre-lens-wavelength-fix sweep
     (1 Aug 2026; the fix landed 6 Aug 2026 -- stage2_fixed/LENS_WAVELENGTH_FIX.md).
     E.g. a=300um, M=1D: r_EE_50 = 23.04um there vs 16.51um now, and the whole optimum
     moved from 300-400um to 400-750um.
  2. GEOMETRY. no_ghost_max_pitch() implements the Master Formulas relation
     s_max = r_EE * d_gap / v_r, which inverts THEORY.md's Eq. (1)
     delta_r = s*v_r/d_gap. Eq. (1) is wrong (Array_Design/ghosting/ghost_separation.py,
     verified in ghosting/delta_r_derivation_check.py): the correct ghost separation is
     delta_r = s*|v_r-v_f|/v_f = s*M/(P0-M), so the correct inversion is

         s_max = r_EE * (P0 - M) / M

     which does NOT depend on d_gap at all, and is larger than the legacy value by
     (P0-M)/M * v_r/d_gap = 14x at M=8D to 111x at M=1D.

The point of the corrected table is not that the constraint got looser. It is that the
constraint mostly has NO SOLUTION: s_max comes out SMALLER than the hole diameter itself
for every aperture in the project's own corrected optimum band at M >= 4 D, i.e. there is
no pitch at which adjacent copies merge into one blur by overlapping. That is not a
numerical accident -- Eq. (4) of ghost_separation.py shows delta_r/blur_diameter =
s/a_stop exactly, so copies overlap only if the holes themselves do. The exception is low
myopia, where the defocus factor M/(P0-M) is small enough that diffraction dominates:
at M = 1 D, a = 300-700 um the corrected s_max does exceed the hole diameter (up to
1948 um at a = 300 um on the copy-diameter convention), which is the same low-myopia
merging window the ghosting classifier independently reports as Regime B. Elsewhere,
ghost copies at this geometry are suppressed by the eye's optical cutoff or avoided by
having only one hole active -- never by blur overlap.

Both merging conventions are tabulated because the answer is sensitive to which one is
used: s_max_corrected_r50 (copies merge when their centres are closer than one r_EE_50)
is the stricter reading of the Master Formulas relation, s_max_corrected_copy_diameter
(closer than a full copy width, 2*r_EE_50) the looser. 2/12 rows have a solution on the
strict convention, 4/12 on the loose one.

Run:  python3 noghost_constraint_corrected.py
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "stage2_fixed"))

import myopia_axial  # noqa: E402

P0 = 60.0
N_PRIME = 1.336
D_GAP_UM = 12000.0


def main():
    r1 = pd.read_csv(os.path.join(HERE, "..", "single_hole_reference",
                                   "r1_multi_EE_sweep_postfix.csv"))
    legacy = pd.read_csv(os.path.join(HERE, "noghost_constraint.csv"))
    wanted = legacy[["a_hole_um", "M_diopters"]].drop_duplicates()

    rows = []
    for _, w in wanted.iterrows():
        m = r1[(r1.a_hole_um == w.a_hole_um) & (r1.M_diopters == w.M_diopters)]
        if m.empty:
            continue
        m = m.iloc[0]
        v_r = myopia_axial.axial_length_for_myopia(w.M_diopters, P0=P0, n_prime=N_PRIME)["L_ax"] * 1e6
        defocus = w.M_diopters / (P0 - w.M_diopters)
        old = legacy[(legacy.a_hole_um == w.a_hole_um) & (legacy.M_diopters == w.M_diopters)].iloc[0]
        rows.append({
            "a_hole_um": w.a_hole_um, "M_diopters": w.M_diopters,
            "r_EE_50_um_postfix": m.r_EE_50_um, "r_EE_80_um_postfix": m.r_EE_80_um,
            "r_EE_50_um_prefix_legacy_file": old.r_EE_50_um,
            "s_max_legacy_formula_um": old.s_max_noghost_r50_um,
            "s_max_corrected_r50_um": m.r_EE_50_um / defocus,
            "s_max_corrected_r80_um": m.r_EE_80_um / defocus,
            "s_max_corrected_copy_diameter_um": 2.0 * m.r_EE_50_um / defocus,
            "s_max_corrected_r50_exceeds_hole_diameter":
                bool((m.r_EE_50_um / defocus) > w.a_hole_um),
            "s_max_corrected_copy_diameter_exceeds_hole_diameter":
                bool((2.0 * m.r_EE_50_um / defocus) > w.a_hole_um),
            "v_r_um": v_r, "defocus_factor_M_over_P0_minus_M": defocus,
        })
    df = pd.DataFrame(rows)
    out = os.path.join(HERE, "noghost_constraint_corrected.csv")
    df.to_csv(out, index=False)

    print(f"{'a(um)':>6} {'M(D)':>5} {'r50 pre':>8} {'r50 post':>9} {'s_max legacy':>13} "
          f"{'s_max corr':>11} {'s_max corr(2r)':>15} {'> a ?':>7}")
    for _, r in df.iterrows():
        print(f"{r.a_hole_um:6.0f} {r.M_diopters:5.1f} {r.r_EE_50_um_prefix_legacy_file:8.2f} "
              f"{r.r_EE_50_um_postfix:9.2f} {r.s_max_legacy_formula_um:13.1f} "
              f"{r.s_max_corrected_r50_um:11.1f} {r.s_max_corrected_copy_diameter_um:15.1f} "
              f"{str(bool(r.s_max_corrected_copy_diameter_exceeds_hole_diameter)):>7}")
    n_ok = int(df.s_max_corrected_copy_diameter_exceeds_hole_diameter.sum())
    print(f"\nrows where the corrected no-ghost pitch even exceeds the hole diameter "
          f"(i.e. where the constraint has any solution at all): {n_ok}/{len(df)}, "
          f"and on the strictest r_EE_50 convention: "
          f"{int(df.s_max_corrected_r50_exceeds_hole_diameter.sum())}/{len(df)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
