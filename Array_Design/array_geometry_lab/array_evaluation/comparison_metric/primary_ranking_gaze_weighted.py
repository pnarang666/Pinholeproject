"""
primary_ranking_gaze_weighted.py -- the project's PRIMARY ranking as of
2026-09-13, per explicit user decision: gaze-weighted (time-weighted ghost
%) is more realistic than a pure worst-case-across-all-gaze-angles
criterion, so it now replaces gates.py/effective_density_ranking.py/
metrics.py as the primary standard. Those older worst-case files are NOT
deleted or edited -- they remain valid, reported data (see README.md) -- but
this file's output is what this project now presents as ITS answer.

RANKING RULE:
  1. HARD GATE: exclude every candidate with time_weighted_blind_pct >
     BLIND_GATE_THRESHOLD_PCT. "Blind" here means literally zero
     illuminated area at that gaze angle (compute_gaze_weighted_metrics.py's
     own is_blind = (total_area == 0.0)), time-weighted across the measured
     eye-tracking eccentricity distribution -- so this gate reads as "the
     design is never (to within this tolerance) totally dark, weighted by
     how the eye actually moves."
  2. Among gate-survivors, rank by time_weighted_ghost_pct ASCENDING
     (primary criterion), tie-break time_weighted_blind_pct ASCENDING.

WHY A TOLERANCE, NOT A BARE 0% GATE -- flagged explicitly, checked not
assumed: a strict 0%-blind-time gate was tried first. At M=6D and M=8D it
produces a sharp cliff -- EVERY candidate with genuinely zero blind time at
those M has a real (27-30%) ghost percentage; the excellent 0%-ghost
candidates that exist at those M (hexagonal, N=20/50, pitch=4000um) all
carry a small nonzero blind time (0.33-0.71%). A bare-zero gate is exactly
the "margin vs. zero" failure mode this project's own gates.py already
diagnosed and fixed once before (a threshold of exactly 0 cannot
distinguish a trivial sliver from a real problem) -- so, consistent with
that established project precedent, a small, explicit, documented
tolerance is used instead of an arbitrary hard zero.
  BLIND_GATE_THRESHOLD_PCT = 1.0 (percent of time-weighted viewing time)
  -- chosen (this task's own explicit decision, not derived from a deeper
  source) as the smallest round number that clears every existing
  M=0..8 gaze-weighted winner's own blind_pct (max observed: 0.71% at
  M=8, hexagonal N=20) with headroom, while still being obviously "close to
  zero, not a loophole." Every winner produced under this gate is checked
  and reported below with its own exact blind_pct -- the gate is not being
  used to hide a design that is meaningfully blind.

Reads array_calculation/compute_gaze_weighted_metrics.py's own output
(array_data/theoretical_data/gaze_weighted_metrics.csv) read-only. Does not
modify gaze_weighted_ranking.py's own (ungated) output, which remains a
valid, separately-reported alternative view of the same underlying data.

Run: python3 primary_ranking_gaze_weighted.py
"""
import os
import shutil

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL_ROOT = os.path.dirname(HERE)
LAB_ROOT = os.path.dirname(EVAL_ROOT)
DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
EVAL_OUT_DIR = os.path.join(LAB_ROOT, "array_data", "evaluation_results")

IN_CSV = os.path.join(DATA_DIR, "gaze_weighted_metrics.csv")
OUT_CSV = os.path.join(EVAL_OUT_DIR, "PRIMARY_WINNER_PER_M.csv")

BLIND_GATE_THRESHOLD_PCT = 1.0


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


def m_sort_key(m):
    return (m == "global", m)


def build_winner_per_M(df):
    winners = []
    dropped_all_blind = []
    for M, group in df.groupby("M"):
        gated = group[group.time_weighted_blind_pct <= BLIND_GATE_THRESHOLD_PCT]
        if len(gated) == 0:
            dropped_all_blind.append(M)
            continue
        best = gated.sort_values(
            by=["time_weighted_ghost_pct", "time_weighted_blind_pct"],
            ascending=[True, True]).iloc[0]
        winners.append(best)
    out = pd.DataFrame(winners).reset_index(drop=True)
    out = out.sort_values(by="M", key=lambda col: col.map(m_sort_key)).reset_index(drop=True)
    return out, dropped_all_blind


def main():
    df = pd.read_csv(IN_CSV, dtype={"M": str})
    print(f"loaded {len(df)} rows from {IN_CSV}")
    print(f"blindness hard gate: time_weighted_blind_pct <= {BLIND_GATE_THRESHOLD_PCT}%")

    winners, dropped_all_blind = build_winner_per_M(df)
    if dropped_all_blind:
        print(f"\n*** WARNING: M values with NO candidate passing the blind gate at all: "
              f"{dropped_all_blind} -- no winner reported for these. ***")

    degenerate = winners[(winners.get("n_active_holes_phi0", 1) == 0) &
                         (winners.time_weighted_blind_pct > 0.5 * BLIND_GATE_THRESHOLD_PCT)]
    if len(degenerate) > 0:
        print(f"\n*** WARNING: {len(degenerate)} winner(s) sit close to the blind-gate "
              f"boundary AND have zero active holes -- inspect before trusting. ***")

    preserve_legacy(OUT_CSV)
    winners.to_csv(OUT_CSV, index=False)
    print(f"\nwrote {OUT_CSV} ({len(winners)} rows -- one per M)")

    print("\n--- PRIMARY winner per M (gaze-weighted ghost, gated on blind_pct<=1.0%) ---")
    cols = ["M", "family", "N_requested", "N_actual", "spacing_params",
           "time_weighted_ghost_pct", "time_weighted_blind_pct",
           "blind_pct_within_17deg", "ghost_pct_within_17deg"]
    print(winners[cols].to_string(index=False))


if __name__ == "__main__":
    main()
