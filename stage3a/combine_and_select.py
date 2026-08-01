"""
Stage 3a: brightness-constrained optimum aperture.

Reads Stage 2's existing r1_full_range_sweep.csv (no new wave-optics simulation --
Stage 1/2 are not touched or re-run). Adds relative retinal illuminance (transmission.py)
per row, then re-derives the optimum aperture under a minimum-brightness constraint
instead of pure blur minimization:

    a*_practical(M, T_min) = argmin_{a_hole : E_rel(a_hole) >= T_min} r_EE_50(a_hole, M)

This tests one specific, cheap hypothesis directly: that the blur-only optimum (300-400
um) sits below the clinical/commercial range (0.94-1.75mm, ~1.2mm typical -- verified via
literature search, see README) because it is simply too dim to be usable, not because
the wave-optics blur calculation itself is wrong.

Usage:
    python3 combine_and_select.py
    python3 combine_and_select.py --csv ../stage2/outputs/r1_full_range_sweep.csv \
        --wavelength 650 --gap 15
"""

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from transmission import relative_illuminance

CLINICAL_BRACKET_UM = (940, 1750)  # 0.94-1.75mm, Review of Optometry, citing a dedicated
                                     # pinhole-size clinical study; most commercial
                                     # instruments ~1.2mm -- see README for citation.

p = argparse.ArgumentParser()
p.add_argument("--csv", default="../stage2/outputs/r1_full_range_sweep.csv")
p.add_argument("--wavelength", type=float, default=550.0)
p.add_argument("--gap", type=float, default=12.0)
p.add_argument("--m-for-fig1", type=float, default=4.0)
args = p.parse_args()

df = pd.read_csv(args.csv)
base = df[(np.isclose(df.wavelength_nm, args.wavelength)) & (np.isclose(df.z_gap_mm, args.gap))].copy()
base["E_rel"] = relative_illuminance(base.a_hole_um, base.D_pupil_um)
tag = f"wl{args.wavelength:g}nm_gap{args.gap:g}mm"

T_min_values = [0.0, 0.005, 0.01, 0.02, 0.03, 0.0625, 0.09, 0.1225, 0.16, 0.25]
Ms = sorted(base.M_diopters.unique())

rows = []
for M in Ms:
    sub = base[base.M_diopters == M].sort_values("a_hole_um")
    for Tmin in T_min_values:
        cand = sub[sub.E_rel >= Tmin]
        if len(cand) == 0:
            rows.append({"M_diopters": M, "T_min": Tmin, "a_star_um": np.nan, "r_EE_50_um": np.nan})
            continue
        imin = cand.r_EE_50_retina_um.idxmin()
        rows.append({"M_diopters": M, "T_min": Tmin,
                     "a_star_um": cand.loc[imin, "a_hole_um"],
                     "r_EE_50_um": cand.loc[imin, "r_EE_50_retina_um"]})

result = pd.DataFrame(rows)
result.to_csv(f"stage3a_constrained_optimum_{tag}.csv", index=False)
print(f"Saved stage3a_constrained_optimum_{tag}.csv\n")
print("a*_practical(M, T_min), um:")
print(result.pivot(index="T_min", columns="M_diopters", values="a_star_um"))

# Figure 1: blur vs aperture with illuminance overlay, one representative M
fig, ax1 = plt.subplots(figsize=(9, 6))
sub = base[base.M_diopters == args.m_for_fig1].sort_values("a_hole_um")
ax1.plot(sub.a_hole_um, sub.r_EE_50_retina_um, "o-", color="#2a78d6", label="r_EE(50%) blur radius")
ax1.set_xscale("log")
ax1.set_xlabel("aperture diameter a_hole (um), log scale")
ax1.set_ylabel("retinal blur radius, r_EE(50%) (um)", color="#2a78d6")
ax1.tick_params(axis="y", labelcolor="#2a78d6")
ax1.axvspan(*CLINICAL_BRACKET_UM, color="green", alpha=0.08, label="clinical bracket (0.94-1.75mm)")
ax2 = ax1.twinx()
ax2.plot(sub.a_hole_um, sub.E_rel * 100, "s--", color="#e34948", label="relative illuminance E_rel")
ax2.set_ylabel("relative retinal illuminance (% of full pupil)", color="#e34948")
ax2.tick_params(axis="y", labelcolor="#e34948")
imin = sub.r_EE_50_retina_um.idxmin()
ax1.plot(sub.loc[imin, "a_hole_um"], sub.loc[imin, "r_EE_50_retina_um"], "*",
          color="#2a78d6", ms=18, mec="black", label="blur-only optimum")
fig.suptitle(f"Blur vs. brightness tradeoff (M={args.m_for_fig1:g}D, {tag})\n"
             f"blur-only optimum sits well left of the clinical bracket, where E_rel < 1%")
l1, lb1 = ax1.get_legend_handles_labels()
l2, lb2 = ax2.get_legend_handles_labels()
ax1.legend(l1 + l2, lb1 + lb2, loc="upper center", fontsize=8)
ax1.grid(alpha=0.3, which="both")
fig.tight_layout()
fig.savefig(f"stage3a_fig1_blur_vs_brightness_{tag}.png", dpi=150)

# Figure 2: constrained optimum vs T_min, all M
fig, ax = plt.subplots(figsize=(9, 6))
colors = cm.viridis(np.linspace(0, 0.9, len(Ms)))
for M, c in zip(Ms, colors):
    s = result[result.M_diopters == M].sort_values("T_min")
    ax.plot(s.T_min * 100, s.a_star_um, "o-", color=c, label=f"M={M:g}D")
ax.axhspan(*CLINICAL_BRACKET_UM, color="green", alpha=0.08, label="clinical bracket (0.94-1.75mm)")
ax.set_xlabel("minimum acceptable relative illuminance, T_min (%)")
ax.set_ylabel("constrained optimum aperture a*_practical (um)")
ax.set_title("Optimum aperture vs brightness floor\n"
              "a modest T_min (~6-9%) alone moves the optimum into the clinical bracket")
ax.legend(fontsize=8, ncol=2)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(f"stage3a_fig2_optimum_vs_Tmin_{tag}.png", dpi=150)
print(f"\nSaved stage3a_fig1_blur_vs_brightness_{tag}.png and stage3a_fig2_optimum_vs_Tmin_{tag}.png")
