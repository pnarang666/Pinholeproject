"""
Single-hole illumination sweep. Array sweep is NOT included here -- see
illumination_model.py's module docstring: stage_array/ (the multi-hole array
photometry + no-ghost pitch module this was originally meant to reuse) does not
exist anywhere in this project, and this project does not invent new physics to
fill that gap. Every row this script writes has row_type="single_hole"; a caller
should not assume row_type="array" rows exist in the output CSV.

Aperture grid: the same 15 discrete values already used in
stage3a/multi_EE_sweep.csv (75-2000um) -- reused directly (not re-picked) so results
are point-for-point comparable to every other sweep in this project without
interpolation.

D_pupil_um: [3000, 4000, 5000] -- natural pupil diameter varies with lighting
condition/individual (this project's other stages default to a single 4000um value
without exploring that range for illumination specifically; this sweep does not
repeat that narrowing).
"""

import os

import pandas as pd

import illumination_model

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")

APERTURE_VALUES_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
D_PUPIL_VALUES_UM = [3000.0, 4000.0, 5000.0]


def run_single_hole_sweep(aperture_values_um=APERTURE_VALUES_UM, D_pupil_values_um=D_PUPIL_VALUES_UM):
    rows = []
    for D_pupil_um in D_pupil_values_um:
        for a_hole_um in aperture_values_um:
            result = illumination_model.percent_illumination(a_hole_um, D_pupil_um)
            rows.append({
                "row_type": "single_hole",
                "a_hole_um": a_hole_um,
                "D_pupil_um": D_pupil_um,
                "percent_illumination": result["percent_illumination"],
                "N_eff": result["N_eff"],
                "model": result["model"],
                "alignment_case": result["alignment_case"],
                "above_brightness_floor_low_6.25pct": result["percent_illumination"] >= illumination_model.BRIGHTNESS_FLOOR_LOW,
                "above_brightness_floor_high_9pct": result["percent_illumination"] >= illumination_model.BRIGHTNESS_FLOOR_HIGH,
            })
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = run_single_hole_sweep()
    out_path = os.path.join(OUT_DIR, "illumination_results.csv")
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path} "
          f"({len(APERTURE_VALUES_UM)} apertures x {len(D_PUPIL_VALUES_UM)} pupil diameters)")
    print("row_type breakdown:", df["row_type"].value_counts().to_dict())
    print()
    print("NOTE: array rows are absent from this file by design -- stage_array/ does "
          "not exist in this project (see illumination_model.py's module docstring "
          "and README.md). Do not silently assume row_type=='array' data is missing "
          "due to a bug here; it is missing because the source module was never built.")


if __name__ == "__main__":
    main()
