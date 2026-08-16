"""
PART 2 of the Phase 2 (full-physics) confirmation pass.

For each of the 9 finalists (coordinates from build_full_masks.py's
finalist_coords.csv / finalist_metadata.csv), propagates the ACTUAL multi-aperture
mask through array_optimization's validated wave-optics engine, at its own
already-fixed a_hole_um and resolved M, at each of a set of gaze angles phi, and
DIRECTLY MEASURES (peak detection on the resulting retinal intensity field -- never
falls back to the closed-form formula) blur (r_EE at 50/70/80/90%) and, where more
than one distinct retinal peak is present, the actual ghost separation between them.

IMPORTED, NOT COPIED (explicit rule for this task, opposite of
array_geometry_lab/'s own copy-not-import convention): Array_Design/
array_psf_envelope.py's single_hole_psf() -- the actual, cached, validated
wave-optics propagation (stage2_fixed.phase2_retina.run_pipeline_point under the
hood) -- and pipeline_junction's encircled-energy machinery, imported via
array_psf_envelope's own re-exports. Also imports
array_optimization/vignetting.py's pupil_shift_um() for the gaze-angle pupil
displacement, the SAME Delta(phi)=R_rot*sin(phi) model
array_geometry_lab/evaluation/vignetting_robustness.py already uses (that module
COPIES vignetting.py per array_geometry_lab's own convention; this script imports
the original directly per THIS task's explicit rule) -- confirmed consistent: same
formula, same default R_rot_mm=13.5, same convention of shifting the pupil center
by (shift_um, 0) relative to the pattern's own centroid.

WHY array_psf_envelope.array_psf() ITSELF IS NOT CALLED (see build_full_masks.py's
own docstring for the full finding): that function only builds coordinates
internally via an infinite regular square/hex lattice -- it has no parameter for an
external, finite, irregular coordinate list. This module therefore replicates
array_psf()'s own documented ALGORITHM (crop sizing, roll-and-sum of the cached
single-hole PSF, r_max_lens aliasing exclusion, centroid-recentring before
measuring r_EE) around an externally supplied (hx_um, hy_um) array plus a gaze
pupil-offset -- the geometry/bookkeeping layer, not the physics, which stays
entirely in the imported, unmodified single_hole_psf()/junction calls.

GAZE ANGLE LIST: the task text names phi = 0, +-10, +-20, +-25 degrees explicitly
(7 values) but also states "9 finalists x 5 gaze angles = 45 full propagations"
(9x5=45, i.e. 5 angles). These two statements in the task are inconsistent with
each other -- flagged here, not silently reconciled.

Resolved by going BEYOND the named 7 values: this script uses
array_geometry_lab/evaluation/vignetting_robustness.py's own phi_grid() exactly --
(-25,-20,-15,-10,-5,0,5,10,15,20,25), 11 values, a strict superset of the named 7 --
because inspecting Phase 1's own per-finalist results (before writing this script)
found that the ONLY finalist with a non-infinite worst_case_vignetting_margin
(rectangular, M=0.0D, margin=1.0) has its single active pair appearing at
phi=+-5deg specifically -- a phi NOT in the named 7-value list. Using only the
named angles would make Part 3's central comparison (Phase 1 predicted vignetting
behavior vs Phase 2 measured behavior) untestable for the one finalist where it
actually matters. Using Phase 1's own exact phi grid instead means every phi Phase
1 itself evaluated is also measured here -- an exact, not approximate,
apples-to-apples comparison. This raises the per-finalist gaze-angle count from 7
to 11 (99 total vs the task's stated 45), but costs almost nothing extra: each
additional gaze angle reuses the SAME cached single_hole_psf() field (see runtime
estimate below) via a cheap roll-and-sum, not an independent full propagation.

RUNTIME ESTIMATE (measured empirically on one point before running the full set,
per this task's explicit requirement): a single cold single_hole_psf() call
(a_hole_um=2000, M=0D) took 19.75s on this machine; a cached repeat call took
0.0000s. There are only 9 DISTINCT (a_hole_um, M) pairs across all 9 finalists (one
each) needing a cold call -- total expensive cost ~9 x 20s = ~180s (~3 minutes),
comfortably under the "few minutes per single propagation" flag threshold this
task set, so this script proceeds automatically rather than stopping to ask. The
99 gaze-angle roll-and-sum evaluations that follow (9 finalists x 11 phi values)
are each well under a second.

Peak detection (generalizing validate_ghost_formula.py's two_peak_positions_um,
which is hardcoded to exactly 2 holes on the x-axis, to this project's actual
N-hole 2D patterns): local maxima found via scipy.ndimage.maximum_filter with a
neighborhood sized to ~2x the single-hole PSF's own r_EE_80 diameter (so
sub-structure WITHIN one true blur spot is not double-counted as separate peaks,
while genuinely resolved ghosts -- separated by MORE than the blur radius, by this
project's own margin definition -- are kept distinct), thresholded at 2% of the
field's own peak intensity to exclude numerical noise. This is peak detection, not
formula lookup, matching this task's explicit requirement.

Run:  python3 run_full_physics.py
"""
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.ndimage import maximum_filter

HERE = os.path.dirname(os.path.abspath(__file__))
ARRAY_DESIGN = os.path.dirname(HERE)

sys.path.insert(0, ARRAY_DESIGN)
import array_psf_envelope as ape  # noqa: E402 -- imports pipeline_junction as
                                  # `junction` and phase2_retina as `p2` internally;
                                  # reused here via ape.junction / the module itself
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "array_optimization"))
import vignetting as vig  # noqa: E402 -- array_optimization's OWN module, imported
                          # directly per this task's explicit rule

IN_COORDS_CSV = os.path.join(HERE, "finalist_coords.csv")
IN_METADATA_CSV = os.path.join(HERE, "finalist_metadata.csv")
OUT_MEASUREMENTS_CSV = os.path.join(HERE, "phase2_measurements.csv")

D_PUPIL_UM = ape.D_PUPIL_UM  # 4000.0, same constant this whole project uses
R_ROT_MM = vig.DEFAULT_R_ROT_MM  # 13.5mm, same as array_geometry_lab's vignetting_robustness.py
GAZE_ANGLES_DEG = [-25.0, -20.0, -15.0, -10.0, -5.0, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0]
                    # Phase 1's OWN phi_grid() exactly (a superset of the task's named
                    # 0/+-10/+-20/+-25) -- see module docstring for why.
EE_PERCENTILES = [0.50, 0.70, 0.80, 0.90]
PEAK_NOISE_FLOOR_FRACTION = 0.02  # 2% of the field's own peak intensity


def _make_grid_XY(N, dx):
    X, Y, R, _ = ape.junction.make_grid(N, N * dx)
    return X, Y, R


def custom_array_psf(hx_um, hy_um, a_hole_um, M, pupil_offset_um=(0.0, 0.0),
                      D_pupil_um=D_PUPIL_UM, exclude_aliased=True):
    """array_psf_envelope.array_psf()'s own algorithm (crop sizing, roll-and-sum
    of the CACHED single-hole PSF, r_max_lens aliasing exclusion), adapted to an
    externally supplied (hx_um, hy_um) coordinate array and an explicit gaze pupil
    offset instead of an internally-generated infinite lattice. Every physics call
    (single_hole_psf) is the imported, unmodified original.

    Returns a dict: I_sum (raw, NOT centroid-recentred -- callers recenter for
    r_EE measurement specifically, see measure_blur_and_ghosts below), dx,
    n_in_pupil, n_included, n_excluded_aliased, hx_active_um, hy_active_um."""
    psf = ape.single_hole_psf(a_hole_um, M, D_pupil_um=D_pupil_um)
    I_single, dx = psf["I_single"], psf["dx"]
    demag = (psf["v_r_um"] - psf["v_f_um"]) / psf["v_f_um"]

    ox, oy = pupil_offset_um
    hx = np.asarray(hx_um, dtype=float) - ox
    hy = np.asarray(hy_um, dtype=float) - oy
    r_hole = np.sqrt(hx ** 2 + hy ** 2)
    inside = r_hole <= (D_pupil_um / 2.0)
    hx, hy, r_hole = hx[inside], hy[inside], r_hole[inside]
    n_in_pupil = int(len(hx))

    safe = ((r_hole + a_hole_um / 2.0) <= psf["r_max_lens_um"]) if exclude_aliased \
        else np.ones_like(r_hole, dtype=bool)
    n_excluded = int((~safe).sum())
    hx, hy, r_hole = hx[safe], hy[safe], r_hole[safe]
    n_included = int(len(hx))

    if n_included == 0:
        return {"I_sum": None, "dx": dx, "n_in_pupil": n_in_pupil, "n_included": 0,
               "n_excluded_aliased": n_excluded, "hx_active_um": hx, "hy_active_um": hy,
               "demag": demag, "psf": psf}

    # NOT CROPPED, unlike array_psf()'s own auto-sized crop (r_EE_98-based margin) --
    # a REAL bug was found here while validating this script's own output before
    # trusting it (not assumed correct because it mirrors array_psf()'s algorithm):
    # at (a_hole_um=2000, M=0D), the r_EE_98-based crop margin (46.4um) badly
    # underestimates where the encircled-energy curve actually stabilizes -- direct
    # sweep of crop half-widths found r_EE_50 JUMPS discontinuously from 2.28um
    # (cropped) to 3.66um (uncropped, matching single_hole_psf()'s own reported
    # single_r_EE_50_um exactly) between half-widths of 375um and 750um, i.e. this
    # PSF has real energy structure far past its own r_EE_98 radius that the 98%
    # heuristic does not anticipate. array_psf_envelope.py's own
    # crop_vs_full_grid_check() never exercised this specific (a_hole, M) pair (it
    # tests (400,900,4D), (700,2000,8D), (300,1200,1D) only) -- this is a genuinely
    # untested regime for that heuristic, not a contradiction of it. Since this
    # script only processes 9 finalists (not a large sweep -- the crop's whole
    # purpose in array_psf_envelope.py), the safe fix is to skip cropping entirely
    # and sum on the FULL single-hole field every time: measured at ~2.7s for the
    # worst-case finalist (50 holes, full 4096x4096 field) -- trivial next to the
    # ~20s/finalist propagation cost already paid, and it cannot exhibit this class
    # of truncation error by construction.
    I_sum = np.zeros_like(I_single)
    hole_shift_px = []
    for x_um, y_um in zip(hx, hy):
        sx = int(round((-demag * x_um * 1e-6) / dx))
        sy = int(round((-demag * y_um * 1e-6) / dx))
        hole_shift_px.append((sx, sy))
        I_sum += np.roll(np.roll(I_single, sy, axis=0), sx, axis=1)

    return {"I_sum": I_sum, "dx": dx, "n_in_pupil": n_in_pupil, "n_included": n_included,
           "n_excluded_aliased": n_excluded, "hx_active_um": hx, "hy_active_um": hy,
           "demag": demag, "psf": psf, "hole_shift_px": hole_shift_px}


def _r_ee_centered(I, dx, P):
    """Same recentre-on-summed-pattern's-own-centroid convention as
    array_psf_envelope.array_psf() uses before measuring r_EE (see that function's
    own extensive comment on why: a single off-axis hole must not be reported as
    'blurry' just because it is displaced)."""
    N = I.shape[0]
    X, Y, _ = _make_grid_XY(N, dx)
    total = I.sum()
    if total <= 0:
        return float("nan")
    cx = float((I * X).sum() / total)
    cy = float((I * Y).sum() / total)
    I_c = np.roll(np.roll(I, -int(round(cy / dx)), axis=0), -int(round(cx / dx)), axis=1)
    _, _, R, _ = ape.junction.make_grid(N, N * dx)
    r_edges, EE, _ = ape.junction.encircled_energy(I_c, R, dx)
    return ape.junction.r_for_EE(r_edges, EE, P) * 1e6


def detect_peaks(I, dx, single_r_EE_80_um):
    """Generalizes validate_ghost_formula.py's two_peak_positions_um (hardcoded to
    2 holes on the x-axis) to arbitrary N-hole 2D patterns -- see module docstring
    for the method and its justification. Returns a DataFrame of
    (x_um, y_um, intensity) for each resolved peak, sorted by intensity descending."""
    if I is None or I.sum() <= 0:
        return pd.DataFrame(columns=["x_um", "y_um", "intensity"])
    N = I.shape[0]
    X, Y, _ = _make_grid_XY(N, dx)
    neighborhood_px = max(3, int(round(2.0 * single_r_EE_80_um * 1e-6 / dx)))
    local_max = maximum_filter(I, size=neighborhood_px) == I
    floor = PEAK_NOISE_FLOOR_FRACTION * I.max()
    peak_mask = local_max & (I > floor)
    ys, xs = np.where(peak_mask)
    rows = [{"x_um": float(X[y, x]) * 1e6, "y_um": float(Y[y, x]) * 1e6,
            "intensity": float(I[y, x])} for y, x in zip(ys, xs)]
    return pd.DataFrame(rows).sort_values("intensity", ascending=False).reset_index(drop=True)


def max_pairwise_separation_um(peaks_df):
    if len(peaks_df) < 2:
        return float("nan")
    pts = peaks_df[["x_um", "y_um"]].values
    max_sep = 0.0
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = float(np.linalg.norm(pts[i] - pts[j]))
            max_sep = max(max_sep, d)
    return max_sep


def measure_one(finalist_id, family, a_hole_um, M, hx_um, hy_um, phi_deg):
    shift_um = float(vig.pupil_shift_um(phi_deg, R_ROT_MM))
    result = custom_array_psf(hx_um, hy_um, a_hole_um, M, pupil_offset_um=(shift_um, 0.0))

    row = {"finalist_id": finalist_id, "family": family, "a_hole_um": a_hole_um, "M": M,
          "phi_deg": phi_deg, "pupil_shift_um": shift_um,
          "n_in_pupil": result["n_in_pupil"], "n_included": result["n_included"],
          "n_excluded_aliased": result["n_excluded_aliased"]}

    if result["I_sum"] is None:
        row.update({f"r_EE_{int(p*100)}_um": float("nan") for p in EE_PERCENTILES})
        row.update({"n_resolved_peaks": 0, "max_ghost_separation_measured_um": float("nan"),
                   "field_dark": True})
        return row

    I_sum, dx = result["I_sum"], result["dx"]
    for p in EE_PERCENTILES:
        row[f"r_EE_{int(p*100)}_um"] = _r_ee_centered(I_sum, dx, p)

    single_r_EE_80 = result["psf"]["single_r_EE_80_um"]
    peaks = detect_peaks(I_sum, dx, single_r_EE_80)
    row["n_resolved_peaks"] = len(peaks)
    row["max_ghost_separation_measured_um"] = max_pairwise_separation_um(peaks)
    row["field_dark"] = False
    return row


def main():
    coords_df = pd.read_csv(IN_COORDS_CSV)
    meta_df = pd.read_csv(IN_METADATA_CSV)
    print(f"loaded {len(meta_df)} finalists, {len(coords_df)} hole-coordinate rows")

    n_distinct_am = meta_df[["a_hole_um", "M_resolved_for_optics"]].drop_duplicates()
    print(f"\n--- runtime estimate ---")
    print(f"{len(n_distinct_am)} distinct (a_hole_um, M) pairs need a cold "
          f"single_hole_psf() call (~20s each measured) -> ~{len(n_distinct_am)*20}s "
          f"(~{len(n_distinct_am)*20/60.0:.1f} min) of expensive propagation total.")
    print(f"{len(meta_df)} finalists x {len(GAZE_ANGLES_DEG)} gaze angles = "
          f"{len(meta_df)*len(GAZE_ANGLES_DEG)} roll-and-sum evaluations, each reusing "
          f"a cached field (<3s each, uncropped -- see custom_array_psf()'s own "
          f"comment on why cropping was removed) -- not independent full propagations.")
    print("Proceeding (well under the 'few minutes per single propagation' flag "
          "threshold).\n")

    t_start = time.time()
    all_rows = []
    for _, meta in meta_df.iterrows():
        finalist_id = meta.finalist_id
        family = meta.family
        a_hole_um = meta.a_hole_um
        M = meta.M_resolved_for_optics
        sub = coords_df[coords_df.finalist_id == finalist_id]
        hx_um, hy_um = sub.x_um.values, sub.y_um.values

        t0 = time.time()
        for phi in GAZE_ANGLES_DEG:
            row = measure_one(finalist_id, family, a_hole_um, M, hx_um, hy_um, phi)
            all_rows.append(row)
        dt = time.time() - t0
        print(f"[{finalist_id}] a_hole={a_hole_um:.0f}um M={M}D: {len(GAZE_ANGLES_DEG)} "
              f"gaze angles done in {dt:.1f}s")

    total_dt = time.time() - t_start
    print(f"\ntotal Part 2 runtime: {total_dt:.1f}s ({total_dt/60.0:.2f} min)")

    out_df = pd.DataFrame(all_rows)
    out_df.to_csv(OUT_MEASUREMENTS_CSV, index=False)
    print(f"wrote {OUT_MEASUREMENTS_CSV} ({len(out_df)} rows: "
          f"{len(meta_df)} finalists x {len(GAZE_ANGLES_DEG)} gaze angles)")


if __name__ == "__main__":
    main()
