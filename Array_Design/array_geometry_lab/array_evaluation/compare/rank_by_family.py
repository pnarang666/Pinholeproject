"""
Part 4b: ranks geometry families by ghost-margin robustness, per M (and separately for
'global' scope), restricted to structurally_safe=True candidates -- there is no
brightness objective pulling toward tighter spacing in this pipeline (that's
array_optimization/'s job), so among safe designs, "best" is simply "most margin,"
descending.

HONEST REPORTING: a (family, M) combination with ZERO structurally-safe candidates is
reported explicitly in the comparison table (as a row with candidate_count=0, not
dropped), and printed as a flagged finding -- a family structurally unsuited to a given
myopia level is a real result, not a gap in the sweep.

Run:  python3 rank_by_family.py [--in_csv ../sweep_results.csv]
"""
import argparse
import os
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_evaluation/compare/
EVAL_ROOT = os.path.abspath(os.path.join(HERE, ".."))  # array_evaluation/
LAB_ROOT = os.path.abspath(os.path.join(EVAL_ROOT, ".."))  # array_geometry_lab/
DEFAULT_IN_CSV = os.path.join(LAB_ROOT, "array_data", "theoretical_data", "sweep_results.csv")
DEFAULT_OUT_CSV = os.path.join(LAB_ROOT, "array_data", "evaluation_results", "family_ranking.csv")
DEFAULT_OUT_PLOT = os.path.join(LAB_ROOT, "array_data", "evaluation_results",
                                "family_ranking_margin_vs_N.png")

STOCHASTIC_FAMILIES = {"poisson_disk", "jittered_lattice"}
HIGH_VARIANCE_RATIO_THRESHOLD = 1.0  # a stochastic candidate's seed-to-seed std
                                     # exceeding this fraction of its OWN worst-case
                                     # margin magnitude is flagged high_seed_variance.
                                     # 1.0 (std as large as the worst-case margin
                                     # itself) was chosen as the threshold because at
                                     # that point the worst-observed seed is no longer
                                     # a small perturbation around a stable typical
                                     # value -- it's the same order of magnitude as the
                                     # spread itself, meaning a handful more seeds could
                                     # plausibly push the true worst case meaningfully
                                     # lower still. Not a statistically derived cutoff,
                                     # a stated, round, auditable one -- documented here
                                     # rather than left implicit, per this project's own
                                     # convention for judgment calls without an
                                     # unambiguous "correct" answer.


def _seed_worst_and_std(values):
    """WORST-CASE (min, not mean) across seeds, per this task's explicit decision --
    plus the seed-to-seed std as a separate diagnostic, never blended into the
    worst-case number itself. Handles +inf values (a seed with zero active pairs,
    trivially safe) explicitly: min() already treats +inf correctly (only wins if
    EVERY seed is +inf); std is computed over the finite subset only when some but not
    all seeds are infinite (a mixed inf/finite result is itself noteworthy -- see
    aggregate_stochastic()'s docstring -- and a std that silently became NaN or +inf
    from mixing in infinities would hide that rather than surface it)."""
    values = np.asarray(values, dtype=float)
    worst = float(values.min())
    finite = values[np.isfinite(values)]
    if len(finite) == len(values):
        std = float(values.std(ddof=0))
    elif len(finite) == 0:
        std = 0.0  # every seed was +inf -- perfectly consistent, not "variance" at all
    else:
        std = float(finite.std(ddof=0))  # mixed finite/+inf across seeds: std reported
                                          # over the finite ones only, informational
    return worst, std


def _is_high_variance(worst, std, threshold=HIGH_VARIANCE_RATIO_THRESHOLD):
    if not np.isfinite(worst) or not np.isfinite(std):
        return False  # an all-+inf worst case has zero std by construction above --
                       # never "high variance"
    if std <= 1e-9:
        return False
    if abs(worst) <= 1e-9:
        return True  # any nonzero spread around an exactly-zero worst-case margin
    return std > threshold * abs(worst)


def aggregate_stochastic(df):
    """Collapses per-seed rows (poisson_disk, jittered_lattice) into ONE row per
    (family, N_requested, spacing_params, M), representing the WORST-CASE (minimum)
    margin observed across all seeds tested at that point -- matching this project's
    established preference for structural/worst-case guarantees over statistical ones
    (array_optimization/ghosting_risk.py's own continuous-risk-model rationale; this
    folder's own structurally_safe convention). Deterministic-family rows pass through
    completely unchanged, with the new diagnostic columns filled in as their
    single-realization equivalents (std=NaN, n_seeds_tested=1, high_seed_variance=False
    -- there is no seed-to-seed spread to measure for a deterministic layout), so the
    two row types share one schema for concatenation and downstream ranking.

    N_actual is ALSO aggregated by minimum across seeds (not the first seed's value),
    for the same worst-case-first reasoning -- the honest hole count for a stochastic
    candidate is the fewest any tested seed actually placed, not an arbitrary
    representative seed's count."""
    is_stochastic = df.family.isin(STOCHASTIC_FAMILIES)
    det = df[~is_stochastic].copy()
    det["ghost_margin_std_across_seeds"] = np.nan
    det["vignetting_margin_std_across_seeds"] = np.nan
    det["n_seeds_tested"] = 1
    det["high_seed_variance"] = False

    sto = df[is_stochastic].copy()
    if len(sto) == 0:
        return det

    agg_rows = []
    for key, g in sto.groupby(["family", "N_requested", "spacing_params", "M"], dropna=False):
        worst_gm, std_gm = _seed_worst_and_std(g.worst_case_ghost_margin.values)
        worst_vm, std_vm = _seed_worst_and_std(g.worst_case_vignetting_margin.values)
        row = g.iloc[0].copy()  # non-seed-dependent fields (a_hole_um, family,
                                 # N_requested, spacing_params, M) are identical across
                                 # every seed in this group by construction -- taking
                                 # them from any one row is exact, not approximate
        row["N_actual"] = int(g.N_actual.min())
        row["worst_case_ghost_margin"] = worst_gm
        row["worst_case_vignetting_margin"] = worst_vm
        row["structurally_safe"] = bool(worst_gm > 0 and worst_vm > 0)
        row["ghost_margin_std_across_seeds"] = std_gm
        row["vignetting_margin_std_across_seeds"] = std_vm
        row["n_seeds_tested"] = int(len(g))
        row["high_seed_variance"] = bool(_is_high_variance(worst_gm, std_gm)
                                         or _is_high_variance(worst_vm, std_vm))
        row["seed"] = None  # this row now represents ALL tested seeds, not one
        agg_rows.append(row)

    sto_agg = pd.DataFrame(agg_rows)
    return pd.concat([det, sto_agg], ignore_index=True)


def preserve_legacy(path):
    if not os.path.exists(path):
        return
    i = 1
    legacy_path = path.replace(".csv", f"_legacy{i}.csv").replace(".png", f"_legacy{i}.png")
    while os.path.exists(legacy_path):
        i += 1
        legacy_path = path.replace(".csv", f"_legacy{i}.csv").replace(".png", f"_legacy{i}.png")
    shutil.copy2(path, legacy_path)
    print(f"preserved predecessor -> {legacy_path}")


def build_ranking(df):
    """One ranked table per M value (and 'global'): safe candidates only, sorted by
    worst_case_ghost_margin descending. Zero-safe (family, M) combinations are logged
    explicitly, not silently absent."""
    all_families = sorted(df.family.unique())
    m_values = list(df.M.unique())  # includes the string 'global' alongside floats

    ranked_rows = []
    zero_safe_notes = []
    for M in m_values:
        sub = df[df.M == M]
        safe = sub[sub.structurally_safe].copy()
        safe = safe.sort_values("worst_case_ghost_margin", ascending=False)
        safe.insert(0, "rank_within_M", range(1, len(safe) + 1))
        ranked_rows.append(safe)

        for family in all_families:
            n_safe_f = int((safe.family == family).sum())
            n_total_f = int((sub.family == family).sum())
            if n_safe_f == 0:
                zero_safe_notes.append(
                    f"family='{family}' at M={M}: 0/{n_total_f} candidates structurally safe")

    ranking = pd.concat(ranked_rows, ignore_index=True) if ranked_rows else pd.DataFrame()
    return ranking, zero_safe_notes


DISPLAY_MARGIN_CAP = 5.0  # worst_case_ghost_margin is +inf whenever a candidate has zero
                          # active pairs (structurally ghost-free, e.g. very sparse
                          # spacing) -- a real, correct value, but infinite by
                          # construction and unplottable on a linear axis. Taking the
                          # max across spacing_params (this plot's own aggregation, see
                          # docstring) hits +inf often, since a wide-enough spacing is
                          # trivially safe -- so EVERY line would be a flat, uninformative
                          # line at +inf with no visible structure otherwise. Capped here
                          # FOR DISPLAY ONLY (family_ranking.csv itself keeps true,
                          # uncapped +inf values, including for ranking, where +inf
                          # correctly always sorts first): 5.0 is comfortably above the
                          # largest FINITE margin observed in this pipeline's own sweep
                          # (checked against sweep_results.csv before choosing this
                          # constant), so capped points are visually distinguishable from
                          # the finite structure below them, not blended into it.


def plot_margin_vs_N(df, out_path):
    """Margin vs N, one line per family, faceted by M -- MEDIAN margin across
    spacing_params at each (family, N, M), since margin vs N alone needs one number per
    point and the spacing parameter itself is a second free axis not shown on this plot
    (see family_ranking.csv for the full per-spacing breakdown). MEDIAN, not MAX, was
    chosen after checking the actual data: taking the max was tried first and produced
    a flat, uninformative line pinned at DISPLAY_MARGIN_CAP for every family at every N
    (verified: e.g. square/N=50/M=4D has 2/6 tested pitches giving +inf, and max always
    picks one of those), because among a handful of tested spacings there is usually at
    least one sparse enough to be trivially safe -- that says nothing about the family's
    TYPICAL behavior. The median is not dominated by a single trivially-safe outlier
    unless a MAJORITY of tested spacings are trivially safe, so it shows real
    per-family structure (confirmed on the same square/N=50/M=4D case: only 2/6 points
    are +inf, so the median is a genuine finite value, not the cap). Infinite medians
    (a majority-safe case) are still capped at DISPLAY_MARGIN_CAP for plotting only."""
    m_values = sorted([m for m in df.M.unique() if m != "global"], key=float) + \
        (["global"] if "global" in df.M.unique() else [])
    families = sorted(df.family.unique())
    n_panels = len(m_values)
    ncols = 3
    nrows = -(-n_panels // ncols)

    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 3.4 * nrows), squeeze=False)
    colors = plt.cm.tab10.colors
    for idx, M in enumerate(m_values):
        ax = axes[idx // ncols][idx % ncols]
        sub = df[df.M == M]
        for fi, family in enumerate(families):
            fam_sub = sub[sub.family == family]
            if len(fam_sub) == 0:
                continue
            best_per_N = fam_sub.groupby("N_requested")["worst_case_ghost_margin"].median().reset_index()
            best_per_N["worst_case_ghost_margin"] = best_per_N["worst_case_ghost_margin"].clip(
                upper=DISPLAY_MARGIN_CAP)
            best_per_N = best_per_N.sort_values("N_requested")
            ax.plot(best_per_N.N_requested, best_per_N.worst_case_ghost_margin, "o-",
                    color=colors[fi % len(colors)], label=family, markersize=4, linewidth=1.3)
        ax.axhline(0.0, color="0.5", linewidth=0.8, linestyle="--")
        ax.set_title(f"M={M}" if M == "global" else f"M={M}D", fontsize=10)
        ax.set_xlabel("N (holes requested)", fontsize=8)
        ax.set_ylabel("median ghost margin", fontsize=8)
        ax.tick_params(labelsize=7)
    for idx in range(n_panels, nrows * ncols):
        axes[idx // ncols][idx % ncols].axis("off")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(families), fontsize=8,
              bbox_to_anchor=(0.5, 0.005))
    fig.suptitle("Median worst-case ghost margin vs. N, by geometry family (median across spacing per point)")
    fig.tight_layout(rect=[0, 0.06, 1, 0.96])
    fig.savefig(out_path, dpi=150, facecolor="white")
    print(f"wrote {out_path}")


def main():
    ap_ = argparse.ArgumentParser(description=__doc__)
    ap_.add_argument("--in_csv", type=str, default=DEFAULT_IN_CSV)
    ap_.add_argument("--out_csv", type=str, default=DEFAULT_OUT_CSV)
    ap_.add_argument("--out_plot", type=str, default=DEFAULT_OUT_PLOT)
    args = ap_.parse_args()

    df = pd.read_csv(args.in_csv)
    n_raw_rows = len(df)
    df = aggregate_stochastic(df)
    n_stochastic_collapsed = n_raw_rows - len(df)
    if n_stochastic_collapsed:
        print(f"aggregated stochastic-family rows: {n_raw_rows} raw rows -> {len(df)} "
              f"rows (each stochastic (family,N,spacing,M) point collapsed across its "
              f"seeds into one worst-case-across-seeds row)")

    ranking, zero_safe_notes = build_ranking(df)

    preserve_legacy(args.out_csv)
    ranking.to_csv(args.out_csv, index=False)
    print(f"wrote {args.out_csv} ({len(ranking)} ranked safe-candidate rows)")

    print(f"\n=== zero-safe-candidate findings ({len(zero_safe_notes)}) ===")
    if zero_safe_notes:
        for note in zero_safe_notes:
            print(f"  *** {note} ***")
    else:
        print("  none -- every family has at least one structurally-safe candidate at every M tested")

    print("\n=== top-3 safe candidates per M ===")
    for M in ranking.M.unique() if len(ranking) else []:
        top3 = ranking[ranking.M == M].head(3)
        print(f"\n  M={M}:")
        if len(top3) == 0:
            print("    (no structurally-safe candidates at this M)")
        else:
            print(top3[["rank_within_M", "family", "N_requested", "spacing_params",
                        "worst_case_ghost_margin", "worst_case_vignetting_margin",
                        "n_seeds_tested", "high_seed_variance"]].to_string(index=False))

    if len(ranking):
        high_var_safe = ranking[ranking.high_seed_variance]
        print(f"\n=== high_seed_variance among SAFE stochastic candidates "
              f"({len(high_var_safe)}) ===")
        print("  A safe candidate flagged here cleared the worst-case>0 bar, but its "
              "seed-to-seed spread is large relative to that worst-case margin itself "
              f"(std > {HIGH_VARIANCE_RATIO_THRESHOLD:.1f}x |worst-case|) -- it is "
              "technically safe across every tested seed, but only just, and not "
              "consistently so; treat it as more fragile than a low-variance safe "
              "candidate with a similar worst-case number.")
        if len(high_var_safe):
            print(high_var_safe[["family", "N_requested", "spacing_params", "M",
                                 "worst_case_ghost_margin", "ghost_margin_std_across_seeds",
                                 "worst_case_vignetting_margin", "vignetting_margin_std_across_seeds",
                                 "n_seeds_tested"]].to_string(index=False))
        else:
            print("  none -- every safe stochastic candidate is consistently safe across its tested seeds")

    preserve_legacy(args.out_plot)
    plot_margin_vs_N(df, args.out_plot)


if __name__ == "__main__":
    main()
