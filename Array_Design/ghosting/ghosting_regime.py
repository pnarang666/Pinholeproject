"""
Implements Eq. (5) from THEORY.md: a three-regime ghosting-perceptibility classifier
for a multi-hole pinhole array, replacing the old crude s < r_EE(P)*d_gap/v_r check.

Regime A (sparse):  N_eff(worst-case alignment) <= 1 -- no second hole simultaneously
                     active, no ghosting possible regardless of blur/frequency.
Regime B (dense):   MTF(f0) < CSF^-1(f0) -- the ripple frequency is already
                     optically/perceptually suppressed even though many holes ARE
                     simultaneously active.
Regime C (danger):  neither holds -- a small number (>1) of holes simultaneously
                     active AND the ripple sits where it's neither optically filtered
                     nor below the CSF threshold. Candidate mechanism for real
                     reported ghosting (Kim et al. 2017 MPH glasses, THEORY.md Sec 2.2).

Reuses, unmodified: stage2_fixed/phase2_retina.py (run_pipeline_point, which itself
reuses stage1_v2/physics.py), this folder's metrics_mtf.py (mtf_radial, verbatim from
stage3_human_vision/metrics.py) and contrast.py (CSF models, verbatim from
stage3_human_vision/contrast.py), and Array_Design/photometry/array_photometry.py
(n_holes_exact_sweep_alignment; was stage_array/array_photometry.py before the
Array_Design consolidation -- same file, moved, not modified).
No new wave-optics physics is invented here --
only the Eq. (5) classification logic itself.

*** KNOWN, TESTED LIMITATION (see RESULTS.md) ***: every ghosting ripple frequency
this project's actual near-eye geometry produces (d_gap~12mm, v_r~22-24mm, pitch
0.7-4.8mm) falls BELOW 0.3 cycles/degree -- far outside the range the implemented
CSF models (csf_photopic_peak, peaked at 4 cpd; csf_mannos_sakrison, peaked at 8 cpd)
were fit or validated for. At these frequencies the log-parabola CSF model predicts
a physically implausible near-zero sensitivity (detection threshold >100,000x
contrast), which makes Regime B trivially satisfied whenever N_eff>1 -- Regime C
was NEVER triggered across a full test sweep as a direct consequence. Do not trust
the B/C boundary quantitatively until the CSF term is replaced with a model actually
valid at sub-1-cpd frequencies (e.g. a real Barten (1999) implementation, or digitized
low-frequency CSF data such as Campbell & Robson 1968, which extends down to ~0.5 cpd
with real measured data rather than an extrapolated fitted peak).
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "stage2_fixed"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "photometry"))
sys.path.insert(0, os.path.dirname(__file__))

import phase2_retina as p2
from metrics_mtf import mtf_radial, cycles_per_um_to_cycles_per_degree, interp_mtf_at_freq
from contrast import neural_contrast_threshold  # heuristic, kept for comparison
from contrast_barten import csf_threshold_barten  # real Barten 1999 model, used by default now
from array_photometry import n_holes_exact_sweep_alignment


def ghost_ripple_frequency(pitch_um, d_gap_um, v_r_um):
    """
    f0 = 1/delta_r (Eq. 1: delta_r = s*v_r/d_gap), returned as BOTH cycles/um
    (retina-plane, for MTF interpolation) and cycles/degree (for CSF lookup, since
    CSF is always tabulated in cycles/degree of visual angle).
    """
    delta_r_um = pitch_um * (v_r_um / d_gap_um)
    f0_cpum = 1.0 / delta_r_um
    um_per_degree = (v_r_um * 1e-6) * (np.pi / 180.0) * 1e6  # v_r um -> m -> back to um/degree
    f0_cpd = f0_cpum * um_per_degree
    return f0_cpum, f0_cpd


def classify_ghosting_regime(a_hole_um, pitch_um, D_pupil_um, wavelength_nm, d_gap_mm,
                              M_diopters, P0=60.0, n_prime=1.336,
                              refractive_index_correction=True, grid_N=2048,
                              window_L_mm=6.0, csf_model="barten_1999",
                              packing="square", n_offsets=15, scene_luminance_cdm2=10000.0,
                              field_deg=10.0):
    """Returns a dict: regime ('A'/'B'/'C'/None), and the numbers that decided it."""
    n_min, n_mean, n_max = n_holes_exact_sweep_alignment(pitch_um, D_pupil_um, packing=packing, n_offsets=n_offsets)
    if n_min <= 1:
        return {"regime": "A", "N_eff_worst": n_min, "N_eff_mean": n_mean,
                "f0_cpd": None, "mtf_f0": None, "csf_threshold_contrast": None,
                "reason": "N_eff(worst-case)<=1: no second hole simultaneously active"}

    result = p2.run_pipeline_point(
        a_hole=a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9, d_gap=d_gap_mm * 1e-3,
        grid_N=grid_N, window_L_mm=window_L_mm, M_diopters=M_diopters, P0=P0,
        n_prime=n_prime, D_pupil_um=D_pupil_um, refractive_index_correction=refractive_index_correction,
    )
    if not result["junction_check_passed"]:
        return {"regime": None, "N_eff_worst": n_min, "N_eff_mean": n_mean,
                "f0_cpd": None, "mtf_f0": None, "csf_threshold_contrast": None,
                "reason": f"junction check failed: {result['junction_fail_reason']}"}

    I_retina = result["I_retina"]
    dx = result["cornea_result"]["dx"]
    v_r_um = result["myopia"]["L_ax"] * 1e6

    f_centers_cpum, mtf_1d = mtf_radial(I_retina, dx)
    f0_cpum, f0_cpd = ghost_ripple_frequency(pitch_um, d_gap_mm * 1e3, v_r_um)
    mtf_at_f0 = interp_mtf_at_freq(f_centers_cpum, mtf_1d, f0_cpum)
    if csf_model == "barten_1999":
        csf_threshold_contrast = csf_threshold_barten(f0_cpd, scene_luminance_cdm2, field_deg)
    else:
        csf_threshold_contrast = float(np.asarray(neural_contrast_threshold(f0_cpd, csf_model)))
    is_regime_b = mtf_at_f0 < csf_threshold_contrast

    return {
        "regime": "B" if is_regime_b else "C",
        "N_eff_worst": n_min, "N_eff_mean": n_mean,
        "f0_cpd": f0_cpd, "mtf_f0": mtf_at_f0, "csf_threshold_contrast": csf_threshold_contrast,
        "reason": ("MTF(f0) below CSF detection threshold" if is_regime_b else
                   "N_eff>1 AND MTF(f0) still above CSF threshold -- danger zone"),
    }
