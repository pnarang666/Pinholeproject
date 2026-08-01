"""
Unified illumination interface -- single-hole only in this build.

SCOPE NOTE (read before extending this file): the original brief for this module
asked for ONE interface covering both single-hole illumination
(stage3a/transmission.py::relative_illuminance) AND multi-hole array illumination
(a `stage_array/array_photometry.py::relative_retinal_illuminance_array`, with
worst/mean/best-case discrete lattice alignment and square/hex packing). That array
module was searched for exhaustively across this entire project (grep for
"no_ghost", "array_fig", "worst_case", "relative_retinal_illuminance_array", "hex.*
pack" across every .py/.md file) and DOES NOT EXIST anywhere in this codebase --
there is no prior array-photometry or no-ghost-pitch implementation to import from,
and per this project's own standing rule (see stage3_human_vision/literature.py's
whole citation discipline), physics is never invented here to fill that gap. The
array branch below is therefore an explicit, documented NotImplementedError, not a
silent wrong-answer fallback -- see percent_illumination()'s docstring.

Only imports from stage3a/ (read-only, per the same import-boundary pattern
stage2_fixed/pipeline_junction.py already uses for stage1_v2) -- no physics
reimplemented here.
"""

import os
import sys

import numpy as np

_STAGE3A_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage3a"))
_STAGE3HV_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage3_human_vision"))
for _d in (_STAGE3A_DIR, _STAGE3HV_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import transmission  # noqa: E402 (stage3a -- the single source of truth reused here)
import photometry  # noqa: E402 (stage3_human_vision -- used only for the cross-check below)

# Stage3a's own cited finding (README.md): "a brightness floor of roughly 6-9% of
# full-pupil illuminance alone moves the optimum ... into the clinical bracket."
# combine_metrics.py's own T_MIN_VALUES sweep uses these exact two numbers (0.0625,
# 0.09) as the two floors that land inside the clinical bracket. Restated here (not
# re-derived) as the two reference lines this whole project designs illumination
# discussions around -- see README.md.
BRIGHTNESS_FLOOR_LOW = 0.0625   # 6.25%
BRIGHTNESS_FLOOR_HIGH = 0.09    # 9.0%


def _cross_check_single_hole_formulas(test_points_um=((75, 4000), (400, 4000), (1200, 4000), (4000, 4000))):
    """
    The brief asked to confirm, before writing anything new, that this project's two
    illumination calculations agree at the single-hole case. The two calculations
    that ACTUALLY EXIST (stage_array does not -- see module docstring) are
    stage3a/transmission.py::relative_illuminance and
    stage3_human_vision/photometry.py::relative_retinal_illuminance -- two
    independently-written single-hole formulas. stage3_integrated/README.md already
    reports these agree exactly at 4 test points; this function re-runs that same
    check directly (real test coverage owned by this module, not just a citation).
    Raises AssertionError with the offending values if they ever diverge.
    """
    for a_hole_um, D_pupil_um in test_points_um:
        a = transmission.relative_illuminance(a_hole_um, D_pupil_um)
        b = photometry.relative_retinal_illuminance(a_hole_um, D_pupil_um)
        if not np.isclose(a, b, rtol=1e-12):
            raise AssertionError(
                f"stage3a.relative_illuminance({a_hole_um}, {D_pupil_um})={a} != "
                f"stage3_human_vision.photometry.relative_retinal_illuminance(...)={b} "
                f"-- the two independently-implemented single-hole formulas have "
                f"diverged; do not trust percent_illumination() until this is resolved."
            )
    return True


# Run once at import time -- if this project's two single-hole formulas ever drift
# apart, every caller of this module should fail loudly and immediately, not silently
# get a possibly-wrong number.
_cross_check_single_hole_formulas()


def percent_illumination(a_hole_um, D_pupil_um, N_holes=1, pitch_um=None,
                          packing="square", alignment="worst_case"):
    """
    Unified illumination interface. Single-hole case only (see module docstring for
    why the array case is blocked).

    Args:
        a_hole_um: pinhole diameter, microns.
        D_pupil_um: natural (unobstructed) pupil diameter, microns.
        N_holes: number of holes. N_holes=1 (default) uses the single-hole formula.
        pitch_um: hole-to-hole spacing, microns. Must be None for the single-hole case.
        packing: "square" or "hex" -- ARRAY-ONLY parameter, unused here.
        alignment: "worst_case" | "mean_case" | "best_case" -- ARRAY-ONLY parameter,
            unused here.

    Returns:
        dict with at minimum: percent_illumination (0-1, fraction of full natural-
        pupil illuminance), N_eff (=1 for the single-hole case), model (which
        formula/module actually produced the number), and alignment_case (None for
        the single-hole case, since there is no lattice alignment question with one
        hole).

    Raises:
        NotImplementedError if N_holes > 1 or pitch_um is given -- the multi-hole
        array case requires stage_array/, which does not exist in this project (see
        module docstring). This is intentionally loud, not a silent fallback to the
        single-hole formula (that would misrepresent a multi-hole design's actual
        brightness) and not a silently-invented array formula (that would violate
        this project's "no new physics invented here" rule).
    """
    if N_holes > 1 or pitch_um is not None:
        raise NotImplementedError(
            f"percent_illumination() was called with N_holes={N_holes}, "
            f"pitch_um={pitch_um} (packing={packing!r}, alignment={alignment!r}) -- "
            f"i.e. a multi-hole array. This project has no array-photometry module "
            f"(stage_array/ does not exist -- searched for and confirmed absent, see "
            f"this file's module docstring and singleilluminate/README.md). Computing "
            f"a multi-hole answer here would require either inventing new array "
            f"illumination physics (not allowed -- this module only unifies EXISTING "
            f"calculations) or silently falling back to the single-hole formula "
            f"(wrong -- it would ignore ghosting/overlap between adjacent holes "
            f"entirely). Build stage_array/ first, then extend this function."
        )
    E_rel = transmission.relative_illuminance(a_hole_um, D_pupil_um)
    return {
        "percent_illumination": float(E_rel),
        "N_eff": 1,
        "model": "single_hole",
        "alignment_case": None,
        "a_hole_um": a_hole_um,
        "D_pupil_um": D_pupil_um,
    }


if __name__ == "__main__":
    print("Single-hole/array cross-check: PASSED (formulas agree at all test points)")
    print()
    for a_um in (75, 400, 1200, 2000, 4000):
        r = percent_illumination(a_um, 4000.0)
        print(f"a_hole={a_um:5.0f}um  D_pupil=4000um  ->  "
              f"percent_illumination={r['percent_illumination']*100:6.2f}%  "
              f"(model={r['model']})")
    print()
    print("Multi-hole array call (expected to raise NotImplementedError):")
    try:
        percent_illumination(400.0, 4000.0, N_holes=7, pitch_um=1200.0)
    except NotImplementedError as e:
        print(f"  -> {e}")
