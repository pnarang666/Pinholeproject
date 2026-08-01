"""
The handbook's deprecated/flawed pre-ASM formula chain (Problem Statement §3.2-3.3,
Master Formulas §2.6/§2.8), kept ONLY as a labeled cross-check against the numerical
r_EE(P) result -- never as the reported design number (both reference docs say so
explicitly). Implemented here, not reused from stage1_v2, since stage1_v2 only ever
computes the cornea-plane a_eff (formula #3) as its own cross-check overlay; it has no
notion of a retina-plane r_geo/r_diff/r_total/a* (formulas #5-#8), which require the eye
lens and v_f/v_r -- concepts stage1_v2 deliberately never models (it stops at the
cornea).
"""

import numpy as np


def a_eff(a_hole, wavelength, d_gap):
    """Formula #3 / Master Formulas §2.8 -- quadrature spot-size estimate at the cornea."""
    return np.sqrt(a_hole ** 2 + (2.44 * wavelength * d_gap / a_hole) ** 2)


def a_stop(a_hole, wavelength, d_gap, D_pupil):
    """Formula #4 -- effective aperture after natural pupil clipping."""
    return np.minimum(a_eff(a_hole, wavelength, d_gap), D_pupil)


def r_geo(a_stop_value, v_r, v_f):
    """Formula #5 -- paraxial geometric defocus blur radius."""
    return (a_stop_value / 2.0) * np.abs(v_r - v_f) / v_f


def r_diff(a_stop_value, wavelength, v_r):
    """Formula #6 -- Fraunhofer first-null diffraction radius (not an energy-based size)."""
    return 1.22 * wavelength * v_r / a_stop_value


def r_total(a_hole, wavelength, d_gap, D_pupil, v_r, v_f):
    """
    Formula #7 -- root-sum-square combination of r_geo and r_diff. Identified as
    PHYSICALLY WRONG in both reference docs (true combination is a convolution, not an
    RSS of radii) -- kept here only as the labeled deprecated overlay curve the
    handbook's own §4 step 3 asks for, plotted against the numerical r_EE(P) result.
    """
    a_s = a_stop(a_hole, wavelength, d_gap, D_pupil)
    return np.sqrt(r_geo(a_s, v_r, v_f) ** 2 + r_diff(a_s, wavelength, v_r) ** 2)


def a_star(wavelength, v_r, v_f):
    """
    Formula #8 -- closed-form "optimal aperture" derived from the flawed formula #7.
    Kept only for comparison against the numerically-found optimum (where r_EE(P) is
    actually minimized over a_hole) -- the reference docs expect this closed form to
    diverge from the numerical result and ask that the divergence be reported, not
    treated as the answer.
    """
    return np.sqrt(2.44 * wavelength * v_r * v_f / np.abs(v_r - v_f))
