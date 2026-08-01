"""
Human contrast-sensitivity models: Weber contrast, Rose-DeVries scaling, and two
published CSF parametrizations (photopic ~4 cpd peak; Mannos-Sakrison ~8 cpd peak) --
implemented as SIMPLIFIED, peak-location-matched curves per literature.py's stated
fidelity, not exact reproductions of a full multi-parameter model (e.g. Barten 1999).
"""

import numpy as np

import literature


def weber_contrast(L_target, L_background):
    """literature.get('weber_contrast')."""
    return abs(L_target - L_background) / L_background


def rose_devries_relative_sensitivity(photon_flux_density, reference_flux_density):
    """
    literature.get('rose_devries_law'). In the DeVries-Rose (mesopic/low-light) regime,
    detectable contrast threshold scales as 1/sqrt(flux) -- i.e. relative sensitivity
    (inverse threshold) scales as sqrt(flux). Returns sensitivity relative to a
    reference flux level, dimensionless. This reproduces the SCALING LAW exactly
    (first-principles Poisson SNR ~ sqrt(N)); it does not reproduce Rose's original
    absolute threshold constants.
    """
    if reference_flux_density <= 0 or photon_flux_density <= 0:
        return 0.0
    return np.sqrt(photon_flux_density / reference_flux_density)


def csf_photopic_peak(f_cpd, f_peak=4.0, bandwidth_octaves=2.0):
    """
    literature.get('csf_photopic_peak'). HEURISTIC log-parabola band-pass curve,
    normalized to 1 at f_peak, matched to the commonly reported photopic CSF peak
    (~4 cpd) and general band-pass shape -- NOT the full Barten (1999) model.
    """
    f_cpd = np.asarray(f_cpd, dtype=float)
    f_safe = np.where(f_cpd > 0, f_cpd, 1e-6)
    log_ratio = np.log2(f_safe / f_peak)
    return np.exp(-(log_ratio ** 2) / (2 * (bandwidth_octaves / 2.355) ** 2))


def csf_mannos_sakrison(f_cpd, f_peak=8.0, bandwidth_octaves=2.5):
    """
    literature.get('mannos_sakrison_csf'). Second CSF variant (peak ~8 cpd), same
    log-parabola functional form as csf_photopic_peak but a different peak location --
    offered per the brief's request to implement multiple accepted models where more
    than one exists in the literature, not because this project derived a second
    independent functional form.
    """
    return csf_photopic_peak(f_cpd, f_peak=f_peak, bandwidth_octaves=bandwidth_octaves)


CSF_MODELS = {
    "photopic_4cpd": csf_photopic_peak,
    "mannos_sakrison_8cpd": csf_mannos_sakrison,
}


def neural_contrast_threshold(f_cpd, csf_model="photopic_4cpd"):
    """Contrast threshold = 1 / CSF(f) -- the minimum contrast detectable at spatial
    frequency f_cpd under the chosen CSF model. Diverges as CSF->0 (very high/low f)."""
    csf = CSF_MODELS[csf_model](f_cpd)
    csf_safe = np.where(np.asarray(csf) > 1e-6, csf, 1e-6)
    return 1.0 / csf_safe
