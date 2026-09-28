"""
Array_Design/array_geometry_lab/proposed_rig_animation/build_rig_explainer_animation.py

Explainer animation for the PROPOSED physical validation rig (from the user's own
hand-drawn schematic, 2026-09-28): a point source shines through a rotating
pinhole-array insert, a fixed +20D convex lens forms an image, and a bare RPi
camera sensor ("mock retina") slides along a calibrated linear rail -- axial
sensor displacement simulates myopic defocus (an out-of-focus retina), while
the array's own rotation (motor, omega) simulates gaze azimuth. An RPi 3B+
drives the linear stage and reads raw sensor frames; a Python script turns
those into a light-intensity-distribution heatmap.

THIS RIG HAS NOT BEEN BUILT OR RUN. This animation explains the MECHANISM only.
The right-hand "expected pattern" panel is a THEORETICAL PREVIEW, computed from
this project's own already-validated physics (the same ghost_formula.py +
vignetting_overlap.py composition used in retinal_light_distribution_simulation/),
NOT measured sensor data -- labelled as such on every frame.

Fixed hardware choice for this preview (a single physical array has one fixed
aperture -- the linear stage sweeps SIMULATED myopia for that one fixed part,
it does not swap parts): the M=8D PRIMARY_WINNER_PER_M design (hexagonal,
a_hole_um=400, N=50, pitch=4000um) -- the "test smallest aperture first" part
in this project's own recommended fabrication build order (Design
Visualisation/DV2's own "Recommended build order").

Side-view geometry (lens position, ray crossing point, sensor travel range,
array icon size) is SCHEMATIC and explicitly NOT to physical scale -- same
convention as ExP3's build_setup_schematic_animation.py. The M<->linear-stage-
position mapping is illustrative only: this project has not yet measured a
real calibration curve for that (it's what the proposed rig is FOR).

Run: python3 build_rig_explainer_animation.py
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
LAB = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(LAB))
sys.path.insert(0, os.path.join(LAB, "array_calculation"))
sys.path.insert(0, os.path.join(LAB, "array_calculation", "engine"))
sys.path.insert(0, os.path.join(LAB, "array_calculation", "margins"))
import degeneracy_filter as dgf
import vignetting_overlap as vo
import ghost_formula as gf

EVAL_DIR = os.path.join(LAB, "array_data", "evaluation_results")
OUT_MP4 = os.path.join(HERE, "rig_explainer_animation.mp4")

FPS = 24
P0 = 60.0
D_PUPIL_UM = 4000.0
R_P = D_PUPIL_UM / 2.0
R_ROT_MM = vo.DEFAULT_R_ROT_MM
ACTIVE_FRAC_THRESHOLD = 0.5
SPOT_RADIUS_DISPLAY_EXAGGERATION = 6.0

INK = "#222222"
MUTED = "#666666"
COLOR_SOURCE = "#F5A623"
COLOR_LENS = "#2C6E9E"
COLOR_RAY = "#E07B39"
COLOR_ARRAY = "#444444"
COLOR_SENSOR = "#4E9F3D"
COLOR_RAIL = "#999999"
COLOR_RPI = "#7A5C3E"


def load_M8_design():
    df = pd.read_csv(os.path.join(EVAL_DIR, "PRIMARY_WINNER_PER_M.csv"), dtype={"M": str})
    row = df[df.M == "8.0"].iloc[0]
    kwargs = dgf.parse_spacing_params(row.spacing_params)
    if pd.notna(row.seed):
        kwargs["seed"] = int(row.seed)
    coords, _meta = dgf.GEN_FUNCS[row.family](N=int(row.N_requested), a_hole_um=row.a_hole_um, **kwargs)
    return np.asarray(coords, dtype=float), float(row.a_hole_um)


def simulate_spots(coords_um, a_hole_um, M, theta_deg, phi_deg=0.0):
    R_h = a_hole_um / 2.0
    hole_area = np.pi * R_h ** 2
    R = vo.pupil_shift_um(phi_deg, R_ROT_MM)
    px, py = R * np.cos(np.radians(theta_deg)), R * np.sin(np.radians(theta_deg))
    dx = coords_um[:, 0] - px
    dy = coords_um[:, 1] - py
    delta = np.sqrt(dx ** 2 + dy ** 2)
    areas = vo.overlap_area_um2(delta, R_P, R_h)
    frac = areas / hole_area
    active_mask = frac > 1e-6
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
    is_blind = float(areas.sum()) == 0.0
    is_ghost = n_active >= 2
    return spots, n_active, is_blind, is_ghost


def main():
    coords, a_hole = load_M8_design()
    max_s = np.hypot(coords[:, 0], coords[:, 1]).max()
    r_ee50_by_M_path = os.path.join(REPO, "new_sweeps", "per_M_optimum_map.csv")
    opt_map = pd.read_csv(r_ee50_by_M_path).set_index("M_diopters")

    def r_ee50_at(M):
        Ms = np.array(opt_map.index)
        idx = (np.abs(Ms - M)).argmin()
        return float(opt_map["r_EE_50_at_blur_opt_um"].iloc[idx])

    fig = plt.figure(figsize=(13.5, 6.2))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1.55, 1.0], wspace=0.22,
                           left=0.03, right=0.98, top=0.80, bottom=0.15)
    ax_side = fig.add_subplot(gs[0])
    ax_sensor = fig.add_subplot(gs[1])

    # fig.text() persists across ax.clear() -- must be tracked and removed every
    # frame or it silently accumulates (the same O(n^2) bug already found and
    # fixed once before in ExP3's build_setup_schematic_animation.py and again in
    # blindness_mechanism_animation.py). intro_card()/outro_card() add fresh
    # texts; draw_frame() clears them before dispatching to any phase.
    card_texts = []

    def clear_card_texts():
        for t in card_texts:
            t.remove()
        card_texts.clear()

    SOURCE_X = 10.0
    ARRAY_X = 8.6
    LENS_X = 5.0
    FOCUS_X = 3.3          # fixed ray-crossing point (paraxial image plane of the +20D lens)
    SENSOR_X_MIN = 1.2     # sensor position at M_sim = 0 (at/near the focus)
    SENSOR_X_MAX = 3.8     # sensor position at M_sim = 8 -- exaggerated travel, NOT to scale
    RAIL_Y = -3.4

    def sensor_x_for_M(M):
        frac = M / 8.0
        return SENSOR_X_MIN + frac * (SENSOR_X_MAX - SENSOR_X_MIN)

    INTRO_F = FPS * 4
    MAIN_F = FPS * 30
    OUTRO_F = FPS * 4
    TOTAL_F = INTRO_F + MAIN_F + OUTRO_F
    REVOLUTIONS = 6

    def intro_card():
        ax_side.clear(); ax_side.axis("off")
        ax_sensor.clear(); ax_sensor.axis("off")
        card_texts.append(fig.text(0.5, 0.68, "A Proposed Validation Rig", fontsize=20, fontweight="bold", ha="center"))
        body = ("Point source -> rotating pinhole-array insert -> fixed +20D lens -> bare\n"
                "camera sensor ('mock retina') on an RPi-driven linear rail.\n\n"
                "Sliding the sensor simulates MYOPIC DEFOCUS (axial displacement from focus).\n"
                "Rotating the array simulates GAZE AZIMUTH.\n\n"
                "THIS RIG HAS NOT BEEN BUILT. The right-hand panel is a THEORETICAL PREVIEW\n"
                "from this project's own validated model -- not measured sensor data.")
        card_texts.append(fig.text(0.5, 0.38, body, fontsize=11.5, ha="center", va="center",
                                   linespacing=1.9, color="#333"))

    def outro_card():
        ax_side.clear(); ax_side.axis("off")
        ax_sensor.clear(); ax_sensor.axis("off")
        card_texts.append(fig.text(0.5, 0.60, "What the Python script would produce", fontsize=16,
                                   fontweight="bold", ha="center"))
        body = ("RPi 3B+ drives the linear stage to a commanded position and reads a raw frame\n"
                "from the bare sensor at each step -- no camera lens, no demosaicing, no auto-exposure.\n\n"
                "A Python script converts each raw frame into a light-intensity-distribution heatmap,\n"
                "exactly like the right-hand panel shown here -- letting the REAL measured pattern be\n"
                "compared directly against this project's theoretical prediction, aperture by aperture,\n"
                "myopia power by myopia power.")
        card_texts.append(fig.text(0.5, 0.32, body, fontsize=11, ha="center", va="center",
                                   linespacing=1.9, color="#333"))

    def draw_side(M, theta_deg, sensor_x, spin_deg):
        ax_side.clear()
        ax_side.set_xlim(0, 11.2)
        ax_side.set_ylim(-4.2, 4.2)
        ax_side.axis("off")
        ax_side.plot([SENSOR_X_MIN - 0.4, SOURCE_X + 0.6], [0, 0], color="#dddddd", linewidth=1, linestyle=":")

        # point source
        ax_side.plot([SOURCE_X], [0], marker="*", markersize=20, color=COLOR_SOURCE, zorder=5)
        ax_side.text(SOURCE_X, 0.5, "point\nsource", ha="center", fontsize=8, color=INK)

        # rotating pinhole-array insert (schematic disk + a few holes that spin)
        disk_r = 1.15
        theta_holes = np.radians(spin_deg) + np.linspace(0, 2 * np.pi, 7, endpoint=False)
        hx = ARRAY_X + 0.05 * np.cos(theta_holes)
        hy = 0.75 * disk_r * np.sin(theta_holes)
        ax_side.add_patch(plt.Circle((ARRAY_X, 0), disk_r, facecolor="#dddddd", edgecolor=COLOR_ARRAY,
                                     linewidth=1.6, zorder=3))
        ax_side.scatter(hx, hy, s=10, color=COLOR_ARRAY, zorder=4)
        ax_side.text(ARRAY_X, -disk_r - 0.55, "pinhole array\n(rotating, omega)", ha="center", fontsize=8, color=INK)
        # rotation arrow (dashed arc around the array disk, indicating spin)
        arc_theta = np.radians(np.linspace(20, 340, 40))
        arc_r = disk_r * 1.35
        ax_side.plot(ARRAY_X + arc_r * np.cos(arc_theta), arc_r * np.sin(arc_theta),
                    color="#B23A48", linewidth=1.3, alpha=0.7, linestyle="--")

        # convex lens (+20D)
        lens_h = 1.7
        ax_side.add_patch(plt.Polygon(np.column_stack([
            LENS_X + 0.28 * np.sin(np.linspace(-np.pi/2, np.pi/2, 40)),
            lens_h * np.linspace(-1, 1, 40)]), closed=True, fill=True, facecolor="#cfe3f2",
            edgecolor=COLOR_LENS, linewidth=1.8, zorder=3))
        ax_side.text(LENS_X, lens_h + 0.35, "+20D\nconvex lens", ha="center", fontsize=8, color=INK)

        # rays: source -> array edge holes -> lens -> cross at FOCUS_X -> sensor
        edge_y = 0.75 * disk_r
        for sign in (+1, -1):
            ax_side.plot([SOURCE_X, ARRAY_X], [0, sign * edge_y * 0.4], color=COLOR_RAY, linewidth=1.1, alpha=0.85)
            ax_side.plot([ARRAY_X, LENS_X], [sign * edge_y * 0.4, sign * edge_y * 0.9], color=COLOR_RAY,
                        linewidth=1.1, alpha=0.85)
            ax_side.plot([LENS_X, FOCUS_X], [sign * edge_y * 0.9, 0], color=COLOR_RAY, linewidth=1.3)
            ax_side.plot([FOCUS_X, sensor_x], [0, -sign * edge_y * 0.9 * (sensor_x - FOCUS_X) / (SENSOR_X_MAX - FOCUS_X + 1e-6)],
                        color=COLOR_RAY, linewidth=1.3, linestyle="--")

        # linear rail + sensor
        ax_side.plot([SENSOR_X_MIN - 0.3, SENSOR_X_MAX + 0.3], [RAIL_Y, RAIL_Y], color=COLOR_RAIL, linewidth=3)
        ax_side.plot([sensor_x, sensor_x], [RAIL_Y, -0.9], color="#333333", linewidth=1.3)
        ax_side.add_patch(plt.Rectangle((sensor_x - 0.12, -0.9), 0.24, 0.55, facecolor=COLOR_SENSOR,
                                        edgecolor="#2b6b2b", zorder=6))
        ax_side.text(sensor_x, -1.65, "mock retina\n(bare sensor)", ha="center", fontsize=7.8, color=INK)
        ax_side.annotate("", xy=(SENSOR_X_MIN, RAIL_Y - 0.35), xytext=(SENSOR_X_MAX, RAIL_Y - 0.35),
                         arrowprops=dict(arrowstyle="<->", color=COLOR_RAIL))
        ax_side.text((SENSOR_X_MIN + SENSOR_X_MAX) / 2, RAIL_Y - 0.75,
                    "calibrated linear drive -- simulates myopic defocus (NOT to physical scale)",
                    ha="center", fontsize=7.3, color=MUTED)

        # RPi box + control/data lines
        rpi_x, rpi_y = 0.4, -2.6
        ax_side.add_patch(plt.Rectangle((rpi_x - 0.5, rpi_y - 0.4), 1.0, 0.8, facecolor="#eee",
                                        edgecolor=COLOR_RPI, linewidth=1.5, zorder=6))
        ax_side.text(rpi_x, rpi_y, "RPi\n3B+", ha="center", va="center", fontsize=8, fontweight="bold", color=COLOR_RPI)
        ax_side.annotate("", xy=(SENSOR_X_MIN - 0.1, RAIL_Y), xytext=(rpi_x, rpi_y + 0.4),
                         arrowprops=dict(arrowstyle="->", color=COLOR_RPI, linewidth=1.3))

        ax_side.text(5.6, 3.6, f"M simulated (from stage position) = {M:.2f}D    "
                              f"gaze theta = {theta_deg % 360:5.1f} deg",
                    ha="center", fontsize=10.5, fontweight="bold", color=INK)

    def draw_sensor_panel(spots, r_ee50, n_active, is_blind, is_ghost, extent):
        ax_sensor.clear()
        ax_sensor.set_xlim(-extent, extent)
        ax_sensor.set_ylim(-extent, extent)
        ax_sensor.set_aspect("equal")
        ax_sensor.set_facecolor("#050505")
        for rx, ry, f in spots:
            ax_sensor.add_patch(plt.Circle((rx, ry), r_ee50 * SPOT_RADIUS_DISPLAY_EXAGGERATION,
                                           facecolor="#FFD966", edgecolor="none", alpha=0.25 + 0.75 * f, zorder=3))
        ax_sensor.plot([0], [0], "+", color="#555", markersize=6, zorder=1)
        if is_blind:
            status, color = "BLIND", "#FF6B6B"
        elif is_ghost:
            status, color = f"GHOST x{n_active}", "#FFA94D"
        elif not spots:
            status, color = "no signal", "#FF6B6B"
        else:
            status, color = "clean", "#8CE99A"
        ax_sensor.set_xticks([]); ax_sensor.set_yticks([])
        ax_sensor.set_title("Expected sensor readout\n(THEORETICAL PREVIEW, not measured)",
                            fontsize=10.5, fontweight="bold")
        ax_sensor.text(0.5, -0.06, status, transform=ax_sensor.transAxes, ha="center", fontsize=10,
                      fontweight="bold", color=color)

    def draw_frame(frame_idx):
        clear_card_texts()
        if frame_idx < INTRO_F:
            intro_card()
            return
        f2 = frame_idx - INTRO_F
        if f2 < MAIN_F:
            u = f2 / (MAIN_F - 1)
            M = 8.0 * u
            theta = 360.0 * REVOLUTIONS * u
            spin = theta  # array visually spins at the same rate as azimuth sweep
        else:
            outro_card()
            return

        sensor_x = sensor_x_for_M(M)
        r_ee50 = r_ee50_at(M)
        spots, n_active, is_blind, is_ghost = simulate_spots(coords, a_hole, M, theta)
        max_dr = gf.delta_r_corrected_from_M_um(max_s, M, P0)
        r_disp = r_ee50 * SPOT_RADIUS_DISPLAY_EXAGGERATION
        extent = max(max_dr, r_disp) * 1.4 + r_disp

        draw_side(M, theta, sensor_x, spin)
        draw_sensor_panel(spots, r_ee50, n_active, is_blind, is_ghost, extent)

    fig.suptitle("Proposed Rig -- Rotating Pinhole Array + Sliding Bare-Sensor Retina",
                fontsize=14, fontweight="bold", y=0.965)
    fig.text(0.5, 0.905, "Hardware fixed for this preview: M=8D primary-winner design "
                        "(hexagonal, 400um aperture, N=50) -- one physical part, myopia swept via stage position",
             ha="center", fontsize=8.8, color=MUTED)
    fig.text(0.5, 0.02, "RPi 3B+ (bottom left) drives the linear stage and reads raw sensor frames -- "
                       "no camera lens, no demosaicing, no auto-exposure.",
             ha="center", fontsize=8.3, color=COLOR_RPI)

    writer = FFMpegWriter(fps=FPS, bitrate=4200)
    anim = FuncAnimation(fig, draw_frame, frames=TOTAL_F, repeat=False)
    anim.save(OUT_MP4, writer=writer, dpi=130)
    plt.close(fig)
    print(f"wrote {OUT_MP4} ({TOTAL_F} frames, {TOTAL_F/FPS:.1f}s)")


if __name__ == "__main__":
    main()
