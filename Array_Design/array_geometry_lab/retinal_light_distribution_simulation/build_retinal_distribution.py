"""
Array_Design/array_geometry_lab/retinal_light_distribution_simulation/build_retinal_distribution.py

Simulates the RETINAL image produced by each array PATTERN (family), per myopia
power M, at three gaze conditions (phi=0, 17, 25deg, azimuth theta=0 -- this
project's own established single-axis convention, e.g.
margins/vignetting_robustness.py). Not a new physics model: composes three
already-validated pieces this project already has, unmodified:

  1. WHICH holes are active at a given gaze: engine/vignetting_overlap.py's
     pupil_shift_um() + overlap_area_um2() -- exact circle-overlap geometry,
     validated to 4.657e-10 um^2 against its own 72-point dataset (VALIDATION.md).
  2. WHERE each active hole's own image lands on the retina: engine/ghost_formula.py's
     delta_r_corrected_from_M_um(s, M, P0) -- validated R^2=0.995135 against an
     independent two-hole wave-optics propagation. s = that hole's own distance
     from the array's centroid (every generator recenters on its own centroid --
     base_generator.py); direction = that hole's own (x,y) unit vector from
     centroid. This is a direct, not-reinterpreted use of the SAME formula the
     project already validated for hole-pair ghost separation, generalized here
     to "each simultaneously-active hole's own image is offset from the foveal
     position by this amount, in the direction of its own mask-plane position."
  3. HOW BIG each hole's own spot is: new_sweeps/per_M_optimum_map.csv's
     r_EE_50_at_blur_opt_um (the project's own standard 50%-encircled-energy
     blur radius), at the acuity-optimal aperture for that M -- which is exactly
     the aperture every real array winner at that M already uses (confirmed
     elsewhere in this project: 0.000 logMAR deviation from this same optimum).

Spot INTENSITY (alpha) = that hole's own overlap fraction (area/hole_area) --
graded, not a hard on/off threshold, so a partially-illuminated hole renders as
a dim spot, not silently dropped.

REAL WINNER GEOMETRIES ONLY -- no invented aperture/pitch/N. For each M, pulls
the first real winning row of each of the three families (square, hexagonal,
ring_offset_concentric -- the only 3 families that appear as an actual winner in
ANY of this project's 6 live evaluation-model tables) from whichever of those 6
tables has it. If a family never wins at a given M in any table, that panel is
left explicitly blank and labelled "no real winner in this project's own tables
at this M" -- not filled in with a placeholder geometry.

Run: python3 build_retinal_distribution.py
"""
import os
import sys
import textwrap

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(LAB))
sys.path.insert(0, os.path.join(LAB, "array_calculation"))
sys.path.insert(0, os.path.join(LAB, "array_calculation", "engine"))
sys.path.insert(0, os.path.join(LAB, "array_calculation", "margins"))
import degeneracy_filter as dgf          # noqa: E402
import vignetting_overlap as vo          # noqa: E402
import ghost_formula as gf               # noqa: E402

EVAL_DIR = os.path.join(LAB, "array_data", "evaluation_results")
WINNER_TABLES = ["FINAL_WINNER_PER_M.csv", "PRIMARY_WINNER_PER_M.csv", "gaze_weighted_winner_per_M.csv",
                 "metric1_max_density_per_M.csv", "effective_density_winner_per_M_cmin0.csv",
                 "effective_density_winner_per_M_cmin55.csv"]
FAMILIES = ["square", "hexagonal", "ring_offset_concentric"]
M_VALUES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
GAZE_CONDITIONS = [0.0, 17.0, 25.0]  # phi (deg), theta=0 (single-axis convention)

P0 = 60.0
D_PUPIL_UM = 4000.0
R_P = D_PUPIL_UM / 2.0
R_ROT_MM = vo.DEFAULT_R_ROT_MM
ACTIVE_FRAC_THRESHOLD = 0.5

FAMILY_COLOR = {"square": "#2C6E9E", "hexagonal": "#4E9F3D", "ring_offset_concentric": "#B23A48"}

# Real r_EE_50 spot radii (3.7-17.5um) are tiny pinpricks next to real ghost
# separations (up to ~hundreds of um) -- visually exaggerated by this factor for
# legibility ONLY (spot SEPARATION/position is never touched), same principle as
# ExP3's setup-schematic animation (exaggerated size, real quantity kept real,
# explicitly labeled every time it is shown).
SPOT_RADIUS_DISPLAY_EXAGGERATION = 6.0


def load_all_winners():
    frames = []
    for f in WINNER_TABLES:
        d = pd.read_csv(os.path.join(EVAL_DIR, f), dtype={"M": str})
        d = d[d.M != "global"].copy()
        d["M"] = d.M.astype(float)
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def pick_real_row(all_winners, family, M):
    rows = all_winners[(all_winners.family == family) & (all_winners.M == M)]
    return rows.iloc[0] if len(rows) else None


def regenerate_coords(row):
    kwargs = dgf.parse_spacing_params(row.spacing_params)
    if pd.notna(row.seed):
        kwargs["seed"] = int(row.seed)
    coords, _meta = dgf.GEN_FUNCS[row.family](N=int(row.N_requested), a_hole_um=row.a_hole_um, **kwargs)
    return np.asarray(coords, dtype=float)


def simulate_retinal_image(coords_um, a_hole_um, M, phi_deg, theta_deg=0.0):
    R_h = a_hole_um / 2.0
    hole_area = np.pi * R_h ** 2
    R = vo.pupil_shift_um(phi_deg, R_ROT_MM)
    px, py = R * np.cos(np.radians(theta_deg)), R * np.sin(np.radians(theta_deg))
    dx = coords_um[:, 0] - px
    dy = coords_um[:, 1] - py
    delta = np.sqrt(dx ** 2 + dy ** 2)
    areas = vo.overlap_area_um2(delta, R_P, R_h)
    frac = areas / hole_area
    active_mask = frac > 1e-6  # any nonzero overlap contributes some light

    spots = []
    for (x, y), f in zip(coords_um[active_mask], frac[active_mask]):
        s = np.hypot(x, y)
        if s < 1e-6:
            rx, ry = 0.0, 0.0
        else:
            dr = gf.delta_r_corrected_from_M_um(s, M, P0)
            rx, ry = (x / s) * dr, (y / s) * dr
        spots.append((rx, ry, min(f, 1.0)))

    n_active = int((frac >= ACTIVE_FRAC_THRESHOLD).sum())
    total_area = float(areas.sum())
    is_blind = (total_area == 0.0)
    is_ghost = (n_active >= 2)
    return spots, n_active, total_area, is_blind, is_ghost


def draw_panel(ax, spots, r_ee50_um, n_active, total_area, is_blind, is_ghost, extent):
    ax.clear()
    ax.set_xlim(-extent, extent)
    ax.set_ylim(-extent, extent)
    ax.set_aspect("equal")
    ax.set_facecolor("#050505")
    for rx, ry, f in spots:
        ax.add_patch(plt.Circle((rx, ry), r_ee50_um * SPOT_RADIUS_DISPLAY_EXAGGERATION, facecolor="#FFD966",
                                edgecolor="none", alpha=0.25 + 0.75 * f, zorder=3))
    ax.plot([0], [0], "+", color="#555", markersize=6, markeredgewidth=1, zorder=1)
    if is_blind:
        status, color = "BLIND", "#FF6B6B"
    elif is_ghost:
        status, color = f"GHOST x{n_active}", "#FFA94D"
    elif len(spots) == 0:
        status, color = "no signal", "#FF6B6B"
    else:
        status, color = "clean", "#8CE99A"
    ax.text(0.5, -0.10, status, transform=ax.transAxes, ha="center", fontsize=9, fontweight="bold", color=color)
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor("#888")


def build_figure_for_M(M, all_winners):
    fig, axes = plt.subplots(len(FAMILIES), len(GAZE_CONDITIONS), figsize=(10.5, 10.5))
    fig.suptitle(f"Simulated retinal light distribution -- M = {M:.0f}D", fontsize=15, fontweight="bold", y=0.98)

    for i, family in enumerate(FAMILIES):
        row = pick_real_row(all_winners, family, M)
        axes[i, 0].set_ylabel(family, fontsize=11, fontweight="bold", color=FAMILY_COLOR[family])
        if row is None:
            for j in range(len(GAZE_CONDITIONS)):
                axes[i, j].clear(); axes[i, j].axis("off")
            axes[i, 0].axis("on"); axes[i, 0].set_xticks([]); axes[i, 0].set_yticks([])
            axes[i, 1].text(0.5, 0.5, "no real winner in this project's\nown tables at this M",
                            transform=axes[i, 1].transAxes, ha="center", va="center", fontsize=9.5, color="#999")
            continue

        coords = regenerate_coords(row)
        a_hole = row.a_hole_um
        r_ee50 = R_EE50_BY_M[M]
        max_s = np.hypot(coords[:, 0], coords[:, 1]).max() if len(coords) else 0.0
        max_dr = gf.delta_r_corrected_from_M_um(max_s, M, P0)
        r_ee50_disp = r_ee50 * SPOT_RADIUS_DISPLAY_EXAGGERATION
        extent = max(max_dr, r_ee50_disp) * 1.4 + r_ee50_disp

        for j, phi in enumerate(GAZE_CONDITIONS):
            spots, n_active, total_area, is_blind, is_ghost = simulate_retinal_image(coords, a_hole, M, phi)
            draw_panel(axes[i, j], spots, r_ee50, n_active, total_area, is_blind, is_ghost, extent)
            if i == 0:
                axes[i, j].set_title(f"gaze phi={phi:.0f}deg", fontsize=10.5)
            if j == 0:
                axes[i, j].text(-0.30, 0.5, family, transform=axes[i, j].transAxes, rotation=90,
                                va="center", ha="center", fontsize=10.5, fontweight="bold",
                                color=FAMILY_COLOR[family])

    caption = (f"Spot size = r_EE_50 = {R_EE50_BY_M[M]:.2f}um x{SPOT_RADIUS_DISPLAY_EXAGGERATION:.0f} "
              "(exaggerated for visibility only -- real value that small). Position = "
              "ghost_formula.delta_r_corrected_from_M_um(s,M,P0), s = that hole's own distance from array "
              "center (NOT exaggerated -- real separation). Brightness = pupil-hole overlap fraction (graded).")
    if M == 0.0:
        caption += (" NOTE: at M=0D the formula gives EXACTLY zero separation regardless of s "
                   "(s*0/(P0-0)=0) -- a 'GHOST x2' label at M=0 means 2 holes are simultaneously active, "
                   "but their images coincide exactly (no myopic defocus to separate them) -- this is the "
                   "formula's own defining property, not a rendering error.")
    wrapped_lines = textwrap.wrap(caption, width=118)
    bottom_margin = 0.025 + 0.014 * len(wrapped_lines)
    for k, wline in enumerate(wrapped_lines):
        fig.text(0.5, bottom_margin - 0.014 * (k + 1), wline, ha="center", fontsize=7.6, color="#555")
    plt.tight_layout(rect=[0.03, bottom_margin, 1, 0.95])
    out_path = os.path.join(HERE, f"retinal_distribution_M{M:.0f}.png")
    fig.savefig(out_path, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"wrote {out_path}")


def main():
    opt_map = pd.read_csv(os.path.join(REPO, "new_sweeps", "per_M_optimum_map.csv")).set_index("M_diopters")
    global R_EE50_BY_M
    R_EE50_BY_M = opt_map["r_EE_50_at_blur_opt_um"].to_dict()

    all_winners = load_all_winners()
    for M in M_VALUES:
        build_figure_for_M(M, all_winners)


if __name__ == "__main__":
    main()
