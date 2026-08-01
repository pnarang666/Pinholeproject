"""
Runs metrics.compute_all_metrics across a representative (a_hole, M) grid at a fixed
wavelength/gap, caching the M=0 diffraction-limited reference per aperture (~2x sweep
cost saving vs. recomputing it for every M). This is the PSF-level sweep task 32 in
the project plan refers to -- coarser than Stage 2's own 630-point r_EE(P)-only sweep,
because every point here also costs an MTF FFT and a second (M=0) full propagation.

Grid: same 15 aperture values already used throughout Stage 2 / model_comparison
(75-2000um), all 7 M values, primary wavelength 550nm, gap 12mm. A smaller wavelength
comparison (polychromatic effect on THESE metrics specifically) is run separately at
a coarser aperture set to bound total compute -- see run_stage3.py.
"""

import os
import time

import pandas as pd

import metrics

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")

APERTURE_VALUES_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
M_VALUES = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]


def run_sweep(aperture_values_um=APERTURE_VALUES_UM, M_values=M_VALUES,
              wavelength_nm=550.0, z_gap_mm=12.0, D_pupil_um=4000.0,
              grid_N=2048, window_L_mm=6.0, log=True):
    wavelength = wavelength_nm * 1e-9
    d_gap = z_gap_mm * 1e-3

    rows = []
    total = len(aperture_values_um) * len(M_values)
    done = 0
    t0 = time.time()

    for a_um in aperture_values_um:
        a_hole = a_um * 1e-6
        I_dl = metrics.get_diffraction_limited_reference(
            a_hole, wavelength, d_gap, D_pupil_um, grid_N=grid_N, window_L_mm=window_L_mm)
        for M in M_values:
            row = metrics.compute_all_metrics(
                a_hole, wavelength, d_gap, M, D_pupil_um,
                grid_N=grid_N, window_L_mm=window_L_mm, precomputed_I_dl=I_dl)
            rows.append(row)
            done += 1
            if log and (done % 10 == 0 or done == total):
                print(f"  {done}/{total} ({time.time()-t0:.0f}s elapsed)")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Running PSF-level metrics sweep: {len(APERTURE_VALUES_UM)} apertures x "
          f"{len(M_VALUES)} myopia levels at 550nm, gap=12mm...")
    df = run_sweep()
    out_path = os.path.join(OUT_DIR, "metrics_sweep.csv")
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    n_fail = (~df["junction_check_passed"]).sum()
    if n_fail:
        print(f"NOTE: {n_fail}/{len(df)} points failed the junction check.")
