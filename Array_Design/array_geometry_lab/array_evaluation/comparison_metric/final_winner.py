"""
final_winner.py -- the final, narrowed-scope winner search: square/hexagonal/
rectangular families ONLY, gated by the now margin-aware gates.py (see that
module's own "AUDIT FIX (margin-vs-zero -> margin-vs-real-threshold)" docstring
section for why >0 was replaced with a real, sourced threshold), ranked by the
SAME metrics.metric1_max_density() this project has always used (unmodified --
this script adds no new ranking criterion, only narrows the candidate set and
uses the already-updated gates).

WHY square/hexagonal/rectangular only: every prior "winner" that turned out to be
a boundary case came from a family with either zero structural constraint
(blackout designs, infinite margin from zero active pairs) or a near-miss sitting
right at the old >0 line. square/hexagonal/rectangular are this project's three
regular-lattice families with a well-defined, non-degenerate closed-form packing
geometry (see gates.py's own viability threshold, which uses exactly this
project's a_hole_um/pi*R_h^2 geometry) -- the families this final answer is
actually built on. The other 7 families' theoretical data is NOT deleted or
altered anywhere (sweep_results_with_density.csv, paper_score outputs,
metric1/metric2, family_ranking.csv all still cover all 10 families for
reporting/comparison) -- they are excluded ONLY from this specific final ranking
step, per this task's own instruction.

LAYER 2 (array_evaluation/): reads array_data/theoretical_data/
sweep_results_with_density.csv (read-only) and imports gates.py/metrics.py --
sibling array_evaluation/ modules, both used exactly as they already exist
(metrics.py untouched by this task; gates.py's thresholds were updated in place,
per this task's own instruction, not duplicated here). No array_calculation/
import (enforced by ../check_no_calculation_imports.py).

Run:  python3 final_winner.py
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_evaluation/comparison_metric/
sys.path.insert(0, HERE)
import gates  # noqa: E402
import metrics  # noqa: E402

EVAL_ROOT = os.path.dirname(HERE)  # array_evaluation/
LAB_ROOT = os.path.dirname(EVAL_ROOT)  # array_geometry_lab/
DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
EVAL_OUT_DIR = os.path.join(LAB_ROOT, "array_data", "evaluation_results")

IN_CSV = os.path.join(DATA_DIR, "sweep_results_with_density.csv")
OUT_CSV = os.path.join(EVAL_OUT_DIR, "FINAL_WINNER_PER_M.csv")

FINAL_FAMILIES = ["square", "hexagonal", "rectangular"]


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


def add_margin_audit_columns(df):
    """Attaches the actual value, the required threshold, and the headroom
    (actual - threshold) for all three gated quantities, using gates.py's own
    threshold functions directly (not re-derived here) -- so a winner's margin is
    visible and auditable, not just its pass/fail bit."""
    df = df.copy()
    df["ghost_margin_actual"] = df["worst_case_ghost_margin"]
    df["ghost_margin_threshold"] = gates.ghost_margin_threshold(df)
    df["ghost_margin_headroom"] = df["ghost_margin_actual"] - df["ghost_margin_threshold"]

    df["vignetting_margin_actual"] = df["worst_case_vignetting_margin"]
    df["vignetting_margin_threshold"] = gates.ghost_margin_threshold(df)
    df["vignetting_margin_headroom"] = df["vignetting_margin_actual"] - df["vignetting_margin_threshold"]

    df["illuminated_area_actual_um2"] = df["min_illuminated_area_um2_across_phi"]
    df["illuminated_area_threshold_um2"] = gates.viability_area_threshold(df)
    df["illuminated_area_headroom_um2"] = (df["illuminated_area_actual_um2"] -
                                           df["illuminated_area_threshold_um2"])
    return df


def main():
    df = pd.read_csv(IN_CSV, dtype={"M": str})
    print(f"loaded {len(df)} rows from {IN_CSV} (all {df.family.nunique()} families)")

    narrowed = df[df.family.isin(FINAL_FAMILIES)].copy()
    print(f"narrowed to {FINAL_FAMILIES}: {len(narrowed)}/{len(df)} rows "
          f"(other families' data untouched in theoretical_data/evaluation_results, "
          f"excluded from this ranking only)")

    survivors = gates.apply_gates(narrowed, gates.DEFAULT_GATES)
    print(f"survivors after margin-aware gating: {len(survivors)}/{len(narrowed)} "
          f"({100.0 * len(survivors) / len(narrowed):.1f}%)")
    print(survivors.groupby(["family", "M"]).size().unstack(fill_value=0)
          [sorted(survivors.M.unique(), key=m_sort_key)].to_string())

    winners = metrics.metric1_max_density(survivors)
    winners = add_margin_audit_columns(winners)
    winners = winners.sort_values(by="M", key=lambda col: col.map(m_sort_key)).reset_index(drop=True)

    preserve_legacy(OUT_CSV)
    winners.to_csv(OUT_CSV, index=False)
    print(f"\nwrote {OUT_CSV} ({len(winners)} rows -- one per M, square/hexagonal/"
          f"rectangular only, margin-aware gates)")

    print("\n--- final winner per M, with margin headroom ---")
    cols = ["M", "family", "N_requested", "N_actual", "spacing_params",
           "ghost_margin_actual", "ghost_margin_threshold", "ghost_margin_headroom",
           "vignetting_margin_actual", "vignetting_margin_threshold", "vignetting_margin_headroom",
           "illuminated_area_actual_um2", "illuminated_area_threshold_um2", "illuminated_area_headroom_um2"]
    print(winners[cols].to_string(index=False))


if __name__ == "__main__":
    main()
