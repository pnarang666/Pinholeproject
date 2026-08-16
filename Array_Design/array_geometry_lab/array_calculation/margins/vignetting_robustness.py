"""
Re-runs the active-pairs/ghost-margin enumeration at gaze angles phi != 0, using the
copied Chapter 13 pupil-shift geometry (engine/vignetting_overlap.py), and reports the
WORST-CASE margin across the whole phi range -- not just the phi=0 result
evaluation/ghost_margin.py itself computes.

Gaze is modelled along a single axis (x), matching array_optimization/vignetting.py's own
convention (a single scalar phi sweep) -- the pupil's center shifts to
(pupil_shift_um(phi, R_rot_mm), 0) relative to the pattern's own centroid at phi=0.

This module does NOT compute per-hole vignetting TRANSMISSION (T_hole(phi), the
overlap-area-weighted quantity array_optimization/vignetting.py itself reports) -- that
is a brightness-adjacent quantity and out of scope per this folder's own "no
transmission/brightness anywhere" rule. What IS in scope, and what this module computes,
is purely geometric: does the set of ACTIVE HOLE PAIRS (and therefore the worst-case
ghost margin) change as the pupil shifts with gaze, independent of how much light any
given hole passes.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
import vignetting_overlap as vo  # noqa: E402
sys.path.insert(0, HERE)
import ghost_margin as gm  # noqa: E402

DEFAULT_PHI_MIN_DEG = -25.0
DEFAULT_PHI_MAX_DEG = 25.0
DEFAULT_PHI_STEP_DEG = 5.0  # matches array_optimization/vignetting.py's own default and
                            # its stated justification (resolves the Rp+Rh transition
                            # scale with >~10 samples across +/-25deg)


def phi_grid(phi_min_deg=DEFAULT_PHI_MIN_DEG, phi_max_deg=DEFAULT_PHI_MAX_DEG,
            phi_step_deg=DEFAULT_PHI_STEP_DEG):
    return np.arange(phi_min_deg, phi_max_deg + 1e-9, phi_step_deg)


def worst_case_across_phi(coords_um, D_pupil_um, M_diopters, a_hole_um,
                          resolvable_blur_um=None, P0=60.0,
                          R_rot_mm=vo.DEFAULT_R_ROT_MM,
                          phi_min_deg=DEFAULT_PHI_MIN_DEG, phi_max_deg=DEFAULT_PHI_MAX_DEG,
                          phi_step_deg=DEFAULT_PHI_STEP_DEG,
                          active_frac_threshold=None):
    """Sweeps phi, shifts the pupil center via the copied Delta(phi)=R_rot*sin(phi)
    mapping, and re-evaluates worst_case_ghost_margin at each shifted position. Returns
    the worst (minimum) margin across the whole phi range, plus which phi achieved it,
    plus the full per-phi breakdown for auditing.

    ALSO returns min_illuminated_area_um2_across_phi (audit fix, Gate 3/viability):
    the MINIMUM of total_illuminated_area_um2 across the entire tested phi range --
    directly analogous to worst_case_vignetting_margin itself (also a worst-across-phi
    summary), and exactly what gate_viability needs: Gate 3's requirement is
    total_illuminated_area_um2 > 0 at EVERY tested phi, which is equivalent to (and
    checked via) this minimum being > 0."""
    if resolvable_blur_um is None:
        resolvable_blur_um = gm.load_resolvable_blur_um(M_diopters, a_hole_um)

    kwargs = {}
    if active_frac_threshold is not None:
        kwargs["active_frac_threshold"] = active_frac_threshold

    phis = phi_grid(phi_min_deg, phi_max_deg, phi_step_deg)
    rows = []
    for phi in phis:
        shift_um = float(vo.pupil_shift_um(phi, R_rot_mm))
        pupil_center = (shift_um, 0.0)
        r = gm.worst_case_ghost_margin(coords_um, D_pupil_um, M_diopters, a_hole_um,
                                       resolvable_blur_um=resolvable_blur_um, P0=P0,
                                       pupil_center_um=pupil_center, **kwargs)
        r["phi_deg"] = float(phi)
        r["in_validated_phi_range"] = bool(vo.phi_in_validated_range(phi))
        r["pupil_shift_um"] = shift_um
        rows.append(r)

    worst_row = min(rows, key=lambda r: r["worst_case_margin"])
    min_illuminated_area = min(r["total_illuminated_area_um2"] for r in rows)
    return {
        "worst_case_vignetting_margin": worst_row["worst_case_margin"],
        "worst_case_phi_deg": worst_row["phi_deg"],
        "phi_range_deg": (float(phi_min_deg), float(phi_max_deg)),
        "R_rot_mm": R_rot_mm,
        "min_illuminated_area_um2_across_phi": min_illuminated_area,
        "per_phi_breakdown": rows,
    }
