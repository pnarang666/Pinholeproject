"""Concentric-ring generator.

EXPLICIT DESIGN DECISION (stated per this folder's task brief, not left implicit):
hole count per ring SCALES WITH ring circumference (constant angular spacing between
holes on every ring), not a fixed count per ring. Chosen because a fixed count would
make outer rings implausibly sparse (huge gaps between holes on a large ring) or inner
rings implausibly crowded (holes forced closer than a_hole_um on a small ring, which
the overlap-rejection step would then discard anyway) for the same nominal
"holes_per_ring" number -- constant angular spacing keeps the arc-length between
adjacent holes on every ring equal to ring 1's, which is the more physically sensible
default for a fabricatable pattern. Ring index 0 is a single hole at the pattern's own
center (r=0); ring k>=1 sits at radius k*ring_spacing_um with
round(holes_per_ring0 * k) holes.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402


def generate(N, a_hole_um, ring_spacing_um, holes_per_ring0):
    """holes_per_ring0: hole count on ring 1 (radius = ring_spacing_um); ring k's
    count is round(holes_per_ring0 * k), i.e. constant angular spacing across rings,
    equal to ring 1's own angular spacing (2*pi/holes_per_ring0)."""
    pts = [np.array([0.0, 0.0])]  # ring 0: single center hole
    k = 1
    while len(pts) < N:
        n_k = max(1, int(round(holes_per_ring0 * k)))
        r_k = k * ring_spacing_um
        thetas = np.linspace(0.0, 2 * np.pi, n_k, endpoint=False)
        pts.extend([np.array([r_k * np.cos(t), r_k * np.sin(t)]) for t in thetas])
        k += 1
        if k > 500:  # hard safety stop -- should never trigger for sane N
            break

    pts = np.array(pts[:N])

    return bg.finalize(pts, a_hole_um, family="concentric", N_requested=N,
                       nominal_spacing_desc={"ring_spacing_um": float(ring_spacing_um),
                                              "holes_per_ring0": int(holes_per_ring0),
                                              "ring_count_rule": "round(holes_per_ring0*k) "
                                                                 "-- constant angular spacing"})
