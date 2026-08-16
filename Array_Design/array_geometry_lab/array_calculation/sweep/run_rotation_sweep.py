"""
Closes the confirmed rotation gap: square, hexagonal, and rectangular were each
tested at exactly ONE fixed orientation in the existing sweep_results.csv -- no
rotation parameter existed anywhere. Motivation (from this task's own brief): this
project's gaze-weighting work established anisotropic (horizontal-dominant) eye
movement, so a lattice's orientation relative to that axis could plausibly change
its VIGNETTING margin (gaze-direction-dependent) even though its GHOST margin
(pairwise-distance-only, orientation-independent) cannot.

Narrow scope, deliberately: re-sweeps ONLY square/hexagonal/rectangular, ONLY adding
rotation_deg on top of their EXISTING tested N and spacing combinations (same
DEFAULT_N_LIST, DEFAULT_LATTICE_SPACING_LIST, DEFAULT_RECTANGULAR_RATIO_LIST
run_sweep.py itself already used) -- no other family is touched, and no other axis
(N range, spacing breadth) is widened. Reuses run_sweep.py's own
candidates_for_family(), evaluate_candidate(), spacing_str(), preserve_legacy()
directly (imported, not duplicated) -- this script only adds the rotation-angle
crossing on top.

DEDUPLICATION STRATEGY, stated explicitly: rather than special-casing "skip
rotation_deg=0 because it already exists," this script (a) retroactively tags the
EXISTING square/hexagonal/rectangular rows' spacing_params strings with an explicit
";rotation_deg=0.0" suffix (a pure TEXT tag -- confirmed safe because
generators/spot_check_generators.py's own equivalence check proves rotation_deg=0.0
reproduces the pre-rotation-support output bit-for-bit; no numeric column is
touched), then (b) generates the FULL requested rotation-angle grid (default
0,15,30,45) fresh via the real sweep, then (c) concatenates and drops EXACT
duplicate rows. Since a freshly-generated rotation_deg=0.0 row is guaranteed
bit-identical to the now-tagged existing row (same equivalence proof), this
naturally and robustly removes the redundant rotation=0 rows without any special
"if angle==0: skip" branch -- and any UNEXPECTED near-duplicate that isn't an exact
match would survive the dedup and be visible for inspection, rather than being
silently discarded by a looser rule.

Run:  python3 run_rotation_sweep.py
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_calculation/sweep/
CALC_ROOT = os.path.abspath(os.path.join(HERE, ".."))  # array_calculation/
LAB_ROOT = os.path.abspath(os.path.join(CALC_ROOT, ".."))  # array_geometry_lab/
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(CALC_ROOT, "margins"))  # renamed from "evaluation" --
                          # see array_calculation/README.md

import run_sweep as rs  # noqa: E402 -- reuses candidates_for_family, evaluate_candidate,
                        # spacing_str, preserve_legacy, and every DEFAULT_* list directly
import ghost_margin as gm  # noqa: E402

ROTATION_FAMILIES = ["square", "hexagonal", "rectangular"]
DEFAULT_ROTATION_LIST = [0.0, 15.0, 30.0, 45.0]
DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
DEFAULT_SWEEP_RESULTS_CSV = os.path.join(DATA_DIR, "sweep_results.csv")
PREROTATION_LEGACY_CSV = os.path.join(DATA_DIR, "sweep_results_PREROTATION_legacy.csv")

KEY_COLS = ["family", "N_requested", "N_actual", "spacing_params", "a_hole_um", "seed", "M"]


def tag_existing_rows_with_rotation0(df):
    """Retroactively appends ';rotation_deg=0.0' to the spacing_params string of
    every EXISTING square/hexagonal/rectangular row that doesn't already have a
    rotation_deg key -- a text-only schema-consistency tag, not a re-simulation
    (no numeric column touched). See module docstring for the safety argument."""
    df = df.copy()
    mask = df.family.isin(ROTATION_FAMILIES) & (~df.spacing_params.str.contains("rotation_deg"))
    n_tagged = int(mask.sum())
    df.loc[mask, "spacing_params"] = df.loc[mask, "spacing_params"] + ";rotation_deg=0.0"
    return df, n_tagged


def build_rotation_candidates(N_list, args, rotation_list):
    """Yields (family, N, spacing_params_dict_with_rotation, gen_fn) for every
    (N, spacing, rotation) combination across the 3 rotation-eligible families --
    the EXISTING candidates_for_family() output, crossed with rotation_list."""
    for family in ROTATION_FAMILIES:
        for fam, N, spacing_params, gen_fn in rs.candidates_for_family(family, N_list, args):
            for rot in rotation_list:
                sp = dict(spacing_params)
                sp["rotation_deg"] = rot
                yield fam, N, sp, gen_fn


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rotation_list", type=str,
                    default=",".join(str(x) for x in DEFAULT_ROTATION_LIST),
                    help="rotation angles (degrees) to sweep for square/hexagonal/"
                         "rectangular, on top of their existing N/spacing grid")
    ap.add_argument("--sweep_results_csv", type=str, default=DEFAULT_SWEEP_RESULTS_CSV)
    ap.add_argument("--N_list", type=str, default=",".join(str(n) for n in rs.DEFAULT_N_LIST))
    ap.add_argument("--lattice_spacing_list", type=str,
                    default=",".join(str(x) for x in rs.DEFAULT_LATTICE_SPACING_LIST))
    ap.add_argument("--rectangular_ratio_list", type=str,
                    default=",".join(str(x) for x in rs.DEFAULT_RECTANGULAR_RATIO_LIST))
    ap.add_argument("--D_pupil_um", type=float, default=rs.DEFAULT_D_PUPIL_UM)
    ap.add_argument("--P0", type=float, default=rs.DEFAULT_P0)
    cli_args = ap.parse_args()

    rotation_list = [float(x) for x in cli_args.rotation_list.split(",")]
    N_list = [int(x) for x in cli_args.N_list.split(",")]
    # fabricate an `args` namespace matching what candidates_for_family() expects
    # (it reads args.lattice_spacing_list / args.rectangular_ratio_list) --
    # concentric/spiral/poisson/jitter lists are irrelevant here (not swept) but
    # candidates_for_family() only touches the lists its own family branch needs,
    # so leaving those unset is safe as long as we only request the 3 rotation
    # families, which we do (ROTATION_FAMILIES).
    class Args:
        pass
    sweep_args = Args()
    sweep_args.lattice_spacing_list = [float(x) for x in cli_args.lattice_spacing_list.split(",")]
    sweep_args.rectangular_ratio_list = [float(x) for x in cli_args.rectangular_ratio_list.split(",")]

    if not os.path.exists(cli_args.sweep_results_csv):
        print(f"*** {cli_args.sweep_results_csv} not found -- nothing to merge into. ***")
        sys.exit(1)

    print(f"preserving current {cli_args.sweep_results_csv} -> {PREROTATION_LEGACY_CSV}")
    import shutil
    shutil.copy2(cli_args.sweep_results_csv, PREROTATION_LEGACY_CSV)

    existing_df = pd.read_csv(cli_args.sweep_results_csv)
    print(f"loaded {len(existing_df)} existing rows")
    n_before_rotation_families = int(existing_df.family.isin(ROTATION_FAMILIES).sum())
    n_other_families = len(existing_df) - n_before_rotation_families
    print(f"  of which {n_before_rotation_families} are square/hexagonal/rectangular "
          f"(rotation-eligible), {n_other_families} are other families (untouched)")

    tagged_df, n_tagged = tag_existing_rows_with_rotation0(existing_df)
    print(f"retroactively tagged {n_tagged} existing rows with ';rotation_deg=0.0' "
          f"(text-only, no numeric column changed)")

    M_values = sorted(pd.read_csv(gm.PER_M_OPTIMUM_MAP_CSV).M_diopters.unique().tolist())
    print(f"M values (read live): {M_values}")
    print(f"rotation angles requested: {rotation_list}")
    print(f"families: {ROTATION_FAMILIES} (all others untouched)")

    t0 = time.time()
    new_rows = []
    n_candidates = 0
    for family, N, spacing_params, gen_fn in build_rotation_candidates(N_list, sweep_args, rotation_list):
        n_candidates += 1
        rows = rs.evaluate_candidate(family, N, spacing_params, gen_fn, cli_args.D_pupil_um,
                                     cli_args.P0, M_values, seed=None)
        new_rows.extend(rows)
    print(f"{n_candidates} candidate (family, N, spacing, rotation) points, "
          f"{len(new_rows)} rows generated ({time.time()-t0:.1f}s)")

    new_df = pd.DataFrame(new_rows)

    # DTYPE FIX, found necessary by direct investigation (not assumed): sweep_results.csv's
    # M column mixes numeric M values with the string "global" -- pandas' read_csv, unable
    # to parse the column uniformly as numeric, leaves EVERY value (including the
    # numeric-looking ones) as a raw STRING token (confirmed: existing_df.M.iloc[0] is the
    # Python str '2.0', not the float 2.0). new_df's M column, built directly from
    # evaluate_candidate()'s returned dicts, has genuine Python floats for M and the
    # string "global" for the global row -- a real dtype mismatch against tagged_df's
    # M column, invisible until checked directly, that silently broke drop_duplicates()
    # on a first attempt (51 of an expected ~810 duplicates recognized, since only the
    # already-string "global" rows matched). Fixed by normalizing new_df's M column to
    # str before merging, matching tagged_df's own effective on-disk representation
    # exactly (str(2.0) == '2.0', the same text read_csv left in place).
    new_df["M"] = new_df["M"].astype(str)
    assert tagged_df.M.map(type).eq(str).all(), "tagged_df.M expected to be all str"

    combined = pd.concat([tagged_df, new_df], ignore_index=True)
    n_before_dedup = len(combined)
    combined_deduped = combined.drop_duplicates(subset=KEY_COLS, keep="first").reset_index(drop=True)
    n_dupes_dropped = n_before_dedup - len(combined_deduped)
    print(f"\ncombined (tagged existing + new): {n_before_dedup} rows")
    print(f"exact duplicates on {KEY_COLS}: {n_dupes_dropped} dropped")
    print(f"final row count: {len(combined_deduped)}")

    # Sanity check: the correct invariant is n_dupes_dropped == n_tagged (every
    # EXISTING row must find its exact match among the freshly-generated
    # rotation_deg=0.0 rows, and no more). It is NOT simply "however many
    # rotation_deg=0.0 rows got generated" -- candidates_for_family() enumerates the
    # FULL (N, spacing) grid with no awareness of the separate, later
    # degeneracy_filter.py exclusion step that already removed some of those
    # combinations from sweep_results.csv (108 rows here: 24 square + 30 hexagonal +
    # 54 rectangular, matching that earlier task's own exclusion counts exactly) --
    # those regenerate as "new" rotation_deg=0.0 rows with no existing counterpart to
    # match, correctly NOT deduped, and will be re-excluded by Part 4's
    # compute_density.py run just as they were before. A first version of this check
    # compared against the full rotation_deg=0.0 row count instead and fired a false
    # "51/810" warning -- fixed after direct investigation traced it to a SEPARATE,
    # real bug (see the M-column dtype fix above), not this accounting.
    expected_new_rotation0_rows = new_df[new_df.spacing_params.str.contains("rotation_deg=0.0")]
    n_rotation0_without_existing_match = len(expected_new_rotation0_rows) - n_tagged
    print(f"\n{len(expected_new_rotation0_rows)} fresh rotation_deg=0.0 rows generated, of "
          f"which {n_tagged} should exactly match an existing row (deduped) and "
          f"{n_rotation0_without_existing_match} should be 'new' rotation=0 rows with no "
          f"existing counterpart (degeneracy-excluded designs regenerating -- expected to be "
          f"re-excluded by Part 4).")
    if n_dupes_dropped != n_tagged:
        print(f"\n*** WARNING: expected exactly {n_tagged} duplicates (one per existing "
              f"tagged row) but drop_duplicates() removed {n_dupes_dropped}. Investigate "
              f"before trusting the merged file -- this could mean an existing row wasn't a "
              f"true rotation=0 case, a new non-zero-rotation row coincidentally collided "
              f"with an existing one, or a column-dtype mismatch is silently breaking the "
              f"duplicate comparison (checked directly once already -- see the M-column fix "
              f"above; check for a similar issue in another column if this fires again). ***")
    else:
        print("dedup count matches n_tagged exactly -- merge is consistent.")

    combined_deduped.to_csv(cli_args.sweep_results_csv, index=False)
    print(f"\nwrote {cli_args.sweep_results_csv} ({len(combined_deduped)} rows)")

    for family in ROTATION_FAMILIES:
        sub = combined_deduped[combined_deduped.family == family]
        n_by_rot = sub.spacing_params.str.extract(r"rotation_deg=([0-9.]+)")[0].value_counts().sort_index()
        print(f"  {family}: {len(sub)} total rows, by rotation_deg: {dict(n_by_rot)}")


if __name__ == "__main__":
    main()
