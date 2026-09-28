"""
ExperimentalComparison/ExP1_clarity_analysis/logmar_illuminated_tasks/build_charts.py

Heatmaps, graphs, and tables for the user-supplied "Logmar_Illuminated_tasks"
BRISQUE dataset (uploaded 2026-09-14; source preserved verbatim as
source_Logmar_Illuminated_tasks.xlsx in this folder).

IMPORTANT, stated explicitly: these BRISQUE values are NOT the same as this
project's own earlier run_brisque.py output (ExP1_clarity_analysis/
brisque_scores.csv, generated 2026-09-09-10) -- per-file scores differ
substantially between the two (e.g. 0D400.dng: 52.04 here vs. 68.41 in the
earlier run). This script treats the uploaded file as its own independent
source of truth, exactly as given, and does not attempt to reconcile,
merge, or silently prefer one over the other.

Reads ONLY source_Logmar_Illuminated_tasks.xlsx. Writes into figures/ and
this folder (new files only).

Run: python3 build_charts.py
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_XLSX = os.path.join(HERE, "source_Logmar_Illuminated_tasks.xlsx")
FIG_DIR = os.path.join(HERE, "figures")
OUT_PDF = os.path.join(HERE, "Logmar_Illuminated_Tasks_BRISQUE_Report.pdf")

APERTURES = [400, 500, 700, 1000, 1200, 1400]
CONTROL_LABEL = "M1-8 no pinhole"
M_ORDER = [0, 1, 2, 3, 4, 6, 8]  # M=5D excluded: only one aperture (500um) has a data point at M=5D
EXCLUDE_CONTROL = True  # per explicit request: no-pinhole control removed from this version

COLOR_ACCENT = "#6B4C9A"
INK = "#222222"
MUTED = "#666666"


def load_df():
    df = pd.read_excel(SRC_XLSX, sheet_name="brisque_scores")
    df["M"] = df["Myopia"].str.replace("d", "", regex=False).astype(int)
    df["Folder_label"] = df["Folder"].apply(lambda v: str(int(v)) if isinstance(v, (int, float)) else str(v))
    n_before = len(df)
    df = df[df.Folder_label != CONTROL_LABEL]                 # no-pinhole control removed, per request
    df = df[df.M != 5]                                         # M=5D removed, per request (sparse: only 500um had a point)
    print(f"filtered {n_before} -> {len(df)} rows (dropped control rows and M=5D row)")
    return df


def savefig(fig, name):
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"wrote {path}")


def build_heatmap(df, value_col, title, cmap, fname, fmt="{:.1f}", pdf=None):
    cols = [str(a) for a in APERTURES]
    grid = np.full((len(M_ORDER), len(cols)), np.nan)
    for i, m in enumerate(M_ORDER):
        for j, col in enumerate(cols):
            match = df[(df.M == m) & (df.Folder_label == col)]
            if len(match) > 0:
                grid[i, j] = match.iloc[0][value_col]

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(grid, aspect="auto", cmap=cmap, origin="upper")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([f"{c}µm" for c in cols], rotation=0, fontsize=9)
    ax.set_yticks(range(len(M_ORDER)))
    ax.set_yticklabels([f"M={m}D" for m in M_ORDER])
    ax.set_title(title, fontsize=13, fontweight="bold")
    for i in range(len(M_ORDER)):
        for j in range(len(cols)):
            v = grid[i, j]
            if not np.isnan(v):
                # pick text color from the ACTUAL rendered cell color's perceptual
                # luminance (not a percentile guess) -- correct for any colormap,
                # including magma_r where high values are dark, unlike magma
                r, g, b, _ = im.cmap(im.norm(v))
                luminance = 0.299 * r + 0.587 * g + 0.114 * b
                text_color = "white" if luminance < 0.5 else INK
                ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=9, color=text_color)
            else:
                ax.text(j, i, "n/a", ha="center", va="center", fontsize=8, color="#aaaaaa", style="italic")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(title.split("--")[0].strip(), fontsize=9)
    plt.tight_layout()
    savefig(fig, fname)
    if pdf is not None:
        pdf.savefig(fig)
    plt.close(fig)
    return grid, cols


def build_line_graph(df, pdf=None):
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = plt.cm.viridis(np.linspace(0.05, 0.9, len(APERTURES)))
    for a, c in zip(APERTURES, colors):
        sub = df[df.Folder_label == str(a)].sort_values("M")
        ax.plot(sub.M, sub["BRISQUE score"], "o-", color=c, linewidth=2, markersize=6, label=f"{a}µm")
    ax.set_xlabel("Myopic power M (D)")
    ax.set_ylabel("BRISQUE score (lower = better perceptual quality)")
    ax.set_title("BRISQUE score vs. myopic power, per aperture", fontsize=13, fontweight="bold")
    ax.grid(axis="y", color="#eaeaea", linewidth=0.7)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=9, ncol=2)
    plt.tight_layout()
    savefig(fig, "line_brisque_vs_M_per_aperture.png")
    if pdf is not None:
        pdf.savefig(fig)
    plt.close(fig)


def build_summary_bar(df, pdf=None):
    labels = [str(a) for a in APERTURES]
    means = [df[df.Folder_label == l]["BRISQUE score"].mean() for l in labels]
    mean_ranks = [df[df.Folder_label == l]["Rank"].mean() for l in labels]
    disp_labels = [f"{l}µm" for l in labels]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    colors = list(plt.cm.viridis(np.linspace(0.05, 0.9, len(APERTURES))))

    ax1 = axes[0]
    bars = ax1.bar(disp_labels, means, color=colors)
    for b, v in zip(bars, means):
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, f"{v:.1f}", ha="center", fontsize=8.5)
    ax1.set_ylabel("mean BRISQUE score (all M combined)")
    ax1.set_title("Mean BRISQUE score per aperture", fontsize=11.5, fontweight="bold")
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    ax2 = axes[1]
    bars2 = ax2.bar(disp_labels, mean_ranks, color=colors)
    for b, v in zip(bars2, mean_ranks):
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05, f"{v:.2f}", ha="center", fontsize=8.5)
    ax2.set_ylabel("mean within-M rank (1 = best)")
    ax2.set_title("Mean rank per aperture", fontsize=11.5, fontweight="bold")
    ax2.invert_yaxis()
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    savefig(fig, "summary_mean_score_and_rank.png")
    if pdf is not None:
        pdf.savefig(fig)
    plt.close(fig)


def render_table_page(pdf, df):
    fig, ax = plt.subplots(figsize=(8.5, 11))
    ax.axis("off")
    ax.text(0.5, 0.98, "Full BRISQUE Data Table -- Logmar Illuminated Tasks", ha="center", fontsize=13,
             fontweight="bold", transform=ax.transAxes)
    df_disp = df[["Myopia", "Folder_label", "Filename", "BRISQUE score", "Rank"]].copy()
    df_disp.columns = ["M", "Aperture/Folder", "Filename", "BRISQUE", "Rank"]
    df_disp["Rank"] = df_disp["Rank"].apply(lambda v: f"{int(v)}" if pd.notna(v) else "")
    n = len(df_disp)
    half = (n + 1) // 2
    for col_idx, chunk in enumerate([df_disp.iloc[:half], df_disp.iloc[half:]]):
        cell_text = chunk.values.tolist()
        tbl = ax.table(cellText=cell_text, colLabels=df_disp.columns, cellLoc="center",
                       bbox=[0.02 + col_idx * 0.5, 0.0, 0.46, 0.94])
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(6.3)
    pdf.savefig(fig)
    plt.close(fig)
    print("wrote table page(s) to combined PDF")


def main():
    df = load_df()

    with PdfPages(OUT_PDF) as pdf:
        # title page
        fig = plt.figure(figsize=(8.5, 11))
        ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
        ax.text(0.5, 0.6, "Logmar Illuminated Tasks", fontsize=22, ha="center", fontweight="bold")
        ax.text(0.5, 0.55, "BRISQUE No-Reference Image Quality -- Heatmaps, Graphs, Tables", fontsize=13,
                 ha="center", color=COLOR_ACCENT)
        ax.text(0.5, 0.45,
                "Source: user-supplied Logmar_Illuminated_tasks.xlsx (uploaded 2026-09-14).\n"
                "NOTE: these BRISQUE values differ from this project's own earlier\n"
                "run_brisque.py output on the same ExP1 folders (generated 2026-09-09/10) --\n"
                "treated here as an independent source, not reconciled or merged.\n\n"
                "Per request: the no-pinhole control series and the M=5D row (only the\n"
                "500um aperture had a data point at M=5D) are EXCLUDED from this version.\n"
                "Rank values shown are exactly as given in the source file -- originally\n"
                "computed across all 7 entries per M (6 apertures + control); with the\n"
                "control row now removed from view, the visible ranks for the 6 remaining\n"
                "apertures may not form a clean 1-6 sequence (a gap marks the control's\n"
                "original rank slot) -- not renumbered/recomputed, shown as-is.",
                fontsize=9, ha="center", va="top", color=MUTED, linespacing=1.7)
        pdf.savefig(fig); plt.close(fig)

        build_heatmap(df, "BRISQUE score", "BRISQUE score -- aperture x myopic power (lower = better)",
                     "magma", "heatmap_brisque_score.png", fmt="{:.1f}", pdf=pdf)
        build_heatmap(df, "Rank", "Within-M rank -- aperture x myopic power (1 = best that row)",
                     "magma_r", "heatmap_rank.png", fmt="{:.0f}", pdf=pdf)
        build_line_graph(df, pdf=pdf)
        build_summary_bar(df, pdf=pdf)
        render_table_page(pdf, df)

    print(f"\nwrote {OUT_PDF}")


if __name__ == "__main__":
    main()
