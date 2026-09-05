"""
COPIED (not imported) from Array_Design/ghosting/ghost_separation.py, as of 2026-08-15.
Source module validated this formula against an independent two-hole coherent wave-optics
propagation (array_optimization/stage0_ghost_validation/validate_ghost_formula.py):
R^2 = 0.995135 (32 measured points) for the corrected formula below, vs. R^2 = -1701.71 for
the legacy formula (kept here for reference only, not used by this pipeline). M=0 gate
passed at the measurement floor (1 grid pixel, 1.46 um).

This file is a deliberate COPY, not an import, so array_geometry_lab/ has zero runtime
dependency on array_optimization/'s internals (folder-isolation requirement). See
../VALIDATION.md for the check that this copy reproduces the original bit-for-bit against
the original validation dataset -- run that check before trusting anything downstream of
this file.

Only the two functions this pipeline actually uses are copied (delta_r_corrected_from_M_um,
the pure-myopia form, since a_hole(M) is a fixed input here and no eye-model axial-length
computation is needed elsewhere in this pipeline; delta_r_corrected_um, the v_r/v_f form,
kept alongside for the VALIDATION.md cross-check against the original CSV, which records
v_r_um). delta_r_legacy_um is NOT copied -- this pipeline has no use for the disproven
formula and copying unused, wrong physics would only invite accidental misuse.
"""
import numpy as np


def delta_r_corrected_um(pitch_um, v_r_um, v_f_um):
    """Eq. (C): delta_r = s * |v_r - v_f| / v_f. Vanishes at v_r = v_f (M=0).
    Verbatim copy of ghost_separation.delta_r_corrected_um."""
    return pitch_um * abs(v_r_um - v_f_um) / v_f_um


def delta_r_corrected_from_M_um(pitch_um, M_diopters, P0=60.0):
    """Eq. (C'): the same quantity written in terms of myopia only, s * M/(P0-M).
    Identical to delta_r_corrected_um() under the axial model (myopia_axial.py) --
    both are provided (in the source module) so the identity can be checked, not
    assumed; this pipeline uses ONLY this M-based form, since a_hole(M) is supplied
    per-M directly and no separate v_r/v_f axial-length computation is otherwise
    needed anywhere in array_geometry_lab/.
    Verbatim copy of ghost_separation.delta_r_corrected_from_M_um."""
    return pitch_um * M_diopters / (P0 - M_diopters)
