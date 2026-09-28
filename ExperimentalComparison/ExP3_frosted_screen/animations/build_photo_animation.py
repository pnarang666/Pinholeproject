"""
ExperimentalComparison/ExP3_frosted_screen/animations/build_photo_animation.py

Animation 2: cycles through the REAL frosted-screen photos (0,5,10,15,20mm)
for each of the 6 apertures + no-pinhole control, with the measured spot
circle, radius, and deviation-from-linear-fit drawn directly on each frame.

Reads measurements/all_spot_measurements.csv (already-verified BT.601
measurements) and the original JPGs in ExP3/Frosted screen / (read-only,
never modified). Writes animations/photo_cycle_animation.mp4.

Run: python3 build_photo_animation.py
"""
import os
import csv

import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
CSV_PATH = os.path.join(LAB, "measurements", "all_spot_measurements.csv")
SRC_DIR = "/Users/parikshitnarang/Pinholeproject/ExP3/Frosted screen "
OUT_MP4 = os.path.join(HERE, "photo_cycle_animation.mp4")

APERTURES = [400, 500, 600, 800, 1000, 1400]
DISPLACEMENTS = [0, 5, 10, 15, 20]
HOLD_SECONDS = 1.1
FPS = 20
HOLD_FRAMES = int(HOLD_SECONDS * FPS)

COLOR_CIRCLE = "#FF3B30"
COLOR_POS = "#7ED957"
COLOR_NEG = "#FF6B6B"


def load_rows():
    rows = {}  # key(aperture or 'control') -> {disp: row dict}
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            key = int(row["aperture_um"]) if row["series"] == "aperture" else "control"
            rows.setdefault(key, {})[int(row["displacement_mm"])] = row
    return rows


def fit_line(xs, ys):
    slope, intercept = np.polyfit(xs, ys, 1)
    return slope, intercept


def load_downsized(path, target_w=700):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    scale = target_w / w
    return cv2.resize(img, (target_w, int(h * scale)), interpolation=cv2.INTER_AREA), scale


def main():
    rows = load_rows()
    keys = APERTURES + ["control"]

    frame_list = []  # (key, disp) pairs, repeated HOLD_FRAMES times each
    for key in keys:
        for disp in DISPLACEMENTS:
            frame_list.extend([(key, disp)] * HOLD_FRAMES)

    fig, ax = plt.subplots(figsize=(8, 7.2))
    plt.subplots_adjust(top=0.90, bottom=0.06, left=0.04, right=0.96)

    def label(k):
        return "no-pinhole control" if k == "control" else f"{k}µm aperture"

    cache = {}

    def draw_frame(idx):
        ax.clear()
        ax.axis("off")
        key, disp = frame_list[idx]
        cache_key = (key, disp)
        row = rows[key][disp]
        fname = row["filename"]
        path = os.path.join(SRC_DIR, fname)
        if cache_key not in cache:
            img, scale = load_downsized(path)
            cache[cache_key] = (img, scale)
        img, scale = cache[cache_key]

        ax.imshow(img)
        cx = float(row["centroid_x"]) * scale
        cy = float(row["centroid_y"]) * scale
        r = float(row["radius_px"]) * scale
        circ = plt.Circle((cx, cy), r, fill=False, edgecolor=COLOR_CIRCLE, linewidth=2.2)
        ax.add_patch(circ)
        ax.plot([cx], [cy], "+", color=COLOR_CIRCLE, markersize=10, markeredgewidth=2)

        # deviation from this key's own full-series linear fit
        xs_all = DISPLACEMENTS
        ys_all = [float(rows[key][d]["radius_px"]) for d in xs_all]
        slope, intercept = fit_line(xs_all, ys_all)
        pred = slope * disp + intercept
        actual = float(row["radius_px"])
        residual = actual - pred
        dev_color = COLOR_POS if residual >= 0 else COLOR_NEG

        flag_text = ""
        if row.get("flags"):
            flag_text = f"\nflag: {row['flags']}"

        info = (f"{label(key)}   |   displacement = {disp} mm\n"
                f"measured radius = {actual:.2f} px   |   fit-predicted = {pred:.2f} px\n"
                f"deviation from linear fit = {residual:+.2f} px{flag_text}")
        ax.text(0.5, -0.05, info, transform=ax.transAxes, ha="center", va="top",
                fontsize=10.5, color="#222")
        ax.text(0.5, -0.05, "\n\n\n", transform=ax.transAxes)  # spacer for layout stability

        fig.suptitle(f"ExP3 Frosted Screen -- Real Photos with Live Deviation Overlay",
                     fontsize=13, fontweight="bold", y=0.975)
        ax.text(0.02, 0.98, f"deviation: {residual:+.2f} px", transform=ax.transAxes,
                fontsize=11, color="white", fontweight="bold", va="top",
                bbox=dict(facecolor=dev_color, alpha=0.85, boxstyle="round,pad=0.3"))

    writer = FFMpegWriter(fps=FPS, bitrate=4000)
    anim = FuncAnimation(fig, draw_frame, frames=len(frame_list), repeat=False)
    anim.save(OUT_MP4, writer=writer, dpi=130)
    plt.close(fig)
    print(f"wrote {OUT_MP4} ({len(frame_list)} frames)")


if __name__ == "__main__":
    main()
