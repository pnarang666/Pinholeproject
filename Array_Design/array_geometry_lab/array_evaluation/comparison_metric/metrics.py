"""
Two metrics, both operating on gate-survivor rows (see gates.py) -- neither metric
applies any gating itself, both assume the caller already ran apply_gates().

METRIC 1 (metric1_max_density): the single densest survivor per M (and 'global') --
a strict, single-winner view.

METRIC 2 (metric2_pareto_front): the full 2D Pareto front of (density, binding
margin) per M (and 'global') -- shows the whole density/safety-margin tradeoff rather
than collapsing it to one answer. By construction, Metric 1's winner for a given M is
always ALSO on Metric 2's front for that M (nothing can have both higher density AND
higher-or-equal binding margin than the single highest-density survivor, since nothing
has higher density at all) -- run_comparison.py checks this explicitly and flags it as
a bug if it ever fails.
"""
import numpy as np
import pandas as pd

DENSITY_COL = "packing_density_per_area_um-2"


def metric1_max_density(survivors):
    """Per M (and 'global'), the single row with the highest packing density. Rows
    with undefined density (NaN -- degenerate N_actual<3 hull, or a zero-area
    enclosing circle; see compute_density.py) cannot participate in a "max density"
    ranking by definition and are dropped first, group-by-group, not from the
    survivors DataFrame as a whole."""
    sub = survivors.dropna(subset=[DENSITY_COL])
    if len(sub) == 0:
        return sub.iloc[0:0]
    idx = sub.groupby("M")[DENSITY_COL].idxmax()
    return sub.loc[idx].sort_values("M").reset_index(drop=True)


def _binding_margin_with_sentinel(survivors):
    """binding_margin = elementwise min(worst_case_ghost_margin,
    worst_case_vignetting_margin) per row -- the tighter of the two safety margins,
    since a candidate is only as safe as its weaker gate. +inf values (zero active
    pairs -- a real, structurally-safe result, not missing data) are replaced by a
    finite SENTINEL for this Pareto comparison only: letting +inf itself into the
    comparison would make every +inf-margin row automatically co-dominant on the
    margin axis regardless of density, collapsing the density/margin tradeoff this
    metric exists to show. Sentinel = 10x the largest FINITE margin value (across
    both ghost and vignetting columns) observed in the survivors passed in -- large
    enough that any genuinely-infinite-margin row still ranks above every finite-
    margin row (preserving "structurally safe beats numerically safe" ordering), but
    finite, so it participates in ordinary dominance comparison instead of trivially
    dominating everything on the margin axis. Computed once per call (not per M
    group), from the WHOLE survivors set passed in, so the sentinel value is stable
    and reported once, not silently different panel to panel."""
    ghost = survivors.worst_case_ghost_margin.to_numpy(dtype=float)
    vign = survivors.worst_case_vignetting_margin.to_numpy(dtype=float)
    finite_vals = np.concatenate([ghost[np.isfinite(ghost)], vign[np.isfinite(vign)]])
    if len(finite_vals) == 0:
        # degenerate: every margin in the survivor set is +inf -- no finite value
        # exists to scale from, so fall back to an arbitrary positive sentinel (its
        # exact value is irrelevant here since every row ties on the margin axis
        # anyway, and ranking then falls entirely to density).
        sentinel = 1.0
    else:
        sentinel = 10.0 * float(np.max(finite_vals))
    ghost_s = np.where(np.isfinite(ghost), ghost, sentinel)
    vign_s = np.where(np.isfinite(vign), vign, sentinel)
    binding = np.minimum(ghost_s, vign_s)
    return binding, sentinel


def _pareto_front_2d(x, y):
    """Standard 2D Pareto-dominance filter, O(n^2), implemented directly (no external
    Pareto library -- unnecessary for a 2D front over a few hundred points at most).
    Point i is DOMINATED if some point j has x[j]>=x[i] AND y[j]>=y[i], with at least
    one strict inequality. Returns a boolean mask, True = on the front (not
    dominated)."""
    n = len(x)
    dominated = np.zeros(n, dtype=bool)
    for i in range(n):
        ge = (x >= x[i]) & (y >= y[i])
        gt = (x > x[i]) | (y > y[i])
        dominated[i] = np.any(ge & gt & (np.arange(n) != i))
    return ~dominated


def metric2_pareto_front(survivors):
    """Full Pareto front of (packing_density_per_area_um-2, binding_margin) per M
    (and 'global') -- every row on the front for its M, not just one. Rows with
    undefined density are dropped first (same reasoning as metric1_max_density: a
    NaN density cannot be compared for dominance)."""
    sub = survivors.dropna(subset=[DENSITY_COL]).copy()
    if len(sub) == 0:
        sub["binding_margin"] = pd.Series(dtype=float)
        sub["binding_margin_sentinel_used"] = pd.Series(dtype=float)
        return sub
    binding, sentinel = _binding_margin_with_sentinel(sub)
    sub["binding_margin"] = binding
    sub["binding_margin_sentinel_used"] = sentinel

    fronts = []
    for M, g in sub.groupby("M"):
        mask = _pareto_front_2d(g[DENSITY_COL].to_numpy(dtype=float), g.binding_margin.to_numpy(dtype=float))
        fronts.append(g[mask])
    out = pd.concat(fronts, ignore_index=True) if fronts else sub.iloc[0:0]
    return out.sort_values(["M", DENSITY_COL], ascending=[True, False]).reset_index(drop=True)
