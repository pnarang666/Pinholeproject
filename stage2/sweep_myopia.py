"""
CLI-driven main sweep: cornea -> pupil -> lens -> retina, across aperture diameter,
wavelength, gap distance, and myopia level. Runs the Airy-disk validation gate first and
refuses to sweep if it fails. Never modifies stage1_v2's code or CSVs, and never
imports stage1_v2 except through pipeline_junction.

Usage:
    python3 sweep_myopia.py
    python3 sweep_myopia.py --a-hole-um 125,150,175,200 --M-diopters 1,2,4,8 \\
        --no-refractive-index-correction --output outputs/my_run.csv
    python3 sweep_myopia.py --a-hole-start-um 75 --a-hole-stop-um 2000 --a-hole-step-um 25
"""

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

import myopia_axial
import phase2_retina as p2
import pipeline_junction as junction
import validation_gate

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")


def parse_float_list(text):
    return [float(v.strip()) for v in text.split(",") if v.strip()]


def range_values(start, stop, step):
    if step <= 0:
        return [start]
    n = int(round((stop - start) / step)) + 1
    return [start + i * step for i in range(n)]


def resolve_a_hole_values_um(args):
    """--a-hole-start-um/--a-hole-stop-um/--a-hole-step-um (a continuous range, matching
    stage1_v2's own sweep-tab convention) takes priority over --a-hole-um (an explicit
    comma list) when start is provided; otherwise falls back to the comma list."""
    if args.a_hole_start_um is not None:
        return range_values(args.a_hole_start_um, args.a_hole_stop_um, args.a_hole_step_um)
    return parse_float_list(args.a_hole_um)


def build_arg_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    # Re-derived from stage1_v2 directly (see stage2/README.md) -- NOT the same as the
    # "100-200um" figure assumed at the start of this task, which turned out to describe
    # neither of the two CSV sources actually found on disk. 125-200um step 25 sits
    # inside the region that passes stage1_v2's full per-config validation outright, and
    # is the closest reasonable default consistent with what was originally assumed --
    # override freely, nothing here is load-bearing.
    p.add_argument("--a-hole-um", type=str, default="125,150,175,200",
                    help="Comma-separated aperture diameters in micrometers. Ignored if "
                         "--a-hole-start-um is given.")
    p.add_argument("--a-hole-start-um", type=float, default=None,
                    help="Start of a continuous aperture-diameter range, micrometers. "
                         "When given, overrides --a-hole-um; must be paired with "
                         "--a-hole-stop-um and --a-hole-step-um.")
    p.add_argument("--a-hole-stop-um", type=float, default=None,
                    help="End of the aperture-diameter range (inclusive), micrometers.")
    p.add_argument("--a-hole-step-um", type=float, default=None,
                    help="Step size for the aperture-diameter range, micrometers.")
    p.add_argument("--wavelengths-nm", type=str, default="450,550,650",
                    help="Comma-separated wavelengths in nanometers.")
    p.add_argument("--d-gap-mm", type=str, default="12,15",
                    help="Comma-separated pinhole-to-cornea gap distances in millimeters.")
    p.add_argument("--M-diopters", type=str, default="1,2,3,4,5,6,8",
                    help="Comma-separated myopia levels in diopters -- the sweep axis, not fixed.")
    p.add_argument("--D-pupil-um", type=float, default=4000.0,
                    help="Pupil diameter in micrometers.")
    p.add_argument("--P0", type=float, default=60.0, help="Emmetropic eye power, diopters.")
    p.add_argument("--n-prime", type=float, default=1.336, help="Vitreous refractive index.")
    p.add_argument("--refractive-index-correction", dest="refractive_index_correction",
                    action="store_true", default=True)
    p.add_argument("--no-refractive-index-correction", dest="refractive_index_correction",
                    action="store_false")
    p.add_argument("--grid-N", type=int, default=2048,
                    help="Grid size for the sweep. Default 2048 trades some accuracy for "
                         "speed vs. the validation gate's N=4096 reference "
                         "(~2.4s vs ~14.5s per point, measured on this machine); raise "
                         "this for a final/confirmatory pass.")
    p.add_argument("--window-L-mm", type=float, default=6.0, help="Simulation window size, mm.")
    p.add_argument("--output", type=str, default=None,
                    help="Output CSV path. Defaults to stage2/outputs/myopia_sweep_<N>pts.csv")
    p.add_argument("--skip-gate", action="store_true",
                    help="Skip the Airy-disk validation gate. NOT recommended -- for debugging only.")
    return p


def refractive_index_mode_label(refractive_index_correction, n_prime):
    if refractive_index_correction:
        return f"anatomical (n'={n_prime:g})"
    return "air-equivalent (n'=1.0)"


def build_row(a_hole, wavelength, d_gap, M_diopters, args):
    result = p2.run_pipeline_point(
        a_hole=a_hole, wavelength=wavelength, d_gap=d_gap, grid_N=args.grid_N,
        window_L_mm=args.window_L_mm, M_diopters=M_diopters, P0=args.P0, n_prime=args.n_prime,
        D_pupil_um=args.D_pupil_um, refractive_index_correction=args.refractive_index_correction,
    )
    myopia = result["myopia"]
    cornea = result["cornea_result"]

    # v2's existing gap-stage column conventions (a_hole_um, wavelength_nm, z_gap_mm, N_F,
    # regime, grid_N, window_L_mm), computed here via pipeline_junction's re-exported v2
    # primitives ONLY -- not by re-deriving v2's full run_configuration/run_validation
    # stack, which also computes FWHM/threshold diagnostics this sweep has no use for.
    N_F = junction.fresnel_number(a_hole, wavelength, d_gap)
    regime = junction.fresnel_regime(N_F)

    row = {
        "a_hole_um": a_hole * 1e6,
        "wavelength_nm": wavelength * 1e9,
        "z_gap_mm": d_gap * 1e3,
        "N_F": N_F,
        "regime": regime,
        "grid_N": args.grid_N,
        "window_L_mm": args.window_L_mm,
        "M_diopters": M_diopters,
        "P0": args.P0,
        "n_prime": args.n_prime,
        "refractive_index_mode": refractive_index_mode_label(args.refractive_index_correction, args.n_prime),
        "L0_mm": myopia["L0"] * 1e3,
        "L_ax_mm": myopia["L_ax"] * 1e3,
        "f_eye_mm": myopia["f_eye"] * 1e3,
        "D_pupil_um": args.D_pupil_um,
        "junction_check_passed": result["junction_check_passed"],
        "junction_fail_reason": result["junction_fail_reason"] or "",
        "r_EE_50_retina_um": None,
        "r_EE_80_retina_um": None,
        "r_EE_90_retina_um": None,
        "cornea_energy_conservation_rel_error": None,
        "cornea_band_limit_energy_suppressed_frac": cornea["band_info"]["fraction_energy_suppressed"],
    }

    return row, result


def finalize_row(row, result, a_hole, N, dx):
    """Fills in fields that need the cornea field itself (kept out of build_row to keep
    that function's argument list -- a_hole/wavelength/d_gap/M/args -- self-explanatory)."""
    cornea = result["cornea_result"]
    U_cornea = cornea["U_cornea"]
    I_cornea = np.abs(U_cornea) ** 2
    # FIXED: compare against the ACTUAL DISCRETE input power of the rasterized aperture
    # (sum|U0|^2*dx^2, matching stage1_v2/physics.py's own run_configuration()), not the
    # continuous geometric area pi*(a_hole/2)^2. A circle rasterized on a square grid
    # never has exactly pi*r^2 of area; comparing discrete output to a continuous
    # reference mixed a ~0.05-0.35% pixelation artifact into a column whose name claims
    # to measure propagation fidelity -- confirmed that artifact alone reproduced the
    # entire previously-reported 0.048%-0.35% error range for this sweep, meaning the old
    # number carried no evidence either way about whether the ASM propagation itself
    # conserved energy.
    U0, _, _ = junction.circular_aperture(N, N * dx, a_hole)
    input_power = float(np.sum(np.abs(U0) ** 2) * dx ** 2)
    output_power = float(np.sum(I_cornea) * dx ** 2)
    row["cornea_energy_conservation_rel_error"] = abs(output_power - input_power) / input_power

    if result["junction_check_passed"]:
        row["r_EE_50_retina_um"] = result["retina_EE"]["r_EE_50"] * 1e6
        row["r_EE_80_retina_um"] = result["retina_EE"]["r_EE_80"] * 1e6
        row["r_EE_90_retina_um"] = result["retina_EE"]["r_EE_90"] * 1e6
    return row


def run_sweep(args):
    a_hole_values = [v * 1e-6 for v in resolve_a_hole_values_um(args)]
    wavelength_values = [v * 1e-9 for v in parse_float_list(args.wavelengths_nm)]
    d_gap_values = [v * 1e-3 for v in parse_float_list(args.d_gap_mm)]
    M_values = parse_float_list(args.M_diopters)

    total = len(a_hole_values) * len(wavelength_values) * len(d_gap_values) * len(M_values)
    est_seconds = total * 2.4  # ~measured per-point cost at grid_N=2048 on this machine
    print(f"Sweeping {total} configurations "
          f"({len(a_hole_values)} apertures x {len(wavelength_values)} wavelengths x "
          f"{len(d_gap_values)} gaps x {len(M_values)} myopia levels), grid_N={args.grid_N}... "
          f"(est. ~{est_seconds/60:.1f} min at grid_N=2048)")
    if total > 1000:
        print(f"NOTE: {total} configurations is large -- consider a coarser --a-hole-step-um, "
              f"fewer wavelengths/gaps/M values, or --grid-N below 2048 if this is exploratory.")

    rows = []
    n_junction_failures = 0
    t0 = time.time()
    done = 0
    for wl in wavelength_values:
        for z in d_gap_values:
            for a_hole in a_hole_values:
                for M in M_values:
                    row, result = build_row(a_hole, wl, z, M, args)
                    dx = result["cornea_result"]["dx"]
                    N = result["cornea_result"]["N"]
                    row = finalize_row(row, result, a_hole, N, dx)
                    rows.append(row)
                    if not row["junction_check_passed"]:
                        n_junction_failures += 1
                    done += 1
                    if done % 10 == 0 or done == total:
                        elapsed = time.time() - t0
                        print(f"  {done}/{total} ({elapsed:.0f}s elapsed)")

    df = pd.DataFrame(rows)
    if n_junction_failures:
        print(f"NOTE: {n_junction_failures}/{total} configurations failed the junction "
              f"validation check -- logged with junction_check_passed=False and a reason, "
              f"not dropped. See junction_fail_reason in the output CSV.")
    return df


def main():
    args = build_arg_parser().parse_args()

    if args.a_hole_start_um is None and (args.a_hole_stop_um is not None or args.a_hole_step_um is not None):
        print("ERROR: --a-hole-stop-um/--a-hole-step-um given without --a-hole-start-um. "
              "All three are required together to build a range.")
        sys.exit(1)
    if args.a_hole_start_um is not None and (args.a_hole_stop_um is None or args.a_hole_step_um is None):
        print("ERROR: --a-hole-start-um given without --a-hole-stop-um and --a-hole-step-um. "
              "All three are required together to build a range.")
        sys.exit(1)

    if not args.skip_gate:
        print("Running Airy-disk validation gate before sweeping...")
        gate = validation_gate.run_validation_gate(
            P0=args.P0, n_prime=args.n_prime, D_pupil_um=args.D_pupil_um,
            refractive_index_correction=args.refractive_index_correction,
        )
        for row in gate["rows"]:
            print(f"  {row['label']}: rel_error={row['rel_error'] * 100:.3f}% "
                  f"(tolerance {row['tolerance'] * 100:.0f}%) -> "
                  f"{'PASS' if row['passed'] else 'FAIL'}")
        if not gate["passed"]:
            print(f"VALIDATION GATE FAILED (reason: {gate['reason']}). Refusing to sweep.")
            sys.exit(1)
        print("Validation gate PASSED.\n")

    df = run_sweep(args)

    os.makedirs(OUT_DIR, exist_ok=True)
    output_path = args.output or os.path.join(OUT_DIR, f"myopia_sweep_{len(df)}pts.csv")
    df.to_csv(output_path, index=False)
    print(f"\nWrote {len(df)} rows to {output_path}")


if __name__ == "__main__":
    main()
