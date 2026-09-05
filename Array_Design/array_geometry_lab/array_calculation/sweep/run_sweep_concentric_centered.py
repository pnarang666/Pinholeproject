"""
run_sweep_concentric_centered.py -- generates ONLY the NEW concentric_centered
family's sweep rows, using EXACTLY the same (N, ring_spacing_um,
holes_per_ring0) grid, M grid, D_pupil_um, and P0 that
sweep/run_sweep.py already uses for ring_offset_concentric (imported
directly from run_sweep.py, not duplicated), then APPENDS these new rows to
the existing array_data/theoretical_data/sweep_results.csv.

Additive only: does not read-modify-rewrite the existing file's content (which
risks silent reformatting on a full round trip) -- the existing file is
legacy-preserved verbatim, then the new rows are appended in raw CSV form
(mode='a', no header), with columns explicitly reordered to match the
existing file's own header exactly first. Does not modify sweep/run_sweep.py.

Run:  python3 run_sweep_concentric_centered.py
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_calculation/sweep/
CALC_ROOT = os.path.abspath(os.path.join(HERE, ".."))  # array_calculation/
LAB_ROOT = os.path.abspath(os.path.join(CALC_ROOT, ".."))  # array_geometry_lab/

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(CALC_ROOT, "generators"))
sys.path.insert(0, os.path.join(CALC_ROOT, "margins"))
import run_sweep as rs  # noqa: E402 -- reuses evaluate_candidate(),
                        # DEFAULT_N_LIST, DEFAULT_CONCENTRIC_RING_SPACING_LIST,
                        # DEFAULT_CONCENTRIC_HOLES_PER_RING0_LIST,
                        # DEFAULT_D_PUPIL_UM, DEFAULT_P0 -- the exact same grid
                        # ring_offset_concentric is swept over, for direct
                        # comparability.
import concentric_centered  # noqa: E402
import ghost_margin as gm  # noqa: E402 -- for the live M grid, same source
                           # run_sweep.py itself uses.

DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
SWEEP_RESULTS_CSV = os.path.join(DATA_DIR, "sweep_results.csv")


def preserve_legacy(path):
    """Standard project convention (see run_sweep.py's own preserve_legacy):
    copies path to path_legacyN.csv (auto-incrementing) before it gets
    overwritten, so nothing is ever silently lost."""
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


def main():
    M_values = sorted(pd.read_csv(gm.PER_M_OPTIMUM_MAP_CSV).M_diopters.unique().tolist())
    print(f"M values (read live from per_M_optimum_map.csv): {M_values}")

    N_list = rs.DEFAULT_N_LIST
    ring_spacing_list = rs.DEFAULT_CONCENTRIC_RING_SPACING_LIST
    holes_per_ring0_list = rs.DEFAULT_CONCENTRIC_HOLES_PER_RING0_LIST
    print(f"N_list={N_list}  ring_spacing_list={ring_spacing_list}  "
          f"holes_per_ring0_list={holes_per_ring0_list}  "
          f"D_pupil_um={rs.DEFAULT_D_PUPIL_UM}  P0={rs.DEFAULT_P0}  "
          f"(all identical to ring_offset_concentric's own grid in run_sweep.py, "
          f"imported not duplicated)")

    all_rows = []
    n_candidates = 0
    for N in N_list:
        for rspac in ring_spacing_list:
            for hpr0 in holes_per_ring0_list:
                spacing_params = {"ring_spacing_um": rspac, "holes_per_ring0": hpr0}
                rows = rs.evaluate_candidate(
                    "concentric_centered", N, spacing_params, concentric_centered.generate,
                    rs.DEFAULT_D_PUPIL_UM, rs.DEFAULT_P0, M_values, seed=None)
                all_rows.extend(rows)
                n_candidates += 1
    new_df = pd.DataFrame(all_rows)
    print(f"\n{n_candidates} candidate (N, ring_spacing, holes_per_ring0) points -> "
          f"{len(new_df)} rows ({len(M_values)} per_M + 1 global each)")

    with open(SWEEP_RESULTS_CSV) as f:
        header_cols = f.readline().strip().split(",")
    new_df = new_df[header_cols]  # exact column order match, defensive

    preserve_legacy(SWEEP_RESULTS_CSV)
    new_df.to_csv(SWEEP_RESULTS_CSV, mode="a", header=False, index=False)
    print(f"appended {len(new_df)} concentric_centered rows to {SWEEP_RESULTS_CSV} "
          f"(existing rows untouched -- raw append, not a read-modify-rewrite)")

    print(f"\nstructurally_safe=True: {int(new_df.structurally_safe.sum())}/{len(new_df)} rows")


if __name__ == "__main__":
    main()
