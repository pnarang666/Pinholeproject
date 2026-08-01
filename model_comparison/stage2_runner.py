"""
Model 2: full cornea -> pupil -> lens -> retina exact ASM chain with the axial-myopia
model (thin wrapper around stage2 -- no reimplementation; imports stage2's own modules).
"""

import os
import sys

_STAGE2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage2"))
if _STAGE2_DIR not in sys.path:
    sys.path.insert(0, _STAGE2_DIR)

import phase2_retina as _p2  # noqa: E402
import myopia_axial as _myopia  # noqa: E402


def retina_blur(a_hole, wavelength, d_gap, M_diopters, P0=60.0, n_prime=1.336,
                 D_pupil_um=4000.0, refractive_index_correction=True, N=2048, L_mm=6.0):
    """Returns r_EE(50/80/90) at the RETINA plane -- full exact-ASM chain, real defocus."""
    result = _p2.run_pipeline_point(
        a_hole=a_hole, wavelength=wavelength, d_gap=d_gap, grid_N=N, window_L_mm=L_mm,
        M_diopters=M_diopters, P0=P0, n_prime=n_prime, D_pupil_um=D_pupil_um,
        refractive_index_correction=refractive_index_correction,
    )
    out = {
        "junction_check_passed": result["junction_check_passed"],
        "junction_fail_reason": result["junction_fail_reason"],
        "v_r": result["myopia"]["L_ax"], "v_f": result["myopia"]["f_eye"],
        "r_EE_50_retina": None, "r_EE_80_retina": None, "r_EE_90_retina": None,
    }
    if result["junction_check_passed"]:
        out["r_EE_50_retina"] = result["retina_EE"]["r_EE_50"]
        out["r_EE_80_retina"] = result["retina_EE"]["r_EE_80"]
        out["r_EE_90_retina"] = result["retina_EE"]["r_EE_90"]
    return out
