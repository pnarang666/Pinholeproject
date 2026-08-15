"""
Array_Design Build step: a joint (diameter, pitch) optimiser, turning Steps 1-3's
feasible REGION (joint_design_space.py) into a scored surface with an actual argmin.
Reuses, does not recompute: blur from multi_hole_blur_sweep.py (Fix 1), ghosting risk
from ghosting_risk.py (Fix 2), brightness from photometry/array_photometry.py directly.

THE OBJECTIVE IS A DESIGN CHOICE, STATED AS ONE, NOT HIDDEN AS PHYSICS.
Four physically-measured quantities go into it; how they trade off against each other
is a values question this analysis cannot answer from physics alone. Every weight below
is a named, overridable parameter with its own documented rationale, and sensitivity()
reports whether the argmin location is stable or fragile against each one -- a result
is only reported as "the optimum" where it is stable across a wide weighting range.

    cost(a, s, M, packing) = w_blur  * blur_ratio
                            + w_dark  * P_dark
                            + w_ghost * min(risk, GHOST_CAP)
                            - w_bright * (E_rel_mean_pct / BRIGHT_REF_PCT)

Term-by-term, what each is and why it is scaled the way it is:

  blur_ratio = array_r_EE_50_mean_um / single_hole_r_EE_50_MIN_at_this_M_um
    The array's alignment-weighted mean blur (multi_hole_blur_sweep.py, which already
    IS the multi-hole PSF, not a single-hole substitute -- ANALYSIS.md F4), divided by
    the BEST blur any single hole achieves at this M (stage2_fixed's own R1-sweep
    minimum, a fixed per-M reference, not this row's own aperture). Dimensionless,
    O(1) by construction: 1.0 = as good as the single-hole ideal, which happens
    exactly at the true single-hole optimum aperture with N_eff<=1, and grows both
    when the aperture is chosen away from that optimum AND when N_eff>1 degrades the
    array's blur beyond what any single hole would give -- one number capturing both
    effects the diameter axis and the pitch axis each separately influence.

  P_dark  (ANALYSIS.md F2/alignment_fractions.py)
    Fraction of pupil alignments with ZERO holes active -- the view goes fully black,
    not just blurry. Already in [0, 1], no normalization needed.

  risk  (ghosting_risk.py, Fix 2)
    P(N_eff>=2) x worst-harmonic perceptibility margin. risk=1 is already a natural
    unit: the point where the (probability-weighted) ghost comb sits exactly at the
    CSF detection threshold. Capped at GHOST_CAP so one point with risk~400 does not
    make every other term in the sum irrelevant by comparison.

  E_rel_mean_pct / BRIGHT_REF_PCT
    Retinal illuminance (%), alignment-MEAN (typical-case brightness; worst-case
    dimness is what P_dark already penalizes separately -- merging the two was
    explicitly ruled out by the task). BRIGHT_REF_PCT=1.0% is a fixed, stated
    reference -- roughly the brightness a single well-chosen pinhole delivers
    (RECOMMENDATION.md's own single-hole brightness figures span 0.4-12.9%, so 1% sits
    inside that range as a round-number "typical" anchor, not a fitted value).

DEFAULT WEIGHTS, each a stated value judgment:
  W_BLUR=1.0    the reference unit every other weight is stated relative to.
  W_DARK=5.0    a momentary total blackout (see literally nothing) is treated as a
                qualitatively harder failure than merely elevated blur (see a worse
                image) -- 5x is a value judgment, not a measurement, and is exactly
                what sensitivity() stress-tests.
  W_GHOST=1.0   risk's own units already put 1.0 at the CSF threshold, so no rescaling
                relative to blur_ratio's unit is applied by default.
  W_BRIGHT=1.0  brightness reward at the same nominal scale as the penalty terms; found
                empirically (see main()'s printed sensitivity table) to need a large
                multiple of this before it can outweigh blur/ghost at N_eff>1 -- stated
                as a finding, not assumed going in.

Run:  python3 optimise.py     (reuses multi_hole_blur_sweep.csv; computes ghosting risk
      and brightness live on that same grid -- ~10min, dominated by corrected_regime's
      own PSF cache, which is SEPARATE from array_psf_envelope's and therefore not free
      even though the underlying propagation was already paid for once by Fix 1 --
      ANALYSIS.md's improvements list notes this as a real, un-fixed inefficiency.)
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ghosting"))
sys.path.insert(0, os.path.join(HERE, "photometry"))

import array_photometry as ap  # noqa: E402
import corrected_regime as cr  # noqa: E402
import ghosting_risk as gr  # noqa: E402
import joint_design_space as jds  # noqa: E402

D_PUPIL_UM = jds.D_PUPIL_UM
N_OFFSETS = jds.N_OFFSETS  # 61
GHOST_CAP = 50.0
BRIGHT_REF_PCT = 1.0

W_BLUR_DEFAULT = 1.0
W_DARK_DEFAULT = 5.0
W_GHOST_DEFAULT = 1.0
W_BRIGHT_DEFAULT = 1.0

BLUR_SWEEP_CSV = os.path.join(HERE, "multi_hole_blur_sweep.csv")


def r1_min_blur_by_M():
    """Per-M minimum r_EE_50 from stage2_fixed's own (post-fix) R1 sweep -- the
    blur_ratio term's fixed reference, read once, not recomputed."""
    df = pd.read_csv(os.path.join(HERE, "single_hole_reference", "r1_multi_EE_sweep_postfix.csv"))
    assert df.junction_ok.all()
    return df.groupby("M_diopters").r_EE_50_um.min().to_dict()


def build_grid():
    """Loads Fix 1's blur sweep and adds ghosting risk (Fix 2, live) and brightness
    (photometry, live) on the IDENTICAL (a, s, M, packing) grid, so all three terms
    describe the same points -- not three separately-gridded approximations merged by
    nearest-neighbour."""
    assert os.path.exists(BLUR_SWEEP_CSV), (
        f"{BLUR_SWEEP_CSV} not found -- run multi_hole_blur_sweep.py first (Fix 1). "
        f"optimise.py reuses its grid rather than re-running the wave-optics sweep.")
    blur = pd.read_csv(BLUR_SWEEP_CSV)
    ref = r1_min_blur_by_M()

    rows = []
    n = len(blur)
    for i, r in blur.iterrows():
        a_um, s_um, M, packing = r.a_hole_um, r.pitch_um, r.M_diopters, r.packing
        risk_row = gr.ghosting_risk(a_um, s_um, M, packing=packing, n_offsets=N_OFFSETS)
        n_min, n_mean, n_max = jds.n_eff_triple(s_um, D_PUPIL_UM, packing, N_OFFSETS)
        e_rel_mean_pct = min(n_mean * ap.hole_area(a_um), ap.pupil_area(D_PUPIL_UM)) \
            / ap.pupil_area(D_PUPIL_UM) * 100.0

        blur_val = r.array_r_EE_50_mean_um
        blur_ratio = (blur_val / ref[M]) if np.isfinite(blur_val) else 100.0  # fully-dark row

        rows.append({
            "a_hole_um": a_um, "pitch_um": s_um, "M_diopters": M, "packing": packing,
            "array_r_EE_50_mean_um": blur_val, "single_hole_r_EE_50_min_at_M_um": ref[M],
            "blur_ratio": blur_ratio,
            "P_dark": risk_row["P_dark"], "P_ghost_capable": risk_row["P_ghost_capable"],
            "risk": risk_row["risk"], "regime_binary": risk_row["regime_binary"],
            "E_rel_mean_pct": e_rel_mean_pct,
            "N_eff_worst": n_min, "N_eff_mean": n_mean, "N_eff_best": n_max,
        })
        if (i + 1) % 200 == 0 or i + 1 == n:
            print(f"  {i+1}/{n} grid points scored")
    return pd.DataFrame(rows)


def cost(row, w_blur=W_BLUR_DEFAULT, w_dark=W_DARK_DEFAULT, w_ghost=W_GHOST_DEFAULT,
         w_bright=W_BRIGHT_DEFAULT):
    return (w_blur * row.blur_ratio
            + w_dark * row.P_dark
            + w_ghost * min(row.risk, GHOST_CAP)
            - w_bright * (row.E_rel_mean_pct / BRIGHT_REF_PCT))


def optimum_per_M_packing(df, **weights):
    df = df.copy()
    df["cost"] = df.apply(lambda r: cost(r, **weights), axis=1)
    idx = df.groupby(["M_diopters", "packing"])["cost"].idxmin()
    return df.loc[idx].sort_values(["M_diopters", "packing"])


def sensitivity(df, factors=(0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)):
    """For each weight in turn, holds the other three at default and sweeps this one
    across `factors` x its default, reporting the argmin (a, s, N_eff_worst) at
    M=4D/square for each. A weight whose argmin does not move across this whole range
    is reported as such -- the finding IS that stability, not a hedge around it."""
    base = dict(w_blur=W_BLUR_DEFAULT, w_dark=W_DARK_DEFAULT, w_ghost=W_GHOST_DEFAULT,
                w_bright=W_BRIGHT_DEFAULT)
    rows = []
    sub = df[(df.M_diopters == 4.0) & (df.packing == "square")].copy()
    for weight_name in ["w_blur", "w_dark", "w_ghost", "w_bright"]:
        for f in factors:
            w = dict(base); w[weight_name] = base[weight_name] * f
            sub["cost"] = sub.apply(lambda r: cost(r, **w), axis=1)
            best = sub.loc[sub["cost"].idxmin()]
            rows.append({"weight_varied": weight_name, "factor": f,
                        "value": w[weight_name], "best_a_um": best.a_hole_um,
                        "best_s_um": best.pitch_um, "best_N_eff_worst": best.N_eff_worst,
                        "best_regime": best.regime_binary, "best_cost": best["cost"]})
    return pd.DataFrame(rows)


def main():
    print(f"phase2_retina in use: {cr.assert_corrected_optics()}")
    print("verifying corrected_regime's margin_detail/classify split is regression-free:")
    cr.self_check()

    print(f"\nbuilding the scored grid from {os.path.basename(BLUR_SWEEP_CSV)} "
          f"(adding ghosting risk + brightness live on the same points)...")
    df = build_grid()
    out = os.path.join(HERE, "optimise_grid.csv")
    df.to_csv(out, index=False)
    print(f"wrote {out} ({len(df)} rows)")

    print(f"\n=== optimum per (M, packing) at default weights "
          f"(w_blur={W_BLUR_DEFAULT}, w_dark={W_DARK_DEFAULT}, w_ghost={W_GHOST_DEFAULT}, "
          f"w_bright={W_BRIGHT_DEFAULT}) ===")
    best = optimum_per_M_packing(df)
    print(best[["M_diopters", "packing", "a_hole_um", "pitch_um", "N_eff_worst",
               "regime_binary", "blur_ratio", "P_dark", "risk", "E_rel_mean_pct",
               "cost"]].to_string(index=False))
    best.to_csv(os.path.join(HERE, "optimise_best_per_M_packing.csv"), index=False)

    n_with_holes = int((best.N_eff_worst >= 1).sum())
    print(f"\n*** THE QUESTION THE TASK ASKS DIRECTLY: does an optimum with N_eff>1 "
          f"exist anywhere in this table? ***")
    print(f"    N_eff_worst>=1 (single-hole-or-more, i.e. NOT the N_eff<1 gap) at "
          f"{n_with_holes}/{len(best)} optima; N_eff_worst>1 (multiple holes GUARANTEED "
          f"active) at {int((best.N_eff_worst > 1).sum())}/{len(best)} optima.")

    print("\n=== sensitivity: does the M=4D/square optimum move as each weight varies "
          "(0.25x-16x default, others held fixed)? ===")
    sens = sensitivity(df)
    print(sens.to_string(index=False))
    sens.to_csv(os.path.join(HERE, "optimise_sensitivity.csv"), index=False)

    for weight_name in ["w_blur", "w_dark", "w_ghost", "w_bright"]:
        s = sens[sens.weight_varied == weight_name]
        stable = (s.best_a_um.nunique() == 1) and (s.best_s_um.nunique() == 1)
        print(f"  {weight_name}: argmin "
              f"{'STABLE' if stable else 'MOVES'} across 0.25x-16x "
              f"(a: {sorted(s.best_a_um.unique())}, s: {sorted(s.best_s_um.unique())})")

    print(f"\nwrote {os.path.join(HERE, 'optimise_best_per_M_packing.csv')}")
    print(f"wrote {os.path.join(HERE, 'optimise_sensitivity.csv')}")


if __name__ == "__main__":
    main()
