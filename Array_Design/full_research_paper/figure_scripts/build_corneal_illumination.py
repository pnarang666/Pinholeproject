"""
build_corneal_illumination.py -- REAL, physically-computed corneal-plane
intensity heatmaps, generated for the first time in this repo.

Calls stage2_fixed/phase2_retina.py's run_pipeline_point() -- the same function
Array_Design/array_geometry_lab/retinal_light_distribution_simulation/
realistic_heatmaps/build_realistic_heatmaps.py already calls to get I_retina --
but renders |U_cornea|^2 from result["cornea_result"]["U_cornea"] instead: the
real field immediately after the pinhole-diffraction propagation to the cornea,
BEFORE the eye's lens phase and retina propagation are applied. U_cornea is
already computed as part of the same run_pipeline_point() call the retinal
heatmaps use -- no extra physics, just a different field from the same result.

Same parameters as build_realistic_heatmaps.py and new_sweeps/run_acuity_sweep.py:
wavelength=550nm, d_gap=12mm, grid_N=4096, window_L_mm=6.0, D_pupil_um=4000,
P0=60, n_prime=1.336, refractive_index_correction=True. Same real per-M apertures,
read fresh from array_data/evaluation_results/PRIMARY_WINNER_PER_M.csv (not
assumed from memory).

Each heatmap normalized to its own peak (same reason as the retinal ones: no
radiometric source-power calibration exists to compare absolute magnitude
across M).

Run: python3 build_corneal_illumination.py
"""
import os
import sys
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PAPER))
EVAL_DIR = os.path.join(REPO, "Array_Design", "array_geometry_lab", "array_data", "evaluation_results")
FIGURES_DIR = os.path.join(PAPER, "figures")

sys.path.insert(0, os.path.join(REPO, "stage2_fixed"))
import phase2_retina as stage2_retina  # noqa: E402

WAVELENGTH_NM = 550.0
D_GAP_MM = 12.0
GRID_N = 4096
WINDOW_L_MM = 6.0
D_PUPIL_UM = 4000.0
P0 = 60.0
N_PRIME = 1.336

HALF_WIDTH_UM = 1300.0  # cornea-plane field is much less tightly focused than the
                        # retinal image -- checked empirically before fixing this value:
                        # radius-to-1%-of-peak measured at 1063um for a=2000um/M=0D (the
                        # widest real case), 434um for a=750um/M=2D, 267um for a=400um/M=8D.
                        # 1300um covers the widest case with margin; smaller apertures show
                        # more background context, which is fine.


def load_M_apertures():
    df = pd.read_csv(os.path.join(EVAL_DIR, "PRIMARY_WINNER_PER_M.csv"), dtype={"M": str})
    df = df[df.M != "global"].copy()
    df["M"] = df.M.astype(float)
    return dict(zip(df.M, df.a_hole_um))


def compute_corneal_intensity(a_hole_um, M):
    result = stage2_retina.run_pipeline_point(
        a_hole=a_hole_um * 1e-6, wavelength=WAVELENGTH_NM * 1e-9, d_gap=D_GAP_MM * 1e-3,
        grid_N=GRID_N, window_L_mm=WINDOW_L_MM, M_diopters=M, P0=P0, n_prime=N_PRIME,
        D_pupil_um=D_PUPIL_UM, refractive_index_correction=True)
    assert result["junction_check_passed"], f"junction check failed at a={a_hole_um}um M={M}D: {result['junction_fail_reason']}"
    U_cornea = result["cornea_result"]["U_cornea"]
    dx = result["cornea_result"]["dx"]
    I_cornea = np.abs(U_cornea) ** 2
    return I_cornea, dx


def crop_center(I, dx_m, half_width_um):
    N = I.shape[0]
    half_px = int(round((half_width_um * 1e-6) / dx_m))
    c = N // 2
    lo, hi = c - half_px, c + half_px
    return I[lo:hi, lo:hi]


def build_one(M, a_hole_um):
    t0 = time.time()
    I_cornea, dx = compute_corneal_intensity(a_hole_um, M)
    I_crop = crop_center(I_cornea, dx, HALF_WIDTH_UM)
    I_norm = I_crop / I_crop.max()

    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    im = ax.imshow(I_norm, cmap="viridis", origin="lower", interpolation="bicubic",
                   extent=[-HALF_WIDTH_UM, HALF_WIDTH_UM, -HALF_WIDTH_UM, HALF_WIDTH_UM])
    ax.set_xlabel("corneal-plane position (um)")
    ax.set_ylabel("corneal-plane position (um)")
    ax.set_title(f"Real corneal-plane intensity distribution\nM = {M:.0f}D, aperture = {a_hole_um:.0f}um "
                f"(post-pinhole, pre-lens)", fontsize=12, fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("intensity (normalized to this image's own peak)")
    fig.text(0.5, 0.032, "Real ASM wave-optics simulation (stage2_fixed, U_cornea field),",
             ha="center", fontsize=7.5, color="#555")
    fig.text(0.5, 0.012, "normalized to its own peak -- not comparable in brightness across M.",
             ha="center", fontsize=7.5, color="#555")
    plt.tight_layout(rect=[0, 0.09, 1, 1])
    out_path = os.path.join(FIGURES_DIR, f"corneal_illumination_M{M:.0f}.png")
    fig.savefig(out_path, dpi=170)
    plt.close(fig)
    print(f"wrote {out_path} (M={M:.0f}D, a={a_hole_um:.0f}um, peak_I={I_crop.max():.4e}, {time.time()-t0:.1f}s)")


def main():
    apertures = load_M_apertures()
    for M in sorted(apertures.keys()):
        build_one(M, apertures[M])


if __name__ == "__main__":
    main()
