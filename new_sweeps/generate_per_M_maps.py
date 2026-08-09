"""
For EACH individual myopia level M, a two-panel figure mapping where the blur-minimum
(r_EE 50%) and acuity-minimum (predicted logMAR) apertures actually sit on their own
full curves -- not just the cross-M summary (Figure 4 in Fresh_Sweep_Analysis.pdf).
Reads ONLY the already-computed new_sweeps/blur_sweep.csv and
new_sweeps/acuity_sweep_stage4.csv -- no new sweep run.

Color: blur and acuity are two distinct series (identity, not magnitude) on the same
axes here, so this uses the documented CATEGORICAL slots (1=blue, 2=orange) -- the
same convention already used for the blur-optimal vs. acuity-optimal comparison
(Figure 4) in the earlier report, kept consistent within this folder.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
CATEGORICAL_1 = "#2a78d6"   # blue -- blur
CATEGORICAL_2 = "#eb6834"   # orange -- acuity

plt.rcParams.update({
    "font.family": "sans-serif", "axes.edgecolor": BASELINE, "axes.labelcolor": INK_PRIMARY,
    "text.color": INK_PRIMARY, "xtick.color": INK_SECONDARY, "ytick.color": INK_SECONDARY,
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.grid": True, "axes.axisbelow": True,
    "font.size": 10.5,
})


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.grid(True, which="major", linewidth=0.8, color=GRID)


def plot_one_M(M, blur, acuity):
    b = blur[blur.M_diopters == M].sort_values("a_hole_um")
    a = acuity[acuity.M_diopters == M].sort_values("a_hole_um")

    b_idx = b.r_EE_50_um.idxmin()
    b_opt_a, b_opt_y = b.loc[b_idx, "a_hole_um"], b.loc[b_idx, "r_EE_50_um"]
    a_idx = a.logmar.idxmin()
    a_opt_a, a_opt_y = a.loc[a_idx, "a_hole_um"], a.loc[a_idx, "logmar"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.4, 6.4), dpi=200, sharex=True)

    ax1.plot(b.a_hole_um, b.r_EE_50_um, color=CATEGORICAL_1, linewidth=1.8, marker="o", markersize=3.5)
    ax1.plot(b_opt_a, b_opt_y, marker="*", markersize=18, color=CATEGORICAL_1,
             markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=5)
    ax1.annotate(f"blur-optimal: {b_opt_a:g}μm\n$r_{{EE}}$(50%)={b_opt_y:.2f}μm",
                 xy=(b_opt_a, b_opt_y), xytext=(10, 12), textcoords="offset points",
                 fontsize=8.3, color=CATEGORICAL_1, ha="left")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_ylabel("$r_{EE}$(50%) at retina (μm)")
    ax1.set_title(f"M = {M:g} D -- blur-minimum vs. acuity-minimum aperture",
                  fontsize=11.5, color=INK_PRIMARY, loc="left", pad=10)
    style_axes(ax1)

    ax2.plot(a.a_hole_um, a.logmar, color=CATEGORICAL_2, linewidth=1.8, marker="o", markersize=3.5)
    ax2.plot(a_opt_a, a_opt_y, marker="*", markersize=18, color=CATEGORICAL_2,
             markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=5)
    ax2.annotate(f"acuity-optimal: {a_opt_a:g}μm\nlogMAR={a_opt_y:.3f}",
                 xy=(a_opt_a, a_opt_y), xytext=(10, 12), textcoords="offset points",
                 fontsize=8.3, color=CATEGORICAL_2, ha="left")
    ax2.set_xscale("log")
    ax2.set_xlabel("Pinhole aperture, $a_{hole}$ (μm)")
    ax2.set_ylabel("Predicted logMAR")
    style_axes(ax2)

    # A shared vertical guide at each optimum, drawn on both panels, makes the "map"
    # between the two optima visually explicit even when they coincide or sit close.
    for ax in (ax1, ax2):
        ax.axvline(b_opt_a, color=CATEGORICAL_1, linewidth=0.8, linestyle="--", alpha=0.35, zorder=0)
        ax.axvline(a_opt_a, color=CATEGORICAL_2, linewidth=0.8, linestyle="--", alpha=0.35, zorder=0)

    fig.tight_layout()
    fname = f"fig_M{M:g}.png"
    fig.savefig(os.path.join(FIG_DIR, fname), bbox_inches="tight")
    plt.close(fig)
    return fname, b_opt_a, b_opt_y, a_opt_a, a_opt_y


def main():
    blur = pd.read_csv(os.path.join(HERE, "blur_sweep.csv"))
    acuity = pd.read_csv(os.path.join(HERE, "acuity_sweep_stage4.csv"))
    m_values = sorted(blur.M_diopters.unique())

    rows = []
    for M in m_values:
        fname, b_a, b_y, a_a, a_y = plot_one_M(M, blur, acuity)
        gap_pct = (a_a - b_a) / b_a * 100 if b_a else float("nan")
        rows.append({"M_diopters": M, "figure": fname,
                     "blur_optimal_um": b_a, "r_EE_50_at_blur_opt_um": round(b_y, 2),
                     "acuity_optimal_um": a_a, "logmar_at_acuity_opt": round(a_y, 3),
                     "aperture_gap_pct": round(gap_pct, 1)})
        print(f"M={M:g}D: blur-opt={b_a:g}um, acuity-opt={a_a:g}um, gap={gap_pct:.1f}%")

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(HERE, "per_M_optimum_map.csv"), index=False)
    print(f"\nWrote {len(out)} rows to per_M_optimum_map.csv and {len(out)} figures to figures/")


if __name__ == "__main__":
    main()
