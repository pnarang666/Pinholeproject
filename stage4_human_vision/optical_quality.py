"""Optical quality metrics computed from the retinal PSF."""

import os
import sys

import numpy as np

_STAGE3_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage3_human_vision"))
if _STAGE3_DIR not in sys.path:
    sys.path.insert(0, _STAGE3_DIR)

import metrics as stage3_metrics  # noqa: E402


def compute_optical_quality(psf, dx_m, v_r_m, diffraction_reference_psf=None):
    f_cpum, mtf_1d = stage3_metrics.mtf_radial(psf, dx_m)
    _, otf_1d = stage3_metrics.otf_radial(psf, dx_m)
    _, ptf_1d = stage3_metrics.ptf_radial(psf, dx_m)
    mtf50_cpum, mtf10_cpum = stage3_metrics.mtf50_mtf10(psf, dx_m)
    out = {
        "rms_spot_radius_um": stage3_metrics.rms_spot_radius(psf, dx_m) * 1e6,
        "mtf_frequency_cpd": stage3_metrics.cycles_per_um_to_cycles_per_degree(f_cpum, v_r_m).tolist(),
        "mtf": mtf_1d.tolist(),
        "otf_real": np.real(otf_1d).tolist(),
        "otf_imag": np.imag(otf_1d).tolist(),
        "ptf_rad": ptf_1d.tolist(),
        "mtf50_cpd": stage3_metrics.cycles_per_um_to_cycles_per_degree(mtf50_cpum, v_r_m),
        "mtf10_cpd": stage3_metrics.cycles_per_um_to_cycles_per_degree(mtf10_cpum, v_r_m)
    }
    if diffraction_reference_psf is not None:
        out["strehl_ratio"] = stage3_metrics.strehl_ratio(psf, diffraction_reference_psf)
    return out
