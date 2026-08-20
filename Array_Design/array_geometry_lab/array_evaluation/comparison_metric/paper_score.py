"""
paper_score.py -- a new judgment metric, S_paper, computed on top of already-existing
theoretical data. This is LAYER 2 (array_evaluation/): it reads columns that
array_calculation/ already produced, does not use gates.py or metrics.py, does not
import anything from array_calculation/ (enforced mechanically by
../check_no_calculation_imports.py -- run it after any change here), and never
regenerates hole geometry or recomputes a physical quantity that already exists.

FORMULA (implemented exactly as given -- see the module-level constants and
compute_row() below for every term; nothing here is invented):

    S = 1.0*a_norm + 0.8*mu_eta + 1.0*mu_g + 0.6*cov

    a_norm = clip(a, 0, 3) / 3
    a      = c_ref / c_tot
    c_ref  = 1.22 * lambda_um * f_prime_um / p_um

    mu_eta  = exp(-(eta - 0.15)^2 / (2*0.08^2))
    eta_sq  = pi*d^2 / (4*s^2)                            (family == "square")
    eta_hex = pi*d^2 / (2*sqrt(3)*s^2)                    (family == "hexagonal")
    eta     = packing_density_per_area_um-2 * pi*(d/2)^2  (every other family)

    mu_g  = sigmoid(2*(1 - g/g_max)),  g_max = 1
    g     = (s * f_prime_um / L_um) / c_tot

    cov = min(1, max(0, (p_um - d) / s))

CONSTANTS, AS GIVEN: f_prime=22.2mm, lambda=550nm, L=15mm. p (pupil diameter) is
D_pupil_um=4000.0 -- the same constant already used everywhere else in this project
(array_calculation/sweep/run_sweep.py's DEFAULT_D_PUPIL_UM,
array_calculation/test_part3_small_case.py's D_PUPIL_UM), not a new value. d is the
row's own a_hole_um. All lengths are converted to a common unit (um) before use, since
the given constants are stated in mixed units (mm, nm, um) -- this is unit conversion
required to evaluate the formula as given, not a formula change.

c_tot -- WHERE IT ACTUALLY COMES FROM, PER ROW TYPE:

  per_M rows (M is a real diopter value): c_tot is r_EE(50%), the single-hole
  half-energy blur radius at that row's exact (M, a_hole_um) pair, looked up from
  new_sweeps/blur_sweep.csv at the project root (Pinholeproject/new_sweeps/, a sibling
  of Array_Design/, NOT inside array_data/) -- the same file
  array_calculation/margins/ghost_margin.py's own load_resolvable_blur_um() reads for
  the same purpose. This script reads that CSV directly (a plain pd.read_csv + dict
  lookup, not a physics computation, and not a `from ghost_margin import ...` -- so it
  does not trip check_no_calculation_imports.py) rather than inventing a new blur
  formula, which the task brief explicitly forbids. This is the one place this script
  reads outside array_data/theoretical_data/, called out here and in this run's own
  printed output, not done silently.

  M="global" rows: c_tot is read directly from the row's own 'resolvable_blur_um'
  column -- array_calculation/sweep/run_sweep.py's evaluate_candidate() now populates
  this for every global row as the WORST CASE (minimum r_EE_50) across every M in the
  tested range that design must support, computed there (not guessed, not picked at a
  single M) because a global row's own a_hole_um isn't tied to one M and there is no
  single (M, a_hole_um) pair to look up in blur_sweep.csv for it directly. See that
  module's own evaluate_candidate() comment for the full derivation and why smaller
  r_EE_50 is the worse case. This closes what used to be a real gap: S_paper was NaN
  for every M="global" row (793/8501) until this column existed.

s (the "pitch/spacing per family" the formula's constants list refers to, generically)
is read from each row's own already-recorded spacing_params string, using whichever
parameter IS that family's spacing control (not an auxiliary one like
rotation_deg/holes_per_ring0/jitter_fraction):
    square, hexagonal, jittered_lattice   -> pitch_um
    concentric, ring_offset_concentric    -> ring_spacing_um
    fibonacci_spiral, golden_angle,
      archimedean_spiral                  -> c_um  (spiral growth constant)
    rectangular                           -> sqrt(pitch_x_um * pitch_y_um)
                                              (reduces to pitch_um exactly when
                                              pitch_x_um == pitch_y_um, matching
                                              rectangular.py's own documented
                                              equivalence with square.py at equal
                                              pitch -- see that module's docstring)
    poisson_disk                          -> spacing_factor * a_hole_um
                                              (poisson_disk.py's own docstring:
                                              "enforced minimum pairwise distance =
                                              a_hole_um * spacing_factor" -- spacing_
                                              factor alone is a dimensionless
                                              multiplier, not a length)
This mapping selects the correct already-recorded field per family; it computes or
estimates nothing new.

Run:  python3 paper_score.py
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_evaluation/comparison_metric/
EVAL_ROOT = os.path.dirname(HERE)  # array_evaluation/
LAB_ROOT = os.path.dirname(EVAL_ROOT)  # array_geometry_lab/
ARRAY_DESIGN_ROOT = os.path.dirname(LAB_ROOT)  # Array_Design/
PINHOLEPROJECT_ROOT = os.path.dirname(ARRAY_DESIGN_ROOT)  # Pinholeproject/

DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
EVAL_OUT_DIR = os.path.join(LAB_ROOT, "array_data", "evaluation_results")

IN_CSV = os.path.join(DATA_DIR, "sweep_results_with_density.csv")
# NOT under array_data/ -- see module docstring's "c_tot -- WHERE IT ACTUALLY COMES
# FROM" section for why this external, read-only reference is necessary and scoped.
BLUR_SWEEP_CSV = os.path.join(PINHOLEPROJECT_ROOT, "new_sweeps", "blur_sweep.csv")

OUT_ALL_CANDIDATES_CSV = os.path.join(EVAL_OUT_DIR, "paper_score_all_candidates.csv")
OUT_WINNER_PER_M_CSV = os.path.join(EVAL_OUT_DIR, "paper_score_winner_per_M.csv")
OUT_COMPARISON_CSV = os.path.join(EVAL_OUT_DIR, "paper_score_vs_current_winner.csv")
METRIC1_CSV = os.path.join(EVAL_OUT_DIR, "metric1_max_density_per_M.csv")

DENSITY_COL = "packing_density_per_area_um-2"

# --- constants, as given in the task brief, converted to a common length unit (um) ---
F_PRIME_UM = 22.2 * 1000.0     # 22.2mm
LAMBDA_UM = 550.0 / 1000.0     # 550nm
L_UM = 15.0 * 1000.0           # 15mm
P_UM = 4000.0                  # pupil diameter -- same constant as
                               # array_calculation/sweep/run_sweep.py's
                               # DEFAULT_D_PUPIL_UM / test_part3_small_case.py's
                               # D_PUPIL_UM; not a new value.
C_REF_UM = 1.22 * LAMBDA_UM * F_PRIME_UM / P_UM
G_MAX = 1.0

SIMPLE_SPACING_KEY = {
    "square": "pitch_um",
    "hexagonal": "pitch_um",
    "jittered_lattice": "pitch_um",
    "concentric": "ring_spacing_um",
    "ring_offset_concentric": "ring_spacing_um",
    "fibonacci_spiral": "c_um",
    "golden_angle": "c_um",
    "archimedean_spiral": "c_um",
}


def parse_spacing_params(s):
    """Same trivial 'key=value;key=value' string parser used elsewhere in this
    project (e.g. array_calculation/degeneracy_filter.py's own copy) -- pure string
    parsing, no physics, so re-implementing it here (rather than importing it from
    array_calculation/) does not violate this layer's no-calculation-imports
    contract."""
    d = {}
    if pd.isna(s) or s == "":
        return d
    for part in str(s).split(";"):
        k, v = part.split("=")
        try:
            v = float(v)
        except ValueError:
            pass
        d[k] = v
    return d


def spacing_um(family, spacing_params, a_hole_um):
    """s, per family -- see module docstring's mapping table."""
    params = parse_spacing_params(spacing_params)
    if family == "poisson_disk":
        return params["spacing_factor"] * a_hole_um
    if family == "rectangular":
        return float(np.sqrt(params["pitch_x_um"] * params["pitch_y_um"]))
    key = SIMPLE_SPACING_KEY.get(family)
    if key is None:
        raise ValueError(f"no spacing mapping defined for family {family!r}")
    return params[key]


def eta_value(family, d, s, packing_density_per_area):
    if family == "square":
        return np.pi * d ** 2 / (4.0 * s ** 2)
    if family == "hexagonal":
        return np.pi * d ** 2 / (2.0 * np.sqrt(3.0) * s ** 2)
    return packing_density_per_area * np.pi * (d / 2.0) ** 2


def sigmoid(x):
    """Numerically stable form of the same 1/(1+exp(-x)) -- identical result, just
    avoids an overflow warning on large negative x (which mu_g's own inputs produce
    whenever g is large, i.e. spacing s is large relative to c_tot)."""
    if x >= 0:
        return 1.0 / (1.0 + np.exp(-x))
    ex = np.exp(x)
    return ex / (1.0 + ex)


def load_blur_lookup():
    """(M_diopters, a_hole_um) -> r_EE_50_um, from the project's own already-validated
    blur sweep (see module docstring). Exact-match lookup only, matching this
    project's established 'raise rather than silently interpolate' convention
    (array_calculation/margins/ghost_margin.py's load_resolvable_blur_um())."""
    blur = pd.read_csv(BLUR_SWEEP_CSV)
    lookup = {}
    for row in blur.itertuples(index=False):
        lookup[(float(row.M_diopters), float(row.a_hole_um))] = float(row.r_EE_50_um)
    return lookup


def compute_row(row, blur_lookup):
    """row: a pandas Series (one row of sweep_results_with_density.csv). Returns a
    dict of every intermediate term plus S_paper.

    c_tot: for a per_M row, the exact-match (M, a_hole_um) lookup into
    blur_sweep.csv (see module docstring), unchanged. For a M='global' row,
    array_calculation/sweep/run_sweep.py now provides this directly as the row's own
    'resolvable_blur_um' column -- the worst case (minimum r_EE_50) across every M in
    the tested range that design must support, not a single arbitrarily-picked M (see
    that module's evaluate_candidate() for how it's computed). c_tot is NaN only if
    that column is somehow missing/NaN on the input row (should not happen after a
    normal array_calculation run)."""
    family = row["family"]
    d = float(row["a_hole_um"])
    s = spacing_um(family, row["spacing_params"], d)

    if row["M"] == "global":
        c_tot = float(row["resolvable_blur_um"]) if pd.notna(row.get("resolvable_blur_um")) else np.nan
    else:
        c_tot = blur_lookup.get((float(row["M"]), d), np.nan)

    eta = eta_value(family, d, s, row[DENSITY_COL])
    mu_eta = np.exp(-((eta - 0.15) ** 2) / (2.0 * 0.08 ** 2))
    cov = min(1.0, max(0.0, (P_UM - d) / s))

    if np.isfinite(c_tot):
        a = C_REF_UM / c_tot
        a_norm = min(max(a, 0.0), 3.0) / 3.0
        g = (s * F_PRIME_UM / L_UM) / c_tot
        mu_g = sigmoid(2.0 * (1.0 - g / G_MAX))
        s_paper = 1.0 * a_norm + 0.8 * mu_eta + 1.0 * mu_g + 0.6 * cov
    else:
        a = np.nan
        a_norm = np.nan
        g = np.nan
        mu_g = np.nan
        s_paper = np.nan

    return {
        "s_um": s, "c_ref_um": C_REF_UM, "c_tot_um": c_tot, "a": a, "a_norm": a_norm,
        "eta": eta, "mu_eta": mu_eta, "g": g, "mu_g": mu_g, "cov": cov,
        "S_paper": s_paper,
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


def build_winner_per_M(scored):
    """Top S_paper design per M (and 'global'), same column shape as
    metric1_max_density_per_M.csv (all original theoretical_data columns) plus the
    S_paper term columns. Every M group (including 'global') now has a real
    resolvable_blur_um-backed c_tot (see module docstring), so this should always find
    a computable winner; the empty-group fallback below is kept as a defensive report
    (not a silent NaN) in case some future row genuinely has no computable S_paper."""
    winners = []
    for M, group in scored.groupby("M"):
        computable = group.dropna(subset=["S_paper"])
        if len(computable) == 0:
            placeholder = group.iloc[0].copy()
            for col in ["family", "N_requested", "N_actual", "spacing_params", "a_hole_um",
                       "seed"]:
                placeholder[col] = np.nan
            placeholder["M"] = M
            placeholder["S_paper"] = np.nan
            placeholder["_note"] = "not computable: no row in this M group has a defined S_paper"
            winners.append(placeholder)
            continue
        best = computable.loc[computable["S_paper"].idxmax()].copy()
        best["_note"] = ""
        winners.append(best)
    out = pd.DataFrame(winners).reset_index(drop=True)
    out = out.sort_values(by="M", key=lambda col: col.map(m_sort_key)).reset_index(drop=True)
    return out


def build_comparison(winner_per_M, scored):
    """Side-by-side: current pipeline's winner (from metric1_max_density_per_M.csv,
    read-only) vs S_paper's winner, per M -- family/N/spacing only, plus S_paper for
    the current winner if computable. Plain report, no interpretation."""
    metric1 = pd.read_csv(METRIC1_CSV)
    rows = []
    all_M = sorted(set(metric1.M.astype(str)) | set(winner_per_M.M.astype(str)), key=m_sort_key)
    for M in all_M:
        m1_row = metric1[metric1.M.astype(str) == M]
        paper_row = winner_per_M[winner_per_M.M.astype(str) == M]

        if len(m1_row) > 0:
            r = m1_row.iloc[0]
            current_family, current_N, current_spacing = r.family, int(r.N_actual), r.spacing_params
            match = scored[(scored.family == current_family) &
                          (scored.N_requested == r.N_requested) &
                          (scored.spacing_params == current_spacing) &
                          (scored.a_hole_um == r.a_hole_um) &
                          (scored.M.astype(str) == M)]
            current_s_paper = float(match.S_paper.iloc[0]) if len(match) > 0 else np.nan
        else:
            current_family = current_N = current_spacing = current_s_paper = np.nan

        if len(paper_row) > 0 and pd.notna(paper_row.iloc[0].get("S_paper")):
            p = paper_row.iloc[0]
            paper_family, paper_N, paper_spacing, paper_s_paper = (
                p.family, int(p.N_actual), p.spacing_params, float(p.S_paper))
        else:
            paper_family = paper_N = paper_spacing = np.nan
            paper_s_paper = np.nan

        rows.append({
            "M": M,
            "current_winner_family": current_family,
            "current_winner_N": current_N,
            "current_winner_spacing": current_spacing,
            "current_winner_S_paper": current_s_paper,
            "paper_winner_family": paper_family,
            "paper_winner_N": paper_N,
            "paper_winner_spacing": paper_spacing,
            "paper_winner_S_paper": paper_s_paper,
        })
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(IN_CSV, dtype={"M": str})
    print(f"loaded {len(df)} rows from {IN_CSV}")

    blur_lookup = load_blur_lookup()
    print(f"loaded {len(blur_lookup)} (M, a_hole_um) -> r_EE_50_um entries from "
          f"{BLUR_SWEEP_CSV} (external, read-only -- see module docstring)")

    terms = df.apply(lambda row: compute_row(row, blur_lookup), axis=1, result_type="expand")
    scored = pd.concat([df, terms], axis=1)

    n_computable = scored["S_paper"].notna().sum()
    n_global = (scored.M == "global").sum()
    n_global_computable = scored[scored.M == "global"]["S_paper"].notna().sum()
    print(f"\nS_paper computable for {n_computable}/{len(scored)} rows "
          f"(including {n_global_computable}/{n_global} M='global' rows, via "
          f"resolvable_blur_um -- see module docstring)")

    preserve_legacy(OUT_ALL_CANDIDATES_CSV)
    scored.to_csv(OUT_ALL_CANDIDATES_CSV, index=False)
    print(f"wrote {OUT_ALL_CANDIDATES_CSV} ({len(scored)} rows, all candidates + S_paper terms)")

    winner_per_M = build_winner_per_M(scored)
    preserve_legacy(OUT_WINNER_PER_M_CSV)
    winner_per_M.to_csv(OUT_WINNER_PER_M_CSV, index=False)
    print(f"wrote {OUT_WINNER_PER_M_CSV} ({len(winner_per_M)} rows -- top S_paper design per M)")
    print("\n--- top S_paper design per M ---")
    for _, r in winner_per_M.iterrows():
        if pd.isna(r.get("S_paper")):
            print(f"  M={r.M:>6}: not computable ({r.get('_note', '')})")
        else:
            print(f"  M={r.M:>6}: {r.family:25s} N_actual={int(r.N_actual):4d}  "
                  f"spacing={r.spacing_params:40s}  S_paper={r.S_paper:.4f}")

    comparison = build_comparison(winner_per_M, scored)
    preserve_legacy(OUT_COMPARISON_CSV)
    comparison.to_csv(OUT_COMPARISON_CSV, index=False)
    print(f"\nwrote {OUT_COMPARISON_CSV} ({len(comparison)} rows)")
    print("\n--- current pipeline winner (Metric 1) vs S_paper winner, per M ---")
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
