"""
concentric_centered.py -- ring_offset_concentric.py's own ring construction
(SAME ring_spacing_um / holes_per_ring0 / alternating-offset formula --
reproduced verbatim below and attributed, matching that module's own
established convention for reusing concentric.py's ring formula, since
neither concentric.py nor ring_offset_concentric.py exposes its per-ring
construction as a standalone callable), PLUS one hole placed at (0,0),
consuming one N_requested slot (N_requested=20 -> 1 center hole + 19 ring
points, not 20+1).

CORRECTION TO THIS FAMILY'S OWN MOTIVATION, established by direct
investigation before writing this file, not assumed: ring_offset_concentric.py
(and concentric.py) do NOT skip a center hole "because rings start at k=1" --
both already start their own point list with a literal `pts =
[np.array([0.0, 0.0])]`. Confirmed empirically: a naive "prepend (0,0), then
reuse the ring loop unchanged" implementation of THIS file produces
BIT-IDENTICAL coordinates to ring_offset_concentric.generate() for the same
inputs (checked directly, max diff = 0.0) -- because that is already exactly
what ring_offset_concentric.py's own construction does. The real reason
neither family's FINAL output has a hole at the origin is
generators/base_generator.py's own shared finalize()/recenter_on_centroid()
step (applied identically to every one of this project's 10 families): it
shifts the whole pattern by -mean(all kept points). A COMPLETE ring (all n_k
points evenly spaced around a full 2*pi) always sums to exactly (0,0) by
rotational symmetry, so a whole number of complete rings never disturbs
this -- but a TRUNCATED final ring (whenever N does not exactly fill an
integer number of complete rings, the common case for an arbitrary N) does
not sum to zero, and the shared recenter step then shifts the nominal center
hole away from the origin by exactly that leftover imbalance. Confirmed
directly against the CONFIRMED FINDING this family was built to test:
ring_offset_concentric's own N=20, ring_spacing_um=4000, holes_per_ring0=8
candidate (its M=2-3 winner) has its nominal center hole recentred to
1704.8um from the origin -- reproduced bit-for-bit by the naive
"prepend-then-recenter-together" construction above, confirming this is the
actual mechanism, not a coincidence.

FIX, THE ACTUAL VALUE THIS FILE ADDS: recenter the RING points ON THEIR OWN
centroid FIRST (via base_generator's own reject_overlapping +
recenter_on_centroid, called directly, not through finalize()'s combined
wrapper), THEN prepend the (0,0) center hole, THEN run finalize() once more
on the combined set. Since the ring points are already exactly zero-mean
after their own recentering, and the center hole contributes (0,0) to any
mean, the COMBINED set's mean is exactly (0,0) by construction -- the final
finalize() call's own recenter_on_centroid() is provably a no-op, and the
center hole survives at EXACTLY (0,0) regardless of whether the ring
construction ends on a complete or a partial ring. Verified directly: the
SAME N=20/ring_spacing_um=4000/holes_per_ring0=8 case that displaced
ring_offset_concentric's own center hole by 1704.8um gives a center-hole
displacement of 1.6e-13 (floating-point noise) here.

This is the one substantive difference from ring_offset_concentric.py -- the
ring-count/radius/alternating-offset formula itself is untouched, reproduced
verbatim, not redesigned.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402
import ring_offset_concentric  # noqa: E402 -- module-level import for
                                # traceability, matching that module's own
                                # convention for concentric.py (see this
                                # file's own docstring for why its ring
                                # formula is reproduced verbatim below rather
                                # than called).


def generate(N, a_hole_um, ring_spacing_um, holes_per_ring0):
    """One hole reserved at (0,0); the remaining N-1 slots are filled by
    ring_offset_concentric.py's own ring-count/radius/alternating-offset
    formula verbatim (k=1,2,3,..., n_k=round(holes_per_ring0*k),
    r_k=k*ring_spacing_um, odd k offset by half its own angular step). See
    module docstring for why the ring points are recentred on their own
    centroid BEFORE the center hole is added, not after."""
    n_ring_slots = max(0, N - 1)
    ring_pts = []
    k = 1
    while len(ring_pts) < n_ring_slots:
        n_k = max(1, int(round(holes_per_ring0 * k)))
        r_k = k * ring_spacing_um
        angular_step = 2 * np.pi / n_k
        offset = (angular_step / 2.0) if (k % 2 == 1) else 0.0  # ALTERNATING,
                                                                  # matches
                                                                  # ring_offset_concentric.py
        thetas = np.linspace(0.0, 2 * np.pi, n_k, endpoint=False) + offset
        ring_pts.extend([np.array([r_k * np.cos(t), r_k * np.sin(t)]) for t in thetas])
        k += 1
        if k > 500:  # same hard safety stop as concentric.py / ring_offset_concentric.py
            break
    ring_pts = np.array(ring_pts[:n_ring_slots]) if ring_pts else np.empty((0, 2))

    # Recenter the ring points ON THEIR OWN, before the center hole exists --
    # see module docstring for why this is what makes the center hole land at
    # EXACTLY (0,0) regardless of partial-ring truncation.
    if len(ring_pts) > 0:
        ring_pts = bg.reject_overlapping(ring_pts, a_hole_um)
        ring_pts = bg.recenter_on_centroid(ring_pts)

    combined = (np.vstack([[[0.0, 0.0]], ring_pts]) if len(ring_pts) > 0
               else np.array([[0.0, 0.0]]))

    return bg.finalize(combined, a_hole_um, family="concentric_centered", N_requested=N,
                       nominal_spacing_desc={"ring_spacing_um": float(ring_spacing_um),
                                              "holes_per_ring0": int(holes_per_ring0),
                                              "ring_count_rule": "round(holes_per_ring0*k) "
                                                                 "-- matches ring_offset_concentric.py",
                                              "offset_rule": "alternating: odd rings "
                                                             "offset by half their own "
                                                             "angular step, even rings none "
                                                             "-- matches ring_offset_concentric.py",
                                              "center_hole": "one explicit hole at (0,0), "
                                                             "consuming one N_requested slot; "
                                                             "ring points pre-recentred on their "
                                                             "own centroid so this survives exactly "
                                                             "-- see module docstring"})


def verify_center_hole_sanity(D_pupil_um=4000.0, a_hole_um=2000.0):
    """REQUIRED sanity check (this family's own task brief): confirm the
    center hole yields 100% overlap (d=0 case) via the SAME overlap_area_um2
    check used elsewhere in this project (active_pairs.py's own
    hole_illumination_fractions, engine/vignetting_overlap.py's validated
    overlap_area_um2 -- imported directly here, not reimplemented).

    Uses N=9, ring_spacing_um=4000, holes_per_ring0=8: n_ring_slots=8 exactly
    fills ring 1 (round(8*1)=8) -- a COMPLETE ring, so even the naive
    'prepend-then-recenter-together' construction would also center exactly
    here (see module docstring) -- but this test exercises this module's own
    generate(), including a case (N=20 below) with a genuinely PARTIAL final
    ring, to confirm the fix actually generalizes, not just the trivial
    complete-ring case."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "margins"))
    import active_pairs as ap  # noqa: E402 -- reused read-only, not modified;
                                # this IS array_calculation code calling
                                # array_calculation code, not a layer-contract
                                # concern (that contract only bars
                                # array_evaluation/ from importing
                                # array_calculation/).

    results = {}
    for N, ring_spacing_um, holes_per_ring0, label in [
        (9, 4000.0, 8, "N=9 (ring 1 exactly complete)"),
        (20, 4000.0, 8, "N=20 (partial ring 2 -- the displaced case)"),
    ]:
        coords, meta = generate(N=N, a_hole_um=a_hole_um, ring_spacing_um=ring_spacing_um,
                                holes_per_ring0=holes_per_ring0)
        dist_from_origin = np.linalg.norm(coords, axis=1)
        nearest_idx = int(np.argmin(dist_from_origin))
        d_um = float(dist_from_origin[nearest_idx])
        fractions, areas = ap.hole_illumination_fractions(coords, D_pupil_um, a_hole_um)
        f_nearest = float(fractions[nearest_idx])
        results[label] = {"N_actual": len(coords), "d_um": d_um, "overlap_fraction": f_nearest}
        print(f"{label}: N_actual={len(coords)}  nearest-hole distance={d_um:.6e}um  "
              f"overlap_fraction={f_nearest:.6f}  (expect 1.0)")
        assert np.isclose(f_nearest, 1.0, atol=1e-6), (
            f"expected overlap_fraction=1.0 (d=0 case) for {label}, got {f_nearest}")
    print("center-hole sanity check PASSED: overlap_fraction=1.0 (100% overlap) confirmed "
          "via active_pairs.hole_illumination_fractions / engine/vignetting_overlap.overlap_area_um2, "
          "for both a complete-ring N and a partial-ring N.")
    return results


if __name__ == "__main__":
    verify_center_hole_sanity()
