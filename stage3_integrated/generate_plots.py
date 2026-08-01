"""
All Phase A plots. Reuses stage3_human_vision/plots.py and metrics.py wherever a plot
type already exists there (extending with the fuller grid, not recopying); adds the
plot types stage3_human_vision never built (OTF/MTF curves, CSF comparison, Trolands,
combined acuity-model comparison, FWHM ring-hopping, all-M Pareto overlay, sensitivity
heatmaps, validation tolerance bands).
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
_STAGE1_V2_DIR = os.path.abspath(os.path.join(HERE, "..", "stage1_v2"))
_STAGE3HV_DIR = os.path.abspath(os.path.join(HERE, "..", "stage3_human_vision"))
for _d in (_STAGE1_V2_DIR, _STAGE3HV_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import physics  # noqa: E402
import metrics  # noqa: E402
import contrast  # noqa: E402
import visual_acuity  # noqa: E402
import pareto  # noqa: E402
import validation_gate  # noqa: E402

OUT_DIR = os.path.join(HERE, "outputs")
CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7", "#e87ba4", "#008300"]
WAVELENGTH_COLORS = {450.0: "#3457D5", 550.0: "#4C9A2A", 650.0: "#C1442D"}
CLINICAL_RANGE_UM = (940, 1750)


def _load_all():
    combined = pd.read_csv(os.path.join(OUT_DIR, "combined_grid_550nm_12mm.csv"))
    fwhm = pd.read_csv(os.path.join(OUT_DIR, "retina_fwhm_sweep.csv"))
    fine_strehl = pd.read_csv(os.path.join(OUT_DIR, "fine_strehl_sweep.csv"))
    wl_gap = pd.read_csv(os.path.join(OUT_DIR, "wavelength_gap_sweep.csv"))
    constrained = pd.read_csv(os.path.join(OUT_DIR, "constrained_optimum_all_metrics.csv"))
    return combined, fwhm, fine_strehl, wl_gap, constrained


def _load_validation():
    stage3hv_out = os.path.join(_STAGE3HV_DIR, "outputs")
    points = pd.read_csv(os.path.join(stage3hv_out, "validation_predicted_vs_observed.csv"))
    stats_df = pd.read_csv(os.path.join(stage3hv_out, "validation_regression_stats.csv"))
    return points, stats_df


# ---------------------------------------------------------------------------------
# 1. MTF / OTF
# ---------------------------------------------------------------------------------
def plot_mtf_curves(a_hole_um=400.0, M_values=(1.0, 4.0, 8.0), wavelength_nm=550.0, d_gap_mm=12.0):
    import phase2_retina as p2
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for i, M in enumerate(M_values):
        result = p2.run_pipeline_point(a_hole=a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9,
                                        d_gap=d_gap_mm * 1e-3, grid_N=2048, window_L_mm=6.0,
                                        M_diopters=M, P0=60.0, n_prime=1.336, D_pupil_um=4000.0,
                                        refractive_index_correction=True)
        I = result["I_retina"]; dx = result["cornea_result"]["dx"]; v_r = result["myopia"]["L_ax"]
        f_cpum, mtf = metrics.mtf_radial(I, dx)
        f_cpd = metrics.cycles_per_um_to_cycles_per_degree(f_cpum, v_r)
        mask = f_cpd <= 30
        ax.plot(f_cpd[mask], mtf[mask], color=CATEGORICAL[i], label=f"M={M:.0f}D")
    ax.set_xlabel("spatial frequency (cycles/degree)")
    ax.set_ylabel("MTF (from OTF = FFT(PSF), normalized)")
    ax.set_title(f"MTF vs spatial frequency (a_hole={a_hole_um:.0f}um, {wavelength_nm:.0f}nm)")
    ax.axhline(0.5, color="gray", linestyle=":", alpha=0.6, label="MTF50 level")
    ax.axhline(0.1, color="gray", linestyle="--", alpha=0.6, label="MTF10 level")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "mtf_curves.png"), dpi=150); plt.close(fig)


def plot_mtf50_extended(combined, wl_gap):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    Ms = sorted(combined["M_diopters"].unique())
    for i, M in enumerate(Ms):
        g = combined[np.isclose(combined["M_diopters"], M)].sort_values("a_hole_um")
        axes[0].plot(g["a_hole_um"], g["mtf50_cpd"], "o-", color=CATEGORICAL[i % 7], label=f"M={M:.0f}D", markersize=4)
    axes[0].set_xlabel("aperture (µm)"); axes[0].set_ylabel("MTF50 (cpd)")
    axes[0].set_title("MTF50 vs aperture, by myopia (550nm/12mm)")
    axes[0].legend(fontsize=7, ncol=2); axes[0].grid(alpha=0.3)

    for wl in sorted(wl_gap["wavelength_nm"].unique()):
        g = wl_gap[np.isclose(wl_gap["wavelength_nm"], wl) & np.isclose(wl_gap["M_diopters"], 4.0)].sort_values("a_hole_um")
        c = WAVELENGTH_COLORS.get(round(wl / 50) * 50, "gray")
        axes[1].plot(g["a_hole_um"], g["mtf50_cpd"], "o-", color=c, label=f"{wl:.0f}nm")
    g0 = combined[np.isclose(combined["M_diopters"], 4.0)].sort_values("a_hole_um")
    axes[1].plot(g0["a_hole_um"], g0["mtf50_cpd"], "o-", color=WAVELENGTH_COLORS[550.0], label="550nm (12mm, full grid)")
    axes[1].set_xlabel("aperture (µm)"); axes[1].set_ylabel("MTF50 (cpd)")
    axes[1].set_title("MTF50 vs aperture, by wavelength (M=4D)")
    axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "mtf50_extended.png"), dpi=150); plt.close(fig)


def plot_otf_phase(a_hole_um=1000.0, M=4.0, wavelength_nm=550.0, d_gap_mm=12.0):
    """
    OTF is now a first-class quantity (metrics.otf_radial), distinct from MTF
    (metrics.mtf_radial only ever returned |OTF|, discarding phase). This plot makes
    that distinction visible: |OTF| vs Re(OTF) (left) and the phase transfer function
    itself (right, degrees).

    Default condition (a_hole=1000um, M=4D) was chosen because it was DIRECTLY
    CONFIRMED (not assumed) to show a genuine OTF sign reversal -- classical defocus
    "spurious resolution": Re(OTF) dips to ~-0.108 near f~0.009 cycles/um with
    Im(OTF) ~1e-19 there (i.e. genuinely real and negative, not numerical noise) --
    a scan across a_hole in [200,2000]um x M in [1,2,4,6,8]D found this reversal
    appears for a_hole >= ~750um at every tested M, and does NOT appear for smaller
    apertures (200-500um) in this same scan. An earlier default (400um, M=4D) showed
    no reversal at all -- Re(OTF) tracked |OTF| exactly down to the noise floor -- so
    was replaced with this one, which actually demonstrates the phenomenon the plot
    is about, rather than asserting it without evidence.
    """
    import phase2_retina as p2
    result = p2.run_pipeline_point(a_hole=a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9,
                                    d_gap=d_gap_mm * 1e-3, grid_N=2048, window_L_mm=6.0,
                                    M_diopters=M, P0=60.0, n_prime=1.336, D_pupil_um=4000.0,
                                    refractive_index_correction=True)
    I = result["I_retina"]; dx = result["cornea_result"]["dx"]; v_r = result["myopia"]["L_ax"]
    f_cpum, otf = metrics.otf_radial(I, dx)
    f_cpd = metrics.cycles_per_um_to_cycles_per_degree(f_cpum, v_r)
    mask = (f_cpd >= 0) & (f_cpd <= 30)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    axes[0].plot(f_cpd[mask], np.abs(otf[mask]), color=CATEGORICAL[0], label="|OTF| (= MTF)")
    axes[0].plot(f_cpd[mask], np.real(otf[mask]), color=CATEGORICAL[3], linestyle="--", label="Re(OTF)")
    axes[0].axhline(0.0, color="gray", linewidth=0.8)
    axes[0].set_xlabel("spatial frequency (cycles/degree)"); axes[0].set_ylabel("value")
    axes[0].set_title(f"|OTF| vs Re(OTF) (a_hole={a_hole_um:.0f}um, M={M:.0f}D)\ndiverge wherever OTF phase != 0")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)

    axes[1].plot(f_cpd[mask], np.degrees(np.angle(otf[mask])), color=CATEGORICAL[2])
    axes[1].axhline(0.0, color="gray", linewidth=0.8)
    axes[1].set_xlabel("spatial frequency (cycles/degree)"); axes[1].set_ylabel("phase (degrees)")
    axes[1].set_title("Phase transfer function (PTF) -- never plotted before\n(near-field defocus can show phase reversals / spurious resolution)")
    axes[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "otf_phase.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------
# 2. CSF comparison
# ---------------------------------------------------------------------------------
def plot_csf_comparison():
    f = np.linspace(0.5, 40, 300)
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.plot(f, contrast.csf_photopic_peak(f), color=CATEGORICAL[0], label="photopic_4cpd (peak ~4 cpd)")
    ax.plot(f, contrast.csf_mannos_sakrison(f), color=CATEGORICAL[3], label="Mannos-Sakrison (peak ~8 cpd)")
    ax.set_xlabel("spatial frequency (cycles/degree)"); ax.set_ylabel("relative contrast sensitivity")
    ax.set_title("Two published CSF parametrizations -- NOT merged into one curve\n(see literature.py for fidelity notes on each)")
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "csf_comparison.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------
# 3. Retinal illuminance / Trolands
# ---------------------------------------------------------------------------------
def plot_illuminance_troland(combined):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    g = combined[np.isclose(combined["M_diopters"], 4.0)].sort_values("a_hole_um")
    axes[0].plot(g["a_hole_um"], g["relative_retinal_illuminance"] * 100, "o-", color=CATEGORICAL[0])
    axes[0].set_xlabel("aperture (µm)"); axes[0].set_ylabel("relative retinal illuminance (%)")
    axes[0].set_title("Relative retinal illuminance vs aperture\n(fraction of full 4mm natural pupil)")
    axes[0].grid(alpha=0.3)

    scene_lum = g["scene_luminance_cdm2"].iloc[0]
    axes[1].plot(g["a_hole_um"], g["retinal_illuminance_troland"], "o-", color=CATEGORICAL[3])
    axes[1].set_xlabel("aperture (µm)"); axes[1].set_ylabel("retinal illuminance (Trolands)")
    axes[1].set_title(f"Absolute retinal illuminance vs aperture\n(assumed scene luminance = {scene_lum:.0f} cd/m^2)")
    axes[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "illuminance_troland.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------
# 4. Combined acuity-model comparison (the view that doesn't exist yet)
# ---------------------------------------------------------------------------------
def plot_acuity_models_combined(combined, M_values=(1.0, 4.0, 8.0)):
    fig, axes = plt.subplots(1, len(M_values), figsize=(6 * len(M_values), 5.5), sharey=True)
    for ax, M in zip(axes, M_values):
        g = combined[np.isclose(combined["M_diopters"], M)].sort_values("a_hole_um")
        ax.plot(g["a_hole_um"], g["snellen_denom_mtf50"], "o-", color=CATEGORICAL[0], label="MTF50 cutoff")
        ax.plot(g["a_hole_um"], g["snellen_denom_mtf10"], "o-", color=CATEGORICAL[1], label="MTF10 cutoff")
        # Rose-DeVries SNR-bound acuity, relative to the 400um point as reference
        ref_flux = g.loc[np.isclose(g["a_hole_um"], 400.0), "photon_flux_density_per_s_per_m2"].iloc[0]
        rd_mar = [visual_acuity.snr_acuity_bound(f, reference_flux_density=ref_flux, reference_mar_arcmin=2.0)
                  for f in g["photon_flux_density_per_s_per_m2"]]
        rd_snellen = [visual_acuity.mar_to_snellen_denominator(m) for m in rd_mar]
        ax.plot(g["a_hole_um"], rd_snellen, "o-", color=CATEGORICAL[3], label="Rose-DeVries SNR bound")
        ax.set_yscale("log")
        ax.set_xlabel("aperture (µm)"); ax.set_title(f"M={M:.0f}D")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("predicted Snellen denominator (log scale, lower=better)")
    axes[0].legend(fontsize=8)
    fig.suptitle("Three acuity-prediction models compared (never plotted together before)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "acuity_models_combined.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------
# 5. Strehl -- annotated with the non-monotonicity investigation
# ---------------------------------------------------------------------------------
def plot_strehl_investigation(combined, fine_strehl):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for i, M in enumerate([4.0, 8.0]):
        g = combined[np.isclose(combined["M_diopters"], M)].sort_values("a_hole_um")
        axes[0].plot(g["a_hole_um"], g["strehl_ratio"], "o-", color=CATEGORICAL[i], label=f"M={M:.0f}D (15-pt grid)")
    axes[0].axhline(1.0, color="black", linestyle=":", alpha=0.5)
    axes[0].set_xlabel("aperture (µm)"); axes[0].set_ylabel("Strehl ratio")
    axes[0].set_title("Original 15-point grid"); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)

    for i, M in enumerate([4.0, 8.0]):
        g = fine_strehl[np.isclose(fine_strehl["M_diopters"], M)].sort_values("a_hole_um")
        axes[1].plot(g["a_hole_um"], g["strehl_ratio"], "o-", color=CATEGORICAL[i], label=f"M={M:.0f}D (100um steps)", markersize=4)
    axes[1].axhline(1.0, color="black", linestyle=":", alpha=0.5)
    axes[1].set_xlabel("aperture (µm)"); axes[1].set_ylabel("Strehl ratio")
    axes[1].set_title("10x finer grid: MORE oscillation revealed, not less\n-> genuine ring interference, not a sampling artifact")
    axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "strehl_investigation.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------
# 6. EE(50/70/80/90) extended
# ---------------------------------------------------------------------------------
def plot_ee_all_percentiles(combined):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    g = combined[np.isclose(combined["M_diopters"], 4.0)].sort_values("a_hole_um")
    for i, p in enumerate(["50", "70", "80", "90"]):
        ax.plot(g["a_hole_um"], g[f"r_EE_{p}_um"], "o-", color=CATEGORICAL[i], label=f"r_EE({p}%)")
    ax.set_xlabel("aperture (µm)"); ax.set_ylabel("blur radius (µm)")
    ax.set_title("Encircled-energy radius at 4 percentiles (M=4D, 550nm/12mm)")
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "ee_all_percentiles.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------
# 7. Retina-plane FWHM -- ring-hopping check
# ---------------------------------------------------------------------------------
def plot_retina_fwhm(fwhm_df):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for i, M in enumerate([1.0, 4.0, 8.0]):
        g = fwhm_df[np.isclose(fwhm_df["M_diopters"], M)].sort_values("a_hole_um")
        ax.plot(g["a_hole_um"], g["fwhm_radius_um"], "o-", color=CATEGORICAL[i], label=f"M={M:.0f}D")
    ax.set_yscale("log")
    ax.set_xlabel("aperture (µm)"); ax.set_ylabel("FWHM radius (µm, log scale)")
    ax.set_title("Retina-plane FWHM vs aperture -- same ring-hopping instability\nfound at the cornea plane in Stage 1, confirmed here too (see README)")
    ax.legend(fontsize=9); ax.grid(alpha=0.3, which="both")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "retina_fwhm_ring_hopping.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------
# 8. Pareto -- all M + overlay, at r_EE(50%), r_EE(70%), r_EE(80%) side by side
# (never just r_EE(50%) alone -- a stricter/looser EE percentile as the blur axis can
# shift where the front sits, which the single-percentile version couldn't show)
# ---------------------------------------------------------------------------------
def plot_pareto_all_M(combined):
    Ms = sorted(combined["M_diopters"].unique())
    blur_cols = [("r_EE_50_um", "r_EE(50%)"), ("r_EE_70_um", "r_EE(70%)"), ("r_EE_80_um", "r_EE(80%)")]
    fig, axes = plt.subplots(1, 3, figsize=(19, 6), sharey=True)
    for ax, (blur_col, blur_label) in zip(axes, blur_cols):
        for i, M in enumerate(Ms):
            g = combined[np.isclose(combined["M_diopters"], M)].copy()
            g = pareto.build_default_pareto(g, blur_col=blur_col, illumination_col="throughput_area_ratio")
            front = g[g["pareto_optimal"]].sort_values(blur_col)
            ax.plot(front[blur_col], front["throughput_area_ratio"], "o-", color=CATEGORICAL[i % 7],
                     label=f"M={M:.0f}D", alpha=0.85, markersize=4)
        ax.set_xlabel(f"{blur_label} blur radius, um (minimize)")
        ax.set_title(blur_label)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("throughput (maximize)")
    axes[0].legend(fontsize=7, ncol=2)
    fig.suptitle("Pareto fronts across all 7 myopia levels, by blur-percentile choice -- "
                 "how the front's shape shifts with M AND with which r_EE(P) is used")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "pareto_all_M_overlay.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------
# 9. Sensitivity heatmaps -- r_EE(50/70/80%) alongside MTF50/Strehl/illuminance
# ---------------------------------------------------------------------------------
def plot_sensitivity_heatmaps(combined, wl_gap):
    fig, axes = plt.subplots(2, 3, figsize=(19, 11))
    metrics_to_plot = [("r_EE_50_um", "r_EE(50%) (µm)"), ("r_EE_70_um", "r_EE(70%) (µm)"),
                       ("r_EE_80_um", "r_EE(80%) (µm)"), ("mtf50_cpd", "MTF50 (cpd)"),
                       ("strehl_ratio", "Strehl ratio"), ("relative_retinal_illuminance", "relative illuminance")]
    for ax, (col, label) in zip(axes.flat, metrics_to_plot):
        pivot = combined.pivot_table(index="M_diopters", columns="a_hole_um", values=col)
        im = ax.imshow(pivot.values, aspect="auto", origin="lower", cmap="viridis",
                       extent=[pivot.columns.min(), pivot.columns.max(), pivot.index.min(), pivot.index.max()])
        ax.set_xlabel("aperture (µm)"); ax.set_ylabel("M (diopters)"); ax.set_title(label)
        fig.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle("Sensitivity heatmaps: aperture x myopia (550nm/12mm)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "sensitivity_heatmaps_aperture_M.png"), dpi=150); plt.close(fig)

    # wavelength x aperture at fixed M=4D -- r_EE(50/80/90%), NOT r_EE(70%): the
    # wavelength_gap_sweep.csv supplementary sweep (450/650nm, 15mm gap) was computed
    # via stage3_human_vision/metrics.py, which never included r_EE(70%) (that column
    # only exists in stage3a's separate multi_EE_sweep.csv, at 550nm/12mm only) -- using
    # it here would silently show NaN at 450/650nm rather than real data, so 50/80/90%
    # (present at every wavelength) are used instead. Documented, not silently patched.
    fig2, axes2 = plt.subplots(1, 3, figsize=(19, 5.5))
    for ax2, (col, label) in zip(axes2, [("r_EE_50_um", "r_EE(50%)"), ("r_EE_80_um", "r_EE(80%)"), ("r_EE_90_um", "r_EE(90%)")]):
        sub = wl_gap[np.isclose(wl_gap["M_diopters"], 4.0) & np.isclose(wl_gap["z_gap_mm"], 12.0)]
        combined_m4 = combined[np.isclose(combined["M_diopters"], 4.0)][["a_hole_um", "wavelength_nm", col]]
        full = pd.concat([sub[["a_hole_um", "wavelength_nm", col]], combined_m4])
        pivot = full.pivot_table(index="wavelength_nm", columns="a_hole_um", values=col)
        im = ax2.imshow(pivot.values, aspect="auto", origin="lower", cmap="viridis",
                        extent=[pivot.columns.min(), pivot.columns.max(), pivot.index.min(), pivot.index.max()])
        ax2.set_xlabel("aperture (µm)"); ax2.set_ylabel("wavelength (nm)")
        ax2.set_title(f"{label} (M=4D, 12mm gap)")
        fig2.colorbar(im, ax=ax2, label=f"{label} um", fraction=0.046)
    fig2.suptitle("Wavelength x aperture sensitivity, by blur-percentile choice")
    fig2.tight_layout(); fig2.savefig(os.path.join(OUT_DIR, "sensitivity_heatmap_wavelength_aperture.png"), dpi=150); plt.close(fig2)


# ---------------------------------------------------------------------------------
# 10. Validation: predicted vs observed LogMAR, against literature.get(
# 'ideal_pinhole_wang_2009') -- the RMSE/MAE/R^2/Pearson r "Validation" stage of the
# pipeline. See stage3_human_vision/validate_against_literature.py for how these two
# CSVs are produced (a sensitivity sweep across M, not a single forced fit).
# ---------------------------------------------------------------------------------
def plot_validation_regression(points_df, stats_df):
    predictor_labels = {"logmar_mtf50": "MTF50 cutoff", "logmar_mtf10": "MTF10 cutoff",
                         "logmar_fwhm": "FWHM-based"}
    Ms = sorted(points_df["M_diopters"].unique())
    fig, axes = plt.subplots(1, len(Ms), figsize=(6 * len(Ms), 5.5), sharex=True, sharey=True)
    for ax, M in zip(axes, Ms):
        g = points_df[np.isclose(points_df["M_diopters"], M)].sort_values("observed_logmar")
        lims = [min(g["observed_logmar"].min(), g[list(predictor_labels)].min().min()) - 0.1,
                max(g["observed_logmar"].max(), g[list(predictor_labels)].max().max()) + 0.1]
        ax.plot(lims, lims, color="gray", linestyle=":", linewidth=1, label="y = x (perfect agreement)")
        annot_lines = []
        for i, (col, label) in enumerate(predictor_labels.items()):
            ax.scatter(g["observed_logmar"], g[col], color=CATEGORICAL[i], label=label, s=45, zorder=3)
            row = stats_df[np.isclose(stats_df["M_diopters"], M) & (stats_df["predictor"] == col)].iloc[0]
            annot_lines.append(f"{label}: RMSE={row['rmse']:.2f} R2={row['r_squared']:.2f} r={row['pearson_r']:.2f}")
        ax.set_xlim(lims); ax.set_ylim(lims)
        ax.set_xlabel("observed LogMAR (Wang et al. 2009)")
        ax.set_title(f"M={M:.0f}D\n" + "\n".join(annot_lines), fontsize=8)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("predicted LogMAR (this project)")
    axes[0].legend(fontsize=7, loc="upper left")
    fig.suptitle("Validation: predicted vs observed LogMAR, sensitivity across M\n"
                 "(no single M is asserted as 'correct' -- see literature.py's fidelity note)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "validation_predicted_vs_observed.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------
# 11. Validation with tolerance bands
# ---------------------------------------------------------------------------------
def plot_validation_tolerance_bands():
    gate = validation_gate.run_validation_gate()
    fig, ax = plt.subplots(figsize=(8, 5.5))
    labels = [r["label"] for r in gate["rows"]]
    rel_err = [r["rel_error"] * 100 for r in gate["rows"]]
    tol = [r["tolerance"] * 100 for r in gate["rows"]]
    x = np.arange(len(labels))
    ax.bar(x, tol, color="lightgray", label="tolerance band", width=0.6)
    ax.bar(x, rel_err, color=[CATEGORICAL[0] if r["passed"] else CATEGORICAL[3] for r in gate["rows"]],
           width=0.3, label="actual relative error")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("relative error vs. closed-form Airy formula (%)")
    ax.set_title("Validation: numeric vs closed-form, with tolerance bands\nr_EE(80%) sits near the Airy first-null zero-slope point -- wider tolerance is a\nproperty of that point's ill-conditioning, not a looser standard (see stage2 README)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "validation_tolerance_bands.png"), dpi=150); plt.close(fig)


def make_all_plots():
    combined, fwhm, fine_strehl, wl_gap, constrained = _load_all()
    print("Plotting MTF/OTF...")
    plot_mtf_curves()
    plot_mtf50_extended(combined, wl_gap)
    plot_otf_phase()
    print("Plotting CSF...")
    plot_csf_comparison()
    print("Plotting illuminance/Trolands...")
    plot_illuminance_troland(combined)
    print("Plotting combined acuity models...")
    plot_acuity_models_combined(combined)
    print("Plotting Strehl investigation...")
    plot_strehl_investigation(combined, fine_strehl)
    print("Plotting EE percentiles...")
    plot_ee_all_percentiles(combined)
    print("Plotting retina FWHM...")
    plot_retina_fwhm(fwhm)
    print("Plotting Pareto (all M)...")
    plot_pareto_all_M(combined)
    print("Plotting sensitivity heatmaps...")
    plot_sensitivity_heatmaps(combined, wl_gap)
    print("Plotting validation (predicted vs observed LogMAR)...")
    points_df, val_stats_df = _load_validation()
    plot_validation_regression(points_df, val_stats_df)
    print("Plotting validation tolerance bands...")
    plot_validation_tolerance_bands()
    print(f"All plots written to {OUT_DIR}")


if __name__ == "__main__":
    make_all_plots()
