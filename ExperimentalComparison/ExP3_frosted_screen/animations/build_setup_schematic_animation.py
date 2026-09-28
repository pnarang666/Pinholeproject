"""
ExperimentalComparison/ExP3_frosted_screen/animations/build_setup_schematic_animation.py

Animation 3: a SCHEMATIC of the physical experimental setup itself -- point
source, fixed pinhole aperture, frosted screen sliding away along the optical
axis -- explaining HOW the experiment produces the measured growth, as a
companion to the data-curve animation (build_fit_animation.py) and the
real-photo animation (build_photo_animation.py) already built.

EXPLICITLY NOT TO PHYSICAL SCALE, labeled as such on every frame: the real
aperture sizes (400-1400um) and screen displacements (0-20mm) differ by
~4 orders of magnitude, so a true-to-scale diagram would show an
invisible pinhole; the diagram is exaggerated for legibility, the same way
this project's own ASM diffraction-pattern figures already are (see
stage2/outputs/stage2_retinal_images_comparison.png's own axis scaling).
The right-hand panel's spot RADIUS is the one quantity kept numerically real
-- taken directly from measurements/all_spot_measurements.csv, not invented.

Reads measurements/all_spot_measurements.csv read-only. Writes
animations/setup_schematic_animation.mp4.

Run: python3 build_setup_schematic_animation.py
"""
import os
import csv

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation, FFMpegWriter

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
CSV_PATH = os.path.join(LAB, "measurements", "all_spot_measurements.csv")
OUT_MP4 = os.path.join(HERE, "setup_schematic_animation.mp4")

APERTURES = [400, 500, 600, 800, 1000, 1400]
DISPLACEMENTS = [0, 5, 10, 15, 20]

COLOR_SOURCE = "#F5A623"
COLOR_PLATE = "#444444"
COLOR_RAY = "#2C6E9E"
COLOR_SCREEN = "#7A5C3E"
COLOR_SPOT = "#3B7DD8"
COLOR_CONTROL_RAY = "#B23A48"
INK = "#222222"

FRAMES_PER_MOVE = 30    # frames for the screen to slide from one displacement to the next
HOLD_FRAMES = 20        # pause once the screen reaches each displacement

SOURCE_X = 0.0
PLATE_X = 3.0
SCREEN_X_AT_0MM = 5.0
SCREEN_X_AT_20MM = 9.5   # exaggerated travel for visibility -- NOT to scale, labeled

AP_GAP_HALF = dict(zip(APERTURES, np.linspace(0.55, 1.35, len(APERTURES))))  # schematic gap sizes
CONTROL_GAP_HALF = 2.6   # no plate restriction at all -- drawn as a fully open frame edge


def load_data():
    data = {}
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            key = int(row["aperture_um"]) if row["series"] == "aperture" else "control"
            data.setdefault(key, {})[int(row["displacement_mm"])] = float(row["radius_px"])
    return data


def screen_x_for(disp_mm):
    frac = disp_mm / 20.0
    return SCREEN_X_AT_0MM + frac * (SCREEN_X_AT_20MM - SCREEN_X_AT_0MM)


def main():
    data = load_data()
    keys = APERTURES + ["control"]

    fig = plt.figure(figsize=(11.5, 6.2))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1.6, 1], wspace=0.28, left=0.05, right=0.97, top=0.80, bottom=0.10)
    ax_side = fig.add_subplot(gs[0])
    ax_front = fig.add_subplot(gs[1])

    global_max_r = max(v for d in data.values() for v in d.values())

    def label(k):
        return "no-pinhole control (unrestricted beam)" if k == "control" else f"{k}µm pinhole aperture"

    n_moves = len(DISPLACEMENTS) - 1
    frames_per_key = n_moves * (FRAMES_PER_MOVE + HOLD_FRAMES) + HOLD_FRAMES
    total_frames = frames_per_key * len(keys)

    def draw_frame(frame_idx):
        ax_side.clear(); ax_front.clear()
        key_idx = frame_idx // frames_per_key
        local = frame_idx % frames_per_key
        key = keys[min(key_idx, len(keys) - 1)]
        is_control = (key == "control")
        gap_half = CONTROL_GAP_HALF if is_control else AP_GAP_HALF[key]

        # figure out which displacement segment we're in and interpolation fraction
        seg = min(local // (FRAMES_PER_MOVE + HOLD_FRAMES), n_moves - 1) if local < frames_per_key - HOLD_FRAMES else n_moves - 1
        local_in_seg = local - seg * (FRAMES_PER_MOVE + HOLD_FRAMES)
        move_frac = min(1.0, local_in_seg / FRAMES_PER_MOVE)
        if local >= frames_per_key - HOLD_FRAMES:
            seg = n_moves - 1
            move_frac = 1.0

        d0 = DISPLACEMENTS[seg]
        d1 = DISPLACEMENTS[seg + 1]
        disp_now = d0 + move_frac * (d1 - d0)
        r0 = data[key][d0]
        r1 = data[key][d1]
        radius_now = r0 + move_frac * (r1 - r0)
        nearest_disp = d0 if move_frac < 0.5 else d1

        sx = screen_x_for(disp_now)

        # Illuminated-spot visual size is tied DIRECTLY to the real measured radius
        # (normalized against this key's OWN max over its sweep) -- bounded, so it
        # can never saturate the screen bar regardless of the schematic ray angle
        # drawn below. This is the one quantity in this diagram kept numerically
        # real; the ray-cone angle itself is a fixed illustrative divergence, not
        # derived from true (invisibly small) optical angles -- see module docstring.
        max_r_key = max(data[key].values())
        norm = radius_now / max_r_key
        spot_half_h_side = 0.45 + 2.0 * norm   # bounded well inside the 3.0 screen half-height
        front_r_norm = 0.15 + 0.85 * norm      # bounded well inside the front-view axis limits

        # ---------------- side-view schematic ----------------
        ax_side.set_xlim(-0.6, 10.5)
        ax_side.set_ylim(-3.6, 3.6)
        ax_side.axis("off")

        # optical axis
        ax_side.plot([SOURCE_X, SCREEN_X_AT_20MM + 0.6], [0, 0], color="#cccccc", linewidth=1, linestyle=":", zorder=1)

        # point source
        ax_side.plot([SOURCE_X], [0], marker="*", markersize=22, color=COLOR_SOURCE, zorder=5)
        ax_side.text(SOURCE_X, -0.55, "point\nsource", ha="center", fontsize=8.5, color=INK)

        if not is_control:
            # opaque plate with a gap (pinhole), drawn as two blocking bars
            plate_h = 3.0
            ax_side.add_patch(plt.Rectangle((PLATE_X - 0.06, gap_half), 0.12, plate_h - gap_half,
                                             color=COLOR_PLATE, zorder=4))
            ax_side.add_patch(plt.Rectangle((PLATE_X - 0.06, -plate_h), 0.12, plate_h - gap_half,
                                             color=COLOR_PLATE, zorder=4))
            ax_side.text(PLATE_X, plate_h + 0.35, f"pinhole plate\n({key}µm aperture)",
                        ha="center", va="bottom", fontsize=8.5, color=INK)
            # rays: source -> aperture edges -> screen, aimed at the (real-data-driven) spot extent
            for edge_sign in (+1, -1):
                ax_side.plot([SOURCE_X, PLATE_X], [0, edge_sign * gap_half], color=COLOR_RAY, linewidth=1.3, zorder=2)
                ax_side.plot([PLATE_X, sx], [edge_sign * gap_half, edge_sign * spot_half_h_side], color=COLOR_RAY,
                            linewidth=1.3, zorder=2, linestyle="--")
        else:
            # unrestricted: rays diverge directly from the source, aimed at the (real-data-driven) spot extent
            for edge_sign in (+1, -1):
                ax_side.plot([SOURCE_X, sx], [0, edge_sign * spot_half_h_side], color=COLOR_CONTROL_RAY, linewidth=1.3,
                            zorder=2, linestyle="--")
            ax_side.text(PLATE_X, 3.35, "(no pinhole plate --\nbeam unrestricted)",
                        ha="center", va="bottom", fontsize=8.5, color=COLOR_CONTROL_RAY, style="italic")

        # frosted screen (a vertical bar sliding along the axis)
        ax_side.add_patch(plt.Rectangle((sx - 0.05, -3.0), 0.10, 6.0, color=COLOR_SCREEN, alpha=0.85, zorder=3))
        # illuminated extent on the screen (thick highlighted segment, real-data-driven)
        ax_side.plot([sx, sx], [-spot_half_h_side, spot_half_h_side], color=COLOR_SPOT, linewidth=6, zorder=6,
                    solid_capstyle="butt", alpha=0.85)
        ax_side.text(sx, -3.15, f"screen\n@ {disp_now:.1f} mm", ha="center", va="top", fontsize=8.5, color=INK)

        ax_side.set_title(label(key), fontsize=11.5, fontweight="bold", pad=14)

        # ---------------- front-view: real measured spot ----------------
        ax_front.set_xlim(-1.3, 1.3)
        ax_front.set_ylim(-1.3, 1.3)
        ax_front.set_aspect("equal")
        ax_front.axis("off")
        circ = plt.Circle((0, 0), front_r_norm, color=COLOR_SPOT, alpha=0.85, zorder=3)
        ax_front.add_patch(circ)
        ax_front.add_patch(plt.Circle((0, 0), 1.0, fill=False, edgecolor="#dddddd", linewidth=1, linestyle=":"))
        ax_front.text(0, -1.18, "(circle size scaled to THIS aperture's own\n0-20mm range, for visibility -- real px value below)",
                     ha="center", fontsize=7.3, color="#888")
        ax_front.set_title("Spot on screen (real measurement)", fontsize=11, fontweight="bold", pad=14)
        ax_front.text(0.5, -0.08, f"measured radius = {radius_now:.2f} px\n(at displacement {nearest_disp} mm)",
                     transform=ax_front.transAxes, ha="center", fontsize=10.5, color=INK)

    # STATIC figure-level text, drawn ONCE outside draw_frame() -- NOT per-frame.
    # BUG FOUND AND FIXED: fig.text() (unlike ax.clear()) is never removed by
    # clearing the axes -- calling it inside draw_frame() silently appended a
    # new overlapping Text artist to fig.texts on every single frame (1540
    # of them by the end), forcing matplotlib to lay out and render an
    # ever-growing pile of identical stacked text every subsequent frame --
    # an O(n^2) blowup that is the actual reason the first rebuild ran ~5x
    # slower than the original version (which never had this call in the
    # per-frame path). fig.suptitle() was NOT part of this bug -- matplotlib
    # tracks and replaces its own suptitle internally on repeated calls.
    fig.suptitle("ExP3 Frosted Screen -- How the Experiment Works", fontsize=14, fontweight="bold", y=0.985)
    fig.text(0.5, 0.905, "Fixed-lens/moving-screen defocus sweep -- schematic of the physical setup, NOT to physical scale",
             ha="center", fontsize=9, color="#555")

    writer = FFMpegWriter(fps=25, bitrate=3500)
    anim = FuncAnimation(fig, draw_frame, frames=total_frames, repeat=False)
    anim.save(OUT_MP4, writer=writer, dpi=140)
    plt.close(fig)
    print(f"wrote {OUT_MP4} ({total_frames} frames)")


if __name__ == "__main__":
    main()
