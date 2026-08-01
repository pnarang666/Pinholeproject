"""
Two-panel figure: (A) plain blur-vs-aperture, unconstrained -- reproduces Stage 2's
original 300-400um result; (B) same curves with the brightness floor applied --
infeasible (too-dim) region shaded/faded, constrained optimum re-marked.

Usage: python3 plot_blur_then_constraint.py [--T-min 0.0625]
"""
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from transmission import relative_illuminance

p = argparse.ArgumentParser()
p.add_argument("--csv", default="multi_EE_sweep.csv")
p.add_argument("--T-min", type=float, default=0.0625,
                help="brightness floor as fraction of full-pupil illuminance (default "
                     "6.25%%, the value that lands the optimum in the clinical bracket)")
p.add_argument("--D-pupil-um", type=float, default=4000.0)
args = p.parse_args()

df = pd.read_csv(args.csv)
df["E_rel"] = relative_illuminance(df.a_hole_um, args.D_pupil_um)
Ms = sorted(df.M_diopters.unique())
colors = cm.viridis(np.linspace(0, 0.9, len(Ms)))
T_MIN = args.T_min

fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

ax = axes[0]
for M, c in zip(Ms, colors):
    sub = df[df.M_diopters == M].sort_values("a_hole_um")
    ax.plot(sub.a_hole_um, sub.r_EE_50_um, "o-", color=c, ms=4, label=f"M={M:g}D")
    imin = sub.r_EE_50_um.idxmin()
    ax.plot(sub.loc[imin, "a_hole_um"], sub.loc[imin, "r_EE_50_um"], "*", color=c, ms=16, mec="black", mew=0.6)
ax.set_xscale("log")
ax.set_xlabel("aperture diameter a_hole (um), log scale")
ax.set_ylabel("r_EE(50%) retinal blur radius (um)")
ax.set_title("A. Blur vs aperture (unconstrained)\nstars = blur-only optimum")
ax.legend(fontsize=8, ncol=2)
ax.grid(alpha=0.3, which="both")

ax = axes[1]
a_min_feasible = args.D_pupil_um * np.sqrt(T_MIN)
for M, c in zip(Ms, colors):
    sub = df[df.M_diopters == M].sort_values("a_hole_um")
    infeasible = sub[sub.E_rel < T_MIN]
    feasible = sub[sub.E_rel >= T_MIN]
    ax.plot(infeasible.a_hole_um, infeasible.r_EE_50_um, "o--", color=c, ms=4, alpha=0.3)
    ax.plot(feasible.a_hole_um, feasible.r_EE_50_um, "o-", color=c, ms=4, label=f"M={M:g}D")
    if len(feasible):
        imin = feasible.r_EE_50_um.idxmin()
        ax.plot(feasible.loc[imin, "a_hole_um"], feasible.loc[imin, "r_EE_50_um"], "*",
                 color=c, ms=16, mec="black", mew=0.6)
ax.axvspan(0, a_min_feasible, color="red", alpha=0.08)
ax.axvline(a_min_feasible, color="red", ls=":", lw=1.5)
ax.text(a_min_feasible * 1.05, ax.get_ylim()[1] * 0.92, f"infeasible\n(E_rel < {T_MIN*100:.1f}%)",
         color="darkred", fontsize=8, va="top")
ax.set_xscale("log")
ax.set_xlabel("aperture diameter a_hole (um), log scale")
ax.set_title(f"B. Same curves, brightness floor applied (T_min={T_MIN*100:.2f}%)\n"
             f"faded/dashed = excluded as too dim; stars = constrained optimum")
ax.legend(fontsize=8, ncol=2)
ax.grid(alpha=0.3, which="both")

fig.suptitle("Blur-only optimization vs brightness-constrained optimization", y=1.02)
fig.tight_layout()
out = f"stage3a_fig4_blur_then_constraint_Tmin{T_MIN:.4f}.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"saved {out}")
