"""
Array_Design/array_geometry_lab/predicted_logmar_analysis/build_logmar_analysis.py

Answers: "predicted LogMAR per array evaluation model per myopia power M, deviation
from real/theoretical pinhole data, and R^2" -- assembled from data this project
already has, nothing invented.

SOURCES (all read-only):
  1. Array winner-per-M tables (Array_Design/array_geometry_lab/array_data/
     evaluation_results/*.csv) -- 6 live evaluation models, none deleted, all
     still reported (see README.md / TIMELINE.txt). Gives (family, a_hole_um,
     N_actual) per M per model.
  2. new_sweeps/acuity_sweep_stage4.csv -- the CORRECTED (grid_N=4096, fixed
     2026-09-12/13) single-pinhole acuity sweep. Every array-winner aperture at
     every M is an EXACT grid point here (400/500/600/750/1250/2000um all
     present) -- no interpolation needed anywhere in this file.
  3. new_sweeps/per_M_optimum_map.csv -- the single-pinhole THEORETICAL acuity-
     optimum aperture and predicted LogMAR per M (same corrected pipeline).
  4. stage4_human_vision/outputs/wang2009_validation_postfix_{predicted,stats}.csv
     -- this project's own existing validation against REAL clinical data: Wang
     (2009) "Ideal Pinhole" study, 5 apertures (500/750/1000/1200/1500um),
     observed LogMAR (0.28/0.31/1.00/0.40/0.50), literature.py's own
     'ideal_pinhole_wang_2009' dataset.
     CORRECTED SOURCE, found during this analysis: the OLDER
     validation_predicted_vs_observed.csv/validation_regression_stats.csv/
     calibration_*.csv in this same folder PREDATE (2026-07-29) the 2026-08-06
     stage2/->stage2_fixed/ import-shadowing optics fix documented in
     stage4_human_vision/RESULTS.md's "Re-run against corrected optics"
     section -- confirmed by file mtime AND by direct re-run (same inputs,
     current code, gave a materially different result: e.g. a=750/M=2 gives
     0.076 now vs 1.010 in the stale file). The '_postfix' files ARE the
     already-corrected re-run and are what this script uses. The affine
     calibration step was NOT re-run post-fix by the project itself
     (RESULTS.md's own words: "Section 4c's calibration fit is reported
     separately below, also not re-touched here") -- this script closes that
     gap by re-fitting calibration.py's existing OLS/leave-one-out functions
     against the corrected postfix predictions (see wang2009_calibration_postfix
     sheet), rather than reporting the stale pre-fix calibration numbers.
     Separately checked (not assumed): this validation's run_stage4_point()
     calls omit grid_N (default 2048) -- verified by direct A/B test (grid_N
     2048 vs 4096, same 5 apertures, M=2D): max difference 0.00032 logMAR --
     negligible, NOT the large-aperture 2x artifact. Safe to leave as-is.

IMPORTANT, HONEST LIMITATION carried forward from run_wang2009_validation.py's
own docstring: Wang (2009)'s summary table has no per-M breakdown -- the same 5
observed values are reused at every M this project compares against. This
script inherits that same limitation; it is not a new approximation introduced
here.

Writes (this folder only):
  predicted_logmar_per_array_model.csv / .xlsx (multi-sheet)
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(LAB))
sys.path.insert(0, REPO)

EVAL_DIR = os.path.join(LAB, "array_data", "evaluation_results")
NEW_SWEEPS = os.path.join(REPO, "new_sweeps")
STAGE4_OUT = os.path.join(REPO, "stage4_human_vision", "outputs")

MODELS = {
    "worst_case_gate_FINAL_WINNER_old_primary": "FINAL_WINNER_PER_M.csv",
    "gaze_weighted_ungated": "gaze_weighted_winner_per_M.csv",
    "gaze_weighted_plus_blindness_gate_CURRENT_PRIMARY": "PRIMARY_WINNER_PER_M.csv",
    "metric1_max_density": "metric1_max_density_per_M.csv",
    "effective_density_cmin0": "effective_density_winner_per_M_cmin0.csv",
    "effective_density_cmin55": "effective_density_winner_per_M_cmin55.csv",
}

# Wang (2009) "Ideal Pinhole" real clinical observed LogMAR, indexed by aperture --
# literature.py's own dataset, reused verbatim (not refit).
WANG2009_OBSERVED = {500: 0.28, 750: 0.31, 1000: 1.00, 1200: 0.40, 1500: 0.50}


def main():
    acuity = pd.read_csv(os.path.join(NEW_SWEEPS, "acuity_sweep_stage4.csv"))
    opt_map = pd.read_csv(os.path.join(NEW_SWEEPS, "per_M_optimum_map.csv")).set_index("M_diopters")

    def lookup_logmar(a_hole_um, M):
        row = acuity[(acuity.a_hole_um == a_hole_um) & (acuity.M_diopters == M)]
        assert len(row) == 1, f"expected exactly 1 exact grid match for a={a_hole_um} M={M}, got {len(row)}"
        return float(row.logmar.values[0])

    detail_rows = []
    for model_label, fname in MODELS.items():
        df = pd.read_csv(os.path.join(EVAL_DIR, fname), dtype={"M": str})
        for _, r in df.iterrows():
            if r["M"] == "global":
                continue  # not a myopia power -- handled separately below
            M = float(r["M"])
            a_hole = float(r["a_hole_um"])
            predicted_logmar = lookup_logmar(a_hole, M)

            opt_a = float(opt_map.loc[M, "acuity_optimal_um"])
            opt_logmar = float(opt_map.loc[M, "logmar_at_acuity_opt"])
            deviation_from_theoretical_optimum = predicted_logmar - opt_logmar

            wang_obs = WANG2009_OBSERVED.get(int(a_hole))
            deviation_from_wang2009 = (predicted_logmar - wang_obs) if wang_obs is not None else None
            wang_note = ("exact aperture match to Wang (2009)" if wang_obs is not None
                        else "no Wang (2009) clinical data at this aperture size -- not interpolated")

            detail_rows.append({
                "M_diopters": M,
                "evaluation_model": model_label,
                "family": r["family"],
                "a_hole_um": a_hole,
                "N_actual": r["N_actual"],
                "predicted_logmar": round(predicted_logmar, 4),
                "theoretical_pinhole_optimum_aperture_um": opt_a,
                "theoretical_pinhole_optimum_logmar": opt_logmar,
                "deviation_from_theoretical_optimum_logmar": round(deviation_from_theoretical_optimum, 4),
                "wang2009_real_observed_logmar": wang_obs,
                "deviation_from_wang2009_observed_logmar": (
                    round(deviation_from_wang2009, 4) if deviation_from_wang2009 is not None else None),
                "wang2009_match_note": wang_note,
            })

    detail = pd.DataFrame(detail_rows)
    detail.to_csv(os.path.join(HERE, "predicted_logmar_per_array_model.csv"), index=False)
    print(f"wrote predicted_logmar_per_array_model.csv ({len(detail)} rows)")

    # Wide pivot: one row per M, one column per model, for quick visual comparison.
    wide = detail.pivot_table(index="M_diopters", columns="evaluation_model",
                              values="predicted_logmar", aggfunc="first")
    wide.to_csv(os.path.join(HERE, "predicted_logmar_wide_by_model.csv"))

    # The "global" (worst-case-across-M) design: a SINGLE fixed aperture (2000um,
    # square/hexagonal, same across every model that has a global row) evaluated
    # at EVERY myopia power it is meant to cover -- not just one number, since a
    # fixed-aperture design's blur depends on the wearer's own M too.
    global_rows = []
    global_aperture_by_model = {}
    for model_label, fname in MODELS.items():
        df = pd.read_csv(os.path.join(EVAL_DIR, fname), dtype={"M": str})
        grow = df[df["M"] == "global"]
        if len(grow):
            global_aperture_by_model[model_label] = float(grow.iloc[0]["a_hole_um"])
    all_M = sorted(acuity.M_diopters.unique())
    for model_label, a_hole in global_aperture_by_model.items():
        for M in all_M:
            global_rows.append({
                "evaluation_model": model_label,
                "global_design_aperture_um": a_hole,
                "M_diopters": M,
                "predicted_logmar_at_this_M": round(lookup_logmar(a_hole, M), 4),
            })
    global_df = pd.DataFrame(global_rows)
    global_df.to_csv(os.path.join(HERE, "global_design_across_all_M.csv"), index=False)
    print(f"wrote global_design_across_all_M.csv ({len(global_df)} rows)")

    # Real clinical (Wang 2009) validation -- the CORRECTED post-fix re-run
    # (see module docstring). This is the ONLY real (non-theoretical) LogMAR
    # validation dataset anywhere in this repo.
    from stage4_human_vision.calibration import fit_linear_calibration, leave_one_out_predictions
    from stage4_human_vision.validation import regression_stats

    pred_vs_obs = pd.read_csv(os.path.join(STAGE4_OUT, "wang2009_validation_postfix_predicted.csv"))
    reg_stats = pd.read_csv(os.path.join(STAGE4_OUT, "wang2009_validation_postfix_stats.csv"))
    pred_vs_obs.to_csv(os.path.join(HERE, "wang2009_predicted_vs_observed.csv"), index=False)
    reg_stats.to_csv(os.path.join(HERE, "wang2009_regression_stats_r2.csv"), index=False)

    raw = pred_vs_obs.predicted_logmar.tolist()
    obs = pred_vs_obs.observed_logmar.tolist()
    a, b = fit_linear_calibration(raw, obs)
    calib_in_sample = regression_stats(obs, [a * x + b for x in raw])
    calib_loo = regression_stats(obs, leave_one_out_predictions(raw, obs))
    calib_raw_pooled = regression_stats(obs, raw)
    calib_stats = pd.DataFrame([
        {"kind": "raw_pooled_uncalibrated", "fit_a": None, "fit_b": None, **calib_raw_pooled},
        {"kind": "affine_calibrated_in_sample", "fit_a": a, "fit_b": b, **calib_in_sample},
        {"kind": "affine_calibrated_leave_one_out", "fit_a": a, "fit_b": b, **calib_loo},
    ])
    calib_stats.to_csv(os.path.join(HERE, "wang2009_calibration_pooled_stats_postfix.csv"), index=False)

    methodology = pd.DataFrame([
        ["Acuity pipeline", "stage4_human_vision/acuity.py: predict_acuity(). MTF10/MTF50 cutoff "
         "frequencies (cycles/deg) -> minimum angle of resolution (MAR, arcmin) -> log10 = LogMAR."],
        ["Recommended model", "'mtf10_vsotf_brightness_adjusted': MTF10-cutoff MAR, divided by "
         "VSOTF^0.1 (Visual Strehl ratio of the OTF, from stage3's wave-optics PSF), then an ADDITIVE "
         "brightness correction in log space (below)."],
        ["Brightness correction", "brightness_logmar_correction(): 0 above 300 Td (Weber-Fechner "
         "regime, Van Nes & Bouman 1967); below 300 Td, += 0.060 * log10(300/Td) (de Vries-Rose "
         "regime slope, Tidbury/Czanner/Newsham 2016, their Table 3, p<0.001). Default scene "
         "luminance 10,000 cd/m^2 (bright outdoor daylight)."],
        ["Legacy alternative (kept, not primary)", "'vsotf_snr_legacy': the original, UNCITED "
         "SNR^0.05 correction term -- retained for comparison, not deleted, per this project's own "
         "'keep alternative models' pattern (DESIGN.md)."],
        ["Grid resolution", "ASM wave-optics propagation grid_N=4096 (fixed 2026-09-12/13; the "
         "single call site in new_sweeps/run_acuity_sweep.py that fed this table was the one with "
         "the stale grid_N=2048 default -- now explicit)."],
        ["Array-vs-single-pinhole relationship", "Every array design's own per-hole optics are "
         "IDENTICAL to a standalone single pinhole of the same a_hole_um at the same M -- the array "
         "only changes ghost/blindness risk (spatial arrangement), not the per-image blur. So "
         "predicted_logmar here is looked up directly from the single-pinhole sweep at each "
         "model's chosen a_hole_um, not re-derived per array family."],
        ["Real-world validation dataset", "Wang (2009) 'Ideal Pinhole' study -- the ONLY external, "
         "clinically-observed LogMAR data in this repo. 5 apertures, observed values are aperture-"
         "indexed only (no per-M breakdown in the source paper) -- reused at each M per this "
         "project's own already-documented limitation, not a new assumption."],
        ["R^2 status, raw model (POST-FIX, current)", "NEGATIVE at every tested M: -4.80 (M=0), "
         "-1.41 (M=2), -0.68 (M=5) -- see wang2009_regression_stats_r2.csv. Still fails R^2>0, but a "
         "real, substantial improvement over the PRE-FIX numbers (-6.39, -4.98, -2.84) -- the 2026-08-06 "
         "stage2_fixed/ optics correction narrowed, but did not close, the gap. Pooled (n=15, all 3 "
         "M's together) raw R^2 = -2.295, mean deviation = -0.187 logMAR (net OPTIMISTIC)."],
        ["R^2 status, calibrated model (affine fit, POST-FIX, computed in this analysis)",
         "The project's own RESULTS.md explicitly left this step un-re-run post-fix -- redone here "
         "using the same unmodified calibration.py fitting code against the corrected predictions. "
         "Pooled in-sample R^2 = +0.0003 (essentially none -- far weaker than the PRE-FIX in-sample "
         "+0.132, meaning that earlier apparent calibration benefit was itself partly an artifact of "
         "the buggy optics). Honest leave-one-out cross-validated R^2 = -0.307 (still fails, though "
         "closer to zero than the pre-fix LOO result of -0.566). See "
         "wang2009_calibration_pooled_stats_postfix.csv."],
        ["Deviation from theoretical (single-pinhole) optimum", "0.000 logMAR at every M for every "
         "array model -- BY CONSTRUCTION: every model's winning aperture already equals the single-"
         "pinhole acuity-optimal aperture for that M (per_M_optimum_map.csv). The array layer changes "
         "WHICH GEOMETRY carries that same optical aperture, not the aperture itself -- see "
         "predicted_logmar_per_array_model.csv, deviation_from_theoretical_optimum_logmar column."],
        ["Correction made during THIS analysis", "The pre-existing stage4_human_vision/outputs/"
         "validation_predicted_vs_observed.csv (+ validation_regression_stats.csv, calibration_*.csv) "
         "were found to predate (2026-07-29) the 2026-08-06 stage2/->stage2_fixed/ optics fix by 8 "
         "days -- confirmed by file mtime and by direct re-run giving a materially different result. "
         "A correct '_postfix' re-run already existed (also 2026-08-06) but its calibration step was "
         "never redone. This report uses the postfix predictions throughout and adds the missing "
         "calibration recomputation -- not a new bug, but a stale/incomplete-refresh gap, same family "
         "as the earlier-found grid_N=2048 staleness."],
        ["Separate, unrelated finding surfaced while checking this", "master_dashboard/wrappers.py's "
         "sweep_stage4_acuity() also omits grid_N (defaults to 2048) -- it is an interactive-"
         "dashboard-only function (no committed/reported CSV output depends on it), so lower "
         "priority than the two fixed/checked call sites above, but flagged for awareness."],
    ], columns=["topic", "explanation"])

    with pd.ExcelWriter(os.path.join(HERE, "predicted_logmar_per_array_model.xlsx"), engine="openpyxl") as xl:
        detail.to_excel(xl, sheet_name="detail_per_model_per_M", index=False)
        wide.to_excel(xl, sheet_name="wide_by_model")
        global_df.to_excel(xl, sheet_name="global_design_across_M", index=False)
        pred_vs_obs.to_excel(xl, sheet_name="wang2009_pred_vs_observed", index=False)
        reg_stats.to_excel(xl, sheet_name="wang2009_R2_regression_stats", index=False)
        calib_stats.to_excel(xl, sheet_name="wang2009_calibration_postfix", index=False)
        methodology.to_excel(xl, sheet_name="methodology_README", index=False)
    print("wrote predicted_logmar_per_array_model.xlsx (7 sheets)")


if __name__ == "__main__":
    main()
