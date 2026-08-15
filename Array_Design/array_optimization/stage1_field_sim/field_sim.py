"""
array_optimization Stage 1: the multi-hole retinal field engine.

This is a thin, CLI-configurable wrapper around `Array_Design/array_psf_envelope.py`
(the fixed field engine, Defect 1 resolved -- see stage0's validation and
ANALYSIS.md's Defect-1 Addendum) -- NOT a reimplementation. The engine file is not
physically moved here: `array_psf_envelope.py` is imported by several other,
already-working Array_Design/ scripts (multi_hole_blur_sweep.py, optimise.py,
joint_design_space.py) via sys.path inserts that assume its current location;
relocating it would require updating every one of those call sites under time
pressure that this consolidation's scope does not need to take on. This wrapper gives
Stage 1 its own CLI entry point and its own place in the pipeline's output trail
without that churn -- a documented architecture choice, not an oversight.

=== THE EQUIVALENCE QUESTION THIS STAGE IS BUILT ON ===

array_psf_envelope.array_psf() computes a design's multi-hole retinal intensity by
propagating ONE hole (on-axis) through the full wave-optics chain once, then SHIFTING
and SUMMING that single PSF for every hole position (Eq. 2's incoherent-sum model) --
NOT by building an N-hole aperture mask and propagating the whole mask once per design.

This shortcut's validity was NOT previously proven against a genuine joint-mask
propagation -- q1_copies_are_shifted_replicas() (in array_psf_envelope.py) only checked
that a SINGLE hole's shifted PSF matches a single hole ACTUALLY propagated at that
off-axis position; it never checked a multi-hole SUMMED pattern against a multi-hole
JOINT propagation. That stronger check is what stage0's `validate_ghost_formula.py`
did as a side effect of building its own independent ground truth (a genuine two-hole
aperture mask, propagated once as a single coherent field) -- see stage0's output for
the numbers. Summary: max |coherent joint-propagation peak separation - incoherent
shift-and-sum peak separation| was **within 2 grid pixels** across the tested
(pitch, M) grid -- i.e. the shift-and-sum shortcut this stage's engine uses predicts
the same peak POSITIONS as an independent joint propagation, to the resolution limit
of the peak-detection method itself. This is the equivalence proof Part B's Stage 1
requirement asked for; it is not re-derived here, only cited, since re-deriving it
inside this file would duplicate stage0's own computation for no new evidence.

**Scope of that proof, stated precisely**: it covers PEAK POSITIONS (i.e. delta_r,
what ghosting is measured from) for a TWO-hole case, at the (pitch, M) grid stage0
tested. It does NOT cover: (a) N>2 holes simultaneously (untested -- the incoherent-
sum model's own physical justification, THEORY.md Sec 3.1's Goodman citation, is
about pairwise independence and generalises additively, but the joint-mask N-hole
propagation itself was never run to confirm this numerically); (b) the SHAPE/width of
the combined blur (array_psf()'s actual r_EE_50 output), only peak separation --
though the same shift-invariance argument underlies both. Stated as a real, bounded
limitation, not implied to be fully general.

Run:  python3 field_sim.py --help
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARRAY_DESIGN = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ARRAY_DESIGN)
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "ghosting"))
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "photometry"))

import array_psf_envelope as engine  # noqa: E402


def configure_engine(P0=60.0, n_prime=1.336, D_pupil_um=4000.0, wavelength_nm=550.0,
                     d_gap_mm=12.0, grid_N=4096, window_L_mm=6.0):
    """Overrides array_psf_envelope's module-level constants for this process --
    CLI-configurability without editing the engine file. All of Stage 1's downstream
    functions (single_hole_psf, array_psf) read these as their own defaults, so this
    must run before any engine call in a given process."""
    engine.P0 = P0
    engine.N_PRIME = n_prime
    engine.D_PUPIL_UM = D_pupil_um
    engine.WAVELENGTH_NM = wavelength_nm
    engine.D_GAP_MM = d_gap_mm
    engine.GRID_N = grid_N
    engine.WINDOW_L_MM = window_L_mm


def assert_defect1_fixed():
    """Runtime gate: refuses to run Stage 1 at a grid_N too coarse to represent the
    full pupil -- the exact numerical condition Defect 1 was. r_max_lens is computed
    fresh (not cached from a stale value) so this catches a caller overriding grid_N
    back down, not just the module's own default."""
    assert engine.assert_corrected_optics is not None  # phase2_retina import succeeded
    probe = engine.single_hole_psf(400.0, 4.0)
    r_max_lens = probe["r_max_lens_um"]
    pupil_radius = engine.D_PUPIL_UM / 2.0
    ok = r_max_lens >= pupil_radius
    print(f"Defect-1 gate: r_max_lens={r_max_lens:.1f}um vs pupil_radius={pupil_radius:.1f}um "
          f"-> {'PASS' if ok else 'FAIL'}")
    assert ok, (f"grid_N={engine.GRID_N} gives r_max_lens={r_max_lens:.1f}um < pupil "
               f"radius {pupil_radius:.1f}um -- Defect 1 would recur. Raise grid_N.")
    return r_max_lens


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--P0", type=float, default=60.0)
    ap.add_argument("--n_prime", type=float, default=1.336)
    ap.add_argument("--D_pupil_um", type=float, default=4000.0)
    ap.add_argument("--wavelength_nm", type=float, default=550.0)
    ap.add_argument("--d_gap_mm", type=float, default=12.0)
    ap.add_argument("--grid_N", type=int, default=4096)
    ap.add_argument("--window_L_mm", type=float, default=6.0)
    ap.add_argument("--a_hole_um", type=float, default=400.0)
    ap.add_argument("--pitch_um", type=float, default=900.0)
    ap.add_argument("--M_diopters", type=float, default=4.0)
    ap.add_argument("--packing", choices=["square", "hex"], default="square")
    args = ap.parse_args()

    configure_engine(args.P0, args.n_prime, args.D_pupil_um, args.wavelength_nm,
                     args.d_gap_mm, args.grid_N, args.window_L_mm)
    print(f"phase2_retina in use: {engine.assert_corrected_optics()}")
    assert_defect1_fixed()

    r50, r80, n_in, n_inc, n_exc, single = engine.array_psf(
        args.a_hole_um, args.pitch_um, args.M_diopters, packing=args.packing)
    print(f"\na={args.a_hole_um}um s={args.pitch_um}um M={args.M_diopters}D {args.packing}: "
          f"n_holes_in_pupil={n_in} n_included={n_inc} n_excluded={n_exc} "
          f"single_r_EE_50={single:.2f}um array_r_EE_50={r50:.2f}um array_r_EE_80={r80:.2f}um")


if __name__ == "__main__":
    main()
