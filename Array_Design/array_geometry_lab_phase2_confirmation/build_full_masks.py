"""
PART 1 of the Phase 2 (full-physics) confirmation pass.

For each of the 9 Metric-1 finalists in
../array_geometry_lab/comparison_metric/metric1_max_density_per_M.csv (read LIVE,
never hardcoded -- see that file for the exact parameters used), regenerates the
finalist's exact hole-coordinate list by calling the SAME generator function (from
../array_geometry_lab/generators/) with the SAME parameters recorded in the CSV row,
and confirms the regenerated N_actual matches the CSV's own recorded N_actual
exactly -- the same sanity check Phase 1's own Part 1 validation gate used. If ANY
finalist fails this check, this script STOPS (raises) before writing anything for
ANY finalist, per this task's explicit requirement ("do not silently skip a
mismatched finalist and proceed with the rest").

WHAT "CONVERT TO array_psf_envelope.py's MASK FORMAT" TURNED OUT TO MEAN, CHECKED
BEFORE GUESSING: array_psf_envelope.py's own array_psf(a_hole_um, pitch_um, M,
packing="square", ...) function does NOT accept an external hole-coordinate list at
all -- it builds its OWN coordinates internally via
photometry/array_photometry.py::hole_lattice(), which only supports "square"/"hex"
INFINITE regular lattices (checked: no other packing string, no explicit-coordinate
parameter exists anywhere in that call chain). None of our 9 finalists are
expressible that way (rectangular has independent x/y pitch, jittered_lattice and
archimedean_spiral are irregular/finite, square here is a finite N=9 array, not an
infinite lattice) -- so array_psf() itself cannot be called unchanged on these
geometries.

What array_psf() DOES internally, once past its own lattice-generation call, is
operate on plain (hx_um, hy_um) numpy arrays of hole-center coordinates in
micrometres, relative to the pattern's own centroid -- exactly
generators/*.py generate()'s own coords_um output format, column-split. THAT is the
"mask format" the reusable part of array_psf_envelope.py actually consumes: not a
boolean 2D image, a coordinate list (Eq. (2) is a sum of shifted single-hole PSF
copies, one per hole coordinate, not a spatial transmission mask multiplied through
a propagator). run_full_physics.py (Part 2) therefore imports
array_psf_envelope.single_hole_psf() directly (the actual expensive, validated ASM
propagation, per this task's explicit import-not-copy rule) and performs its OWN
roll-and-sum over these exact coordinates, replicating array_psf()'s own documented
algorithm (recenter on the summed pattern's own centroid, exclude holes beyond
r_max_lens) -- not reimplementing any physics, only supplying the geometry input
array_psf() itself has no parameter for.

Output: finalist_coords.csv (long format: finalist_id, family, M, x_um, y_um) and
finalist_metadata.csv (one row per finalist, N_requested/N_actual/spacing_params/
a_hole_um/seed/M plus the regenerated N_actual and the pass/fail check).

Run:  python3 build_full_masks.py
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ARRAY_DESIGN = os.path.dirname(HERE)
LAB = os.path.join(ARRAY_DESIGN, "array_geometry_lab")

sys.path.insert(0, os.path.join(LAB, "generators"))
sys.path.insert(0, os.path.join(LAB, "evaluation"))

import square, hexagonal, concentric, fibonacci_spiral, golden_angle  # noqa: E402
import rectangular, archimedean_spiral, ring_offset_concentric  # noqa: E402
import poisson_disk, jittered_lattice  # noqa: E402
import ghost_margin as gm  # noqa: E402

GEN_FUNCS = {
    "square": square.generate, "hexagonal": hexagonal.generate,
    "concentric": concentric.generate, "fibonacci_spiral": fibonacci_spiral.generate,
    "golden_angle": golden_angle.generate, "rectangular": rectangular.generate,
    "archimedean_spiral": archimedean_spiral.generate,
    "ring_offset_concentric": ring_offset_concentric.generate,
    "poisson_disk": poisson_disk.generate, "jittered_lattice": jittered_lattice.generate,
}

FINALISTS_CSV = os.path.join(LAB, "comparison_metric", "metric1_max_density_per_M.csv")
D_PUPIL_UM = 4000.0  # matches array_geometry_lab/evaluation's own default (ghost_margin.py,
                     # vignetting_robustness.py) and array_psf_envelope.py's D_PUPIL_UM

OUT_COORDS_CSV = os.path.join(HERE, "finalist_coords.csv")
OUT_METADATA_CSV = os.path.join(HERE, "finalist_metadata.csv")


def parse_spacing_params(s):
    d = {}
    if pd.isna(s) or s == "":
        return d
    for part in str(s).split(";"):
        k, v = part.split("=")
        try:
            v = float(v)
        except ValueError:
            pass
        d[k] = v
    return d


def resolve_M_for_optics(family, coords_um, M_col_value):
    """Every finalist except the 'global'-scope one has a literal M value in the CSV
    -- used as-is. The 'global' finalist's own coordinates were generated at ONE
    a_hole_um (the largest across the tested M range, per
    evaluation/ghost_margin.py::evaluate_global()'s own documented convention) but a
    real build still needs ONE M for wave-optics purposes (eye axial length depends
    on M). Resolved here, not arbitrarily: re-run evaluate_global() on this
    finalist's own regenerated coordinates and use the M at which its OWN worst-case
    margin across the whole M range was found (worst_case_M) -- i.e. the physically
    most stringent M for this exact design, not an arbitrary pick."""
    if M_col_value != "global":
        return float(M_col_value), None
    result = gm.evaluate_global(coords_um, D_PUPIL_UM)
    chosen_M = float(result["worst_case_M"])
    note = (f"'global' scope: M resolved to worst_case_M={chosen_M}D from "
           f"evaluate_global() re-run on this finalist's own coordinates "
           f"(worst_case_margin={result['worst_case_margin']})")
    return chosen_M, note


def main():
    df = pd.read_csv(FINALISTS_CSV)
    print(f"loaded {len(df)} finalists from {FINALISTS_CSV}")

    all_coord_rows = []
    all_meta_rows = []
    any_mismatch = False

    for i, row in df.iterrows():
        family = row.family
        kwargs = parse_spacing_params(row.spacing_params)
        if pd.notna(row.seed):
            kwargs["seed"] = int(row.seed)

        coords, meta = GEN_FUNCS[family](N=int(row.N_requested), a_hole_um=row.a_hole_um, **kwargs)
        N_actual_regenerated = int(meta["N_actual"])
        N_actual_expected = int(row.N_actual)
        match = (N_actual_regenerated == N_actual_expected)

        M_resolved, M_note = resolve_M_for_optics(family, coords, row.M)

        finalist_id = f"M{row.M}_{family}"
        print(f"[{finalist_id}] N_requested={int(row.N_requested)} "
              f"N_actual_expected={N_actual_expected} N_actual_regenerated={N_actual_regenerated} "
              f"{'MATCH' if match else '*** MISMATCH ***'}  a_hole_um={row.a_hole_um} "
              f"M_resolved={M_resolved}D" + (f"  ({M_note})" if M_note else ""))
        if not match:
            any_mismatch = True

        all_meta_rows.append({
            "finalist_id": finalist_id, "family": family, "M_csv": row.M,
            "M_resolved_for_optics": M_resolved, "M_resolution_note": M_note,
            "N_requested": int(row.N_requested), "N_actual_expected": N_actual_expected,
            "N_actual_regenerated": N_actual_regenerated, "N_actual_match": match,
            "spacing_params": row.spacing_params, "a_hole_um": row.a_hole_um,
            "seed": row.seed,
        })
        for x_um, y_um in coords:
            all_coord_rows.append({"finalist_id": finalist_id, "family": family,
                                   "M_csv": row.M, "x_um": x_um, "y_um": y_um})

    meta_df = pd.DataFrame(all_meta_rows)

    if any_mismatch:
        print("\n*** N_actual SANITY CHECK FAILED for at least one finalist. ***")
        print("Per this task's explicit instruction, STOPPING before writing any output "
              "for ANY finalist (not silently skipping the mismatched one) -- something "
              "about a generator or its stored parameters has changed since the sweep ran.")
        print(meta_df[~meta_df.N_actual_match].to_string())
        sys.exit(1)

    print(f"\nAll {len(meta_df)} finalists PASS the N_actual sanity check.")

    coords_df = pd.DataFrame(all_coord_rows)
    coords_df.to_csv(OUT_COORDS_CSV, index=False)
    meta_df.to_csv(OUT_METADATA_CSV, index=False)
    print(f"wrote {OUT_COORDS_CSV} ({len(coords_df)} hole-coordinate rows across "
          f"{len(meta_df)} finalists)")
    print(f"wrote {OUT_METADATA_CSV} ({len(meta_df)} finalist rows)")


if __name__ == "__main__":
    main()
