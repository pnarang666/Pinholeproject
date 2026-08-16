"""Archimedean spiral: r = c*theta (theta in radians, UNWRAPPED -- grows without bound,
not reduced mod 2*pi), the curve where each full revolution increases r by the same
constant amount 2*pi*c ("constant radial spacing" between successive wraps -- the
defining property of this spiral family, distinct from e.g. a logarithmic spiral).

NOT THE SAME PATTERN AS fibonacci_spiral.py -- STATED EXPLICITLY, SAME STYLE AS
golden_angle.py's IDENTITY DISCLOSURE, BUT THE OPPOSITE CONCLUSION:
fibonacci_spiral.py places point n at r=c*sqrt(n), theta=n*golden_angle -- radius grows
with sqrt(POINT INDEX), and consecutive points are separated by a fixed IRRATIONAL
angle (Vogel's model), never revisiting the same angular direction, which is what gives
that pattern its uniform-packing property. This generator places points along a
CONTINUOUS curve r=c*theta -- radius grows LINEARLY with the swept ANGLE (not with
point index), and consecutive points step forward by a small, radius-dependent
angular increment (see below), spiralling outward along one continuous arm rather than
jumping around by a fixed large angle each time. These produce visibly different point
clouds (confirmed NOT identical in spot_check_generators.py's
archimedean-vs-fibonacci difference check -- the opposite assertion from the
golden_angle identity check) -- this file does not re-implement Vogel's model.

ANGULAR STEP, DERIVED NOT GUESSED: consecutive points are spaced by approximately
a_hole_um*spacing_factor along the spiral's own arc length. For r=c*theta, the
arc-length rate is ds/dtheta = sqrt(r^2 + (dr/dtheta)^2) = sqrt(r^2 + c^2) (since
dr/dtheta = c). A first-order (Euler) step that keeps ds approximately constant at each
point is therefore dtheta = target_spacing / sqrt(r^2 + c^2), evaluated at the CURRENT
r before each step -- a standard local approximation for placing near-evenly-spaced
points along a smooth curve, not an ad hoc angular increment. spacing_factor (default
1.5) matches this project's existing convention of requesting a spacing multiplier
above the physical overlap minimum (a_hole_um itself), same role as
concentric.py/fibonacci_spiral.py's own spacing parameters, before base_generator's
overlap-rejection is applied as the actual hard constraint.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402


def generate(N, a_hole_um, c_um, spacing_factor=1.5):
    target_spacing_um = a_hole_um * spacing_factor
    theta = 0.0
    pts = [np.array([0.0, 0.0])]  # theta=0 -> r=0, a single center hole, matching
                                   # concentric.py's own ring-0 convention
    while len(pts) < N:
        r = c_um * theta
        dtheta = target_spacing_um / np.sqrt(r ** 2 + c_um ** 2)
        theta += dtheta
        r = c_um * theta
        pts.append(np.array([r * np.cos(theta), r * np.sin(theta)]))

    pts = np.array(pts[:N])

    return bg.finalize(pts, a_hole_um, family="archimedean_spiral", N_requested=N,
                       nominal_spacing_desc={"c_um": float(c_um),
                                              "spacing_factor": float(spacing_factor)})
