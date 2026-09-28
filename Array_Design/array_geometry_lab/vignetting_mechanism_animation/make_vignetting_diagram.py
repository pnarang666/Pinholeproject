"""
Array_Design/array_geometry_lab/vignetting_mechanism_animation/make_vignetting_diagram.py

Static explainer: HOW vignetting happens for a single hole, as the pupil shifts
off-axis with gaze eccentricity phi. Uses this project's own real geometry
(array_calculation/engine/vignetting_overlap.py, imported directly -- not
reimplemented), same Chapter 13 formulas validated there against Monte Carlo
(max error 0.177 percentage points of hole area, 72 test points).

R_p = 2000um (4mm pupil, project constant). R_h = 300um (600um hole diameter,
a representative mid-M aperture) -- chosen only because it gives clean, visible
regime transitions well inside the validated |phi|<=25deg range; not tied to
any specific winning design.

Three panels show the three overlap regimes (full containment / partial lens
overlap / zero overlap) at the gaze angles where this particular R_p,R_h pair
crosses each boundary, plus a bottom panel of the full overlap-vs-shift curve
with those three points marked.

Writes: vignetting_mechanism_diagram.png (this folder only).
Run: python3 make_vignetting_diagram.py
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LAB, "array_calculation", "engine"))
import vignetting_overlap as vo  # noqa: E402

OUT_PNG = os.path.join(HERE, "vignetting_mechanism_diagram.png")

R_P = 2000.0
R_H = 300.0
LO = abs(R_P - R_H)
HI = R_P + R_H


def phi_for_delta(delta_um, R_rot_mm=vo.DEFAULT_R_ROT_MM):
    s = np.clip(delta_um / (R_rot_mm * 1000.0), -1.0, 1.0)
    return np.degrees(np.arcsin(s))

phi_lo = phi_for_delta(LO)
phi_hi = phi_for_delta(HI)

cases = [
    dict(phi=0.0, label="phi = 0 deg  (straight ahead)",
         regime="FULL - hole entirely inside pupil"),
    dict(phi=(phi_lo + phi_hi) / 2, label=f"phi = {(phi_lo+phi_hi)/2:.1f} deg  (mid gaze)",
         regime="PARTIAL - lens-shaped overlap"),
    dict(phi=phi_hi + 2.0, label=f"phi = {phi_hi+2.0:.1f} deg  (large gaze)",
         regime="ZERO - hole fully outside pupil"),
]

fig = plt.figure(figsize=(15, 8.5))
gs = gridspec.GridSpec(2, 3, height_ratios=[1.15, 0.85], hspace=0.42, wspace=0.15,
                        left=0.045, right=0.98, top=0.88, bottom=0.09)
extent = R_P * 1.7


for i, c in enumerate(cases):
    ax = fig.add_subplot(gs[0, i])
    delta = vo.pupil_shift_um(c["phi"])
    area = float(vo.overlap_area_um2(delta, R_P, R_H))
    hole_area = np.pi * R_H ** 2
    frac = area / hole_area

    ax.add_patch(plt.Circle((0, 0), R_P, facecolor="#eaf3ff", edgecolor="#1f6feb", lw=2.2, zorder=1))
    hx = -delta
    ax.add_patch(plt.Circle((hx, 0), R_H, facecolor="#333333", edgecolor="none", zorder=2, alpha=0.55))
    overlap_patch = plt.Circle((hx, 0), R_H, facecolor="#c0392b", edgecolor="none", zorder=3, alpha=0.75)
    ax.add_patch(overlap_patch)
    overlap_patch.set_clip_path(plt.Circle((0, 0), R_P, transform=ax.transData))

    ax.set_xlim(-extent, extent)
    ax.set_ylim(-extent, extent)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_title(f"{c['label']}\nDelta = {delta:.0f} um", fontsize=11, fontweight="bold")
    ax.text(0.5, -0.08, c["regime"], transform=ax.transAxes, ha="center", fontsize=10.5,
            fontweight="bold", color="#c0392b")
    ax.text(0.5, -0.16, f"illuminated fraction of this hole = {frac*100:.0f}%",
            transform=ax.transAxes, ha="center", fontsize=9.5, color="#333")

    if i == 0:
        ax.legend(loc="lower left", fontsize=8, frameon=False, handles=[
            mpatches.Patch(facecolor="#eaf3ff", edgecolor="#1f6feb", label="pupil (4mm, fixed frame)"),
            mpatches.Patch(facecolor="#333333", alpha=0.55, label="pinhole (fixed to array/frame)"),
            mpatches.Patch(facecolor="#c0392b", alpha=0.75, label="overlap = light reaching retina"),
        ])


ax2 = fig.add_subplot(gs[1, :])
deltas = np.linspace(0, R_P + R_H + 400, 500)
areas = vo.overlap_area_um2(deltas, R_P, R_H)
hole_area = np.pi * R_H ** 2
ax2.axvspan(0, LO, color="#2ecc71", alpha=0.12)
ax2.axvspan(LO, HI, color="#f39c12", alpha=0.12)
ax2.axvspan(HI, deltas.max(), color="#e74c3c", alpha=0.10)
ax2.plot(deltas, areas / hole_area * 100, color="#1f2937", lw=2.4)
ax2.axvline(LO, color="#888", ls="--", lw=1)
ax2.axvline(HI, color="#888", ls="--", lw=1)
ax2.text(LO/2, 104, "FULL\n(100% lit)", ha="center", fontsize=9, color="#2ecc71", fontweight="bold")
ax2.text((LO+HI)/2, 104, "PARTIAL\n(vignetted)", ha="center", fontsize=9, color="#e67e22", fontweight="bold")
ax2.text((HI+deltas.max())/2, 104, "ZERO\n(blind, this hole)", ha="center", fontsize=9, color="#e74c3c", fontweight="bold")

for c in cases:
    delta = vo.pupil_shift_um(c["phi"])
    area = float(vo.overlap_area_um2(delta, R_P, R_H))
    ax2.plot([delta], [area/hole_area*100], "o", color="#1f6feb", ms=9, zorder=5)

ax2.set_ylim(0, 115)
ax2.set_xlim(0, deltas.max())
ax2.set_xlabel("pupil-hole center separation  Delta(phi) = R_rot . sin(phi)   (um)", fontsize=10.5)
ax2.set_ylabel("illuminated fraction of hole (%)", fontsize=10.5)
ax2.set_title("Overlap area vs. pupil shift -- vo.overlap_area_um2, this project's own validated formula",
              fontsize=11.5, fontweight="bold")
ax2.grid(alpha=0.25)


fig.suptitle("How Vignetting Happens: the pupil disc shifts off-axis with gaze angle phi,\n"
             "and each hole's illumination is set by how much of it still overlaps the pupil",
             fontsize=14, fontweight="bold", y=0.985)

fig.savefig(OUT_PNG, dpi=200)
print("saved", OUT_PNG)
