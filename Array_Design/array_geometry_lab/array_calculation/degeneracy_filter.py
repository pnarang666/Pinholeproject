"""
Shared degeneracy-exclusion AND density-area logic for the density/packing-quality
pipeline -- single source of truth, not duplicated anywhere downstream.

AUDIT FIX (Defect A -- the density metric was apples-to-oranges): this module used
to compute bounding area with a DIFFERENT formula per family "shape" -- unit-cell
(N_actual * cell_area) for square/hexagonal/rectangular, buffered enclosing-circle
for concentric/ring_offset_concentric, buffered convex hull for the remaining five.
Confirmed by direct controlled test: the SAME physical hole arrangement scored
1.56x-2.25x differently depending on which formula its family happened to use
(worst at small N, which every tested Metric-1 winner had) -- the unit-cell formula
systematically PENALIZED square/hexagonal/rectangular relative to every hull-based
family, biasing the whole comparison pipeline toward hull-based families regardless
of their actual physical packing.

FIX: ONE family-agnostic area formula, applied IDENTICALLY to every one of the 10
families -- the buffered (Minkowski-offset) convex hull of the actual generated hole
coordinates: area = hull.volume + hull.area*R_h + pi*R_h**2 (see convex_hull_area()
below). The unit-cell and enclosing-circle area FORMULAS are gone entirely (not left
dead) -- every family's coordinates are now regenerated and hulled the same way.
Verified (comparison_metric/README.md and this module's own callers) that
geometrically IDENTICAL arrangements across different families now produce
BIT-IDENTICAL density -- the property the old per-family-formula design could never
have, by construction.

unit_cell_area() is KEPT, but its role NARROWED: it is no longer used to compute
density for square/hexagonal/rectangular -- it is used ONLY as a fast, no-regeneration-
needed FEASIBILITY pre-check (see LATTICE_FEASIBILITY_FAMILIES below) for those three
families specifically, since only a periodic lattice has a single well-defined
"nominal pitch" to check against the hole diameter before bothering to regenerate
coordinates and compute a hull at all.

Two degeneracy mechanisms now apply, in order:

1. LATTICE FEASIBILITY (square, rectangular, hexagonal ONLY, checked FIRST, no
   coordinate regeneration needed): excluded if the row's own hole_footprint_area
   (pi/4*a_hole_um**2) exceeds its OWN nominal cell_area (from unit_cell_area()) --
   independent of N_actual entirely, since N_actual cancels out of that ratio
   (confirmed: identical a_hole_um/pitch_um ratio produces bit-identical
   open_area_fraction across wildly different N_actual). No N_actual floor can catch
   this -- it is a property of the requested pitch/hole-size combination itself, not
   of how many points survive overlap rejection.

2. HULL VALIDITY (every family, including the three above once they pass check 1):
   excluded if
   - N_actual < MIN_N_ACTUAL_HULL -- a HARD MATHEMATICAL MINIMUM (no convex hull
     exists below 3 points), not a judgment call. (Formerly square/hexagonal/
     rectangular used a stricter, formula-specific floor of 4 -- that floor's own
     justification, "a unit-cell-area x count formula isn't meaningful below a ~2x2
     tiling," no longer applies once the unit-cell formula itself is gone; unified
     to the hull's own hard minimum of 3 for every family, an intentional
     consequence of "one measure applied identically to everyone," not an
     oversight); OR
   - the buffered hull area is pathologically small relative to N_actual*a_hole_um**2
     -- a near-collinear/near-coincident point set.

is_degenerate(row) needs the ACTUAL regenerated coordinates for check 2 (the
buffered hull area cannot be computed from N_actual and spacing alone) -- it calls
this family's own generators/*.py generate() with the exact
(N_requested, a_hole_um, spacing_params, seed) recorded on the row.

`row` is anything with attribute access to family, N_requested, N_actual,
spacing_params, a_hole_um, seed (a pandas itertuples() row or Series both work --
this module makes no assumption beyond attribute access).
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull
try:
    from scipy.spatial import QhullError
except ImportError:
    from scipy.spatial.qhull import QhullError

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "generators"))

import square, hexagonal, concentric, fibonacci_spiral, golden_angle  # noqa: E402
import rectangular, archimedean_spiral, ring_offset_concentric  # noqa: E402
import poisson_disk, jittered_lattice  # noqa: E402

GEN_FUNCS = {
    "square": square.generate, "hexagonal": hexagonal.generate,
    "concentric": concentric.generate, "fibonacci_spiral": fibonacci_spiral.generate,
    "golden_angle": golden_angle.generate, "rectangular": rectangular.generate,
    "archimedean_spiral": archimedean_spiral.generate,
    "ring_offset_concentric": ring_offset_concentric.generate,
    "poisson_disk": poisson_disk.generate, "jittered_lattice": jittered_lattice.generate,
}

ALL_FAMILIES = set(GEN_FUNCS.keys())
# LATTICE_FEASIBILITY_FAMILIES: the three families with a single well-defined
# "nominal pitch" to run the fast feasibility pre-check (step 1) against, BEFORE
# regenerating coordinates -- NOT a density-formula grouping anymore (every family
# uses convex_hull_area() for density, unconditionally; see module docstring).
LATTICE_FEASIBILITY_FAMILIES = {"square", "rectangular", "hexagonal"}

# --- degeneracy thresholds -- MODELING JUDGMENT CALLS, not physical constants,
# except where noted ---
MIN_N_ACTUAL_HULL = 3       # hard mathematical minimum, not a judgment call -- now
                             # applies to EVERY family (see module docstring for why
                             # the former unit-cell-specific floor of 4 was retired,
                             # not merely forgotten)
MIN_AREA_PER_HOLE_RATIO = 0.05  # deliberately looser than the physical
                                 # open_area_fraction<=1 check performed
                                 # independently downstream -- this only catches
                                 # area estimates so small they are not even a sane
                                 # starting point (e.g. a near-zero-area sliver hull)
OPEN_AREA_FEASIBILITY_TOLERANCE = 1.0001  # floating-point slack only


def parse_spacing_params(s):
    d = {}
    if pd.isna(s) or s == "":
        return d
    for part in str(s).split(";"):
        k, v = part.split("=")
        try:
            v = float(v)
        except ValueError:
            pass
        d[k] = v
    return d


def unit_cell_area(family, kwargs, N_actual):
    """NARROWED ROLE (see module docstring, Defect A fix): this is NO LONGER the
    density formula for square/hexagonal/rectangular -- it exists ONLY to compute
    a NOMINAL cell_area for the fast feasibility pre-check in is_degenerate(), which
    needs to know whether the requested pitch can geometrically host a hole of the
    given size AT ALL, before bothering to regenerate coordinates. The actual density
    value used everywhere downstream comes from convex_hull_area(), unconditionally,
    for every family including these three.

    square, rectangular: N_actual * pitch_x_um * pitch_y_um (unit cell area x
    count -- for square, pitch_x=pitch_y=pitch_um, i.e. this reduces to
    N_actual * pitch_um**2). hexagonal: N_actual * (sqrt(3)/2) * pitch_um**2, the
    area of a single hexagonal unit cell (a rhombus with side pitch_um and 60/120
    degree angles) times count -- the standard closed-form hex-lattice cell area."""
    if family == "hexagonal":
        pitch = kwargs["pitch_um"]
        return N_actual * (np.sqrt(3) / 2.0) * pitch ** 2
    if family == "rectangular":
        return N_actual * kwargs["pitch_x_um"] * kwargs["pitch_y_um"]
    if family == "square":
        pitch = kwargs["pitch_um"]
        return N_actual * pitch * pitch
    raise ValueError(family)


def convex_hull_area(coords, a_hole_um):
    """THE density-area formula for EVERY family (Defect A fix -- see module
    docstring): convex hull area of the actual generated coordinates, buffered
    outward (Minkowski sum) by the hole radius r=a_hole_um/2:
    buffered_area = hull_area + hull_perimeter * r + pi * r**2
    -- the standard closed-form area of a convex polygon offset outward by a constant
    radius r (each straight edge sweeps out a rectangle of edge_length * r; each
    vertex sweeps a circular wedge, and a convex polygon's exterior-angle wedges sum
    to exactly one full circle of radius r, giving the final + pi*r**2 term). The
    buffer is a CORRECTNESS fix, not an embellishment: a hull built from hole
    CENTERS omits the physical margin each hole disk extends past its own center --
    confirmed necessary with a real counterexample found in production (a
    `concentric` row, N_actual=7, ring_spacing_um=700, a_hole_um=2000, where every
    pairwise hole-center distance is legitimately >= a_hole_um -- a genuinely valid,
    non-overlapping configuration -- still produced open_area_fraction=1.587
    (physically impossible) using the un-buffered hull area; the buffered version
    brings the identical case down to a physically sane 0.728).
    `ConvexHull.volume` is the 2D area and `ConvexHull.area` is the 2D perimeter --
    scipy's own (confusing but documented) naming for a 2D hull. NaN for fewer than
    3 points (no hull exists) or a degenerate (collinear/coincident) point set
    QhullError raises on."""
    if len(coords) < 3:
        return np.nan
    try:
        hull = ConvexHull(coords)
        r = a_hole_um / 2.0
        return float(hull.volume + hull.area * r + np.pi * r ** 2)
    except QhullError:
        return np.nan


def is_degenerate(row):
    """Returns (is_degenerate: bool, reason: str or None).

    reason is None iff is_degenerate is False. Applies EXACTLY the two-mechanism
    exclusion logic described in this module's own docstring, using only
    (family, N_requested, N_actual, spacing_params, a_hole_um, seed) off `row` --
    identical to what compute_density.py's own inline version used before this
    extraction. For hull/enclosing-circle families this regenerates coordinates
    (deterministic given the same inputs) and raises RuntimeError -- not a
    degenerate classification, a hard stop -- if the regenerated N_actual doesn't
    match the row's own recorded N_actual, since that would mean the generator
    isn't reproducing the original row at all, a different and more serious
    problem than ordinary degeneracy."""
    family = row.family
    kwargs = parse_spacing_params(row.spacing_params)
    N_actual = int(row.N_actual)

    # --- Step 1: lattice feasibility pre-check (square/hexagonal/rectangular ONLY,
    # no coordinate regeneration needed -- fast, and independent of N_actual, see
    # module docstring) ---
    if family in LATTICE_FEASIBILITY_FAMILIES:
        nominal_area = unit_cell_area(family, kwargs, N_actual)
        hole_footprint_area = np.pi / 4.0 * row.a_hole_um ** 2
        cell_area = nominal_area / N_actual
        if hole_footprint_area > cell_area * OPEN_AREA_FEASIBILITY_TOLERANCE:
            return True, (f"hole_footprint_area={hole_footprint_area:.4e}um^2 > "
                          f"cell_area={cell_area:.4e}um^2 (requested pitch cannot "
                          f"geometrically host a hole of this size as a periodic "
                          f"tiling, independent of N_actual)")

    # --- Step 2: hull validity, EVERY family (unconditional since Defect A's fix --
    # see module docstring for why the floor is now 3 uniformly, not 4 for the
    # three lattice families above) ---
    if N_actual < MIN_N_ACTUAL_HULL:
        return True, (f"N_actual={N_actual} < MIN_N_ACTUAL_HULL={MIN_N_ACTUAL_HULL} "
                      f"(convex hull area is mathematically undefined below 3 points)")
    gen_kwargs = dict(kwargs)
    if pd.notna(row.seed):
        gen_kwargs["seed"] = int(row.seed)
    coords, meta = GEN_FUNCS[family](N=int(row.N_requested), a_hole_um=row.a_hole_um, **gen_kwargs)
    if int(meta["N_actual"]) != N_actual:
        raise RuntimeError(
            f"regeneration mismatch for {family} N_requested={row.N_requested} "
            f"spacing={row.spacing_params} seed={row.seed} a_hole_um={row.a_hole_um}: "
            f"row says N_actual={N_actual}, regenerated={meta['N_actual']} -- "
            f"generator is not reproducing the original row, STOP and investigate.")

    area = convex_hull_area(coords, row.a_hole_um)

    if not np.isfinite(area) or area <= 0:
        return True, f"area computation returned {area} (degenerate point set)"

    min_plausible_area = MIN_AREA_PER_HOLE_RATIO * N_actual * row.a_hole_um ** 2
    if area < min_plausible_area:
        return True, (f"area={area:.4e}um^2 < MIN_AREA_PER_HOLE_RATIO*N_actual*"
                      f"a_hole_um^2={min_plausible_area:.4e}um^2 (pathologically "
                      f"small/near-collinear hull)")
    return False, None
