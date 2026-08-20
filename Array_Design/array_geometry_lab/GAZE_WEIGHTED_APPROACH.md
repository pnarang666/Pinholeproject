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
- The worst-case gates remain the primary safety criterion for anything
  presented as "guaranteed safe." The gaze-weighted numbers are reported
  as a secondary, realistic-use metric, not a substitute pass/fail rule.
- This does not resolve which design should be preferred — it makes the
  actual trade-off (rare severe failure vs. common mild failure) visible
  and quantified, which is a precondition for that decision, not the
  decision itself.
