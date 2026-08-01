"""
Validates Phase 3 metrics against published/commercial reference values, and compares
the Stage-2-only optimum (minimize r_EE(P) alone) against Phase-3 optima under several
candidate human-vision-constrained metrics. Reuses model_comparison/'s already-
researched literature values rather than re-deriving them.
"""

import numpy as np
import pandas as pd

# Reference values researched for model_comparison/ (Phase 2) and reused here --
# see model_comparison/README.md "Literature and commercial comparison" for the
# original citations; restated here so stage3_human_vision has no import dependency
# on model_comparison/ (a sibling analysis folder, not a prerequisite).
CLINICAL_PINHOLE_RANGE_UM = (940, 1750)
CLINICAL_PINHOLE_TYPICAL_UM = 1200
COMMERCIAL_PINHOLE_GLASSES_RANGE_UM = (900, 1200)
CLINICAL_ACUITY_1200UM_5D_SNELLEN_DENOM = 30  # 20/30 at ~5D, 1.2mm aperture


def stage2_only_optimum(df, blur_col="r_EE_50_um", group_cols=("M_diopters",)):
    """The Stage-2-only answer: minimize retinal blur alone, per group (e.g. per M)."""
    rows = []
    for keys, g in df.groupby(list(group_cols)):
        idx = g[blur_col].idxmin()
        row = {"blur_col": blur_col, "a_hole_optimum_um": g.loc[idx, "a_hole_um"]}
        for col, val in zip(group_cols, keys if isinstance(keys, tuple) else (keys,)):
            row[col] = val
        rows.append(row)
    return pd.DataFrame(rows)


def phase3_optimum_by_metric(df, metric_specs, group_cols=("M_diopters",)):
    """
    metric_specs: dict of {label: (column, "min"|"max")}. Returns a DataFrame with
    the optimal a_hole under EACH candidate metric, per group -- the direct "which
    metric moves the optimum where" comparison the brief asks for.
    """
    rows = []
    for keys, g in df.groupby(list(group_cols)):
        row = {}
        for col, val in zip(group_cols, keys if isinstance(keys, tuple) else (keys,)):
            row[col] = val
        for label, (col, direction) in metric_specs.items():
            idx = g[col].idxmin() if direction == "min" else g[col].idxmax()
            row[f"a_hole_optimum_{label}_um"] = g.loc[idx, "a_hole_um"]
        rows.append(row)
    return pd.DataFrame(rows)


def compare_to_published(optimum_um_series):
    """
    For a series of predicted optima (um), reports whether/how far they fall from the
    clinical/commercial reference range -- honest distance reporting, not a pass/fail
    threshold tuned to make anything match.
    """
    lo, hi = CLINICAL_PINHOLE_RANGE_UM
    results = []
    for val in optimum_um_series:
        if val < lo:
            gap_pct = (lo - val) / lo * 100
            note = f"{gap_pct:.0f}% below the clinical range's lower bound ({lo}um)"
        elif val > hi:
            gap_pct = (val - hi) / hi * 100
            note = f"{gap_pct:.0f}% above the clinical range's upper bound ({hi}um)"
        else:
            note = "within the clinical/commercial range"
        results.append({"optimum_um": val, "note": note})
    return pd.DataFrame(results)
