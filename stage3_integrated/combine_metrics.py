"""
Combines stage3a's brightness-constrained-optimum logic with stage3_human_vision's
full metric set on ONE shared sweep grid (15 apertures x 7 M, 550nm/12mm -- the grid
both source datasets already share, confirmed identical below).

Reuses, does not recompute: stage3_human_vision/outputs/phase3_full_metrics.csv
(MTF50/10, Strehl, RMS radius, photometry, acuity -- from stage3_human_vision/
run_stage3.py) and stage3a/multi_EE_sweep.csv (r_EE at 50/70/80/90% -- from
stage2_fixed/recompute_multi_EE.py). Neither stage2/stage2_fixed/stage3a/
stage3_human_vision is imported for its CODE here beyond the one cross-checked
formula noted below -- this module only reads their already-computed CSV outputs.

Cross-check performed before merging (see stage3_integrated/README.md): stage3a/
transmission.py::relative_illuminance() and stage3_human_vision/photometry.py::
relative_retinal_illuminance() (== metrics.py::throughput_area_ratio()) agree
EXACTLY at every tested point (75/400/1200/4000 um). Standardized on
stage3_human_vision's version below (phase3_full_metrics.csv's own
'relative_retinal_illuminance' column) since it carries the fuller citation trail
in stage3_human_vision/literature.py; stage3a's transmission.py is retired in favor
of it, not deleted -- both remain on disk for reference.
"""

import os

import numpy as np
import pandas as pd

STAGE3_HV_METRICS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                  "stage3_human_vision", "outputs", "phase3_full_metrics.csv")
STAGE3A_MULTI_EE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                 "stage3a", "multi_EE_sweep.csv")

CLINICAL_BRACKET_UM = (940, 1750)  # see stage3a/README.md citation

# Every metric this project has produced, with its optimization direction. Extends
# comparison.py's CANDIDATE_METRICS (r_EE_80/50, rms, strehl, mtf50, throughput) with
# the newly-available r_EE_70 and the acuity-prediction columns.
ALL_METRICS = {
    "min_r_EE_50": ("r_EE_50_um", "min"),
    "min_r_EE_70": ("r_EE_70_um", "min"),
    "min_r_EE_80": ("r_EE_80_um", "min"),
    "min_r_EE_90": ("r_EE_90_um", "min"),
    "min_rms_radius": ("rms_spot_radius_um", "min"),
    "min_fwhm": ("fwhm_radius_um", "min"),
    "max_strehl": ("strehl_ratio", "max"),
    "max_mtf50": ("mtf50_cpd", "max"),
    "min_mar_mtf50": ("mar_arcmin_mtf50", "min"),
    "min_mar_mtf10": ("mar_arcmin_mtf10", "min"),
    "min_logmar_mtf50": ("logmar_mtf50", "min"),
    "max_throughput": ("throughput_area_ratio", "max"),
}

T_MIN_VALUES = [0.0, 0.005, 0.01, 0.02, 0.03, 0.0625, 0.09, 0.1225, 0.16, 0.25]


def build_combined_grid():
    """Merges the two 105-point (15 aperture x 7 M) CSVs into one dataframe."""
    hv = pd.read_csv(STAGE3_HV_METRICS)
    ee = pd.read_csv(STAGE3A_MULTI_EE)

    # Both were generated from the same A_HOLE_UM/M_diopters lists (see
    # stage2_fixed/recompute_multi_EE.py and stage3_human_vision/run_metrics_sweep.py)
    # -- round before merging since independent float arithmetic (e.g. 1e6 * 1e-6)
    # can differ in the last bit.
    hv["a_hole_um_key"] = hv["a_hole_um"].round(3)
    ee["a_hole_um_key"] = ee["a_hole_um"].round(3)

    merged = hv.merge(
        ee[["a_hole_um_key", "M_diopters", "r_EE_70_um"]],
        on=["a_hole_um_key", "M_diopters"], how="inner", validate="one_to_one",
    )
    n_expected = 105
    if len(merged) != n_expected:
        raise ValueError(f"Expected {n_expected} merged rows (15 apertures x 7 M), got "
                          f"{len(merged)} -- the two source grids no longer match; "
                          f"investigate before trusting downstream tables/plots.")
    return merged.drop(columns=["a_hole_um_key"])


def constrained_optimum_all_metrics(df, T_min_values=T_MIN_VALUES, metrics=ALL_METRICS):
    """
    Generalizes stage3a/combine_and_select.py's single-metric (r_EE_50) constrained
    argmin to EVERY metric in `metrics`, reproducing (and extending) the
    "all percentiles converge under a brightness floor" finding across the full set.

    a*_practical(M, T_min, metric) = argmin/argmax_{a_hole : E_rel(a_hole) >= T_min} metric(a_hole, M)
    """
    rows = []
    Ms = sorted(df["M_diopters"].unique())
    for M in Ms:
        sub = df[df["M_diopters"] == M].sort_values("a_hole_um")
        for T_min in T_min_values:
            cand = sub[sub["relative_retinal_illuminance"] >= T_min]
            row = {"M_diopters": M, "T_min": T_min, "n_candidates": len(cand)}
            for label, (col, direction) in metrics.items():
                if len(cand) == 0:
                    row[f"a_star_{label}_um"] = np.nan
                    continue
                idx = cand[col].idxmin() if direction == "min" else cand[col].idxmax()
                row[f"a_star_{label}_um"] = cand.loc[idx, "a_hole_um"]
            rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(out_dir, exist_ok=True)

    df = build_combined_grid()
    df.to_csv(os.path.join(out_dir, "combined_grid_550nm_12mm.csv"), index=False)
    print(f"Wrote combined_grid_550nm_12mm.csv ({len(df)} rows, {len(df.columns)} columns)")

    constrained = constrained_optimum_all_metrics(df)
    constrained.to_csv(os.path.join(out_dir, "constrained_optimum_all_metrics.csv"), index=False)
    print(f"Wrote constrained_optimum_all_metrics.csv ({len(constrained)} rows)")

    # Quick convergence check at T_min=6.25%, echoing stage3a's own finding, now
    # across ALL metrics (not just r_EE_50/70/80/90).
    at_floor = constrained[np.isclose(constrained["T_min"], 0.0625)]
    a_star_cols = [c for c in constrained.columns if c.startswith("a_star_")]
    print("\nAt T_min=6.25%, optimum by metric (all M):")
    print(at_floor[["M_diopters"] + a_star_cols].to_string(index=False))
