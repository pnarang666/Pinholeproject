"""
Part 4: sweeps every geometry family across N and its own spacing parameter(s),
evaluates ghost margin (both --scope modes) and vignetting robustness for each, and
writes ONE combined CSV (family column distinguishes rows) -- chosen over one-CSV-per-
family so cross-family ranking (compare/rank_by_family.py) doesn't need to re-join
files. Documented here per this folder's own "your choice, document it" instruction.

SCHEMA: family, N_requested, N_actual, spacing_params (compact "key=val;key=val" string,
since different families have different parameter sets), a_hole_um, M (float, or the
string 'global'), worst_case_ghost_margin, worst_case_vignetting_margin,
structurally_safe (bool: both margins > 0), n_active_pairs_phi0, n_active_holes_phi0,
total_illuminated_area_um2_phi0, min_illuminated_area_um2_across_phi.

AUDIT FIX (Defect B/1 -- gates rewarded blindness; Defect C/2 -- active-hole test was
a binary center-in-pupil test): n_active_pairs_phi0/n_active_holes_phi0 now come from
evaluation/active_pairs.py's TRUE partial-overlap test (thresholded at
--active_frac_threshold, default 0.5), not the old zero-radius-point test.
total_illuminated_area_um2_phi0 (continuous, never thresholded) and
min_illuminated_area_um2_across_phi (the worst-case across the WHOLE tested phi
range, and for --scope=global rows, across the tested M range too -- see
evaluate_candidate()'s own comment for that resolution) are the new columns Gate 3
(comparison_metric/gates.py::gate_viability) checks: a design that goes fully dark
at ANY tested phi (or, for global scope, at any tested (M, phi) pair) fails Gate 3,
closing the "opaque lens is the literal optimum" defect the old two gates alone
could not catch (both only tested for ABSENCE of ghosting, which zero illuminated
holes trivially satisfies).

--scope=global rows: geometry is generated ONCE per (family, N, spacing) using the
LARGEST a_hole(M) across the tested M range as the overlap-rejection constraint --
conservative, since a layout valid (non-overlapping) at the largest hole diameter is
automatically valid at every smaller one too. That single coordinate set is then
evaluated at every M via ghost_margin.evaluate_global(). See README.md for what the
resulting a_hole_um ambiguity means.

Every output CSV is legacy-preserved before being overwritten, matching this project's
existing convention (never silently overwrite a prior run's numbers).

Run:  python3 run_sweep.py --help
"""
import argparse
import itertools
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_calculation/sweep/
CALC_ROOT = os.path.abspath(os.path.join(HERE, ".."))  # array_calculation/
LAB_ROOT = os.path.abspath(os.path.join(CALC_ROOT, ".."))  # array_geometry_lab/
sys.path.insert(0, os.path.join(CALC_ROOT, "generators"))
sys.path.insert(0, os.path.join(CALC_ROOT, "margins"))  # renamed from "evaluation" --
                          # see array_calculation/README.md

import square, hexagonal, concentric, fibonacci_spiral, golden_angle  # noqa: E402
import rectangular, archimedean_spiral, ring_offset_concentric  # noqa: E402
import poisson_disk, jittered_lattice  # noqa: E402
import ghost_margin as gm  # noqa: E402
import vignetting_robustness as vr  # noqa: E402
import active_pairs as ap  # noqa: E402 -- only for DEFAULT_ACTIVE_FRAC_THRESHOLD's
                           # default value here; the actual pair-enumeration logic is
                           # called via gm/vr, not directly from this module.

STOCHASTIC_FAMILIES = {"poisson_disk", "jittered_lattice"}  # same (N, spacing) produces
                                                             # a DIFFERENT layout per
                                                             # call -- these need the
                                                             # seed loop in main() below,
                                                             # deterministic families do
                                                             # not.

DEFAULT_D_PUPIL_UM = 4000.0
DEFAULT_P0 = 60.0
DEFAULT_N_LIST = [20, 50, 100]
DEFAULT_LATTICE_SPACING_LIST = [700.0, 1000.0, 1500.0, 2000.0, 3000.0, 4000.0]
DEFAULT_CONCENTRIC_RING_SPACING_LIST = [700.0, 1000.0, 1500.0, 2000.0, 3000.0, 4000.0]
DEFAULT_CONCENTRIC_HOLES_PER_RING0_LIST = [6, 8]
DEFAULT_SPIRAL_C_LIST = [400.0, 700.0, 1000.0, 1500.0, 2000.0]
DEFAULT_RECTANGULAR_RATIO_LIST = [1.0, 1.5, 2.0]  # pitch_y_um = pitch_x_um * ratio;
                                                   # 1.0 reproduces square.py's own
                                                   # tested points exactly (see
                                                   # rectangular.py's docstring), 1.5
                                                   # and 2.0 are the requested
                                                   # asymmetric cases
DEFAULT_POISSON_SPACING_FACTOR_LIST = [1.2, 1.5, 2.0, 3.0]  # poisson_disk's only
                                                   # spacing-controlling parameter;
                                                   # spans ~2.5x min-to-max, comparable
                                                   # in spread to the other families'
                                                   # own spacing lists (e.g.
                                                   # lattice_spacing_list spans ~5.7x)
DEFAULT_JITTER_FRACTION_LIST = [0.0, 0.2, 0.4]  # covers the requested 0.0-0.4 range
                                                 # (endpoints + midpoint); trimmed from
                                                 # a finer grid to keep total sweep time
                                                 # reasonable once crossed with pitch,
                                                 # N, and NUM_SEEDS (see NUM_SEEDS'
                                                 # own justification below) -- 0.0 is
                                                 # included deliberately so the
                                                 # jitter_fraction=0 exact-reduction-to-
                                                 # hexagonal property is visible in the
                                                 # real sweep output too, not just the
                                                 # standalone spot-check
DEFAULT_NUM_SEEDS = 8  # JUSTIFICATION: this is a first, exploratory pass at stochastic
                       # families, not a final statistical claim. 8 independent seeds
                       # is enough that a single "lucky" seed is unlikely to dominate a
                       # worst-case-across-seeds summary by chance alone (catching a bad
                       # arrangement usually doesn't require many draws once one exists
                       # in the design's neighborhood), while keeping the added compute
                       # cost bounded -- stochastic families already multiply their own
                       # candidate count by NUM_SEEDS on top of every (N, spacing)
                       # combination tested. CLI-configurable via --num_seeds; increase
                       # it if a specific stochastic candidate's worst-case margin needs
                       # a tighter guarantee than this first pass provides.
DEFAULT_OUT_CSV = os.path.join(LAB_ROOT, "array_data", "theoretical_data", "sweep_results.csv")
_SPACING_STR_EXCLUDE_KEYS = {"ring_count_rule", "offset_rule"}  # descriptive-string
                                                                 # entries in
                                                                 # nominal_spacing_desc,
                                                                 # not numeric sweep
                                                                 # parameters -- excluded
                                                                 # from the compact CSV
                                                                 # column, not from the
                                                                 # metadata dict itself


def preserve_legacy(path):
    if not os.path.exists(path):
        return
    i = 1
    legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    while os.path.exists(legacy_path):
        i += 1
        legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    shutil.copy2(path, legacy_path)
    print(f"preserved predecessor -> {legacy_path}")


def spacing_str(d):
    return ";".join(f"{k}={v}" for k, v in d.items() if k not in _SPACING_STR_EXCLUDE_KEYS)


def candidates_for_family(family, N_list, args):
    """Yields (family_name, N, spacing_params_dict, generate_fn_kwargs) for every
    (N, spacing) combination requested for this family."""
    if family in ("square", "hexagonal"):
        gen = square.generate if family == "square" else hexagonal.generate
        for N, pitch in itertools.product(N_list, args.lattice_spacing_list):
            yield family, N, {"pitch_um": pitch}, gen
    elif family == "concentric":
        for N, rs, hpr0 in itertools.product(
                N_list, args.concentric_ring_spacing_list, args.concentric_holes_per_ring0_list):
            yield family, N, {"ring_spacing_um": rs, "holes_per_ring0": hpr0}, concentric.generate
    elif family in ("fibonacci_spiral", "golden_angle"):
        gen = fibonacci_spiral.generate if family == "fibonacci_spiral" else golden_angle.generate
        for N, c in itertools.product(N_list, args.spiral_c_list):
            yield family, N, {"c_um": c}, gen
    elif family == "rectangular":
        # pitch_x from the same list square.py's own pitch is drawn from; pitch_y =
        # pitch_x * ratio, ratio=1.0 included so this sweep contains square.py's exact
        # points too (as rectangular candidates, not deduplicated against them --
        # comparing "rectangular at ratio 1.0" against "square" directly in the
        # ranking is itself a live check that the two families agree there).
        for N, px, ratio in itertools.product(N_list, args.lattice_spacing_list, args.rectangular_ratio_list):
            yield family, N, {"pitch_x_um": px, "pitch_y_um": px * ratio}, rectangular.generate
    elif family == "archimedean_spiral":
        for N, c in itertools.product(N_list, args.spiral_c_list):
            yield family, N, {"c_um": c}, archimedean_spiral.generate
    elif family == "ring_offset_concentric":
        for N, rs, hpr0 in itertools.product(
                N_list, args.concentric_ring_spacing_list, args.concentric_holes_per_ring0_list):
            yield family, N, {"ring_spacing_um": rs, "holes_per_ring0": hpr0}, ring_offset_concentric.generate
    elif family == "poisson_disk":
        # spacing_params yielded here deliberately EXCLUDES seed -- main()'s own loop
        # adds the seed dimension for stochastic families, since seed is not a spacing
        # parameter and needs its own explicit CSV column, not folding into
        # spacing_params's compact string.
        for N, sf in itertools.product(N_list, args.poisson_spacing_factor_list):
            yield family, N, {"spacing_factor": sf}, poisson_disk.generate
    elif family == "jittered_lattice":
        for N, pitch, jf in itertools.product(
                N_list, args.lattice_spacing_list, args.jitter_fraction_list):
            yield family, N, {"pitch_um": pitch, "jitter_fraction": jf}, jittered_lattice.generate
    else:
        raise ValueError(f"unknown family {family}")


def evaluate_candidate(family, N, spacing_params, gen_fn, D_pupil_um, P0, M_values, seed=None,
                       active_frac_threshold=ap.DEFAULT_ACTIVE_FRAC_THRESHOLD):
    """Generates geometry, evaluates per_M (one row per M) and global (one row) ghost
    margin + vignetting robustness. Returns a list of result-row dicts.

    seed=None (deterministic families): every row's "seed" column is None/blank, and
    gen_fn is called without a seed kwarg, exactly as before this function supported
    stochastic families at all.
    seed=int (stochastic families): threaded into every gen_fn call for this candidate
    (so the SAME seed is used for every M's own geometry AND the global-scope geometry
    at this (N, spacing) point -- one seed = one full realization of the design,
    evaluated the same way a deterministic design would be), and recorded in every
    row's "seed" column so per-seed rows are never silently collapsed together.

    active_frac_threshold: threaded straight through to
    evaluation/active_pairs.py's thresholded active-hole test (Gate-1/ghost pair
    enumeration only) -- see that module's own DEFAULT_ACTIVE_FRAC_THRESHOLD comment
    for the modeling choice. The illuminated-area columns below are NEVER thresholded
    (see active_pairs.py's own docstring for why the two must stay separate)."""
    rows = []
    gen_kwargs = dict(spacing_params)
    if seed is not None:
        gen_kwargs["seed"] = seed

    # per_M rows: geometry regenerated at EACH M's own a_hole(M), since per_M scope is
    # explicitly "evaluate this design against only the single M it's associated with"
    # -- a genuinely different physical hole size per M, not one fixed layout.
    for M in M_values:
        a_hole_um = gm.load_acuity_optimal_aperture(M)
        coords, meta = gen_fn(N=N, a_hole_um=a_hole_um, **gen_kwargs)
        vig = vr.worst_case_across_phi(coords, D_pupil_um, M, a_hole_um, P0=P0,
                                       active_frac_threshold=active_frac_threshold)
        phi0 = next(r for r in vig["per_phi_breakdown"] if r["phi_deg"] == 0.0)
        ghost_margin_val = phi0["worst_case_margin"]
        rows.append({
            "family": family, "N_requested": N, "N_actual": meta["N_actual"],
            "spacing_params": spacing_str(spacing_params), "a_hole_um": a_hole_um,
            "seed": seed,
            "M": M, "worst_case_ghost_margin": ghost_margin_val,
            "worst_case_vignetting_margin": vig["worst_case_vignetting_margin"],
            "structurally_safe": bool(ghost_margin_val > 0 and vig["worst_case_vignetting_margin"] > 0),
            "n_active_pairs_phi0": phi0["n_active_pairs"], "n_active_holes_phi0": phi0["n_active_holes"],
            "total_illuminated_area_um2_phi0": phi0["total_illuminated_area_um2"],
            "min_illuminated_area_um2_across_phi": vig["min_illuminated_area_um2_across_phi"],
        })

    # global row: ONE geometry, generated at the LARGEST a_hole(M) across M_values (the
    # most conservative overlap constraint -- valid at every smaller a_hole too).
    a_hole_values = {M: gm.load_acuity_optimal_aperture(M) for M in M_values}
    a_hole_for_global = max(a_hole_values.values())
    coords_g, meta_g = gen_fn(N=N, a_hole_um=a_hole_for_global, **gen_kwargs)
    glob = gm.evaluate_global(coords_g, D_pupil_um, M_values=M_values, P0=P0)

    # vignetting robustness under global scope: worst across phi AND across M, using
    # the same fixed geometry -- computed ONCE per M here (not inside a throwaway
    # generator expression) so the illuminated-area figures below are extracted from
    # the SAME calls, not a second, redundant phi-sweep.
    per_m_vig_results = [
        vr.worst_case_across_phi(coords_g, D_pupil_um, M, a_hole_for_global, P0=P0,
                                 active_frac_threshold=active_frac_threshold)
        for M in M_values]
    worst_vig_global = min(r["worst_case_vignetting_margin"] for r in per_m_vig_results)

    # AUDIT FIX (Defect B/1's "228 NaN global-scope rows, viability never checked in
    # either direction"): global scope's own semantics (evaluated across BOTH phi AND
    # M, per evaluate_global()'s own docstring) make a single unambiguous "phi=0"
    # value ill-defined the way it is for per_M rows -- resolved here explicitly,
    # not left as NaN:
    #   - total_illuminated_area_um2_phi0 for a global row = the WORST (minimum)
    #     illuminated area AT phi=0 SPECIFICALLY, across the tested M range -- the
    #     phi=0 analogue of the "worst case across phi" convention already used for
    #     worst_case_vignetting_margin's own global-scope value above.
    #   - min_illuminated_area_um2_across_phi for a global row = the WORST across
    #     BOTH phi AND M jointly -- exactly analogous to worst_vig_global's own
    #     "worst across phi AND M" framing, and the number Gate 3 actually gates on.
    # Both are now real, non-NaN numbers for every global row.
    min_illum_area_global_all_phi_and_M = min(
        r["min_illuminated_area_um2_across_phi"] for r in per_m_vig_results)
    illum_area_phi0_per_m = [
        next(p for p in r["per_phi_breakdown"] if p["phi_deg"] == 0.0)["total_illuminated_area_um2"]
        for r in per_m_vig_results]
    worst_illum_area_phi0_global = min(illum_area_phi0_per_m)

    rows.append({
        "family": family, "N_requested": N, "N_actual": meta_g["N_actual"],
        "spacing_params": spacing_str(spacing_params), "a_hole_um": a_hole_for_global,
        "seed": seed,
        "M": "global", "worst_case_ghost_margin": glob["worst_case_margin"],
        "worst_case_vignetting_margin": worst_vig_global,
        "structurally_safe": bool(glob["worst_case_margin"] > 0 and worst_vig_global > 0),
        "n_active_pairs_phi0": None, "n_active_holes_phi0": None,
        "total_illuminated_area_um2_phi0": worst_illum_area_phi0_global,
        "min_illuminated_area_um2_across_phi": min_illum_area_global_all_phi_and_M,
    })
    return rows


def main():
    ap_ = argparse.ArgumentParser(description=__doc__)
    ap_.add_argument("--families", type=str,
                     default="square,hexagonal,concentric,fibonacci_spiral,golden_angle,"
                             "rectangular,archimedean_spiral,ring_offset_concentric,"
                             "poisson_disk,jittered_lattice")
    ap_.add_argument("--N_list", type=str, default=",".join(str(n) for n in DEFAULT_N_LIST))
    ap_.add_argument("--lattice_spacing_list", type=str,
                     default=",".join(str(x) for x in DEFAULT_LATTICE_SPACING_LIST))
    ap_.add_argument("--concentric_ring_spacing_list", type=str,
                     default=",".join(str(x) for x in DEFAULT_CONCENTRIC_RING_SPACING_LIST))
    ap_.add_argument("--concentric_holes_per_ring0_list", type=str,
                     default=",".join(str(x) for x in DEFAULT_CONCENTRIC_HOLES_PER_RING0_LIST))
    ap_.add_argument("--spiral_c_list", type=str,
                     default=",".join(str(x) for x in DEFAULT_SPIRAL_C_LIST))
    ap_.add_argument("--rectangular_ratio_list", type=str,
                     default=",".join(str(x) for x in DEFAULT_RECTANGULAR_RATIO_LIST))
    ap_.add_argument("--poisson_spacing_factor_list", type=str,
                     default=",".join(str(x) for x in DEFAULT_POISSON_SPACING_FACTOR_LIST))
    ap_.add_argument("--jitter_fraction_list", type=str,
                     default=",".join(str(x) for x in DEFAULT_JITTER_FRACTION_LIST))
    ap_.add_argument("--num_seeds", type=int, default=DEFAULT_NUM_SEEDS,
                     help="seeds 0..num_seeds-1 tested per (N, spacing) point for "
                          "STOCHASTIC families only (poisson_disk, jittered_lattice); "
                          "ignored for deterministic families. See DEFAULT_NUM_SEEDS "
                          "comment for why 8 is the default.")
    ap_.add_argument("--D_pupil_um", type=float, default=DEFAULT_D_PUPIL_UM)
    ap_.add_argument("--P0", type=float, default=DEFAULT_P0)
    ap_.add_argument("--out_csv", type=str, default=DEFAULT_OUT_CSV)
    ap_.add_argument("--active_frac_threshold", type=float, default=ap.DEFAULT_ACTIVE_FRAC_THRESHOLD,
                     help="fraction of a hole's own area that must overlap the pupil for "
                          "it to count as 'active' in pairwise ghost enumeration (Gate 1). "
                          "See evaluation/active_pairs.py's own DEFAULT_ACTIVE_FRAC_THRESHOLD "
                          "comment for why 0.5 is the default -- a modeling choice, not a "
                          "physical constant. Does NOT affect the illuminated-area columns "
                          "Gate 3 (viability) uses, which are never thresholded.")
    args = ap_.parse_args()
    args.lattice_spacing_list = [float(x) for x in args.lattice_spacing_list.split(",")]
    args.concentric_ring_spacing_list = [float(x) for x in args.concentric_ring_spacing_list.split(",")]
    args.concentric_holes_per_ring0_list = [int(x) for x in args.concentric_holes_per_ring0_list.split(",")]
    args.spiral_c_list = [float(x) for x in args.spiral_c_list.split(",")]
    args.rectangular_ratio_list = [float(x) for x in args.rectangular_ratio_list.split(",")]
    args.poisson_spacing_factor_list = [float(x) for x in args.poisson_spacing_factor_list.split(",")]
    args.jitter_fraction_list = [float(x) for x in args.jitter_fraction_list.split(",")]
    N_list = [int(x) for x in args.N_list.split(",")]
    families = args.families.split(",")

    M_values = sorted(pd.read_csv(gm.PER_M_OPTIMUM_MAP_CSV).M_diopters.unique().tolist())
    print(f"M values (read live from per_M_optimum_map.csv): {M_values}")
    print(f"num_seeds for stochastic families: {args.num_seeds}")

    t0 = time.time()
    all_rows = []
    n_candidates = 0
    n_seed_runs = 0
    for family in families:
        for fam, N, spacing_params, gen_fn in candidates_for_family(family, N_list, args):
            n_candidates += 1
            if fam in STOCHASTIC_FAMILIES:
                for seed in range(args.num_seeds):
                    n_seed_runs += 1
                    rows = evaluate_candidate(fam, N, spacing_params, gen_fn, args.D_pupil_um,
                                              args.P0, M_values, seed=seed,
                                              active_frac_threshold=args.active_frac_threshold)
                    all_rows.extend(rows)
            else:
                rows = evaluate_candidate(fam, N, spacing_params, gen_fn, args.D_pupil_um,
                                          args.P0, M_values, seed=None,
                                          active_frac_threshold=args.active_frac_threshold)
                all_rows.extend(rows)
        print(f"  {family}: done ({time.time()-t0:.1f}s elapsed)")

    df = pd.DataFrame(all_rows)
    preserve_legacy(args.out_csv)
    df.to_csv(args.out_csv, index=False)
    print(f"\n{n_candidates} candidate (family, N, spacing) points "
          f"({n_seed_runs} of those are stochastic seed-runs, {args.num_seeds} seeds each), "
          f"{len(df)} rows ({len(M_values)} per_M + 1 global per candidate-or-seed-run)")
    print(f"wrote {args.out_csv}")

    n_safe = int(df.structurally_safe.sum())
    print(f"structurally_safe=True: {n_safe}/{len(df)} rows")
    for family in families:
        sub = df[df.family == family]
        n_safe_f = int(sub.structurally_safe.sum())
        print(f"  {family}: {n_safe_f}/{len(sub)} rows structurally safe"
              f"{'  *** ZERO SAFE CANDIDATES ***' if n_safe_f == 0 else ''}")


if __name__ == "__main__":
    main()
