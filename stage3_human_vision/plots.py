"""
All Phase 3 plots. Reads metrics_sweep.csv (run_metrics_sweep.py) and, where relevant,
Stage 2's own r1_full_range_sweep.csv (reused, not recomputed).
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import pareto

CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7", "#e87ba4", "#008300"]
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")


def _series_by_M(df, y_col, ax, ylabel=None, title=None):
    Ms = sorted(df["M_diopters"].unique())
    for i, M in enumerate(Ms):
        g = df[np.isclose(df["M_diopters"], M)].sort_values("a_hole_um")
        ax.plot(g["a_hole_um"], g[y_col], "o-", color=CATEGORICAL[i % len(CATEGORICAL)],
                label=f"M={M:.0f}D", markersize=4)
    ax.set_xlabel("aperture diameter (µm)")
    ax.set_ylabel(ylabel or y_col)
    ax.set_title(title or y_col)
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)


def plot_metric_vs_aperture(df, y_col, ylabel, title, out_name):
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    _series_by_M(df, y_col, ax, ylabel=ylabel, title=title)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, out_name), dpi=150)
    plt.close(fig)


def plot_pareto_front(df, blur_col="r_EE_50_um", illum_col="throughput_area_ratio",
                       M_diopters=4.0, out_name="pareto_front.png"):
    g = df[np.isclose(df["M_diopters"], M_diopters)].copy()
    g = pareto.build_default_pareto(g, blur_col=blur_col, illumination_col=illum_col)
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.scatter(g.loc[~g["pareto_optimal"], blur_col], g.loc[~g["pareto_optimal"], illum_col],
               color="lightgray", label="dominated")
    front = g.loc[g["pareto_optimal"]].sort_values(blur_col)
    ax.plot(front[blur_col], front[illum_col], "o-", color=CATEGORICAL[3], label="Pareto front")
    for _, row in front.iterrows():
        ax.annotate(f"{row['a_hole_um']:.0f}um", (row[blur_col], row[illum_col]),
                    fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel(f"{blur_col} (minimize)")
    ax.set_ylabel(f"{illum_col} (maximize)")
    ax.set_title(f"Pareto front: blur vs. throughput (M={M_diopters:.0f}D)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, out_name), dpi=150)
    plt.close(fig)


def plot_optimum_vs_myopia(df, metric_specs, out_name="optimum_vs_myopia_by_metric.png"):
    import validation
    opt_df = validation.phase3_optimum_by_metric(df, metric_specs, group_cols=("M_diopters",))
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for i, label in enumerate(metric_specs):
        col = f"a_hole_optimum_{label}_um"
        ax.plot(opt_df["M_diopters"], opt_df[col], "o-", color=CATEGORICAL[i % len(CATEGORICAL)], label=label)
    lo, hi = 940, 1750
    ax.axhspan(lo, hi, color="gray", alpha=0.12, label="clinical pinhole range")
    ax.set_xlabel("myopia severity M (diopters)")
    ax.set_ylabel("optimal aperture (µm)")
    ax.set_title("Optimal aperture vs. myopia, by candidate metric")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, out_name), dpi=150)
    plt.close(fig)


def plot_wavelength_comparison(df_by_wavelength, y_col, ylabel, M_diopters, out_name):
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for i, (wl, df) in enumerate(df_by_wavelength.items()):
        g = df[np.isclose(df["M_diopters"], M_diopters)].sort_values("a_hole_um")
        ax.plot(g["a_hole_um"], g[y_col], "o-", color=CATEGORICAL[i], label=f"{wl:.0f}nm")
    ax.set_xlabel("aperture diameter (µm)")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel} vs aperture, by wavelength (M={M_diopters:.0f}D)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, out_name), dpi=150)
    plt.close(fig)


def make_all_plots(df):
    os.makedirs(OUT_DIR, exist_ok=True)

    plot_metric_vs_aperture(df, "r_EE_80_um", "r_EE(80%) blur radius (µm)", "Retinal blur (r_EE 80%) vs aperture", "ee80_vs_aperture.png")
    plot_metric_vs_aperture(df, "rms_spot_radius_um", "RMS spot radius (µm)", "RMS spot radius vs aperture", "rms_vs_aperture.png")
    plot_metric_vs_aperture(df, "strehl_ratio", "Strehl ratio", "Strehl ratio vs aperture (see README: ill-posed in this regime)", "strehl_vs_aperture.png")
    plot_metric_vs_aperture(df, "mtf50_cpd", "MTF50 (cycles/degree)", "MTF50 vs aperture", "mtf50_vs_aperture.png")
    plot_metric_vs_aperture(df, "throughput_area_ratio", "throughput (fraction of natural pupil)", "Retinal illumination (throughput) vs aperture", "illumination_vs_aperture.png")

    metric_specs = {
        "min_r_EE_80": ("r_EE_80_um", "min"),
        "min_rms_radius": ("rms_spot_radius_um", "min"),
        "max_strehl": ("strehl_ratio", "max"),
        "max_mtf50": ("mtf50_cpd", "max"),
    }
    plot_optimum_vs_myopia(df, metric_specs)

    for M in [1.0, 4.0, 8.0]:
        plot_pareto_front(df, M_diopters=M, out_name=f"pareto_front_M{int(M)}.png")

    print(f"Wrote plots to {OUT_DIR}")
