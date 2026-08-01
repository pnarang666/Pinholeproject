"""
Generic regression/agreement statistics (RMSE, MAE, R^2, Pearson r) for comparing
this project's own predictions against published experimental data points. This is
the "Validation" stage of the project's pipeline (Wave Optics -> Image Quality ->
Human Vision -> Optimisation -> Validation) -- previously the only comparisons this
project made against literature/clinical data were qualitative ("how far from the
clinical range", validation.py::compare_to_published) or a rank correlation
(pareto.py::rank_correlation_with_reference). Nothing computed a direct
predicted-vs-observed regression-agreement statistic anywhere in the project before
this module.

First-principles statistics -- no literature citation needed for the FORMULAS
themselves (standard regression-diagnostic definitions, e.g. any statistics
textbook). What IS cited is the DATA being compared against; see literature.py
(e.g. 'ideal_pinhole_wang_2009') for that.
"""

import numpy as np
from scipy import stats


def regression_stats(predicted, observed):
    """
    Standard predicted-vs-observed agreement statistics:
      - RMSE (root-mean-square error, same units as the inputs)
      - MAE (mean absolute error, same units as the inputs)
      - R^2 (coefficient of determination, 1 - SS_res/SS_tot; can be negative if the
        predictions are worse than just predicting the observed mean)
      - Pearson r (linear correlation) and its two-sided p-value

    Requires n >= 2 (raises ValueError below that -- RMSE/MAE are undefined with
    fewer than 2 points, and there is nothing to compare). Pearson r/p are reported
    as NaN (not a crash, and not a fabricated number) when n < 3 or either series is
    constant, since correlation is not a meaningful concept in either case.
    """
    predicted = np.asarray(predicted, dtype=float)
    observed = np.asarray(observed, dtype=float)
    if predicted.shape != observed.shape:
        raise ValueError(f"predicted and observed must be the same shape, got "
                          f"{predicted.shape} vs {observed.shape}")
    n = len(predicted)
    if n < 2:
        raise ValueError(f"regression_stats needs at least 2 points, got {n}")

    resid = predicted - observed
    rmse = float(np.sqrt(np.mean(resid ** 2)))
    mae = float(np.mean(np.abs(resid)))

    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((observed - observed.mean()) ** 2))
    r_squared = (1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

    if n < 3 or np.std(predicted) == 0 or np.std(observed) == 0:
        pearson_r, pearson_p = float("nan"), float("nan")
    else:
        pearson_r, pearson_p = stats.pearsonr(predicted, observed)
        pearson_r, pearson_p = float(pearson_r), float(pearson_p)

    return {
        "n": n, "rmse": rmse, "mae": mae, "r_squared": r_squared,
        "pearson_r": pearson_r, "pearson_p_value": pearson_p,
    }
