"""
Which holes are illuminated, and which PAIRS can be simultaneously illuminated,
under the pupil footprint.

DEFECT FIX (audit-confirmed): the previous version of this module marked a hole
"active" iff its CENTER fell within the pupil circle -- a binary, zero-radius-point
test. This both under-counts (a hole 90% overlapping the pupil, center just outside,
counted as fully inactive) and over-counts (a hole whose center is just inside but
barely overlapping counted as fully active). Every n_active_holes/n_active_pairs
value in the dataset, and therefore every ghost margin and gate outcome, inherited
this approximation.

FIX: TRUE partial circle-circle overlap area, via engine/vignetting_overlap.py's
validated overlap_area_um2() -- this folder's own COPY (per its established
copy-not-import convention) of array_optimization/vignetting.py's Handbook 2 Ch.13
geometry, itself validated against an independent Monte Carlo estimate (max error
0.177 percentage points of full hole area, see that module's own docstring). Reused
here, not reimplemented a third time.

Per hole: f_i = A_overlap(hole_i, pupil) / (pi*R_h^2), in [0,1] -- the fraction of
the hole's own area actually inside the pupil. Two SEPARATE quantities are built
from this, kept SEPARATE in the output schema, never collapsed into one:

  1. THRESHOLDED count (n_active_holes / active pairs) -- for pairwise ghost
     enumeration, a hole counts as "active" iff f_i >= active_frac_threshold
     (default 0.5, CLI-configurable via evaluation-level callers). This is a
     discrete yes/no needed because ghost-pair enumeration is inherently
     combinatorial (itertools.combinations over a finite active set).
  2. CONTINUOUS total illuminated area -- sum_i A_overlap(hole_i, pupil), never
     thresholded. This is what comparison_metric/gates.py's gate_viability (Gate 3)
     checks: is ANY light reaching the wearer at all, independent of the pairwise
     ghosting threshold. A design with ten holes each 10% illuminated has
     total_illuminated_area > 0 (viable) even though NONE of them individually
     clear the 50% pairing threshold (n_active_holes == 0) -- these are genuinely
     different questions and must not be conflated.

Unlike array_optimization/'s N_eff work, this module does not sweep a lattice-periodic
"alignment offset" ensemble -- that concept doesn't generalize to non-periodic patterns
(there is no periodic unit cell to sweep one period of). Evaluation here uses a SINGLE
pupil position: centered at the pattern's own centroid (origin, per
generators/base_generator.py's recenter_on_centroid) for phi=0, or offset by the gaze-
angle pupil shift for phi!=0 (evaluation/vignetting_robustness.py). This is a deliberate
scope decision, not an oversight -- stated explicitly per this project's own convention
of not leaving judgment calls implicit.
"""
import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
import vignetting_overlap as vo  # noqa: E402 -- validated circle-overlap geometry,
                                 # this folder's own established copy; see module
                                 # docstring above for the validation reference.

DEFAULT_ACTIVE_FRAC_THRESHOLD = 0.5
# MODELING CHOICE, NOT A PHYSICAL CONSTANT: a hole counts as "active" for PAIRWISE
# GHOST enumeration if at least half its own area is inside the pupil. Below 50%
# overlap, more of the hole's light is being clipped at the vignetted edge than is
# getting through the open aperture, so folding it into full-weight pair enumeration
# would overstate its contribution to a ghost pair; at or above 50%, the majority of
# its light IS getting through, so treating it as a full participant is the
# conservative (safety-biased) choice for a WORST-CASE ghost-margin screen. 0.5 is
# the natural, unbiased midpoint of a binary in/out decision -- it is NOT derived
# from any photometric perceptibility threshold (this project's own scope explicitly
# excludes brightness/transmission as an objective; this threshold governs PAIR
# COUNTING only, not how much light a hole passes). CLI-configurable
# (--active_frac_threshold) by any caller that exposes it; see sweep/run_sweep.py.


def hole_illumination_fractions(coords_um, D_pupil_um, a_hole_um, pupil_center_um=(0.0, 0.0)):
    """Per-hole illumination fraction f_i = A_overlap(hole_i, pupil) / (pi*R_h^2), in
    [0,1] -- TRUE partial-overlap geometry, not the binary center-in-pupil test this
    module used to use. Returns (fractions, areas_um2) -- BOTH, since callers need
    the raw area for total_illuminated_area_um2 (viability) and the fraction for the
    thresholded active/inactive decision (pair enumeration) -- see module docstring."""
    coords_um = np.asarray(coords_um, dtype=float)
    if len(coords_um) == 0:
        return np.array([]), np.array([])
    R_h = a_hole_um / 2.0
    R_p = D_pupil_um / 2.0
    ox, oy = pupil_center_um
    delta = np.sqrt((coords_um[:, 0] - ox) ** 2 + (coords_um[:, 1] - oy) ** 2)
    areas = np.atleast_1d(vo.overlap_area_um2(delta, R_p, R_h))
    hole_area = np.pi * R_h ** 2
    fractions = areas / hole_area
    return fractions, areas


def active_hole_indices(coords_um, D_pupil_um, a_hole_um, pupil_center_um=(0.0, 0.0),
                        active_frac_threshold=DEFAULT_ACTIVE_FRAC_THRESHOLD):
    """Indices of holes whose illumination fraction f_i >= active_frac_threshold --
    replaces the old binary center-in-pupil test. See DEFAULT_ACTIVE_FRAC_THRESHOLD's
    own comment for the modeling choice behind the default."""
    fractions, _ = hole_illumination_fractions(coords_um, D_pupil_um, a_hole_um, pupil_center_um)
    if len(fractions) == 0:
        return np.array([], dtype=int)
    return np.where(fractions >= active_frac_threshold)[0]


def active_pairs(coords_um, D_pupil_um, a_hole_um, pupil_center_um=(0.0, 0.0),
                 active_frac_threshold=DEFAULT_ACTIVE_FRAC_THRESHOLD):
    """Returns (pairs, active_idx) -- same shape as before this fix, now built on the
    thresholded partial-overlap active-hole test instead of the binary center test.
    pairs: list of (i, j) index tuples, both indices into coords_um, for every pair
    of holes simultaneously active at this pupil position."""
    active_idx = active_hole_indices(coords_um, D_pupil_um, a_hole_um, pupil_center_um,
                                     active_frac_threshold)
    pairs = list(itertools.combinations(active_idx.tolist(), 2))
    return pairs, active_idx


def total_illuminated_area_um2(coords_um, D_pupil_um, a_hole_um, pupil_center_um=(0.0, 0.0)):
    """Gate 3 (viability)'s continuous quantity: sum of EVERY hole's actual overlap
    area with the pupil, NOT thresholded -- a hole 40% illuminated still contributes
    light even though it doesn't clear the pairing threshold above. This answers "is
    any light reaching the wearer at all," independent of the pairwise-ghosting
    question. NOT a brightness/transmission objective (this project's scope
    explicitly excludes that) -- a minimum-viability floor only: zero means the
    wearer sees nothing, a positive value (of any size) means they see something."""
    _, areas = hole_illumination_fractions(coords_um, D_pupil_um, a_hole_um, pupil_center_um)
    return float(np.sum(areas)) if len(areas) else 0.0


def n_eff(coords_um, D_pupil_um, a_hole_um, pupil_center_um=(0.0, 0.0),
         active_frac_threshold=DEFAULT_ACTIVE_FRAC_THRESHOLD):
    """Convenience: how many holes are active (thresholded) at this pupil position --
    directly comparable to array_optimization's own N_eff, for sanity cross-checks."""
    return len(active_hole_indices(coords_um, D_pupil_um, a_hole_um, pupil_center_um,
                                   active_frac_threshold))


def verify_single_hole_sanity(D_pupil_um=4000.0, a_hole_um=400.0):
    """PART 1 STEP 4's REQUIRED sanity gate: a single hole centered EXACTLY at the
    pupil's own center must be FULLY illuminated (delta=0, deep inside the
    full-containment regime of overlap_area_um2) -- f=1.0 exactly, n_active=1, and
    total_illuminated_area_um2 == pi*R_h^2 exactly. If this fails, the overlap
    wiring itself is wrong and nothing downstream (ghost margins, gates) can be
    trusted. Not run automatically at import time (this project's convention is
    standalone, explicitly-invoked spot-check scripts, e.g.
    spot_check_generators.py, not import-time side effects) -- call this directly
    before trusting any change to this module."""
    coords = np.array([[0.0, 0.0]])
    R_h = a_hole_um / 2.0
    expected_area = np.pi * R_h ** 2

    fractions, areas = hole_illumination_fractions(coords, D_pupil_um, a_hole_um)
    assert np.isclose(fractions[0], 1.0), f"expected f=1.0, got {fractions[0]}"
    assert np.isclose(areas[0], expected_area), f"expected area={expected_area}, got {areas[0]}"

    active_idx = active_hole_indices(coords, D_pupil_um, a_hole_um)
    assert len(active_idx) == 1, f"expected n_active=1, got {len(active_idx)}"

    total = total_illuminated_area_um2(coords, D_pupil_um, a_hole_um)
    assert np.isclose(total, expected_area), f"expected total_illuminated_area={expected_area}, got {total}"

    return {"f": float(fractions[0]), "area_um2": float(areas[0]), "n_active": len(active_idx),
           "total_illuminated_area_um2": total, "expected_area_um2": expected_area}


if __name__ == "__main__":
    result = verify_single_hole_sanity()
    print("single-hole-at-origin sanity check PASSED:")
    for k, v in result.items():
        print(f"  {k}: {v}")
