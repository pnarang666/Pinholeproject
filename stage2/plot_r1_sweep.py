"""
Handbook Master-Formulas doc, section 4, steps 2-3: plot r_EE(0.5/0.8/0.9) vs a_hole
for the R1 single-hole sweep, and overlay the deprecated RSS-combined blur formula
r_total (#7) plus its closed-form optimum a* (#8) for comparison. Reads a CSV produced
by sweep_myopia.py.

Usage:
    python3 plot_r1_sweep.py outputs/r1_full_range_sweep.csv
"""

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import classical_formulas as cf

CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7"]


def plot_ee_vs_aperture(df, wavelength_nm, z_gap_mm, M_diopters, D_pupil_um, out_path):
    sub = df[np.isclose(df["wavelength_nm"], wavelength_nm) &
              np.isclose(df["z_gap_mm"], z_gap_mm) &
              np.isclose(df["M_diopters"], M_diopters)].sort_values("a_hole_um")
    if sub.empty:
        print(f"no rows for wavelength={wavelength_nm} z_gap={z_gap_mm} M={M_diopters}")
        return None

    wavelength_m = wavelength_nm * 1e-9
    d_gap_m = z_gap_mm * 1e-3
    D_pupil_m = D_pupil_um * 1e-6
    v_r = sub["L_ax_mm"].iloc[0] * 1e-3
    v_f = sub["f_eye_mm"].iloc[0] * 1e-3
    a_hole_m = sub["a_hole_um"].values * 1e-6

    r_total_um = cf.r_total(a_hole_m, wavelength_m, d_gap_m, D_pupil_m, v_r, v_f) * 1e6
    a_star_um = cf.a_star(wavelength_m, v_r, v_f) * 1e6

    fig, ax = plt.subplots(figsize=(8, 5.5))
    for i, (col, label) in enumerate([
        ("r_EE_50_retina_um", "r_EE(0.5) -- numerical"),
        ("r_EE_80_retina_um", "r_EE(0.8) -- numerical"),
        ("r_EE_90_retina_um", "r_EE(0.9) -- numerical"),
    ]):
        ax.plot(sub["a_hole_um"], sub[col], "o-", color=CATEGORICAL[i], label=label, markersize=5)

    ax.plot(sub["a_hole_um"], r_total_um, "--", color=CATEGORICAL[3],
            label="r_total (#7, deprecated RSS) -- same retina plane, comparable")
    ax.axvline(a_star_um, color=CATEGORICAL[4], linestyle=":",
               label=f"a* (#8, closed-form optimum) = {a_star_um:.0f} um")

    idx_min_50 = sub["r_EE_50_retina_um"].idxmin()
    a_hole_numeric_opt = sub.loc[idx_min_50, "a_hole_um"]
    ax.axvline(a_hole_numeric_opt, color=CATEGORICAL[0], linestyle=":",
               label=f"numerical r_EE(0.5) optimum in range = {a_hole_numeric_opt:.0f} um")

    ax.set_xlabel("aperture diameter a_hole (µm)")
    ax.set_ylabel("retinal blur radius (µm)")
    ax.set_title(f"R1 sweep: retinal blur vs aperture "
                 f"(λ={wavelength_nm:.0f}nm, gap={z_gap_mm:.0f}mm, M={M_diopters:.0f}D)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    print(f"--- λ={wavelength_nm:.0f}nm, gap={z_gap_mm:.0f}mm, M={M_diopters:.0f}D "
          f"(v_r={v_r*1e3:.2f}mm, v_f={v_f*1e3:.2f}mm) ---")
    for col, label in [("r_EE_50_retina_um", "r_EE(0.5)"), ("r_EE_80_retina_um", "r_EE(0.8)"),
                       ("r_EE_90_retina_um", "r_EE(0.9)")]:
        idx_min = sub[col].idxmin()
        at_edge = sub.loc[idx_min, "a_hole_um"] == sub["a_hole_um"].min()
        edge_note = "  <-- AT THE EDGE OF THE SWEPT RANGE, true optimum may lie outside it" if at_edge else ""
        print(f"  {label} minimized at a_hole={sub.loc[idx_min,'a_hole_um']:.0f}um "
              f"-> {sub.loc[idx_min, col]:.2f}um{edge_note}")
    print(f"  classical closed-form a* (#8) = {a_star_um:.1f}um")
    print(f"  numerical r_EE(0.5) optimum in swept range = {a_hole_numeric_opt:.0f}um")
    return out_path


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/r1_full_range_sweep.csv"
    df = pd.read_csv(csv_path)

    wavelength_nm = 550.0
    z_gap_mm = 12.0
    D_pupil_um = df["D_pupil_um"].iloc[0]
    M_values = sorted(df["M_diopters"].unique())

    for M in M_values:
        out_path = f"outputs/r1_sweep_M{int(M)}.png"
        plot_ee_vs_aperture(df, wavelength_nm, z_gap_mm, M, D_pupil_um, out_path)
        print(f"  -> saved {out_path}\n")


if __name__ == "__main__":
    main()
