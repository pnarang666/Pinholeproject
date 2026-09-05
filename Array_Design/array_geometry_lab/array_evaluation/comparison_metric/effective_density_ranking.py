"""
effective_density_ranking.py -- a NEW ranking script (does not edit gates.py or
metrics.py) built on the CONFIRMED FINDING that every prior margin-aware winner
has exactly ONE active hole at phi=0: packing_density_per_area_um-2 (N_actual /
hull_area) counts every generated hole, including ones that structurally never
admit any light -- for the winning designs, that is most of them. This script
replaces the RANKING OBJECTIVE with effective_density = n_active_holes_phi0 /
hull_area (only holes that actually admit light), while KEEPING
packing_density_per_area_um-2 in the output untouched, for direct comparison --
per this task's own explicit instruction, nothing is deleted.

hull_area is not a stored column -- it is recovered algebraically from two
EXISTING columns already in theoretical_data: hull_area = N_actual /
packing_density_per_area_um-2 (the exact definition compute_density.py's own
docstring states). So effective_density = n_active_holes_phi0 *
packing_density_per_area_um-2 / N_actual -- pure arithmetic on existing columns,
no new geometry computed here.

blind_rate is read straight from array_calculation/compute_coverage_metrics.py's
output (a NEW array_calculation file, itself not editing sweep/run_sweep.py or
compute_density.py) and reported as a ranking-adjacent column (lower better),
per this task's own instruction -- NOT folded into effective_density itself,
kept as its own separate, auditable number.

GATING: reuses gates.py's own threshold FUNCTIONS (ghost_margin_threshold,
viability_area_threshold -- the exact sourced, justified numbers from that
module's own "AUDIT FIX (margin-vs-zero -> margin-vs-real-threshold)" docstring
section) unmodified, via import, not duplicated. Applied here to
ghost_margin_c_min_floored / vignetting_margin_c_min_floored (compute_
coverage_metrics.py's own columns) instead of gates.py's own
gate_ghost_safety/gate_vignetting_safety (which read worst_case_ghost_margin /
worst_case_vignetting_margin, the optical-only originals) -- this is a NEW gate
check, not an edit to the existing one, because this task is specifically about
testing ranking under a DIFFERENT (c_min-floored) margin definition, which
gates.py's own functions have no parameter for. viability uses the SAME
min_illuminated_area_um2_across_phi column either way (task 2's c_min floor is a
ghost/vignetting-only concept, not a viability one).

LAYER 2 (array_evaluation/): reads array_data/theoretical_data/ (the coverage
CSVs compute_coverage_metrics.py wrote) read-only. Imports gates.py -- a sibling
array_evaluation/ module -- for its threshold functions/constants only, never
gate_* wrapper functions (which reference the wrong margin columns for this
task), never metrics.py or array_calculation/. check_no_calculation_imports.py
must still pass.

SEED-AWARE RANKING FOR STOCHASTIC FAMILIES (poisson_disk, jittered_lattice --
this project's own established STOCHASTIC_FAMILIES set, see
compare/rank_by_family.py): previously each seed was ranked as an independent
candidate row, so a design could win purely by having one lucky seed clear the
margin gates while most of its other seeds did not (CONFIRMED: poisson_disk,
M=1.0, seed=7 -- only 2 of 8 tested seeds at the same (N, spacing_params)
actually passed both floored margins). Fixed in
aggregate_stochastic_groups()/build_winner_per_M_seed_aware(): stochastic
candidates are now grouped by (family, N_requested, spacing_params, M),
eligible only if the WORST (minimum) seed clears both floored margins, and
ranked by MEAN effective_density across seeds that also pass the full
row-level gate (including viability). Deterministic families are unaffected --
gated and ranked per row exactly as before.

Run:  python3 effective_density_ranking.py --c_min_um 0
      python3 effective_density_ranking.py --c_min_um 55
"""
import argparse
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_evaluation/comparison_metric/
sys.path.insert(0, HERE)
import gates  # noqa: E402 -- sibling array_evaluation/ module; only its threshold
              # functions/constants are used, gate_* wrappers are not (see module
              # docstring: those read the wrong margin columns for this task).

EVAL_ROOT = os.path.dirname(HERE)  # array_evaluation/
LAB_ROOT = os.path.dirname(EVAL_ROOT)  # array_geometry_lab/
DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
EVAL_OUT_DIR = os.path.join(LAB_ROOT, "array_data", "evaluation_results")

DENSITY_COL = "packing_density_per_area_um-2"


def preserve_legacy(path):
    """Standard project convention (see array_calculation/sweep/run_sweep.py's own
    preserve_legacy): copies path to path_legacyN.csv (auto-incrementing) before it
    gets overwritten, so nothing is ever silently lost."""
    if not os.path.exists(path):
        return
    import shutil
    i = 1
    legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    while os.path.exists(legacy_path):
        i += 1
        legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    shutil.copy2(path, legacy_path)
    print(f"preserved predecessor -> {legacy_path}")


def m_sort_key(m):
    return (m == "global", m)


def add_effective_density(df):
    """No join/merge happens anywhere in this module -- effective_density is
    pure arithmetic on two columns already present on each row (see module
    docstring). Investigated 2026-08 after a report of a winning row showing
    effective_density==0.0: confirmed via direct scalar access (not print()/
    .T, which coerce a single row's mixed dtypes to a common 'object' dtype
    and can DISPLAY a tiny float as '0.0' without altering the stored value --
    a pandas repr artifact, reproduced with a minimal 2-row example) that the
    stored value was never actually zero. The assertion below is a permanent
    defensive check regardless -- if a genuine zero-density active-hole row
    ever does appear (e.g. a future upstream change divides by an unguarded
    zero), stop here rather than silently ranking on it."""
    df = df.copy()
    hull_area_um2 = df["N_actual"] / df[DENSITY_COL]
    df["effective_density_per_area_um-2"] = df["n_active_holes_phi0"] / hull_area_um2

    bad = df[(df["n_active_holes_phi0"] >= 1) & (df["effective_density_per_area_um-2"] == 0.0)]
    assert len(bad) == 0, (
        f"{len(bad)} row(s) have n_active_holes_phi0>=1 but "
        f"effective_density_per_area_um-2==0.0 -- a real zero-density bug, not "
        f"the print()/.T display artifact this check exists to guard against. "
        f"Offending rows (family, N_requested, spacing_params, seed, M):\n"
        f"{bad[['family', 'N_requested', 'spacing_params', 'seed', 'M']].to_string()}")
    return df


def row_gate_mask(df, c_min_um):
    """Same three checks as gates.py's DEFAULT_GATES, same sourced CONSTANTS
    (gates.MARGIN_SAFETY_MULTIPLE, gates.GHOST_DELTA_R_UNCERTAINTY_UM,
    gates.viability_area_threshold -- reused via import, not duplicated), but
    ghost/vignetting compare against THIS row's c_min-floored margin columns.
    Returns a boolean mask (not a filtered df) so it can be reused both for
    deterministic-family row-level filtering AND for per-seed pass/fail
    determination within a stochastic-family group (see
    build_winner_per_M_seed_aware()).

    IMPORTANT: the required THRESHOLD's own denominator must be floored the
    SAME way the margin itself was (max(resolvable_blur_um, c_min_um)), not
    left as gates.py's own optical-only resolvable_blur_um -- both margin and
    threshold are ratios over the same resolvable scale, and comparing a
    floored margin against an un-floored threshold would silently compare two
    different scales. This is why gates.py's own gate_ghost_safety/
    gate_vignetting_safety/ghost_margin_threshold are not called directly here
    (see module docstring)."""
    floored_c_tot = df["resolvable_blur_um"].clip(lower=c_min_um)
    ghost_thresh = gates.MARGIN_SAFETY_MULTIPLE * gates.GHOST_DELTA_R_UNCERTAINTY_UM / floored_c_tot
    vign_thresh = ghost_thresh  # identical formula, same source -- see gates.py docstring
    viability_thresh = gates.viability_area_threshold(df)
    return ((df["ghost_margin_c_min_floored"] >= ghost_thresh) &
            (df["vignetting_margin_c_min_floored"] >= vign_thresh) &
            (df["min_illuminated_area_um2_across_phi"] >= viability_thresh))


def apply_c_min_gates(df, c_min_um):
    return df[row_gate_mask(df, c_min_um)]


# Same set this project's own compare/rank_by_family.py already established for
# its own worst-case-across-seeds aggregation -- reused, not redefined.
STOCHASTIC_FAMILIES = {"poisson_disk", "jittered_lattice"}


def aggregate_stochastic_groups(sto_df, c_min_um):
    """CONFIRMED FINDING this function exists to fix: effective_density_ranking.py
    previously ranked each stochastic-family SEED as an independent candidate row,
    so a design could win by having exactly one lucky seed clear the margin gates
    while most of its other seeds did not (poisson_disk, M=1.0, seed=7: passed:
    only 2 of 8 tested seeds at the same (N, spacing) actually passed both floored
    margins). Matches this project's own established worst-case-across-seeds
    convention (compare/rank_by_family.py's aggregate_stochastic()), applied here
    at the (family, N_requested, spacing_params, M) level (M included in the
    group key, unlike rank_by_family.py, since eligibility is margin-based and
    margins are M-dependent).

    ELIGIBILITY (per this task's own explicit definition): a group is eligible
    only if BOTH margins' WORST case (minimum) across every tested seed is
    positive -- i.e. every single seed clears both floored margins, not just a
    majority. Viability (Gate 3) is not part of the task's eligibility
    definition, but IS still required per seed for a seed to count toward the
    ranked density (see 'passing seeds' below) -- dropping it would reopen the
    exact 'opaque lens' blind-spot this project's gates.py was built to close,
    for stochastic families only.

    RANKED VALUE: mean effective_density_per_area_um-2 across 'passing seeds' --
    seeds that ALSO clear the full row-level 3-gate check (ghost, vignetting,
    viability). For an eligible group this is normally every tested seed (since
    eligibility already requires both margins positive for the worst seed), MINUS
    any seed that specifically fails viability -- logged, not silently dropped."""
    rows = []
    key_cols = ["family", "N_requested", "spacing_params", "M"]
    for key, group in sto_df.groupby(key_cols, dropna=False):
        worst_ghost = float(group["ghost_margin_c_min_floored"].min())
        worst_vign = float(group["vignetting_margin_c_min_floored"].min())
        eligible = (worst_ghost > 0.0) and (worst_vign > 0.0)
        if not eligible:
            continue

        passing_mask = row_gate_mask(group, c_min_um)
        passing = group[passing_mask]
        n_seeds_tested = len(group)
        n_seeds_passing = len(passing)
        if n_seeds_passing == 0:
            print(f"  NOTE: group {dict(zip(key_cols, key))} is margin-eligible "
                  f"(worst ghost={worst_ghost:.4f}, worst vign={worst_vign:.4f}) but "
                  f"every one of its {n_seeds_tested} seeds fails viability -- "
                  f"excluded from ranking, not silently averaged over zero seeds.")
            continue

        row = group.iloc[0].copy()  # non-seed-dependent fields (family,
                                     # N_requested, spacing_params, a_hole_um, M)
                                     # are identical across every seed in this
                                     # group by construction -- exact, not
                                     # approximate.
        row["seed"] = None  # this row now represents an aggregate across seeds
        row["N_actual"] = int(passing["N_actual"].min())  # worst-case-first,
                                                            # same convention as
                                                            # rank_by_family.py's
                                                            # own N_actual
                                                            # aggregation
        row["n_active_holes_phi0"] = float(passing["n_active_holes_phi0"].mean())
        row["blind_rate"] = float(passing["blind_rate"].mean())
        row[DENSITY_COL] = float(passing[DENSITY_COL].mean())
        row["effective_density_per_area_um-2"] = float(passing["effective_density_per_area_um-2"].mean())
        row["n_seeds_tested"] = n_seeds_tested
        row["n_seeds_passing"] = n_seeds_passing
        row["worst_ghost_margin_c_min_floored_across_seeds"] = worst_ghost
        row["worst_vignetting_margin_c_min_floored_across_seeds"] = worst_vign
        rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=sto_df.columns)


def build_winner_per_M_seed_aware(df, c_min_um):
    """Deterministic-family rows: unaffected -- gated and ranked individually,
    exactly as before (single 'seed' trivially, per this task's own
    instruction). Stochastic-family rows: aggregated by
    aggregate_stochastic_groups() BEFORE ranking, so a lucky single seed can
    never win on its own. The two pools are combined and ranked together per M
    -- effective_density_per_area_um-2 is directly comparable either way (a
    real value per row vs. a mean-over-passing-seeds value per group)."""
    is_stochastic = df.family.isin(STOCHASTIC_FAMILIES)
    det_df = df[~is_stochastic]
    sto_df = df[is_stochastic]

    det_survivors = det_df[row_gate_mask(det_df, c_min_um)].copy()
    det_survivors["n_seeds_tested"] = 1
    det_survivors["n_seeds_passing"] = 1
    det_survivors["worst_ghost_margin_c_min_floored_across_seeds"] = det_survivors["ghost_margin_c_min_floored"]
    det_survivors["worst_vignetting_margin_c_min_floored_across_seeds"] = det_survivors["vignetting_margin_c_min_floored"]

    print(f"\n--- aggregating {len(sto_df)} stochastic-family rows "
          f"({sorted(STOCHASTIC_FAMILIES)}) into (family, N_requested, spacing_params, M) groups ---")
    sto_groups = aggregate_stochastic_groups(sto_df, c_min_um)
    print(f"  {sto_df.groupby(['family', 'N_requested', 'spacing_params', 'M']).ngroups} stochastic "
          f"groups total -> {len(sto_groups)} margin-eligible (worst seed positive on both floored margins)")

    combined = pd.concat([det_survivors, sto_groups], ignore_index=True) if len(sto_groups) else det_survivors

    winners = []
    for M, group in combined.groupby("M"):
        sub = group.dropna(subset=["effective_density_per_area_um-2"])
        if len(sub) == 0:
            continue
        best = sub.loc[sub["effective_density_per_area_um-2"].idxmax()].copy()
        winners.append(best)
    out = pd.DataFrame(winners).reset_index(drop=True)
    out = out.sort_values(by="M", key=lambda col: col.map(m_sort_key)).reset_index(drop=True)
    return out


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--c_min_um", type=float, required=True,
                   help="which coverage CSV to read: "
                        "array_data/theoretical_data/sweep_results_with_coverage_cmin{int}.csv")
    return p.parse_args()


def main():
    args = parse_args()
    in_csv = os.path.join(DATA_DIR, f"sweep_results_with_coverage_cmin{int(args.c_min_um)}.csv")
    out_csv = os.path.join(EVAL_OUT_DIR, f"effective_density_winner_per_M_cmin{int(args.c_min_um)}.csv")

    df = pd.read_csv(in_csv, dtype={"M": str})
    print(f"loaded {len(df)} rows from {in_csv}")

    df = add_effective_density(df)
    print(f"\n--- effective_density vs old packing_density, whole dataset ---")
    print(f"  old {DENSITY_COL}: mean={df[DENSITY_COL].mean():.4e}")
    print(f"  new effective_density_per_area_um-2: mean={df['effective_density_per_area_um-2'].mean():.4e}")
    ratio = (df["effective_density_per_area_um-2"] / df[DENSITY_COL]).mean()
    print(f"  mean ratio (effective/old) = {ratio:.4f} "
          f"(1.0 would mean every hole is always active; this dataset's actual ratio "
          f"reflects how much of the old density metric was counting dark holes)")

    winners = build_winner_per_M_seed_aware(df, args.c_min_um)
    preserve_legacy(out_csv)
    winners.to_csv(out_csv, index=False)
    print(f"\nwrote {out_csv} ({len(winners)} rows -- one per M, ranked by effective_density, "
          f"stochastic families aggregated worst-case-across-seeds)")

    print(f"\n--- winner per M (c_min_um={args.c_min_um}), effective density vs old density ---")
    cols = ["M", "family", "N_requested", "N_actual", "spacing_params", "n_active_holes_phi0",
           "blind_rate", DENSITY_COL, "effective_density_per_area_um-2",
           "n_seeds_tested", "n_seeds_passing"]
    print(winners[cols].to_string(index=False))


if __name__ == "__main__":
    main()
