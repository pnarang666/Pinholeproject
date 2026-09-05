"""
Comparison runner: loads sweep_results_with_density.csv, applies the active gates
(gates.py), reports survivor counts, runs both metrics (metrics.py), and writes their
outputs as new CSVs. Produces CSVs only -- no plotting in this pass (that comes after
these results are inspected).

Run:  python3 run_comparison.py
      python3 run_comparison.py --gates ghost_safety,vignetting_safety
"""
import argparse
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_evaluation/comparison_metric/
sys.path.insert(0, HERE)
import gates  # noqa: E402
import metrics  # noqa: E402

EVAL_ROOT = os.path.dirname(HERE)  # array_evaluation/
LAB_ROOT = os.path.dirname(EVAL_ROOT)  # array_geometry_lab/
DEFAULT_IN_CSV = os.path.join(LAB_ROOT, "array_data", "theoretical_data",
                              "sweep_results_with_density.csv")
OUT_METRIC1_CSV = os.path.join(LAB_ROOT, "array_data", "evaluation_results",
                               "metric1_max_density_per_M.csv")
OUT_METRIC2_CSV = os.path.join(LAB_ROOT, "array_data", "evaluation_results",
                               "metric2_pareto_front_per_M.csv")


def preserve_legacy(path):
    """Standard project convention (see sweep/run_sweep.py's own preserve_legacy):
    copies path to path_legacyN.csv (auto-incrementing) before it gets overwritten,
    so nothing is ever silently lost. Added here (this script previously had no
    preservation at all for its own two output files) per this project's own
    'every overwritten file preserved first' requirement."""
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


def parse_args():
    p = argparse.ArgumentParser(description="Run the gated density-vs-safety-margin comparison.")
    p.add_argument("--gates", type=str, default=",".join(gates.DEFAULT_GATES),
                   help=f"comma-separated gate names to apply (default: "
                        f"{','.join(gates.DEFAULT_GATES)}). known gates: "
                        f"{','.join(sorted(gates.GATES.keys()))}")
    p.add_argument("--in_csv", type=str, default=DEFAULT_IN_CSV,
                   help="input CSV, must already have packing_density_per_area_um-2 "
                        "(run compute_density.py first if it doesn't)")
    return p.parse_args()


def report_survivor_counts(df, survivors):
    """Per-family, per-M survivor counts before vs after gating -- makes the
    'stochastic families get filtered out naturally by Gates 1/2' claim checkable
    directly from this printout, not just asserted."""
    print("\n--- survivor counts per family (before -> after gating, all M combined) ---")
    before = df.groupby("family").size()
    after = survivors.groupby("family").size().reindex(before.index, fill_value=0)
    for family in before.index:
        b, a = int(before[family]), int(after[family])
        pct = 100.0 * a / b if b else 0.0
        marker = "  <-- 0% survival" if a == 0 else ""
        print(f"  {family:25s} {b:5d} -> {a:5d}  ({pct:5.1f}%){marker}")

    print("\n--- survivor counts per family per M (after gating only; 'global' included) ---")
    after_by_m = survivors.groupby(["family", "M"]).size().unstack(fill_value=0)
    m_order = sorted(after_by_m.columns, key=lambda m: (m == "global", m))
    print(after_by_m[m_order].to_string())


def check_metric1_on_metric2_front(m1, m2):
    print("\n--- per-M summary: Metric 1 winner vs Metric 2 Pareto front ---")
    any_bug = False
    m_order = sorted(m1.M.unique(), key=lambda m: (m == "global", m))
    for M in m_order:
        m1_row = m1[m1.M == M]
        m2_front = m2[m2.M == M]
        if len(m1_row) == 0:
            print(f"  M={M}: no Metric-1 winner (no gate-surviving row has a defined density)")
            continue
        r = m1_row.iloc[0]
        r_seed = r.seed if pd.notna(r.seed) else -1.0
        on_front = ((m2_front.family == r.family) & (m2_front.N_requested == r.N_requested) &
                   (m2_front.spacing_params == r.spacing_params) &
                   (m2_front.seed.fillna(-1.0) == r_seed)).any()
        if on_front:
            flag = "OK -- also on Metric-2 front"
        else:
            flag = "*** BUG: Metric-1 winner NOT found on Metric-2's own front for this M ***"
            any_bug = True
        print(f"  M={M:>6s}: Metric1 winner = {r.family} (N_requested={int(r.N_requested)}, "
              f"spacing={r.spacing_params}, density={r[metrics.DENSITY_COL]:.4e})  |  "
              f"Metric2 front size = {len(m2_front)}  [{flag}]")
    if any_bug:
        print("\n*** WARNING: at least one Metric-1 winner is missing from Metric-2's own front for "
              "the same M. This should be impossible by construction -- nothing can have both higher "
              "density AND a tied-or-higher binding margin than the single highest-density survivor, "
              "since nothing has higher density at all. Investigate metrics.py before trusting either "
              "output CSV. ***")
    else:
        print("\nconsistency check passed: every Metric-1 winner is present on Metric-2's front for its M.")


def main():
    args = parse_args()
    gate_names = [g.strip() for g in args.gates.split(",") if g.strip()]

    df = pd.read_csv(args.in_csv)
    print(f"loaded {len(df)} rows from {args.in_csv}")
    print(f"active gates: {gate_names}")

    survivors = gates.apply_gates(df, gate_names)
    print(f"survivors after gating: {len(survivors)} / {len(df)} "
          f"({100.0 * len(survivors) / len(df):.1f}%)")

    report_survivor_counts(df, survivors)

    preserve_legacy(OUT_METRIC1_CSV)
    m1 = metrics.metric1_max_density(survivors)
    m1.to_csv(OUT_METRIC1_CSV, index=False)
    print(f"\nwrote {OUT_METRIC1_CSV} ({len(m1)} rows -- one per M)")

    preserve_legacy(OUT_METRIC2_CSV)
    m2 = metrics.metric2_pareto_front(survivors)
    m2.to_csv(OUT_METRIC2_CSV, index=False)
    print(f"wrote {OUT_METRIC2_CSV} ({len(m2)} rows -- full Pareto front, all M combined)")

    check_metric1_on_metric2_front(m1, m2)


if __name__ == "__main__":
    main()
