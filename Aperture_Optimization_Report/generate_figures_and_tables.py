"""
Generates every figure and LaTeX table this report's chapters reference, from the
CSVs in new_sweeps/ (already-current post-fix full-grid sweeps) and
Aperture_Optimization_Report/data/ (this report's own fresh sweeps). No physics is
computed here -- only plotting and table formatting, following the same
dataviz-skill palette conventions already established in master_dashboard/app.py
(sequential blue colormap for the continuous ordered magnitude M; fixed categorical
blue/orange slots for genuine two-series identity comparisons).
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.cm import ScalarMappable

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REPORT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(REPORT, "data")
NEW_SWEEPS = os.path.join(ROOT, "new_sweeps")
FIG_DIR = os.path.join(REPORT, "figures")
TAB_DIR = os.path.join(REPORT, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

# --- palette (dataviz skill references/palette.md, same as master_dashboard/app.py) ---
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID_COLOR = "#e1e0d9"
BASELINE = "#c3c2b7"
CATEGORICAL_1 = "#2a78d6"
CATEGORICAL_2 = "#eb6834"
SEQ_BLUE_STOPS = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#184f95", "#0d366b"]
SEQ_CMAP = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE_STOPS, N=256)

plt.rcParams.update({
    "font.family": "sans-serif", "axes.edgecolor": BASELINE, "axes.labelcolor": INK_PRIMARY,
    "text.color": INK_PRIMARY, "xtick.color": INK_SECONDARY, "ytick.color": INK_SECONDARY,
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "grid.color": GRID_COLOR, "grid.linewidth": 0.8, "axes.grid": True, "axes.axisbelow": True,
    "font.size": 10,
})


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.grid(True, which="major", linewidth=0.8, color=GRID_COLOR)


def save(fig, name):
    path = os.path.join(FIG_DIR, name)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  figure -> {name}")


def write_table(tex, name):
    path = os.path.join(TAB_DIR, f"{name}.tex")
    with open(path, "w") as f:
        f.write(tex)
    print(f"  table  -> {name}.tex")


def df_to_longtable(df, caption, label, float_fmt="{:.3f}", max_rows=None):
    cols = df.columns.tolist()
    col_spec = "r" * len(cols)
    def _escape(s):
        return s.replace("\\", "").replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")
    header = " & ".join(_escape(c) for c in cols) + r" \\"
    lines = [
        r"{\small",
        r"\begin{longtable}{%s}" % col_spec,
        r"\caption{%s}\label{%s}\\" % (caption, label),
        r"\toprule", header, r"\midrule", r"\endfirsthead",
        r"\multicolumn{%d}{c}{\tablename\ \thetable\ -- continued}\\" % len(cols),
        r"\toprule", header, r"\midrule", r"\endhead",
        r"\bottomrule", r"\endfoot",
    ]
    rows = df if max_rows is None else df.head(max_rows)
    for _, row in rows.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if isinstance(v, (float, np.floating)):
                cells.append(float_fmt.format(v))
            else:
                cells.append(_escape(str(v)))
        lines.append(" & ".join(cells) + r" \\")
    lines.append(r"\end{longtable}")
    lines.append(r"}")
    return "\n".join(lines)


def seq_color(v, vmin, vmax):
    t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
    return SEQ_CMAP(0.15 + 0.85 * t)


def plot_lines_by_M(df, x_col, y_col, ax_labels, M_col="M_diopters"):
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
    vals = sorted(df[M_col].unique())
    vmin, vmax = min(vals), max(vals)
    sm = ScalarMappable(cmap=SEQ_CMAP, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    for v in vals:
        g = df[df[M_col] == v].sort_values(x_col)
        ax.plot(g[x_col], g[y_col], color=seq_color(v, vmin, vmax), linewidth=1.8,
                marker="o", markersize=3.5)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.06)
    cbar.set_label("M (D)", color=INK_SECONDARY, fontsize=9)
    cbar.outline.set_visible(False)
    ax.set_xlabel(ax_labels[0])
    ax.set_ylabel(ax_labels[1])
    style_axes(ax)
    return fig, ax


def plot_heatmap(df, x_col, row_col, val_col, ax_labels):
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
    pivot = df.pivot_table(index=row_col, columns=x_col, values=val_col, aggfunc="mean")
    im = ax.imshow(pivot.values, aspect="auto", cmap=SEQ_CMAP, origin="lower")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{c:g}" for c in pivot.columns], rotation=45, fontsize=8)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{r:g}" for r in pivot.index], fontsize=8)
    ax.set_xlabel(ax_labels[0])
    ax.set_ylabel(ax_labels[1])
    cbar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.06)
    cbar.set_label(ax_labels[2], color=INK_SECONDARY, fontsize=9)
    return fig


print("Loading data...")
blur = pd.read_csv(os.path.join(NEW_SWEEPS, "blur_sweep.csv"))
blur = blur[blur.junction_ok]
acuity = pd.read_csv(os.path.join(NEW_SWEEPS, "acuity_sweep_stage4.csv"))
acuity = acuity[acuity.junction_ok]
stage1 = pd.read_csv(os.path.join(DATA, "stage1_cornea_sweep.csv"))
dep = pd.read_csv(os.path.join(DATA, "stage2_deprecated_sweep.csv"))
dep = dep[dep.junction_ok]
stage3a = pd.read_csv(os.path.join(DATA, "stage3a_brightness_sweep.csv"))
hv = pd.read_csv(os.path.join(DATA, "stage3_human_vision_sweep.csv"))
hv = hv[hv.junction_check_passed] if "junction_check_passed" in hv.columns else hv
mc = pd.read_csv(os.path.join(DATA, "model_comparison_sweep.csv"))
r7 = pd.read_csv(os.path.join(DATA, "r7acuity_closed_form_sweep.csv"))
br = pd.read_csv(os.path.join(DATA, "brightness_reconciliation_sweep.csv"))
si = pd.read_csv(os.path.join(DATA, "singleilluminate_sweep.csv"))
print("All CSVs loaded OK.")

# ======================================================================
# FIGURES
# ======================================================================
print("Generating figures...")

# 1. Stage 1 cornea radii
fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
g = stage1.sort_values("a_hole_um")
ax.plot(g.a_hole_um, g.r_EE_50_um, color=CATEGORICAL_1, marker="o", label=r"$r_{EE}(50\%)$")
ax.plot(g.a_hole_um, g.r_EE_80_um, color=CATEGORICAL_2, marker="s", label=r"$r_{EE}(80\%)$")
ax.plot(g.a_hole_um, g.r_EE_90_um, color="#184f95", marker="^", label=r"$r_{EE}(90\%)$")
ax.plot(g.a_hole_um, g.second_moment_um, color=INK_SECONDARY, marker="d", linestyle="--", label="second moment")
ax.set_xlabel("aperture (um)"); ax.set_ylabel("cornea-plane radius (um)")
leg = ax.legend(frameon=False, fontsize=9)
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_stage1_cornea_radii.png")

# 2/3. R1 sweep lines + heatmap
fig, ax = plot_lines_by_M(blur, "a_hole_um", "r_EE_50_um", ("aperture (um)", "r_EE(50%) (um)"))
save(fig, "fig_r1_lines.png")
fig = plot_heatmap(blur, "a_hole_um", "M_diopters", "r_EE_50_um", ("aperture (um)", "M (D)", "r_EE(50%) (um)"))
save(fig, "fig_r1_heatmap.png")

# 2b/3b. R1 sweep, ALL FOUR percentiles as first-class primary figures (2x2 panels),
# not deferred to a later subsection -- this is the report's headline blur-optimization
# result, shown for every percentile at the same spot as the r_EE(50%)-only figures above.
_pct_cols_r1 = ["r_EE_50_um", "r_EE_70_um", "r_EE_80_um", "r_EE_90_um"]
_pct_titles_r1 = ["r_EE(50%)", "r_EE(70%)", "r_EE(80%)", "r_EE(90%)"]

fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.0), dpi=150)
vals = sorted(blur.M_diopters.unique()); vmin, vmax = min(vals), max(vals)
sm = ScalarMappable(cmap=SEQ_CMAP, norm=plt.Normalize(vmin=vmin, vmax=vmax))
for ax, col, title in zip(axes.ravel(), _pct_cols_r1, _pct_titles_r1):
    for v in vals:
        g = blur[blur.M_diopters == v].sort_values("a_hole_um")
        ax.plot(g.a_hole_um, g[col], color=seq_color(v, vmin, vmax), linewidth=1.5, marker="o", markersize=2.5)
    ax.set_title(title, fontsize=10, color=INK_PRIMARY)
    ax.set_xlabel("aperture (um)", fontsize=9); ax.set_ylabel(f"{title} (um)", fontsize=9)
    style_axes(ax)
sm.set_array([])
fig.subplots_adjust(hspace=0.45, wspace=0.32)
cbar = fig.colorbar(sm, ax=axes, pad=0.03, fraction=0.035)
cbar.set_label("M (D)", color=INK_SECONDARY, fontsize=9)
fig.savefig(os.path.join(FIG_DIR, "fig_r1_lines_all_percentiles.png"), dpi=150)
plt.close(fig)
print("  figure -> fig_r1_lines_all_percentiles.png")

fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.0), dpi=150)
for ax, col, title in zip(axes.ravel(), _pct_cols_r1, _pct_titles_r1):
    pivot = blur.pivot_table(index="M_diopters", columns="a_hole_um", values=col, aggfunc="mean")
    im = ax.imshow(pivot.values, aspect="auto", cmap=SEQ_CMAP, origin="lower")
    ax.set_xticks(range(len(pivot.columns))); ax.set_xticklabels([f"{c:g}" for c in pivot.columns], rotation=60, fontsize=6)
    ax.set_yticks(range(len(pivot.index))); ax.set_yticklabels([f"{r:g}" for r in pivot.index], fontsize=7)
    ax.set_title(title, fontsize=10, color=INK_PRIMARY)
    ax.set_xlabel("aperture (um)", fontsize=8); ax.set_ylabel("M (D)", fontsize=8)
    cbar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.046)
    cbar.ax.tick_params(labelsize=7)
fig.subplots_adjust(hspace=0.65, wspace=0.4)
fig.savefig(os.path.join(FIG_DIR, "fig_r1_heatmap_all_percentiles.png"), dpi=150)
plt.close(fig)
print("  figure -> fig_r1_heatmap_all_percentiles.png")

# 4. Stage3a optimum vs M (with unconstrained comparison)
blur_opt = blur.loc[blur.groupby("M_diopters").r_EE_50_um.idxmin()][["M_diopters", "a_hole_um"]]
fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
ax.plot(stage3a.M_diopters, stage3a.a_star_um, color=CATEGORICAL_1, marker="o", label="brightness-constrained (T_min=6.25%)")
ax.plot(blur_opt.M_diopters, blur_opt.a_hole_um, color=CATEGORICAL_2, marker="s", linestyle="--", label="unconstrained blur-only")
ax.set_xlabel("M (D)"); ax.set_ylabel("optimal aperture (um)")
leg = ax.legend(frameon=False, fontsize=9)
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_stage3a_optimum_vs_M.png")

# 5. Brightness reconciliation
fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
ax.plot(br.scene_luminance_cdm2, br.min_aperture_van_nes_bouman_um, color=CATEGORICAL_1, marker="o", label="Van Nes & Bouman (300 Td, strict)")
ax.plot(br.scene_luminance_cdm2, br.min_aperture_CIE_low_um, color=CATEGORICAL_2, marker="s", label="CIE 191:2010 low")
ax.plot(br.scene_luminance_cdm2, br.min_aperture_CIE_high_um, color="#184f95", marker="^", label="CIE 191:2010 high")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("scene luminance (cd/m^2)"); ax.set_ylabel("minimum aperture (um)")
leg = ax.legend(frameon=False, fontsize=9)
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_brightness_reconciliation.png")

# 6. Single illuminate
fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
for i, dp in enumerate(sorted(si.D_pupil_um.unique())):
    g = si[si.D_pupil_um == dp].sort_values("a_hole_um")
    ax.plot(g.a_hole_um, g.percent_illumination * 100, marker="o", markersize=3.5,
            color=SEQ_CMAP(0.25 + 0.65 * i / max(len(si.D_pupil_um.unique()) - 1, 1)),
            label=f"D_pupil={dp:g}um")
ax.set_xlabel("aperture (um)"); ax.set_ylabel("percent illumination (%)")
leg = ax.legend(frameon=False, fontsize=9)
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_singleilluminate.png")

# 7. Strehl heatmap
fig = plot_heatmap(hv, "a_hole_um", "M_diopters", "strehl_ratio", ("aperture (um)", "M (D)", "Strehl ratio"))
save(fig, "fig_strehl_heatmap.png")

# 8. CSF models
import sys
sys.path.insert(0, os.path.join(ROOT, "stage3_human_vision"))
sys.path.insert(0, os.path.join(ROOT, "R7acuity"))
import contrast as s3_contrast  # noqa
import ntf as r7_ntf  # noqa
f_cpd = np.linspace(0.5, 60, 300)
fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
ax.plot(f_cpd, s3_contrast.csf_photopic_peak(f_cpd), color=CATEGORICAL_1, label="heuristic, 4 cpd peak")
ax.plot(f_cpd, s3_contrast.csf_mannos_sakrison(f_cpd), color=CATEGORICAL_2, label="heuristic (Mannos-Sakrison), 8 cpd peak")
for L, style in zip([10, 100, 1000], ["-", "--", ":"]):
    csf = r7_ntf.real_barten_csf(f_cpd, luminance_cdm2=L, field_diameter_deg=20.0)
    ax.plot(f_cpd, csf / np.nanmax(csf), color="#184f95", linestyle=style, label=f"Barten 1999, L={L} cd/m^2 (normalized)")
ax.set_xlabel("spatial frequency (cpd)"); ax.set_ylabel("sensitivity (normalized)")
leg = ax.legend(frameon=False, fontsize=8)
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_csf_models.png")

# 9. Acuity models comparison (at a representative M, using stage3_human_vision sweep to derive MTF-based routes)
import visual_acuity as s3_va  # noqa
M_rep = 4.0
g = hv[hv.M_diopters == M_rep].sort_values("a_hole_um")
mar10 = s3_va.cutoff_cpd_to_mar(g.mtf10_cpd.values)
mar50 = s3_va.cutoff_cpd_to_mar(g.mtf50_cpd.values)
logmar10 = s3_va.logmar_from_mar(mar10)
logmar50 = s3_va.logmar_from_mar(mar50)
acuity_M = acuity[acuity.M_diopters == M_rep].sort_values("a_hole_um")
fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
ax.plot(g.a_hole_um, logmar10, color=CATEGORICAL_1, marker="o", label="MTF10-cutoff route")
ax.plot(g.a_hole_um, logmar50, color=CATEGORICAL_2, marker="s", label="MTF50-cutoff route")
ax.plot(acuity_M.a_hole_um, acuity_M.logmar, color="#184f95", marker="^", label="VSOTF+brightness-adjusted (Stage 4 recommended)")
ax.set_xlabel("aperture (um)"); ax.set_ylabel(f"predicted logMAR (M={M_rep:g}D)")
leg = ax.legend(frameon=False, fontsize=9)
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_acuity_models_comparison.png")

# 10. Stage4 logMAR heatmap
fig = plot_heatmap(acuity, "a_hole_um", "M_diopters", "logmar", ("aperture (um)", "M (D)", "predicted logMAR"))
save(fig, "fig_stage4_logmar_heatmap.png")

# 11. Stage3 integrated heatmap (merge stage3a full_grid-equivalent E_rel with blur)
merged = blur.merge(
    pd.DataFrame({"a_hole_um": blur.a_hole_um, "M_diopters": blur.M_diopters,
                  "E_rel": np.minimum(blur.a_hole_um, 4000.0) ** 2 / 4000.0 ** 2}),
    on=["a_hole_um", "M_diopters"])
fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
pivot = merged.pivot_table(index="M_diopters", columns="a_hole_um", values="r_EE_50_um", aggfunc="mean")
im = ax.imshow(pivot.values, aspect="auto", cmap=SEQ_CMAP, origin="lower")
ax.set_xticks(range(len(pivot.columns))); ax.set_xticklabels([f"{c:g}" for c in pivot.columns], rotation=45, fontsize=8)
ax.set_yticks(range(len(pivot.index))); ax.set_yticklabels([f"{r:g}" for r in pivot.index], fontsize=8)
E_pivot = merged.pivot_table(index="M_diopters", columns="a_hole_um", values="E_rel", aggfunc="mean")
cs = ax.contour(range(len(pivot.columns)), range(len(pivot.index)), E_pivot.values,
                 levels=[0.0625, 0.25, 0.5, 0.75], colors=INK_PRIMARY, linewidths=1.0)
ax.clabel(cs, inline=True, fontsize=7, fmt=lambda v: f"E_rel={v:.0%}")
ax.set_xlabel("aperture (um)"); ax.set_ylabel("M (D)")
cbar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.06); cbar.set_label("r_EE(50%) (um)", color=INK_SECONDARY, fontsize=9)
save(fig, "fig_stage3_integrated_heatmap.png")

# 12. Model comparison divergence
fig = plot_heatmap(mc, "a_hole_um", "M_diopters", "divergence_pct", ("aperture (um)", "M (D)", "RSS divergence (%)"))
save(fig, "fig_model_comparison_divergence.png")

# 12b. RSS divergence against ALL FOUR percentiles, not r_EE(50%) alone -- the RSS
# r_total estimate itself carries no percentile notion (it's a single closed-form
# blur-radius estimate, Eq. 16.5), so "divergence" depends entirely on which exact
# numerical percentile it is being compared against; reuses mc's own r_total_rss_um
# merged onto blur's r_EE_70/80/90_um columns, no new sweep needed.
mc_ext = mc.merge(blur[["a_hole_um", "M_diopters", "r_EE_70_um", "r_EE_80_um", "r_EE_90_um"]],
                   on=["a_hole_um", "M_diopters"], how="inner")
for col in ["r_EE_50_exact_um", "r_EE_70_um", "r_EE_80_um", "r_EE_90_um"]:
    mc_ext[f"div_{col}"] = (mc_ext.r_total_rss_um - mc_ext[col]).abs() / mc_ext[col] * 100

fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
_mc_labels = {"div_r_EE_50_exact_um": "vs. r_EE(50%)", "div_r_EE_70_um": "vs. r_EE(70%)",
              "div_r_EE_80_um": "vs. r_EE(80%)", "div_r_EE_90_um": "vs. r_EE(90%)"}
_mc_colors = {"div_r_EE_50_exact_um": CATEGORICAL_1, "div_r_EE_70_um": CATEGORICAL_2,
              "div_r_EE_80_um": "#184f95", "div_r_EE_90_um": "#7a3a9e"}
for col, label in _mc_labels.items():
    grp = mc_ext.groupby("M_diopters")[col].mean()
    ax.plot(grp.index, grp.values, color=_mc_colors[col], marker="o", markersize=4, linewidth=1.8, label=label)
ax.set_xlabel("M (D)"); ax.set_ylabel("mean RSS divergence (%)")
leg = ax.legend(frameon=False, fontsize=9)
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_model_comparison_all_percentiles.png")

mc_summary_all = mc_ext.groupby("M_diopters")[["div_r_EE_50_exact_um", "div_r_EE_70_um", "div_r_EE_80_um", "div_r_EE_90_um"]].mean().reset_index()
mc_summary_all.columns = ["M (D)", "mean div. vs r_EE(50%)", "mean div. vs r_EE(70%)", "mean div. vs r_EE(80%)", "mean div. vs r_EE(90%)"]
write_table(df_to_longtable(mc_summary_all,
            "RSS closed-form mean divergence (\\%) against all four exact numerical percentiles, per myopia level.",
            "tab:model-comparison-all-percentiles", "{:.1f}"),
            "model_comparison_all_percentiles_table")

# 13. R7acuity closed-form heatmap
fig = plot_heatmap(r7, "a_hole_um", "M_diopters", "logmar_from_vsotf", ("aperture (um)", "M (D)", "logMAR (from VSOTF)"))
save(fig, "fig_r7acuity_closedform_heatmap.png")

# 14. Percentile optimum vs M, with saturation flagged
def optimum_table(df, y_col, x_col="a_hole_um", group_col="M_diopters", rtol=1e-6):
    rows = []
    for g_val in sorted(df[group_col].unique()):
        sub = df[df[group_col] == g_val]
        y_min = sub[y_col].min()
        tied = sub[np.isclose(sub[y_col], y_min, rtol=rtol, atol=1e-9)]
        rows.append({group_col: g_val, "opt": tied[x_col].min(), "saturated": len(tied) > 1})
    return pd.DataFrame(rows)

fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
colors = {"r_EE_50_um": CATEGORICAL_1, "r_EE_70_um": CATEGORICAL_2, "r_EE_80_um": "#184f95", "r_EE_90_um": "#7a3a9e"}
for col, color in colors.items():
    opt = optimum_table(blur, col)
    ax.plot(opt.M_diopters, opt.opt, color=color, linewidth=1.6, label=col.replace("_um", "").replace("_", "("))
    genuine = opt[~opt.saturated]; sat = opt[opt.saturated]
    ax.scatter(genuine.M_diopters, genuine.opt, color=color, marker="o", s=45, zorder=3)
    ax.scatter(sat.M_diopters, sat.opt, facecolor="none", edgecolor=color, marker="^", s=90, linewidth=1.6, zorder=4)
ax.set_xlabel("M (D)"); ax.set_ylabel("optimal aperture (um)")
leg = ax.legend(frameon=False, fontsize=8, loc="upper right")
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_percentile_optimum_vs_M.png")

# 15. Deprecated vs corrected overlay
fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
vals = sorted(blur.M_diopters.unique())
vmin, vmax = min(vals), max(vals)
for v in vals:
    g1 = blur[blur.M_diopters == v].sort_values("a_hole_um")
    g2 = dep[dep.M_diopters == v].sort_values("a_hole_um")
    c = seq_color(v, vmin, vmax)
    ax.plot(g1.a_hole_um, g1.r_EE_50_um, color=c, linewidth=1.6, linestyle="-")
    ax.plot(g2.a_hole_um, g2.r_EE_50_um, color=c, linewidth=1.6, linestyle="--")
sm = ScalarMappable(cmap=SEQ_CMAP, norm=plt.Normalize(vmin=vmin, vmax=vmax)); sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.06); cbar.set_label("M (D)", color=INK_SECONDARY, fontsize=9)
from matplotlib.lines import Line2D
style_handles = [Line2D([0], [0], color=INK_SECONDARY, linestyle="-", label="corrected (stage2_fixed/)"),
                 Line2D([0], [0], color=INK_SECONDARY, linestyle="--", label="deprecated (stage2/, pre-fix)")]
leg = ax.legend(handles=style_handles, frameon=False, fontsize=9, loc="upper right")
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
ax.set_xlabel("aperture (um)"); ax.set_ylabel("r_EE(50%) (um)")
style_axes(ax)
save(fig, "fig_deprecated_vs_corrected_overlay.png")

print("All figures done.")

# ======================================================================
# TABLES
# ======================================================================
print("Generating tables...")

# stage1_summary_table -- one row per aperture (12mm gap, 550nm)
t = stage1[["a_hole_um", "N_F", "regime", "r_EE_50_um", "r_EE_80_um", "r_EE_90_um", "second_moment_um"]].copy()
t.columns = ["a_hole (um)", "N_F", "regime", "r_EE50 (um)", "r_EE80 (um)", "r_EE90 (um)", "2nd moment (um)"]
write_table(df_to_longtable(t, "Stage 1 cornea-plane sweep, 12mm gap, 550nm.", "tab:stage1-full", "{:.2f}"),
            "stage1_summary_table")

# r1_optimum_table -- optimal aperture per M, corrected optics
opt = blur.loc[blur.groupby("M_diopters").r_EE_50_um.idxmin()][["M_diopters", "a_hole_um", "r_EE_50_um"]]
opt.columns = ["M (D)", "optimal aperture (um)", "r_EE(50%) at optimum (um)"]
write_table(df_to_longtable(opt, "Blur-only optimal aperture per myopia level, corrected optics.", "tab:r1-optimum", "{:.2f}"),
            "r1_optimum_table")

# stage3a_summary_table
t = stage3a[["M_diopters", "T_min", "a_star_um", "r_EE_50_um", "E_rel_at_optimum"]].copy()
t.columns = ["M (D)", "T_min", "a* (um)", "r_EE(50%) at a* (um)", "E_rel at a*"]
write_table(df_to_longtable(t, "Brightness-constrained optimum, T\\_min=6.25\\%.", "tab:stage3a-full", "{:.4f}"),
            "stage3a_summary_table")

# brightness_reconciliation_table
t = br.copy()
t.columns = ["scene lum (cd/m2)", "min aperture, CIE low (um)", "min aperture, CIE high (um)", "min aperture, VN&B (um)"]
write_table(df_to_longtable(t, "Minimum aperture clearing each absolute brightness threshold, vs. scene luminance.", "tab:brightness-full", "{:.1f}"),
            "brightness_reconciliation_table")

# singleilluminate_table
t = si[["a_hole_um", "D_pupil_um", "percent_illumination"]].copy()
t["percent_illumination"] = t["percent_illumination"] * 100
t.columns = ["a_hole (um)", "D_pupil (um)", "percent illumination (%)"]
write_table(df_to_longtable(t, "Single-hole percent illumination vs. aperture and natural pupil diameter.", "tab:singleilluminate-full", "{:.3f}"),
            "singleilluminate_table")

# mtf_strehl_summary_table -- one representative row per M at a mid aperture
rep_a = 750
t = hv[hv.a_hole_um == rep_a][["M_diopters", "mtf50_cpd", "mtf10_cpd", "strehl_ratio", "strehl_exceeds_unity", "rms_spot_radius_um"]].copy()
t.columns = ["M (D)", "MTF50 (cpd)", "MTF10 (cpd)", "Strehl", "Strehl>1", "RMS radius (um)"]
write_table(df_to_longtable(t, f"Stage 3 optical-quality metrics at aperture={rep_a}um, all myopia levels.", "tab:mtf-strehl-full", "{:.3f}"),
            "mtf_strehl_summary_table")

# stage4_summary_table -- optimal aperture by predicted logMAR per M
opt4 = acuity.loc[acuity.groupby("M_diopters").logmar.idxmin()][["M_diopters", "a_hole_um", "logmar", "vsotf", "retinal_illuminance_td"]]
opt4.columns = ["M (D)", "best-logMAR aperture (um)", "logMAR", "VSOTF", "retinal illuminance (Td)"]
write_table(df_to_longtable(opt4, "Aperture minimizing predicted logMAR, per myopia level (10000 cd/m2 scene).", "tab:stage4-full", "{:.3f}"),
            "stage4_summary_table")

# model_comparison_table -- summary stats per M
mc_summary = mc.groupby("M_diopters").agg(
    mean_divergence_pct=("divergence_pct", "mean"),
    max_divergence_pct=("divergence_pct", "max")).reset_index()
mc_summary.columns = ["M (D)", "mean divergence (%)", "max divergence (%)"]
write_table(df_to_longtable(mc_summary, "RSS closed-form vs. exact numerical divergence, summarized per myopia level.", "tab:model-comparison-full", "{:.2f}"),
            "model_comparison_table")

# r7acuity_summary_table
t = r7[["a_hole_um", "M_diopters", "strehl_ratio", "vsotf", "logmar_from_strehl", "logmar_from_vsotf"]].copy()
t.columns = ["a_hole (um)", "M (D)", "Strehl", "VSOTF", "logMAR (Strehl)", "logMAR (VSOTF)"]
write_table(df_to_longtable(t, "R7acuity closed-form Strehl/VSOTF cross-check, full sweep.", "tab:r7-full", "{:.3f}"),
            "r7acuity_summary_table")

# deprecated_vs_corrected_table
merged_dc = blur.merge(dep, on=["a_hole_um", "M_diopters"], suffixes=("_corrected", "_deprecated"))
opt_c = blur.loc[blur.groupby("M_diopters").r_EE_50_um.idxmin()].set_index("M_diopters").a_hole_um
opt_d = dep.loc[dep.groupby("M_diopters").r_EE_50_um.idxmin()].set_index("M_diopters").a_hole_um
cmp_tab = pd.DataFrame({"M (D)": opt_c.index, "corrected optimum (um)": opt_c.values,
                        "deprecated optimum (um)": opt_d.reindex(opt_c.index).values})
cmp_tab["change (%)"] = 100 * (cmp_tab["corrected optimum (um)"] - cmp_tab["deprecated optimum (um)"]) / cmp_tab["deprecated optimum (um)"]
write_table(df_to_longtable(cmp_tab, "Optimal aperture, corrected vs. deprecated optics, full grid.", "tab:dep-vs-corr-full", "{:.2f}"),
            "deprecated_vs_corrected_table")

# Appendix: the headline sweep in full (120 rows), the other two condensed to a
# per-myopia-level summary (their own full 120-row grids are in the delivered CSVs,
# not reproduced here -- see this appendix's own opening note).
write_table(df_to_longtable(blur[["a_hole_um","M_diopters","r_EE_50_um","r_EE_70_um","r_EE_80_um","r_EE_90_um","rms_radius_um"]],
            "Full Stage 2 (corrected) blur sweep -- all 120 points (the headline dataset this report's Chapter 7 derives from).",
            "tab:app-stage2-blur", "{:.3f}"),
            "appendix_stage2_blur_full")

acuity_summary = acuity.groupby("M_diopters").agg(
    best_aperture_um=("a_hole_um", lambda s: acuity.loc[s.index].loc[acuity.loc[s.index].logmar.idxmin(), "a_hole_um"]),
    min_logmar=("logmar", "min"), max_logmar=("logmar", "max"), mean_logmar=("logmar", "mean")).reset_index()
acuity_summary.columns = ["M (D)", "best aperture (um)", "min logMAR", "max logMAR", "mean logMAR"]
write_table(df_to_longtable(acuity_summary,
            "Stage 4 acuity sweep, condensed per myopia level (full 120-point grid in new\\_sweeps/acuity\\_sweep\\_stage4.csv).",
            "tab:app-stage4", "{:.3f}"),
            "appendix_stage4_acuity_full")

dep_summary = dep.groupby("M_diopters").agg(
    best_aperture_um=("a_hole_um", lambda s: dep.loc[s.index].loc[dep.loc[s.index].r_EE_50_um.idxmin(), "a_hole_um"]),
    min_r_ee50=("r_EE_50_um", "min"), max_r_ee50=("r_EE_50_um", "max"), mean_r_ee50=("r_EE_50_um", "mean")).reset_index()
dep_summary.columns = ["M (D)", "best aperture (um)", "min r_EE50 (um)", "max r_EE50 (um)", "mean r_EE50 (um)"]
write_table(df_to_longtable(dep_summary,
            "Deprecated (pre-fix) Stage 2 blur sweep, condensed per myopia level (full 120-point grid in Aperture\\_Optimization\\_Report/data/stage2\\_deprecated\\_sweep.csv).",
            "tab:app-stage2-dep", "{:.3f}"),
            "appendix_stage2_deprecated_full")

print("All tables done.")

# ======================================================================
# MULTI-PERCENTILE EXTENSION: r50/r70/r80/r90 optimization "at each spot",
# not just in the standalone percentile chapter. Reuses blur/dep, which already
# carry all four r_EE columns -- no new sweep needed. The brightness-constrained
# multi-percentile optimum inlines transmission.py's own E_rel formula (a pure
# area-ratio, already reused verbatim elsewhere in this script for the Stage 3
# Integrated figure) rather than re-running wrappers.sweep_stage3a_brightness(),
# which only ever selects r_EE_50_um internally.
# ======================================================================
print("Generating multi-percentile extension figures/tables...")

PCT_COLS = ["r_EE_50_um", "r_EE_70_um", "r_EE_80_um", "r_EE_90_um"]
PCT_LABELS = {"r_EE_50_um": "r_EE(50%)", "r_EE_70_um": "r_EE(70%)",
              "r_EE_80_um": "r_EE(80%)", "r_EE_90_um": "r_EE(90%)"}
PCT_COLORS = {"r_EE_50_um": CATEGORICAL_1, "r_EE_70_um": CATEGORICAL_2,
              "r_EE_80_um": "#184f95", "r_EE_90_um": "#7a3a9e"}


def brightness_constrained_optimum(df, y_col, T_min=0.0625, D_pupil_um=4000.0,
                                    x_col="a_hole_um", group_col="M_diopters"):
    """Same selection df.sort_values(x_col); cand = sub[E_rel>=T_min]; argmin(y_col)
    stage3a/combine_and_select.py and wrappers.sweep_stage3a_brightness() perform,
    parameterized over any blur column instead of only r_EE_50_um."""
    d = df.copy()
    d["E_rel"] = np.minimum(d[x_col], D_pupil_um) ** 2 / D_pupil_um ** 2
    rows = []
    for g_val in sorted(d[group_col].unique()):
        sub = d[d[group_col] == g_val].sort_values(x_col)
        cand = sub[sub.E_rel >= T_min]
        if len(cand) == 0:
            rows.append({group_col: g_val, "a_star": np.nan, y_col: np.nan})
            continue
        imin = cand[y_col].idxmin()
        rows.append({group_col: g_val, "a_star": cand.loc[imin, x_col], y_col: cand.loc[imin, y_col]})
    return pd.DataFrame(rows)


# --- Ch7 R1 sweep: unconstrained optimum, all 4 percentiles, one table ---
r1_all = []
for col in PCT_COLS:
    opt = optimum_table(blur, col)
    for _, r in opt.iterrows():
        r1_all.append({"M_diopters": r.M_diopters, "percentile": PCT_LABELS[col],
                       "optimal_a_hole_um": r.opt, "saturated": r.saturated})
r1_all_df = pd.DataFrame(r1_all)
r1_all_pivot = r1_all_df.pivot(index="M_diopters", columns="percentile", values="optimal_a_hole_um").reset_index()
r1_all_pivot.columns = ["M (D)"] + [c for c in r1_all_pivot.columns[1:]]
write_table(df_to_longtable(r1_all_pivot,
            "Unconstrained blur-only optimal aperture (um), all four percentiles, per myopia level.",
            "tab:r1-all-percentiles", "{:.0f}"),
            "r1_all_percentiles_table")

# --- Ch8 stage3a: brightness-constrained optimum, all 4 percentiles ---
stage3a_all = []
for col in PCT_COLS:
    opt = brightness_constrained_optimum(blur, col)
    for _, r in opt.iterrows():
        stage3a_all.append({"M_diopters": r.M_diopters, "percentile": PCT_LABELS[col], "a_star": r.a_star})
stage3a_all_df = pd.DataFrame(stage3a_all)
stage3a_all_pivot = stage3a_all_df.pivot(index="M_diopters", columns="percentile", values="a_star").reset_index()
stage3a_all_pivot.columns = ["M (D)"] + [c for c in stage3a_all_pivot.columns[1:]]
write_table(df_to_longtable(stage3a_all_pivot,
            "Brightness-constrained optimal aperture (um, T\\_min=6.25\\%), all four percentiles, per myopia level.",
            "tab:stage3a-all-percentiles", "{:.0f}"),
            "stage3a_all_percentiles_table")

fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
for col in PCT_COLS:
    opt = brightness_constrained_optimum(blur, col)
    ax.plot(opt.M_diopters, opt.a_star, color=PCT_COLORS[col], marker="o", markersize=4,
            linewidth=1.8, label=PCT_LABELS[col])
ax.set_xlabel("M (D)"); ax.set_ylabel("brightness-constrained optimal aperture (um)")
leg = ax.legend(frameon=False, fontsize=9)
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_stage3a_all_percentiles.png")

# --- Ch20 deprecated vs corrected: optimum-aperture change, all 4 percentiles ---
dvc_rows = []
for col in PCT_COLS:
    opt_c = blur.loc[blur.groupby("M_diopters")[col].idxmin()].set_index("M_diopters")["a_hole_um"]
    opt_d = dep.loc[dep.groupby("M_diopters")[col].idxmin()].set_index("M_diopters")["a_hole_um"]
    for M in opt_c.index:
        c_val, d_val = opt_c[M], opt_d.reindex(opt_c.index)[M]
        dvc_rows.append({"M_diopters": M, "percentile": PCT_LABELS[col],
                         "corrected_um": c_val, "deprecated_um": d_val,
                         "change_pct": 100 * (c_val - d_val) / d_val})
dvc_df = pd.DataFrame(dvc_rows)
dvc_pivot = dvc_df.pivot(index="M_diopters", columns="percentile", values="change_pct").reset_index()
dvc_pivot.columns = ["M (D)"] + [c for c in dvc_pivot.columns[1:]]
write_table(df_to_longtable(dvc_pivot,
            "Optimal-aperture change, corrected vs. deprecated optics (\\%), all four percentiles.",
            "tab:dvc-all-percentiles", "{:.1f}"),
            "deprecated_vs_corrected_all_percentiles_table")

fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
for col in PCT_COLS:
    sub = dvc_df[dvc_df.percentile == PCT_LABELS[col]].sort_values("M_diopters")
    ax.plot(sub.M_diopters, sub.change_pct, color=PCT_COLORS[col], marker="o", markersize=4,
            linewidth=1.8, label=PCT_LABELS[col])
ax.axhline(0, color=BASELINE, linewidth=1.0)
ax.set_xlabel("M (D)"); ax.set_ylabel("optimum-aperture change, corrected vs. deprecated (%)")
leg = ax.legend(frameon=False, fontsize=9)
for t in leg.get_texts(): t.set_color(INK_SECONDARY)
style_axes(ax)
save(fig, "fig_deprecated_vs_corrected_all_percentiles.png")

print("Multi-percentile extension done.")
print("Generation complete.")
