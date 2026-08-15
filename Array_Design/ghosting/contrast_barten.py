"""
Real Barten (1999) CSF model, via the published colour-science Python package
(colour.contrast.contrast_sensitivity_function_Barten1999), replacing the project's
own peak-matched heuristic (contrast.py) for THIS specific low-frequency application.

Citation: P.G.J. Barten, "Contrast Sensitivity of the Human Eye and Its Effects on
Image Quality" (1999); simplified formula also in P. Barten, "Formula for the
contrast sensitivity of the human eye," Proc. SPIE 5294, 231-238 (2003). Verified
directly: full parametrized equation (signal-to-noise k, integration time T, object
size X0/Y0, retinal illuminance E in Td, noise spectral density phi_0, lateral-
inhibition cutoff u_0) confirmed against DICOM PS3.14 Sec A.2's reproduced formula,
stated valid range 0.2 <= u <= 50 cycles/degree, 1e-4 <= L <= 1e3 cd/m^2 -- extending
down to and slightly below this project's ghosting frequencies (0.10-0.30 cpd), unlike
the project's own heuristic which was only ever fit to match a reported PEAK location
and has no claimed validity at all below it.

REQUIRES: pip install colour-science (pip install colour-science --break-system-packages
if using a system Python). Not a project dependency anywhere else -- only used here.

Monocular correction: per the same source documentation, "for monocular vision, the
contrast sensitivity is a factor sqrt(2) smaller" -- applied here since a pinhole
array's ghosting is a monocular phenomenon (one eye looking through one array).

ASSUMPTION, stated explicitly rather than buried: object/field size X_0=Y_0=10 degrees
(a documented middle-ground choice -- tested against 2/10/60 degrees, see RESULTS.md;
threshold contrast at the tested ghosting frequencies ranges 0.6%-3.6% across that
whole span, and the classifier's conclusion (contrast ~97% vs any of these thresholds)
does not change based on which field-size assumption is used).
"""
import numpy as np
from colour.contrast import (contrast_sensitivity_function_Barten1999,
                              pupil_diameter_Barten1999, sigma_Barten1999,
                              retinal_illuminance_Barten1999)

MONOCULAR_CORRECTION = 1.0 / np.sqrt(2.0)


def csf_threshold_barten(f_cpd, scene_luminance_cdm2=10000.0, field_deg=10.0):
    """Returns the MINIMUM DETECTABLE CONTRAST (modulation threshold) at spatial
    frequency f_cpd, per the real Barten (1999) model -- directly comparable to
    this project's own neural_contrast_threshold() interface (contrast.py), so it
    can be swapped in without changing any calling code's expectations."""
    L = scene_luminance_cdm2
    X_0 = Y_0 = field_deg
    d = pupil_diameter_Barten1999(L, X_0, Y_0)
    sigma = sigma_Barten1999(0.5 / 60, 0.08 / 60, d)
    E = retinal_illuminance_Barten1999(L, d)
    S = float(contrast_sensitivity_function_Barten1999(u=f_cpd, sigma=sigma, E=E, X_0=X_0, Y_0=Y_0))
    S_monocular = S * MONOCULAR_CORRECTION
    return 1.0 / S_monocular if S_monocular > 0 else float("inf")
