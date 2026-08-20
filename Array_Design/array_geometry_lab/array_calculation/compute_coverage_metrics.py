"""
compute_coverage_metrics.py -- NEW script (does not edit sweep/run_sweep.py,
compute_density.py, or anything in margins/), triggered by the CONFIRMED FINDING
that every candidate surviving this project's margin-aware gates has exactly ONE
active hole at phi=0 (n_active_holes_phi0=1, n_active_pairs_phi0=0): non-overlap
geometrically requires spacing >= hole diameter, while simultaneous two-hole
"fusion" (both illuminated at once) requires spacing well under that -- the two
constraints cannot both hold in this dataset's tested regime. This means the
array's real function is COVERAGE (some hole is always available as gaze/pupil
position wanders), not simultaneous multi-hole light-gathering. This script adds
two independent, SAMPLED (not assumed) physical quantities on top of that
finding, both as new columns on a new output CSV -- nothing existing is
overwritten or edited.

PART 1 -- blind_rate (a coverage metric): fraction of sampled pupil-center
positions, across BOTH the tested gaze range (phi, reusing
margins/vignetting_robustness.py's own phi_grid()/pupil_shift_um -- the SAME
gaze-shift model already validated and used everywhere else in this project) AND
local wander (see WANDER SAMPLING below), that admit ZERO illuminated holes
(reusing margins/active_pairs.py's own established illumination-fraction /
active_frac_threshold semantics -- NOT a new "illuminated" definition). SAMPLED,
not analytically assumed, per the task's own explicit instruction -- the two
sanity checks below (single hole; square/hex lattice near the touching limit)
report the ACTUAL computed numbers against Shen's closed-form point-coverage
floors (1-pi/4, 1-pi/(2*sqrt(3))), including if they do NOT match, rather than
assuming a match.

WANDER SAMPLING: this project has no existing cited fixational-eye-movement
amplitude, so "wander disc" is implemented as uniform sampling across one
lattice-period-sized square window ("unit cell" for periodic families:
square/hexagonal/rectangular/jittered_lattice, sized by that family's own pitch;
"characteristic local spacing" for the other 6 families, sized by their own
ring_spacing_um/c_um/spacing_factor*a_hole_um -- the SAME per-family field this
project's own comparison_metric/paper_score.py already reads for an analogous
purpose, re-derived here locally since array_calculation/ cannot import
array_evaluation/), centered at the origin (every generator in this project
places its pattern "closest-to-origin" / recentred on centroid -- see
generators/base_generator.py -- so the origin is always this project's own
established bulk-representative point). This is a documented modeling choice,
not a physical constant -- CLI-configurable via --unit_cell_samples_per_axis.

PART 2 -- optional perceptual fusion floor (--c_min_um, default 0.0 = current
optical-only behaviour, UNCHANGED): the resolvable threshold used in the margin
formula becomes max(c_resolvable_optical, c_min_um). Both the optical-only and
the c_min-floored ghost AND vignetting margins are emitted as separate columns
(4 new margin columns total) so the choice is always auditable, never silently
substituted. Implemented by RE-CALLING margins/ghost_margin.py's own
worst_case_ghost_margin() and margins/vignetting_robustness.py's own
worst_case_across_phi() -- both already accept an explicit resolvable_blur_um
override -- on REGENERATED coordinates (same deterministic
regenerate-from-spacing_params-and-seed approach compute_density.py already
established as valid), not a new formula. For M='global' rows, this loops over
every M in ghost_margin.ALL_M_VALUES with that M's own optical c_tot floored
individually before taking the worst case across M -- an ALGEBRAIC shortcut
(inverting the existing worst_case_ghost_margin column via its own
resolvable_blur_um column) was considered and rejected: a global row's own
resolvable_blur_um column is an INDEPENDENT worst-case-across-M reduction (see
sweep/run_sweep.py's own resolvable_blur_um documentation) that is not
guaranteed to be the same M that produced worst_case_ghost_margin, so only a
real per-M re-evaluation is correct here.

LAYER 1 (array_calculation/): physics/geometry only, reads
array_data/theoretical_data/sweep_results_with_density.csv (read-only, not
modified), writes a NEW file. No new families, no new metrics beyond blind_rate
and the two margin variants this task asked for.

Run:  python3 compute_coverage_metrics.py                    # c_min_um=0 (default)
      python3 compute_coverage_metrics.py --c_min_um 55       # Shen's floor
      python3 compute_coverage_metrics.py --sanity_check_only # prints Part 1's two
                                                                # sanity checks, writes nothing
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_calculation/
LAB_ROOT = os.path.dirname(HERE)  # array_geometry_lab/
sys.path.insert(0, HERE)
import degeneracy_filter  # noqa: E402 -- GEN_FUNCS + parse_spacing_params, same
                          # regeneration approach compute_density.py already uses
sys.path.insert(0, os.path.join(HERE, "margins"))
sys.path.insert(0, os.path.join(HERE, "engine"))
sys.path.insert(0, os.path.join(HERE, "generators"))
import ghost_margin as gm  # noqa: E402
import vignetting_robustness as vr  # noqa: E402
import active_pairs as ap  # noqa: E402
import vignetting_overlap as vo  # noqa: E402

DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
IN_CSV = os.path.join(DATA_DIR, "sweep_results_with_density.csv")

D_PUPIL_UM = 4000.0  # same project constant as sweep/run_sweep.py's
                     # DEFAULT_D_PUPIL_UM / test_part3_small_case.py's D_PUPIL_UM
PHI_GRID = vr.phi_grid()  # -25..25deg step 5deg, 11 samples -- SAME gaze range
                          # already used everywhere else in this project

SIMPLE_SPACING_KEY = {
    "square": "pitch_um",
    "hexagonal": "pitch_um",
    "jittered_lattice": "pitch_um",
    "concentric": "ring_spacing_um",
    "ring_offset_concentric": "ring_spacing_um",
    "concentric_centered": "ring_spacing_um",  # NEW, additive family -- same
                                               # spacing_params key as
                                               # ring_offset_concentric (same
                                               # ring construction)
    "fibonacci_spiral": "c_um",
    "golden_angle": "c_um",
    "archimedean_spiral": "c_um",
}


def cell_half_width_um(family, spacing_params, a_hole_um):
    """W/2 for the wander-sampling window -- see module docstring's WANDER
    SAMPLING section for the per-family field mapping (same mapping
    comparison_metric/paper_score.py uses for an analogous purpose, re-derived
    locally here -- array_calculation/ does not import array_evaluation/)."""
    params = degeneracy_filter.parse_spacing_params(spacing_params)
    if family == "poisson_disk":
        w = params["spacing_factor"] * a_hole_um
    elif family == "rectangular":
        w = float(np.sqrt(params["pitch_x_um"] * params["pitch_y_um"]))
    else:
        key = SIMPLE_SPACING_KEY.get(family)
        if key is None:
            raise ValueError(f"no spacing mapping defined for family {family!r}")
        w = params[key]
    return w / 2.0


def sample_pupil_positions_um(half_width_um, n_per_axis, phi_grid=PHI_GRID,
                              R_rot_mm=vo.DEFAULT_R_ROT_MM):
    """(K^2 * len(phi_grid), 2) array of pupil-center positions: a K x K grid
    spanning [-half_width_um, half_width_um] in both x and y (the wander
    window, centered at the origin -- see module docstring), offset along x by
    each tested phi's own gaze-induced pupil shift (vignetting_overlap's own
    validated pupil_shift_um(), the SAME single-axis convention
    margins/vignetting_robustness.py already uses)."""
    offsets_1d = np.linspace(-half_width_um, half_width_um, n_per_axis)
    ox, oy = np.meshgrid(offsets_1d, offsets_1d)
    ox = ox.ravel()
    oy = oy.ravel()
    all_positions = []
    for phi in phi_grid:
        shift_um = float(vo.pupil_shift_um(phi, R_rot_mm))
        all_positions.append(np.column_stack([ox + shift_um, oy]))
    return np.vstack(all_positions)


def any_hole_active_batch(coords_um, a_hole_um, pupil_centers_um,
                          active_frac_threshold=ap.DEFAULT_ACTIVE_FRAC_THRESHOLD):
    """Vectorized (all sampled positions x all holes at once, via numpy
    broadcasting) version of active_pairs.hole_illumination_fractions's own
    per-hole test ('active' iff overlap_area/hole_area >= active_frac_threshold
    -- reused unchanged, not redefined). Returns a boolean array, one entry per
    sampled pupil position: True iff at least one hole is active there."""
    coords_um = np.asarray(coords_um, dtype=float)
    if len(coords_um) == 0:
        return np.zeros(len(pupil_centers_um), dtype=bool)
    R_h = a_hole_um / 2.0
    R_p = D_PUPIL_UM / 2.0
    dx = pupil_centers_um[:, 0][:, None] - coords_um[:, 0][None, :]
    dy = pupil_centers_um[:, 1][:, None] - coords_um[:, 1][None, :]
    delta = np.sqrt(dx ** 2 + dy ** 2)
    areas = vo.overlap_area_um2(delta, R_p, R_h)
    hole_area = np.pi * R_h ** 2
    fractions = areas / hole_area
    return (fractions >= active_frac_threshold).any(axis=1)


def compute_blind_rate(coords_um, half_width_um, a_hole_um, n_per_axis, phi_grid=PHI_GRID):
    """phi_grid defaults to the full tested gaze range (this is what the main
    per-row column below uses -- 'across the tested phi range AND within the
    unit cell', per the task's own instruction). Sanity checks below ALSO call
    this with phi_grid=[0.0] -- gaze-shift alone can legitimately blind an
    ISOLATED single hole at large phi (the pupil moves ~5.7mm off-axis at
    phi=25deg, DEFAULT_R_ROT_MM=13.5mm -- a real, already-validated effect, not
    a sampling bug), which is a different question from whether the WANDER
    sampling itself is implemented correctly. Both are reported, not conflated."""
    positions = sample_pupil_positions_um(half_width_um, n_per_axis, phi_grid=phi_grid)
    active = any_hole_active_batch(coords_um, a_hole_um, positions)
    return float(1.0 - active.mean())


def verify_blind_rate_sanity(n_per_axis):
    """PART 1's REQUIRED sanity checks (task's own instruction: 'sample it,
    don't assume', 'report whether it reproduces those floors'). Prints the
    ACTUAL sampled numbers against Shen's closed-form point-coverage floors --
    does not force a match. Reports BOTH a phi=0-only (wander dimension in
    isolation -- the only version that could ever match a gaze-independent
    closed-form constant) and the full phi+wander combined number (what the
    main sweep's blind_rate column below actually uses)."""
    print("=== blind_rate sanity checks ===")

    coords_single = np.array([[0.0, 0.0]])
    br_single_phi0 = compute_blind_rate(coords_single, half_width_um=1000.0, a_hole_um=400.0,
                                        n_per_axis=n_per_axis, phi_grid=[0.0])
    br_single_full = compute_blind_rate(coords_single, half_width_um=1000.0, a_hole_um=400.0,
                                        n_per_axis=n_per_axis)
    print(f"single hole at origin (D_pupil_um={D_PUPIL_UM}, a_hole_um=400, wander window +-1000um):")
    print(f"  phi=0 only (wander dimension in isolation): blind_rate = {br_single_phi0:.6f} (expect 0.0)")
    print(f"  full phi range {list(PHI_GRID)}: blind_rate = {br_single_full:.6f} "
          f"(NOT expected to be 0 -- a lone hole cannot stay illuminated once gaze-induced "
          f"pupil shift moves the pupil ~5.7mm off-axis at phi=+-25deg; this is the same "
          f"CONFIRMED FINDING this task is built on, re-derived here: coverage needs "
          f"multiple holes, one hole alone cannot cover the tested gaze range)")

    import square
    import hexagonal
    a_hole = 749.0  # just under the pitch, sidesteps compute_density.py's own
                    # documented exact-tangency tie-break degeneracy at ratio==1.0
    pitch = 750.0
    coords_sq, _ = square.generate(N=400, a_hole_um=a_hole, pitch_um=pitch, rotation_deg=0.0)
    coords_hex, _ = hexagonal.generate(N=400, a_hole_um=a_hole, pitch_um=pitch, rotation_deg=0.0)
    br_sq_phi0 = compute_blind_rate(coords_sq, half_width_um=pitch / 2.0, a_hole_um=a_hole,
                                    n_per_axis=n_per_axis, phi_grid=[0.0])
    br_hex_phi0 = compute_blind_rate(coords_hex, half_width_um=pitch / 2.0, a_hole_um=a_hole,
                                     n_per_axis=n_per_axis, phi_grid=[0.0])
    br_sq_full = compute_blind_rate(coords_sq, half_width_um=pitch / 2.0, a_hole_um=a_hole,
                                    n_per_axis=n_per_axis)
    br_hex_full = compute_blind_rate(coords_hex, half_width_um=pitch / 2.0, a_hole_um=a_hole,
                                     n_per_axis=n_per_axis)
    floor_sq = 1.0 - np.pi / 4.0
    floor_hex = 1.0 - np.pi / (2.0 * np.sqrt(3.0))
    print(f"\nsquare lattice, s={pitch}um ~= d={a_hole}um (near-touching), D_pupil_um={D_PUPIL_UM}:")
    print(f"  phi=0 only: blind_rate = {br_sq_phi0:.6f}  (Shen's closed-form point-coverage floor: {floor_sq:.6f})")
    print(f"  full phi range: blind_rate = {br_sq_full:.6f}")
    print(f"hexagonal lattice, s={pitch}um ~= d={a_hole}um (near-touching), D_pupil_um={D_PUPIL_UM}:")
    print(f"  phi=0 only: blind_rate = {br_hex_phi0:.6f}  (Shen's closed-form point-coverage floor: {floor_hex:.6f})")
    print(f"  full phi range: blind_rate = {br_hex_full:.6f}")
    print("\n(This project's D_pupil_um=4000um is not a point -- a real pupil this "
          "large, straddling many holes at once at this pitch, is expected to see "
          "'blind' far less often than Shen's own point-aperture derivation, even at "
          "phi=0. A mismatch here is a reportable physical finding, not a bug.)")
    return {"single_hole_phi0": br_single_phi0, "single_hole_full_phi": br_single_full,
           "square_near_touching_phi0": br_sq_phi0, "square_near_touching_full_phi": br_sq_full,
           "hexagonal_near_touching_phi0": br_hex_phi0, "hexagonal_near_touching_full_phi": br_hex_full,
           "shen_floor_square": floor_sq, "shen_floor_hexagonal": floor_hex}


def floored_ghost_margin(coords_um, M_diopters, a_hole_um, c_min_um):
    optical_c_tot = gm.load_resolvable_blur_um(M_diopters, a_hole_um)
    floored_c_tot = max(optical_c_tot, c_min_um)
    r_optical = gm.worst_case_ghost_margin(coords_um, D_PUPIL_UM, M_diopters, a_hole_um,
                                           resolvable_blur_um=optical_c_tot)
    r_floored = gm.worst_case_ghost_margin(coords_um, D_PUPIL_UM, M_diopters, a_hole_um,
                                           resolvable_blur_um=floored_c_tot)
    return r_optical["worst_case_margin"], r_floored["worst_case_margin"]


def floored_vignetting_margin(coords_um, M_diopters, a_hole_um, c_min_um):
    optical_c_tot = gm.load_resolvable_blur_um(M_diopters, a_hole_um)
    floored_c_tot = max(optical_c_tot, c_min_um)
    v_optical = vr.worst_case_across_phi(coords_um, D_PUPIL_UM, M_diopters, a_hole_um,
                                         resolvable_blur_um=optical_c_tot)
    v_floored = vr.worst_case_across_phi(coords_um, D_PUPIL_UM, M_diopters, a_hole_um,
                                         resolvable_blur_um=floored_c_tot)
    return v_optical["worst_case_vignetting_margin"], v_floored["worst_case_vignetting_margin"]


def regenerate_coords(row):
    family = row.family
    kwargs = degeneracy_filter.parse_spacing_params(row.spacing_params)
    gen_kwargs = dict(kwargs)
    if pd.notna(row.seed):
        gen_kwargs["seed"] = int(row.seed)
    coords, meta = degeneracy_filter.GEN_FUNCS[family](
        N=int(row.N_requested), a_hole_um=row.a_hole_um, **gen_kwargs)
    return coords


def process_row(row, c_min_um, n_per_axis):
    coords = regenerate_coords(row)
    half_width = cell_half_width_um(row.family, row.spacing_params, row.a_hole_um)
    blind_rate = compute_blind_rate(coords, half_width, row.a_hole_um, n_per_axis)

    if row.M == "global":
        ghost_opt_vals, ghost_floor_vals = [], []
        vig_opt_vals, vig_floor_vals = [], []
        for M in gm.ALL_M_VALUES:
            a_hole_this_M = gm.load_acuity_optimal_aperture(M)
            # global-scope coords were generated at THIS row's own a_hole_um
            # (a_hole_for_global, the largest in the tested range -- see
            # sweep/run_sweep.py's evaluate_candidate()); the per-M lookup
            # below only picks that M's OWN resolvable_blur_um for the
            # threshold, exactly mirroring ghost_margin.evaluate_global()'s
            # own per-M loop -- geometry itself is not regenerated per M.
            g_opt, g_floor = floored_ghost_margin(coords, M, a_hole_this_M, c_min_um)
            ghost_opt_vals.append(g_opt)
            ghost_floor_vals.append(g_floor)
            v_opt, v_floor = floored_vignetting_margin(coords, M, row.a_hole_um, c_min_um)
            vig_opt_vals.append(v_opt)
            vig_floor_vals.append(v_floor)
        ghost_optical = min(ghost_opt_vals)
        ghost_floored = min(ghost_floor_vals)
        vig_optical = min(vig_opt_vals)
        vig_floored = min(vig_floor_vals)
    else:
        M = float(row.M)
        ghost_optical, ghost_floored = floored_ghost_margin(coords, M, row.a_hole_um, c_min_um)
        vig_optical, vig_floored = floored_vignetting_margin(coords, M, row.a_hole_um, c_min_um)

    return {
        "blind_rate": blind_rate,
        "ghost_margin_optical": ghost_optical,
        "ghost_margin_c_min_floored": ghost_floored,
        "vignetting_margin_optical": vig_optical,
        "vignetting_margin_c_min_floored": vig_floored,
    }


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
    p.add_argument("--c_min_um", type=float, default=0.0,
                   help="perceptual fusion floor (Shen's c_min); 0.0 = current "
                        "optical-only behaviour, unchanged (default)")
    p.add_argument("--unit_cell_samples_per_axis", type=int, default=9,
                   help="K: blind_rate samples a KxK grid per phi across the "
                        "wander window (default 9 -> 81 samples/phi x 11 phi "
                        "= 891 pupil positions per row)")
    p.add_argument("--sanity_check_only", action="store_true",
                   help="print Part 1's sanity checks and exit, write nothing")
    p.add_argument("--limit", type=int, default=None,
                   help="process only the first N rows (for testing runtime)")
    p.add_argument("--out_csv", type=str, default=None)
    return p.parse_args()


def main():
    args = parse_args()

    sanity = verify_blind_rate_sanity(args.unit_cell_samples_per_axis)
    if args.sanity_check_only:
        return

    out_csv = args.out_csv or os.path.join(
        DATA_DIR, f"sweep_results_with_coverage_cmin{int(args.c_min_um)}.csv")

    df = pd.read_csv(IN_CSV, dtype={"M": str})
    if args.limit:
        df = df.head(args.limit).copy()
    print(f"\nloaded {len(df)} rows from {IN_CSV}")
    print(f"c_min_um={args.c_min_um}  unit_cell_samples_per_axis={args.unit_cell_samples_per_axis}")

    results = []
    n_done = 0
    for row in df.itertuples():
        results.append(process_row(row, args.c_min_um, args.unit_cell_samples_per_axis))
        n_done += 1
        if n_done % 500 == 0:
            print(f"  {n_done}/{len(df)} rows done")

    results_df = pd.DataFrame(results)
    out_df = pd.concat([df.reset_index(drop=True), results_df], axis=1)

    preserve_legacy(out_csv)
    out_df.to_csv(out_csv, index=False)
    print(f"\nwrote {out_csv} ({len(out_df)} rows)")

    print("\n--- blind_rate summary by family ---")
    print(out_df.groupby("family")["blind_rate"].describe()[["count", "mean", "min", "max"]].to_string())

    changed = (out_df["ghost_margin_c_min_floored"] != out_df["ghost_margin_optical"]).sum()
    print(f"\nc_min_um={args.c_min_um}: ghost_margin changed vs optical-only for "
          f"{changed}/{len(out_df)} rows")


if __name__ == "__main__":
    main()
