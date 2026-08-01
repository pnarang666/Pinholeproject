"""Mirrors stage3_human_vision/contrast.py's CSF models verbatim (see that file for
full citations: literature.get('csf_photopic_peak'), literature.get('mannos_sakrison_csf')).
Copied rather than imported cross-package to keep this folder's dependency graph
self-contained, per the same reasoning stage2_fixed/metrics_mtf.py in this folder
already documents."""
import numpy as np

def csf_photopic_peak(f_cpd, f_peak=4.0, bandwidth_octaves=2.0):
    f_cpd = np.asarray(f_cpd, dtype=float)
    f_safe = np.where(f_cpd > 0, f_cpd, 1e-6)
    log_ratio = np.log2(f_safe / f_peak)
    return np.exp(-(log_ratio ** 2) / (2 * (bandwidth_octaves / 2.355) ** 2))

def csf_mannos_sakrison(f_cpd, f_peak=8.0, bandwidth_octaves=2.5):
    return csf_photopic_peak(f_cpd, f_peak=f_peak, bandwidth_octaves=bandwidth_octaves)

CSF_MODELS = {"photopic_4cpd": csf_photopic_peak, "mannos_sakrison_8cpd": csf_mannos_sakrison}

def neural_contrast_threshold(f_cpd, csf_model="photopic_4cpd"):
    csf = CSF_MODELS[csf_model](f_cpd)
    csf_safe = np.where(np.asarray(csf) > 1e-6, csf, 1e-6)
    return 1.0 / csf_safe
