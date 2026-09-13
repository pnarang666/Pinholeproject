"""
Fresh acuity-model sweep against the corrected optics (stage2_fixed/, reached via
stage4_human_vision/pipeline.py post the import-shadowing fix -- PHYSICS_AUDIT.md /
RESULTS.md). Computes stage4_human_vision's own "recommended" predicted acuity
(logMAR, MAR arcmin, Snellen denominator) for every (aperture, M) pair on the same
15 x 8 grid run_blur_sweep.py uses, so the two are directly comparable on one grid.

No locked/pre-registered parameter (brightness-correction slope, CSF model choice,
adaptation) is touched -- every call uses stage4_human_vision's own existing defaults.

Run once, from scratch -- does not read or append to any existing CSV.

CORRECTED 2026-09-12: grid_N was previously left at run_stage4_point's own
default (2048) -- the same grid-resolution artifact run_blur_sweep.py fixed
on 2026-08-16 (r_EE values ~2x too large for large apertures), but this
script's own call site was never updated to match. Now passes grid_N=4096
explicitly, matching run_blur_sweep.py, so the two sweeps are on the same
corrected grid. The stale (grid_N=2048) acuity_sweep_stage4.csv, and every
file derived from it (table1_optimum_summary.csv, per_M_optimum_map.csv,
figures/fig_M*.png), was regenerated -- see new_sweeps/TIMELINE.txt.

Run: python3 run_acuity_sweep.py
"""
import os
import sys
import time

import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from stage4_human_vision.pipeline import run_stage4_point

A_HOLE_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
M_VALUES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
WAVELENGTH_NM = 550.0
D_GAP_MM = 12.0

OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "acuity_sweep_stage4.csv")


def main():
    rows = []
    t0 = time.time()
    total = len(M_VALUES) * len(A_HOLE_UM)
    n = 0
    for M in M_VALUES:
        for a_um in A_HOLE_UM:
            n += 1
            r = run_stage4_point(a_hole_um=a_um, wavelength_nm=WAVELENGTH_NM,
                                  d_gap_mm=D_GAP_MM, M_diopters=M, grid_N=4096)
            row = {"a_hole_um": a_um, "M_diopters": M, "junction_ok": r.junction_check_passed}
            if r.junction_check_passed:
                row["recommended_model"] = r.acuity["recommended_model"]
                row["mar_arcmin"] = r.acuity["mar_arcmin"]
                row["logmar"] = r.acuity["logmar"]
                row["snellen_denominator"] = r.acuity["snellen_denominator"]
                row["vsotf"] = r.visual_strehl.get("vsotf")
                row["retinal_illuminance_td"] = r.illuminance.get("retinal_illuminance_photopic_td")
            rows.append(row)
            elapsed = time.time() - t0
            print(f"[{n}/{total}] a={a_um}um M={M}D ok={row['junction_ok']} "
                  f"logmar={row.get('logmar', float('nan')):.3f} "
                  f"(elapsed {elapsed:.0f}s)", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV} ({len(df)} rows)")


if __name__ == "__main__":
    main()
