"""
build_realistic_heatmaps.py -- REAL, physically-computed retinal light-intensity
heatmaps (not the flat-disc schematic in ../build_retinal_distribution.py).

Straight-ahead gaze only (phi=0, theta=0) -- at zero gaze eccentricity every real
array winner in this project has exactly ONE active hole (confirmed elsewhere:
n_active_holes_phi0=1 for every row in PRIMARY_WINNER_PER_M.csv), so the retinal
image is identical to a standalone single pinhole of that aperture at that M --
no array-specific ghost/blind geometry needed for this view.

Calls stage2_fixed/phase2_retina.run_pipeline_point() DIRECTLY (the same function
stage4_human_vision/pipeline.py itself calls internally) to get the actual
I_retina 2D wave-optics intensity array -- not a flat circle, the REAL diffraction+
defocus PSF this project's own physics produces. Same parameters as
new_sweeps/run_acuity_sweep.py (the established, corrected reference sweep):
wavelength=550nm, d_gap=12mm, grid_N=4096, window_L_mm=6.0, D_pupil_um=4000,
P0=60, n_prime=1.336, refractive_index_correction=True.

One design per M (the real PRIMARY_WINNER_PER_M aperture for that M), one PNG per
M, saved separately (not a multi-panel grid) for direct use in a presentation.

Each heatmap is normalized to ITS OWN peak (stated on every image) -- necessary
because raw |U|^2 units are not comparable in magnitude across M without a
radiometric source-power calibration this project has not made; the SHAPE and
RELATIVE size of the blur is real, the absolute color scale is per-image.

Run: python3 build_realistic_heatmaps.py
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
LAB = os.path.dirname(os.path.dirname(HERE))
REPO = os.path.dirname(os.path.dirname(LAB))
EVAL_DIR = os.path.join(LAB, "array_data", "evaluation_results")

sys.path.insert(0, os.path.join(REPO, "stage2_fixed"))
import phase2_retina as stage2_retina  # noqa: E402

WAVELENGTH_NM = 550.0
D_GAP_MM = 12.0
GRID_N = 4096
WINDOW_L_MM = 6.0
D_PUPIL_UM = 4000.0
P0 = 60.0
N_PRIME = 1.336

HALF_WIDTH_UM = 150.0  # fixed crop window, same for every M -- lets relative
                       # blur SIZE be compared directly across M on one visual scale


def load_M_apertures():
    df = pd.read_csv(os.path.join(EVAL_DIR, "PRIMARY_WINNER_PER_M.csv"), dtype={"M": str})
    df = df[df.M != "global"].copy()
    df["M"] = df.M.astype(float)
    return dict(zip(df.M, df.a_hole_um))


def compute_I_retina(a_hole_um, M):
    result = stage2_retina.run_pipeline_point(
        a_hole=a_hole_um * 1e-6, wavelength=WAVELENGTH_NM * 1e-9, d_gap=D_GAP_MM * 1e-3,
        grid_N=GRID_N, window_L_mm=WINDOW_L_MM, M_diopters=M, P0=P0, n_prime=N_PRIME,
        D_pupil_um=D_PUPIL_UM, refractive_index_correction=True)
    assert result["junction_check_passed"], f"junction check failed at a={a_hole_um}um M={M}D: {result['junction_fail_reason']}"
    return result["I_retina"], result["cornea_result"]["dx"]


def crop_center(I, dx_m, half_width_um):
    N = I.shape[0]
    half_width_m = half_width_um * 1e-6
    half_px = int(round(half_width_m / dx_m))
    c = N // 2
    lo, hi = c - half_px, c + half_px
    return I[lo:hi, lo:hi]


def build_one(M, a_hole_um):
    t0 = time.time()
    I_retina, dx = compute_I_retina(a_hole_um, M)
    I_crop = crop_center(I_retina, dx, HALF_WIDTH_UM)
    I_norm = I_crop / I_crop.max()
    extent_um = HALF_WIDTH_UM

    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    im = ax.imshow(I_norm, cmap="inferno", origin="lower", interpolation="bicubic",
                   extent=[-extent_um, extent_um, -extent_um, extent_um])
    ax.set_xlabel("retinal position (um)")
    ax.set_ylabel("retinal position (um)")
    ax.set_title(f"Real light-intensity distribution on retina\nM = {M:.0f}D, aperture = {a_hole_um:.0f}um "
                f"(straight-ahead gaze)", fontsize=12, fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("intensity (normalized to this image's own peak)")
    fig.text(0.5, 0.032, "Real ASM wave-optics simulation (stage2_fixed),", ha="center", fontsize=7.5, color="#555")
    fig.text(0.5, 0.012, "normalized to its own peak -- not comparable in brightness across M.",
             ha="center", fontsize=7.5, color="#555")
    plt.tight_layout(rect=[0, 0.09, 1, 1])
    out_path = os.path.join(HERE, f"realistic_heatmap_M{M:.0f}.png")
    fig.savefig(out_path, dpi=170)
    plt.close(fig)
    print(f"wrote {out_path} (M={M:.0f}D, a={a_hole_um:.0f}um, {time.time()-t0:.1f}s)")


def main():
    apertures = load_M_apertures()
    for M in sorted(apertures.keys()):
        build_one(M, apertures[M])


if __name__ == "__main__":
    main()
