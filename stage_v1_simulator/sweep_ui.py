"""
Live sweep runner + flexible interactive plotting for the Sweep & Explore tab.

run_custom_sweep() reuses live_compute.compute_point() (itself a thin wrapper around
stage2_fixed/phase2_retina.py + stage3_human_vision's metrics/photometry/visual_acuity)
-- no physics logic here, only orchestration + a progress callback for Streamlit.

Plotting functions are PARAMETRIZED (metric/axis/group chosen at call time) so the same
functions render either a freshly-run sweep or any of stage3_integrated's precomputed
CSVs -- unlike stage3_integrated/generate_plots.py's fixed, one-plot-per-function
originals, which this module deliberately does not duplicate the fixed versions of.
"""

import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_compute as lc

_STAGE3HV_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage3_human_vision"))
if _STAGE3HV_DIR not in sys.path:
    sys.path.insert(0, _STAGE3HV_DIR)
import pareto  # noqa: E402

CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7", "#e87ba4", "#008300"]

# Human-readable labels for every metric this project computes, keyed the same way in
# both a freshly-run sweep (live_compute output) and stage3_integrated's precomputed
# CSVs -- one registry, used by both data paths.
METRIC_LABELS = {
    "r_EE_50_um": "r_EE(50%) blur radius (µm)",
    "r_EE_70_um": "r_EE(70%) blur radius (µm)",
    "r_EE_80_um": "r_EE(80%) blur radius (µm)",
    "r_EE_90_um": "r_EE(90%) blur radius (µm)",
    "rms_spot_radius_um": "RMS spot radius (µm)",
    "strehl_ratio": "Strehl ratio (ill-posed in this regime -- see README)",
    "mtf50_cpd": "MTF50 (cycles/degree)",
    "mtf10_cpd": "MTF10 (cycles/degree)",
    "airy_diameter_um": "Airy diameter (µm)",
    "f_number": "F-number",
    "throughput_area_ratio": "Throughput (fraction of natural pupil area)",
    "relative_retinal_illuminance": "Relative retinal illuminance",
    "retinal_illuminance_troland": "Retinal illuminance (Trolands)",
    "photon_flux_density_per_s_per_m2": "Photon flux density (/s/m^2)",
    "snellen_denom_mtf50": "Predicted Snellen denominator (MTF50 cutoff)",
    "snellen_denom_mtf10": "Predicted Snellen denominator (MTF10 cutoff)",
    "rose_devries_snellen_denom": "Predicted Snellen denominator (Rose-DeVries SNR bound)",
    "visual_strehl_photopic": "Visual Strehl, VSOTF (photopic CSF)",
    "visual_strehl_mannos_sakrison": "Visual Strehl, VSOTF (Mannos-Sakrison CSF)",
}

DEFAULT_APERTURES_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]


def run_custom_sweep(apertures_um, M_values, wavelength_nm, d_gap_mm, D_pupil_um,
                      grid_N=512, progress_callback=None):
    """
    Live sweep: computes every (aperture, M) point via live_compute.compute_point().
    progress_callback(done, total, elapsed_s) is called after every point, if given
    (wired to a Streamlit progress bar by the caller).
    """
    rows = []
    total = len(apertures_um) * len(M_values)
    done = 0
    t0 = time.time()

    for a_um in apertures_um:
        for M in M_values:
            # compute_point recomputes its own M=0 diffraction-limited reference
            # internally per call (it's a self-contained single-point API, not
            # threaded through here) -- acceptable since grid_N=512 makes even the
            # uncached path fast enough (~0.1-0.5s/point) for interactive sweep sizes
            # (a few hundred points).
            row = lc.compute_point(a_um, wavelength_nm, M, d_gap_mm, D_pupil_um, grid_N=grid_N)
            row.pop("I_retina", None)
            row.pop("mtf_freq_cpd", None)
            row.pop("mtf_values", None)
            rows.append(row)
            done += 1
            if progress_callback:
                progress_callback(done, total, time.time() - t0)

    return pd.DataFrame(rows)


def plot_metric_vs_aperture_grouped(df, metric_col, group_col="M_diopters", group_label="M"):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    groups = sorted(df[group_col].dropna().unique())
    for i, g in enumerate(groups):
        sub = df[np.isclose(df[group_col], g)].sort_values("a_hole_um")
        if sub[metric_col].isna().all():
            continue
        ax.plot(sub["a_hole_um"], sub[metric_col], "o-", color=CATEGORICAL[i % 7],
                label=f"{group_label}={g:g}", markersize=4)
    ax.set_xlabel("aperture diameter (µm)")
    ax.set_ylabel(METRIC_LABELS.get(metric_col, metric_col))
    ax.set_title(f"{METRIC_LABELS.get(metric_col, metric_col)} vs aperture")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def plot_heatmap(df, metric_col, x_col="a_hole_um", y_col="M_diopters"):
    pivot = df.pivot_table(index=y_col, columns=x_col, values=metric_col)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    im = ax.imshow(pivot.values, aspect="auto", origin="lower", cmap="viridis",
                   extent=[pivot.columns.min(), pivot.columns.max(), pivot.index.min(), pivot.index.max()])
    ax.set_xlabel(x_col); ax.set_ylabel(y_col)
    ax.set_title(f"{METRIC_LABELS.get(metric_col, metric_col)} heatmap")
    fig.colorbar(im, ax=ax, label=METRIC_LABELS.get(metric_col, metric_col))
    fig.tight_layout()
    return fig


def plot_pareto_front_ui(df, blur_col, illum_col, group_val, group_col="M_diopters"):
    sub = df[np.isclose(df[group_col], group_val)].copy() if group_col in df.columns else df.copy()
    sub = pareto.build_default_pareto(sub, blur_col=blur_col, illumination_col=illum_col)
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    dominated = sub[~sub["pareto_optimal"]]
    front = sub[sub["pareto_optimal"]].sort_values(blur_col)
    ax.scatter(dominated[blur_col], dominated[illum_col], color="lightgray", label="dominated")
    ax.plot(front[blur_col], front[illum_col], "o-", color=CATEGORICAL[3], label="Pareto front")
    for _, row in front.iterrows():
        ax.annotate(f"{row['a_hole_um']:.0f}um", (row[blur_col], row[illum_col]),
                    fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel(f"{METRIC_LABELS.get(blur_col, blur_col)} (minimize)")
    ax.set_ylabel(f"{METRIC_LABELS.get(illum_col, illum_col)} (maximize)")
    ax.set_title(f"Pareto front ({group_col}={group_val:g})")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig
