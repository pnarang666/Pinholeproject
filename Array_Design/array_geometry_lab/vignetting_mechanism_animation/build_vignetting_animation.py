"""
Array_Design/array_geometry_lab/vignetting_mechanism_animation/build_vignetting_animation.py

Animation: HOW vignetting happens for a single hole, as gaze eccentricity phi
sweeps 0 -> 16deg -> 0. Uses this project's own real geometry
(array_calculation/engine/vignetting_overlap.py, imported directly -- same
module build_blindness_animation.py in the sibling folder uses), not a
reimplementation.

Same R_p=2000um (4mm pupil, project constant), R_h=300um (600um hole,
representative mid-M aperture -- not tied to any specific winning design)
as make_vignetting_diagram.py in this folder, so the still and the animation
describe the same physical case.

Left panel: front view, pupil fixed in the drawing frame, hole shifts by
Delta(phi)=R_rot*sin(phi) (vignetting_overlap.pupil_shift_um), overlap area
shaded. Right panel: the same overlap-vs-shift curve as the static diagram,
with a moving marker at the current phi.

PHI_MAX=16deg is chosen so the sweep clears this R_h's zero-overlap boundary
(~11.8deg) with margin, while staying inside the formula's own validated
|phi|<=25deg range (vo.DEFAULT_PHI_VALID_DEG) -- so nothing here needs the
extrapolation flag that build_blindness_animation.py's phi=27deg segment
needs.

Writes: vignetting_mechanism_animation.mp4 (this folder only).
Run: python3 build_vignetting_animation.py
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation, FFMpegWriter

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LAB, "array_calculation", "engine"))
import vignetting_overlap as vo  # noqa: E402

OUT_MP4 = os.path.join(HERE, "vignetting_mechanism_animation.mp4")


R_P = 2000.0
R_H = 300.0
HOLE_AREA = np.pi * R_H ** 2
LO = abs(R_P - R_H)
HI = R_P + R_H
PHI_VALID_MAX = vo.DEFAULT_PHI_VALID_DEG

FPS = 24
PHI_MAX = 16.0  # deg


def regime_of(delta):
    if delta <= LO:
        return "FULL", "#2ecc71"
    if delta >= HI:
        return "ZERO", "#e74c3c"
    return "PARTIAL", "#e67e22"


DELTA_MAX = float(vo.pupil_shift_um(PHI_MAX))
extent = (DELTA_MAX + R_H) * 1.15
deltas_full = np.linspace(0, DELTA_MAX * 1.1, 500)
areas_full = vo.overlap_area_um2(deltas_full, R_P, R_H)

fig = plt.figure(figsize=(13, 6))
gs = gridspec.GridSpec(1, 2, width_ratios=[1, 1.15], wspace=0.25, left=0.04, right=0.97, top=0.82, bottom=0.13)
ax_front = fig.add_subplot(gs[0])
ax_curve = fig.add_subplot(gs[1])


N_SWEEP = FPS * 8
N_FRAMES = N_SWEEP


def draw_frame(i):
    ax_front.clear()
    ax_curve.clear()

    u = i / (N_FRAMES - 1)
    tri = 1 - abs(2 * u - 1)  # triangle wave: 0 -> 1 -> 0
    phi = PHI_MAX * tri

    delta = float(vo.pupil_shift_um(phi))
    area = float(vo.overlap_area_um2(delta, R_P, R_H))
    frac = area / HOLE_AREA
    regime, col = regime_of(delta)
    extrapolated = not vo.phi_in_validated_range(phi)

    ax_front.add_patch(plt.Circle((0, 0), R_P, facecolor="#eaf3ff", edgecolor="#1f6feb", lw=2.2, zorder=1))
    hx = -delta
    ax_front.add_patch(plt.Circle((hx, 0), R_H, facecolor="#333333", edgecolor="none", zorder=2, alpha=0.5))
    overlap_patch = plt.Circle((hx, 0), R_H, facecolor="#c0392b", edgecolor="none", zorder=3, alpha=0.8)
    ax_front.add_patch(overlap_patch)
    overlap_patch.set_clip_path(plt.Circle((0, 0), R_P, transform=ax_front.transData))


    ax_front.set_xlim(-extent, extent)
    ax_front.set_ylim(-extent, extent)
    ax_front.set_aspect("equal")
    ax_front.set_xticks([]); ax_front.set_yticks([])
    for s in ax_front.spines.values():
        s.set_visible(False)
    ax_front.set_title(f"phi = {phi:5.1f} deg   Delta = {delta:6.0f} um", fontsize=13, fontweight="bold")
    ax_front.text(0.5, -0.06, regime, transform=ax_front.transAxes, ha="center",
                   fontsize=14, fontweight="bold", color=col)
    ax_front.text(0.5, -0.14, f"illuminated fraction of this hole = {frac*100:.0f}%",
                   transform=ax_front.transAxes, ha="center", fontsize=11)
    if extrapolated:
        ax_front.text(0.5, 1.10, "beyond formula's 25 deg validated range", transform=ax_front.transAxes,
                       ha="center", fontsize=9, color="#e74c3c", fontweight="bold")

    ax_curve.axvspan(0, LO, color="#2ecc71", alpha=0.12)
    ax_curve.axvspan(LO, HI, color="#f39c12", alpha=0.12)
    ax_curve.axvspan(HI, deltas_full.max(), color="#e74c3c", alpha=0.10)
    ax_curve.plot(deltas_full, areas_full / HOLE_AREA * 100, color="#1f2937", lw=2.2)
    ax_curve.plot([delta], [frac * 100], "o", color=col, ms=13, zorder=6,
                   markeredgecolor="black", markeredgewidth=1)

    ax_curve.set_xlim(0, deltas_full.max())
    ax_curve.set_ylim(0, 108)
    ax_curve.set_xlabel("pupil-hole separation Delta (um)", fontsize=10.5)
    ax_curve.set_ylabel("illuminated fraction (%)", fontsize=10.5)
    ax_curve.set_title("Overlap area vs. pupil shift (vo.overlap_area_um2)", fontsize=12, fontweight="bold")
    ax_curve.grid(alpha=0.25)

    fig.suptitle("How Vignetting Happens: pupil shifts off-axis as gaze rotates,\n"
                 "a single hole's illumination tracks how much of it the pupil still covers",
                 fontsize=13.5, fontweight="bold", y=0.975)


def main():
    writer = FFMpegWriter(fps=FPS, bitrate=3000)
    anim = FuncAnimation(fig, draw_frame, frames=N_FRAMES, repeat=False)
    anim.save(OUT_MP4, writer=writer, dpi=140)
    plt.close(fig)
    print(f"wrote {OUT_MP4} ({N_FRAMES} frames, {N_FRAMES/FPS:.1f}s)")


if __name__ == "__main__":
    main()
