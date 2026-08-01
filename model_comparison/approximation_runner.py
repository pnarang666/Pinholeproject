"""
Model 3: the OLD, closed-form formula chain from the reference handbooks (Problem
Statement Sec 3.2-3.3, Master Formulas Sec 2.6-2.8) -- a_eff, a_stop, r_geo, r_diff,
r_total (flawed RSS combination), a* (closed-form "optimum"). No simulation, no FFT --
pure algebra, evaluated instantly. Kept ONLY as the labeled cross-check both reference
docs explicitly ask for; never the reported design number.

Reuses stage2/classical_formulas.py rather than re-deriving the formulas a second time.
"""

import os
import sys

_STAGE2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage2"))
if _STAGE2_DIR not in sys.path:
    sys.path.insert(0, _STAGE2_DIR)

import classical_formulas as _cf  # noqa: E402
import myopia_axial as _myopia  # noqa: E402


def approximate_blur(a_hole, wavelength, d_gap, M_diopters, P0=60.0, n_prime=1.336, D_pupil_um=4000.0):
    """Returns r_total (#7) and a* (#8) for the same (a_hole, wavelength, d_gap, M) point."""
    myopia = _myopia.axial_length_for_myopia(M_diopters, P0=P0, n_prime=n_prime)
    v_r, v_f = myopia["L_ax"], myopia["f_eye"]
    D_pupil = D_pupil_um * 1e-6

    r_tot = _cf.r_total(a_hole, wavelength, d_gap, D_pupil, v_r, v_f)
    a_opt = _cf.a_star(wavelength, v_r, v_f)
    a_eff_val = _cf.a_eff(a_hole, wavelength, d_gap)

    return {"r_total_approx": r_tot, "a_star_approx": a_opt, "a_eff_cornea_approx": a_eff_val,
            "v_r": v_r, "v_f": v_f}
