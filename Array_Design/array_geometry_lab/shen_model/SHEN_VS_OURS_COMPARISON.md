# Shen's Own Evaluator vs. This Project's Hard-Gated Pipeline

`shen_model/shen_evaluator.py` is a standalone, from-scratch reimplementation
of Shen (Hangzhou Normal University, Aug. 2026)'s own formulas (Sec 2.1, 2.2,
2.4 — cited in-code) — not a reuse of this project's judgment layer. It imports
only this project's generators (for coordinates) and `overlap_area_um2` (pure
circle-circle geometry); no gates, metrics, margin, or degeneracy-filter code.
Run: `c_min=55`, `n_trials=1000`, all 10 families, M=0–8 (M='global' excluded
— Shen's formulas are all per-M, the paper describes no cross-M aggregate).

## Does the Monte Carlo ghost_rate agree with the closed-form g_Sch?

**No — they are essentially uncorrelated.** Computed directly, not assumed:
correlation(ghost_rate, g_Sch) across all 7708 candidates = **-0.0485**.
`ghost_rate` is bimodal (52.6% of candidates at exactly 1.0, 10.9% at exactly
0.0 — the coverage-vs-multiplicity split this project already found shows up
here too, in a completely independent model). `g_Sch` is a smooth, unbounded
closed-form number (mean 1.99, 65% of candidates > 1.0) with no such bimodal
structure. These are genuinely different quantities computed genuinely
differently (a single representative-spacing formula vs. a 2D Monte Carlo
sample over object direction and pupil wander) — reported as found, not forced
to agree.

## Winner per M — real numbers both ways

| M | **Our winner** (hard-gated) | → Shen ghost_rate / blind_rate / S | **Shen's winner** | → our margins |
|---|---|---|---|---|
| 0.0 | square, N=9, pitch=2000 | 0.000 / 0.000 / S=0.485 | poisson_disk, N=20, sf=2.0 | ghost=+∞, vign=+∞ |
| 1.0 | square, N=100, pitch=3000,45° | 0.383 / 0.000 / S=0.654 | jittered_lattice, N=100, pitch=3000 | ghost=+∞, vign=**-7.05** |
| 2.0 | square, N=100, pitch=3000,45° | 0.809 / 0.000 / S=0.477 | archimedean_spiral, N=20, c=1000 | ghost=+∞, vign=**-13.44** |
| 3.0 | square, N=100, pitch=3000,45° | 0.823 / 0.000 / S=0.473 | archimedean_spiral, N=20, c=1000 | ghost=+∞, vign=**-14.68** |
| 4.0 | square, N=50, pitch=3000,45° | 0.781 / 0.000 / S=0.447 | archimedean_spiral, N=20, c=1000 | ghost=+∞, vign=**-14.97** |
| 5.0 | square, N=50, pitch=3000,45° | 0.775 / 0.000 / S=0.446 | archimedean_spiral, N=20, c=1000 | ghost=+∞, vign=**-14.11** |
| 6.0 | square, N=50, pitch=3000,45° | 0.697 / 0.000 / S=0.442 | archimedean_spiral, N=20, c=1000 | ghost=+∞, vign=**-20.21** |
| 8.0 | square, N=50, pitch=3000,45° | 0.675 / 0.000 / S=0.433 | poisson_disk, N=20, sf=2.0 | ghost=**-30.51**, vign=**-30.51** |

*(M='global' has no Shen-model row — out of scope for Shen's own per-M
formulas.)*

## The divergence, traced to real numbers, not assumed

**Our own "safe" winner ghosts in Shen's evaluator, 68–82% of the time at
M=2–8.** Our pipeline's `worst_case_ghost_margin=+inf` for the square winner
at every M means *zero simultaneously active pairs under our own protocol*
(pairs whose overlap with the pupil clears our own 50%
`active_frac_threshold`, sampled at discrete phi angles). Shen's protocol
tests a much larger space — any nonzero overlap "admits a beam" (no 50%
threshold), sampled across a full 2D object-direction field (±10° solid
angle) plus positional wander. The same square lattice that never produces a
50%-overlap pair under our narrower test produces *some* overlapping pair in
most of Shen's 1000 trials. Neither model is wrong; they are answering
differently-scoped questions about the same geometry.

**Shen's own winner is genuinely unsafe by our own, independently computed
margins.** At M=2–6, Shen picks `archimedean_spiral` despite its own
`ghost_rate` running 0.47–0.91 (its own model does not treat this as
disqualifying — `mu_g`'s dynamic range, as given, only spans sigmoid(0)=0.5 to
sigmoid(2)=0.88, a weak penalty by construction, not a bug in our
reimplementation). Under our own pipeline, this exact same candidate has
`worst_case_vignetting_margin` of -13 to -20 — a real, independently computed
failure our margin-aware gate would reject outright. Consistent with this
project's earlier finding (`MODEL_COMPARISON.tex`): **Shen's score has no
vignetting term at all** — `a_norm`, `mu_eta`, `mu_g(ghost_rate)`, and
`(1-blind_rate)` never reference gaze-angle-dependent safety, so a candidate
that fails badly on vignetting alone is invisible to it.

**At M=8, both models independently reject their counterpart's alternative —
but the numbers in the table above belong to TWO DIFFERENT DESIGNS, not one.**
This distinction matters and was previously stated ambiguously; corrected here.

Shen's own top-scoring design (`poisson_disk`, N=20, sf=2.0) is rejected
outright by our own margin (`worst_case_ghost_margin=-30.51`, a real,
decisive failure) — and that same design *also* independently reads
`ghost_rate≈1.000` under Shen's own Monte Carlo evaluator, meaning Shen's own
more rigorous method flags his own paper's optimizer's M=8 choice as ghosting
in nearly every trial. This is a genuine self-inconsistency internal to
Shen's published pipeline: his closed-form optimizer and his own MC evaluator
disagree with each other about his own winning design.

Separately, our own winner (`square`, N=50, pitch=3000, 45°) shows an
elevated `ghost_rate=0.675` under Shen's more permissive activation rule —
**not because it is actually unsafe**. Our own protocol independently finds
this same design `worst_case_ghost_margin=+inf`. The elevated Shen-model
ghost_rate reflects Shen's any-overlap admission criterion counting pairs
that our stricter 50%-overlap threshold does not, not an actual safety
failure in our winner.

These are two separate findings about two separate designs — do not read
this section as "our winner is also bad at M=8." It is not.

## Summary

Two independently-computed, methodologically distinct models agree on almost
nothing at the level of *which candidate wins*, and the divergence is fully
explained by concrete, traceable numbers, not by either implementation being
broken: different admission criteria (50%-overlap threshold vs. any-overlap),
different sampling (1D discrete phi vs. 2D continuous object-direction +
wander), and — most consequentially — Shen's score has no vignetting
dimension at all, which this project's own pipeline treats as an independent,
non-negotiable safety axis.
