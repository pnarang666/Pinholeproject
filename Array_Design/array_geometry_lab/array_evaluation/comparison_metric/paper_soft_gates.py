"""
paper_soft_gates.py -- a SEPARATE, comparison-only judgment metric, S_paper_soft: does
the near-eta=0.15 hexagonal candidate our hard gates reject
(worst_case_ghost_margin=-16.6, confirmed: M=4.0, N=100,
pitch_um=1500.0;rotation_deg=0.0, S_paper=1.5007 -- see paper_score_all_candidates.csv)
recover under the paper's OWN soft ghost treatment (mu_g, no hard cutoff) plus a
closed-form blind_rate estimate in place of the geometric `cov` term?

This is a METHODOLOGY COMPARISON, not a replacement for this project's actual ranking.
gates.py, metrics.py, and every existing winner file are untouched; this script only
reads them.

LAYER 2 (array_evaluation/): read-only from array_data/theoretical_data/ (via
array_data/evaluation_results/paper_score_all_candidates.csv, which already carries
every theoretical_data column through unchanged -- no separate theoretical_data read
needed) and other existing evaluation outputs (metric1_max_density_per_M.csv,
paper_score_winner_per_M.csv). Imports gates.py -- a SIBLING module within
array_evaluation/, not array_calculation/ -- read-only (apply_gates() only, never
modified), purely to answer "would this candidate pass our hard gates" using the
existing single source of truth for that question rather than re-deriving it a second
time. Does not import anything from array_calculation/ (enforced by
../check_no_calculation_imports.py).

FORMULA:
    S_paper_soft = 1.0*a_norm + 0.8*mu_eta + 1.0*mu_g + 0.6*(1 - blind_rate)

    g_paper = (s * f_prime_um / L_um) / c_tot_um
    mu_g    = sigmoid(2*(1 - g_paper/1.0))

a_norm, mu_eta, g_paper, mu_g are IDENTICAL in formula and inputs to paper_score.py's
own a_norm/mu_eta/g/mu_g (same s, same c_tot, same constants) -- reused DIRECTLY from
paper_score_all_candidates.csv's own columns, not recomputed, per this task's own
instruction. The only new term is blind_rate, replacing paper_score.py's `cov`
(geometric coverage ratio) with the paper's own closed-form geometric-packing-floor
estimate of structurally dark fraction, by family, AS GIVEN:
    square:    1 - pi/4           ~= 0.2146
    hexagonal: 1 - pi/(2*sqrt(3)) ~= 0.0931
Flagged, per the task brief's own instruction, as "the paper's closed-form estimate,"
not an independently measured quantity -- it is a fixed number per family, not derived
from any row's own data.

NO formula was given for this project's other 8 families (concentric,
fibonacci_spiral, golden_angle, rectangular, archimedean_spiral,
ring_offset_concentric, poisson_disk, jittered_lattice). Rather than invent one,
blind_rate (and therefore S_paper_soft) is left NaN for those rows -- reported as such
in this run's own printed output, not silently guessed or dropped. "Rank ALL
candidates" in the task brief means "no gate filtering applied" (the entire point of
this experiment: the paper's method has no hard safety cutoff), not "every family
regardless of whether blind_rate is defined for it" -- square vs. hexagonal is what
this experiment is actually about.

Run:  python3 paper_soft_gates.py
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_evaluation/comparison_metric/
sys.path.insert(0, HERE)
import gates  # noqa: E402 -- sibling array_evaluation/ module, read-only use
              # (apply_gates only, never modified). NOT an array_calculation/ import.

EVAL_ROOT = os.path.dirname(HERE)  # array_evaluation/
LAB_ROOT = os.path.dirname(EVAL_ROOT)  # array_geometry_lab/
EVAL_OUT_DIR = os.path.join(LAB_ROOT, "array_data", "evaluation_results")

IN_PAPER_SCORE_CSV = os.path.join(EVAL_OUT_DIR, "paper_score_all_candidates.csv")
METRIC1_CSV = os.path.join(EVAL_OUT_DIR, "metric1_max_density_per_M.csv")
PAPER_SCORE_WINNER_CSV = os.path.join(EVAL_OUT_DIR, "paper_score_winner_per_M.csv")
OUT_CSV = os.path.join(EVAL_OUT_DIR, "paper_soft_gates_winner_per_M.csv")

BLIND_RATE_BY_FAMILY = {
    "square": 1.0 - np.pi / 4.0,
    "hexagonal": 1.0 - np.pi / (2.0 * np.sqrt(3.0)),
}


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


def compute_S_paper_soft(scored):
    """scored: paper_score_all_candidates.csv, already loaded -- a_norm/mu_eta/mu_g
    are read straight from its own columns (identical formula/inputs to
    paper_score.py, reused not recomputed, per the task brief)."""
    scored = scored.copy()
    scored["blind_rate"] = scored["family"].map(BLIND_RATE_BY_FAMILY)
    scored["S_paper_soft"] = (1.0 * scored["a_norm"] + 0.8 * scored["mu_eta"] +
                              1.0 * scored["mu_g"] + 0.6 * (1.0 - scored["blind_rate"]))
    return scored


def passes_hard_gates(row):
    """Lookup only, no new physics: re-applies gates.py's own three threshold checks
    (DEFAULT_GATES: ghost_safety, vignetting_safety, viability) to this single
    candidate's already-computed margin/viability columns -- the exact same function
    run_comparison.py itself calls, not a re-derivation of what 'passes' means."""
    one_row_df = pd.DataFrame([row])
    survivors = gates.apply_gates(one_row_df, gates.DEFAULT_GATES)
    return len(survivors) == 1


def build_soft_winner_per_M(scored):
    """Top S_paper_soft design per M (and 'global'), NO gates applied -- ranks over
    the full candidate set exactly as paper_score.py's own winner selection does.
    Rows with undefined blind_rate (every family except square/hexagonal) cannot
    have a defined S_paper_soft and are excluded from contention, group-by-group;
    an M group with zero computable rows is reported as not-computable, not
    silently dropped."""
    winners = []
    for M, group in scored.groupby("M"):
        computable = group.dropna(subset=["S_paper_soft"])
        if len(computable) == 0:
            placeholder = group.iloc[0].copy()
            for col in ["family", "N_requested", "N_actual", "spacing_params", "a_hole_um", "seed"]:
                placeholder[col] = np.nan
            placeholder["M"] = M
            placeholder["S_paper_soft"] = np.nan
            placeholder["_note"] = ("not computable: no row in this M group has a defined "
                                    "blind_rate (only square/hexagonal have the paper's "
                                    "closed-form estimate -- see module docstring)")
            winners.append(placeholder)
            continue
        best = computable.loc[computable["S_paper_soft"].idxmax()].copy()
        best["_note"] = ""
        winners.append(best)
    out = pd.DataFrame(winners).reset_index(drop=True)
    out = out.sort_values(by="M", key=lambda col: col.map(m_sort_key)).reset_index(drop=True)
    return out


def build_comparison(soft_winner_per_M):
    """Side-by-side, per M: our hard-gated winner (metric1_max_density_per_M.csv) vs
    S_paper's winner (paper_score_winner_per_M.csv, already computed) vs
    S_paper_soft's winner (this run) -- family/N/spacing for each, plus whether the
    S_paper_soft winner would pass our hard gates. Plain report, no interpretation."""
    metric1 = pd.read_csv(METRIC1_CSV, dtype={"M": str})
    paper_winner = pd.read_csv(PAPER_SCORE_WINNER_CSV, dtype={"M": str})

    all_M = sorted(
        set(metric1.M) | set(paper_winner.M) | set(soft_winner_per_M.M.astype(str)),
        key=m_sort_key)

    rows = []
    for M in all_M:
        m1 = metric1[metric1.M == M]
        ps = paper_winner[paper_winner.M == M]
        pss = soft_winner_per_M[soft_winner_per_M.M.astype(str) == M]

        hard_family = hard_N = hard_spacing = np.nan
        if len(m1) > 0:
            r = m1.iloc[0]
            hard_family, hard_N, hard_spacing = r.family, int(r.N_actual), r.spacing_params

        paper_family = paper_N = paper_spacing = paper_s_val = np.nan
        if len(ps) > 0 and pd.notna(ps.iloc[0].get("S_paper")):
            r = ps.iloc[0]
            paper_family, paper_N, paper_spacing = r.family, int(r.N_actual), r.spacing_params
            paper_s_val = float(r.S_paper)

        soft_family = soft_N = soft_spacing = soft_s_val = np.nan
        soft_passes_hard = None
        if len(pss) > 0 and pd.notna(pss.iloc[0].get("S_paper_soft")):
            r = pss.iloc[0]
            soft_family, soft_N, soft_spacing = r.family, int(r.N_actual), r.spacing_params
            soft_s_val = float(r.S_paper_soft)
            soft_passes_hard = passes_hard_gates(r)

        rows.append({
            "M": M,
            "hard_gated_winner_family": hard_family,
            "hard_gated_winner_N": hard_N,
            "hard_gated_winner_spacing": hard_spacing,
            "s_paper_winner_family": paper_family,
            "s_paper_winner_N": paper_N,
            "s_paper_winner_spacing": paper_spacing,
            "s_paper_winner_value": paper_s_val,
            "s_paper_soft_winner_family": soft_family,
            "s_paper_soft_winner_N": soft_N,
            "s_paper_soft_winner_spacing": soft_spacing,
            "s_paper_soft_winner_value": soft_s_val,
            "s_paper_soft_winner_passes_hard_gates": soft_passes_hard,
        })
    return pd.DataFrame(rows)


def main():
    scored_in = pd.read_csv(IN_PAPER_SCORE_CSV, dtype={"M": str})
    print(f"loaded {len(scored_in)} rows from {IN_PAPER_SCORE_CSV}")

    scored = compute_S_paper_soft(scored_in)
    n_computable = scored["S_paper_soft"].notna().sum()
    families_with_blind_rate = sorted(BLIND_RATE_BY_FAMILY.keys())
    families_without = sorted(set(scored.family.unique()) - set(BLIND_RATE_BY_FAMILY.keys()))
    print(f"S_paper_soft computable for {n_computable}/{len(scored)} rows "
          f"(families with a closed-form blind_rate: {families_with_blind_rate}; "
          f"NOT computable for: {families_without} -- no formula given, see module "
          f"docstring)")

    soft_winner_per_M = build_soft_winner_per_M(scored)
    print("\n--- top S_paper_soft design per M (no gates applied) ---")
    for _, r in soft_winner_per_M.iterrows():
        if pd.isna(r.get("S_paper_soft")):
            print(f"  M={r.M:>6}: not computable ({r.get('_note', '')})")
        else:
            passes = passes_hard_gates(r)
            print(f"  M={r.M:>6}: {r.family:12s} N_actual={int(r.N_actual):4d}  "
                  f"spacing={r.spacing_params:35s}  S_paper_soft={r.S_paper_soft:.4f}  "
                  f"passes_hard_gates={passes}")

    comparison = build_comparison(soft_winner_per_M)
    preserve_legacy(OUT_CSV)
    comparison.to_csv(OUT_CSV, index=False)
    print(f"\nwrote {OUT_CSV} ({len(comparison)} rows)")
    print("\n--- hard-gated winner vs S_paper winner vs S_paper_soft winner, per M ---")
    print(comparison.to_string(index=False))

    n_hex_soft_wins = (soft_winner_per_M.family == "hexagonal").sum()
    n_square_soft_wins = (soft_winner_per_M.family == "square").sum()
    n_rows = len(soft_winner_per_M[soft_winner_per_M.S_paper_soft.notna()])
    verdict = "YES, hex recovers under the paper's soft treatment" if n_hex_soft_wins > 0 else \
        "NO, hex still does not win even under the soft treatment"
    print("\n--- one-line answer ---")
    print(f"hexagonal wins {n_hex_soft_wins}/{n_rows} computable M-slots under "
          f"S_paper_soft (square wins {n_square_soft_wins}/{n_rows}) -- {verdict}.")


if __name__ == "__main__":
    main()
