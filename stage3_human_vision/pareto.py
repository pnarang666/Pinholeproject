"""
Multi-objective Pareto optimization over the metrics_sweep.csv grid. Standard,
first-principles Pareto-dominance computation (no external citation needed -- this is
a generic multi-objective optimization technique, not a vision-science-specific model).

Objectives handled (each direction-normalized so "higher is better" uniformly):
  - retinal blur (r_EE, RMS radius, MAR)         -> minimize (used as -value)
  - retinal illumination / photon flux            -> maximize
  - contrast / CSF-weighted visual Strehl          -> maximize
  - throughput                                    -> maximize
  - Strehl ratio                                  -> maximize (with the important
                                                      caveat from metrics.py: ill-posed
                                                      in this regime, included per the
                                                      brief's request but flagged)
  - MTF50                                         -> maximize
"""

import numpy as np
import pandas as pd


def pareto_front(df, objective_cols, maximize):
    """
    Returns a boolean Series marking which rows are Pareto-optimal (non-dominated)
    across `objective_cols`. `maximize` is a list of bools, same length as
    objective_cols, True where higher is better for that column.
    """
    values = df[objective_cols].to_numpy(dtype=float)
    n = len(values)
    sign = np.array([1.0 if m else -1.0 for m in maximize])
    signed = values * sign  # now "higher is always better" in every column

    is_dominated = np.zeros(n, dtype=bool)
    for i in range(n):
        if is_dominated[i]:
            continue
        # j dominates i if j is >= i in every objective and > in at least one
        ge_all = np.all(signed >= signed[i], axis=1)
        gt_any = np.any(signed > signed[i], axis=1)
        dominators = ge_all & gt_any
        dominators[i] = False
        if dominators.any():
            is_dominated[i] = True

    return pd.Series(~is_dominated, index=df.index, name="pareto_optimal")


def build_default_pareto(df, blur_col="r_EE_50_um", illumination_col="throughput_area_ratio",
                          quality_col="mtf50_cpd"):
    """
    Convenience wrapper for the three headline objectives explicitly named in the
    brief: retinal blur (minimize), retinal illumination/throughput (maximize), and
    an optical-quality proxy such as MTF50 (maximize). Returns df with a new
    'pareto_optimal' column.
    """
    objective_cols = [blur_col, illumination_col, quality_col]
    maximize = [False, True, True]
    mask = pareto_front(df, objective_cols, maximize)
    out = df.copy()
    out["pareto_optimal"] = mask
    return out


def rank_correlation_with_reference(df, candidate_cols, reference_col):
    """
    Spearman rank correlation between each candidate optimization metric's own
    per-configuration OPTIMUM (the a_hole that minimizes/maximizes it, grouped by
    every other varying column) and a reference column (e.g. a literature/commercial
    aperture value repeated as a constant, or an experimentally-observed acuity).
    Used by comparison.py's "which metric correlates best with experiment" analysis --
    implemented here as a generic, reusable utility, not hardcoded to one dataset.
    """
    from scipy import stats
    correlations = {}
    for col in candidate_cols:
        if df[col].nunique() < 2 or df[reference_col].nunique() < 2:
            correlations[col] = None
            continue
        rho, p = stats.spearmanr(df[col], df[reference_col])
        correlations[col] = {"rho": rho, "p_value": p}
    return correlations
