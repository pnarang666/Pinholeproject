"""
Relative retinal illuminance from a single pinhole aperture, referenced to natural
(unobstructed) pupil viewing.

Scope: single circular aperture directly in front of the eye (Phase 1/2's actual
geometry -- not yet a multi-hole array, which is a separate R2/R3 photometry question
using Master Formulas Sec2.11's T = N*(pi*a_hole^2/4)/A_total for an array over a frame).
That formula answers a different question (fraction of a frame's area that's open) and
is NOT reused here -- it would be the wrong formula for "how much light reaches the
retina relative to normal viewing" for a single central aperture.

Physics: diffraction does not destroy or absorb power, it only redistributes it
spatially -- total transmitted power through a circular aperture of area A is A times
incident irradiance, regardless of the diffraction pattern downstream. So relative
illuminance depends on the RAW physical aperture area (a_hole), not on any
diffraction-broadened spot-size estimate (a_eff) -- using a_eff here would be a
category error (conflating a blur-radius concept with a light-throughput concept).

Once a_hole exceeds the natural pupil diameter D_pupil, the pupil itself becomes the
limiting stop -- a wider external aperture no longer admits more light through the eye.
"""

import numpy as np


def relative_illuminance(a_hole_um, D_pupil_um):
    """
    Returns E_rel in [0, 1]: retinal illuminance as a fraction of normal (full natural
    pupil, unobstructed) illuminance, for a single circular aperture of diameter
    a_hole_um placed in front of an eye with natural pupil diameter D_pupil_um.

    E_rel = (min(a_hole, D_pupil) / D_pupil)^2   -- area ratio, clipped at the pupil.
    """
    a_eff_stop = np.minimum(a_hole_um, D_pupil_um)
    return (a_eff_stop / D_pupil_um) ** 2
