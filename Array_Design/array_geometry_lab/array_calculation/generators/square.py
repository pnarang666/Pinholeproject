"""Square lattice generator. Pitch (nearest-neighbor spacing) is the free spacing
parameter, matching this project's existing square-packing convention elsewhere
(Array_Design/photometry/array_photometry.py's own square packing: area per lattice
point = pitch^2)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402


def generate(N, a_hole_um, pitch_um, rotation_deg=0.0):
    """Builds a square lattice large enough to contain N points, keeps the N points
    closest to the origin (by radial distance), in that radial order -- so overlap
    rejection (base_generator.reject_overlapping) preferentially keeps the innermost
    points if pitch_um <= a_hole_um forces rejections.

    rotation_deg: rotates the lattice about the array center before overlap
    rejection/recentering (base_generator.rotate_points) -- applied to the
    already-radially-sorted candidate set, so it changes ONLY each point's (x,y),
    never which points are selected or which survive overlap rejection (rotation
    preserves every pairwise distance and every distance-from-origin exactly).
    Default 0.0 reproduces the pre-rotation-support output exactly (rotate_points
    short-circuits to a no-op at 0.0)."""
    n_side = int(np.ceil(np.sqrt(N))) + 3  # margin so the closest-N selection has
                                            # enough candidates beyond the sqrt(N)
                                            # minimal square to actually be the N
                                            # closest-to-origin, not an artifact of
                                            # a too-tight bounding box
    idx = np.arange(-n_side, n_side + 1)
    X, Y = np.meshgrid(idx * pitch_um, idx * pitch_um)
    pts = np.column_stack([X.ravel(), Y.ravel()])
    r2 = np.sum(pts ** 2, axis=1)
    order = np.argsort(r2)
    pts = pts[order][:N]
    pts = bg.rotate_points(pts, rotation_deg)

    return bg.finalize(pts, a_hole_um, family="square", N_requested=N,
                       nominal_spacing_desc={"pitch_um": float(pitch_um),
                                              "rotation_deg": float(rotation_deg)})
