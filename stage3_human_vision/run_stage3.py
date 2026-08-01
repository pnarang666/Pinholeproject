"""
Phase 3 orchestrator: runs (or reuses) the metrics sweep, computes photometry/acuity/
contrast quantities, the Pareto/validation/comparison analysis, and every plot.

Usage:
    python3 run_stage3.py                 # reuse outputs/metrics_sweep.csv if present
    python3 run_stage3.py --resweep        # force a fresh PSF-level sweep
"""

import argparse
import os

import numpy as np
import pandas as pd

import comparison
import contrast
import literature
import metrics
import pareto
import photometry
import plots
import run_metrics_sweep
import validation
import visual_acuity

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--resweep", action="store_true", help="Force a fresh PSF-level sweep.")
    args = p.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    sweep_path = os.path.join(OUT_DIR, "metrics_sweep.csv")

    if args.resweep or not os.path.exists(sweep_path):
        print("Running PSF-level metrics sweep...")
        df = run_metrics_sweep.run_sweep()
        df.to_csv(sweep_path, index=False)
    else:
        print(f"Reusing existing sweep at {sweep_path}")
        df = pd.read_csv(sweep_path)

    print(f"\n{len(df)} configurations, {df['junction_check_passed'].sum()} passed junction check.")

    # --- Photometry / acuity / contrast, appended per row ---
    print("Computing photometry and acuity predictions...")
    photometry_rows = []
    for _, row in df.iterrows():
        v_r_m = row["v_r_mm"] * 1e-3
        flux = photometry.photon_flux_at_retina(row["a_hole_um"], v_r_m, row["wavelength_nm"] * 1e-9)
        acuity = visual_acuity.acuity_from_mtf_cutoff(row["mtf50_cpd"], row["mtf10_cpd"])
        rel_ill = photometry.relative_retinal_illuminance(row["a_hole_um"], row["D_pupil_um"])
        photometry_rows.append({
            **flux, **acuity,
            "relative_retinal_illuminance": rel_ill,
        })
    photometry_df = pd.DataFrame(photometry_rows)
    full_df = pd.concat([df.reset_index(drop=True), photometry_df.reset_index(drop=True)], axis=1)
    full_df.to_csv(os.path.join(OUT_DIR, "phase3_full_metrics.csv"), index=False)
    print(f"Wrote phase3_full_metrics.csv ({len(full_df)} rows, {len(full_df.columns)} columns)")

    # --- Validation / comparison ---
    print("\nComparing candidate metrics against clinical/commercial reference range...")
    summary, opt_df = comparison.metric_vs_clinical_distance(full_df)
    summary.to_csv(os.path.join(OUT_DIR, "metric_correlation_summary.csv"))
    opt_df.to_csv(os.path.join(OUT_DIR, "optimum_by_metric_and_M.csv"), index=False)
    print(summary.to_string())

    stage2_opt = validation.stage2_only_optimum(full_df)
    stage2_opt.to_csv(os.path.join(OUT_DIR, "stage2_only_optimum.csv"), index=False)

    err_budget = comparison.error_budget(
        polychromatic_shift_um=85.7,  # measured directly, see README.md
        ocular_aberration_note="~0.33-0.38 micron RMS over a 6mm pupil in normal eyes; "
                                "expected to be much smaller at pinhole-scale apertures "
                                "(<2mm) since higher-order aberration RMS scales steeply "
                                "with aperture -- NOT independently re-derived for this "
                                "specific aperture range in this project.",
    )
    pd.DataFrame(err_budget).to_csv(os.path.join(OUT_DIR, "error_budget.csv"), index=False)

    # --- Plots ---
    print("\nGenerating plots...")
    plots.make_all_plots(full_df)

    print(f"\nDone. All outputs in {OUT_DIR}")


if __name__ == "__main__":
    main()
