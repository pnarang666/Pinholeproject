"""Rectangular (anisotropic square) lattice generator. pitch_x_um and pitch_y_um are
SEPARATE free parameters -- the point of this generator vs. square.py's single
pitch_um. At pitch_x_um == pitch_y_um this reduces to exactly the same lattice
square.py produces (verified in spot_check_generators.py's rectangular==square
equivalence check, the same pattern as the fibonacci_spiral/golden_angle identity
check) -- construction below is deliberately kept structurally identical to
square.py's (same meshgrid-then-radial-sort approach, same margin constant, same
overlap-rejection via base_generator.finalize) so that equivalence holds exactly,
not just approximately."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402


def generate(N, a_hole_um, pitch_x_um, pitch_y_um, rotation_deg=0.0):
    """Builds a rectangular lattice large enough to contain N points, keeps the N
    points closest to the origin (by radial distance), in that radial order -- same
    approach as square.py, with independent x/y pitches.

    rotation_deg: see square.py's generate() docstring -- same convention and same
    exact-reproduction guarantee at the 0.0 default. Note this is exactly why the
    rectangular==square-at-equal-pitch identity (this file's own module docstring)
    still holds at any shared rotation_deg, not just 0.0 -- rotation is applied
    identically in both generators, after the identical meshgrid-then-radial-sort
    construction."""
    n_side = int(np.ceil(np.sqrt(N))) + 3  # same margin constant as square.py, for
                                            # the same reason (enough candidates
                                            # beyond the minimal sqrt(N) box)
    idx = np.arange(-n_side, n_side + 1)
    X, Y = np.meshgrid(idx * pitch_x_um, idx * pitch_y_um)
    pts = np.column_stack([X.ravel(), Y.ravel()])
    r2 = np.sum(pts ** 2, axis=1)
    order = np.argsort(r2)
    pts = pts[order][:N]
    pts = bg.rotate_points(pts, rotation_deg)

    return bg.finalize(pts, a_hole_um, family="rectangular", N_requested=N,
                       nominal_spacing_desc={"pitch_x_um": float(pitch_x_um),
                                              "pitch_y_um": float(pitch_y_um),
                                              "rotation_deg": float(rotation_deg)})
