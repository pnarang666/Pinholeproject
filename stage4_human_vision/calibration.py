"""
Small-sample linear calibration for the recommended acuity predictor:
logmar_calibrated = a * logmar_recommended + b.

With only n=5 (Wang 2009's aperture count) real clinical points to calibrate against,
fitting a,b and evaluating on the SAME 5 points would overfit and report a falsely
good R^2 -- see RESULTS.md. This module only provides the fitting/cross-validation
mechanics; stage4_human_vision/validation.py's existing regression_stats() is reused
for all reported statistics, not duplicated here.

First-principles statistics (ordinary least squares, leave-one-out) -- no literature
citation needed for the fitting PROCEDURE itself, same reasoning as
stage3_human_vision/validation_stats.py's own docstring. What IS cited is the DATA
being fit/validated against (see literature.py).
"""


def fit_linear_calibration(raw_values, observed_values):
    """Ordinary least squares fit of observed = a*raw + b. Returns (a, b)."""
    n = len(raw_values)
    if n < 2:
        raise ValueError("need at least 2 points to fit a linear calibration")
    mean_x = sum(raw_values) / n
    mean_y = sum(observed_values) / n
    var_x = sum((x - mean_x) ** 2 for x in raw_values)
    if var_x == 0:
        raise ValueError("raw_values has zero variance -- cannot fit a slope")
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(raw_values, observed_values))
    a = cov / var_x
    b = mean_y - a * mean_x
    return a, b


def apply_calibration(raw_value, a, b):
    return a * raw_value + b


def leave_one_out_predictions(raw_values, observed_values):
    """
    For each point i: fit (a,b) on all OTHER n-1 points, predict point i with that
    fit. Returns held-out predictions in the same order as the inputs -- the honest
    way to validate a linear calibration this small (see RESULTS.md).
    """
    n = len(raw_values)
    predictions = []
    for i in range(n):
        train_raw = raw_values[:i] + raw_values[i + 1:]
        train_obs = observed_values[:i] + observed_values[i + 1:]
        a, b = fit_linear_calibration(train_raw, train_obs)
        predictions.append(apply_calibration(raw_values[i], a, b))
    return predictions


def leave_one_group_out_predictions(raw_values, observed_values, group_ids):
    """
    Same idea, but holds out an entire GROUP at a time (e.g. every M-sensitivity
    replicate of one aperture) rather than a single row. Needed whenever the same
    real observation appears more than once in the input arrays (once per candidate
    M here) -- plain row-wise leave-one-out would leak that observation's value into
    the training fold through its OTHER replicates, inflating the held-out score.
    """
    predictions = [None] * len(raw_values)
    for held_out_group in sorted(set(group_ids)):
        train_raw = [x for x, g in zip(raw_values, group_ids) if g != held_out_group]
        train_obs = [y for y, g in zip(observed_values, group_ids) if g != held_out_group]
        a, b = fit_linear_calibration(train_raw, train_obs)
        for idx, (x, g) in enumerate(zip(raw_values, group_ids)):
            if g == held_out_group:
                predictions[idx] = apply_calibration(x, a, b)
    return predictions
