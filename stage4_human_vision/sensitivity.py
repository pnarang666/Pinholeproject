"""Sensitivity-analysis helpers."""


def centered_fractional_sensitivity(func, base_value, frac_step=0.05):
    delta = max(abs(base_value) * frac_step, frac_step)
    lower = func(base_value - delta)
    center = func(base_value)
    upper = func(base_value + delta)
    derivative = (upper - lower) / (2.0 * delta)
    normalized = derivative * base_value / center if center not in (0, None) else None
    return {
        "lower": lower,
        "center": center,
        "upper": upper,
        "derivative": derivative,
        "normalized_sensitivity": normalized
    }
