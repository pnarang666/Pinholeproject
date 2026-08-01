"""
Schematic eye ray/distance diagram: aperture -> d_gap -> cornea -> lens -> v_r ->
retina, to scale using the ACTUAL L0/L_ax/f_eye numbers for the current point (never
fabricated anatomy). Explicitly labeled "schematic, not anatomical" everywhere it's
shown -- this is a distances-to-scale diagram, not a rendering of real ocular geometry.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def draw_eye_diagram(a_hole_um, d_gap_mm, L0_mm, v_r_mm, f_eye_mm, M_diopters):
    """Returns a matplotlib Figure: a labeled, to-scale (in the propagation-distance
    axis only) schematic of pinhole -> gap -> cornea/lens -> retina."""
    fig, ax = plt.subplots(figsize=(9, 3.2))

    x_pinhole = 0.0
    x_cornea = d_gap_mm
    x_retina = d_gap_mm + v_r_mm

    # Pinhole (aperture) -- drawn with an exaggerated height since a_hole_um is
    # microns and the propagation axis is millimeters; NOT to the same scale as x.
    aperture_half_height = 0.6
    ax.plot([x_pinhole, x_pinhole], [-aperture_half_height, -0.08], color="black", lw=3)
    ax.plot([x_pinhole, x_pinhole], [0.08, aperture_half_height], color="black", lw=3)
    ax.annotate(f"pinhole\n{a_hole_um:.0f} um", (x_pinhole, aperture_half_height + 0.15),
                ha="center", fontsize=8)

    # Cornea/lens plane
    ax.plot([x_cornea, x_cornea], [-0.5, 0.5], color="#2a78d6", lw=2)
    ax.annotate("cornea + lens\n(fixed power P0)", (x_cornea, 0.65), ha="center", fontsize=8, color="#2a78d6")

    # Retina plane
    ax.plot([x_retina, x_retina], [-0.5, 0.5], color="#e34948", lw=2)
    ax.annotate(f"retina\nv_r={v_r_mm:.2f}mm", (x_retina, 0.65), ha="center", fontsize=8, color="#e34948")

    # Emmetropic focal point (L0) for reference, if it differs from v_r
    x_focus = x_cornea + L0_mm
    if abs(x_focus - x_retina) > 1e-6:
        ax.axvline(x_focus, color="gray", linestyle=":", alpha=0.7)
        ax.annotate(f"emmetropic focus\n(f_eye={f_eye_mm:.2f}mm)", (x_focus, -0.75), ha="center", fontsize=7, color="gray")

    # Rays: converging lines from aperture edge through cornea to retina
    for y0 in (-aperture_half_height * 0.5, aperture_half_height * 0.5):
        ax.plot([x_pinhole, x_cornea], [y0, 0], color="black", lw=0.6, alpha=0.5)
        ax.plot([x_cornea, x_retina], [0, 0], color="black", lw=0.6, alpha=0.3, linestyle="--")

    ax.set_xlim(-2, x_retina + 3)
    ax.set_ylim(-1, 1)
    ax.set_yticks([])
    ax.set_xlabel("distance (mm) -- horizontal axis to scale; vertical axis exaggerated for visibility")
    ax.set_title(f"SCHEMATIC, NOT ANATOMICAL -- pinhole-to-retina distances only (M={M_diopters:.0f}D)",
                 fontsize=10, style="italic")
    fig.tight_layout()
    return fig
