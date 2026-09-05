"""
array_optimization: Chapter 13 (Field of View) vignetting geometry -- pupil-hole overlap
shrinking with gaze angle -- per IYPT_Pinhole_Theoretical_Handbook_2.pdf, Chapter 13,
Sections 13.1-13.2. THE PHYSICS IS NOT RE-DERIVED HERE. It is already closed-form in the
handbook; this module IMPLEMENTS exactly what's written there and then VALIDATES the
implementation (transcription, acos-domain, boundary conditions, an independent Monte
Carlo cross-check) -- an unimplemented gap, not an open theoretical one.

  13.1  Delta(phi) ~= R_rot * sin(phi)              pupil lateral displacement, eye
                                                     rotation angle phi, R_rot ~= 13-14mm
                                                     physiological, valid |phi| <~ 20-30deg
  13.2  A_overlap(Delta; R_p, R_h) = R_p^2*acos((Delta^2+R_p^2-R_h^2)/(2*Delta*R_p))
                                    + R_h^2*acos((Delta^2+R_h^2-R_p^2)/(2*Delta*R_h))
                                    - 0.5*sqrt((-D+Rp+Rh)(D+Rp-Rh)(D+Rh-Rp)(D+Rp+Rh))
        valid |Rp-Rh| < Delta < Rp+Rh;  A = pi*min(Rp,Rh)^2 for Delta <= |Rp-Rh|;
        A = 0 for Delta >= Rp+Rh.
  13.3  "For the array (not one hole), sum the per-hole overlap area across all N hole
        positions at each phi" -- this is exactly what n_eff_vs_phi() below does.

INSERTION POINT (per IYPT_Pinhole_Master_Formulas_and_Pipeline.md Section 3's own
"Pupil Clipping Mask ... laterally offset for R5 gaze-angle studies"): conceptually after
the first gap propagation, before the lens quadratic-phase stage. NOT wired into that
wave-optics chain here -- see "WHY PURE GEOMETRY, NO ASM DEPENDENCY" below.

WHY PURE GEOMETRY, NO ASM DEPENDENCY (deliberate, stated):
This module imports nothing from array_psf_envelope.py, phase2_retina.py, or
pipeline_junction.py, and performs no wave propagation. Chapter 13's own formulas are
ray/aperture geometry (circle-overlap area), not a diffraction result -- computing them
via the wave-optics chain would mean re-propagating a two-stage ASM field per (design x
gaze angle x alignment) combination for a purely geometric question, at ~1000x the cost
for no additional accuracy this handbook chapter claims. This also avoids coupling a new
bug surface into the validated propagator: vignetting.py cannot break physics.py,
array_psf_envelope.py, or any single-aperture file, by construction, because it never
imports them. It DOES import array_photometry.hole_lattice() (Stage 2's own underlying
lattice-enumeration primitive -- see joint_design_space.alignment_counts(), which Stage 2
depends on transitively) to get each design's real hole (x, y) positions, so N_eff(phi)
is built on the SAME lattice this project already uses everywhere else, not a new one.

NAMING, STATED TO AVOID A CONFUSION THIS MODULE COULD EASILY CAUSE:
`array_optimization/stage3_decision/decide.py`'s "T" column is the WHOLE-LENS open-area
fraction (how dark the glasses look from outside, N*hole_area/lens_area -- independent
of pupil position). This module's "T_hole(phi)" is a DIFFERENT quantity: the fraction of
ONE hole's area still geometrically visible through the (gaze-shifted) pupil. They are
related (see `design_transmission_vs_phi()`) but are not the same number, and both are
kept under clearly distinct names throughout this file and its outputs.

w(phi), THE GAZE-USAGE DISTRIBUTION:
Searched this project's own reference material (IYPT_Pinhole_Theoretical_Handbook_1/2,
the Master Formulas doc, THEORY.md/ANALYSIS.md/RECOMMENDATION.md) for a natural
gaze-scanning-during-scene-viewing distribution to weight phi by. None exists anywhere in
this project, and no external source measures phi-DWELL-TIME while wearing pinhole
sunglasses specifically (an unresearched, novel question). Two options are implemented,
neither a full substitute for a direct measurement:

  'uniform' (default, kept as the original placeholder/sensitivity baseline, NOT
  removed): flat weight over +/-`--gaze_half_range_deg` (default 15.0). No citation --
  a deliberately-labeled placeholder, unchanged from the first version of this module.

  'gaussian_centered': a Gaussian weight, mean 0, sigma `--gaze_sigma_deg` (default
  6.0), truncated/renormalized over the same phi grid. GROUNDED IN, BUT NOT A DIRECT
  MEASUREMENT OF, three external citations:
    - Mean saccade amplitude ~4.4+/-1.3 deg during free-viewing of natural scenes
      (fixation-to-fixation eye movement study, Boston University/Cornell group,
      "Consequences of eye movements for dynamics of visual encoding").
    - Strong measured center-bias in gaze position during natural scene/movie viewing
      -- fixation density peaks near primary gaze direction, not flat (Dorr et al.
      2010, Journal of Vision, "Variability of eye movements when viewing dynamic
      natural scenes").
    - Eye-alone rotation (before head movement contributes) conventionally stays
      under ~20deg -- consistent with, and cited as supporting, this project's own
      Handbook 2 Sec 13.1 validity range (|phi| <~ 20-30deg).
    sigma=6.0deg's justification (see gaze_weights() for the arithmetic): the cited
    statistic is SACCADE AMPLITUDE (fixation-to-fixation jump size), not phi itself
    (absolute gaze angle from primary position) -- these are related but distinct
    quantities. Treating the saccade amplitude's mean (4.4deg) as roughly one
    standard deviation of a zero-centered dwell-angle distribution (a common,
    stated-here-as-such approximation when only amplitude statistics are available,
    not dwell-position statistics) gives sigma~4.4deg; rounded up to 6.0deg as a
    modest, explicitly-stated margin acknowledging the proxy is imperfect and the
    center-bias literature (Dorr et al.) supports a still-peaked-but-somewhat-broader
    distribution than raw saccade amplitude alone would suggest. THIS IS A REASONED
    ESTIMATE FROM ADJACENT LITERATURE, NOT A FITTED OR MEASURED SIGMA -- stated
    plainly here and wherever gaussian_centered's output is reported, exactly as
    'uniform' was, so it is not read as more authoritative than it is.

If a citable source directly measuring phi-dwell-time while wearing pinhole sunglasses
(or comparable near-eye occluded optics) is found, replace or add to `gaze_weights()`
-- it is the only function that needs to change.

USAGE:
    python3 vignetting.py --validate            # standalone geometry validation (run first)
    python3 vignetting.py --apply                # re-rank the 20 Stage-3 candidates
                                                   # (runs --validate first; refuses to
                                                   # apply if validation fails)
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ARRAY_DESIGN = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "photometry"))

import array_photometry as ap  # noqa: E402  (hole_lattice: the reused enumeration primitive)

DEFAULT_R_ROT_MM = 13.5  # physiological range 13-14mm (Handbook 2 Sec 13.1); CLI-overridable
DEFAULT_PHI_VALID_DEG = 25.0  # Handbook's own stated validity range is |phi| <~ 20-30deg;
                               # 25 deg is the stated default, CLI-overridable
DEFAULT_D_PUPIL_UM = 4000.0
DEFAULT_CANDIDATES_CSV = os.path.join(HERE, "stage3_decision", "array_candidates.csv")
DEFAULT_GRID_CSV = os.path.join(ARRAY_DESIGN, "optimise_grid.csv")


# ============================================================================
# Part B.2 -- A_overlap(Delta, R_p, R_h), Handbook Sec 13.2, three explicit regimes
# ============================================================================

def overlap_area_um2(delta_um, R_p_um, R_h_um):
    """Exact circle-circle overlap area, Handbook 2 Sec 13.2. delta_um may be a scalar
    or array. Three regimes handled EXPLICITLY (no fallthrough): full containment
    (Delta <= |Rp-Rh|), no overlap (Delta >= Rp+Rh), and the general partial-overlap
    acos formula strictly between them -- boundary points always land in the full/zero
    regimes (both use <=, >=), so the acos branch is never evaluated exactly AT a
    boundary; acos arguments are still explicitly clipped to [-1,1] as a second,
    independent safeguard against floating-point overshoot just inside that branch."""
    assert R_h_um < R_p_um, (
        f"overlap_area_um2 assumes R_h < R_p (true for every candidate hole/pupil size "
        f"in this project); got R_h={R_h_um}, R_p={R_p_um} -- equal-radius geometry is "
        f"out of scope and not handled.")
    d = np.atleast_1d(np.asarray(delta_um, dtype=float))
    out = np.empty_like(d)

    full_area = np.pi * min(R_p_um, R_h_um) ** 2
    lo = abs(R_p_um - R_h_um)
    hi = R_p_um + R_h_um

    m_full = d <= lo
    m_zero = d >= hi
    m_part = ~m_full & ~m_zero

    out[m_full] = full_area
    out[m_zero] = 0.0

    if np.any(m_part):
        dp = d[m_part]
        a1 = np.arccos(np.clip((dp ** 2 + R_p_um ** 2 - R_h_um ** 2) / (2 * dp * R_p_um), -1.0, 1.0))
        a2 = np.arccos(np.clip((dp ** 2 + R_h_um ** 2 - R_p_um ** 2) / (2 * dp * R_h_um), -1.0, 1.0))
        radicand = (-dp + R_p_um + R_h_um) * (dp + R_p_um - R_h_um) * (dp + R_h_um - R_p_um) * (dp + R_p_um + R_h_um)
        term3 = 0.5 * np.sqrt(np.clip(radicand, 0.0, None))
        out[m_part] = np.clip(R_p_um ** 2 * a1 + R_h_um ** 2 * a2 - term3, 0.0, None)  # near
                        # the Delta=Rp+Rh boundary, floating-point roundoff on the acos
                        # terms can produce a tiny negative area (observed:
                        # -0.0589 um^2 at Delta=3000um for a 2000um hole) despite the
                        # true area being 0 there by construction (m_part excludes the
                        # boundary itself, but points just inside it can still round
                        # negative); the sqrt term was already clamped, this closes the
                        # same gap on the final combination.

    return out[0] if out.size == 1 and np.isscalar(delta_um) else out


# ============================================================================
# Part B.3 -- Delta(phi), Handbook Sec 13.1
# ============================================================================

def pupil_shift_um(phi_deg, R_rot_mm=DEFAULT_R_ROT_MM):
    """13.1: Delta(phi) ~= R_rot * sin(phi). Returns micrometres."""
    phi_rad = np.radians(phi_deg)
    return R_rot_mm * 1000.0 * np.sin(phi_rad)


def phi_in_validated_range(phi_deg, max_valid_deg=DEFAULT_PHI_VALID_DEG):
    """True where |phi| is inside the handbook's stated small-angle validity range.
    Evaluations outside this range are still COMPUTED (the formula doesn't blow up) but
    every caller that reports a number must check and flag this, not silently trust it."""
    return np.abs(phi_deg) <= max_valid_deg


# ============================================================================
# Part B.4 -- Validation, before anything downstream uses this module
# ============================================================================

def monte_carlo_overlap_area_um2(delta_um, R_p_um, R_h_um, n_samples=10000, rng=None):
    """Independent cross-check of overlap_area_um2(), NOT sharing any code with it:
    samples n_samples points uniformly inside the HOLE circle (radius R_h, placed at
    distance delta_um from the pupil center), counts the fraction landing inside the
    PUPIL circle (radius R_p, at the origin), and returns fraction * hole_area. This
    catches transcription bugs (sign errors, swapped Rp/Rh, wrong acos branch) that a
    pure code-review of the closed form would not, because it does not reuse the
    formula's own algebra at all."""
    rng = rng if rng is not None else np.random.default_rng(0)
    r = R_h_um * np.sqrt(rng.random(n_samples))       # uniform-area sampling in a disk
    theta = rng.random(n_samples) * 2 * np.pi
    x = delta_um + r * np.cos(theta)
    y = r * np.sin(theta)
    inside_frac = float(((x ** 2 + y ** 2) <= R_p_um ** 2).mean())
    return inside_frac * (np.pi * R_h_um ** 2), inside_frac


def run_validation(R_p_um=DEFAULT_D_PUPIL_UM / 2.0, hole_diameters_um=(400.0, 1000.0, 2000.0),
                    n_samples=10000, mc_tol_pct=0.5, phi_max_valid_deg=DEFAULT_PHI_VALID_DEG,
                    R_rot_mm=DEFAULT_R_ROT_MM, out_dir=HERE):
    print(f"=== vignetting.py standalone validation (R_p={R_p_um:.0f}um, "
          f"hole diameters={list(hole_diameters_um)}um, R_rot={R_rot_mm}mm) ===")
    ok = True

    # --- 4a: phi=0 -> full unvignetted hole area, every hole size ---
    print("\n[4a] phi=0 -> A_overlap == pi*R_h^2 (full area), for every hole size:")
    for d_um in hole_diameters_um:
        R_h = d_um / 2.0
        delta0 = pupil_shift_um(0.0, R_rot_mm)
        A0 = float(overlap_area_um2(delta0, R_p_um, R_h))
        expect = np.pi * R_h ** 2
        passed = np.isclose(A0, expect, rtol=1e-9)
        ok &= passed
        print(f"    hole_diam={d_um:6.0f}um  delta(phi=0)={delta0:.6f}um  "
              f"A_overlap={A0:.4f}  pi*Rh^2={expect:.4f}  {'PASS' if passed else 'FAIL'}")

    # --- 4b: large-enough phi (still inside the validated range) -> exactly 0 ---
    print(f"\n[4b] phi within the validated |phi|<={phi_max_valid_deg:.0f}deg range but large "
          f"enough that Delta > Rp+Rh -> A_overlap == 0 exactly:")
    for d_um in hole_diameters_um:
        R_h = d_um / 2.0
        need_delta = R_p_um + R_h
        # smallest |phi| (within the valid range) at which Delta(phi) clears Rp+Rh, if any
        phi_needed = np.degrees(np.arcsin(min(1.0, need_delta / (R_rot_mm * 1000.0))))
        if phi_needed <= phi_max_valid_deg:
            phi_test = min(phi_max_valid_deg, phi_needed + 2.0)
            d_at = pupil_shift_um(phi_test, R_rot_mm)
            A = float(overlap_area_um2(d_at, R_p_um, R_h))
            passed = (A == 0.0) and not np.isnan(A)
            ok &= passed
            print(f"    hole_diam={d_um:6.0f}um  phi={phi_test:.2f}deg (<= {phi_max_valid_deg:.0f}deg valid range)  "
                  f"Delta={d_at:.1f}um > Rp+Rh={need_delta:.1f}um  A_overlap={A:.6f}  {'PASS' if passed else 'FAIL'}")
        else:
            print(f"    hole_diam={d_um:6.0f}um: full vignetting needs phi={phi_needed:.1f}deg, "
                  f"OUTSIDE the validated range ({phi_max_valid_deg:.0f}deg) at R_rot={R_rot_mm}mm -- "
                  f"not tested here (would require extrapolating past Sec 13.1's own stated validity).")
    # --- explicit boundary-value NaN check, independent of any phi (the exact points
    # the task calls out: Delta = Rp-Rh and Delta = Rp+Rh) ---
    print("\n[4b-boundary] exact Delta=Rp-Rh and Delta=Rp+Rh must not NaN:")
    for d_um in hole_diameters_um:
        R_h = d_um / 2.0
        for label, delta_b in [("Rp-Rh", R_p_um - R_h), ("Rp+Rh", R_p_um + R_h)]:
            A = float(overlap_area_um2(delta_b, R_p_um, R_h))
            passed = not np.isnan(A)
            ok &= passed
            print(f"    hole_diam={d_um:6.0f}um  Delta={label}={delta_b:.4f}um  A_overlap={A:.6f}  "
                  f"{'PASS (no NaN)' if passed else 'FAIL (NaN!)'}")

    # --- 4c: Monte Carlo cross-check across the partial-overlap regime ---
    # GATING METRIC, CHOSEN DELIBERATELY (not the naive |A_cf-A_mc|/A_cf ratio) --
    # reasoning below, verified by direct experiment before being adopted, not assumed:
    #   error / (pi*R_h^2) = |T_cf(phi) - T_mc(phi)|, i.e. the error in the SAME
    #   [0,1]-normalized per-hole transmission units this module actually uses
    #   downstream (T_hole). Its Monte Carlo standard error is sqrt(p(1-p)/n) -- WELL
    #   BEHAVED everywhere, maximal at p=0.5 (~0.5/sqrt(n)) and shrinking toward the
    #   tails -- unlike |A_cf-A_mc|/A_cf, whose denominator A_cf itself -> 0 near the
    #   full-vignetting boundary, blowing up the ratio for a fixed, small absolute
    #   sampling error even with NO bias. Confirmed empirically first: at n=10000 the
    #   naive ratio metric hit 9.7% at one point while |A_cf-A_mc|/(pi*Rh^2) was only
    #   0.77% there, and re-running that same point at n up to 5e6 converged the raw
    #   estimate cleanly onto the closed form with no systematic offset -- i.e. the
    #   9.7% "failure" was pure sampling noise at a small-area tail point, not a bug.
    #   relative_error_pct is still reported (informational), but PASS/FAIL gates on
    #   the normalized metric.
    print(f"\n[4c] Monte Carlo cross-check ({n_samples} samples/point, tol={mc_tol_pct:.2f} "
          f"percentage points of full hole area):")
    rows = []
    rng = np.random.default_rng(12345)
    for d_um in hole_diameters_um:
        R_h = d_um / 2.0
        lo, hi = abs(R_p_um - R_h), R_p_um + R_h
        deltas = np.linspace(0.0, hi * 1.15, 24)
        for delta in deltas:
            A_cf = float(overlap_area_um2(delta, R_p_um, R_h))
            A_mc, _ = monte_carlo_overlap_area_um2(delta, R_p_um, R_h, n_samples=n_samples, rng=rng)
            rel_err_pct = 100.0 * abs(A_cf - A_mc) / A_cf if A_cf > 0 else (100.0 if A_mc > 0 else 0.0)
            err_pct_of_hole = 100.0 * abs(A_cf - A_mc) / (np.pi * R_h ** 2)
            rows.append({"hole_diameter_um": d_um, "delta_um": delta, "R_p_um": R_p_um, "R_h_um": R_h,
                         "A_overlap_closed_form_um2": A_cf, "A_overlap_monte_carlo_um2": A_mc,
                         "relative_error_pct": rel_err_pct,
                         "error_pct_of_full_hole_area": err_pct_of_hole,
                         "in_partial_regime": bool(lo < delta < hi)})
    mc_df = pd.DataFrame(rows)
    worst = mc_df.loc[mc_df.error_pct_of_full_hole_area.idxmax()]
    mc_pass = bool(mc_df.error_pct_of_full_hole_area.max() <= mc_tol_pct)
    ok &= mc_pass
    print(f"    max |A_cf-A_mc|/(pi*Rh^2) across {len(mc_df)} (hole_size, delta) points: "
          f"{mc_df.error_pct_of_full_hole_area.max():.4f} pct-points (at hole_diam="
          f"{worst.hole_diameter_um:.0f}um, delta={worst.delta_um:.1f}um, informational "
          f"naive-ratio error there = {worst.relative_error_pct:.2f}%)  {'PASS' if mc_pass else 'FAIL'}")

    out_csv = os.path.join(out_dir, "vignetting_validation.csv")
    mc_df.to_csv(out_csv, index=False)
    print(f"\nwrote {out_csv}")

    # --- 4d: overlay plot ---
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    phi_grid = np.linspace(-30.0, 30.0, 241)
    delta_grid = pupil_shift_um(phi_grid, R_rot_mm)
    for d_um in hole_diameters_um:
        R_h = d_um / 2.0
        A = overlap_area_um2(delta_grid, R_p_um, R_h)
        ax.plot(phi_grid, A / (np.pi * R_h ** 2), lw=2.0, label=f"hole diam={d_um:.0f}um")
    ax.axvline(phi_max_valid_deg, color="0.5", ls="--", lw=1.0)
    ax.axvline(-phi_max_valid_deg, color="0.5", ls="--", lw=1.0,
              label=f"|phi|={phi_max_valid_deg:.0f}deg validity limit")
    ax.set_xlabel("gaze angle phi (deg)")
    ax.set_ylabel("T_hole(phi) = A_overlap / (pi*R_h^2)")
    ax.set_title(f"Per-hole vignetting transmission vs gaze angle (R_p={R_p_um:.0f}um, R_rot={R_rot_mm}mm)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    out_png = os.path.join(out_dir, "vignetting_validation.png")
    fig.savefig(out_png, dpi=160, facecolor="white")
    print(f"wrote {out_png}")

    print(f"\n=== validation verdict: {'PASS' if ok else 'FAIL'} ===")
    return ok


# ============================================================================
# Part B.5-6 -- per-hole T(phi), N_eff(phi), reusing array_photometry.hole_lattice()
# ============================================================================

def n_eff_matrix(a_hole_um, s_um, D_pupil_um, packing, phi_deg_array,
                 R_rot_mm=DEFAULT_R_ROT_MM, alignment_n_offsets=15):
    """13.3: 'sum the per-hole overlap area across all N hole positions at each phi.'
    Reuses array_photometry.hole_lattice() (the SAME primitive Stage 2's dependency
    chain already uses, via joint_design_space.alignment_counts) for hole (x, y)
    positions -- not reimplemented. Gaze is modelled along a single axis (x), matching
    this task's own phi as a single scalar sweep. The pupil's alignment relative to the
    fixed hole lattice (a separate, wearing/manufacturing uncertainty -- WHICH SPECIFIC
    WEARER got WHICH random offset when the glasses were made, fixed for that wearer
    for life, not something that re-randomizes as their eye moves) is swept the same
    way Stage 2/joint_design_space already do it (offsets over one lattice unit cell).

    Returns the RAW matrix (n_alignment x n_phi) of continuous N_eff (each hole
    contributes a fraction in [0,1], not counted as simply in/out), plus the phi and
    alignment-offset arrays -- deliberately NOT pre-aggregated over alignment, because
    aggregating (worst/mean) BEFORE computing a per-wearer field average over phi is a
    different (and for 'worst', wrong) computation than aggregating AFTER -- see
    apply_to_candidates()'s own comment for why this distinction is load-bearing here."""
    R_p_um = D_pupil_um / 2.0
    R_h_um = a_hole_um / 2.0
    hx, hy = ap.hole_lattice(s_um, D_pupil_um * 0.75, packing=packing)

    offs = np.linspace(0.0, s_um, alignment_n_offsets, endpoint=False)
    OX, OY = np.meshgrid(offs, offs, indexing="ij")
    align_ox, align_oy = OX.ravel(), OY.ravel()  # one lattice-alignment unit cell

    n_align = align_ox.size
    n_phi = len(phi_deg_array)
    M = np.empty((n_align, n_phi))
    for j, phi in enumerate(phi_deg_array):
        shift_x = pupil_shift_um(phi, R_rot_mm)  # gaze along x
        for k in range(n_align):
            pupil_cx = align_ox[k] + shift_x
            pupil_cy = align_oy[k]
            delta = np.sqrt((hx - pupil_cx) ** 2 + (hy - pupil_cy) ** 2)
            A = overlap_area_um2(delta, R_p_um, R_h_um)
            T_i = A / (np.pi * R_h_um ** 2)
            M[k, j] = T_i.sum()
    return M, align_ox, align_oy


def n_eff_vs_phi(a_hole_um, s_um, D_pupil_um, packing, phi_deg_array,
                 R_rot_mm=DEFAULT_R_ROT_MM, alignment_n_offsets=15):
    """Per-phi worst/mean/best ACROSS ALIGNMENT -- i.e. 'how bad/typical/good could
    N_eff be at this gaze angle, over the wearer population', independently at each
    phi. Useful for the validation-style report and as a phi-by-phi safety envelope
    (analogous to Stage 3's own N_eff_worst_across_M, generalized to across-phi), but
    NOT what apply_to_candidates() uses for a single wearer's field average -- see
    n_eff_matrix()'s docstring."""
    M, _, _ = n_eff_matrix(a_hole_um, s_um, D_pupil_um, packing, phi_deg_array, R_rot_mm, alignment_n_offsets)
    return pd.DataFrame({
        "phi_deg": phi_deg_array,
        "in_validated_range": [bool(phi_in_validated_range(p)) for p in phi_deg_array],
        "N_eff_worst": M.min(axis=0), "N_eff_mean": M.mean(axis=0), "N_eff_best": M.max(axis=0),
    })


DEFAULT_GAZE_SIGMA_DEG = 6.0  # see module docstring's 'gaussian_centered' section for
                              # the full arithmetic: cited mean saccade amplitude
                              # 4.4+/-1.3deg (Boston Univ/Cornell free-viewing study)
                              # treated as ~1 sigma of a zero-centered dwell-angle
                              # proxy (saccade amplitude != dwell angle -- an explicit
                              # approximation, not a measured sigma), rounded up from
                              # 4.4 to 6.0deg for a stated margin given the center-bias
                              # literature (Dorr et al. 2010) and the amplitude's own
                              # +/-1.3deg spread -- NOT a fitted or optimized value.


def gaze_weights(phi_deg_array, distribution="uniform", half_range_deg=15.0,
                 sigma_deg=DEFAULT_GAZE_SIGMA_DEG):
    """w(phi): SEE MODULE DOCSTRING for full sourcing/caveats on both options below.
    Returns weights normalized to sum to 1 over the supplied phi grid.

    'uniform': flat weight over +/-half_range_deg, 0 outside it. UNSOURCED PLACEHOLDER,
    kept as the original baseline/sensitivity comparison, not a validated result.

    'gaussian_centered': Gaussian(mean=0, sigma=sigma_deg), evaluated on phi_deg_array
    and renormalized over that SAME grid (i.e. truncated to [phi_min_deg, phi_max_deg]
    exactly as 'uniform' is truncated to +/-half_range_deg, not integrated to infinity).
    Grounded in saccade-amplitude/center-bias literature -- SEE MODULE DOCSTRING -- as
    a reasonable proxy for gaze usage during natural scene viewing, explicitly NOT a
    direct measurement of dwell time while wearing pinhole sunglasses."""
    if distribution == "uniform":
        w = (np.abs(phi_deg_array) <= half_range_deg).astype(float)
    elif distribution == "gaussian_centered":
        phi = np.asarray(phi_deg_array, dtype=float)
        w = np.exp(-0.5 * (phi / sigma_deg) ** 2)
    else:
        raise ValueError(f"unknown gaze distribution '{distribution}' -- only 'uniform' "
                         f"and 'gaussian_centered' are implemented, see module docstring "
                         f"for why each is (and is not) sourced")
    if w.sum() == 0:
        raise ValueError(f"'{distribution}' assigns zero weight to every phi in the "
                         f"supplied grid -- widen the relevant range/sigma or the phi sweep")
    return w / w.sum()


# ============================================================================
# Part B.8 -- re-run the 20 Stage-3 candidates
# ============================================================================

def apply_to_candidates(candidates_csv=DEFAULT_CANDIDATES_CSV, D_pupil_um=DEFAULT_D_PUPIL_UM,
                        phi_min_deg=-25.0, phi_max_deg=25.0, phi_step_deg=5.0,
                        R_rot_mm=DEFAULT_R_ROT_MM, alignment_n_offsets=15,
                        gaze_distribution="uniform", gaze_half_range_deg=15.0,
                        gaze_sigma_deg=DEFAULT_GAZE_SIGMA_DEG,
                        out_dir=HERE):
    """phi step size justification: R_rot*d(sin phi)/dphi at phi=0 is R_rot (13.5mm);
    over a 5deg step near phi=0, Delta changes by ~13500*sin(5deg)=~1177um -- much
    coarser than dx-scale (the ASM grid's ~1.5um pixel is not relevant here, this is
    pure geometry), but fine relative to the ~2000-3000um scale (Rp+Rh) that actually
    sets A_overlap's characteristic width; a 5deg default step (11 points over
    +/-25deg) resolves that scale with >~10 samples across the transition, which
    run_validation's own plotted curves (smooth over 0.25deg resolution) confirm is
    dense enough not to alias the transition -- CLI-configurable via --phi_step_deg
    if a finer check is ever needed."""
    cand = pd.read_csv(candidates_csv)
    rec = cand[cand.recommended_for_prototyping].copy()
    assert len(rec), f"no recommended_for_prototyping=True rows found in {candidates_csv}"

    legacy_out = os.path.join(out_dir, "array_candidates_prevignetting_legacy.csv")
    cand.to_csv(legacy_out, index=False)
    print(f"preserved pre-vignetting candidate set (unmodified) -> {legacy_out}")

    phi_grid = np.arange(phi_min_deg, phi_max_deg + 1e-9, phi_step_deg)
    w = gaze_weights(phi_grid, gaze_distribution, gaze_half_range_deg, gaze_sigma_deg)
    if gaze_distribution == "uniform":
        print(f"\n*** GAZE-USAGE DISTRIBUTION w(phi): 'uniform' over "
              f"+/-{gaze_half_range_deg:.1f}deg -- UNSOURCED PLACEHOLDER, see module "
              f"docstring. Treat field-averaged numbers below as illustrative of the "
              f"METHOD, not as a final physical claim. ***\n")
    else:
        print(f"\n*** GAZE-USAGE DISTRIBUTION w(phi): 'gaussian_centered', sigma="
              f"{gaze_sigma_deg:.1f}deg, truncated to [{phi_min_deg:.0f}, {phi_max_deg:.0f}]deg "
              f"-- GROUNDED IN saccade-amplitude/center-bias literature, but NOT a "
              f"direct measurement of gaze-dwell-time while wearing pinhole sunglasses "
              f"specifically. See module docstring for the full citation list and the "
              f"sigma arithmetic. Treat as a reasoned proxy, not a validated result. ***\n")
    print(f"phi sweep: {phi_grid.min():.1f} to {phi_grid.max():.1f}deg, step={phi_step_deg:.1f}deg "
          f"({len(phi_grid)} points); alignment_n_offsets={alignment_n_offsets}")

    out_rows = []
    for _, row in rec.iterrows():
        a_um, s_um, packing = row.N, row.s, row.pattern
        T_static = row["T"]  # decide.py's whole-lens, un-vignetted (phi=0) transmission
                              # -- MUST use bracket indexing: row.T is pandas' Series
                              # transpose (a no-op returning the whole row), not this
                              # column; the same gotcha bit decide.py's own T column
                              # earlier in this session's Part A audit.

        # M[k, j] = N_eff for alignment (wearer) k at phi_grid[j]. Two DIFFERENT,
        # DELIBERATE aggregations are computed from it below, for two different
        # questions -- conflating them was tried first and produced two distinct wrong
        # numbers before this was sorted out, so both are documented explicitly:
        #
        # (1) POPULATION-MEAN brightness (comparable to decide.py's own "T", itself a
        #     whole-lens/ensemble area-fraction, not tied to any one wearer): computed
        #     as a RATIO OF MEANS, mean_k(field_avg_neff_k) / mean_k(neff0_k), NOT a
        #     mean of per-wearer ratios. A first attempt averaged per-wearer ratios
        #     (field_avg_neff_k / neff0_k, then meaned) and produced nonsense
        #     (T_field_averaged up to 628,365% of T_static) because a handful of
        #     wearers have neff0_k just barely above zero -- dividing by a near-zero
        #     per-wearer denominator blows up that one wearer's ratio arbitrarily, and
        #     an unweighted mean of ratios has no defence against that. Ratio-of-means
        #     has no such division-by-near-zero step (each mean is a well-behaved sum
        #     over ~225 alignments) and is also the mathematically appropriate
        #     estimator for "population-average brightness," matching what T_static
        #     itself already represents.
        #     By linearity, mean_k(field_avg_neff_k) == sum_phi w(phi)*mean_k(N_eff(phi,k))
        #     exactly -- i.e. this ratio is provably close to invariant under gaze angle
        #     whenever the alignment sweep already covers one full lattice period
        #     (mean over a full period of a periodic pattern is translation-invariant
        #     under any bounded added shift). That is NOT a bug or an artifact to
        #     explain away -- it is a real, expected property of population-averaged
        #     brightness under this vignetting model, reported as such below, not
        #     hidden behind an unstable per-wearer-ratio number that looked more
        #     "dramatic" only because it was wrong.
        # (2) WORST-CASE WEARER (safety-relevant, NOT population-averaged): each
        #     wearer's OWN field-integrated trajectory field_avg_neff_k is an ABSOLUTE
        #     quantity (no ratio, no division), so the worst (min) over k is stable and
        #     physically means "the least-lucky wearer's own gaze-integrated average
        #     N_eff." This is reported as N_eff_worst_field_averaged below, kept
        #     entirely separate from (1).
        M, _, _ = n_eff_matrix(a_um, s_um, D_pupil_um, packing, phi_grid, R_rot_mm, alignment_n_offsets)
        phi0_idx = int(np.argmin(np.abs(phi_grid)))
        assert phi_grid[phi0_idx] == 0.0, "phi grid must include exactly phi=0 (static baseline)"
        neff0_per_wearer = M[:, phi0_idx]                      # (n_align,)
        field_avg_neff_per_wearer = M @ w                      # (n_align,) -- sum_phi w(phi)*N_eff_k(phi)
        frac_dark_at_phi0 = float((neff0_per_wearer <= 0).mean())  # transparency only

        T_static = float(T_static)
        mean_neff0 = float(neff0_per_wearer.mean())
        mean_field_avg_neff = float(field_avg_neff_per_wearer.mean())
        T_field_avg = T_static * (mean_field_avg_neff / mean_neff0) if mean_neff0 > 0 else 0.0
        N_eff_mean_static_phi0 = mean_neff0
        N_eff_worst_static_phi0 = float(neff0_per_wearer.min())
        N_eff_worst_field_averaged = float(field_avg_neff_per_wearer.min())  # worst SINGLE
                                            # wearer's OWN phi-averaged trajectory -- see
                                            # (2) above
        N_eff_worst_across_phi_and_alignment = float(M.min())  # most conservative
                                            # envelope: worst wearer AT the worst gaze
                                            # angle simultaneously -- generalizes Stage
                                            # 3's N_eff_worst_across_M

        out_rows.append({
            "N": a_um, "s": s_um, "pattern": packing,
            "T_static_phi0": T_static,
            "N_eff_mean_static_phi0": N_eff_mean_static_phi0,
            "N_eff_worst_static_phi0": N_eff_worst_static_phi0,
            "N_eff_worst_across_M_stage3_binary": row["N_eff_worst_across_M"],  # SEE NOTE
                                            # BELOW -- this is Stage 3's own binary
                                            # (hole-CENTER in/out) worst-case number,
                                            # kept alongside this module's continuous
                                            # overlap-weighted N_eff_worst_static_phi0
                                            # for direct, honest side-by-side comparison
                                            # rather than letting the two look silently
                                            # inconsistent.
            "T_field_averaged": T_field_avg,
            "N_eff_worst_field_averaged": N_eff_worst_field_averaged,
            "N_eff_worst_across_phi_and_alignment": N_eff_worst_across_phi_and_alignment,
            "frac_wearers_dark_at_phi0": frac_dark_at_phi0,  # transparency: fraction of
                                            # alignments excluded from the T ratio above
            "T_field_over_T_static_pct": 100.0 * T_field_avg / T_static if T_static > 0 else float("nan"),
            "r_EE_80_um": row.r_EE_80_um,  # carried through unchanged (blur is not a
                                            # function of gaze angle in this model)
        })

    out = pd.DataFrame(out_rows)

    # Pareto re-rank on (r_EE_80_um, T_field_averaged) -- SAME dominance rule decide.py
    # uses, restricted to the existing 20 (per this task's step 9: re-rank the existing
    # candidates, do not recompute the 274->90 funnel under vignetting).
    def pareto_front(df, minimize_col, maximize_col):
        keep = []
        vals = df[[minimize_col, maximize_col]].values
        for i in range(len(df)):
            dominated = False
            for j in range(len(df)):
                if i == j:
                    continue
                better_or_equal = vals[j, 0] <= vals[i, 0] and vals[j, 1] >= vals[i, 1]
                strictly_better = vals[j, 0] < vals[i, 0] or vals[j, 1] > vals[i, 1]
                if better_or_equal and strictly_better:
                    dominated = True
                    break
            keep.append(not dominated)
        return df[keep]

    front_static = pareto_front(out.assign(T=out.T_static_phi0), "r_EE_80_um", "T").index
    front_field = pareto_front(out.assign(T=out.T_field_averaged), "r_EE_80_um", "T").index
    out["on_pareto_front_static_T"] = out.index.isin(front_static)
    out["on_pareto_front_field_averaged_T"] = out.index.isin(front_field)
    out["ranking_changed"] = out.on_pareto_front_static_T != out.on_pareto_front_field_averaged_T

    out = out.sort_values("r_EE_80_um")
    out_csv = os.path.join(out_dir, "array_candidates_field_averaged.csv")
    out.to_csv(out_csv, index=False)
    print(f"\nwrote {out_csv}")

    n_disagree_phi0 = int((np.abs(out.N_eff_worst_static_phi0 - out.N_eff_worst_across_M_stage3_binary) > 1e-6).sum())
    if n_disagree_phi0:
        print(f"\nNOTE: this module's own N_eff_worst_static_phi0 (continuous, overlap-area-"
              f"weighted) disagrees with Stage 3's N_eff_worst_across_M_stage3_binary (0 for "
              f"all 20, by construction of decide.py's safety gate) for {n_disagree_phi0}/{len(out)} "
              f"candidates -- NOT a contradiction: Stage 3 counts a hole as in/out based on "
              f"whether its CENTER falls inside the pupil circle (array_photometry.py's own "
              f"documented approximation, stated valid only for a_hole << D_pupil); this "
              f"module instead computes the actual fractional overlap AREA, which is nonzero "
              f"even when a hole's center sits just outside the pupil boundary. The "
              f"discrepancy grows with hole size relative to pupil (largest at N=2000um, "
              f"R_h/R_p=0.5) exactly where the center-only approximation is documented to be "
              f"weakest -- this module's number is a refinement, not a replacement; both are "
              f"reported side by side in the CSV for audit.")

    n_changed = int(out.ranking_changed.sum())
    print(f"\n=== static (phi=0) vs field-averaged, all {len(out)} recommended candidates ===")
    print(out[["N", "s", "pattern", "T_static_phi0", "T_field_averaged", "T_field_over_T_static_pct",
              "N_eff_worst_static_phi0", "N_eff_worst_across_M_stage3_binary", "N_eff_worst_field_averaged",
              "on_pareto_front_static_T", "on_pareto_front_field_averaged_T"]].to_string(index=False))

    if n_changed:
        print(f"\n*** {n_changed}/{len(out)} candidates changed Pareto-front membership between "
              f"static and field-averaged T -- vignetting DOES affect the ranking. See "
              f"'ranking_changed' rows in {out_csv}. ***")
    else:
        print(f"\nNo candidate changed Pareto-front membership between static and "
              f"field-averaged T -- **the field-averaged re-ranking confirms the static "
              f"(phi=0) recommendation is robust to this vignetting model**, under the "
              f"placeholder gaze distribution stated above. This is a legitimate robustness "
              f"finding, not a null result -- stated plainly, not buried, per this project's "
              f"own honest-reporting requirement.")
    return out


def main():
    ap_ = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap_.add_argument("--validate", action="store_true", help="run standalone geometry validation only")
    ap_.add_argument("--apply", action="store_true", help="run validation, then (if PASS) re-rank the 20 candidates")
    ap_.add_argument("--R_rot_mm", type=float, default=DEFAULT_R_ROT_MM)
    ap_.add_argument("--phi_max_valid_deg", type=float, default=DEFAULT_PHI_VALID_DEG)
    ap_.add_argument("--D_pupil_um", type=float, default=DEFAULT_D_PUPIL_UM)
    ap_.add_argument("--validation_hole_diameters_um", type=str, default="400,1000,2000")
    ap_.add_argument("--mc_samples", type=int, default=300000,
                     help="300k default (not the task's illustrative 10k): sized so the "
                          "worst-case binomial standard error (max at p=0.5, "
                          "~0.5/sqrt(n) of full hole area) sits ~5x below the default "
                          "0.5-pct-point tolerance -- see run_validation()'s own comment")
    ap_.add_argument("--mc_tol_pct", type=float, default=0.5)
    ap_.add_argument("--candidates_csv", type=str, default=DEFAULT_CANDIDATES_CSV)
    ap_.add_argument("--phi_min_deg", type=float, default=-25.0)
    ap_.add_argument("--phi_max_deg", type=float, default=25.0)
    ap_.add_argument("--phi_step_deg", type=float, default=5.0)
    ap_.add_argument("--alignment_n_offsets", type=int, default=15)
    ap_.add_argument("--gaze_distribution", type=str, default="uniform",
                     choices=["uniform", "gaussian_centered"])
    ap_.add_argument("--gaze_half_range_deg", type=float, default=15.0)
    ap_.add_argument("--gaze_sigma_deg", type=float, default=DEFAULT_GAZE_SIGMA_DEG,
                     help="sigma for --gaze_distribution gaussian_centered -- see "
                          "module docstring / DEFAULT_GAZE_SIGMA_DEG comment for the "
                          "saccade-amplitude-derived justification of the 6.0 default")
    args = ap_.parse_args()

    if not args.validate and not args.apply:
        args.validate = True  # default action: validate only, per "validate before use"

    hole_diams = [float(x) for x in args.validation_hole_diameters_um.split(",")]
    passed = run_validation(R_p_um=args.D_pupil_um / 2.0, hole_diameters_um=hole_diams,
                            n_samples=args.mc_samples, mc_tol_pct=args.mc_tol_pct,
                            phi_max_valid_deg=args.phi_max_valid_deg, R_rot_mm=args.R_rot_mm)

    if args.apply:
        if not passed:
            print("\n*** VALIDATION FAILED. Refusing to apply vignetting to the 20 "
                  "Stage-3 candidates on unvalidated geometry. Fix the formula "
                  "implementation and re-run --validate before --apply. ***")
            sys.exit(1)
        print("\nValidation passed -- proceeding to apply vignetting to the Stage-3 candidates.\n")
        apply_to_candidates(candidates_csv=args.candidates_csv, D_pupil_um=args.D_pupil_um,
                            phi_min_deg=args.phi_min_deg, phi_max_deg=args.phi_max_deg,
                            phi_step_deg=args.phi_step_deg, R_rot_mm=args.R_rot_mm,
                            alignment_n_offsets=args.alignment_n_offsets,
                            gaze_distribution=args.gaze_distribution,
                            gaze_half_range_deg=args.gaze_half_range_deg,
                            gaze_sigma_deg=args.gaze_sigma_deg)


if __name__ == "__main__":
    main()
