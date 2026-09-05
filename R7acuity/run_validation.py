"""
Full validation run: calibrate noise sigma against the reference condition ONCE,
then predict logMAR for all 5 Wang (2009) apertures x M=[0,2,5]D (matching
stage4_human_vision's own sensitivity setup for direct comparability), report
regression_stats() (imported from stage4_human_vision/validation.py, not
reimplemented) -- both "in-sample" and "leave-one-out" labels, which are
identical here since R7acuity has no parameter fit to Wang 2009 (see
validation.py's in_sample_equals_leave_one_out_here() docstring) -- plus the two
closed-form cross-check approximations for the same points.

Run: python3 -m R7acuity.run_validation
"""
import os
import sys

import numpy as np
import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_STAGE3HV_DIR = os.path.join(_ROOT, "stage3_human_vision")
for _d in (_ROOT, _STAGE3HV_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from stage4_human_vision.validation import regression_stats  # noqa: E402

from .threshold import (calibrate_noise_sigma, closed_form_approximations,  # noqa: E402
                        mar_to_logmar, find_threshold_mar)
from .validation import wang_2009_dataset, in_sample_equals_leave_one_out_here  # noqa: E402

M_VALUES = [0.0, 2.0, 5.0]
WAVELENGTH_NM = 550.0
D_GAP_MM = 12.0
D_PUPIL_UM = 4000.0
SCENE_LUMINANCE_CDM2 = 10000.0
FIELD_DIAMETER_DEG = 20.0
MAR_SEARCH_RANGE_ARCMIN = np.array([0.7, 1.2, 2.0, 3.5, 6.0, 10.0, 17.0])
N_TRIALS = 300

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(20260802)

    print("=== Step 1: calibrate noise sigma against reference condition ===")
    print("(diffraction-limited, emmetropic, 3mm aperture, target 1.0 arcmin MAR / 20/20)")
    print("This MUST happen before any Wang 2009 data is used -- no post-hoc tuning.\n")
    sigma, achieved_threshold, calib_log = calibrate_noise_sigma(n_trials=N_TRIALS, rng=rng, verbose=True)
    print(f"\nLOCKED sigma = {sigma:.6f} (reference threshold achieved: {achieved_threshold:.4f} arcmin)\n")

    pd.DataFrame(calib_log, columns=["sigma", "threshold_mar_arcmin"]).to_csv(
        os.path.join(OUT_DIR, "sigma_calibration_log.csv"), index=False)
    with open(os.path.join(OUT_DIR, "calibrated_sigma.txt"), "w") as fh:
        fh.write(str(sigma))

    print("=== Step 2: predict logMAR for Wang 2009 apertures x M=0,2,5D ===")
    apertures_um, observed_logmar = wang_2009_dataset()

    rows = []
    for M in M_VALUES:
        for a_um, obs in zip(apertures_um, observed_logmar):
            print(f"  a={a_um}um M={M}D ...", end=" ", flush=True)
            threshold_mar, slope, proportions = find_threshold_mar(
                dict(a_hole_um=a_um, wavelength_nm=WAVELENGTH_NM, M_diopters=M,
                     d_gap_mm=D_GAP_MM, D_pupil_um=D_PUPIL_UM,
                     scene_luminance_cdm2=SCENE_LUMINANCE_CDM2, field_diameter_deg=FIELD_DIAMETER_DEG),
                sigma, MAR_SEARCH_RANGE_ARCMIN, n_trials=N_TRIALS, rng=rng)
            logmar_r7 = mar_to_logmar(threshold_mar)

            closed_form = closed_form_approximations(
                a_hole_um=a_um, wavelength_nm=WAVELENGTH_NM, M_diopters=M, d_gap_mm=D_GAP_MM,
                D_pupil_um=D_PUPIL_UM, scene_luminance_cdm2=SCENE_LUMINANCE_CDM2,
                field_diameter_deg=FIELD_DIAMETER_DEG)

            print(f"threshold={threshold_mar:.3f}arcmin logMAR_r7={logmar_r7:.3f} "
                  f"(observed={obs:.3f})")
            rows.append({
                "M_diopters": M, "a_hole_um": a_um, "observed_logmar": obs,
                "threshold_mar_arcmin": threshold_mar, "psychometric_slope": slope,
                "logmar_r7_ideal_observer": logmar_r7,
                "strehl_ratio": closed_form["strehl_ratio"],
                "vsotf": closed_form["vsotf"],
                "logmar_from_strehl_closed_form": closed_form["logmar_from_strehl"],
                "logmar_from_vsotf_closed_form": closed_form["logmar_from_vsotf"],
            })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT_DIR, "validation_predicted_vs_observed.csv"), index=False)
    print(f"\nWrote {os.path.join(OUT_DIR, 'validation_predicted_vs_observed.csv')}")

    print("\n=== Step 3: regression stats (in-sample == leave-one-out here; see below) ===")
    assert in_sample_equals_leave_one_out_here()
    predictors = ["logmar_r7_ideal_observer", "logmar_from_strehl_closed_form", "logmar_from_vsotf_closed_form"]
    stats_rows = []
    for M in M_VALUES:
        g = df[df["M_diopters"] == M]
        for predictor in predictors:
            stats = regression_stats(g["observed_logmar"].tolist(), g[predictor].tolist())
            for label in ("in_sample", "leave_one_out_identical_by_construction"):
                stats_rows.append({"M_diopters": M, "predictor": predictor, "kind": label, **stats})

    stats_df = pd.DataFrame(stats_rows)
    stats_df.to_csv(os.path.join(OUT_DIR, "validation_regression_stats.csv"), index=False)
    print(stats_df[stats_df["kind"] == "in_sample"].to_string(index=False))
    print(f"\nWrote {os.path.join(OUT_DIR, 'validation_regression_stats.csv')}")

    print("\n=== BOTTOM LINE ===")
    main_stats = stats_df[(stats_df["predictor"] == "logmar_r7_ideal_observer") & (stats_df["kind"] == "in_sample")]
    r2_lo, r2_hi = main_stats["r2"].min(), main_stats["r2"].max()
    p_lo, p_hi = main_stats["pearson_p_value"].min(), main_stats["pearson_p_value"].max()
    print(f"R7 ideal-observer model: R^2 range [{r2_lo:.3f}, {r2_hi:.3f}], "
          f"p range [{p_lo:.3f}, {p_hi:.3f}] across M={M_VALUES}")
    if r2_lo > 0 and p_hi < 0.05:
        print("PASSES the stated bar: R^2>0 AND p<0.05 at every M tested.")
    else:
        print("DOES NOT clear the stated bar (R^2>0 AND p<0.05) at every M tested.")

    return df, stats_df, sigma


if __name__ == "__main__":
    main()
