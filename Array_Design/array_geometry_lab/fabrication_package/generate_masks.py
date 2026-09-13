"""
Array_Design/array_geometry_lab/fabrication_package/generate_masks.py

Turns this project's own gaze-weighted winner-per-M table
(array_data/evaluation_results/gaze_weighted_winner_per_M.csv) into a
physical photomask fabrication package for etching each design into a
0.05mm (50um) brass shim via UV photoresist + a printed transparency film.

Hole coordinates are computed by IMPORTING the project's own real generator
functions (array_calculation/generators/square.py, hexagonal.py) directly --
NOT reimplemented -- so the coordinates in this package are guaranteed
bit-for-bit identical to the design the gaze-weighted evaluation actually
scored, not a re-derivation that could silently drift from it.

UNDERCUT COMPENSATION -- explicitly flagged, not silently assumed:
This project has NO empirical etch-rate/undercut calibration for this exact
brass alloy, thickness, etchant, or equipment. The compensation used below
(UNDERCUT_COMPENSATION_UM) is a standard, widely-cited starting design rule
for photochemical machining (PCM) of thin metal via double-sided
(simultaneous two-sided) chemical etching -- NOT a project-validated
number. See fabrication_spec.py / the generated PDF for the full derivation,
the low/mid/high bracket, and the explicit recommendation to confirm with a
test-etch coupon before committing the real shim.

Outputs (all under this folder):
  hole_coordinates/hole_coordinates_M{label}.csv   -- one row per hole,
      (x_mm, y_mm), target etched diameter, and the undercut-compensated
      mask-aperture diameter actually drawn in the artwork.
  masks/M{label}_{polarity}_{side}.svg             -- print-ready, true-
      physical-scale (mm-unit viewBox) vector artwork, one file per
      (design, resist polarity, shim side) combination.
  fabrication_summary.csv                          -- one row per M, all
      derived geometry + compensation numbers, feeding the spec PDF.

Run: python3 generate_masks.py
"""
import os
import sys
import csv
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB_ROOT = os.path.dirname(HERE)  # array_geometry_lab/
GENERATORS_DIR = os.path.join(LAB_ROOT, "array_calculation", "generators")
WINNER_CSV = os.path.join(LAB_ROOT, "array_data", "evaluation_results", "gaze_weighted_winner_per_M.csv")

sys.path.insert(0, GENERATORS_DIR)
import square as square_gen      # noqa: E402  -- this project's real generator, not reimplemented
import hexagonal as hex_gen      # noqa: E402

COORD_DIR = os.path.join(HERE, "hole_coordinates")
MASK_DIR = os.path.join(HERE, "masks")
os.makedirs(COORD_DIR, exist_ok=True)
os.makedirs(MASK_DIR, exist_ok=True)

# ---------------------------------------------------------------- process --
SHIM_THICKNESS_UM = 50.0  # 0.05mm, as given

# Standard PCM (photochemical machining) starting design rule for a
# double-sided (simultaneous two-face) chemical etch: total undercut on a
# feature's diameter is commonly approximated in the 0.5x-1.5x material-
# thickness range for a reasonably controlled process; 1.0x thickness is
# the most commonly cited nominal starting point. NOT an empirical
# calibration of THIS shim/etchant/equipment -- see module docstring.
UNDERCUT_LOW_UM = 0.5 * SHIM_THICKNESS_UM
UNDERCUT_NOMINAL_UM = 1.0 * SHIM_THICKNESS_UM
UNDERCUT_HIGH_UM = 1.5 * SHIM_THICKNESS_UM

MARGIN_MM = 8.0          # blank margin around the array's own bounding circle
FIDUCIAL_R_MM = 0.75     # corner registration/fiducial dot radius
CAL_SQUARE_SIDE_MM = 10.0  # 1:1 print-verification reference square, exact


def load_winners():
    with open(WINNER_CSV) as f:
        return list(csv.DictReader(f))


def generate_coords_um(family, N_requested, pitch_um, a_hole_um, rotation_deg=0.0):
    if family == "square":
        coords, meta = square_gen.generate(N_requested, a_hole_um, pitch_um, rotation_deg)
    elif family == "hexagonal":
        coords, meta = hex_gen.generate(N_requested, a_hole_um, pitch_um, rotation_deg)
    else:
        raise ValueError(f"no generator wired up for family={family!r}")
    return coords, meta


def parse_spacing_params(s):
    out = {}
    for part in s.split(";"):
        k, v = part.split("=")
        out[k.strip()] = float(v)
    return out


# ------------------------------------------------------------- SVG export --

def _circle(cx, cy, r, fill):
    return f'<circle cx="{cx:.5f}" cy="{cy:.5f}" r="{r:.5f}" fill="{fill}" stroke="none"/>'


def write_svg(path, coords_mm, hole_r_mm, blank_w_mm, blank_h_mm, polarity, label_text, mirror_x):
    """polarity: 'positive' or 'negative' resist convention (see module docstring
    / spec PDF section 3 for the full derivation of which fill goes where):
      - negative resist (exposure HARDENS resist -- protects metal where exposed):
        mask must be CLEAR everywhere except OPAQUE dots at hole centers (opaque
        = stays unexposed = washes away in developer = bare metal = etched = hole).
      - positive resist (exposure DISSOLVES resist -- exposed area develops away):
        mask must be OPAQUE everywhere except CLEAR circles at hole centers
        (clear = light passes = exposed = develops away = bare metal = hole).
    mirror_x: True for the bottom-side film (see spec PDF section 5 -- the two
    masks that contact opposite faces of the shim must be mirror images of one
    another so their hole centers register through the sheet)."""
    half_w, half_h = blank_w_mm / 2.0, blank_h_mm / 2.0

    if polarity == "negative":
        field_fill, hole_fill = "none", "black"
    elif polarity == "positive":
        field_fill, hole_fill = "black", "white"
    else:
        raise ValueError(polarity)

    elems = []
    if field_fill != "none":
        elems.append(f'<rect x="{-half_w:.5f}" y="{-half_h:.5f}" width="{blank_w_mm:.5f}" '
                     f'height="{blank_h_mm:.5f}" fill="{field_fill}" stroke="none"/>')

    for x_mm, y_mm in coords_mm:
        xs = -x_mm if mirror_x else x_mm
        elems.append(_circle(xs, y_mm, hole_r_mm, hole_fill))

    # 1:1 print-verification calibration square (exact CAL_SQUARE_SIDE_MM,
    # measure with calipers/certified ruler AFTER printing, before exposing --
    # see spec PDF section 6) + 4 corner registration fiducials, placed
    # outside the working array, same for every mask so top/bottom align.
    cs = CAL_SQUARE_SIDE_MM
    cal_x, cal_y = -half_w + cs / 2.0 + 2.0, half_h - cs / 2.0 - 2.0
    cal_fill = hole_fill if polarity == "negative" else hole_fill  # outline only, see below
    elems.append(f'<rect x="{cal_x - cs/2.0:.5f}" y="{cal_y - cs/2.0:.5f}" width="{cs:.5f}" '
                 f'height="{cs:.5f}" fill="none" stroke="{hole_fill}" stroke-width="0.15"/>')
    elems.append(f'<text x="{cal_x:.5f}" y="{cal_y + cs/2.0 + 3.0:.5f}" font-size="2.2" '
                 f'text-anchor="middle" fill="{hole_fill}">{cs:.1f} mm ref</text>')

    fid_positions = [(-half_w + 4.0, -half_h + 4.0), (half_w - 4.0, -half_h + 4.0),
                      (-half_w + 4.0, half_h - 4.0), (half_w - 4.0, half_h - 4.0)]
    for fx, fy in fid_positions:
        elems.append(_circle(fx, fy, FIDUCIAL_R_MM, hole_fill))

    elems.append(f'<text x="0" y="{-half_h + 5.5:.5f}" font-size="2.6" text-anchor="middle" '
                 f'fill="{hole_fill}">{label_text}</text>')

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{blank_w_mm}mm" height="{blank_h_mm}mm" '
        f'viewBox="{-half_w} {-half_h} {blank_w_mm} {blank_h_mm}">\n'
        + "\n".join(elems) + "\n</svg>\n"
    )
    with open(path, "w") as f:
        f.write(svg)


def main():
    winners = load_winners()
    summary_rows = []

    for row in winners:
        M_label = row["M"]
        family = row["family"]
        N_req = int(row["N_requested"])
        a_hole_um = float(row["a_hole_um"])
        sp = parse_spacing_params(row["spacing_params"])
        pitch_um = sp["pitch_um"]
        rotation_deg = sp.get("rotation_deg", 0.0)

        coords_um, meta = generate_coords_um(family, N_req, pitch_um, a_hole_um, rotation_deg)
        N_actual = meta["N_actual"]
        coords_mm = coords_um / 1000.0

        target_diam_um = a_hole_um
        mask_diam_nominal_um = target_diam_um - UNDERCUT_NOMINAL_UM
        mask_diam_low_um = target_diam_um - UNDERCUT_LOW_UM   # least aggressive compensation
        mask_diam_high_um = target_diam_um - UNDERCUT_HIGH_UM  # most aggressive compensation
        if mask_diam_high_um <= 0:
            raise ValueError(f"M={M_label}: high-bracket undercut compensation drives the mask "
                              f"aperture to <=0 -- would need a redesign, not silently clamped")

        # ---- coordinate CSV ----
        coord_path = os.path.join(COORD_DIR, f"hole_coordinates_M{M_label}.csv")
        with open(coord_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["hole_index", "x_mm", "y_mm", "target_etched_diameter_um",
                        "mask_aperture_diameter_um_nominal_1p0x", "mask_aperture_diameter_um_low_0p5x",
                        "mask_aperture_diameter_um_high_1p5x"])
            for i, (x_mm, y_mm) in enumerate(coords_mm):
                w.writerow([i, round(x_mm, 5), round(y_mm, 5), target_diam_um,
                            round(mask_diam_nominal_um, 2), round(mask_diam_low_um, 2),
                            round(mask_diam_high_um, 2)])
        print(f"M={M_label}: wrote {coord_path} ({N_actual} holes)")

        # ---- blank size, from the ACTUAL coordinates, not assumed ----
        r_max_mm = float(np.max(np.sqrt((coords_mm ** 2).sum(axis=1)))) if N_actual > 0 else 0.0
        blank_side_mm = 2.0 * r_max_mm + 2.0 * MARGIN_MM
        blank_side_mm = math.ceil(blank_side_mm / 5.0) * 5.0  # round up to a clean 5mm blank size

        hole_r_mm = (mask_diam_nominal_um / 1000.0) / 2.0
        label = f"M={M_label}  {family}  a_hole={a_hole_um:.0f}um  pitch={pitch_um:.0f}um  N={N_actual}"

        for polarity in ("negative", "positive"):
            for side, mirror in (("top", False), ("bottom_mirrored", True)):
                svg_path = os.path.join(MASK_DIR, f"M{M_label}_{polarity}_{side}.svg")
                side_tag = side.replace("_", " ").upper()
                file_label = f"{label} | {polarity.upper()} {side_tag}"
                write_svg(svg_path, coords_mm, hole_r_mm, blank_side_mm, blank_side_mm,
                          polarity, file_label, mirror)

        summary_rows.append({
            "M": M_label, "family": family, "N_requested": N_req, "N_actual": N_actual,
            "pitch_um": pitch_um, "rotation_deg": rotation_deg,
            "target_etched_diameter_um": target_diam_um,
            "mask_aperture_diameter_um_nominal": round(mask_diam_nominal_um, 2),
            "mask_aperture_diameter_um_low": round(mask_diam_low_um, 2),
            "mask_aperture_diameter_um_high": round(mask_diam_high_um, 2),
            "r_max_mm": round(r_max_mm, 3),
            "blank_side_mm": blank_side_mm,
        })

    summary_path = os.path.join(HERE, "fabrication_summary.csv")
    with open(summary_path, "w", newline="") as f:
        fieldnames = list(summary_rows[0].keys())
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in summary_rows:
            w.writerow(r)
    print(f"\nwrote {summary_path} ({len(summary_rows)} rows)")
    print(f"wrote {len(summary_rows) * 4} SVG mask files under {MASK_DIR}")


if __name__ == "__main__":
    main()
