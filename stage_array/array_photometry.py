"""
Array photometry: how much light actually reaches the retina through a MULTI-HOLE
pinhole array, as opposed to stage3a's single-aperture relative_illuminance().

This is a RESTORED file -- the original was lost during a project reorganization.
Rebuilt verbatim from verified conversation history, not re-derived from scratch.
array_ghosting_theory/ghosting_regime.py and harmonic_analysis.py both directly
depend on this module (sys.path insert to "../stage_array") -- without this file,
neither of those scripts can run.

This module does not modify stage1_v2, stage2, stage2_fixed, stage3a, or
stage3_human_vision -- it is a new, independent module that reuses their published
radius/illuminance data as inputs, not their code paths.

THE KEY PHYSICAL SUBTLETY THIS MODULE IS BUILT AROUND, STATED UP FRONT:

The naive treatment (used in the project's own Master Formulas doc, Eq. "T = N*pi*a^2/4
/ A_total") treats the perforated sheet as a spatially-averaged neutral-density filter --
correct ONLY when hole pitch s is much smaller than the pupil diameter D_pupil, so many
holes sit under the pupil at any instant and a continuum/area-fraction average applies.

Checked against the two real patents examined in this project (Chapter 8): KR
10-2081511 uses hole pitch 3.2-4.8mm; CN 201716487U uses 0.7-1.2mm. Natural pupil
diameter is ~3-4mm (this project's default: 4mm). These pitches are NOT much smaller
than the pupil -- they are comparable to it. That means the continuum approximation is
questionable for real designs, and the actual number of holes under the pupil at any
instant is a small integer (often 1-4), NOT a smooth average -- and that integer count is
sensitive to the exact alignment between the pupil center and the hole lattice, which
shifts continuously as the eye's pupil moves (a real, physical effect the eyewear
designer cannot control).

This module computes BOTH: the continuum estimate (for comparison / sanity-check), and
an exact discrete lattice enumeration showing how much N_eff actually varies with
alignment -- rather than silently reporting only the smoother, more optimistic number.
"""

import numpy as np


def pupil_area(D_pupil_um):
    return np.pi * (D_pupil_um / 2.0) ** 2


def hole_area(a_hole_um):
    return np.pi * (a_hole_um / 2.0) ** 2


def n_holes_continuum(s_um, D_pupil_um, packing="square"):
    """
    Continuum (area-ratio) estimate of holes under the pupil: pupil_area / (area per
    lattice point). Valid only when s << D_pupil -- see module docstring. Returns a
    real number (not rounded), since this is an average-density estimate, not a count.

    packing: "square" (area per point = s^2) or "hex" (area per point = s^2 * sqrt(3)/2,
    i.e. hex packing fits ~1.1547x more points per unit area than square for the same
    nearest-neighbor spacing s).
    """
    if packing == "square":
        area_per_point = s_um ** 2
    elif packing == "hex":
        area_per_point = s_um ** 2 * (np.sqrt(3) / 2.0)
    else:
        raise ValueError("packing must be 'square' or 'hex'")
    return pupil_area(D_pupil_um) / area_per_point


def hole_lattice(s_um, extent_um, packing="square"):
    """Generates (x, y) hole-center coordinates for a lattice covering a square region
    of the given extent, centered at the origin. Used for exact discrete enumeration."""
    n = int(np.ceil(extent_um / s_um)) + 2
    if packing == "square":
        xs = (np.arange(-n, n + 1)) * s_um
        ys = (np.arange(-n, n + 1)) * s_um
        X, Y = np.meshgrid(xs, ys)
    elif packing == "hex":
        row_h = s_um * np.sqrt(3) / 2.0
        rows = np.arange(-n, n + 1)
        pts = []
        for r in rows:
            y = r * row_h
            x_offset = (s_um / 2.0) if (r % 2) else 0.0
            xs = np.arange(-n, n + 1) * s_um + x_offset
            pts.append(np.column_stack([xs, np.full_like(xs, y, dtype=float)]))
        pts = np.vstack(pts)
        X, Y = pts[:, 0], pts[:, 1]
    else:
        raise ValueError("packing must be 'square' or 'hex'")
    return np.ravel(X), np.ravel(Y)


def n_holes_exact(s_um, D_pupil_um, packing="square", pupil_offset=(0.0, 0.0)):
    """
    Exact count of hole centers falling within the pupil circle, for a given lattice
    alignment offset. Approximates each hole as fully-in or fully-out based on its
    CENTER position -- valid when a_hole << D_pupil (true throughout this project:
    tested a_hole is 300-1000um vs D_pupil=4000um, ratio <25%), since at that ratio a
    hole whose center is inside/outside the pupil boundary has only a small partially-
    clipped edge case contribution. Not exact for a_hole approaching D_pupil.
    """
    X, Y = hole_lattice(s_um, D_pupil_um * 0.75, packing=packing)
    ox, oy = pupil_offset
    dist2 = (X - ox) ** 2 + (Y - oy) ** 2
    R = D_pupil_um / 2.0
    return int(np.sum(dist2 <= R ** 2))


def n_holes_exact_sweep_alignment(s_um, D_pupil_um, packing="square", n_offsets=25):
    """
    Sweeps the pupil center over one lattice unit cell (the alignment the eyewear
    designer cannot control, since it depends on where the wearer's pupil happens to
    sit relative to the fixed hole pattern) and returns (min, mean, max) N_eff observed.
    This is the number that actually matters for a design margin -- the worst case, not
    just the average.
    """
    offsets_x = np.linspace(0, s_um, n_offsets, endpoint=False)
    offsets_y = np.linspace(0, s_um, n_offsets, endpoint=False)
    counts = []
    for ox in offsets_x:
        for oy in offsets_y:
            counts.append(n_holes_exact(s_um, D_pupil_um, packing=packing, pupil_offset=(ox, oy)))
    counts = np.array(counts)
    return int(counts.min()), float(counts.mean()), int(counts.max())


def relative_retinal_illuminance_array(a_hole_um, s_um, D_pupil_um, packing="square",
                                        alignment="worst_case", n_offsets=25):
    """
    THE MAIN RESULT: actual retinal illuminance through the array, as a fraction of full
    natural-pupil brightness (directly comparable to stage3a's single-hole E_rel).

    E_rel_array = min(N_eff * hole_area, pupil_area) / pupil_area

    alignment: "worst_case" (uses the minimum N_eff found across the alignment sweep --
    the conservative, guaranteed-at-least-this-bright design number), "mean" (average
    over alignment, an optimistic/typical-case estimate), or "best_case".
    """
    n_min, n_mean, n_max = n_holes_exact_sweep_alignment(s_um, D_pupil_um, packing, n_offsets)
    n_eff = {"worst_case": n_min, "mean": n_mean, "best_case": n_max}[alignment]
    open_area = min(n_eff * hole_area(a_hole_um), pupil_area(D_pupil_um))
    e_rel = open_area / pupil_area(D_pupil_um)
    return {"E_rel_array": e_rel, "N_eff": n_eff, "N_eff_min": n_min, "N_eff_mean": n_mean, "N_eff_max": n_max}


def global_transmission(a_hole_um, s_um, lens_diameter_mm=50.0, packing="square"):
    """
    Whole-lens open-area fraction T = N_total * hole_area / A_total (Master Formulas doc
    Eq., T = N*pi*a^2/4 / A_total) -- the "how dark do the glasses look overall" metric,
    DISTINCT from retinal illuminance above. A typical adult sunglass lens is ~50mm
    diameter; overridable since real frame size varies.
    """
    A_total = np.pi * (lens_diameter_mm * 1000 / 2.0) ** 2  # mm -> um
    N_total = n_holes_continuum(s_um, lens_diameter_mm * 1000, packing=packing)
    return N_total * hole_area(a_hole_um) / A_total


def no_ghost_max_pitch(r_EE_P_um, d_gap_um, v_r_um):
    """
    Ghosting constraint (Master Formulas doc): s < r_EE(P) * d_gap / v_r. Returns the
    maximum pitch that keeps adjacent holes' retinal images from separating into visible
    ghost images, given the ACTUAL numerically-computed r_EE(P) for this a_hole/M
    (never the deprecated r_total formula -- see Model Comparison, Chapter 7).
    """
    return r_EE_P_um * d_gap_um / v_r_um
