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
"""
import pandas as pd


def gate_ghost_safety(df):
    return df.worst_case_ghost_margin > 0


def gate_vignetting_safety(df):
    return df.worst_case_vignetting_margin > 0


def gate_viability(df):
    """Requires total_illuminated_area_um2 > 0 at EVERY tested gaze angle phi (not
    merely at phi=0) -- checked via min_illuminated_area_um2_across_phi (see
    sweep/run_sweep.py's own schema comment), the worst-case-across-the-whole-
    tested-phi-range summary sweep/run_sweep.py already computes per row (and, for
    --scope=global rows, across the tested M range too -- see
    evaluate_candidate()'s own comment for that explicit resolution; NO row is left
    NaN/unchecked). A design that goes fully dark at ANY tested phi (or, for global
    scope, at any tested (M, phi) pair) fails this gate -- this is a MINIMUM-
    VIABILITY FLOOR (can the wearer see anything at all), NOT a brightness/
    transmission target: it does not compare or rank illuminated-area MAGNITUDE
    among viable designs, only excludes the ones that are strictly zero somewhere."""
    return df.min_illuminated_area_um2_across_phi > 0


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
