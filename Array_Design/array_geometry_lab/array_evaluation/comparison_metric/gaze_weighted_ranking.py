"""
gaze_weighted_ranking.py -- a NEW, PARALLEL ranking, additive only. Does not
replace or modify the existing worst-case metrics (gates.py,
effective_density_ranking.py, metrics.py) -- those stay exactly as they are,
still reported, still the project's own primary ranking. Reads
array_calculation/compute_gaze_weighted_metrics.py's own output (a NEW
array_calculation file, itself additive) read-only.

RANKING RULE, AS GIVEN, implemented literally, not redesigned: rank
candidates by time_weighted_ghost_pct ASCENDING (lower is better), tie-break
on time_weighted_blind_pct ASCENDING. No gate is applied here -- this task
did not specify one, unlike effective_density_ranking.py's own margin-aware
gates.

HONESTLY FLAGGED, NOT SILENTLY FIXED: a literal ascending-ghost-then-blind
sort has the same theoretical "rewards blindness" failure mode this project's
own gates.py already found and closed once for the worst-case metric (a
design with ZERO holes illuminated anywhere has time_weighted_ghost_pct=0%
by construction -- nothing to ghost -- and would rank ABOVE a real,
mostly-safe design with e.g. ghost_pct=0.1%, even though the zero-hole design
is not viable at all). This script does not add a viability gate to
"fix" this, since the task's own ranking rule is stated exactly as above --
GAZE_WEIGHTED_COMPARISON.md checks the actual winners for this pattern
directly and reports honestly if it appears, rather than silently
special-casing it away.

LAYER 2 (array_evaluation/): reads array_data/theoretical_data/ (the gaze CSV
array_calculation wrote) read-only. Imports nothing from array_calculation/.
check_no_calculation_imports.py must still pass.

Run:  python3 gaze_weighted_ranking.py
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_evaluation/comparison_metric/
EVAL_ROOT = os.path.dirname(HERE)  # array_evaluation/
LAB_ROOT = os.path.dirname(EVAL_ROOT)  # array_geometry_lab/
DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
EVAL_OUT_DIR = os.path.join(LAB_ROOT, "array_data", "evaluation_results")

IN_CSV = os.path.join(DATA_DIR, "gaze_weighted_metrics.csv")
OUT_CSV = os.path.join(EVAL_OUT_DIR, "gaze_weighted_winner_per_M.csv")


def preserve_legacy(path):
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


def build_winner_per_M(df):
    winners = []
    for M, group in df.groupby("M"):
        best = group.sort_values(
            by=["time_weighted_ghost_pct", "time_weighted_blind_pct"],
            ascending=[True, True]).iloc[0]
        winners.append(best)
    out = pd.DataFrame(winners).reset_index(drop=True)
    out = out.sort_values(by="M", key=lambda col: col.map(m_sort_key)).reset_index(drop=True)
    return out


def main():
    df = pd.read_csv(IN_CSV, dtype={"M": str})
    print(f"loaded {len(df)} rows from {IN_CSV}")

    winners = build_winner_per_M(df)

    # Honest check for the "rewards blindness" degenerate pattern -- see
    # module docstring. n_active_holes_phi0 == 0 combined with
    # time_weighted_blind_pct at or near 100 would mean a winner that is
    # ranked #1 on ghost_pct purely because it never illuminates anything.
    degenerate = winners[(winners.get("n_active_holes_phi0", 1) == 0) &
                         (winners.time_weighted_blind_pct > 50.0)]
    if len(degenerate) > 0:
        print(f"\n*** WARNING: {len(degenerate)} winner(s) look like the 'rewards "
              f"blindness' degenerate case (near-zero ghost_pct because the design "
              f"is mostly/always dark, not because it is actually safe) -- see "
              f"module docstring. Reported honestly in GAZE_WEIGHTED_COMPARISON.md, "
              f"not silently filtered. ***")
        print(degenerate[["M", "family", "N_requested", "spacing_params",
                          "time_weighted_ghost_pct", "time_weighted_blind_pct"]].to_string(index=False))
    else:
        print("\nno degenerate 'blind-but-ranked-first' winners found among the "
              "per-M results (checked directly, not assumed).")

    preserve_legacy(OUT_CSV)
    winners.to_csv(OUT_CSV, index=False)
    print(f"\nwrote {OUT_CSV} ({len(winners)} rows -- one per M)")

    print("\n--- gaze-weighted winner per M ---")
    cols = ["M", "family", "N_requested", "N_actual", "spacing_params",
           "time_weighted_ghost_pct", "time_weighted_blind_pct",
           "blind_pct_within_17deg", "ghost_pct_within_17deg"]
    print(winners[cols].to_string(index=False))


if __name__ == "__main__":
    main()
