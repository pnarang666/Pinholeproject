"""
COPIED (not imported) from Array_Design/array_optimization/vignetting.py, as of 2026-08-15.
Source module implements IYPT_Pinhole_Theoretical_Handbook_2.pdf Chapter 13 (Sec 13.1-13.2)
pupil-hole circle-overlap geometry, validated there against an independent Monte Carlo
estimate: max error 0.177 percentage points of full hole area (tolerance 0.5, 72 test
points, array_optimization/vignetting_validation.csv) -- including the boundary-clamp fix
for the Delta=Rp+Rh floating-point-roundoff negative-area defect (observed: -0.0589 um^2 at
Delta=3000um for a 2000um hole), copied here WITH that fix already applied, not the
pre-fix version.

This file is a deliberate COPY, not an import, so array_geometry_lab/ has zero runtime
dependency on array_optimization/'s internals (folder-isolation requirement). See
../VALIDATION.md for the check that this copy reproduces the original bit-for-bit against
the original validation dataset -- run that check before trusting anything downstream of
this file.

Only the pure-geometry functions are copied (overlap_area_um2, pupil_shift_um,
phi_in_validated_range) -- NOT n_eff_matrix/n_eff_vs_phi/gaze_weights/apply_to_candidates,
which are array_optimization/'s own Stage-3-candidate-specific application code, out of
scope for this pipeline (array_geometry_lab/evaluation/ builds its own active-pair-based
application of these same primitives, since this pipeline's hole geometries are arbitrary
coordinate lists, not lattice-derived Stage-3 candidates).
"""
import numpy as np

DEFAULT_R_ROT_MM = 13.5  # physiological range 13-14mm (Handbook 2 Sec 13.1)
DEFAULT_PHI_VALID_DEG = 25.0  # Handbook's own stated validity range is |phi| <~ 20-30deg


def overlap_area_um2(delta_um, R_p_um, R_h_um):
    """Exact circle-circle overlap area, Handbook 2 Sec 13.2. delta_um may be a scalar
    or array. Three regimes handled EXPLICITLY (no fallthrough): full containment
    (Delta <= |Rp-Rh|), no overlap (Delta >= Rp+Rh), and the general partial-overlap
    acos formula strictly between them -- boundary points always land in the full/zero
    regimes (both use <=, >=), so the acos branch is never evaluated exactly AT a
    boundary; acos arguments are still explicitly clipped to [-1,1] as a second,
    independent safeguard against floating-point overshoot just inside that branch.
    Verbatim copy of vignetting.overlap_area_um2, including the boundary-clamp fix."""
    assert R_h_um < R_p_um, (
        f"overlap_area_um2 assumes R_h < R_p (true for every candidate hole/pupil size "
        f"in this project); got R_h={R_h_um}, R_p={R_p_um} -- equal-radius geometry is "
        f"out of scope and not handled.")
    d = np.atleast_1d(np.asarray(delta_um, dtype=float))
    out = np.empty_like(d)

    full_area = np.pi * min(R_p_um, R_h_um) ** 2
    lo = abs(R_p_um - R_h_um)
    hi = R_p_um + R_h_um

    m_full = d <= lo
    m_zero = d >= hi
    m_part = ~m_full & ~m_zero

    out[m_full] = full_area
    out[m_zero] = 0.0

    if np.any(m_part):
        dp = d[m_part]
        a1 = np.arccos(np.clip((dp ** 2 + R_p_um ** 2 - R_h_um ** 2) / (2 * dp * R_p_um), -1.0, 1.0))
        a2 = np.arccos(np.clip((dp ** 2 + R_h_um ** 2 - R_p_um ** 2) / (2 * dp * R_h_um), -1.0, 1.0))
        radicand = (-dp + R_p_um + R_h_um) * (dp + R_p_um - R_h_um) * (dp + R_h_um - R_p_um) * (dp + R_p_um + R_h_um)
        term3 = 0.5 * np.sqrt(np.clip(radicand, 0.0, None))
        out[m_part] = np.clip(R_p_um ** 2 * a1 + R_h_um ** 2 * a2 - term3, 0.0, None)  # near
                        # the Delta=Rp+Rh boundary, floating-point roundoff on the acos
                        # terms can produce a tiny negative area despite the true area
                        # being 0 there by construction -- the sqrt term was already
                        # clamped, this closes the same gap on the final combination.

    return out[0] if out.size == 1 and np.isscalar(delta_um) else out


def pupil_shift_um(phi_deg, R_rot_mm=DEFAULT_R_ROT_MM):
    """13.1: Delta(phi) ~= R_rot * sin(phi). Returns micrometres.
    Verbatim copy of vignetting.pupil_shift_um."""
    phi_rad = np.radians(phi_deg)
    return R_rot_mm * 1000.0 * np.sin(phi_rad)


def phi_in_validated_range(phi_deg, max_valid_deg=DEFAULT_PHI_VALID_DEG):
    """True where |phi| is inside the handbook's stated small-angle validity range.
    Evaluations outside this range are still COMPUTED (the formula doesn't blow up) but
    every caller that reports a number must check and flag this, not silently trust it.
    Verbatim copy of vignetting.phi_in_validated_range."""
    return np.abs(phi_deg) <= max_valid_deg
