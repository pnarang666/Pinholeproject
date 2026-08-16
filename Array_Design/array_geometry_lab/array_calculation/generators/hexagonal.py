"""Hexagonal lattice generator. Pitch (nearest-neighbor spacing) is the free spacing
parameter. Row construction (row height = pitch*sqrt(3)/2, alternate rows offset by
pitch/2) matches this project's existing hex-packing convention
(Array_Design/photometry/array_photometry.py::hole_lattice) -- re-implemented fresh
here (not imported) per this folder's self-containment rule, same geometry."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402


def generate(N, a_hole_um, pitch_um, rotation_deg=0.0):
    """Builds a hex lattice large enough to contain N points, keeps the N points
    closest to the origin (by radial distance), in that radial order.

    rotation_deg: see square.py's generate() docstring -- same convention (rotate
    the radially-sorted candidate set about the array center before overlap
    rejection/recentering, via base_generator.rotate_points), same exact-
    reproduction guarantee at the 0.0 default."""
    n_side = int(np.ceil(np.sqrt(N))) + 3
    row_h = pitch_um * np.sqrt(3) / 2.0
    rows = np.arange(-n_side, n_side + 1)
    pts_list = []
    for r in rows:
        y = r * row_h
        x_offset = (pitch_um / 2.0) if (r % 2) else 0.0
        xs = np.arange(-n_side, n_side + 1) * pitch_um + x_offset
        pts_list.append(np.column_stack([xs, np.full_like(xs, y, dtype=float)]))
    pts = np.vstack(pts_list)

    r2 = np.sum(pts ** 2, axis=1)
    order = np.argsort(r2)
    pts = pts[order][:N]
    pts = bg.rotate_points(pts, rotation_deg)

    return bg.finalize(pts, a_hole_um, family="hexagonal", N_requested=N,
                       nominal_spacing_desc={"pitch_um": float(pitch_um),
                                              "rotation_deg": float(rotation_deg)})
