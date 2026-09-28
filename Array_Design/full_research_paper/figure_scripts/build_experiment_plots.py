"""
build_experiment_plots.py -- real plots generated directly from the exact CSVs
Section 4 (single-aperture experiments) already cites in its tables, so the
plot and the table are guaranteed to agree (same source file, same mtime).

Run: python3 build_experiment_plots.py
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FIGURES_DIR = os.path.join(os.path.dirname(HERE), "figures")

BRISQUE_CSV = os.path.join(REPO, "ExperimentalComparison", "ExP1_clarity_analysis",
                           "measurements", "brisque_scores.csv")
FROSTED_CSV = os.path.join(REPO, "ExperimentalComparison", "ExP3_frosted_screen",
                           "measurements", "all_spot_measurements.csv")

ORDER = ["M1-8 no pinhole", "700", "1000", "1200", "500", "400", "1400"]
LABELS = {"M1-8 no pinhole": "no-pinhole\ncontrol"}


def build_brisque():
    df = pd.read_csv(BRISQUE_CSV)
    means = df.groupby("folder")["brisque_score"].mean()
    order = [c for c in ORDER if c in means.index] + [c for c in means.index if c not in ORDER]
    vals = [means[c] for c in order]
    labels = [LABELS.get(c, f"{c}um") for c in order]
    colors = ["#B23A48" if c == "M1-8 no pinhole" else "#2C6E9E" for c in order]

    fig, ax = plt.subplots(figsize=(9, 5.2))
    bars = ax.bar(labels, vals, color=colors)
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:.1f}", (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=9)
    ax.set_ylabel("mean BRISQUE score (lower = more natural)")
    ax.set_title("ExP1 scenery BRISQUE scores by condition", fontsize=12, fontweight="bold")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.5, 0.01, "Source: ExperimentalComparison/ExP1_clarity_analysis/measurements/brisque_scores.csv",
             ha="center", fontsize=8, color="#555")
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out = os.path.join(FIGURES_DIR, "brisque_scenery_scores.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}")


def build_frosted():
    df = pd.read_csv(FROSTED_CSV)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    apertures = sorted(df[df.series == "aperture"].aperture_um.unique())
    colors = plt.cm.viridis(np.linspace(0.1, 0.85, len(apertures)))
    for a, c in zip(apertures, colors):
        sub = df[(df.series == "aperture") & (df.aperture_um == a)].sort_values("displacement_mm")
        ax.plot(sub.displacement_mm, sub.radius_px, "o-", color=c, label=f"{int(a)}um")
    ctrl = df[df.series != "aperture"].sort_values("displacement_mm")
    if len(ctrl):
        ax.plot(ctrl.displacement_mm, ctrl.radius_px, "s--", color="#B23A48", linewidth=2,
                label="no-pinhole control")
    ax.set_xlabel("screen displacement (mm)")
    ax.set_ylabel("measured spot radius (px)")
    ax.set_title("ExP3 frosted-screen defocus sweep: spot radius vs. displacement",
                 fontsize=12, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.5, 0.01, "Source: ExperimentalComparison/ExP3_frosted_screen/measurements/all_spot_measurements.csv",
             ha="center", fontsize=8, color="#555")
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out = os.path.join(FIGURES_DIR, "frosted_screen_growth_curves.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    build_brisque()
    build_frosted()
