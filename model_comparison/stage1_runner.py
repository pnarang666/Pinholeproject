"""
Model 1: cornea-only exact ASM propagation (thin wrapper around stage1_v2 -- no
reimplementation of the physics, same rule pipeline_junction.py already follows).
"""

import os
import sys

_STAGE1_V2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage1_v2"))
if _STAGE1_V2_DIR not in sys.path:
    sys.path.insert(0, _STAGE1_V2_DIR)

import physics as _v2_physics  # noqa: E402


def cornea_blur(a_hole, wavelength, d_gap, ee_percent=50.0, N=1024, L=6e-3):
    """Returns r_EE(ee_percent) at the CORNEA plane -- exact ASM, no eye/lens/retina."""
    cfg = _v2_physics.RunConfig(a_hole=a_hole, wavelength=wavelength, z=d_gap, N=N, L=L, band_limit=True)
    result = _v2_physics.run_configuration(cfg)
    r_ee = _v2_physics.effective_radius(result, "EE", ee_percent=ee_percent)
    return {
        "r_EE_cornea": r_ee,
        "N_F": result["N_F"],
        "regime": result["regime"],
        "energy_conservation_rel_error": result["energy_conservation_error"],
        "all_checks_ok": all(c["ok"] for c in result["validation"]),
    }
