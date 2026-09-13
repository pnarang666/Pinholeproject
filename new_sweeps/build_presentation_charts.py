"""
new_sweeps/build_presentation_charts.py

Full set of individual PNG charts for IYPT presentation use, built entirely
from fresh, corrected data:
  blur_sweep.csv          -- ASM, grid_N=4096, correct since 2026-08-16
  acuity_sweep_stage4.csv -- corrected 2026-09-12 (grid_N=4096 fix)
  per_M_optimum_map.csv   -- regenerated 2026-09-12 from the two files above

Does NOT depend on table1_optimum_summary.csv (no live generator exists for
that file -- it was a one-off historical artifact, now archived; every number
that file used to hold is recomputed here directly from blur_sweep.csv).

Every chart is written as its own standalone PNG (not one combined PDF), per
explicit instruction. Output: new_sweeps/figures/corrected_model_results/.

Run: python3 build_presentation_charts.py
"""
import os
import csv
import shutil

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
BLUR_CSV = os.path.join(HERE, "blur_sweep.csv")
ACUITY_CSV = os.path.join(HERE, "acuity_sweep_stage4.csv")
OPTMAP_CSV = os.path.join(HERE, "per_M_optimum_map.csv")
OUT_DIR = os.path.join(HERE, "figures", "corrected_model_results")
os.makedirs(OUT_DIR, exist_ok=True)

M_ORDER = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
PERCENTILES = [50, 70, 80, 90]
PCT_COLORS = {50: "#AFCBE3", 70: "#6BA3D1", 80: "#2C6E9E", 90: "#123A5C"}
M_COLORS = dict(zip(M_ORDER, plt.cm.viridis(np.linspace(0, 0.9, len(M_ORDER)))))
COLOR_BLUR = "#2C6E9E"
COLOR_ACUITY = "#E07B39"
INK = "#222222"


def savefig(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def load_blur():
    df = pd.read_csv(BLUR_CSV)
    return df[df.junction_ok == True]


def load_acuity():
    df = pd.read_csv(ACUITY_CSV)
    return df[df.junction_ok == True]


# ---------------------------------------------------------- A: per-M curves --

def build_per_M_curves(blur):
    for M in M_ORDER:
        sub = blur[blur.M_diopters == M].sort_values("a_hole_um")
        fig, ax = plt.subplots(figsize=(7, 5.5))
        for p in PERCENTILES:
            ax.plot(sub.a_hole_um, sub[f"r_EE_{p}_um"], "o-", color=PCT_COLORS[p],
                     markersize=4, linewidth=1.8, label=f"r$_{{EE}}$({p}%)")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("aperture (µm)"); ax.set_ylabel("blur radius (µm)")
        ax.set_title(f"Corrected ASM: blur vs. aperture, M={M:g}D", fontweight="bold")
        ax.grid(True, which="both", color="#eaeaea", linewidth=0.6)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.legend(frameon=False, fontsize=9)
        savefig(fig, f"01_blur_vs_aperture_M{M:g}.png")


# ---------------------------------------------- B/C: optimum vs M, per pct --

def build_optimum_vs_M(blur):
    rows = []
    for M in M_ORDER:
        sub = blur[blur.M_diopters == M]
        row = {"M": M}
        for p in PERCENTILES:
            idx = sub[f"r_EE_{p}_um"].idxmin()
            row[f"opt_aperture_r{p}"] = sub.loc[idx, "a_hole_um"]
            row[f"r{p}_at_opt"] = sub.loc[idx, f"r_EE_{p}_um"]
        rows.append(row)
    opt = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(8, 6))
    for p in PERCENTILES:
        ax.plot(opt.M, opt[f"opt_aperture_r{p}"], "o-", color=PCT_COLORS[p],
                 linewidth=2, markersize=6, label=f"optimum for r$_{{EE}}$({p}%)")
    ax.set_xlabel("Myopic power M (D)"); ax.set_ylabel("Optimum aperture (µm)")
    ax.set_title("Corrected ASM: optimum aperture vs. M, by percentile", fontweight="bold")
    ax.grid(axis="y", color="#eaeaea", linewidth=0.7)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(frameon=False)
    savefig(fig, "02_optimum_aperture_vs_M.png")

    fig, ax = plt.subplots(figsize=(8, 6))
    for p in PERCENTILES:
        ax.plot(opt.M, opt[f"r{p}_at_opt"], "s--", color=PCT_COLORS[p],
                 linewidth=2, markersize=6, label=f"r$_{{EE}}$({p}%) at its own optimum")
    ax.set_xlabel("Myopic power M (D)"); ax.set_ylabel("Blur radius at optimum (µm)")
    ax.set_title("Corrected ASM: best-achievable blur radius vs. M", fontweight="bold")
    ax.grid(axis="y", color="#eaeaea", linewidth=0.7)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(frameon=False)
    savefig(fig, "03_best_blur_radius_vs_M.png")
    return opt


# ------------------------------------------------- D: multi-M overlay charts --

def build_multi_M_overlay(blur):
    for p in PERCENTILES:
        fig, ax = plt.subplots(figsize=(8, 6))
        for M in M_ORDER:
            sub = blur[blur.M_diopters == M].sort_values("a_hole_um")
            ax.plot(sub.a_hole_um, sub[f"r_EE_{p}_um"], "o-", color=M_COLORS[M],
                     markersize=4, linewidth=1.8, label=f"M={M:g}D")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("aperture (µm)"); ax.set_ylabel(f"r$_{{EE}}$({p}%) (µm)")
        ax.set_title(f"Corrected ASM: r$_{{EE}}$({p}%) vs. aperture, all M overlaid", fontweight="bold")
        ax.grid(True, which="both", color="#eaeaea", linewidth=0.6)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.legend(frameon=False, fontsize=8, ncol=2)
        savefig(fig, f"04_multiM_overlay_r_EE_{p}.png")


# --------------------------------------------------------------- E: heatmaps --

def build_heatmaps(blur):
    apertures = sorted(blur.a_hole_um.unique())
    metrics = [("r_EE_50_um", "r_EE(50%)"), ("r_EE_70_um", "r_EE(70%)"),
               ("r_EE_80_um", "r_EE(80%)"), ("r_EE_90_um", "r_EE(90%)"),
               ("rms_radius_um", "RMS radius")]

    grids = {}
    for col, label in metrics:
        grid = np.full((len(M_ORDER), len(apertures)), np.nan)
        for i, M in enumerate(M_ORDER):
            sub = blur[blur.M_diopters == M].set_index("a_hole_um")
            for j, a in enumerate(apertures):
                if a in sub.index:
                    grid[i, j] = sub.loc[a, col]
        grids[col] = grid

        fig, ax = plt.subplots(figsize=(9, 5))
        im = ax.imshow(np.log10(grid), aspect="auto", cmap="magma", origin="lower")
        ax.set_xticks(range(len(apertures))); ax.set_xticklabels([f"{int(a)}" for a in apertures], rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(M_ORDER))); ax.set_yticklabels([f"{m:g}" for m in M_ORDER])
        ax.set_xlabel("aperture (µm)"); ax.set_ylabel("M (D)")
        ax.set_title(f"Corrected ASM: {label} (µm), log$_{{10}}$ scale", fontweight="bold")
        cbar = fig.colorbar(im, ax=ax); cbar.set_label(f"log$_{{10}}$({label} / µm)")
        savefig(fig, f"05_heatmap_{col}.png")

    fig, axes = plt.subplots(1, 5, figsize=(22, 4.2))
    for ax, (col, label) in zip(axes, metrics):
        im = ax.imshow(np.log10(grids[col]), aspect="auto", cmap="magma", origin="lower")
        ax.set_xticks(range(len(apertures))); ax.set_xticklabels([f"{int(a)}" for a in apertures], rotation=90, fontsize=6)
        ax.set_yticks(range(len(M_ORDER))); ax.set_yticklabels([f"{m:g}" for m in M_ORDER], fontsize=8)
        ax.set_title(label, fontsize=10)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Corrected ASM: all blur metrics side-by-side (log$_{10}$ µm)", fontweight="bold", y=1.05)
    savefig(fig, "05_heatmap_ALL_METRICS_comparison.png")


# --------------------------------------------------- F: optical quality/acuity --

def build_acuity_metric_graphs(acuity):
    metrics = [("mar_arcmin", "MAR (arcmin)", True),
               ("logmar", "logMAR", False),
               ("snellen_denominator", "Snellen denominator (20/X)", True),
               ("vsotf", "Visual Strehl OTF (VSOTF)", False),
               ("retinal_illuminance_td", "Retinal illuminance (Td)", False)]
    for col, label, logy in metrics:
        fig, ax = plt.subplots(figsize=(8, 6))
        for M in M_ORDER:
            sub = acuity[acuity.M_diopters == M].sort_values("a_hole_um")
            if col not in sub.columns or sub[col].isna().all():
                continue
            ax.plot(sub.a_hole_um, sub[col], "o-", color=M_COLORS[M], markersize=4,
                     linewidth=1.8, label=f"M={M:g}D")
        ax.set_xscale("log")
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel("aperture (µm)"); ax.set_ylabel(label)
        ax.set_title(f"Corrected model: {label} vs. aperture, all M", fontweight="bold")
        ax.grid(True, which="both", color="#eaeaea", linewidth=0.6)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.legend(frameon=False, fontsize=8, ncol=2)
        savefig(fig, f"06_acuity_{col}_vs_aperture.png")


# -------------------------------------------------- G/H: blur vs logMAR optima --

def build_logmar_optimum_charts(optmap):
    Ms = optmap.M_diopters.values
    blur_opt = optmap.blur_optimal_um.values
    acuity_opt = optmap.acuity_optimal_um.values
    gap = optmap.aperture_gap_pct.values
    logmar = optmap.logmar_at_acuity_opt.values

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(Ms, blur_opt, "o-", color=COLOR_BLUR, linewidth=2, markersize=7, label="blur-minimum optimum (r$_{EE}$50%)")
    ax.plot(Ms, acuity_opt, "s--", color=COLOR_ACUITY, linewidth=2, markersize=7, label="logMAR-acuity-minimum optimum")
    ax.set_xlabel("Myopic power M (D)"); ax.set_ylabel("Optimal aperture (µm)")
    ax.set_title("Blur-optimal vs. acuity(logMAR)-optimal aperture", fontweight="bold")
    ax.grid(axis="y", color="#eaeaea", linewidth=0.7)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    savefig(fig, "07_blur_vs_logmar_optimum_aperture.png")

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar([str(int(m)) for m in Ms], gap, color=COLOR_ACUITY, width=0.55)
    for b, g in zip(bars, gap):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f"{g:.0f}%", ha="center", fontsize=8)
    ax.set_xlabel("Myopic power M (D)"); ax.set_ylabel("Aperture gap (%)")
    ax.set_title("Divergence between blur-optimal and acuity-optimal aperture", fontweight="bold")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    savefig(fig, "08_optimum_aperture_gap_pct.png")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(Ms, logmar, "o-", color=COLOR_ACUITY, linewidth=2, markersize=7)
    ax.axhline(0.0, color="#999999", linewidth=1, linestyle=":")
    ax.text(Ms[-1], 0.02, "logMAR=0 (20/20)", fontsize=8, color="#666666", ha="right")
    ax.set_xlabel("Myopic power M (D)"); ax.set_ylabel("Predicted logMAR at acuity-optimal aperture")
    ax.set_title("Best achievable logMAR acuity vs. M (corrected model)", fontweight="bold")
    ax.grid(axis="y", color="#eaeaea", linewidth=0.7)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    savefig(fig, "09_best_logmar_vs_M.png")


# ------------------------------------------------------ I: per-M comparison --

def copy_per_M_comparison_charts():
    for M in [0, 1, 2, 3, 4, 5, 6, 8]:
        src = os.path.join(HERE, "figures", f"fig_M{M}.png")
        if os.path.exists(src):
            dst = os.path.join(OUT_DIR, f"10_per_M_blur_vs_logmar_M{M}.png")
            shutil.copy2(src, dst)
            print(f"copied fresh {src} -> {dst}")
        else:
            print(f"[MISSING] {src} not found -- not copied")


def main():
    blur = load_blur()
    acuity = load_acuity()
    optmap = pd.read_csv(OPTMAP_CSV)

    build_per_M_curves(blur)
    build_optimum_vs_M(blur)
    build_multi_M_overlay(blur)
    build_heatmaps(blur)
    build_acuity_metric_graphs(acuity)
    build_logmar_optimum_charts(optmap)
    copy_per_M_comparison_charts()

    n = len([f for f in os.listdir(OUT_DIR) if f.endswith(".png")])
    print(f"\n{n} PNG charts now in {OUT_DIR}")


if __name__ == "__main__":
    main()
