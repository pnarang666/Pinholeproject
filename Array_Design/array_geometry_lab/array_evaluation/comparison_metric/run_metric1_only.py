"""
Re-runs gates.py + metrics.py's Metric 1 ONLY (not Metric 2's Pareto front) across
the full, rotation-inclusive dataset -- written for the rotation-gap task, which
explicitly does not need Metric 2 for its specific question ("does any rotated
square/hexagonal/rectangular candidate beat jittered_lattice's current winning
density"). Reuses gates.apply_gates() and metrics.metric1_max_density() directly
(imported, not duplicated) -- this script is pure orchestration, no gate or metric
logic lives here.

Deliberately does NOT touch metric2_pareto_front_per_M.csv -- recomputing an unused
Pareto front would be scope creep past what this task asked for, and this dataset
change (adding rotation, a new degenerate-value axis for square/hexagonal/
rectangular) doesn't invalidate the existing Metric 2 file for any other purpose.

Run:  python3 run_metric1_only.py
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
IN_CSV = os.path.join(LAB_ROOT, "array_data", "theoretical_data",
                      "sweep_results_with_density.csv")
OUT_CSV = os.path.join(LAB_ROOT, "array_data", "evaluation_results",
                       "metric1_max_density_per_M.csv")


def main():
    df = pd.read_csv(IN_CSV)
    print(f"loaded {len(df)} rows from {IN_CSV}")
    print(f"active gates: {gates.DEFAULT_GATES}")

    survivors = gates.apply_gates(df)
    print(f"survivors after gating: {len(survivors)} / {len(df)} "
          f"({100.0 * len(survivors) / len(df):.1f}%)")

    print("\n--- survivor counts per family (before -> after gating) ---")
    before = df.groupby("family").size()
    after = survivors.groupby("family").size().reindex(before.index, fill_value=0)
    for family in before.index:
        b, a = int(before[family]), int(after[family])
        pct = 100.0 * a / b if b else 0.0
        print(f"  {family:25s} {b:5d} -> {a:5d}  ({pct:5.1f}%)")

    m1 = metrics.metric1_max_density(survivors)
    m1.to_csv(OUT_CSV, index=False)
    print(f"\nwrote {OUT_CSV} ({len(m1)} rows -- one per M)")
    print(m1[["M", "family", "N_requested", "spacing_params",
             "packing_density_per_area_um-2"]].to_string())


if __name__ == "__main__":
    main()
