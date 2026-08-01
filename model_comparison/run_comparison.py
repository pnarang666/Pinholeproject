"""
Runs (or reuses) all three models on the same grid and merges into one comparison CSV:

  Model 1 (stage1_runner)        -- exact ASM, cornea plane only, no myopia/eye
  Model 2 (stage2_runner)        -- exact ASM x2 + lens, full retina chain, axial myopia
  Model 3 (approximation_runner) -- closed-form RSS formula chain from the handbooks

Model 2's existing 630-point sweep (stage2/outputs/r1_full_range_sweep.csv) already
covers the (a_hole, wavelength, d_gap, M) grid this comparison needs -- reused directly
rather than re-run. Model 3 is cheap (pure algebra) and evaluated fresh on that same
grid. Model 1 has no myopia axis, so it's compared separately at the cornea plane only
(stage2/outputs/stage1_sweep_summary.csv, already computed).
"""

import os

import pandas as pd

import approximation_runner as approx

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
STAGE2_OUTPUTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage2", "outputs")


def build_retina_comparison():
    """Model 2 (already computed) + Model 3 (computed fresh here) on the same grid."""
    df2 = pd.read_csv(os.path.join(STAGE2_OUTPUTS, "r1_full_range_sweep.csv"))

    rows = []
    for _, row in df2.iterrows():
        a_hole = row["a_hole_um"] * 1e-6
        wavelength = row["wavelength_nm"] * 1e-9
        d_gap = row["z_gap_mm"] * 1e-3
        M = row["M_diopters"]

        approx_result = approx.approximate_blur(a_hole, wavelength, d_gap, M,
                                                  P0=row["P0"], n_prime=row["n_prime"],
                                                  D_pupil_um=row["D_pupil_um"])
        rows.append({
            "a_hole_um": row["a_hole_um"], "wavelength_nm": row["wavelength_nm"],
            "z_gap_mm": row["z_gap_mm"], "M_diopters": M,
            "stage2_r_EE_50_um": row["r_EE_50_retina_um"],
            "stage2_r_EE_80_um": row["r_EE_80_retina_um"],
            "stage2_r_EE_90_um": row["r_EE_90_retina_um"],
            "approx_r_total_um": approx_result["r_total_approx"] * 1e6,
            "approx_a_star_um": approx_result["a_star_approx"] * 1e6,
            "junction_check_passed": row["junction_check_passed"],
        })

    df = pd.DataFrame(rows)
    df["rel_diff_r_total_vs_r_EE50_pct"] = (
        (df["approx_r_total_um"] - df["stage2_r_EE_50_um"]).abs() / df["stage2_r_EE_50_um"] * 100
    )
    return df


def build_cornea_comparison():
    """Model 1 (already computed) + Model 3's a_eff (computed fresh here), no myopia axis."""
    df1 = pd.read_csv(os.path.join(STAGE2_OUTPUTS, "stage1_sweep_summary.csv"))

    rows = []
    for _, row in df1.iterrows():
        a_hole = row["a_hole_um"] * 1e-6
        wavelength = row["wavelength_nm"] * 1e-9
        d_gap = row["z_gap_mm"] * 1e-3
        a_eff_val = approx.approximate_blur(a_hole, wavelength, d_gap, M_diopters=1.0)["a_eff_cornea_approx"]
        rows.append({
            "a_hole_um": row["a_hole_um"], "wavelength_nm": row["wavelength_nm"],
            "z_gap_mm": row["z_gap_mm"],
            "stage1_r_EE_80_um": row["r_EE_80pct_um"],
            "approx_a_eff_um": a_eff_val * 1e6,
        })
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    retina_df = build_retina_comparison()
    retina_df.to_csv(os.path.join(OUT_DIR, "retina_model_comparison.csv"), index=False)
    print(f"Wrote {len(retina_df)} rows to retina_model_comparison.csv "
          f"(stage2 exact vs approximation formula)")

    cornea_df = build_cornea_comparison()
    cornea_df.to_csv(os.path.join(OUT_DIR, "cornea_model_comparison.csv"), index=False)
    print(f"Wrote {len(cornea_df)} rows to cornea_model_comparison.csv "
          f"(stage1 exact vs a_eff approximation)")


if __name__ == "__main__":
    main()
