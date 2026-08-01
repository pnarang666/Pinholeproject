"""
Compares this project's R7-style acuity conversion (angular blur = r_EE(P)/v_r, exactly
as both reference docs prescribe) against a real clinical measurement: a 1.2mm pinhole
aperture is reported to give ~20/30 Snellen acuity (0.17 logMAR) for refractive error up
to 5.5 D (see README.md "Literature and commercial comparison" for the citation).

Finds that r_EE(50%) -- the metric this project uses everywhere else -- badly
overestimates blur for this purpose, because it is a cumulative-ENERGY radius and
therefore counts diffuse peripheral light that does not meaningfully degrade letter
recognition. FWHM (a core-width metric) lands far closer to the clinical figure.
Neither is a substitute for a real MTF/contrast-threshold acuity model -- this script
exists to demonstrate the metric-choice error concretely, not to produce a validated
new acuity formula.
"""

import os
import sys

import numpy as np

_STAGE1_V2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage1_v2"))
_STAGE2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage2"))
for d in (_STAGE1_V2_DIR, _STAGE2_DIR):
    if d not in sys.path:
        sys.path.insert(0, d)

import physics  # noqa: E402
import phase2_retina as p2  # noqa: E402

ARCMIN_PER_RAD = (180 / np.pi) * 60
CLINICAL_APERTURE_UM = 1200.0
CLINICAL_M_DIOPTERS = 5.0        # "up to 5.5 D" -- nearest value in this project's M grid
CLINICAL_SNELLEN_DENOM = 30      # 20/30, i.e. 0.17 logMAR, per the cited study


def angular_blur_arcmin(radius_m, v_r_m):
    return (radius_m / v_r_m) * ARCMIN_PER_RAD


def implied_snellen_denominator(angular_arcmin):
    """MAR(arcmin) = Snellen denominator / 20 for a 20-ft chart -- i.e. denom = 20*MAR."""
    return 20 * angular_arcmin


def run_check(a_hole_um=CLINICAL_APERTURE_UM, M_diopters=CLINICAL_M_DIOPTERS):
    a_hole = a_hole_um * 1e-6
    result = p2.run_pipeline_point(
        a_hole=a_hole, wavelength=550e-9, d_gap=12e-3, grid_N=2048, window_L_mm=6.0,
        M_diopters=M_diopters, P0=60.0, n_prime=1.336, D_pupil_um=4000.0,
        refractive_index_correction=True,
    )
    I_retina = result["I_retina"]
    dx = result["cornea_result"]["dx"]
    v_r = result["myopia"]["L_ax"]

    r_centers, I_radial = physics.radial_profile(I_retina, None, dx)
    I_peak = I_radial.max()
    fwhm_detail = physics.locate_threshold_crossing(r_centers, I_radial, 0.5, I_peak=I_peak)

    r_ee50_um = result["retina_EE"]["r_EE_50"] * 1e6
    fwhm_um = fwhm_detail["radius"] * 1e6

    rows = []
    for label, r_um in [("r_EE(50%) [this project's usual metric]", r_ee50_um),
                         ("FWHM radius [core-width metric]", fwhm_um)]:
        arcmin = angular_blur_arcmin(r_um * 1e-6, v_r)
        denom = implied_snellen_denominator(arcmin)
        rows.append({"metric": label, "radius_um": r_um, "angular_arcmin": arcmin,
                     "implied_snellen_denom": denom})

    return {
        "a_hole_um": a_hole_um, "M_diopters": M_diopters, "v_r_mm": v_r * 1e3,
        "clinical_snellen_denom": CLINICAL_SNELLEN_DENOM, "rows": rows,
    }


if __name__ == "__main__":
    check = run_check()
    print(f"Condition: a_hole={check['a_hole_um']:.0f}um, M={check['M_diopters']:.0f}D, "
          f"v_r={check['v_r_mm']:.2f}mm")
    print(f"Clinical reference: ~20/{check['clinical_snellen_denom']} Snellen "
          f"(0.17 logMAR) at this aperture, refractive error up to 5.5D "
          f"[citation: README.md]")
    print()
    for row in check["rows"]:
        print(f"  {row['metric']}")
        print(f"    radius = {row['radius_um']:.2f} um")
        print(f"    angular blur = {row['angular_arcmin']:.2f} arcmin")
        print(f"    implied Snellen ~ 20/{row['implied_snellen_denom']:.0f}")
        print()
