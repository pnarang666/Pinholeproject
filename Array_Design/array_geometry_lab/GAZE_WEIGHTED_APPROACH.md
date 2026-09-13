# Gaze-Weighted Evaluation: What It Is and Why It's Useful

## The Problem With Worst-Case-Only Evaluation

Every design in this project has, up to this point, been judged by a single
rule: **it must remain ghost-free and non-blind at every tested gaze angle,
from straight-ahead (0°) out to 25° off-axis, with no exceptions.**

This is a legitimate and conservative engineering standard. But it has a
real cost: it treats a failure at 25° — an angle the human eye visits for
a tiny fraction of the time — exactly as seriously as a failure at 0°,
where the eye spends the vast majority of its time. A design that is
excellent for 98% of real use and only breaks down in the rare periphery
gets discarded identically to a design that is broken at every angle.

This is not a hypothetical concern. The `concentric_centered` variant
tested in this project fails the worst-case gate specifically because of
a complete blackout in the 20°–25° range — while it is *better* than the
current winner everywhere inside 15°. Worst-case evaluation alone cannot
tell these two situations apart.


## The Data: How Often the Eye Actually Looks Where

Real eye-tracking data on gaze eccentricity (how far off-axis the eye
points during natural viewing) gives a measured distribution, not an
assumption:

| Eccentricity | % of time in this 1° bin | Cumulative |
|---|---|---|
| 0°–1° | 9.29% | 9.29% |
| 5°–6° | 7.57% | 51.61% (median) |
| 10°–11° | 4.40% | 80.07% |
| 16°–17° | 1.45% | 95.27% |
| 20°–21° | 0.50% | 98.46% |
| >25° | 0.58% | 100.00% |

The distribution is sharply peaked at the center and falls off fast: half
of all viewing time is within 6° of straight ahead, and 95% is within 17°.
The 20°–25° range that disqualifies `concentric_centered` accounts for
roughly 1.5% of total viewing time.

## The Math: Weighting Instead of Worst-Casing

Instead of asking *"does this design fail anywhere in 0°–25°?"*, the
gaze-weighted evaluation asks a different, complementary question:

$$P(\text{blind}) = \int w(\varphi) \cdot \mathbb{1}[\text{blind at } \varphi] \, d\varphi$$

$$P(\text{ghost}) = \int w(\varphi) \cdot \mathbb{1}[\text{ghosting at } \varphi] \, d\varphi$$

where $w(\varphi)$ is the measured eccentricity distribution above,
normalized to sum to 1. The result is not a margin number — it is a
directly interpretable quantity: **"this design ghosts for X% of a
wearer's actual viewing time."**

Two details matter for correctness:
- **The weight applies to the outcome, not the margin.** Averaging raw
  margins can hide a rare-but-total failure inside a good mean. Averaging
  the binary blind/ghost outcome cannot.
- **Every angle is sampled across all azimuths (gaze directions), not
  just one.** This project's own data showed that blackouts in ring-based
  geometries appear in the *gaps between* discrete ring holes, invisible
  if only a single radial direction is checked.


## Why This Is Useful — Three Concrete Benefits

**1. It separates two genuinely different kinds of failure.** A design
that is unsafe at every angle and a design that is unsafe only in the
rarely-visited periphery are physically very different products. Only the
gaze-weighted metric can distinguish "broken" from "excellent, with a
narrow edge case."

**2. It directly answers the question a reviewer will ask.** "Do you
really need to guarantee safety all the way to 25°, given the eye is
barely ever there?" is an obvious, fair question once a worst-case-only
result is presented. Having the weighted number ready — not as a
replacement, but alongside — answers it with data instead of argument.

**3. It does not discard the conservative standard — it adds to it.**
This project reports both numbers for every design: the existing
worst-case margin (a hard engineering guarantee, useful for safety-
critical framing) and the new gaze-weighted percentage (a realistic
in-use performance figure). Neither replaces the other. A design that
looks bad on worst-case but excellent on gaze-weighted invites an honest,
explicit statement of that trade-off — which is a stronger position than
silently picking one standard and hiding the other.

## What This Does Not Change

- The underlying physics (ghost formula, overlap geometry) is identical —
  only the *aggregation* of gaze angles is new.
- This does not resolve which design should be preferred on its own — it
  makes the actual trade-off (rare severe failure vs. common mild failure)
  visible and quantified, which is a precondition for that decision, not
  the decision itself.

## UPDATE, 2026-09-13 -- gaze-weighted is now this project's PRIMARY standard

Per explicit user decision, the ranking hierarchy stated above (worst-case
primary, gaze-weighted secondary) is superseded: **gaze-weighted ghost %,
combined with a hard blindness gate, is now the project's primary
methodology**, judged more realistic than a pure worst-case-across-every-
tested-gaze-angle criterion. The worst-case gates (`gates.py`,
`effective_density_ranking.py`, `metrics.py`) are NOT deleted or edited —
their output remains valid, reported data — but they are no longer this
project's headline answer.

The new primary ranking (`comparison_metric/primary_ranking_gaze_weighted.py`,
output `array_data/evaluation_results/PRIMARY_WINNER_PER_M.csv`):
  1. HARD GATE: exclude any candidate with `time_weighted_blind_pct > 1.0%`.
  2. Among survivors, minimize `time_weighted_ghost_pct` (tie-break on
     `time_weighted_blind_pct`).

**Checked, not assumed, before picking 1.0% as the gate threshold:** a
strict 0%-blind gate was tried first and produces a sharp cliff at M=6D and
M=8D — every genuinely-zero-blind candidate at those M has 27–30% ghost,
while the excellent 0%-ghost candidates that exist there (hexagonal,
pitch=4000µm) carry a small nonzero blind time (0.33–0.71%). A bare-zero
threshold is exactly the "margin vs. zero" failure this project's own
`gates.py` already diagnosed once before — so a small, explicit, documented
tolerance (1.0%, chosen to clear every observed winner's own blind_pct with
headroom while staying obviously non-degenerate) is used instead, matching
established project precedent rather than introducing a new unexamined
convention.

**Result:** hexagonal wins M=1–6, square wins M=0/8/global — identical
family choices to the old (ungated) `gaze_weighted_winner_per_M.csv`, since
every one of those winners already happened to clear the 1.0% gate on its
own. The gate did not have to override any existing pick; it exists to
guarantee that a future re-run, on different candidate data, cannot
silently select a degenerate mostly-blind design the way the old ungated
ranking's own docstring warned it theoretically could.
