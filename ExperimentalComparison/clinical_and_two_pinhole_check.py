"""
ExperimentalComparison/clinical_and_two_pinhole_check.py

Two independent, narrow additions to the existing 1000b/ASM/RSS work. Reads
existing outputs and project source files READ-ONLY; writes two new files
only (report/clinical_anchor_check.txt, report/two_pinhole_experiment_targets.csv).
Does not modify or re-derive anything already in all_measurements.csv,
rss_vs_asm_comparison.csv, or the existing *.txt/*.pdf reports.

PART A -- clinical anchor check (Miller & Johnson 1977, quoted in Shen 2026):
  a 1000um pinhole reportedly tolerates ~5D of induced refractive error while
  staying >= 20/40 Snellen acuity. Checked two ways:
   (1) Qualitative shape of this project's OWN MEASURED 1000b r_EE_50_px data
       (pixels, uncalibrated -- normalized to its own M=1 value, since 1000b
       has no M=0 photo) against the shape the clinical claim implies.
   (2) A SEPARATE, calibration-free check: blur_sweep.csv's r_EE_50_um for
       a_hole_um=1000 is already an absolute physical quantity (um), not a
       camera pixel measurement -- so it CAN be compared directly to the
       20/40 MAR-derived retinal blur radius without any pixel calibration
       gap. This is an extra, clearly-labeled finding beyond what the task
       asked for the measured data, using data that was never pixel-based.

PART B -- two-pinhole separation targets: this project's own validated ghost
formula (array_geometry_lab/array_calculation/engine/ghost_formula.py,
delta_r_corrected_from_M_um = pitch_um * M / (P0 - M)) combined with its own
margin/threshold framework (array_geometry_lab/array_evaluation/
comparison_metric/gates.py) to solve for the critical hole separation
s_crit(M) at a_hole_um=1000 (this project's real physical rig aperture).

CONSTANTS -- traced, not assumed (see report text for full citation of each):
  P0 = 60.0 D                      -- new_sweeps/run_blur_sweep.py line 56,
                                       AND array_calculation/engine/
                                       ghost_formula.py's own default -- same
                                       value from two independent sources.
  n_prime = 1.336                  -- new_sweeps/run_blur_sweep.py line 56.
  f_prime_um = n_prime/P0 * 1e6    -- stage2_fixed/myopia_axial.py /
                                       phase2_retina.py convention (reduced
                                       eye, refractive_index_correction=True,
                                       matching how blur_sweep.csv itself was
                                       generated) -- NOT the naive 1/P0.
  GHOST_FORMULA_GRID_DX_UM = 1.46484375, GHOST_DELTA_R_UNCERTAINTY_UM =
  2*that, MARGIN_SAFETY_MULTIPLE = 2.0 -- array_evaluation/comparison_metric/
  gates.py lines 89-91, unchanged from that file (read, not re-derived).
  resolvable_blur_um(M, a_hole_um=1000) -- array_calculation/margins/
  ghost_margin.py's load_resolvable_blur_um() reads this directly from
  new_sweeps/blur_sweep.csv at the exact (M, a_hole_um) pair -- the SAME
  source file used throughout ExperimentalComparison's ASM comparison.

Run: python3 clinical_and_two_pinhole_check.py
"""
import os
import csv
import math

ROOT = "/Users/parikshitnarang/Pinholeproject"
EXP_DIR = os.path.join(ROOT, "ExperimentalComparison")
ALL_MEAS_CSV = os.path.join(EXP_DIR, "measurements", "all_measurements.csv")
BLUR_SWEEP_CSV = os.path.join(ROOT, "new_sweeps", "blur_sweep.csv")

OUT_TXT = os.path.join(EXP_DIR, "report", "clinical_anchor_check.txt")
OUT_CSV = os.path.join(EXP_DIR, "report", "two_pinhole_experiment_targets.csv")

# ---- constants, traced (see docstring) ----
P0 = 60.0
N_PRIME = 1.336
F_PRIME_UM = (N_PRIME / P0) * 1e6  # 22266.667 um

GHOST_FORMULA_GRID_DX_UM = 1.46484375
GHOST_DELTA_R_UNCERTAINTY_UM = 2.0 * GHOST_FORMULA_GRID_DX_UM
MARGIN_SAFETY_MULTIPLE = 2.0
THRESHOLD_ABS_UM = MARGIN_SAFETY_MULTIPLE * GHOST_DELTA_R_UNCERTAINTY_UM  # 5.859375 um

A_HOLE_1000_UM = 1000.0
M_LIST = [1, 2, 3, 4, 6, 8]


def r_20_40_um():
    mar_arcmin = 2.0
    theta_rad = math.radians(mar_arcmin / 60.0)
    return F_PRIME_UM * math.tan(theta_rad)


def load_1000b_measured_px():
    out = {}
    with open(ALL_MEAS_CSV) as f:
        for row in csv.DictReader(f):
            if row["folder"] == "1000b":
                out[int(float(row["parsed_M"]))] = float(row["measured_r_EE_50_px"])
    return out


def load_blur_sweep_1000():
    out = {}
    with open(BLUR_SWEEP_CSV) as f:
        for row in csv.DictReader(f):
            if float(row["a_hole_um"]) == A_HOLE_1000_UM:
                out[float(row["M_diopters"])] = (float(row["r_EE_50_um"]), row["junction_ok"] == "True")
    return out


def part_a():
    r2040 = r_20_40_um()
    measured_px = load_1000b_measured_px()
    ref = measured_px[1]  # normalize to M=1 -- no M=0 photo exists for 1000b
    normalized = {M: measured_px[M] / ref for M in M_LIST}

    blur1000 = load_blur_sweep_1000()

    lines = []
    lines.append("CLINICAL ANCHOR CHECK -- 1000um pinhole vs Miller & Johnson (1977),")
    lines.append("as quoted in Shen (2026)")
    lines.append("=" * 74)
    lines.append("")
    lines.append("CALIBRATION LIMITATION (stated up front, not glossed over):")
    lines.append("This project's own measured r_EE_50 for the 1000b photos is in PIXELS.")
    lines.append("No pixel-to-micrometer conversion exists yet (documented limitation of")
    lines.append("the existing ExperimentalComparison pipeline -- see comparison_summary.txt).")
    lines.append("No conversion factor is invented here. Part 1 below is therefore a")
    lines.append("QUALITATIVE SHAPE comparison only -- NOT a quantitative validation of the")
    lines.append("clinical claim against measured data.")
    lines.append("")
    lines.append("CITATION: the clinical anchor (a 1000um/1mm pinhole tolerates ~5D of")
    lines.append("induced refractive error while remaining >= 20/40 Snellen acuity) is")
    lines.append("Miller & Johnson (1977), as quoted in Shen (2026) -- an independent,")
    lines.append("non-computational reference point. It is not this project's own finding.")
    lines.append("")

    lines.append("PART 1 -- qualitative shape comparison (measured, uncalibrated pixels)")
    lines.append("-" * 74)
    lines.append("20/40 Snellen = logMAR 0.301 = MAR of 2 arcmin. At this project's own")
    lines.append(f"f_prime_um = n_prime/P0 * 1e6 = {F_PRIME_UM:.3f} um (n_prime=1.336, P0=60.0D,")
    lines.append("traced to new_sweeps/run_blur_sweep.py and stage2_fixed/myopia_axial.py's")
    lines.append(f"reduced-eye convention), the corresponding retinal blur radius is:")
    lines.append(f"  r_20/40_um = f_prime_um * tan(2 arcmin) = {r2040:.3f} um")
    lines.append("This is an absolute physical length -- it cannot be compared directly to")
    lines.append("the uncalibrated pixel measurements below; it is reported here as the")
    lines.append("reference value a future calibrated re-measurement should be checked")
    lines.append("against, and is used directly (calibration-free) in Part 2.")
    lines.append("")
    lines.append("What the clinical claim implies about SHAPE: acuity stays at/above 20/40")
    lines.append("out to M=5D, which implies the retinal blur radius stays at or below")
    lines.append(f"~{r2040:.1f}um (roughly bounded / slowly-growing, not a fast runaway climb)")
    lines.append("across M=1..5D. The 1977 study does not claim what happens beyond 5D, so")
    lines.append("no specific inflection point or growth rate past M=5D is implied here --")
    lines.append("only that growth should be SLOW/BOUNDED through M=5, not that it must")
    lines.append("break down sharply exactly at M=5D.")
    lines.append("")
    lines.append("This project's own MEASURED 1000b r_EE_50_px, normalized to M=1 (no M=0")
    lines.append("photo exists for this folder -- same convention as all_measurements.csv):")
    for M in M_LIST:
        note = "  <- normalization reference" if M == 1 else ""
        lines.append(f"  M={M}: r_EE_50_px={measured_px[M]:.1f}, normalized={normalized[M]:.4f}{note}")
    lo, hi = min(normalized.values()), max(normalized.values())
    lines.append("")
    lines.append(f"Shape observed: normalized values range {lo:.3f}-{hi:.3f} across M=1..8 --")
    lines.append("i.e. roughly FLAT/bounded (within about +/-13% of the M=1 value), NOT a")
    lines.append("clear monotonic growth curve, and with no visible inflection specifically")
    lines.append("near M=5 (M=4 is the local minimum, M=2 the local maximum, in this small,")
    lines.append("single-photo-per-M dataset).")
    lines.append("")
    lines.append("VERDICT (shape only): the measured curve staying roughly flat/bounded")
    lines.append("across the whole tested range is NOT INCONSISTENT with the clinical")
    lines.append("claim's implication of bounded acuity loss through M=5 -- both are")
    lines.append("'flat, not runaway growth.' But this is a weak agreement: the clinical")
    lines.append("claim implies flatness only through 5D with 20/40 as the specific")
    lines.append("threshold, while this measured curve is flat (by a different, unrelated")
    lines.append("criterion -- pixel-ratio variability) all the way to M=8 with no way to")
    lines.append("locate where, or whether, a real acuity threshold is crossed. This is")
    lines.append("NOT a quantitative validation of the 5D/20/40 figure -- only a")
    lines.append("shape-level observation that neither confirms nor contradicts it.")
    lines.append("")

    lines.append("PART 2 -- calibration-free check: ASM THEORY (not measured pixels) vs the")
    lines.append("clinical threshold")
    lines.append("-" * 74)
    lines.append("blur_sweep.csv's own r_EE_50_um for a_hole_um=1000 is already an absolute")
    lines.append("physical quantity (um), not a camera-pixel measurement -- so, unlike the")
    lines.append("measured photos, it CAN be compared to r_20/40_um directly, with no")
    lines.append("calibration gap. This is an extra check beyond what was asked for the")
    lines.append("measured data, using data that was never pixel-based to begin with.")
    lines.append("")
    lines.append(f"{'M':>4}  {'r_EE_50_um (ASM)':>18}  {'vs r_20/40=' + f'{r2040:.2f}um':>18}")
    for M in [0.0] + [float(m) for m in M_LIST]:
        r_um, ok = blur1000[M]
        status = "at/below (>=20/40 by this proxy)" if r_um <= r2040 else "ABOVE (<20/40 by this proxy)"
        lines.append(f"{M:>4.0f}  {r_um:>18.3f}  {status}")
    crossing_M = None
    for M in sorted(blur1000):
        r_um, _ = blur1000[M]
        if r_um > r2040:
            crossing_M = M
            break
    lines.append("")
    if crossing_M is not None:
        lines.append(f"ASM's own r_EE_50_um for this aperture crosses r_20/40_um between M="
                      f"{crossing_M-1:.0f} and M={crossing_M:.0f}D -- well BEFORE the clinical")
        lines.append("anchor's ~5D figure, IF r_EE_50 (50%-encircled-energy radius) is treated")
        lines.append("as a like-for-like stand-in for the MAR-based acuity blur radius. This is")
        lines.append("a genuine, reportable tension between this project's ASM model and the")
        lines.append("clinical literature anchor -- NOT explained or resolved here. Plausible,")
        lines.append("unverified candidate reasons (none confirmed): r_EE_50 (a fixed-fraction")
        lines.append("encircled-energy radius) and the MAR-equivalent blur-disc radius implied")
        lines.append("by a Snellen acuity test are not necessarily the same optical quantity;")
        lines.append("the clinical study's viewing/testing conditions (letter contrast,")
        lines.append("luminance, subject accommodation) differ from this project's idealized")
        lines.append("point-source model. Reported as an open discrepancy, not explained away.")
    else:
        lines.append("ASM's own r_EE_50_um for this aperture stays at/below r_20/40_um across")
        lines.append("the whole tested M range -- consistent with the clinical anchor by this")
        lines.append("proxy (with the same encircled-energy-vs-MAR caveat noted above).")

    with open(OUT_TXT, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT_TXT}")


def part_b():
    blur1000 = load_blur_sweep_1000()
    rows = []
    for M in M_LIST:
        rb_um, ok = blur1000[float(M)]
        delta_r_crit_um = rb_um - THRESHOLD_ABS_UM
        s_crit_um = delta_r_crit_um * (P0 - M) / M
        rows.append({
            "M_diopters": M,
            "a_hole_um": A_HOLE_1000_UM,
            "resolvable_blur_um": round(rb_um, 4),
            "P0": P0,
            "GHOST_DELTA_R_UNCERTAINTY_UM": GHOST_DELTA_R_UNCERTAINTY_UM,
            "MARGIN_SAFETY_MULTIPLE": MARGIN_SAFETY_MULTIPLE,
            "s_crit_predicted_um": round(s_crit_um, 2),
        })
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["M_diopters", "a_hole_um", "resolvable_blur_um", "P0",
                                          "GHOST_DELTA_R_UNCERTAINTY_UM", "MARGIN_SAFETY_MULTIPLE",
                                          "s_crit_predicted_um"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {OUT_CSV} ({len(rows)} rows)")
    return rows


if __name__ == "__main__":
    part_a()
    part_b()
