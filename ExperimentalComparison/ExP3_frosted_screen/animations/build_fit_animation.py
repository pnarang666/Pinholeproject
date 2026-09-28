"""
ExperimentalComparison/ExP3_frosted_screen/animations/build_fit_animation.py

Animation 1: radius-vs-displacement curves for all 6 apertures + no-pinhole
control, drawn step-by-step (0->20mm), with each point's deviation
(residual) from that aperture's OWN linear fit shown live as a bar in a
side panel -- makes the 800um non-monotonic dip and the cross-aperture
slope-ordering mismatch visible as they happen, not just stated in text.

Reads ONLY measurements/all_spot_measurements.csv (already-verified,
corrected BT.601-grayscale measurements from analyze_exp3.py). Does not
re-measure or modify anything. Writes animations/fit_deviation_animation.mp4.

Run: python3 build_fit_animation.py
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
OUT_MP4 = os.path.join(HERE, "fit_deviation_animation.mp4")

APERTURES = [400, 500, 600, 800, 1000, 1400]
DISPLACEMENTS = [0, 5, 10, 15, 20]

COLOR_MEASURED = "#2C6E9E"
COLOR_FIT = "#E07B39"
COLOR_POS_DEV = "#4E9F3D"
COLOR_NEG_DEV = "#B23A48"
COLOR_CONTROL = "#8B5CF6"
INK = "#222222"

AP_COLORS = dict(zip(APERTURES, plt.cm.viridis(np.linspace(0.05, 0.9, len(APERTURES)))))

FRAMES_PER_STEP = 15   # smoothness of the "point appears" animation
HOLD_FRAMES = 20        # pause at the end of each aperture before moving on


def load_data():
    data = {}  # aperture(int or 'control') -> {disp: radius}
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            key = int(row["aperture_um"]) if row["series"] == "aperture" else "control"
            data.setdefault(key, {})[int(row["displacement_mm"])] = float(row["radius_px"])
    return data


def fit_line(xs, ys):
    slope, intercept = np.polyfit(xs, ys, 1)
    return slope, intercept


def main():
    data = load_data()
    keys = APERTURES + ["control"]

    fig = plt.figure(figsize=(11, 6.2))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1.4, 1], wspace=0.32, left=0.08, right=0.96, top=0.88, bottom=0.12)
    ax_main = fig.add_subplot(gs[0])
    ax_dev = fig.add_subplot(gs[1])

    all_radii_flat = [v for d in data.values() for v in d.values()]
    global_max_r = max(all_radii_flat)

    def get_key_label(k):
        return "no-pinhole control" if k == "control" else f"{k}µm aperture"

    def get_color(k):
        return COLOR_CONTROL if k == "control" else AP_COLORS[k]

    # total frame schedule: for each key, N_disp-1 growth segments * FRAMES_PER_STEP + HOLD
    segments_per_key = (len(DISPLACEMENTS) - 1) * FRAMES_PER_STEP + HOLD_FRAMES
    total_frames = segments_per_key * len(keys)

    def draw_frame(frame_idx):
        ax_main.clear()
        ax_dev.clear()

        key_idx = frame_idx // segments_per_key
        local_frame = frame_idx % segments_per_key
        current_key = keys[min(key_idx, len(keys) - 1)]

        # progress within current key's 4 growth segments
        seg_idx = min(local_frame // FRAMES_PER_STEP, len(DISPLACEMENTS) - 2)
        seg_frac = min(1.0, (local_frame - seg_idx * FRAMES_PER_STEP) / FRAMES_PER_STEP) if local_frame < (len(DISPLACEMENTS) - 1) * FRAMES_PER_STEP else 1.0
        n_full_points = seg_idx + 1  # points 0..seg_idx fully shown
        if local_frame >= (len(DISPLACEMENTS) - 1) * FRAMES_PER_STEP:
            n_full_points = len(DISPLACEMENTS)
            seg_frac = 1.0

        xs_full = DISPLACEMENTS[:n_full_points]
        ys_full = [data[current_key][d] for d in xs_full]

        # draw all PREVIOUSLY completed keys faded in the background for context
        for k in keys[:key_idx]:
            xs_k = DISPLACEMENTS
            ys_k = [data[k][d] for d in xs_k]
            ax_main.plot(xs_k, ys_k, "-", color=get_color(k), alpha=0.18, linewidth=1.3, zorder=1)

        # current key's points (with the partial next point interpolated for smooth growth)
        plot_xs = list(xs_full)
        plot_ys = list(ys_full)
        if n_full_points < len(DISPLACEMENTS) and seg_frac < 1.0:
            d_next = DISPLACEMENTS[n_full_points]
            r_next_full = data[current_key][d_next]
            r_prev = ys_full[-1]
            d_prev = xs_full[-1]
            interp_x = d_prev + seg_frac * (d_next - d_prev)
            interp_y = r_prev + seg_frac * (r_next_full - r_prev)
            plot_xs = plot_xs + [interp_x]
            plot_ys = plot_ys + [interp_y]

        ax_main.plot(plot_xs, plot_ys, "o-", color=get_color(current_key), linewidth=2.4,
                     markersize=7, zorder=3, label=get_key_label(current_key))

        # linear fit, drawn once at least 2 points exist
        if n_full_points >= 2:
            slope, intercept = fit_line(xs_full, ys_full)
            fit_xs = np.array([0, 20])
            ax_main.plot(fit_xs, slope * fit_xs + intercept, "--", color=COLOR_FIT, linewidth=1.6,
                         zorder=2, label=f"linear fit ({slope:.3f} px/mm)")

            # deviation bars: residual of each FULLY shown point from the current fit
            residuals = [ys_full[i] - (slope * xs_full[i] + intercept) for i in range(n_full_points)]
            bar_colors = [COLOR_POS_DEV if r >= 0 else COLOR_NEG_DEV for r in residuals]
            ax_dev.bar([str(d) for d in xs_full], residuals, color=bar_colors, width=0.55)
            for i, r in enumerate(residuals):
                ax_dev.text(i, r + (0.15 if r >= 0 else -0.15), f"{r:+.2f}", ha="center",
                            va="bottom" if r >= 0 else "top", fontsize=8)
            max_abs_dev = max(3.0, max(abs(r) for r in residuals) * 1.4)
            ax_dev.set_ylim(-max_abs_dev, max_abs_dev)
            ax_dev.axhline(0, color="#999999", linewidth=1)
            if not (n_full_points == len(DISPLACEMENTS) and any(
                    ys_full[i + 1] < ys_full[i] for i in range(len(ys_full) - 1))):
                pass
            # flag non-monotonic points explicitly
            for i in range(1, n_full_points):
                if ys_full[i] < ys_full[i - 1]:
                    ax_dev.text(i, residuals[i] + (2.0 if residuals[i] >= 0 else -2.0),
                                "NON-\nMONOTONIC", ha="center", fontsize=7.5, color=COLOR_NEG_DEV,
                                fontweight="bold")
        else:
            ax_dev.set_ylim(-3, 3)
            ax_dev.text(0.5, 0.5, "need >=2 points\nfor a fit", ha="center", va="center",
                        transform=ax_dev.transAxes, fontsize=9, color="#888")

        ax_dev.set_xlabel("displacement (mm)")
        ax_dev.set_ylabel("deviation from linear fit (px)")
        ax_dev.set_title("Residual vs. fit, live", fontsize=10)
        ax_dev.spines["top"].set_visible(False); ax_dev.spines["right"].set_visible(False)

        ax_main.set_xlim(-1, 21)
        ax_main.set_ylim(0, global_max_r * 1.08)
        ax_main.set_xlabel("screen displacement (mm)")
        ax_main.set_ylabel("measured spot radius (px)")
        ax_main.set_title(f"Frosted screen: radius vs. displacement -- {get_key_label(current_key)}",
                          fontsize=12, fontweight="bold")
        ax_main.spines["top"].set_visible(False); ax_main.spines["right"].set_visible(False)
        ax_main.legend(loc="upper left", frameon=False, fontsize=9)
        ax_main.grid(axis="y", color="#eaeaea", linewidth=0.6)

        fig.suptitle("ExP3 Frosted Screen -- Growth Curves and Fit Deviation", fontsize=13, fontweight="bold")

    writer = FFMpegWriter(fps=20, bitrate=3000)
    anim = FuncAnimation(fig, draw_frame, frames=total_frames, repeat=False)
    anim.save(OUT_MP4, writer=writer, dpi=140)
    plt.close(fig)
    print(f"wrote {OUT_MP4} ({total_frames} frames)")


if __name__ == "__main__":
    main()
