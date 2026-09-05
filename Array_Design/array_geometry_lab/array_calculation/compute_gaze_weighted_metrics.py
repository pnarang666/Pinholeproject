"""
compute_gaze_weighted_metrics.py -- a NEW, PARALLEL evaluation, additive only.
Does not replace or modify the existing worst-case-across-phi gates/metrics
(margins/vignetting_robustness.py, comparison_metric/gates.py, etc.) -- those
stay exactly as they are, still reported, still the project's own primary
ranking. This file answers a different question: not "is there ANY tested
gaze angle where this design fails" (worst-case, unweighted -- treats
phi=25deg, where the eye spends ~0.6% of its time, as heavily as phi=0deg),
but "what FRACTION OF VIEWING TIME is this design blind or ghosting," using
an empirically measured eccentricity distribution (not a fitted Gaussian, not
assumed).

EMPIRICAL GAZE WEIGHTS, AS GIVEN (measured eccentricity distribution, % of
viewing time per 1-degree bin) -- see verify_weights() below, which asserts
these sum to 100.0 and reproduce the two stated cumulative checkpoints
(51.61% by 6deg, 95.27% by 17deg) BEFORE any sweep runs, not after.

AZIMUTHAL SAMPLING, WHY IT MATTERS: this project's existing worst-case gates
model gaze along a SINGLE AXIS (phi shifts the pupil along +x only -- see
margins/vignetting_robustness.py's own docstring). Eccentricity, physically,
has no preferred direction -- a wearer's gaze wanders in every azimuth at a
given eccentricity, and for a RING-based family in particular, a blackout can
occur in the gap BETWEEN two ring holes at one azimuth while an adjacent
azimuth at the SAME eccentricity sits right on top of a hole. Sampling only
the +x axis (this project's existing convention) can silently miss this.
Fixed here by sampling N_THETA>=36 azimuths uniformly around the full circle
at each eccentricity bin, using the SAME validated radial-shift MAGNITUDE
formula (engine/vignetting_overlap.pupil_shift_um -- imported, not
reimplemented) applied in an arbitrary direction: pupil_center = (R*cos(theta),
R*sin(theta)), R = pupil_shift_um(phi_deg, R_rot_mm). This is the geometry's
own existing validated radial-shift model, generalized to the azimuth this
project's own single-axis convention never needed before -- not a new physics
formula.

THE ">25deg" BIN (0.58% of viewing time, evaluated at phi=27deg per this
task's own instruction): 27deg is OUTSIDE
engine/vignetting_overlap.DEFAULT_PHI_VALID_DEG=25deg, the Handbook's own
stated small-angle validity range for the pupil-shift formula. The formula
does not blow up there (it is evaluated, per phi_in_validated_range()'s own
docstring, "the formula doesn't blow up... every caller that reports a
number must check and flag this, not silently trust it") -- flagged here in
this docstring and via the EXTRAPOLATED_BIN constant below, not silently
trusted. At only 0.58% of total weight, its influence on the final
time-weighted numbers is small regardless.

ACTIVE-HOLE THRESHOLD: n_active (for the ghost condition) uses the SAME
active_frac_threshold=0.5 this project's own margins/active_pairs.py already
uses everywhere else (DEFAULT_ACTIVE_FRAC_THRESHOLD) -- reused, not
redefined, so "ghosting" means the same thing here as it does in the existing
worst-case gates.

LAYER 1 (array_calculation/): physics/geometry only. Reads
array_data/theoretical_data/sweep_results_with_density.csv (read-only, not
modified), writes a NEW file to the same directory -- does not overwrite
anything.

Run:  python3 compute_gaze_weighted_metrics.py
      python3 compute_gaze_weighted_metrics.py --verify_weights_only
      python3 compute_gaze_weighted_metrics.py --limit 50   # testing
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_calculation/
sys.path.insert(0, HERE)
import degeneracy_filter  # noqa: E402 -- GEN_FUNCS + parse_spacing_params,
                          # same regeneration approach compute_density.py /
                          # compute_coverage_metrics.py already use.
sys.path.insert(0, os.path.join(HERE, "margins"))
sys.path.insert(0, os.path.join(HERE, "engine"))
import active_pairs as ap  # noqa: E402 -- DEFAULT_ACTIVE_FRAC_THRESHOLD, reused
import vignetting_overlap as vo  # noqa: E402 -- overlap_area_um2, pupil_shift_um,
                                  # DEFAULT_PHI_VALID_DEG, all reused unmodified

DATA_DIR = os.path.join(os.path.dirname(HERE), "array_data", "theoretical_data")
IN_CSV = os.path.join(DATA_DIR, "sweep_results_with_density.csv")
OUT_CSV = os.path.join(DATA_DIR, "gaze_weighted_metrics.csv")  # NEW file, does not
                                                                # overwrite anything

D_PUPIL_UM = 4000.0  # this project's own established pupil diameter constant
                     # (sweep/run_sweep.py's DEFAULT_D_PUPIL_UM)
N_THETA = 36  # azimuths per eccentricity bin -- this task's own stated minimum

# (bin_center_deg, weight_pct), AS GIVEN. The ">25" bin's center is 27deg, per
# this task's own explicit instruction -- see module docstring's "THE >25deg
# BIN" section for why that is outside the Handbook's own validated range.
GAZE_BINS = [
    (0.5, 9.29), (1.5, 9.16), (2.5, 8.92), (3.5, 8.56), (4.5, 8.11),
    (5.5, 7.57), (6.5, 6.98), (7.5, 6.35), (8.5, 5.69), (9.5, 5.04),
    (10.5, 4.40), (11.5, 3.79), (12.5, 3.22), (13.5, 2.70), (14.5, 2.23),
    (15.5, 1.81), (16.5, 1.45), (17.5, 1.14), (18.5, 0.88), (19.5, 0.67),
    (20.5, 0.50), (21.5, 0.37), (22.5, 0.27), (23.5, 0.19), (24.5, 0.13),
    (27.0, 0.58),
]
EXTRAPOLATED_BIN_DEG = 27.0  # outside vo.DEFAULT_PHI_VALID_DEG=25 -- flagged,
                             # not silently trusted (see module docstring)
WITHIN_17DEG_CUTOFF_DEG = 17.0  # bins with center < 17deg -- the 95.27%-of-time
                                # cone (checkpoint verified below)

BIN_CENTERS = np.array([c for c, _ in GAZE_BINS])
BIN_WEIGHTS = np.array([w for _, w in GAZE_BINS])
WITHIN_17_MASK = BIN_CENTERS < WITHIN_17DEG_CUTOFF_DEG


def verify_weights():
    """REQUIRED (this task's own instruction): assert the weights sum to
    100.0 and reproduce the two stated cumulative checkpoints, BEFORE any
    sweep runs."""
    total = BIN_WEIGHTS.sum()
    assert np.isclose(total, 100.0, atol=1e-9), f"weights sum to {total}, expected 100.0"

    cum_6deg = BIN_WEIGHTS[BIN_CENTERS < 6.0].sum()
    assert np.isclose(cum_6deg, 51.61, atol=1e-9), (
        f"cumulative weight by 6deg = {cum_6deg}, expected 51.61 (checkpoint FAILED)")

    cum_17deg = BIN_WEIGHTS[BIN_CENTERS < 17.0].sum()
    assert np.isclose(cum_17deg, 95.27, atol=1e-9), (
        f"cumulative weight by 17deg = {cum_17deg}, expected 95.27 (checkpoint FAILED)")

    print(f"weight verification PASSED: sum={total:.4f} (expect 100.0), "
          f"cumulative by 6deg={cum_6deg:.4f} (expect 51.61), "
          f"cumulative by 17deg={cum_17deg:.4f} (expect 95.27)")
    print(f"within-17deg cone total weight: {BIN_WEIGHTS[WITHIN_17_MASK].sum():.4f} "
          f"({WITHIN_17_MASK.sum()} of {len(GAZE_BINS)} bins)")


def precompute_positions_um(R_rot_mm=vo.DEFAULT_R_ROT_MM, n_theta=N_THETA):
    """(n_bins*n_theta, 2) pupil-center positions, and the (n_bins*n_theta,)
    bin index each belongs to -- computed ONCE (independent of any candidate's
    own geometry, since it only depends on phi/theta/R_rot_mm, all constants),
    reused for every row."""
    all_pos = []
    bin_idx = []
    thetas = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    for i, (phi_deg, _w) in enumerate(GAZE_BINS):
        R = vo.pupil_shift_um(phi_deg, R_rot_mm)
        pos = np.column_stack([R * np.cos(thetas), R * np.sin(thetas)])
        all_pos.append(pos)
        bin_idx.extend([i] * n_theta)
    return np.vstack(all_pos), np.array(bin_idx)


ALL_POSITIONS_UM, BIN_INDEX = precompute_positions_um()


def compute_row_gaze_metrics(coords_um, a_hole_um, D_pupil_um=D_PUPIL_UM,
                             active_frac_threshold=ap.DEFAULT_ACTIVE_FRAC_THRESHOLD):
    coords_um = np.asarray(coords_um, dtype=float)
    R_h = a_hole_um / 2.0
    R_p = D_pupil_um / 2.0
    hole_area = np.pi * R_h ** 2
    n_samples = len(ALL_POSITIONS_UM)

    if len(coords_um) == 0:
        total_area = np.zeros(n_samples)
        n_active = np.zeros(n_samples, dtype=int)
    else:
        dx = ALL_POSITIONS_UM[:, 0][:, None] - coords_um[:, 0][None, :]
        dy = ALL_POSITIONS_UM[:, 1][:, None] - coords_um[:, 1][None, :]
        delta = np.sqrt(dx ** 2 + dy ** 2)
        areas = vo.overlap_area_um2(delta, R_p, R_h)  # (n_samples, N_holes)
        total_area = areas.sum(axis=1)
        fractions = areas / hole_area
        n_active = (fractions >= active_frac_threshold).sum(axis=1)

    is_blind = (total_area == 0.0)
    is_ghost = (n_active >= 2)

    n_bins = len(GAZE_BINS)
    frac_blind_per_bin = np.zeros(n_bins)
    frac_ghost_per_bin = np.zeros(n_bins)
    mean_area_per_bin = np.zeros(n_bins)
    for i in range(n_bins):
        m = BIN_INDEX == i
        frac_blind_per_bin[i] = is_blind[m].mean()
        frac_ghost_per_bin[i] = is_ghost[m].mean()
        mean_area_per_bin[i] = total_area[m].mean()

    time_weighted_blind_pct = float(np.dot(BIN_WEIGHTS, frac_blind_per_bin))
    time_weighted_ghost_pct = float(np.dot(BIN_WEIGHTS, frac_ghost_per_bin))
    time_weighted_mean_lit_area_um2 = float(np.dot(BIN_WEIGHTS, mean_area_per_bin) / 100.0)

    w17 = BIN_WEIGHTS[WITHIN_17_MASK]
    w17_total = w17.sum()
    blind_pct_within_17deg = float(100.0 * np.dot(w17, frac_blind_per_bin[WITHIN_17_MASK]) / w17_total)
    ghost_pct_within_17deg = float(100.0 * np.dot(w17, frac_ghost_per_bin[WITHIN_17_MASK]) / w17_total)

    return {
        "time_weighted_blind_pct": time_weighted_blind_pct,
        "time_weighted_ghost_pct": time_weighted_ghost_pct,
        "time_weighted_mean_lit_area_um2": time_weighted_mean_lit_area_um2,
        "blind_pct_within_17deg": blind_pct_within_17deg,
        "ghost_pct_within_17deg": ghost_pct_within_17deg,
    }


def regenerate_coords(row):
    kwargs = degeneracy_filter.parse_spacing_params(row.spacing_params)
    gen_kwargs = dict(kwargs)
    if pd.notna(row.seed):
        gen_kwargs["seed"] = int(row.seed)
    coords, meta = degeneracy_filter.GEN_FUNCS[row.family](
        N=int(row.N_requested), a_hole_um=row.a_hole_um, **gen_kwargs)
    return coords


def preserve_legacy(path):
    if not os.path.exists(path):
        return
    import shutil
    i = 1
    legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    while os.path.exists(legacy_path):
        i += 1
        legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    shutil.copy2(path, legacy_path)
    print(f"preserved predecessor -> {legacy_path}")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify_weights_only", action="store_true",
                   help="run verify_weights() and exit, write nothing")
    p.add_argument("--limit", type=int, default=None, help="process only first N rows (testing)")
    return p.parse_args()


def main():
    args = parse_args()
    verify_weights()
    if args.verify_weights_only:
        return

    df = pd.read_csv(IN_CSV, dtype={"M": str})
    if args.limit:
        df = df.head(args.limit).copy()
    print(f"\nloaded {len(df)} rows from {IN_CSV}")
    print(f"N_THETA={N_THETA}  n_bins={len(GAZE_BINS)}  "
          f"total samples/row={N_THETA * len(GAZE_BINS)}")

    results = []
    n_done = 0
    for row in df.itertuples():
        coords = regenerate_coords(row)
        results.append(compute_row_gaze_metrics(coords, row.a_hole_um))
        n_done += 1
        if n_done % 1000 == 0:
            print(f"  {n_done}/{len(df)} rows done")

    results_df = pd.DataFrame(results)
    out_df = pd.concat([df.reset_index(drop=True), results_df], axis=1)

    preserve_legacy(OUT_CSV)
    out_df.to_csv(OUT_CSV, index=False)
    print(f"\nwrote {OUT_CSV} ({len(out_df)} rows)")

    print("\n--- time_weighted_ghost_pct / blind_pct summary by family ---")
    print(out_df.groupby("family")[["time_weighted_ghost_pct", "time_weighted_blind_pct"]]
          .mean().to_string())


if __name__ == "__main__":
    main()
