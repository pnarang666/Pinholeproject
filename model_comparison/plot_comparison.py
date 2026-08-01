"""
Plots comparing all three models, plus literature/commercial/clinical reference values
researched for this comparison. See README.md for full citations and discussion.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7"]

# Researched reference values -- see README.md "Literature and commercial comparison"
# section for full citations.
CLINICAL_PINHOLE_RANGE_UM = (940, 1750)       # effective clinical pinhole range
CLINICAL_PINHOLE_TYPICAL_UM = 1200            # most common clinical instrument aperture
COMMERCIAL_PINHOLE_GLASSES_RANGE_UM = (900, 1200)
RAYLEIGH_K_RANGE = (1.2, 2.0)                  # d = k * sqrt(f * lambda), k=1.56-1.9 typical
RAYLEIGH_K_TYPICAL = 1.9


def rayleigh_pinhole_diameter(f, wavelength, k=RAYLEIGH_K_TYPICAL):
    return k * np.sqrt(f * wavelength)


def plot_retina_comparison(df, M_diopters, wavelength_nm=550.0, z_gap_mm=12.0, out_path=None):
    sub = df[np.isclose(df["wavelength_nm"], wavelength_nm) &
              np.isclose(df["z_gap_mm"], z_gap_mm) &
              np.isclose(df["M_diopters"], M_diopters)].sort_values("a_hole_um")

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(sub["a_hole_um"], sub["stage2_r_EE_50_um"], "o-", color=CATEGORICAL[0],
            label="Model 2: stage2 exact (r_EE 50%)", markersize=6)
    ax.plot(sub["a_hole_um"], sub["approx_r_total_um"], "s--", color=CATEGORICAL[3],
            label="Model 3: approximation (r_total, RSS formula)", markersize=5)

    a_star = sub["approx_a_star_um"].iloc[0]
    ax.axvline(a_star, color=CATEGORICAL[3], linestyle=":", alpha=0.7,
               label=f"Model 3 predicted optimum a* = {a_star:.0f} um")

    idx_opt = sub["stage2_r_EE_50_um"].idxmin()
    ax.axvline(sub.loc[idx_opt, "a_hole_um"], color=CATEGORICAL[0], linestyle=":", alpha=0.7,
               label=f"Model 2 numerical optimum = {sub.loc[idx_opt, 'a_hole_um']:.0f} um")

    ax.axvspan(*CLINICAL_PINHOLE_RANGE_UM, color=CATEGORICAL[2], alpha=0.15,
               label=f"Clinical pinhole occluder range ({CLINICAL_PINHOLE_RANGE_UM[0]}-{CLINICAL_PINHOLE_RANGE_UM[1]} um)")
    ax.axvspan(*COMMERCIAL_PINHOLE_GLASSES_RANGE_UM, color=CATEGORICAL[1], alpha=0.15,
               label=f"Commercial pinhole glasses ({COMMERCIAL_PINHOLE_GLASSES_RANGE_UM[0]}-{COMMERCIAL_PINHOLE_GLASSES_RANGE_UM[1]} um)")

    v_r = sub["z_gap_mm"].iloc[0] * 1e-3  # placeholder, overwritten below with real v_r
    ax.set_xlabel("aperture diameter a_hole (µm)")
    ax.set_ylabel("retinal blur radius (µm)")
    ax.set_title(f"Model comparison: exact numerical vs. RSS approximation vs. real-world designs\n"
                 f"(M={M_diopters:.0f}D, λ={wavelength_nm:.0f}nm, gap={z_gap_mm:.0f}mm)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    if out_path:
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
    return fig


def plot_optimum_vs_rayleigh(retina_df, out_path):
    """Compares Model 2's numerical optimum, Model 3's a*, and the Rayleigh pinhole-camera
    formula (an independent, well-established formula from a physically analogous but
    different field), across myopia severity."""
    sub = retina_df[np.isclose(retina_df["wavelength_nm"], 550) & np.isclose(retina_df["z_gap_mm"], 12)]
    Ms = sorted(sub["M_diopters"].unique())

    numerical_opt, a_star_vals, rayleigh_vals = [], [], []
    for M in Ms:
        g = sub[np.isclose(sub["M_diopters"], M)].sort_values("a_hole_um")
        numerical_opt.append(g.loc[g["stage2_r_EE_50_um"].idxmin(), "a_hole_um"])
        a_star_vals.append(g["approx_a_star_um"].iloc[0])
        # Rayleigh pinhole-camera formula, using v_r (the eye's own analog to "focal length")
        # -- an INDEPENDENT well-established formula from actual pinhole-camera literature,
        # not derived from anything in this project; see README for citation.
        v_r_mm = 1.336 / (60.0 - M) * 1e3 if M < 60 else np.nan
        rayleigh_vals.append(rayleigh_pinhole_diameter(v_r_mm * 1e-3, 550e-9) * 1e6)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(Ms, numerical_opt, "o-", color=CATEGORICAL[0], label="Model 2: numerical optimum (r_EE 50%)")
    ax.plot(Ms, a_star_vals, "s--", color=CATEGORICAL[3], label="Model 3: closed-form a* (RSS formula)")
    ax.plot(Ms, rayleigh_vals, "^-", color=CATEGORICAL[4], label="Rayleigh pinhole-camera formula (independent literature)")
    ax.axhspan(*CLINICAL_PINHOLE_RANGE_UM, color=CATEGORICAL[2], alpha=0.15, label="Clinical pinhole range")
    ax.axhspan(*COMMERCIAL_PINHOLE_GLASSES_RANGE_UM, color=CATEGORICAL[1], alpha=0.15, label="Commercial pinhole glasses")
    ax.set_xlabel("myopia severity M (diopters)")
    ax.set_ylabel("aperture diameter (µm)")
    ax.set_title("Optimal aperture: numerical model vs. formulas vs. real-world designs")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_cornea_comparison(cornea_df, wavelength_nm, z_gap_mm, out_path):
    sub = cornea_df[np.isclose(cornea_df["wavelength_nm"], wavelength_nm) &
                     np.isclose(cornea_df["z_gap_mm"], z_gap_mm)].sort_values("a_hole_um")
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(sub["a_hole_um"], sub["stage1_r_EE_80_um"], "o-", color=CATEGORICAL[0],
            label="Model 1: stage1 exact ASM (r_EE 80%, cornea)")
    ax.plot(sub["a_hole_um"], sub["approx_a_eff_um"] / 2, "s--", color=CATEGORICAL[3],
            label="Model 3: a_eff/2 (quadrature approximation, cornea)")
    ax.set_xlabel("aperture diameter a_hole (µm)")
    ax.set_ylabel("cornea-plane spot radius (µm)")
    ax.set_title(f"Cornea-plane comparison: exact ASM vs. quadrature approximation\n"
                 f"(λ={wavelength_nm:.0f}nm, gap={z_gap_mm:.0f}mm)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    retina_df = pd.read_csv("outputs/retina_model_comparison.csv")
    cornea_df = pd.read_csv("outputs/cornea_model_comparison.csv")

    for M in [1.0, 4.0, 8.0]:
        plot_retina_comparison(retina_df, M, out_path=f"outputs/comparison_retina_M{int(M)}.png")
        print(f"saved comparison_retina_M{int(M)}.png")

    plot_optimum_vs_rayleigh(retina_df, "outputs/comparison_optimum_vs_rayleigh.png")
    print("saved comparison_optimum_vs_rayleigh.png")

    plot_cornea_comparison(cornea_df, 550.0, 12.0, "outputs/comparison_cornea.png")
    print("saved comparison_cornea.png")


if __name__ == "__main__":
    main()
