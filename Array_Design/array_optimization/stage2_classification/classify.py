"""
array_optimization Stage 2: ghosting classification, continuous risk as the SOLE
decision input going forward.

Wraps `Array_Design/ghosting_risk.py` (fixed once Defect 2's validated formula is wired
in -- see stage0's validation and the Defect-2 Addendum in ANALYSIS.md). Not physically
relocated, for the same reason as Stage 1 (other Array_Design/ scripts still import it
from its current location).

=== DEPRECATION, STATED EXPLICITLY ===

The ORIGINAL binary A/B/C gate (`ghosting/ghosting_regime.py`, and
`corrected_regime.classify()`'s `regime_binary`/`regime_harmonic` fields built on top
of it) is **deprecated as a DECISION input from this stage onward**. It is not deleted
(ghosting_regime.py is untouched history; classify()'s regime fields are still computed
and still exposed here for reference) -- it is deprecated because ANALYSIS.md's F2
finding is that its Regime-A cutoff is decided on the alignment MINIMUM, which is wrong
for ghosting specifically, and the live optimiser found 541/1370 points across the full
design grid labelled "safe" by that rule while carrying risk >10x past the CSF
threshold (ANALYSIS.md's second-pass Addendum). Stage 3's Pareto front is gated on
`ghosting_risk.py`'s continuous `risk` value (threshold documented at the call site
below), never on `regime_binary`. `classify_design()` still RETURNS the binary label
alongside risk, for transparency and for anyone auditing a Stage-3 decision against the
older rule -- but nothing downstream branches on it.

=== FULL HARMONIC-SERIES CHECK: ALREADY IMPLEMENTED, AND A FACTUAL CORRECTION ===

The task that requested this stage stated "prior work found the dangerous harmonic is
usually n=2-3." That does not match either of this project's own prior findings, and is
corrected here with the actual numbers rather than propagated:

  - Pass 3 (`ghosting/RESULTS.md`), UNDER THE LEGACY (since-invalidated) separation
    formula: worst harmonic was NEVER n=1, but ranged n=4 to n=20 depending on pitch --
    not "usually 2-3."
  - Pass 4 (same file), UNDER THE CORRECTED formula: worst harmonic is n=1 at 20/20
    dense points tested, worst-margin/fundamental-margin ratio = 1.000 exactly.
  - TODAY (stage0's validate_ghost_formula.py, an independent two-hole propagation,
    not a reuse of Pass 4's own code): confirms the corrected formula is the right one
    (R^2=0.999 vs measured peak separations, M=0 gate passed at 1 grid pixel).

So the harmonic-series check this stage exposes is not a NEW requirement being added --
`corrected_regime.margin_detail()` (called by `ghosting_risk.py`, called by this file)
already loops every harmonic n=1..40 up to the eye's resolution limit and reports the
WORST one, not just n=1 (`ghosting/corrected_regime.py`, unchanged by this stage). What
changes here is only the documentation: with the now-doubly-validated corrected
formula, that worst harmonic is expected to be n=1 almost everywhere in this project's
geometry, and `classify_design()` reports which n actually won for every design so this
can be checked per-point rather than assumed from the aggregate finding above.

Run:  python3 classify.py --help
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARRAY_DESIGN = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ARRAY_DESIGN)
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "ghosting"))
sys.path.insert(0, os.path.join(ARRAY_DESIGN, "photometry"))

import ghosting_risk as gr  # noqa: E402
import corrected_regime as cr  # noqa: E402
import joint_design_space as jds  # noqa: E402

# The threshold Stage 3 gates on. risk=1.0 is ghosting_risk.py's own natural unit (the
# point where the probability-weighted worst-harmonic margin crosses the CSF detection
# threshold) -- documented in ghosting_risk.py's module docstring, not invented here.
RISK_SAFE_THRESHOLD = 1.0


def configure(P0=60.0, n_prime=1.336, D_pupil_um=4000.0, wavelength_nm=550.0,
             d_gap_mm=12.0, grid_N=4096, window_L_mm=6.0):
    import array_psf_envelope as engine
    engine.P0 = P0; engine.N_PRIME = n_prime; engine.D_PUPIL_UM = D_pupil_um
    engine.WAVELENGTH_NM = wavelength_nm; engine.D_GAP_MM = d_gap_mm
    engine.GRID_N = grid_N; engine.WINDOW_L_MM = window_L_mm
    jds.D_PUPIL_UM = D_pupil_um


def classify_design(a_hole_um, pitch_um, M_diopters, packing="square",
                    n_offsets=61, risk_safe_threshold=RISK_SAFE_THRESHOLD, **kwargs):
    """The sole classification call Stage 3 should use. Returns risk (the decision
    input), is_safe (risk < threshold -- what Stage 3 actually gates on), and the
    deprecated binary label alongside it for reference only."""
    r = gr.ghosting_risk(a_hole_um, pitch_um, M_diopters, packing=packing,
                         n_offsets=n_offsets, **kwargs)
    r["is_safe"] = bool(r["risk"] < risk_safe_threshold)
    r["risk_safe_threshold"] = risk_safe_threshold
    r["deprecated_binary_regime"] = r.pop("regime_binary")
    return r


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
    ap.add_argument("--risk_safe_threshold", type=float, default=RISK_SAFE_THRESHOLD)
    args = ap.parse_args()

    configure(args.P0, args.n_prime, args.D_pupil_um, args.wavelength_nm,
             args.d_gap_mm, args.grid_N, args.window_L_mm)
    print(f"phase2_retina in use: {cr.assert_corrected_optics()}")
    cr.self_check()

    r = classify_design(args.a_hole_um, args.pitch_um, args.M_diopters, args.packing,
                        wavelength_nm=args.wavelength_nm, d_gap_mm=args.d_gap_mm,
                        D_pupil_um=args.D_pupil_um, P0=args.P0, n_prime=args.n_prime,
                        grid_N=args.grid_N, window_L_mm=args.window_L_mm,
                        risk_safe_threshold=args.risk_safe_threshold)
    print(f"\na={args.a_hole_um}um s={args.pitch_um}um M={args.M_diopters}D {args.packing}:")
    for k, v in r.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
