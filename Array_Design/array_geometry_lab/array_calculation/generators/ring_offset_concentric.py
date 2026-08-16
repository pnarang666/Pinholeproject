"""Ring-offset concentric generator ("brick" pattern): a variant of concentric.py
where ALTERNATING rings get a half-angular-step rotation offset relative to their
un-rotated position, so holes on adjacent rings sit staggered rather than aligned
radially -- the same visual idea as staggered brick courses.

REUSES concentric.py's own ring-spacing/holes-per-ring formulas (imported at module
level below) rather than duplicating them -- permitted per this folder's own rule that
new files within array_geometry_lab/ may import from each other (the "copy, don't
import" rule from Part 1 applies only to the array_optimization/ boundary). concentric.py
does not expose its per-ring construction as a standalone callable (it is inline in
generate()), so there is no single function to call directly; the ring-count formula
(round(holes_per_ring0*k) holes on ring k, radius k*ring_spacing_um) is reproduced here
verbatim and attributed, not silently re-derived, and importing the `concentric` module
itself (below) keeps this file's dependency on it explicit and traceable.

EXPLICIT DESIGN DECISION -- ALTERNATING, NOT PROGRESSIVE OFFSET:
Two ways to stagger rings were considered: (a) ALTERNATING -- every other ring (odd k)
gets a fixed offset of half that ring's own angular step (pi/n_k radians), even rings
get none, so the pattern repeats every 2 rings (the brick-course analogy); (b)
PROGRESSIVE -- each successive ring's offset increases by a fixed increment
(cumulative), producing a spiral-like drift rather than a repeating brick course.
This file implements ONLY (a) -- chosen as the more literal reading of "brick pattern"
(real brick courses alternate, they don't progressively drift) and because it is the
simpler, unambiguous construction. (b) is a plausible future variant, noted here, not
implemented -- shipping both under one flag was considered and rejected as
over-engineering for a pattern this folder has not yet found a use for.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402
import concentric  # noqa: E402  (module-level import for traceability -- see docstring
                    # for why its ring formula is reproduced, not called, here)


def generate(N, a_hole_um, ring_spacing_um, holes_per_ring0):
    """Ring-count/ring-radius formula matches concentric.generate() exactly (see that
    file and this module's docstring); the only addition is the alternating half-step
    rotation on odd-indexed rings."""
    pts = [np.array([0.0, 0.0])]  # ring 0: single center hole, same as concentric.py
    k = 1
    while len(pts) < N:
        n_k = max(1, int(round(holes_per_ring0 * k)))
        r_k = k * ring_spacing_um
        angular_step = 2 * np.pi / n_k
        offset = (angular_step / 2.0) if (k % 2 == 1) else 0.0  # ALTERNATING: odd
                                                                  # rings get a
                                                                  # half-step offset,
                                                                  # even rings none
        thetas = np.linspace(0.0, 2 * np.pi, n_k, endpoint=False) + offset
        pts.extend([np.array([r_k * np.cos(t), r_k * np.sin(t)]) for t in thetas])
        k += 1
        if k > 500:  # same hard safety stop as concentric.py
            break

    pts = np.array(pts[:N])

    return bg.finalize(pts, a_hole_um, family="ring_offset_concentric", N_requested=N,
                       nominal_spacing_desc={"ring_spacing_um": float(ring_spacing_um),
                                              "holes_per_ring0": int(holes_per_ring0),
                                              "ring_count_rule": "round(holes_per_ring0*k) "
                                                                 "-- matches concentric.py",
                                              "offset_rule": "alternating: odd rings "
                                                             "offset by half their own "
                                                             "angular step, even rings none"})
