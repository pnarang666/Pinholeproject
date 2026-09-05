"""
Fresh blur-optimization sweep against the corrected optics (stage2_fixed/, post the
lens-wavelength fix -- PHYSICS_AUDIT.md item A/B). Computes r_EE(50/70/80/90%) and the
second-moment (RMS) spot radius at the retina plane, for every (aperture, M) pair on a
15 x 8 grid, matching this project's own standard aperture list and an extended M range
(M=0 included as the emmetropic baseline, not just M=1-8D).

Run once, from scratch -- does not read or append to any existing CSV (multi_EE_sweep.csv
or any *_baseline/*_audit output from earlier tasks).

Run: python3 run_blur_sweep.py
"""
import os
import sys
import time

import numpy as np
import pandas as pd

_STAGE2_FIXED = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage2_fixed"))
if _STAGE2_FIXED not in sys.path:
    sys.path.insert(0, _STAGE2_FIXED)

import phase2_retina as p2  # noqa: E402
import pipeline_junction as junction  # noqa: E402

A_HOLE_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
M_VALUES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
WAVELENGTH_NM = 550.0
D_GAP_MM = 12.0
D_PUPIL_UM = 4000.0
GRID_N = 4096  # Corrected 2026-08-16: was 2048, matched the r_max_lens grid
                # artifact already found and fixed in array_optimization/
                # (Defect 1). Confirmed stale via Phase 2 full-physics
                # confirmation: blur_sweep.csv values at grid_N=2048 were
                # exactly 2x the grid_N=4096 fresh value for large apertures,
                # and identical across DIFFERENT aperture sizes (a clear
                # shared-artifact fingerprint). Old file preserved as
                # blur_sweep_gridN2048_legacy.csv.
WINDOW_L_MM = 6.0
PERCENTILES = [0.50, 0.70, 0.80, 0.90]

OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blur_sweep.csv")


def main():
    rows = []
    t0 = time.time()
    total = len(M_VALUES) * len(A_HOLE_UM)
    n = 0
    for M in M_VALUES:
        for a_um in A_HOLE_UM:
            n += 1
            result = p2.run_pipeline_point(
                a_hole=a_um * 1e-6, wavelength=WAVELENGTH_NM * 1e-9, d_gap=D_GAP_MM * 1e-3,
                grid_N=GRID_N, window_L_mm=WINDOW_L_MM, M_diopters=M, P0=60.0, n_prime=1.336,
                D_pupil_um=D_PUPIL_UM, refractive_index_correction=True,
            )
            row = {"a_hole_um": a_um, "M_diopters": M, "junction_ok": result["junction_check_passed"]}
            if result["junction_check_passed"]:
                I_retina = result["I_retina"]
                dx = result["cornea_result"]["dx"]
                N = I_retina.shape[0]
                L = N * dx
                _, _, R, _ = junction.make_grid(N, L)
                r_edges, EE, total_power = junction.encircled_energy(I_retina, R, dx)
                for p in PERCENTILES:
                    row[f"r_EE_{int(p*100)}_um"] = junction.r_for_EE(r_edges, EE, p) * 1e6
                row["rms_radius_um"] = junction.second_moment_radius(I_retina, R, dx) * 1e6
            rows.append(row)
            elapsed = time.time() - t0
            print(f"[{n}/{total}] a={a_um}um M={M}D ok={row['junction_ok']} "
                  f"r_EE_50={row.get('r_EE_50_um', float('nan')):.2f}um "
                  f"rms={row.get('rms_radius_um', float('nan')):.2f}um "
                  f"(elapsed {elapsed:.0f}s)", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV} ({len(df)} rows)")


if __name__ == "__main__":
    main()
