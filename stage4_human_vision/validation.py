"""Validation statistics for Stage 4."""

import math

from scipy import stats as _scipy_stats


def regression_stats(observed, predicted):
    """
    Standard predicted-vs-observed agreement statistics: RMSE, MAE, R^2, and Pearson
    r with its two-sided p-value (added -- see stage4_human_vision/CHANGES.md; mirrors
    stage3_human_vision/validation_stats.py's use of scipy.stats.pearsonr and its
    n<3/constant-series guard, since correlation significance is not a meaningful
    concept in either case).
    """
    n = float(len(observed))
    if n == 0:
        return {"n": 0, "rmse": math.nan, "mae": math.nan, "r2": math.nan,
                "pearson_r": math.nan, "pearson_p_value": math.nan}

    residuals = [p - o for o, p in zip(observed, predicted)]
    mse = sum(r * r for r in residuals) / n
    mae = sum(abs(r) for r in residuals) / n
    obs_mean = sum(observed) / n
    ss_tot = sum((o - obs_mean) ** 2 for o in observed)
    ss_res = sum((p - o) ** 2 for o, p in zip(observed, predicted))
    cov = sum((o - obs_mean) * (p - sum(predicted) / n) for o, p in zip(observed, predicted))
    obs_var = sum((o - obs_mean) ** 2 for o in observed)
    pred_mean = sum(predicted) / n
    pred_var = sum((p - pred_mean) ** 2 for p in predicted)
    pearson = cov / math.sqrt(obs_var * pred_var) if obs_var > 0 and pred_var > 0 else math.nan

    if n < 3 or obs_var == 0 or pred_var == 0:
        pearson_p = math.nan
    else:
        _, pearson_p = _scipy_stats.pearsonr(list(observed), list(predicted))
        pearson_p = float(pearson_p)

    return {
        "n": int(n),
        "rmse": math.sqrt(mse),
        "mae": mae,
        "r2": 1.0 - ss_res / ss_tot if ss_tot > 0 else math.nan,
        "pearson_r": pearson,
        "pearson_p_value": pearson_p
    }
