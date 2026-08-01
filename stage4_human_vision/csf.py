"""Contrast sensitivity models used by Stage 4."""

import math

import numpy as np

from .config import load_default_config


def watson_normalized_csf(f_cpd, config=None):
    """
    Compact normalized Watson-style template.

    This is a lightweight band-pass template suitable for comparative weighting when
    the full multi-channel Watson-Ahumada detector is out of scope.
    """
    config = config or load_default_config()
    f_cpd = np.asarray(f_cpd, dtype=float)
    f_safe = np.where(f_cpd > 0, f_cpd, 1e-9)
    log_ratio = np.log2(f_safe / config.csf.watson_peak_cpd)
    sigma = config.csf.watson_bandwidth_octaves / 2.355
    return np.exp(-(log_ratio ** 2) / (2.0 * sigma ** 2))


def mannos_sakrison_csf(f_cpd, config=None):
    config = config or load_default_config()
    f_cpd = np.asarray(f_cpd, dtype=float)
    positive = np.where(f_cpd > 0, f_cpd, 0.0)
    base = config.csf.mannos_offset + config.csf.mannos_slope * positive
    exponent = -np.power(config.csf.mannos_slope * positive, config.csf.mannos_exponent)
    return config.csf.mannos_scale * base * np.exp(exponent)


def barten_simplified_csf(f_cpd, luminance_cdm2, field_diameter_deg, config=None):
    """
    Barten-inspired simplified CSF engineering form.

    The parameterization follows the commonly used luminance-dependent closed form
    reported as a simplification of Barten's 1999 model.
    """
    config = config or load_default_config()
    f_cpd = np.asarray(f_cpd, dtype=float)
    L = max(luminance_cdm2, 1e-6)
    w = max(field_diameter_deg, 1e-6)
    a = 540.0 * math.pow(1.0 + 0.7 / L, -0.2)
    a /= (1.0 + 12.0 * np.power(1.0 + f_cpd / 3.0, -2.0) / w)
    b = 0.3 * math.pow(1.0 + 100.0 / L, 0.15)
    c = config.csf.barten_c
    positive = np.where(f_cpd > 0, f_cpd, 0.0)
    return a * positive * np.exp(-b * positive) * np.sqrt(1.0 + c * np.exp(b * positive))


def evaluate_csf_models(f_cpd, luminance_cdm2, field_diameter_deg, config=None):
    config = config or load_default_config()
    models = {
        "barten": barten_simplified_csf(f_cpd, luminance_cdm2, field_diameter_deg, config),
        "mannos_sakrison": mannos_sakrison_csf(f_cpd, config),
        "watson_normalized": watson_normalized_csf(f_cpd, config)
    }
    summary = {}
    for name, values in models.items():
        peak_index = int(np.argmax(values))
        summary[name] = {
            "values": np.asarray(values, dtype=float).tolist(),
            "peak_sensitivity": float(values[peak_index]),
            "peak_frequency_cpd": float(f_cpd[peak_index]),
            "cutoff_frequency_cpd": float(_cutoff_frequency(f_cpd, values))
        }
    return summary


def weight_mtf_with_csf(freq_cpd, mtf, csf_values):
    freq_cpd = np.asarray(freq_cpd, dtype=float)
    mtf = np.asarray(mtf, dtype=float)
    csf_values = np.asarray(csf_values, dtype=float)
    weighted = mtf * csf_values
    return {
        "weighted_mtf": weighted.tolist(),
        "area": float(np.trapz(weighted, freq_cpd))
    }


def _cutoff_frequency(freq_cpd, values):
    values = np.asarray(values, dtype=float)
    freq_cpd = np.asarray(freq_cpd, dtype=float)
    below = values < 1.0
    if not below.any():
        return freq_cpd[-1]
    idx = int(np.argmax(below))
    return freq_cpd[idx]
