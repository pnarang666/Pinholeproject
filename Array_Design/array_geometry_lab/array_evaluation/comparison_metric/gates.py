"""
Pluggable safety-gate framework. Each gate is an independent, named, boolean-mask
function over a DataFrame -- gates are combined by AND in apply_gates(), so adding or
removing a gate is a one-function change to GATES, never a rewrite of the ranking
logic in metrics.py/run_comparison.py.

Originally only two gates existed here ('ghost_safety', 'vignetting_safety'). There
is deliberately still NO reproducibility/seed-variance gate, even though
high_seed_variance is available in family_ranking.csv -- stochastic families'
greater susceptibility to failing these gates should show up naturally in survivor
counts (run_comparison.py reports this per family), not be pre-filtered before the
comparison even runs.

Confirmed against sweep_results.csv before this module was written: ghost-margin
safety (worst_case_ghost_margin > 0) and vignetting-margin safety
(worst_case_vignetting_margin > 0) are NOT redundant -- among rows with
worst_case_ghost_margin == inf, the fraction that also have
worst_case_vignetting_margin <= 0 ranges from 36% (concentric) to 89%
(fibonacci_spiral/golden_angle) depending on family. Neither gate is a proxy for
the other; both are applied independently.

AUDIT FIX (Defect B/1 -- "the metric rewards blindness"): gate_ghost_safety and
gate_vignetting_safety BOTH test only for the ABSENCE of ghosting. A design with
ZERO illuminated holes has zero active pairs, therefore infinite margin on BOTH
gates, therefore scores as maximally safe -- the literal global optimum of the old
two-gate objective was an opaque lens (confirmed: the Metric-1 winners at M=4.0/5.0
were exactly this, a genuine blackout design with zero true overlap area at
phi=0, not a counting artifact). gate_viability is a THIRD, INDEPENDENT,
separately-named gate closing this -- kept separate from the other two on purpose
(not folded into either) so its own effect on survivor counts stays independently
auditable, per this module's own explicit instruction. Gate 3 is a MINIMUM-
VIABILITY FLOOR ONLY -- "can the wearer see anything at all" -- NOT a brightness or
transmission OBJECTIVE; it does not rank or reward MORE light, only excludes
designs with strictly ZERO illuminated area at some tested condition. This project's
scope explicitly excludes brightness/transmission as an optimization target
elsewhere, and this gate does not reintroduce it.

AUDIT FIX (margin-vs-zero -> margin-vs-real-threshold): every prior "winner" that
turned out to be a boundary case (blackout designs with margin=+inf from zero active
pairs; a near-miss hexagonal candidate at worst_case_ghost_margin=-16.6 sitting right
next to designs passing at single-digit margins) shared one root cause -- these three
gates required margin > 0, not margin > a real, justified threshold. A margin of
+0.001 and a margin of +50 both passed identically. Fixed below by requiring a real
margin above a KNOWN, SOURCED uncertainty in the underlying quantity, not an
arbitrary round number:

  GHOST_FORMULA_GRID_DX_UM = 1.46484375: the grid pixel size from
  array_optimization/stage0_ghost_validation/validate_ghost_formula.py's own M=0
  validation run (grid_N=4096, window_L_mm=6.0 -> dx=6000um/4096;
  ghost_formula_validation.csv, generated 2026-08-14), the SAME physical-optics
  simulation this project's copied ghost_formula.py was validated against.

  GHOST_DELTA_R_UNCERTAINTY_UM = 2 * GHOST_FORMULA_GRID_DX_UM = 2.9297um: THAT
  file's own already-stated tolerance for a two-peak separation measurement ("a
  peak-detection method resolves position to about +-1 pixel per peak, so +-2
  pixels for a two-peak separation is the natural, grid-justified tolerance; not an
  arbitrarily chosen round number" -- validate_ghost_formula.py's own comment). This
  is the known measurement uncertainty in delta_r_actual, the quantity
  worst_case_ghost_margin AND worst_case_vignetting_margin are both built from
  (margin = 1 - delta_r_actual/resolvable_blur_um -- vignetting margin is the same
  formula, evaluated at shifted pupil positions via the same
  worst_case_ghost_margin() call, see margins/vignetting_robustness.py). Converted
  from an absolute (um) uncertainty into this row's own margin units by dividing by
  its own resolvable_blur_um column (now present for every row, per_M and global
  alike -- see sweep/run_sweep.py's own resolvable_blur_um documentation) --
  NOT a single fixed margin number, since margin is a ratio and resolvable_blur_um
  varies row to row (M and a_hole_um dependent).

  MARGIN_SAFETY_MULTIPLE = 2.0: this task's own requested multiple, applied ON TOP
  of the already-established uncertainty above -- i.e. the margin must clear its own
  known positional noise floor by a further factor of 2 before being trusted as a
  real pass, not a coin-flip near the boundary. No stronger project-internal
  precedent exists for a different number, and 2x is the same order the grid
  tolerance itself already uses (2 pixels, not 1) -- kept consistent rather than
  introducing an unrelated third number.

  gate_viability's new floor (0.20 * pi*R_h^2, R_h = a_hole_um/2, hole radius -- the
  only "R_h" quantity this project has) is as given in this task's own brief, not
  independently re-derived here.

Both new thresholds are computed PER ROW (not one global constant), since
resolvable_blur_um and a_hole_um both vary by M and candidate -- printed and written
out explicitly by array_evaluation/comparison_metric/final_winner.py so the actual
margin vs. its required threshold is auditable per winner, not just a pass/fail bit.
"""
import numpy as np
import pandas as pd

GHOST_FORMULA_GRID_DX_UM = 1.46484375
GHOST_DELTA_R_UNCERTAINTY_UM = 2.0 * GHOST_FORMULA_GRID_DX_UM
MARGIN_SAFETY_MULTIPLE = 2.0

VIABILITY_MIN_FRACTION_OF_HOLE_AREA = 0.20


def ghost_margin_threshold(df):
    """Per-row required margin -- see module docstring. Uses this row's OWN
    resolvable_blur_um (present for every row, per_M and global alike)."""
    return MARGIN_SAFETY_MULTIPLE * GHOST_DELTA_R_UNCERTAINTY_UM / df.resolvable_blur_um


def viability_area_threshold(df):
    """Per-row required illuminated area -- 20% of this row's own single-hole area
    (pi*R_h^2, R_h=a_hole_um/2), as given in this task's brief."""
    R_h = df.a_hole_um / 2.0
    return VIABILITY_MIN_FRACTION_OF_HOLE_AREA * np.pi * R_h ** 2


def gate_ghost_safety(df):
    return df.worst_case_ghost_margin >= ghost_margin_threshold(df)


def gate_vignetting_safety(df):
    return df.worst_case_vignetting_margin >= ghost_margin_threshold(df)


def gate_viability(df):
    """Requires illuminated_area_um2 >= 0.20*pi*R_h^2 at EVERY tested gaze angle phi
    (not merely at phi=0) -- checked via min_illuminated_area_um2_across_phi (see
    sweep/run_sweep.py's own schema comment), the worst-case-across-the-whole-
    tested-phi-range summary sweep/run_sweep.py already computes per row (and, for
    --scope=global rows, across the tested M range too). A design that drops below
    20% of one hole's own area at ANY tested phi (or, for global scope, at any
    tested (M, phi) pair) fails this gate -- see module docstring's AUDIT FIX
    (margin-vs-zero -> margin-vs-real-threshold) for why this replaced the prior
    >0 check. Still a MINIMUM-VIABILITY FLOOR, not a brightness/transmission
    ranking target -- it does not compare or reward illuminated-area magnitude
    beyond this floor."""
    return df.min_illuminated_area_um2_across_phi >= viability_area_threshold(df)


GATES = {
    "ghost_safety": gate_ghost_safety,
    "vignetting_safety": gate_vignetting_safety,
    "viability": gate_viability,
}

DEFAULT_GATES = ["ghost_safety", "vignetting_safety", "viability"]


def apply_gates(df, gate_names=None):
    """Returns the subset of df where EVERY named gate's mask is True (logical AND).
    gate_names defaults to DEFAULT_GATES, not all of GATES -- so adding a future gate
    to the registry does not silently change what a caller who didn't ask for it
    gets."""
    if gate_names is None:
        gate_names = DEFAULT_GATES
    unknown = set(gate_names) - set(GATES.keys())
    if unknown:
        raise ValueError(f"unknown gate name(s): {sorted(unknown)} -- known gates: {sorted(GATES.keys())}")
    mask = pd.Series(True, index=df.index)
    for name in gate_names:
        mask &= GATES[name](df)
    return df[mask]
