"""
Generates all figures for the fresh-sweep analysis report, from new_sweeps/blur_sweep.csv,
new_sweeps/acuity_sweep_stage4.csv, and new_sweeps/r7acuity_calibration_attempt.log only
-- no old/previously-computed data.

Color: M (myopia, diopters) is a continuous, ordered magnitude sampled at 8 points, so it
is encoded SEQUENTIALLY (one hue, light->dark, colorbar) rather than as 8 discrete
categorical/ordinal swatches -- the documented palette's blue sequential ramp
(dataviz skill references/palette.md) does not have enough pairwise-distinct discrete
steps for 8 ordinal entries in a legend (validated: adjacent ΔL ~0.047 < the 0.06 ordinal
floor), and per that skill's own color-formula.md, a true sequential/continuous ramp is
checked for lightness monotonicity only, not pairwise CVD separation. The blur-optimal
vs acuity-optimal comparison (Figure 4) IS a genuine 2-series categorical/identity
comparison and uses the documented categorical slots 1 (blue) and 2 (orange).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# -- palette (dataviz skill references/palette.md, documented values only) --
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
CATEGORICAL_1 = "#2a78d6"  # blue -- slot 1
CATEGORICAL_2 = "#eb6834"  # orange -- slot 2

# Sequential blue ramp anchor stops (documented steps 100..700), used as control points
# for a smooth interpolated colormap for the continuous M encoding.
SEQ_BLUE_STOPS = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#184f95", "#0d366b"]
seq_cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE_STOPS, N=256)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_PRIMARY,
    "text.color": INK_PRIMARY,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "axes.facecolor": SURFACE,
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.grid": True,
    "axes.axisbelow": True,
    "font.size": 10.5,
})


def m_color(M, m_min, m_max):
    t = (M - m_min) / (m_max - m_min) if m_max > m_min else 0.5
    return seq_cmap(0.15 + 0.85 * t)  # keep lightest end off pure-white for legibility


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9.5)
    ax.grid(True, which="major", linewidth=0.8, color=GRID)
    ax.set_axisbelow(True)


def add_m_colorbar(fig, ax, m_min, m_max):
    sm = ScalarMappable(cmap=seq_cmap, norm=plt.Normalize(vmin=m_min, vmax=m_max))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.015, fraction=0.06, aspect=22)
    cbar.set_label("Myopia M (D)", color=INK_SECONDARY, fontsize=9.5)
    cbar.ax.tick_params(colors=INK_SECONDARY, labelsize=8.5)
    cbar.outline.set_visible(False)


def plot_metric_vs_aperture(df, ycol, ylabel, title, fname, logy=False, caption=None):
    m_values = sorted(df.M_diopters.unique())
    m_min, m_max = min(m_values), max(m_values)
    fig, ax = plt.subplots(figsize=(6.2, 4.3), dpi=200,
                            gridspec_kw={"bottom": 0.14 if not caption else 0.24})
    for M in m_values:
        g = df[df.M_diopters == M].sort_values("a_hole_um")
        ax.plot(g.a_hole_um, g[ycol], color=m_color(M, m_min, m_max), linewidth=1.8,
                marker="o", markersize=3.2, markeredgewidth=0)
    ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    ax.set_xlabel("Pinhole aperture, $a_{hole}$ ($\\mu$m)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11.5, color=INK_PRIMARY, loc="left", pad=10)
    style_axes(ax)
    add_m_colorbar(fig, ax, m_min, m_max)
    if caption:
        fig.text(0.06, 0.02, caption, fontsize=7.6, color=INK_MUTED, ha="left",
                  va="bottom", wrap=True)
    fig.savefig(os.path.join(FIG_DIR, fname), bbox_inches="tight")
    plt.close(fig)


def plot_optimum_comparison(blur_df, acuity_df):
    rows = []
    for M in sorted(blur_df.M_diopters.unique()):
        gb = blur_df[blur_df.M_diopters == M]
        best_blur = gb.loc[gb.r_EE_50_um.idxmin()]
        ga = acuity_df[acuity_df.M_diopters == M]
        best_acuity = ga.loc[ga.logmar.idxmin()]
        rows.append({"M": M, "blur_opt_um": best_blur.a_hole_um,
                     "acuity_opt_um": best_acuity.a_hole_um})
    comp = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(6.2, 4.0), dpi=200)
    ax.plot(comp.M, comp.blur_opt_um, color=CATEGORICAL_1, linewidth=2.0,
            marker="o", markersize=6, markeredgewidth=1.6, markeredgecolor=SURFACE,
            label="Blur-optimal (min $r_{EE}$ 50%)")
    ax.plot(comp.M, comp.acuity_opt_um, color=CATEGORICAL_2, linewidth=2.0,
            marker="o", markersize=6, markeredgewidth=1.6, markeredgecolor=SURFACE,
            label="Acuity-optimal (min predicted logMAR)")
    ax.set_xlabel("Myopia M (D)")
    ax.set_ylabel("Optimal aperture ($\\mu$m)")
    ax.set_title("Blur-optimal vs. acuity-optimal aperture, by myopia level",
                 fontsize=11.5, color=INK_PRIMARY, loc="left", pad=10)
    style_axes(ax)
    leg = ax.legend(frameon=False, fontsize=9, loc="upper left")
    for text in leg.get_texts():
        text.set_color(INK_SECONDARY)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig4_optimum_comparison.png"), bbox_inches="tight")
    plt.close(fig)
    return comp


def plot_r7_ceiling():
    probe = pd.read_csv(os.path.join(HERE, "..", "R7acuity", "outputs",
                                      "reference_condition_sigma_probe_postfix.csv"))
    fig, ax = plt.subplots(figsize=(6.2, 3.8), dpi=200)
    ax.plot(probe.sigma, probe.min_proportion_correct, color=CATEGORICAL_1, linewidth=2.0,
            marker="o", markersize=6, markeredgewidth=1.6, markeredgecolor=SURFACE)
    ax.axhline(1.0, color=BASELINE, linewidth=0.8, linestyle="-", zorder=0)
    ax.set_xscale("log")
    ax.set_ylim(0.9, 1.02)
    ax.set_xlabel("Noise $\\sigma$ (ideal-observer model units)")
    ax.set_ylabel("Min. proportion correct\n(across 9 tested letter sizes)")
    ax.set_title("R7acuity reference condition: ceiling performance across ~5 decades of noise",
                 fontsize=10.8, color=INK_PRIMARY, loc="left", pad=10)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig5_r7_ceiling.png"), bbox_inches="tight")
    plt.close(fig)


def main():
    blur = pd.read_csv(os.path.join(HERE, "blur_sweep.csv"))
    acuity = pd.read_csv(os.path.join(HERE, "acuity_sweep_stage4.csv"))

    plot_metric_vs_aperture(
        blur, "r_EE_50_um", "$r_{EE}$(50%) at retina ($\\mu$m)",
        "Figure 1 -- Encircled-energy blur radius vs. aperture",
        "fig1_blur_ree50_vs_aperture.png", logy=True,
        caption=("Note: at M=0D, apertures >=700um, r_EE(50%) is pinned near 7.3um -- "
                  "the encircled-energy histogram's own bin-width resolution floor "
                  "(~2.5x the grid spacing), not a genuine plateau in the physics. "
                  "See RMS radius (Fig. 2) in this regime."))
    plot_metric_vs_aperture(
        blur, "r_EE_70_um", "$r_{EE}$(70%) at retina ($\\mu$m)",
        "Figure 1b -- Encircled-energy blur radius (70%) vs. aperture",
        "fig1b_blur_ree70_vs_aperture.png", logy=True)
    plot_metric_vs_aperture(
        blur, "r_EE_80_um", "$r_{EE}$(80%) at retina ($\\mu$m)",
        "Figure 1c -- Encircled-energy blur radius (80%) vs. aperture",
        "fig1c_blur_ree80_vs_aperture.png", logy=True)
    plot_metric_vs_aperture(
        blur, "r_EE_90_um", "$r_{EE}$(90%) at retina ($\\mu$m)",
        "Figure 1d -- Encircled-energy blur radius (90%) vs. aperture",
        "fig1d_blur_ree90_vs_aperture.png", logy=True)
    plot_metric_vs_aperture(
        blur, "rms_radius_um", "RMS spot radius at retina ($\\mu$m)",
        "Figure 2 -- RMS spot radius vs. aperture",
        "fig2_blur_rms_vs_aperture.png", logy=True)
    plot_metric_vs_aperture(
        acuity, "logmar", "Predicted logMAR (Stage 4 recommended model)",
        "Figure 3 -- Predicted visual acuity vs. aperture",
        "fig3_acuity_logmar_vs_aperture.png", logy=False)

    comp = plot_optimum_comparison(blur, acuity)
    plot_r7_ceiling()

    comp.to_csv(os.path.join(HERE, "optimum_comparison.csv"), index=False)
    print("Figures written to", FIG_DIR)
    print(comp.to_string(index=False))


if __name__ == "__main__":
    main()
