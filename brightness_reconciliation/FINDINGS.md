# Brightness Floor Reconciliation: Percentage vs. Absolute (Troland) Thresholds

## The question

Does the project's reverse-engineered percentage brightness floor (6.25-9% of
full-pupil illuminance, `stage3a`) agree with the absolute, literature-derived
troland thresholds found in the separate illumination literature review (Van Nes &
Bouman 1967's 300 Td strict floor; the CIE 191:2010 ~3-5 cd/m^2 photopic boundary)?
These have never been checked against each other until now.

## The answer: yes and no, and the "no" case reveals something worth fixing

**At this project's own default scene luminance (10,000 cd/m^2, "bright daylight,"
used throughout Stage 3/4's sweeps), the two thresholds flatly disagree:**

| Scene luminance | CIE floor: min aperture | Van Nes & Bouman: min aperture |
|---|---|---|
| 10,000 cd/m^2 (this project's default) | 69-89 um | 195 um |

Both absolute floors are cleared by an aperture **far smaller** than even the
pure blur-only optimum (300-400um). At bright daylight, brightness is not a binding
constraint at all under either absolute criterion -- contradicting the entire premise
that a 6.25-9%/900-1250um floor is needed.

**But clinical visual acuity testing (where the clinical bracket and the reverse-
engineered floor both come from) is never done at bright-daylight luminance.** It is
done under standardized indoor lighting. Sheedy, Bailey & Raasch (1984, already cited
in the illumination review) tested the photopic acuity plateau over 40-600 cd/m^2;
typical clinical VA chart luminance (ETDRS-style) is commonly in the 85-320 cd/m^2
range. Re-running the same comparison at THAT luminance range instead:

| Scene luminance | CIE floor: min aperture | Van Nes & Bouman: min aperture |
|---|---|---|
| 100 cd/m^2 | 693-894 um | **1954 um** |
| 200 cd/m^2 | 490-632 um | **1382 um** |
| 300 cd/m^2 | 400-516 um | **1128 um** |

**At 300 cd/m^2, Van Nes & Bouman's independently-derived, strict absolute floor
predicts an aperture of 1128um -- almost exactly inside the reverse-engineered
900-1250um range, and well inside the verified clinical bracket (940-1750um).**
This is not a tuned match; Van Nes & Bouman's number was never touched to make this
happen, it simply lands there once a realistic clinical luminance is used instead of
this project's own bright-daylight default.

See `brightness_reconciliation.png` for the full picture across the whole realistic
luminance range, with both benchmark apertures and both absolute floors overlaid.

## What this actually establishes, stated precisely

**This substantially STRENGTHENS the headline brightness-floor finding, provisionally.**
The 6.25-9% figure was reverse-engineered with no independent physiological basis when
it was first found. It is no longer entirely unsupported: an independently-cited,
directly-verified 1967 result (not tuned to match anything in this project), applied at
a realistic — not this project's own overly bright — viewing luminance, predicts an
aperture in the same range. That is real, if provisional, corroboration.

**It also surfaces a genuine, previously-unnoticed problem worth fixing**:
`DEFAULT_SCENE_LUMINANCE_CDM2=10000` in `stage3_human_vision/photometry.py`, used
throughout every Stage 3/4 sweep to date, is the wrong luminance to assume when the
goal is comparing against clinically-measured acuity data -- clinical studies were
almost certainly conducted at 1-2 orders of magnitude dimmer light. Every troland/
photopic-illuminance number this project has computed so far (Stage 4's full sweep,
the illuminance-vs-aperture plots, etc.) used the bright-daylight default, not a
clinically-matched one. This does not invalidate those results as internally-consistent
optics (the relative comparisons across aperture are unaffected by an overall
luminance scaling), but it means none of them are actually comparable, in absolute
terms, to the clinical acuity data this project has been validating against.

## What remains open

1. **Sensitivity to the exact assumed luminance is real and large** (100 vs 300 cd/m^2
   changes the Van Nes & Bouman prediction by nearly 2x, from 1954 to 1128um). The
   actual chart/room luminance used in the Wang 2009 and Kim et al. 2017 studies was
   not stated in either paper as read in this project -- this reconciliation is
   therefore itself provisional on an assumed, not measured, clinical luminance.
2. **The two absolute floors (CIE vs. Van Nes & Bouman) disagree with each other by
   roughly 2-3x at any given luminance** -- they encode genuinely different
   physiological criteria (photopic/mesopic rod-cone boundary vs. Weber/de Vries-Rose
   contrast-threshold transition), not interchangeable numbers. Which one is the
   "correct" criterion for THIS specific question (pinhole-restricted acuity, not
   general low-light vision) is itself unresolved.
3. **Recommended next step**: re-run Stage 3/4's photometry-dependent sweeps at a
   clinically-realistic luminance (100-300 cd/m^2) alongside the existing bright-
   daylight default, and check whether Stage 4's failed acuity validation (RESULTS.md)
   changes at all under a correctly-matched luminance assumption -- it used the same
   10,000 cd/m^2 default throughout, which per this finding may itself have
   contributed to the validation mismatch, not just the small-N/non-monotonic-dataset
   causes already identified.
