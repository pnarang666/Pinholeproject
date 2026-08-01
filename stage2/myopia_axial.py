"""
Axial-length myopia model.

The eye's optical power is held FIXED at its emmetropic value P0 for every degree of
myopia M -- only the axial length grows to push the retina past the fixed focal point.
This is the defining assumption of an *axial* myopia model, as opposed to a *refractive*
one (where P0 itself would change and axial length would stay fixed). Everything in
stage2 that needs "how far is the retina" for a given M reads L_ax from here; nothing
recomputes eye power per M.
"""

REFRACTIVE_INDEX_CORRECTION = True
"""
True  -- retina-stage propagation uses wavelength/n_prime as the effective wavelength
          (n_prime=1.336 by default); f0 = n_prime/P0 ~= 22.3 mm at P0=60 D. This is the
          anatomically-scaled convention: distances inside the vitreous are measured
          with the vitreous's own refractive index.
False -- n_prime is forced to 1.0 throughout; f0 = 1/P0 ~= 16.7 mm at P0=60 D. Air-
          equivalent convention.

stage1_v2 has no pre-existing lens/retina code to match conventions against -- Stage 1
is explicitly scoped to stop at the cornea (see stage1_v2/physics.py's module
docstring), so this flag is the first place either convention is established, not an
attempt to match something that already existed. Logged on every run so a sweep's CSV
always records which convention produced it (see `refractive_index_mode` column).
"""


def axial_length_for_myopia(M_diopters, P0=60.0, n_prime=1.336):
    """
    L0    = n_prime / P0                 emmetropic axial length (fixed reference)
    L_ax  = n_prime / (P0 - M_diopters)  myopic axial length for this M
    f_eye = L0                          eye power fixed at the emmetropic value for
                                         every M -- the defining feature of this axial
                                         model versus a refractive one.

    Raises ValueError if M_diopters >= P0 (L_ax would be singular or negative -- the
    modeled eye has run out of power to converge at all).
    """
    if M_diopters >= P0:
        raise ValueError(
            f"M_diopters={M_diopters} >= P0={P0}: L_ax = n_prime/(P0-M) is singular or "
            f"negative at this myopia level for this P0. Reduce M_diopters or raise P0."
        )

    L0 = n_prime / P0
    L_ax = n_prime / (P0 - M_diopters)
    f_eye = L0
    delta_L = L_ax - L0

    return {
        "L0": L0, "L_ax": L_ax, "f_eye": f_eye, "delta_L": delta_L,
        "M_diopters": M_diopters, "P0": P0, "n_prime": n_prime,
    }
