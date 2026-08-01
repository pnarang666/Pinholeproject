"""Visual Strehl calculations."""

import numpy as np


def compute_vsotf(freq_cpd, otf_real, ref_freq_cpd, ref_otf_real, neural_weights):
    freq_cpd = np.asarray(freq_cpd, dtype=float)
    otf_real = np.asarray(otf_real, dtype=float)
    ref_freq_cpd = np.asarray(ref_freq_cpd, dtype=float)
    ref_otf_real = np.asarray(ref_otf_real, dtype=float)
    neural_weights = np.asarray(neural_weights, dtype=float)

    common_freq = freq_cpd
    ref_interp = np.interp(common_freq, ref_freq_cpd, ref_otf_real)
    num = np.trapz(otf_real * neural_weights, common_freq)
    den = np.trapz(ref_interp * neural_weights, common_freq)
    return {
        "vsotf": float(num / den) if abs(den) > 1e-12 else 0.0,
        "numerator": float(num),
        "denominator": float(den)
    }
