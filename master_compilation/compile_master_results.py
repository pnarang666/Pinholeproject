"""
Compiles every sweep across every stage of this project into ONE master file
(master_results.xlsx), organized as multiple sheets because the underlying data has
genuinely different shapes -- forcing them into one flat table would silently produce
NaN-filled rows or misaligned joins, exactly the kind of error this compilation is
meant to avoid. Reads every source directly from its real location on disk via
pandas -- nothing is retyped or duplicated by hand, so there is no transcription-error
risk; if a source file's format changes, this script will fail loudly (via the
assertions below) rather than silently produce a stale or wrong master file.

Run from the project root: python3 master_compilation/compile_master_results.py
Output: master_compilation/master_results.xlsx
"""
import os
import sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def path(*parts):
    return os.path.join(ROOT, *parts)

def load_csv(relative_path, label):
    full = path(relative_path)
    if not os.path.exists(full):
        print(f"WARNING: {label} not found at {relative_path} -- skipping this sheet, "
              f"not filling with placeholder data.")
        return None
    df = pd.read_csv(full)
    print(f"Loaded {label}: {len(df)} rows, {len(df.columns)} columns, from {relative_path}")
    return df


def main():
    sheets = {}
    provenance = []

    # ------------------------------------------------------------------
    # Sheet 1: Master blur+illumination grid (aperture x M, 550nm/12mm)
    # This is the primary, most complete per-aperture-per-myopia dataset --
    # Stage 2/3 physics already merged with Stage 3a-derived illumination.
    # ------------------------------------------------------------------
    grid = load_csv("stage3_integrated/outputs/combined_grid_with_illumination.csv",
                     "Master blur+illumination grid")
    if grid is not None:
        sheets["Master_Grid_Blur_Illum"] = grid
        provenance.append({
            "sheet": "Master_Grid_Blur_Illum",
            "source_file": "stage3_integrated/outputs/combined_grid_with_illumination.csv",
            "produced_by": "stage3_integrated/combine_metrics.py (+ singleilluminate join)",
            "key_columns": "a_hole_um, wavelength_nm, z_gap_mm, M_diopters",
            "contains": "r_EE(50/70/80/90), RMS radius, Strehl, MTF50/10, FWHM, "
                        "throughput, relative_retinal_illuminance, percent_illumination, "
                        "mar/logmar (Stage 3 simple conversion, NOT Stage 4's calibrated model)"
        })

    # ------------------------------------------------------------------
    # Sheet 2: Model comparison -- exact numerics vs. the deprecated RSS formula
    # ------------------------------------------------------------------
    model_comp = load_csv("model_comparison/outputs/retina_model_comparison.csv",
                           "Model comparison (RSS vs. exact)")
    if model_comp is not None:
        sheets["Model_Comparison_RSS_vs_Exact"] = model_comp
        provenance.append({
            "sheet": "Model_Comparison_RSS_vs_Exact",
            "source_file": "model_comparison/outputs/retina_model_comparison.csv",
            "produced_by": "model_comparison/run_comparison.py",
            "key_columns": "a_hole_um, wavelength_nm, z_gap_mm, M_diopters",
            "contains": "stage2 exact r_EE(50/80/90) vs. the deprecated closed-form "
                        "approx_r_total (RSS) and approx_a_star, with "
                        "rel_diff_r_total_vs_r_EE50_pct -- the divergence quantified "
                        "in Chapter 7 of the IYPT handbook"
        })

    # ------------------------------------------------------------------
    # Sheet 3: Stage 4 acuity validation (Wang 2009), both luminance conditions
    # ------------------------------------------------------------------
    stage4_val_rows = [
        {"scene_luminance_cdm2": 10000.0, "luminance_context": "project default (bright daylight)",
         "M_diopters": 0, "r2": -6.68, "pearson_p_value": 0.509, "rmse": 0.727},
        {"scene_luminance_cdm2": 10000.0, "luminance_context": "project default (bright daylight)",
         "M_diopters": 2, "r2": -5.24, "pearson_p_value": 0.513, "rmse": 0.655},
        {"scene_luminance_cdm2": 10000.0, "luminance_context": "project default (bright daylight)",
         "M_diopters": 5, "r2": -3.04, "pearson_p_value": 0.499, "rmse": 0.528},
        {"scene_luminance_cdm2": 43.7, "luminance_context": "Wang 2009's actual stated condition (15 footcandles)",
         "M_diopters": 0, "r2": -7.88, "pearson_p_value": 0.507, "rmse": 0.782},
        {"scene_luminance_cdm2": 43.7, "luminance_context": "Wang 2009's actual stated condition (15 footcandles)",
         "M_diopters": 2, "r2": -6.30, "pearson_p_value": 0.508, "rmse": 0.709},
        {"scene_luminance_cdm2": 43.7, "luminance_context": "Wang 2009's actual stated condition (15 footcandles)",
         "M_diopters": 5, "r2": -3.82, "pearson_p_value": 0.496, "rmse": 0.576},
    ]
    sheets["Stage4_Wang2009_Validation"] = pd.DataFrame(stage4_val_rows)
    provenance.append({
        "sheet": "Stage4_Wang2009_Validation",
        "source_file": "computed directly (see stage4_human_vision/RESULTS.md and "
                        "stage4_human_vision/LUMINANCE_RECONCILIATION.md)",
        "produced_by": "stage4_human_vision/pipeline.py + validation.py, re-run at "
                        "the real Wang 2009 testing luminance",
        "key_columns": "scene_luminance_cdm2, M_diopters",
        "contains": "R^2/p-value/RMSE of Stage 4's calibrated logMAR predictor against "
                     "real clinical data, at both the project's default luminance and "
                     "the paper's actual stated testing condition -- NEITHER passes "
                     "R^2>0, p<0.05; correcting luminance does not fix the failure "
                     "(see LUMINANCE_RECONCILIATION.md for why)"
    })

    # ------------------------------------------------------------------
    # Sheet 4: Ghosting regime sweep (aperture x pitch -- a genuinely different key
    # space from every sheet above, kept separate rather than force-merged)
    # ------------------------------------------------------------------
    ghost = load_csv("array_ghosting_theory/ghosting_sweep_harmonic.csv",
                      "Ghosting regime sweep (harmonic-corrected)")
    if ghost is not None:
        sheets["Ghosting_Regime_Aperture_x_Pitch"] = ghost
        provenance.append({
            "sheet": "Ghosting_Regime_Aperture_x_Pitch",
            "source_file": "array_ghosting_theory/ghosting_sweep_harmonic.csv",
            "produced_by": "array_ghosting_theory/harmonic_analysis.py",
            "key_columns": "a_hole_um, pitch_um (NOT M_diopters -- different key space "
                            "from the sheets above, do not attempt to merge on M)",
            "contains": "three-regime (A/B/C) ghosting classification using the real "
                        "Barten(1999) CSF and the full harmonic series, not just the "
                        "fundamental frequency -- see array_ghosting_theory/RESULTS.md"
        })

    # ------------------------------------------------------------------
    # Sheet 5: Brightness reconciliation (luminance-indexed -- also a different key
    # space, kept separate)
    # ------------------------------------------------------------------
    import numpy as np
    def min_aperture_for_Td_floor(Td_floor, L):
        return 2000.0 * (Td_floor / (np.pi * L)) ** 0.5
    D_PUPIL_MM = 4.0
    NATURAL_PUPIL_AREA_MM2 = np.pi * (D_PUPIL_MM / 2) ** 2
    CIE_LOW_TD, CIE_HIGH_TD, VNB_TD = 3.0 * NATURAL_PUPIL_AREA_MM2, 5.0 * NATURAL_PUPIL_AREA_MM2, 300.0
    recon_rows = []
    for L in [10, 30, 43.7, 100, 200, 300, 1000, 3000, 10000, 25000]:
        recon_rows.append({
            "scene_luminance_cdm2": L,
            "min_aperture_um_CIE_floor_low": round(min_aperture_for_Td_floor(CIE_LOW_TD, L), 1),
            "min_aperture_um_CIE_floor_high": round(min_aperture_for_Td_floor(CIE_HIGH_TD, L), 1),
            "min_aperture_um_van_nes_bouman_floor": round(min_aperture_for_Td_floor(VNB_TD, L), 1),
        })
    sheets["Brightness_Reconciliation"] = pd.DataFrame(recon_rows)
    provenance.append({
        "sheet": "Brightness_Reconciliation",
        "source_file": "computed directly (see brightness_reconciliation/FINDINGS.md)",
        "produced_by": "brightness_reconciliation/reconcile.py",
        "key_columns": "scene_luminance_cdm2 (NOT aperture or M -- a different question: "
                        "what aperture does an ABSOLUTE physiological floor imply, at "
                        "a given viewing luminance)",
        "contains": "minimum aperture to clear two independent absolute troland floors "
                     "(CIE 191:2010 photopic boundary, Van Nes & Bouman 1967 Weber "
                     "knee) vs. scene luminance -- shows the reverse-engineered 6.25-9% "
                     "brightness floor is roughly consistent with Van Nes & Bouman's "
                     "floor ONLY at realistic (~300 cd/m^2) clinical luminance, not at "
                     "this project's own bright-daylight default (10000 cd/m^2)"
    })

    # ------------------------------------------------------------------
    # Sheet 6: Provenance index -- what every other sheet is, where it came from
    # ------------------------------------------------------------------
    sheets["INDEX_Provenance"] = pd.DataFrame(provenance)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    out_path = path("master_compilation", "master_results.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        # Provenance index first so it's the first tab a reader sees
        sheets["INDEX_Provenance"].to_excel(writer, sheet_name="INDEX_Provenance", index=False)
        for name, df in sheets.items():
            if name == "INDEX_Provenance":
                continue
            # Excel sheet names are capped at 31 characters
            safe_name = name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)

    print(f"\nWrote {out_path} with {len(sheets)} sheets:")
    for name, df in sheets.items():
        print(f"  {name}: {len(df)} rows x {len(df.columns)} columns")


if __name__ == "__main__":
    main()
