"""
Validates this project's own predicted LogMAR (three candidate predictors: MTF50-
cutoff, MTF10-cutoff, FWHM-based) against literature.get('ideal_pinhole_wang_2009')'s
5-point (aperture, LogMAR) dataset -- the "Validation" stage of the project's pipeline
(RMSE/MAE/R^2/Pearson r), previously absent from this project entirely (see
validation_stats.py's own docstring: nothing computed a direct predicted-vs-observed
regression-agreement statistic anywhere before this script).

Because that paper's summary table does not report a single myopia level (M) each
point was measured at (see the citation's fidelity note), this reports a SENSITIVITY
table across several representative M values rather than a single forced fit --
consistent with how every other point of genuine uncertainty in this project is
handled (e.g. model_comparison/acuity_check.py's own M-matching caveat). Picking
whichever M maximizes R^2 after the fact and reporting only that one would be
circular; this script deliberately does not do that.

FWHM is included as a candidate predictor (not just the two MTF-cutoff predictors)
because model_comparison/'s own Finding 3 already found FWHM tracks a real clinical
LogMAR figure far more closely than this project's usual r_EE(50) metric -- worth
checking directly against a second, independent clinical dataset here.
"""

import os

import pandas as pd

import literature
import metrics
import validation_stats
import visual_acuity

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")

M_VALUES = [0.0, 2.0, 5.0]
WAVELENGTH_NM = 550.0
D_GAP_MM = 12.0
D_PUPIL_UM = 4000.0

PREDICTORS = ["logmar_mtf50", "logmar_mtf10", "logmar_fwhm"]


def predicted_points(M_values=M_VALUES, wavelength_nm=WAVELENGTH_NM, d_gap_mm=D_GAP_MM,
                      D_pupil_um=D_PUPIL_UM):
    """
    Runs this project's own pipeline (metrics.compute_all_metrics -- no physics
    reimplemented here) at every (aperture, M) combination in the
    ideal_pinhole_wang_2009 dataset x M_values, returning one row per combination
    with all three candidate LogMAR predictors plus the observed LogMAR for that
    aperture (repeated across M, since the dataset itself has no M axis -- see
    literature.py's fidelity note on this dataset).
    """
    data = literature.get("ideal_pinhole_wang_2009")["data"]
    apertures_um = data["aperture_um"]
    observed_logmar = data["logmar"]

    rows = []
    for M in M_values:
        for a_um, obs in zip(apertures_um, observed_logmar):
            m = metrics.compute_all_metrics(
                a_hole=a_um * 1e-6, wavelength=wavelength_nm * 1e-9, d_gap=d_gap_mm * 1e-3,
                M_diopters=M, D_pupil_um=D_pupil_um,
            )
            if not m["junction_check_passed"]:
                continue

            acuity = visual_acuity.acuity_from_mtf_cutoff(m["mtf50_cpd"], m["mtf10_cpd"])
            fwhm_radius_m = m["fwhm_radius_um"] * 1e-6
            v_r_m = m["v_r_mm"] * 1e-3
            mar_fwhm = visual_acuity.mar_from_angular_blur(fwhm_radius_m, v_r_m)
            logmar_fwhm = visual_acuity.logmar_from_mar(mar_fwhm)

            rows.append({
                "M_diopters": M, "a_hole_um": a_um, "observed_logmar": obs,
                "logmar_mtf50": acuity["logmar_mtf50"], "logmar_mtf10": acuity["logmar_mtf10"],
                "logmar_fwhm": float(logmar_fwhm), "fwhm_mode": m["fwhm_mode"],
            })
    return pd.DataFrame(rows)


def sensitivity_table(points_df, predictors=PREDICTORS):
    """One row per (M, predictor), with regression_stats() vs the observed LogMAR."""
    rows = []
    for M in sorted(points_df["M_diopters"].unique()):
        g = points_df[points_df["M_diopters"] == M]
        for predictor in predictors:
            stats_dict = validation_stats.regression_stats(g[predictor], g["observed_logmar"])
            rows.append({"M_diopters": M, "predictor": predictor, **stats_dict})
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    points_df = predicted_points()
    points_df.to_csv(os.path.join(OUT_DIR, "validation_predicted_vs_observed.csv"), index=False)
    print(f"Wrote validation_predicted_vs_observed.csv ({len(points_df)} rows: "
          f"{len(M_VALUES)} M values x 5 apertures)")

    stats_df = sensitivity_table(points_df)
    stats_df.to_csv(os.path.join(OUT_DIR, "validation_regression_stats.csv"), index=False)
    print(f"Wrote validation_regression_stats.csv ({len(stats_df)} rows)\n")

    print("RMSE/MAE/R^2/Pearson r sensitivity across M and predictor, against "
          "literature.get('ideal_pinhole_wang_2009') (n=5 apertures per M):")
    print("NOTE: no single M is asserted as 'correct' here -- see literature.py's "
          "fidelity note on why this dataset has no clean per-point M.\n")
    print(stats_df.to_string(index=False))


if __name__ == "__main__":
    main()
