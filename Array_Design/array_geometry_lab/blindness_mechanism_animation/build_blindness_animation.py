"""
Array_Design/array_geometry_lab/blindness_mechanism_animation/build_blindness_animation.py

Animation: HOW "blinding" occurs in a pinhole array, as the eye's gaze rotates
through multiple gaze ANGLES -- both senses of "angle" that this project's own
gaze-weighted model (array_calculation/compute_gaze_weighted_metrics.py) uses:
  (1) eccentricity phi (how far the eye has rotated off the array's optical axis)
  (2) azimuth theta (WHICH direction it rotated in, at a given eccentricity)

MECHANISM (exactly this project's own physics, not reinvented): the eye's pupil
(diameter D_PUPIL_UM, real project constant) is a fixed-size disc. As the eye
rotates by phi, the pupil's center shifts laterally relative to the (fixed,
head-mounted) hole array by R = pupil_shift_um(phi, R_rot_mm) = R_rot*sin(phi)
(array_calculation/engine/vignetting_overlap.py, Handbook 2 Sec 13.1), in an
arbitrary azimuth theta. At each (phi, theta), light only reaches the retina
through whichever holes' discs still overlap the shifted pupil disc
(overlap_area_um2(), Handbook 2 Sec 13.2). is_blind = zero holes overlap at all
(total illuminated area = 0) -- literally no light reaches the retina at that
gaze direction. is_ghost = >=2 holes each cover >=50% of their own area inside
the pupil (DEFAULT_ACTIVE_FRAC_THRESHOLD, margins/active_pairs.py) -- two
separated, potentially double images. This animation renders BOTH real,
already-evaluated candidates from array_data/theoretical_data/gaze_weighted_metrics.csv,
side by side, sweeping the SAME (phi, theta) path for each so the mechanism is
directly comparable:

  Case A -- archimedean_spiral, M=4D, N=50, a_hole_um=600, c_um=2000 (no seed).
            REAL, EVALUATED, REJECTED candidate: time_weighted_blind_pct=90.79%,
            time_weighted_ghost_pct=4.63% -- the concrete instance of this
            project's own documented "rewards blindness" degenerate pattern
            (GAZE_WEIGHTED_APPROACH.md). Regenerated via
            array_calculation/generators/archimedean_spiral.generate(), the
            exact function the sweep itself used -- not redrawn by hand.
  Case B -- hexagonal, M=8D, a_hole_um=400, the PRIMARY-RANKING SHIPPED WINNER
            for M=8D (array_data/evaluation_results/PRIMARY_WINNER_PER_M.csv).
            Coordinates read directly from the fabrication package's own
            hole_coordinates_M8.0.csv (mm -> um) -- the literal array this
            project would cut. time_weighted_blind_pct=0.33%,
            time_weighted_ghost_pct=0.0%.

FRONT-VIEW PANELS ARE TRUE TO RELATIVE SCALE: real hole coordinates and real
pupil diameter, both in micrometres -- unlike ExP3's setup-schematic animation,
which was deliberately exaggerated for legibility (see that script's own
docstring). No invented geometry here.

EXTRAPOLATION FLAG: the animation sweeps phi up to 27deg, matching this
project's own EXTRAPOLATED_BIN_DEG=27.0 in compute_gaze_weighted_metrics.py --
outside vignetting_overlap.DEFAULT_PHI_VALID_DEG=25deg. Flagged on-screen
during that segment, exactly as compute_gaze_weighted_metrics.py's own
docstring requires of every caller ("every caller that reports a number must
check and flag this, not silently trust it").

PACING IS REAL: the phi ramp is paced by this project's own empirically
measured eccentricity time-weights (GAZE_BINS, copied verbatim from
compute_gaze_weighted_metrics.py) via an inverse-CDF mapping -- more real
animation-seconds are spent at low eccentricity (where the eye actually
spends most of its viewing time) than at high eccentricity, not a uniform
sweep.

The small "running fraction blind/ghost so far" counters shown during the
sweep are a frame-sampling tally over THIS animation's own path -- explicitly
labelled as illustrative, NOT a re-derivation of the project's real
time-weighted metric (which integrates over the full 26-bin x 36-azimuth grid,
reported once per case in the title/closing cards instead).

Reads (read-only): array_data/theoretical_data/gaze_weighted_metrics.csv,
array_data/evaluation_results/PRIMARY_WINNER_PER_M.csv,
fabrication_package/hole_coordinates/hole_coordinates_M8.0.csv.
Writes: blindness_mechanism_animation.mp4 (this folder only).

Run: python3 build_blindness_animation.py
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation, FFMpegWriter

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)  # array_geometry_lab/
sys.path.insert(0, os.path.join(LAB, "array_calculation"))
sys.path.insert(0, os.path.join(LAB, "array_calculation", "engine"))
sys.path.insert(0, os.path.join(LAB, "array_calculation", "margins"))
sys.path.insert(0, os.path.join(LAB, "array_calculation", "generators"))
import vignetting_overlap as vo          # noqa: E402 -- overlap_area_um2, pupil_shift_um, DEFAULT_R_ROT_MM
import active_pairs as ap                # noqa: E402 -- DEFAULT_ACTIVE_FRAC_THRESHOLD
import archimedean_spiral                # noqa: E402 -- generate(), same fn the sweep used

HOLE_COORDS_M8_CSV = os.path.join(LAB, "fabrication_package", "hole_coordinates", "hole_coordinates_M8.0.csv")
OUT_MP4 = os.path.join(HERE, "blindness_mechanism_animation.mp4")

FPS = 24
D_PUPIL_UM = 4000.0                       # this project's own established pupil diameter constant
R_P = D_PUPIL_UM / 2.0
R_ROT_MM = vo.DEFAULT_R_ROT_MM             # 13.5mm
ACTIVE_FRAC_THRESHOLD = ap.DEFAULT_ACTIVE_FRAC_THRESHOLD  # 0.5

# Copied verbatim from array_calculation/compute_gaze_weighted_metrics.py (GAZE_BINS)
GAZE_BINS = [
    (0.5, 9.29), (1.5, 9.16), (2.5, 8.92), (3.5, 8.56), (4.5, 8.11),
    (5.5, 7.57), (6.5, 6.98), (7.5, 6.35), (8.5, 5.69), (9.5, 5.04),
    (10.5, 4.40), (11.5, 3.79), (12.5, 3.22), (13.5, 2.70), (14.5, 2.23),
    (15.5, 1.81), (16.5, 1.45), (17.5, 1.14), (18.5, 0.88), (19.5, 0.67),
    (20.5, 0.50), (21.5, 0.37), (22.5, 0.27), (23.5, 0.19), (24.5, 0.13),
    (27.0, 0.58),
]
BIN_CENTERS = np.array([c for c, _ in GAZE_BINS])
BIN_WEIGHTS = np.array([w for _, w in GAZE_BINS])
PHI_VALID_MAX = vo.DEFAULT_PHI_VALID_DEG   # 25.0
PHI_HARD_MAX = BIN_CENTERS.max()           # 27.0 (this project's own extrapolated bin)

_cum = np.cumsum(BIN_WEIGHTS)
_CUM_EDGES = np.concatenate([[0.0], _cum])
_PHI_NODES = np.concatenate([[0.0], BIN_CENTERS])


def phi_of_t(t_pct):
    """Inverse-CDF: given a percent of total real gaze-time-weight (0-100),
    return the phi (deg) at/under which that much weight has accumulated.
    Real-weighted pacing, not a uniform ramp."""
    return float(np.interp(t_pct, _CUM_EDGES, _PHI_NODES))


CASE_A = dict(
    key="A", family="archimedean_spiral", M="4D", a_hole_um=600.0, N=50, c_um=2000.0,
    real_blind_pct=90.793333, real_ghost_pct=4.625278,
    verdict="REJECTED candidate", color_tag="#B23A48",
    title="Case A -- archimedean spiral, M=4D (REJECTED)",
)
CASE_B = dict(
    key="B", family="hexagonal", M="8D", a_hole_um=400.0, N=50,
    real_blind_pct=0.3327777777777777, real_ghost_pct=0.0,
    verdict="SHIPPED primary winner", color_tag="#2E9E3B",
    title="Case B -- hexagonal, M=8D (SHIPPED WINNER)",
)


def load_case_a_coords():
    coords, meta = archimedean_spiral.generate(N=CASE_A["N"], a_hole_um=CASE_A["a_hole_um"], c_um=CASE_A["c_um"])
    return np.asarray(coords, dtype=float)


def load_case_b_coords():
    df = pd.read_csv(HOLE_COORDS_M8_CSV)
    coords = df[["x_mm", "y_mm"]].values.astype(float) * 1000.0
    assert len(coords) == CASE_B["N"], f"expected {CASE_B['N']} holes, got {len(coords)}"
    return coords


def compute_state(coords, R_h, phi_deg, theta_rad):
    R = vo.pupil_shift_um(phi_deg, R_ROT_MM)
    px, py = R * np.cos(theta_rad), R * np.sin(theta_rad)
    dx = coords[:, 0] - px
    dy = coords[:, 1] - py
    delta = np.sqrt(dx ** 2 + dy ** 2)
    areas = vo.overlap_area_um2(delta, R_P, R_h)
    hole_area = np.pi * R_h ** 2
    frac = areas / hole_area
    n_active = int((frac >= ACTIVE_FRAC_THRESHOLD).sum())
    total_area = float(areas.sum())
    is_blind = (total_area == 0.0)
    is_ghost = (n_active >= 2)
    return px, py, areas, hole_area, total_area, n_active, is_blind, is_ghost


def state_color(is_blind, is_ghost):
    if is_blind:
        return "#B23A48"
    if is_ghost:
        return "#E07B39"
    return "#2C6E9E"


def status_text(is_blind, is_ghost, n_active):
    if is_blind:
        return "BLIND -- 0 holes reach retina"
    if is_ghost:
        return f"GHOST -- {n_active} holes overlap pupil"
    return "clean single image"


def draw_case_panel(ax, coords, R_h, extent, state, title):
    px, py, areas, hole_area, total_area, n_active, is_blind, is_ghost = state
    ax.clear()
    ax.set_xlim(-extent, extent)
    ax.set_ylim(-extent, extent)
    ax.set_aspect("equal")
    ax.axis("off")

    frac = areas / hole_area
    for (x, y), f in zip(coords, frac):
        if f <= 0.0:
            face = "#e2e2e2"
        elif f < ACTIVE_FRAC_THRESHOLD:
            face = "#BFE3B4"
        else:
            face = "#2E9E3B"
        ax.add_patch(plt.Circle((x, y), R_h, facecolor=face, edgecolor="#666666", linewidth=0.5, zorder=2))

    col = state_color(is_blind, is_ghost)
    ax.add_patch(plt.Circle((px, py), R_P, fill=False, edgecolor=col, linewidth=2.4, zorder=5))
    ax.plot([px], [py], "+", color=col, markersize=9, markeredgewidth=1.8, zorder=6)

    lw = 4.5 if (is_blind or is_ghost) else 1.2
    ec = col if (is_blind or is_ghost) else "#cccccc"
    ax.add_patch(plt.Rectangle((-extent, -extent), 2 * extent, 2 * extent, fill=False,
                                edgecolor=ec, linewidth=lw, zorder=10))

    ax.set_title(title, fontsize=10.5, fontweight="bold", pad=8)
    ax.text(0.5, -0.05, status_text(is_blind, is_ghost, n_active), transform=ax.transAxes,
            ha="center", fontsize=10.5, fontweight="bold", color=col)
    ax.text(0.5, -0.115, f"illuminated area = {total_area:,.0f} um2  |  active holes = {n_active}",
            transform=ax.transAxes, ha="center", fontsize=8, color="#555")


def draw_dial(ax, phi_deg, theta_rad, extrapolated):
    ax.clear()
    ax.set_aspect("equal")
    ax.axis("off")
    lim = PHI_HARD_MAX * 1.2
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    for r, ls, col, lw in [(6.0, "-", "#dddddd", 1.0), (17.0, "-", "#dddddd", 1.0),
                           (PHI_VALID_MAX, "--", "#B23A48", 1.3), (PHI_HARD_MAX, ":", "#B23A48", 1.3)]:
        ax.add_patch(plt.Circle((0, 0), r, fill=False, edgecolor=col, linewidth=lw, linestyle=ls))
    ax.text(0, 6.0, "6° (51.6% of viewing time)", fontsize=6, color="#999", ha="center", va="bottom")
    ax.text(0, 17.6, "17° (95.3% of viewing time)", fontsize=6, color="#999", ha="center", va="bottom")
    ax.text(-PHI_VALID_MAX * 0.72, -PHI_VALID_MAX * 0.72, "25° -- formula's\nvalidated limit",
            fontsize=6.3, color="#B23A48", ha="center", va="top", rotation=45)
    ax.text(PHI_HARD_MAX * 0.72, -PHI_HARD_MAX * 0.72, "27° -- extrapolated\n(0.6% of viewing time)",
            fontsize=6.3, color="#B23A48", ha="center", va="top", rotation=-45)

    gx, gy = phi_deg * np.cos(theta_rad), phi_deg * np.sin(theta_rad)
    ax.plot([0, gx], [0, gy], color="#2C6E9E", linewidth=2, zorder=4)
    ax.plot([gx], [gy], "o", color="#2C6E9E", markersize=9, zorder=5)
    ax.plot([0], [0], "*", color="#F5A623", markersize=14, zorder=5)
    ax.text(0, -1.8, "fovea", fontsize=6.5, color="#777", ha="center", va="top")

    ax.set_title("Gaze direction: eccentricity φ, azimuth θ", fontsize=10, fontweight="bold", pad=10)
    theta_deg = np.degrees(theta_rad) % 360.0
    ax.text(0.5, -0.06, f"φ = {phi_deg:5.1f}°      θ = {theta_deg:5.1f}°", transform=ax.transAxes,
            ha="center", fontsize=11, fontweight="bold")
    if extrapolated:
        ax.text(0.5, -0.14, "beyond validated formula range -- EXTRAPOLATED, flagged", transform=ax.transAxes,
                ha="center", fontsize=8, color="#B23A48", fontweight="bold")


def main():
    coords_A = load_case_a_coords()
    coords_B = load_case_b_coords()
    R_h_A = CASE_A["a_hole_um"] / 2.0
    R_h_B = CASE_B["a_hole_um"] / 2.0
    R_max = vo.pupil_shift_um(PHI_HARD_MAX, R_ROT_MM)
    extent_A = max(np.abs(coords_A).max() + R_h_A, R_max + R_P) + 300.0
    extent_B = max(np.abs(coords_B).max() + R_h_B, R_max + R_P) + 300.0
    print(f"coords_A: {len(coords_A)} holes, extent={extent_A:.0f}um | "
          f"coords_B: {len(coords_B)} holes, extent={extent_B:.0f}um | R_max={R_max:.0f}um")

    fig = plt.figure(figsize=(13.5, 5.6))
    gs = gridspec.GridSpec(1, 3, width_ratios=[1.05, 1.05, 0.85], wspace=0.18,
                           left=0.03, right=0.98, top=0.86, bottom=0.14)
    ax_a = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1])
    ax_dial = fig.add_subplot(gs[2])

    INTRO_F = FPS * 4
    RAMP_F = FPS * 22
    HOLD24_F = FPS * 3
    HOLD27_F = FPS * 4
    OUTRO_F = FPS * 5
    TOTAL_F = INTRO_F + RAMP_F + HOLD24_F + HOLD27_F + OUTRO_F

    REV_RAMP = 5.0
    REV_HOLD24 = 2.0
    REV_HOLD27 = 2.0
    T_END_PCT = float(_CUM_EDGES[-2])  # cumulative weight through the 24.5deg bin (excludes the 27deg bin)

    counts = {"A": {"blind": 0, "ghost": 0, "n": 0}, "B": {"blind": 0, "ghost": 0, "n": 0}}

    def reset_counts():
        for k in counts:
            counts[k] = {"blind": 0, "ghost": 0, "n": 0}

    def tally(key, is_blind, is_ghost):
        counts[key]["n"] += 1
        if is_blind:
            counts[key]["blind"] += 1
        if is_ghost:
            counts[key]["ghost"] += 1

    card_texts = []  # tracked fig.text() artists so they can be removed before the next card/frame

    def clear_card_texts():
        for t in card_texts:
            t.remove()
        card_texts.clear()

    def intro_card():
        ax_a.clear(); ax_a.axis("off")
        ax_b.clear(); ax_b.axis("off")
        ax_dial.clear(); ax_dial.axis("off")
        card_texts.append(fig.text(0.5, 0.72, "How Blindness Occurs in a Pinhole Array",
                                   fontsize=19, fontweight="bold", ha="center"))
        body = ("As the eye rotates by eccentricity φ and azimuth θ, the pupil (4mm) shifts off-axis\n"
                "relative to the fixed hole array. Light only reaches the retina through holes\n"
                "whose disc still overlaps the pupil disc.\n\n"
                "BLIND = zero holes overlap at all (0% illuminated area).\n"
                "GHOST = 2+ holes overlap enough to form separate images.\n\n"
                "Two REAL, already-evaluated candidates, swept through the SAME (φ, θ) path --\n"
                "a rejected degenerate design vs. the shipped winner.")
        card_texts.append(fig.text(0.5, 0.40, body, fontsize=12, ha="center", va="center",
                                   linespacing=1.8, color="#333"))

    def outro_card():
        ax_a.clear(); ax_a.axis("off")
        ax_b.clear(); ax_b.axis("off")
        ax_dial.clear(); ax_dial.axis("off")
        card_texts.append(fig.text(0.5, 0.80, "Real, project-reported time-weighted metrics",
                                   fontsize=15, fontweight="bold", ha="center"))
        txt_a = (f"{CASE_A['title']}\n"
                 f"time_weighted_blind_pct = {CASE_A['real_blind_pct']:.2f}%\n"
                 f"time_weighted_ghost_pct = {CASE_A['real_ghost_pct']:.2f}%\n"
                 f"({CASE_A['verdict']} -- exploits blindness for a low ghost score)")
        txt_b = (f"{CASE_B['title']}\n"
                 f"time_weighted_blind_pct = {CASE_B['real_blind_pct']:.2f}%\n"
                 f"time_weighted_ghost_pct = {CASE_B['real_ghost_pct']:.2f}%\n"
                 f"({CASE_B['verdict']})")
        card_texts.append(fig.text(0.27, 0.52, txt_a, fontsize=10.5, ha="center", va="center",
                                   color=CASE_A["color_tag"], linespacing=1.9, fontweight="bold"))
        card_texts.append(fig.text(0.73, 0.52, txt_b, fontsize=10.5, ha="center", va="center",
                                   color=CASE_B["color_tag"], linespacing=1.9, fontweight="bold"))
        card_texts.append(fig.text(0.5, 0.24,
                          "Integrated over the full real evaluation grid: 26 eccentricity bins x 36 azimuths,\n"
                          "weighted by measured eye-tracking time. (the running counters shown during the\n"
                          "sweep were illustrative frame tallies only, not this same computation)",
                          fontsize=9.5, ha="center", va="center", color="#555", linespacing=1.7))

    def draw_frame(frame_idx):
        clear_card_texts()  # fig.text() persists across ax.clear() -- must be cleared every frame
                            # regardless of phase, or a card's text leaks into every later frame
                            # (this is exactly the O(n^2) accumulation bug already found and fixed
                            # once before in ExP3's build_setup_schematic_animation.py).
        if frame_idx < INTRO_F:
            intro_card()
            return
        f2 = frame_idx - INTRO_F

        if f2 < RAMP_F:
            reset_at_start = (f2 == 0)
            if reset_at_start:
                reset_counts()
            u = f2 / (RAMP_F - 1)
            phi = phi_of_t(u * T_END_PCT)
            theta = 2.0 * np.pi * REV_RAMP * u
            extrapolated = False
        elif f2 < RAMP_F + HOLD24_F:
            u = (f2 - RAMP_F) / (HOLD24_F - 1)
            phi = 24.5
            theta_ramp_end = 2.0 * np.pi * REV_RAMP
            theta = theta_ramp_end + 2.0 * np.pi * REV_HOLD24 * u
            extrapolated = False
        elif f2 < RAMP_F + HOLD24_F + HOLD27_F:
            u = (f2 - RAMP_F - HOLD24_F) / (HOLD27_F - 1)
            phi = 27.0
            theta_hold24_end = 2.0 * np.pi * REV_RAMP + 2.0 * np.pi * REV_HOLD24
            theta = theta_hold24_end + 2.0 * np.pi * REV_HOLD27 * u
            extrapolated = True
        else:
            outro_card()
            return

        state_A = compute_state(coords_A, R_h_A, phi, theta)
        state_B = compute_state(coords_B, R_h_B, phi, theta)
        tally("A", state_A[6], state_A[7])
        tally("B", state_B[6], state_B[7])

        draw_case_panel(ax_a, coords_A, R_h_A, extent_A, state_A, CASE_A["title"])
        draw_case_panel(ax_b, coords_B, R_h_B, extent_B, state_B, CASE_B["title"])
        draw_dial(ax_dial, phi, theta, extrapolated)

        ca, cb = counts["A"], counts["B"]
        if ca["n"] > 0:
            ax_dial.text(0.5, -0.24,
                         f"running sample (this sweep): A blind {100*ca['blind']/ca['n']:.0f}%, "
                         f"ghost {100*ca['ghost']/ca['n']:.0f}%  |  "
                         f"B blind {100*cb['blind']/cb['n']:.0f}%, ghost {100*cb['ghost']/cb['n']:.0f}%",
                         transform=ax_dial.transAxes, ha="center", fontsize=7, color="#888")

        fig.suptitle("Pinhole Array -- How Blindness Occurs Across Gaze Eccentricity and Azimuth",
                     fontsize=13, fontweight="bold", y=0.975)

    writer = FFMpegWriter(fps=FPS, bitrate=4000)
    anim = FuncAnimation(fig, draw_frame, frames=TOTAL_F, repeat=False)
    anim.save(OUT_MP4, writer=writer, dpi=130)
    plt.close(fig)
    print(f"wrote {OUT_MP4} ({TOTAL_F} frames, {TOTAL_F/FPS:.1f}s)")


if __name__ == "__main__":
    main()
