"""
Shared generator interface for array_geometry_lab/generators/*.py.

A generator function has the signature:

    generate(N, a_hole_um, **pattern_params) -> (coords_um, metadata)

  coords_um : np.ndarray, shape (n_actual, 2), columns (x_um, y_um) -- hole-center
              positions, centered on the pattern's own centroid at the origin (so
              evaluation code can assume phi=0 gaze means "pupil centered at (0,0)"
              without each generator re-deriving that).
  metadata  : dict, always containing at least:
              - "family": generator name (str)
              - "N_requested": the requested hole count (int)
              - "N_actual": len(coords_um) after overlap rejection (int) -- may be
                less than N_requested; see reject_overlapping() below
              - "nominal_spacing_desc": dict of the parameter(s) that define this
                pattern's spacing (one number for lattices, e.g. {"pitch_um": ...};
                multiple for irregular patterns, e.g. {"ring_spacing_um": ...,
                "holes_per_ring0": ...} or {"c_um": ...} for spirals) -- always a
                dict, never a bare number, so callers don't need per-family branches
                just to log what was asked for.

FABRICATION-VALIDITY CONSTRAINT (prior to and separate from ghosting evaluation):
Two holes closer than a_hole_um center-to-center would physically overlap (a_hole_um
is a DIAMETER, this project's standing convention -- confirmed via
array_optimization/stage3_decision/array_candidates.csv's own "N" column). Matches
this project's own established boundary convention (RECOMMENDATION.md: "s <= a_hole
is not an array -- the holes would overlap"): valid requires center-to-center
distance > a_hole_um, i.e. REJECT (not clip/reposition) any candidate whose distance
to an already-accepted hole is <= a_hole_um. Rejection, not repositioning, is used
throughout this folder because repositioning would silently change the pattern's own
geometry (defeating the point of testing a specific, named pattern) -- a design that
requests more holes than can physically fit at the given spacing simply returns fewer
holes than requested, reported honestly via N_actual < N_requested, not silently
patched by moving holes off the pattern.
"""
import numpy as np


def reject_overlapping(coords_um, a_hole_um):
    """Greedily keeps points in their given (generation) order, rejecting any point
    whose center is <= a_hole_um from an already-kept point. Order-dependent by
    construction -- each generator produces points in a natural order (lattice
    scan order, ring-by-ring, spiral index order) and that order is treated as the
    generator's own priority for which holes to keep when a later point would
    collide with an earlier one, since earlier-generated points are typically the
    ones closer to the pattern's own center/origin."""
    if len(coords_um) == 0:
        return np.empty((0, 2))
    kept = [coords_um[0]]
    for p in coords_um[1:]:
        kept_arr = np.array(kept)
        d2 = np.sum((kept_arr - p) ** 2, axis=1)
        if np.all(d2 > a_hole_um ** 2):
            kept.append(p)
    return np.array(kept)


def rotate_points(coords_um, rotation_deg):
    """Rotates coords_um about the origin by rotation_deg (standard 2D rotation
    matrix, counterclockwise positive, degrees). rotation_deg=0.0 returns coords_um
    UNCHANGED (the same array, not a recomputed identity-rotation) -- this is the
    exact-reproduction guarantee square.py/hexagonal.py/rectangular.py's own
    rotation_deg=0.0 default relies on, not merely "numerically close."

    Called on the PRE-finalize (pre-overlap-rejection, pre-recenter) point set, by
    convention -- rotation preserves every pairwise distance and every point's
    distance from the origin, so reject_overlapping()'s greedy result (which point
    indices survive) and the radial closest-N-to-origin selection upstream of it
    are BOTH exactly invariant to rotation; only rotating first (rather than after
    finalize()) needs no separate justification for why N_actual doesn't change
    with rotation_deg -- it's a direct consequence of rotation being an isometry
    that fixes the origin, not a property that has to be re-checked per generator."""
    if rotation_deg == 0.0:
        return coords_um
    theta = np.radians(rotation_deg)
    c, s = np.cos(theta), np.sin(theta)
    R = np.array([[c, -s], [s, c]])
    return coords_um @ R.T


def recenter_on_centroid(coords_um):
    """Recenters a coordinate list on its own centroid -- generators build patterns
    nominally centered at the origin already, but overlap rejection can leave an
    asymmetric leftover set (e.g. if generation order isn't perfectly radial); this
    guarantees phi=0 in evaluation code always means "pupil centered at this
    pattern's actual centroid," not its pre-rejection nominal center."""
    if len(coords_um) == 0:
        return coords_um
    centroid = coords_um.mean(axis=0)
    return coords_um - centroid


def finalize(coords_um, a_hole_um, family, N_requested, nominal_spacing_desc):
    """Every generator calls this at the end: applies overlap rejection, recenters,
    and builds the standard metadata dict -- so the reject/recenter/metadata logic
    is written once, not duplicated five times."""
    coords_um = np.asarray(coords_um, dtype=float)
    accepted = reject_overlapping(coords_um, a_hole_um)
    accepted = recenter_on_centroid(accepted)
    metadata = {
        "family": family,
        "N_requested": int(N_requested),
        "N_actual": int(len(accepted)),
        "a_hole_um": float(a_hole_um),
        "nominal_spacing_desc": dict(nominal_spacing_desc),
    }
    return accepted, metadata
