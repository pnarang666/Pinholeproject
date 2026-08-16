"""Fibonacci/Vogel spiral: r_n = c*sqrt(n), theta_n = n*golden_angle, n = 1..N.
c_um (radial scale) is the free spacing parameter -- larger c spreads holes further
apart for the same N. golden_angle = 137.50776...deg (2*pi*(1 - 1/phi), phi the golden
ratio), the irrational angle that maximizes packing uniformity for this family
(Vogel 1979). This is the SAME formula this folder's golden_angle.py generator uses --
see that file's docstring for why it re-exports this one rather than duplicating it."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402

GOLDEN_ANGLE_RAD = np.pi * (3.0 - np.sqrt(5.0))  # = 2*pi*(1 - 1/phi) ~= 137.50776 deg


def generate(N, a_hole_um, c_um, family_name="fibonacci_spiral"):
    """family_name is overridden by golden_angle.py's thin wrapper so metadata
    correctly self-reports which requested filename produced a given output, even
    though both call this exact same implementation."""
    n = np.arange(1, N + 1)
    r = c_um * np.sqrt(n)
    theta = n * GOLDEN_ANGLE_RAD
    pts = np.column_stack([r * np.cos(theta), r * np.sin(theta)])

    return bg.finalize(pts, a_hole_um, family=family_name, N_requested=N,
                       nominal_spacing_desc={"c_um": float(c_um),
                                              "golden_angle_deg": float(np.degrees(GOLDEN_ANGLE_RAD))})
