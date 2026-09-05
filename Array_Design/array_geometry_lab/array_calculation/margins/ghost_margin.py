"""
Ghost margin: for each active hole pair, compute the retinal ghost separation via the
copied, validated formula, and compare it against a "resolvable" reference size --
positive margin means the ghost separation is smaller than what the eye can resolve as
separate (imperceptible), negative means the design shows real ghosting risk.

WHAT "Delta_r_resolvable" IS, AND WHY, GIVEN THIS FOLDER'S "NO BLUR RECOMPUTATION" RULE:
This pipeline is explicitly forbidden from recomputing blur (a_hole(M) is a FIXED input,
not a search variable, and blur is "already fixed by the choice of a_hole(M)" per this
folder's own task brief). But a margin still needs SOME resolvable-size reference to
compare Delta_r_actual against. Rather than derive one (which would be a recomputation),
this module LOOKS UP the already-computed single-hole r_EE(50%) blur radius, at exactly
the acuity-optimal aperture a_hole(M), from new_sweeps/blur_sweep.csv -- a pre-existing
sweep artifact, read live, never recomputed or hardcoded. This is the same physical
quantity (r_EE(50%), the blur spot's own half-energy radius) this project's ENTIRE prior
no-ghost criterion has always compared Delta_r against (THEORY.md's original
`s < r_EE(P)*d_gap/v_r`, and Array_Design's corrected descendant of it) -- so this
module's margin definition is a direct continuation of that same established comparison,
not a new invented threshold.

An earlier candidate design for Delta_r_resolvable (converting per_M_optimum_map.csv's
own logmar_at_acuity_opt into a diffraction-limited MAR-based retinal size) was tried and
rejected: it gives a resolvable size of order 1um (correct for absolute foveal acuity),
which is smaller than essentially any physically buildable array pitch's ghost
separation, making every design fail trivially -- a degenerate, uninformative margin.
The r_EE_50 blur-radius lookup used here (order 7-18um across M=0-8D) is the metric this
project has always actually used for ghost-vs-blur comparison, and produces a
non-degenerate result. Documented here rather than silently choosing one.
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
import ghost_formula as gf  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "generators"))
sys.path.insert(0, HERE)
import active_pairs as ap  # noqa: E402

PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PER_M_OPTIMUM_MAP_CSV = os.path.join(PROJECT_ROOT, "new_sweeps", "per_M_optimum_map.csv")
BLUR_SWEEP_CSV = os.path.join(PROJECT_ROOT, "new_sweeps", "blur_sweep.csv")

ALL_M_VALUES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]  # matches per_M_optimum_map.csv's
                                                          # own M grid exactly (read live
                                                          # below; this list is only the
                                                          # default --scope=global sweep
                                                          # range, CLI-overridable)


def load_acuity_optimal_aperture(M_diopters):
    """a_hole(M): read live from new_sweeps/per_M_optimum_map.csv, never hardcoded or
    recomputed. Raises if M isn't in the file rather than silently interpolating."""
    df = pd.read_csv(PER_M_OPTIMUM_MAP_CSV)
    match = df[df.M_diopters == M_diopters]
    assert len(match) == 1, (
        f"M={M_diopters} not found (or found >1 time) in {PER_M_OPTIMUM_MAP_CSV} -- "
        f"available M values: {sorted(df.M_diopters.unique())}")
    return float(match.iloc[0].acuity_optimal_um)


def load_resolvable_blur_um(M_diopters, a_hole_um):
    """Delta_r_resolvable: r_EE(50%) looked up (not recomputed) from
    new_sweeps/blur_sweep.csv at exactly (M_diopters, a_hole_um). Raises if that exact
    (M, a_hole) combination isn't in the sweep -- this pipeline only ever asks for it at
    the acuity-optimal aperture, which the sweep grid was confirmed (by direct lookup,
    2026-08-15) to include for every M in per_M_optimum_map.csv."""
    df = pd.read_csv(BLUR_SWEEP_CSV)
    match = df[(df.M_diopters == M_diopters) & (df.a_hole_um == a_hole_um)]
    assert len(match) == 1, (
        f"(M={M_diopters}, a_hole_um={a_hole_um}) not found in {BLUR_SWEEP_CSV} -- "
        f"this pipeline only looks up r_EE_50 at the acuity-optimal aperture; if "
        f"per_M_optimum_map.csv's acuity_optimal_um values have changed, blur_sweep.csv "
        f"may need its own aperture grid extended to match (not something this pipeline "
        f"does automatically, since that would be a recomputation).")
    row = match.iloc[0]
    assert bool(row.junction_ok), f"blur_sweep.csv row at (M={M_diopters}, a={a_hole_um}) has junction_ok=False"
    return float(row.r_EE_50_um)


def margin_for_pair(i, j, coords_um, M_diopters, resolvable_blur_um, P0=60.0):
    """Delta_r_actual generalizes 'pitch' in the copied formula to the actual Euclidean
    center-to-center distance between holes i and j -- valid because the underlying
    derivation (ghost_formula.py's source docstring) only ever used 's' as the
    transverse height difference between two hole positions, never assumed a periodic
    lattice; a pairwise Euclidean distance IS that same quantity for two arbitrary
    points."""
    pair_distance_um = float(np.linalg.norm(coords_um[i] - coords_um[j]))
    delta_r_actual = gf.delta_r_corrected_from_M_um(pair_distance_um, M_diopters, P0=P0)
    margin = (resolvable_blur_um - delta_r_actual) / resolvable_blur_um
    return margin, delta_r_actual, pair_distance_um


def worst_case_ghost_margin(coords_um, D_pupil_um, M_diopters, a_hole_um,
                            resolvable_blur_um=None, P0=60.0, pupil_center_um=(0.0, 0.0),
                            active_frac_threshold=ap.DEFAULT_ACTIVE_FRAC_THRESHOLD):
    """Worst-case (minimum) margin across every active pair at this pupil position.
    If resolvable_blur_um is not given, looked up live at (M_diopters, a_hole_um).
    Returns a dict, not a bare number, so 'no active pairs' (structurally ghost-free,
    nothing CAN ghost) is reported explicitly rather than conflated with 'margin=+inf
    because ghosting happens to be small' -- both give margin=+inf, but n_active_pairs
    distinguishes why.

    a_hole_um is now threaded into active_pairs() (audit fix, Defect C/2): pair
    membership is TRUE partial-overlap area, not a binary center-in-pupil test, so
    the hole radius is required. total_illuminated_area_um2 is ALSO returned here
    (continuous, never thresholded) -- the quantity Gate 3 (viability) needs, kept
    separate from the thresholded n_active_pairs/n_active_holes used for pairwise
    ghost enumeration -- see active_pairs.py's own module docstring for why these
    must not be collapsed into one number."""
    if resolvable_blur_um is None:
        resolvable_blur_um = load_resolvable_blur_um(M_diopters, a_hole_um)

    pairs, active_idx = ap.active_pairs(coords_um, D_pupil_um, a_hole_um, pupil_center_um,
                                        active_frac_threshold=active_frac_threshold)
    total_illuminated_area_um2 = ap.total_illuminated_area_um2(coords_um, D_pupil_um, a_hole_um,
                                                                pupil_center_um)
    if not pairs:
        return {"worst_case_margin": float("inf"), "n_active_pairs": 0,
                "n_active_holes": int(len(active_idx)), "resolvable_blur_um": resolvable_blur_um,
                "worst_pair_distance_um": None, "worst_delta_r_actual_um": None,
                "total_illuminated_area_um2": total_illuminated_area_um2}

    results = [margin_for_pair(i, j, coords_um, M_diopters, resolvable_blur_um, P0)
              for i, j in pairs]
    margins = [r[0] for r in results]
    worst_k = int(np.argmin(margins))
    worst_margin, worst_delta_r, worst_dist = results[worst_k]

    return {"worst_case_margin": worst_margin, "n_active_pairs": len(pairs),
            "n_active_holes": int(len(active_idx)), "resolvable_blur_um": resolvable_blur_um,
            "worst_pair_distance_um": worst_dist, "worst_delta_r_actual_um": worst_delta_r,
            "total_illuminated_area_um2": total_illuminated_area_um2}


def evaluate_per_M(coords_um, D_pupil_um, M_diopters, P0=60.0):
    """--scope=per_M: this design (generated at a_hole(M)) evaluated against only that
    same M."""
    a_hole_um = load_acuity_optimal_aperture(M_diopters)
    result = worst_case_ghost_margin(coords_um, D_pupil_um, M_diopters, a_hole_um, P0=P0)
    result["scope"] = "per_M"
    result["M_diopters"] = M_diopters
    result["a_hole_um"] = a_hole_um
    return result


def evaluate_global(coords_um, D_pupil_um, M_values=None, P0=60.0):
    """--scope=global: a SINGLE fixed hole-coordinate layout, evaluated at EVERY M in
    M_values, using each M's own a_hole(M) for the resolvable-blur lookup. The
    coordinates themselves do NOT change per M (this is one candidate design, not a
    family of them) -- callers are responsible for having generated those coordinates
    at an a_hole_um that is valid (non-overlapping) across the WHOLE M range tested,
    e.g. by generating at the LARGEST a_hole(M) in that range (sweep/run_sweep.py does
    this explicitly). Returns the worst-case-across-M result, PLUS the full per-M
    breakdown, PLUS an explicit ambiguity flag -- a 'global' design's own hole
    coordinates were generated at one specific a_hole_um for overlap-validity purposes,
    but which single a_hole_um a real pair of glasses would actually be manufactured at
    is NOT decided here (a real wearer has one M, not a distribution) -- see this
    folder's README.md for how to interpret that."""
    if M_values is None:
        M_values = ALL_M_VALUES
    per_M_results = []
    for M in M_values:
        a_hole_um = load_acuity_optimal_aperture(M)
        r = worst_case_ghost_margin(coords_um, D_pupil_um, M, a_hole_um, P0=P0)
        r["M_diopters"] = M
        r["a_hole_um"] = a_hole_um
        per_M_results.append(r)

    worst_row = min(per_M_results, key=lambda r: r["worst_case_margin"])
    return {
        "scope": "global",
        "worst_case_margin": worst_row["worst_case_margin"],
        "worst_case_M": worst_row["M_diopters"],
        "a_hole_um_AMBIGUOUS": (
            "global scope evaluated across multiple a_hole(M) values "
            f"({sorted(set(r['a_hole_um'] for r in per_M_results))}) -- no single "
            "a_hole_um is 'the' answer for this design; a physical build must still "
            "pick one, see README.md"),
        "per_M_breakdown": per_M_results,
    }
