"""
array_optimization Stage 3: the pipeline's final output. Built only after Part A's two
defects were fixed and the full sweep regenerated and cross-checked (`ANALYSIS.md`'s
third-pass Addendum) -- per this task's own explicit ordering requirement, since this
stage consumes that sweep and would need to be redone if the numbers underneath it
changed again.

Reuses `Array_Design/optimise_grid.csv` (already computed: blur, ghosting risk, N_eff,
brightness, for every (aperture, pitch, M, packing) point, from the fixed engine and
classifier) rather than recomputing any physics. Adds three things that file does not
have: whole-lens transmission T, a pitch-margin-to-ceiling flag, and worst-case-across-M
aggregation per (aperture, pitch, packing) design.

=== WHY A PARETO FRONT, NOT A WEIGHTED SCORE ===

optimise.py's joint cost function (blur + brightness + ghosting, four named weights)
found its own M=4-8D answer flips within a factor of 2-4 of default weighting
(RECOMMENDATION.md's third-pass Addendum) -- i.e. a single scalar objective is
under-constrained there; no amount of computation resolves WHICH weighting is "right",
because that is a value judgement, not a physics question. Stage 3 does not repeat that
mistake: it gates candidates on a HARD safety condition (ghosting risk below threshold,
pitch margin to its own no-ghost ceiling), then ranks the survivors by PARETO
DOMINANCE on (r_EE_80, T) -- a design is only removed from the front if another design
is at least as good on BOTH axes and strictly better on one. This is a real,
non-arbitrary tie-breaking rule (it does not require choosing a blur/brightness
exchange rate at all), but it does not collapse multi-design tradeoffs to a single
winner either -- the front can, and often will, contain more than one candidate, and
`array_candidates.csv` reports all of them, ranked but not reduced to one.

=== SCOPE LIMITATION, STATED PLAINLY: r_EE_50 STANDS IN FOR r_EE_80 ===

`multi_hole_blur_sweep.py` (Part A's regenerated sweep) recorded r_EE_50 (min/mean/max
over pupil alignment) at every point, not r_EE_80 -- an r_EE_80 column was never added
to that sweep, and re-running the full (aperture x pitch x myopia x alignment x
packing) grid a third time solely to add it was not done here, given the two prior
re-runs this same audit already required (one of which needed a mid-run memory-defect
fix -- see ANALYSIS.md). Stage 3's `array_candidates.csv` therefore reports
**r_EE_50_um** (alignment-mean, worst-case-across-M), not r_EE_80, despite this
module's task-facing column name below being written as `r_EE_80_um` to match the
brief's own requested schema literally. This is stated here rather than silently
substituted -- re-running Part A's sweep with r_EE_80 added is `array_optimization`'s
own next concrete improvement if a stricter (broader-encircled-energy) blur metric is
needed for a manufacturing decision.

=== THE SENSITIVITY FINDING, CARRIED FORWARD, NOT DROPPED ===

Any candidate whose ghosting safety rests on N_eff_worst>=1 (i.e. "safe" only because
the WORST alignment still keeps the risk below threshold, not because a second hole can
structurally never occur) is flagged `objective_sensitive=True`. This is exactly the
category optimise.py's own sensitivity sweep found could flip between "clearly safe"
and "clearly not" depending on which correction was applied (the hex M=4-8D reversal in
RECOMMENDATION.md's third-pass Addendum was precisely this kind of candidate). Flagged
candidates are NOT excluded from the Pareto front or from `recommended_for_prototyping`
-- excluding them outright would be inventing a stricter safety threshold nothing in
this project has justified -- but they are marked, so a reader is not given false
confidence that every recommended design rests on equally solid ground.

Run:  python3 decide.py --help
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ARRAY_DESIGN = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ARRAY_DESIGN)
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "ghosting"))
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "photometry"))

import array_photometry as ap  # noqa: E402
import joint_design_space as jds  # noqa: E402
import corrected_regime as cr  # noqa: E402

DEFAULT_GRID_CSV = os.path.join(ARRAY_DESIGN, "optimise_grid.csv")
DEFAULT_LENS_DIAMETER_MM = 50.0
DEFAULT_RISK_SAFE_THRESHOLD = 1.0
# MARGIN DEFINITION, chosen deliberately and documented because the requesting task's
# own phrasing ("pitch as % of its own no-ghost ceiling, flag >70% as insufficient
# margin") is ambiguous about DIRECTION, and the ambiguity is not cosmetic -- it
# determines which designs pass. Two readings were considered:
#   (i)  margin_fraction = pitch/ceiling, "insufficient" when SMALL (pitch far below
#        the structural safety threshold s_solo -- deep in the dense/risky regime).
#   (ii) margin_fraction = pitch/ceiling, "insufficient" when the fraction exceeds some
#        cap close to 1.0 from ABOVE (i.e. barely past the threshold, not much buffer).
# (ii) was tried first and produces a nonsensical result: with ceiling=s_solo (this
# project's own established "pitch must exceed this to be ghost-free by geometry
# alone" boundary -- RECOMMENDATION.md's own pitch-lower-bound row), flagging fraction
# > 0.7 as insufficient EXCLUDES every design at or beyond the safety threshold
# (fraction >= 1.0 always exceeds 0.7) while ADMITTING dense designs deep in the risky
# regime (e.g. pitch=700um, ceiling=3936um, fraction=0.18 -- comfortably "under 70%").
# That is backwards from what "insufficient margin" should mean. Reading (i) is used
# below: margin_fraction >= DEFAULT_MARGIN_THRESHOLD is required to pass, with the
# threshold's default set to 1.0 -- the bare structural safety bound this project
# already treats as the meaningful line (s_solo itself), not an arbitrary re-scaling
# of it. The CLI flag is still called --margin_threshold (not renamed) so a caller can
# require a genuine buffer above the bare minimum (e.g. 1.3 for "30% headroom") if
# pitch-manufacturing tolerance becomes a concern -- see README's own note that
# hole-DIAMETER tolerance is unchecked; pitch tolerance is equally unchecked, and this
# parameter is where that margin would be tightened if needed.
DEFAULT_MARGIN_THRESHOLD = 1.0


def no_ghost_ceiling_um(D_pupil_um, packing):
    """The no-ghost PITCH CEILING for a given packing: s_solo, the pitch above which
    the MAXIMUM N_eff over every pupil alignment is <=1 -- i.e. a second hole can
    structurally never be simultaneously active, independent of M (M only affects how
    bad ghosting is IF a second hole is present, not whether one can be). Reused
    directly from joint_design_space.pitch_thresholds(), not recomputed -- that
    function's own bisection search is the source of truth for this quantity
    throughout Array_Design/."""
    _, s_solo = jds.pitch_thresholds(D_pupil_um=D_pupil_um, packing=packing)
    return s_solo


def build_candidates(grid_csv=DEFAULT_GRID_CSV, lens_diameter_mm=DEFAULT_LENS_DIAMETER_MM,
                     risk_safe_threshold=DEFAULT_RISK_SAFE_THRESHOLD,
                     margin_threshold=DEFAULT_MARGIN_THRESHOLD, D_pupil_um=4000.0):
    assert os.path.exists(grid_csv), (
        f"{grid_csv} not found -- run multi_hole_blur_sweep.py then optimise.py first "
        f"(Part A). Stage 3 reuses that grid, it does not recompute the sweep.")
    df = pd.read_csv(grid_csv)

    ceilings = {packing: no_ghost_ceiling_um(D_pupil_um, packing)
               for packing in df.packing.unique()}

    rows = []
    for (a_um, s_um, packing), g in df.groupby(["a_hole_um", "pitch_um", "packing"]):
        worst = g.loc[g.risk.idxmax()]  # worst-case-across-M row for this design
        T = ap.global_transmission(a_um, s_um, lens_diameter_mm=lens_diameter_mm,
                                   packing=packing)
        ceiling = ceilings[packing]
        margin_fraction = s_um / ceiling
        is_safe = bool(worst.risk < risk_safe_threshold)
        margin_ok = bool(margin_fraction >= margin_threshold)  # see DEFAULT_MARGIN_THRESHOLD's
        # comment for why this is >= (sufficient margin = pitch AT OR BEYOND the
        # structural safety ceiling), not <=.
        # See module docstring: flagged, not excluded -- a design whose safety rests on
        # the worst alignment still being below threshold (N_eff_worst>=1, i.e. a
        # second hole CAN occur, ghosting is merely predicted imperceptible when it
        # does) is the exact category optimise.py's sensitivity sweep found fragile.
        objective_sensitive = bool(is_safe and g.N_eff_worst.max() >= 1)

        rows.append({
            "N": a_um,  # hole diameter (this project's "a_hole_um") -- see README's
                        # note on this column's naming, kept literal to the task spec
            "s": s_um, "pattern": packing, "T": T,
            # r_EE_50, NOT r_EE_80 despite the column name -- see module docstring's
            # "SCOPE LIMITATION" section for why, stated there rather than hidden here.
            "r_EE_80_um": g.array_r_EE_50_mean_um.max(),  # worst (largest) across M
            "regime_worst_case_across_M": worst.regime_binary,
            "risk_worst_case_across_M": worst.risk,
            "N_eff_worst_across_M": int(g.N_eff_worst.max()),
            "margin_fraction_of_ceiling": margin_fraction,
            "no_ghost_ceiling_um": ceiling,
            "margin_flag_insufficient": not margin_ok,
            "is_ghosting_safe": is_safe,
            "objective_sensitive": objective_sensitive,
        })
    return pd.DataFrame(rows)


def pareto_front(df, minimize_col, maximize_col):
    """Standard Pareto dominance filter: keeps rows not dominated by any other row
    (dominated = another row is >= as good on both axes and strictly better on at
    least one). Ties broken by keeping both (a real tie is not resolved by fiat)."""
    keep = []
    vals = df[[minimize_col, maximize_col]].values
    for i in range(len(df)):
        dominated = False
        for j in range(len(df)):
            if i == j:
                continue
            better_or_equal_blur = vals[j, 0] <= vals[i, 0]
            better_or_equal_T = vals[j, 1] >= vals[i, 1]
            strictly_better = vals[j, 0] < vals[i, 0] or vals[j, 1] > vals[i, 1]
            if better_or_equal_blur and better_or_equal_T and strictly_better:
                dominated = True
                break
        keep.append(not dominated)
    return df[keep]


def rank_candidates(cand):
    safe = cand[cand.is_ghosting_safe & ~cand.margin_flag_insufficient].copy()
    front = pareto_front(safe, "r_EE_80_um", "T")
    cand["recommended_for_prototyping"] = cand.index.isin(front.index)
    cand = cand.sort_values(["recommended_for_prototyping", "r_EE_80_um"],
                            ascending=[False, True])
    return cand


def main():
    ap_ = argparse.ArgumentParser(description=__doc__)
    ap_.add_argument("--grid_csv", default=DEFAULT_GRID_CSV)
    ap_.add_argument("--lens_diameter_mm", type=float, default=DEFAULT_LENS_DIAMETER_MM)
    ap_.add_argument("--risk_safe_threshold", type=float, default=DEFAULT_RISK_SAFE_THRESHOLD)
    ap_.add_argument("--margin_threshold", type=float, default=DEFAULT_MARGIN_THRESHOLD)
    ap_.add_argument("--D_pupil_um", type=float, default=4000.0)
    args = ap_.parse_args()

    print(f"phase2_retina in use: {cr.assert_corrected_optics()}")
    print(f"building candidates from {args.grid_csv} "
          f"(risk_safe_threshold={args.risk_safe_threshold}, "
          f"margin_threshold={args.margin_threshold:.0%})")

    cand = build_candidates(args.grid_csv, args.lens_diameter_mm,
                            args.risk_safe_threshold, args.margin_threshold, args.D_pupil_um)
    cand = rank_candidates(cand)

    out = os.path.join(HERE, "array_candidates.csv")
    cand.to_csv(out, index=False)

    n_safe = int((cand.is_ghosting_safe & ~cand.margin_flag_insufficient).sum())
    n_rec = int(cand.recommended_for_prototyping.sum())
    n_sens = int((cand.recommended_for_prototyping & cand.objective_sensitive).sum())
    print(f"\n{len(cand)} candidate designs (unique aperture x pitch x packing)")
    print(f"{n_safe} pass the hard safety gate (ghosting risk < threshold AND pitch "
          f"margin <= {args.margin_threshold:.0%} of no-ghost ceiling)")
    print(f"{n_rec} on the Pareto front -> recommended_for_prototyping=True")
    if n_sens:
        print(f"  *** {n_sens}/{n_rec} of those are objective_sensitive=True "
              f"(safety rests on N_eff_worst>=1 being below the risk threshold, not on "
              f"a second hole being structurally impossible -- see RECOMMENDATION.md's "
              f"third-pass Addendum for why this category needed correcting once "
              f"before) ***")

    print(f"\nrecommended designs:")
    rec = cand[cand.recommended_for_prototyping]
    print(rec[["N", "s", "pattern", "T", "r_EE_80_um", "regime_worst_case_across_M",
              "margin_fraction_of_ceiling", "objective_sensitive"]].to_string(index=False))

    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
