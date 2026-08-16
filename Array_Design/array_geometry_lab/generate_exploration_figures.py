"""
Generates every figure and the Section 5 summary-table data for
THEORETICAL_DATASET_EXPLORATION.tex, entirely from sweep_results.csv and
family_ranking.csv (plus, for Section 1's real coordinates, the actual generator
functions -- coordinates are not stored in the CSVs, so they are regenerated here
using the SAME representative (N, spacing) parameters the figures report, not
invented ones).

This script is descriptive-only infrastructure: it computes and plots, it does not
rank, gate, or pick a "best" anything -- that is explicitly a separate, later step
(see THEORETICAL_DATASET_EXPLORATION.tex's own preface).

Run:  python3 generate_exploration_figures.py
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "array_calculation", "generators"))

import square, hexagonal, concentric, fibonacci_spiral, golden_angle  # noqa: E402
import rectangular, archimedean_spiral, ring_offset_concentric  # noqa: E402
import poisson_disk, jittered_lattice  # noqa: E402

FIGS_DIR = os.path.join(HERE, "figs_exploration")
os.makedirs(FIGS_DIR, exist_ok=True)

SWEEP_CSV = os.path.join(HERE, "array_data", "theoretical_data", "sweep_results.csv")
RANKING_CSV = os.path.join(HERE, "array_data", "evaluation_results", "family_ranking.csv")
PER_M_OPTIMUM_MAP_CSV = os.path.join(PROJECT_ROOT, "new_sweeps", "per_M_optimum_map.csv")

STOCHASTIC_FAMILIES = {"poisson_disk", "jittered_lattice"}
DISPLAY_MARGIN_CAP = 5.0  # same cap value and rationale as compare/rank_by_family.py's
                          # own DISPLAY_MARGIN_CAP: +inf margins (structurally zero
                          # active pairs) are real, correct values but unplottable on a
                          # linear/color scale; capped for display only, never for the
                          # underlying data written out in Section 5's table.

M_ORDER = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, "global"]

GEN_FUNCS = {
    "square": square.generate, "hexagonal": hexagonal.generate,
    "concentric": concentric.generate, "fibonacci_spiral": fibonacci_spiral.generate,
    "golden_angle": golden_angle.generate, "rectangular": rectangular.generate,
    "archimedean_spiral": archimedean_spiral.generate,
    "ring_offset_concentric": ring_offset_concentric.generate,
    "poisson_disk": poisson_disk.generate, "jittered_lattice": jittered_lattice.generate,
}

FAMILIES = sorted(GEN_FUNCS.keys())


def parse_spacing_params(s):
    d = {}
    for part in s.split(";"):
        k, v = part.split("=")
        try:
            v = float(v)
        except ValueError:
            pass
        d[k] = v
    return d


# Primary spacing parameter (heatmap/catalog axis) per family, and which secondary
# parameters exist (held fixed at a representative tested value, chosen the same way
# as the primary: median of the values actually swept) -- STATED HERE, not left
# implicit, since different families do not share one spacing parameterization.
PRIMARY_PARAM = {
    "square": "pitch_um", "hexagonal": "pitch_um",
    "concentric": "ring_spacing_um", "ring_offset_concentric": "ring_spacing_um",
    "fibonacci_spiral": "c_um", "golden_angle": "c_um", "archimedean_spiral": "c_um",
    "rectangular": "pitch_x_um", "poisson_disk": "spacing_factor",
    "jittered_lattice": "pitch_um",
}
SECONDARY_PARAMS = {
    "concentric": ["holes_per_ring0"], "ring_offset_concentric": ["holes_per_ring0"],
    "rectangular": ["pitch_y_um"], "jittered_lattice": ["jitter_fraction"],
}


def load_data():
    df = pd.read_csv(SWEEP_CSV)
    params = df.spacing_params.apply(parse_spacing_params)
    for key in set().union(*params.map(lambda d: d.keys())):
        df[f"param__{key}"] = params.map(lambda d: d.get(key, np.nan))
    return df


def median_tested_value(df, family, param_col):
    vals = sorted(df.loc[df.family == family, param_col].dropna().unique())
    if not vals:
        return None
    return vals[len(vals) // 2]


def representative_params(df, family):
    """Mid-range N and mid-range primary spacing value, both drawn from values ACTUALLY
    swept for this family (never invented) -- N: median of [20,50,100] tested -> 50.
    Secondary params (if any) fixed at their own median tested value, per-family."""
    N = median_tested_value(df, family, "N_requested")
    primary_col = f"param__{PRIMARY_PARAM[family]}"
    primary_val = median_tested_value(df, family, primary_col)
    secondary = {}
    for p in SECONDARY_PARAMS.get(family, []):
        secondary[p] = median_tested_value(df, family, f"param__{p}")
    return int(N), primary_val, secondary


def build_gen_kwargs(family, primary_val, secondary):
    """Translates (primary_val, secondary dict) into this family's own generate()
    kwargs -- each family's parameter NAMES differ, so this mapping is written out
    explicitly per family rather than assumed generic."""
    p = PRIMARY_PARAM[family]
    kwargs = {p: primary_val}
    if family == "rectangular":
        kwargs = {"pitch_x_um": primary_val, "pitch_y_um": secondary["pitch_y_um"]}
    elif family in ("concentric", "ring_offset_concentric"):
        kwargs["holes_per_ring0"] = int(secondary["holes_per_ring0"])
    elif family == "jittered_lattice":
        kwargs["jitter_fraction"] = secondary["jitter_fraction"]
    return kwargs


def load_a_hole_um(M):
    opt = pd.read_csv(PER_M_OPTIMUM_MAP_CSV)
    return float(opt.loc[opt.M_diopters == M, "acuity_optimal_um"].iloc[0])


# ============================================================================
# Section 1 -- Design Catalog
# ============================================================================

def plot_layout(ax, coords, a_hole_um, title):
    r = a_hole_um / 2.0
    for x, y in coords:
        ax.add_patch(Circle((x, y), r, facecolor="#4C72B0", edgecolor="none", alpha=0.75))
    ax.set_aspect("equal")
    if len(coords):
        span = max(np.abs(coords).max() * 1.15, r * 3)
    else:
        span = r * 3
    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("x (um)", fontsize=7)
    ax.set_ylabel("y (um)", fontsize=7)
    ax.tick_params(labelsize=6)


def section1_design_catalog(df, M_repr=4.0):
    a_hole_um = load_a_hole_um(M_repr)
    print(f"Section 1: representative M={M_repr}D, a_hole_um={a_hole_um}")

    deterministic = [f for f in FAMILIES if f not in STOCHASTIC_FAMILIES]
    ncols = 3
    nrows = -(-len(deterministic) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.0 * ncols, 4.0 * nrows), squeeze=False)
    catalog_meta = []
    for i, family in enumerate(deterministic):
        N, primary_val, secondary = representative_params(df, family)
        kwargs = build_gen_kwargs(family, primary_val, secondary)
        coords, meta = GEN_FUNCS[family](N=N, a_hole_um=a_hole_um, **kwargs)
        ax = axes[i // ncols][i % ncols]
        param_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        plot_layout(ax, coords, a_hole_um, f"{family}\nN={N}, {param_str}\n(N_actual={meta['N_actual']})")
        catalog_meta.append({"family": family, "N_requested": N, **kwargs,
                             "N_actual": meta["N_actual"], "a_hole_um": a_hole_um})
    for i in range(len(deterministic), nrows * ncols):
        axes[i // ncols][i % ncols].axis("off")
    fig.suptitle(f"Section 1: representative layouts, deterministic families "
                f"(M={M_repr}D, a_hole={a_hole_um:.0f}um; circles drawn to scale)")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(FIGS_DIR, "section1_deterministic_catalog.png")
    fig.savefig(out, dpi=140, facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")

    # Stochastic families: 3 seeds side-by-side, one row per family
    fig, axes = plt.subplots(len(STOCHASTIC_FAMILIES), 3, figsize=(4.0 * 3, 4.0 * len(STOCHASTIC_FAMILIES)),
                             squeeze=False)
    for r, family in enumerate(sorted(STOCHASTIC_FAMILIES)):
        N, primary_val, secondary = representative_params(df, family)
        kwargs = build_gen_kwargs(family, primary_val, secondary)
        param_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        for c, seed in enumerate([0, 1, 2]):
            coords, meta = GEN_FUNCS[family](N=N, a_hole_um=a_hole_um, seed=seed, **kwargs)
            plot_layout(axes[r][c], coords, a_hole_um,
                       f"{family} seed={seed}\nN={N}, {param_str}\n(N_actual={meta['N_actual']})")
            catalog_meta.append({"family": family, "N_requested": N, **kwargs, "seed": seed,
                                 "N_actual": meta["N_actual"], "a_hole_um": a_hole_um})
    fig.suptitle(f"Section 1: representative layouts, stochastic families, 3 seeds each "
                f"(M={M_repr}D, a_hole={a_hole_um:.0f}um; circles drawn to scale)")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(FIGS_DIR, "section1_stochastic_catalog.png")
    fig.savefig(out, dpi=140, facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")

    return pd.DataFrame(catalog_meta)


# ============================================================================
# Section 2 -- Margin Heatmaps
# ============================================================================

def cap_for_display(vals):
    v = np.array(vals, dtype=float)
    is_inf = ~np.isfinite(v)
    v_capped = np.where(is_inf, DISPLAY_MARGIN_CAP, np.clip(v, -DISPLAY_MARGIN_CAP, DISPLAY_MARGIN_CAP))
    return v_capped, is_inf


def compute_family_grid(df, family):
    """Shared grid builder, reused by the heatmap, the raw-data appendix table, and
    the per-family line plot -- ONE row per (N, primary spacing, M) for this family,
    covering EVERY tested point (safe or not), with secondary params fixed at their
    own median tested value (same convention as Section 1). For the two stochastic
    families, the seed dimension is collapsed to worst-case-across-seeds (min),
    matching compare/rank_by_family.py's own aggregation rule -- computed HERE
    directly from sweep_results.csv (all tested points), not from
    family_ranking.csv, which only contains rows that ended up structurally safe
    overall and would silently leave gaps at every unsafe (N, spacing, M) point for
    the stochastic families specifically (found and fixed while adding this
    function: the original heatmap code read family_ranking.csv for stochastic
    families, leaving blank cells wherever the worst seed failed).

    Returns (N_vals, p_vals, secondary_fixed, data) where data has columns
    [N_requested, primary_val, M, ghost_margin, vignetting_margin]."""
    primary_col = f"param__{PRIMARY_PARAM[family]}"
    sub = df[df.family == family].copy()
    secondary_fixed = {}
    for p in SECONDARY_PARAMS.get(family, []):
        col = f"param__{p}"
        val = median_tested_value(df, family, col)
        secondary_fixed[p] = val
        sub = sub[np.isclose(sub[col], val)]

    if family in STOCHASTIC_FAMILIES:
        rows = []
        for (N, pv, M), g in sub.groupby(["N_requested", primary_col, "M"]):
            rows.append({"N_requested": N, "primary_val": pv, "M": M,
                        "ghost_margin": float(np.min(g.worst_case_ghost_margin.values)),
                        "vignetting_margin": float(np.min(g.worst_case_vignetting_margin.values))})
        data = pd.DataFrame(rows)
    else:
        data = sub[["N_requested", primary_col, "M", "worst_case_ghost_margin",
                    "worst_case_vignetting_margin"]].rename(columns={
            primary_col: "primary_val", "worst_case_ghost_margin": "ghost_margin",
            "worst_case_vignetting_margin": "vignetting_margin"}).copy()

    N_vals = sorted(data.N_requested.unique())
    p_vals = sorted(data.primary_val.unique())
    return N_vals, p_vals, secondary_fixed, data


def section2_heatmaps(df, family):
    N_vals, p_vals, secondary_fixed, data = compute_family_grid(df, family)

    fig, axes = plt.subplots(2, len(M_ORDER), figsize=(2.6 * len(M_ORDER), 5.6))
    for row, metric in enumerate(["ghost_margin", "vignetting_margin"]):
        for col, M in enumerate(M_ORDER):
            ax = axes[row][col]
            msub = data[data.M.astype(str) == str(M)]
            grid = np.full((len(p_vals), len(N_vals)), np.nan)
            raw_grid = np.full((len(p_vals), len(N_vals)), np.nan)
            inf_mask = np.zeros_like(grid, dtype=bool)
            for _, r in msub.iterrows():
                i = p_vals.index(r.primary_val)
                j = N_vals.index(r.N_requested)
                val = r[metric]
                raw_grid[i, j] = val
                if not np.isfinite(val):
                    inf_mask[i, j] = True
                    grid[i, j] = DISPLAY_MARGIN_CAP
                else:
                    grid[i, j] = np.clip(val, -DISPLAY_MARGIN_CAP, DISPLAY_MARGIN_CAP)
            im = ax.imshow(grid, origin="lower", aspect="auto", cmap="RdYlGn",
                           vmin=-DISPLAY_MARGIN_CAP, vmax=DISPLAY_MARGIN_CAP)
            # RAW NUMBER ANNOTATION on every cell (not just color) -- the actual
            # worst_case_ghost_margin/worst_case_vignetting_margin value, not the
            # clipped display value, so the printed number is always the real one.
            for i in range(len(p_vals)):
                for j in range(len(N_vals)):
                    if inf_mask[i, j]:
                        ax.text(j, i, "inf", ha="center", va="center", fontsize=5.5, color="black")
                    elif np.isfinite(raw_grid[i, j]):
                        ax.text(j, i, f"{raw_grid[i, j]:.1f}", ha="center", va="center",
                               fontsize=5.5, color="black")
            ax.set_xticks(range(len(N_vals))); ax.set_xticklabels(N_vals, fontsize=6)
            ax.set_yticks(range(len(p_vals))); ax.set_yticklabels([f"{v:g}" for v in p_vals], fontsize=6)
            if row == 0:
                ax.set_title(f"M={M}" if M == "global" else f"M={M}D", fontsize=8)
            if col == 0:
                ax.set_ylabel(f"{PRIMARY_PARAM[family]}\n({'ghost' if row==0 else 'vignetting'})", fontsize=7)
            if row == 1:
                ax.set_xlabel("N", fontsize=7)
    sec_str = f" (fixed: {secondary_fixed})" if secondary_fixed else ""
    fig.suptitle(f"Section 2: {family} -- worst_case_ghost_margin (top row) and "
                f"worst_case_vignetting_margin (bottom row) vs (N, {PRIMARY_PARAM[family]}), "
                f"by M{sec_str}. Color clipped to [-{DISPLAY_MARGIN_CAP:.0f}, {DISPLAY_MARGIN_CAP:.0f}]; "
                f"cell text is the ACTUAL raw value (or 'inf' for zero active pairs), "
                f"never clipped.", fontsize=8, wrap=True)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    out = os.path.join(FIGS_DIR, f"section2_heatmap_{family}.png")
    fig.savefig(out, dpi=160, facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")
    return N_vals, p_vals, secondary_fixed


def section2_sign_agreement(df, family, secondary_fixed_unused=None):
    N_vals, p_vals, secondary_fixed, sub = compute_family_grid(df, family)

    def sign(v):
        if not np.isfinite(v):
            return 1
        return 1 if v > 0 else (-1 if v < 0 else 0)

    fig, axes = plt.subplots(1, len(M_ORDER), figsize=(2.3 * len(M_ORDER), 3.0))
    n_disagree_total = 0
    cmap_codes = {"both_pos": 0, "both_neg": 1, "disagree": 2}
    colors = ["#2ca02c", "#d62728", "#ff7f0e"]
    for col, M in enumerate(M_ORDER):
        ax = axes[col]
        msub = sub[sub.M.astype(str) == str(M)]
        grid = np.full((len(p_vals), len(N_vals)), np.nan)
        for _, r in msub.iterrows():
            i = p_vals.index(r.primary_val); j = N_vals.index(r.N_requested)
            sg, sv = sign(r.ghost_margin), sign(r.vignetting_margin)
            if sg >= 0 and sv >= 0:
                code = cmap_codes["both_pos"]
            elif sg < 0 and sv < 0:
                code = cmap_codes["both_neg"]
            else:
                code = cmap_codes["disagree"]
                n_disagree_total += 1
            grid[i, j] = code
        from matplotlib.colors import ListedColormap
        ax.imshow(grid, origin="lower", aspect="auto", cmap=ListedColormap(colors), vmin=0, vmax=2)
        ax.set_xticks(range(len(N_vals))); ax.set_xticklabels(N_vals, fontsize=6)
        ax.set_yticks(range(len(p_vals))); ax.set_yticklabels([f"{v:g}" for v in p_vals], fontsize=6)
        ax.set_title(f"M={M}" if M == "global" else f"M={M}D", fontsize=8)
        if col == 0:
            ax.set_ylabel(PRIMARY_PARAM[family], fontsize=7)
        ax.set_xlabel("N", fontsize=7)
    handles = [Line2D([0], [0], marker="s", color="w", markerfacecolor=c, markersize=10)
              for c in colors]
    fig.legend(handles, ["both margins positive", "both margins negative", "signs disagree"],
              loc="lower center", ncol=3, fontsize=7, bbox_to_anchor=(0.5, -0.05))
    fig.suptitle(f"Section 2: {family} -- ghost-margin-sign vs vignetting-margin-sign "
                f"agreement, by M. Disagreements found: {n_disagree_total}.", fontsize=8)
    fig.tight_layout(rect=[0, 0.06, 1, 0.88])
    out = os.path.join(FIGS_DIR, f"section2_signagreement_{family}.png")
    fig.savefig(out, dpi=140, facecolor="white")
    plt.close(fig)
    print(f"wrote {out} (disagreements: {n_disagree_total})")
    return n_disagree_total


def section2_lineplot(df, family):
    """Complementary GRAPHICAL view of the same Section 2 data as the heatmap: margin
    vs N, one line per tested primary-spacing value, faceted by M -- trends across N
    that a color grid can make hard to read directly (e.g. is margin monotonic in N?)
    are immediate on a line plot. Same underlying numbers as compute_family_grid, no
    new aggregation."""
    N_vals, p_vals, secondary_fixed, data = compute_family_grid(df, family)
    cmap = plt.cm.viridis(np.linspace(0, 1, max(len(p_vals), 1)))

    fig, axes = plt.subplots(2, len(M_ORDER), figsize=(2.3 * len(M_ORDER), 5.2), sharex=True)
    for row, metric in enumerate(["ghost_margin", "vignetting_margin"]):
        for col, M in enumerate(M_ORDER):
            ax = axes[row][col]
            msub = data[data.M.astype(str) == str(M)]
            for pi, pv in enumerate(p_vals):
                psub = msub[msub.primary_val == pv].sort_values("N_requested")
                if not len(psub):
                    continue
                raw = psub[metric].values.astype(float)
                yvals = np.where(np.isfinite(raw), np.clip(raw, -DISPLAY_MARGIN_CAP, DISPLAY_MARGIN_CAP),
                                 DISPLAY_MARGIN_CAP)
                ax.plot(psub.N_requested, yvals, marker="o", markersize=3, linewidth=1,
                       color=cmap[pi])
            ax.axhline(0.0, color="0.6", linewidth=0.6, linestyle="--")
            ax.set_xticks(N_vals)
            ax.tick_params(labelsize=6)
            if row == 0:
                ax.set_title(f"M={M}" if M == "global" else f"M={M}D", fontsize=8)
            if col == 0:
                ax.set_ylabel(f"{'ghost' if row==0 else 'vignetting'} margin\n(capped display)", fontsize=7)
            if row == 1:
                ax.set_xlabel("N", fontsize=7)
    handles = [Line2D([0], [0], color=cmap[i], marker="o", markersize=4) for i in range(len(p_vals))]
    fig.legend(handles, [f"{PRIMARY_PARAM[family]}={v:g}" for v in p_vals],
              loc="lower center", ncol=min(max(len(p_vals), 1), 6), fontsize=6.5, bbox_to_anchor=(0.5, -0.03))
    fig.suptitle(f"Section 2: {family} -- margin vs N, one line per "
                f"{PRIMARY_PARAM[family]} value, by M (same data as the heatmap above, "
                f"line view; capped to [-{DISPLAY_MARGIN_CAP:.0f},{DISPLAY_MARGIN_CAP:.0f}] "
                f"for display; dashed line marks margin=0).", fontsize=8, wrap=True)
    fig.tight_layout(rect=[0, 0.06, 1, 0.90])
    out = os.path.join(FIGS_DIR, f"section2_lineplot_{family}.png")
    fig.savefig(out, dpi=140, facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")


def write_family_raw_table_tex(family, N_vals, p_vals, data):
    """Raw number list backing this family's heatmap and line plot -- one row per
    tested (N, primary spacing, M) point, listing the exact (uncapped, uncolored)
    worst_case_ghost_margin / worst_case_vignetting_margin values. Written as ONE
    fully self-contained longtable environment (\\begin{longtable}...\\end{longtable}
    all in this single file, including \\bottomrule/\\endlastfoot) rather than body
    rows meant to be wrapped by a tabular in the calling .tex -- booktabs rule macros
    do not reliably track state across an \\input file boundary in this engine (the
    same class of bug fixed in exploration_summary_table_rows.tex, whose own
    \\bottomrule had to move inside the input file); keeping the whole environment in
    one file sidesteps that boundary entirely rather than re-risking it."""
    def fmt(v):
        return "inf" if not np.isfinite(v) else f"{v:.3f}"

    primary_name = str(PRIMARY_PARAM[family]).replace("_", "\\_")
    lines = []
    header = f"N & {primary_name} & M & ghost\\_margin & vignetting\\_margin \\\\"
    lines.append("\\begin{longtable}{rrrrr}")
    lines.append("\\caption{" + family.replace("_", "\\_") + ": raw "
                 "worst\\_case\\_ghost\\_margin and worst\\_case\\_vignetting\\_margin values "
                 "behind the heatmap and line plot above -- one row per tested $(N, " +
                 primary_name + ", M)$ point. `inf' = zero active hole pairs under the "
                 "pupil at that point (structurally safe, undisplayable on a linear scale).} \\\\")
    lines.append("\\toprule")
    lines.append(header)
    lines.append("\\midrule")
    lines.append("\\endfirsthead")
    lines.append("\\toprule")
    lines.append(header)
    lines.append("\\midrule")
    lines.append("\\endhead")
    lines.append("\\midrule")
    lines.append("\\multicolumn{5}{r}{\\itshape continued on next page} \\\\")
    lines.append("\\endfoot")
    lines.append("\\bottomrule")
    lines.append("\\endlastfoot")
    for pv in p_vals:
        for N in N_vals:
            for M in M_ORDER:
                cell = data[(data.N_requested == N) & (data.primary_val == pv) &
                           (data.M.astype(str) == str(M))]
                if not len(cell):
                    continue
                g = fmt(cell.iloc[0].ghost_margin)
                v = fmt(cell.iloc[0].vignetting_margin)
                m_str = "global" if M == "global" else f"{M:g}D"
                lines.append(f"{int(N)} & {pv:g} & {m_str} & {g} & {v} \\\\")
    lines.append("\\end{longtable}")
    out = os.path.join(HERE, f"section2_rawtable_{family}.tex")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


# ============================================================================
# Section 3 -- Seed Variance
# ============================================================================

def section3_seed_variance(df, M_repr=4.0):
    """M is held FIXED at M_repr (same representative value as Section 1) for the
    violin plot specifically -- pooling all M values into one violin was tried first
    and rejected: M-driven variation (M=0's forced near-zero ghosting vs M=8's much
    tighter margins) is far larger than seed-to-seed variation at fixed M, so pooling
    them drowns out the very thing this section exists to show. The std-vs-mean
    companion scatter below still reports every (N, spacing, M) point separately
    (each point's std is computed strictly ACROSS SEEDS at that one fixed M, never
    blended across M), so the full M range is still represented there, just not
    conflated within a single violin's spread."""
    for family in sorted(STOCHASTIC_FAMILIES):
        sub_all_M = df[df.family == family].copy()
        sub = sub_all_M[sub_all_M.M.astype(str) == str(M_repr)].copy()
        sub["combo"] = sub.N_requested.astype(str) + " | " + sub.spacing_params

        combos = sorted(sub.combo.unique())
        # keep the figure legible: sample every k-th combo if there are many
        max_combos_shown = 24
        if len(combos) > max_combos_shown:
            step = int(np.ceil(len(combos) / max_combos_shown))
            combos_shown = combos[::step]
        else:
            combos_shown = combos

        data = []
        for combo in combos_shown:
            vals = sub.loc[sub.combo == combo, "worst_case_ghost_margin"].values
            vals_capped = np.clip(np.where(np.isfinite(vals), vals, DISPLAY_MARGIN_CAP),
                                  -DISPLAY_MARGIN_CAP, DISPLAY_MARGIN_CAP)
            data.append(vals_capped)

        fig, ax = plt.subplots(figsize=(max(10, 0.4 * len(combos_shown)), 5))
        ax.violinplot(data, showmedians=True)
        ax.set_xticks(range(1, len(combos_shown) + 1))
        ax.set_xticklabels(combos_shown, rotation=90, fontsize=6)
        ax.axhline(0.0, color="0.5", linewidth=0.8, linestyle="--")
        ax.set_ylabel(f"worst_case_ghost_margin across seeds, M={M_repr}D (capped display)")
        ax.set_xlabel("(N | spacing_params) combination")
        ax.set_title(f"Section 3: {family} -- distribution of worst_case_ghost_margin across "
                    f"{sub.groupby('combo').seed.nunique().max()} seeds, per (N, spacing) point, "
                    f"AT FIXED M={M_repr}D (M held fixed so the spread shown is seed-driven only, "
                    f"not mixed with cross-M variation). {len(combos_shown)}/{len(combos)} combinations shown.",
                    fontsize=8, wrap=True)
        fig.tight_layout()
        out = os.path.join(FIGS_DIR, f"section3_violin_{family}.png")
        fig.savefig(out, dpi=140, facecolor="white")
        plt.close(fig)
        print(f"wrote {out}")

        # companion: std vs mean scatter, one point per (N, spacing, M) combo -- ALL M
        # (M=global excluded) shown here, unlike the violin above, since each point's
        # own std is computed strictly across seeds AT that point's one M value, never
        # blended across M -- see this function's own docstring.
        sub_companion = sub_all_M.copy()
        sub_companion["combo"] = sub_companion.N_requested.astype(str) + " | " + sub_companion.spacing_params
        mean_vals = sub_companion.groupby(["combo", "M"]).worst_case_ghost_margin.apply(
            lambda s: np.mean(np.clip(np.where(np.isfinite(s), s, DISPLAY_MARGIN_CAP),
                                      -DISPLAY_MARGIN_CAP, DISPLAY_MARGIN_CAP)))
        std_vals = sub_companion.groupby(["combo", "M"]).worst_case_ghost_margin.apply(
            lambda s: np.std(np.clip(np.where(np.isfinite(s), s, DISPLAY_MARGIN_CAP),
                                     -DISPLAY_MARGIN_CAP, DISPLAY_MARGIN_CAP)))
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(mean_vals.values, std_vals.values, s=14, alpha=0.6, color="#4C72B0")
        ax.set_xlabel("mean worst_case_ghost_margin across seeds (capped display)")
        ax.set_ylabel("std dev across seeds (capped display)")
        ax.set_title(f"Section 3: {family} -- seed-to-seed std vs mean margin, "
                    f"one point per (N, spacing, M) combination (no threshold drawn)", fontsize=8, wrap=True)
        fig.tight_layout()
        out = os.path.join(FIGS_DIR, f"section3_std_vs_mean_{family}.png")
        fig.savefig(out, dpi=140, facecolor="white")
        plt.close(fig)
        print(f"wrote {out}")


# ============================================================================
# Section 4 -- Density vs Safety
# ============================================================================

def compute_density(family, coords, N_actual):
    """Packing density = N_actual per unit area. AREA COMPUTATION, STATED PER FAMILY
    (irregular families have no closed-form lattice cell the way square/hex pitch
    does):
    - square, hexagonal, rectangular: area of the convex hull of the generated
      coordinates (a direct, family-agnostic measure of the region the array actually
      occupies -- for a lattice this converges to N_actual * cell_area for large N).
    - concentric, ring_offset_concentric, fibonacci_spiral, golden_angle,
      archimedean_spiral, poisson_disk, jittered_lattice: SAME convex-hull-area
      measure, for consistency across all 9 families -- a single, uniformly-applied
      definition rather than a different formula per family, so density values are
      directly comparable on one Section 4 axis. Degenerate cases (fewer than 3
      points, or collinear points -- convex hull undefined) return NaN density,
      excluded from the plot rather than assigned an arbitrary fallback area.
    """
    if len(coords) < 3:
        return np.nan
    try:
        hull = ConvexHull(coords)
        area_um2 = hull.volume  # scipy convention: .volume is area in 2D
    except Exception:
        return np.nan
    if area_um2 <= 0:
        return np.nan
    return N_actual / area_um2  # holes per um^2


def section4_density_vs_safety(df, catalog_meta):
    """Density is computed once per (family, N, spacing[, seed]) combination actually
    present in df, by regenerating that exact combination's coordinates (same
    generator, same parameters) and taking its convex-hull density -- not estimated
    or looked up, computed directly, tying every plotted point to a real generated
    layout."""
    m_targets = [4.0, "global"]
    print(f"Section 4: computing convex-hull density for every safe candidate "
          f"(this regenerates coordinates -- may take a moment)...")

    rows_by_family_combo = {}
    for family in FAMILIES:
        primary_col = f"param__{PRIMARY_PARAM[family]}"
        sub = df[(df.family == family)]
        cols = ["N_requested", primary_col] + [f"param__{p}" for p in SECONDARY_PARAMS.get(family, [])]
        if family in STOCHASTIC_FAMILIES:
            cols.append("seed")
        combos = sub[cols].drop_duplicates()
        for _, row in combos.iterrows():
            key = tuple(row[c] for c in cols)
            rows_by_family_combo.setdefault(family, []).append((key, cols))

    density_cache = {}
    for family in FAMILIES:
        for key, cols in rows_by_family_combo.get(family, []):
            kv = dict(zip(cols, key))
            N = int(kv["N_requested"])
            primary_val = kv[f"param__{PRIMARY_PARAM[family]}"]
            secondary = {p: kv[f"param__{p}"] for p in SECONDARY_PARAMS.get(family, [])}
            gen_kwargs = build_gen_kwargs(family, primary_val, secondary)
            call_kwargs = dict(gen_kwargs)
            if family in STOCHASTIC_FAMILIES:
                call_kwargs["seed"] = int(kv["seed"])
            # use M=4D's a_hole for density (a fixed, stated reference -- density is a
            # pure geometry property of the coordinate set at whatever a_hole the
            # candidate's own hard M uses; M=4D chosen as one consistent reference
            # across all candidates purely for this geometric recomputation, not
            # implying anything about the M axis of the safety data itself)
            coords, meta = GEN_FUNCS[family](N=N, a_hole_um=load_a_hole_um(4.0), **call_kwargs)
            dens = compute_density(family, coords, meta["N_actual"])
            cache_key = (family, N, primary_val, tuple(sorted(secondary.items())),
                        kv.get("seed"))
            density_cache[cache_key] = dens

    def lookup_density(r):
        family = r.family
        primary_val = r[f"param__{PRIMARY_PARAM[family]}"]
        secondary = tuple(sorted((p, r[f"param__{p}"]) for p in SECONDARY_PARAMS.get(family, [])))
        seed = r.seed if family in STOCHASTIC_FAMILIES and pd.notna(r.seed) else None
        return density_cache.get((family, int(r.N_requested), primary_val, secondary, seed), np.nan)

    for M in m_targets:
        sub = df[df.M.astype(str) == str(M)].copy()
        sub["density"] = sub.apply(lookup_density, axis=1)
        safe = sub[sub.structurally_safe & sub.density.notna()].copy()
        vals_capped, is_inf = cap_for_display(safe.worst_case_ghost_margin.values)
        safe["margin_display"] = vals_capped
        safe["is_inf"] = is_inf

        fig, ax = plt.subplots(figsize=(8, 6))
        families_present = sorted(safe.family.unique())
        cmap = plt.cm.tab10.colors
        for fi, family in enumerate(families_present):
            fsub = safe[safe.family == family]
            finite_mask = ~fsub.is_inf
            ax.scatter(fsub.density[finite_mask], fsub.margin_display[finite_mask],
                      s=18, alpha=0.7, color=cmap[fi % len(cmap)], label=family)
            ax.scatter(fsub.density[~finite_mask], fsub.margin_display[~finite_mask],
                      s=30, alpha=0.9, color=cmap[fi % len(cmap)], marker="^")
        ax.axhline(DISPLAY_MARGIN_CAP, color="0.6", linewidth=0.7, linestyle=":")
        ax.set_xlabel("packing density: N_actual / convex-hull area (holes / um^2)")
        ax.set_ylabel(f"worst_case_ghost_margin (capped at {DISPLAY_MARGIN_CAP:.0f}; "
                      f"triangle marker = actually +inf)")
        ax.set_title(f"Section 4: density vs. ghost margin, ALL structurally-safe "
                    f"candidates, M={M}" + ("D" if M != "global" else ""), fontsize=10)
        ax.legend(fontsize=7, ncol=2, markerscale=1.2)
        fig.tight_layout()
        out = os.path.join(FIGS_DIR, f"section4_density_vs_safety_M{M}.png")
        fig.savefig(out, dpi=140, facecolor="white")
        plt.close(fig)
        print(f"wrote {out} ({len(safe)} safe points plotted)")


# ============================================================================
# Section 5 -- Cross-Family Summary Table
# ============================================================================

def section5_summary_table(df):
    rows = []
    for family in FAMILIES:
        sub = df[df.family == family]
        n_tested = len(sub[["N_requested", "spacing_params"] +
                          (["seed"] if family in STOCHASTIC_FAMILIES else [])].drop_duplicates())
        n_safe = int(sub.structurally_safe.sum())
        finite = sub[np.isfinite(sub.worst_case_ghost_margin)]
        n_inf = int((~np.isfinite(sub.worst_case_ghost_margin)).sum())
        best_finite = float(finite.worst_case_ghost_margin.max()) if len(finite) else float("nan")

        row = {"family": family, "n_rows_tested": len(sub),
              "n_candidate_points": n_tested,
              "n_structurally_safe_rows": n_safe,
              "n_inf_margin_rows": n_inf,
              "best_finite_ghost_margin": best_finite}

        if family in STOCHASTIC_FAMILIES:
            # Computed directly from sweep_results.csv (ALL tested points), not from
            # family_ranking.csv -- that file only contains rows that ended up
            # structurally_safe overall (worst-case-across-seeds > 0), which silently
            # excludes exactly the high-variance points whose worst seed pulled the
            # aggregate below zero (found by inspection: e.g. poisson_disk
            # spacing_factor=3.0 shows seed outcomes spanning the full display range
            # in Section 3's violin plot, yet is absent from family_ranking.csv
            # because its worst-case-across-seeds is negative overall). "std observed"
            # should mean observed across everything tested, not only the safe subset.
            def std_across_seeds(s):
                v = s.values.astype(float)
                v_capped = np.where(np.isfinite(v), np.clip(v, -DISPLAY_MARGIN_CAP, DISPLAY_MARGIN_CAP),
                                    DISPLAY_MARGIN_CAP)
                return float(np.std(v_capped, ddof=0))
            per_point_std = sub.groupby(["N_requested", "spacing_params", "M"]).worst_case_ghost_margin.apply(
                std_across_seeds)
            row["mean_seed_std"] = float(per_point_std.mean()) if len(per_point_std) else float("nan")
            row["max_seed_std"] = float(per_point_std.max()) if len(per_point_std) else float("nan")
        else:
            row["mean_seed_std"] = float("nan")
            row["max_seed_std"] = float("nan")
        rows.append(row)

    summary = pd.DataFrame(rows)
    out_csv = os.path.join(HERE, "exploration_summary_table.csv")
    summary.to_csv(out_csv, index=False)
    print(f"wrote {out_csv}")

    # LaTeX table body rows, \input directly, not hand-typed
    lines = []
    for _, r in summary.iterrows():
        best_str = f"{r.best_finite_ghost_margin:.3f}" if np.isfinite(r.best_finite_ghost_margin) else "--"
        std_mean_str = f"{r.mean_seed_std:.3f}" if np.isfinite(r.mean_seed_std) else "--"
        std_max_str = f"{r.max_seed_std:.3f}" if np.isfinite(r.max_seed_std) else "--"
        fam_tex = r.family.replace("_", "\\_")
        lines.append(f"{fam_tex} & {int(r.n_candidate_points)} & {int(r.n_structurally_safe_rows)} & "
                    f"{best_str} & {int(r.n_inf_margin_rows)} & {std_mean_str} & {std_max_str} \\\\")
    # \bottomrule is emitted HERE, as the last line of the SAME \input'd file, not by
    # the wrapper .tex after the \input -- booktabs' rule macros track "are we
    # immediately after a row" internally, and that tracking does not survive a
    # \input file-boundary reliably in this engine (reproduced in isolation with a
    # trivial 2-row table: \bottomrule placed in the calling document right after
    # \input{...} throws "Misplaced \noalign" every time, regardless of the input
    # file's own content; moving \bottomrule inside the input file fixes it
    # immediately). Documented here since it is non-obvious and would otherwise look
    # like a content bug.
    lines.append("\\bottomrule")
    out_tex = os.path.join(HERE, "exploration_summary_table_rows.tex")
    with open(out_tex, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out_tex}")
    return summary


def write_section2_family_pages_tex(family_secondary_fixed):
    """Generates the LaTeX fragment THEORETICAL_DATASET_EXPLORATION.tex \\input's for
    Chapter 2 -- one \\section per family with its two figures, captions naming the
    actual fixed secondary-parameter values used (never hand-typed into the .tex)."""
    def esc(s):
        return str(s).replace("_", "\\_")

    lines = []
    for family in FAMILIES:
        secondary_fixed = family_secondary_fixed[family]
        sec_str = (", ".join(f"{esc(k)}={v}" for k, v in secondary_fixed.items()) + " held fixed at "
                  "its own median tested value; " if secondary_fixed else "")
        fam_tex = esc(family)
        lines.append(f"\\section{{{fam_tex}}}")
        lines.append(f"\\begin{{figure}}[h!]")
        lines.append(f"\\centering\\includegraphics[width=\\textwidth]"
                    f"{{figs_exploration/section2_heatmap_{family}.png}}")
        lines.append(f"\\caption{{{fam_tex}: worst\\_case\\_ghost\\_margin (top row) and "
                    f"worst\\_case\\_vignetting\\_margin (bottom row) vs.\\ $(N, "
                    f"\\text{{{esc(PRIMARY_PARAM[family])}}})$, by $M$. {sec_str}"
                    f"axes: $N \\in \\{{20,50,100\\}}$.}}")
        lines.append(f"\\end{{figure}}")
        lines.append(f"\\begin{{figure}}[h!]")
        lines.append(f"\\centering\\includegraphics[width=\\textwidth]"
                    f"{{figs_exploration/section2_signagreement_{family}.png}}")
        lines.append(f"\\caption{{{fam_tex}: ghost-margin-sign vs.\\ vignetting-margin-sign "
                    f"agreement, by $M$ (see the figure's own title for the exact "
                    f"disagreement count).}}")
        lines.append(f"\\end{{figure}}")
        lines.append(f"\\clearpage")
        lines.append(f"\\begin{{figure}}[h!]")
        lines.append(f"\\centering\\includegraphics[width=\\textwidth]"
                    f"{{figs_exploration/section2_lineplot_{family}.png}}")
        lines.append(f"\\caption{{{fam_tex}: same margin data as the heatmap above, "
                    f"shown as line plots (margin vs.\\ $N$, one line per "
                    f"{esc(PRIMARY_PARAM[family])} value) -- a complementary graphical "
                    f"view for reading trends across $N$ directly.}}")
        lines.append(f"\\end{{figure}}")
        lines.append(f"\\clearpage")
        lines.append(f"\\subsection*{{{fam_tex}: raw number list}}")
        lines.append(f"\\input{{section2_rawtable_{family}.tex}}")
        lines.append(f"\\clearpage")
        lines.append("")
    out = os.path.join(HERE, "section2_family_pages.tex")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    df = load_data()
    print(f"loaded {len(df)} rows, families: {sorted(df.family.unique())}")

    catalog_meta = section1_design_catalog(df)

    family_secondary_fixed = {}
    for family in FAMILIES:
        N_vals, p_vals, secondary_fixed = section2_heatmaps(df, family)
        section2_sign_agreement(df, family, secondary_fixed)
        section2_lineplot(df, family)
        _, _, _, grid_data = compute_family_grid(df, family)
        write_family_raw_table_tex(family, N_vals, p_vals, grid_data)
        family_secondary_fixed[family] = secondary_fixed
    write_section2_family_pages_tex(family_secondary_fixed)

    section3_seed_variance(df)

    section4_density_vs_safety(df, catalog_meta)

    section5_summary_table(df)

    print("\nAll figures/tables generated.")
