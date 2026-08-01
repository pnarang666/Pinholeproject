# PROJECT STATUS — Consolidated Summary
*Compiled to support discussion of where the project stands and what to prioritize next.
Distinguishes VERIFIED (personally checked against actual files/data in this conversation)
from LISTED (exists on disk, referenced by other files, but not independently audited here)
-- same evidence discipline the rest of this project has used throughout.*

---

## 1. The Physics Pipeline (VERIFIED, core chain solid)

**Stage 1 / Stage 1_v2** — exact Angular Spectrum Method propagation of a circular
pinhole to the corneal plane. Validated against real closed-form theory (Fresnel
on-axis oscillation formula, r=0.997 correlation). Fixed a real FWHM ring-hopping bug
(disambiguated threshold-crossing algorithm). **Known limitation, never fully
resolved**: the same ring-hopping instability reappears at the retina plane (Stage 3
Integrated found this too — see below).

**Stage 2 / Stage 2_fixed** — extends Stage 1 through eye lens + second ASM propagation
to retina, axial-length myopia model. Validated against the closed-form Airy disk at
zero defocus (r_EE 50/90% within 2%, r_EE 80% within 8%, the latter's wider tolerance
explained by real ill-conditioning near the Airy first null, not sloppiness). **Two
real bugs found and fixed** (documented in `CHANGES.md`): the energy-conservation check
was mathematically redundant with the band-limit check (proven, correlation=1.000000);
the wraparound safety margin was backwards (a minimum-divergence formula mislabeled as
conservative).

**R1 sweep result (the original headline number)**: pure blur minimization
(r_EE 50%) gives optimum aperture **300µm (M=1-4D) to 400µm (M=5-8D)**.

---

## 2. Brightness/Illuminance Work (VERIFIED)

**Stage 3a** — single-hole relative illuminance `E_rel = (min(a_hole,D_pupil)/D_pupil)^2`.
**Key finding**: a brightness floor of **6.25-9%** of full-pupil illuminance moves the
optimum from 300-400µm into the real clinical bracket (900-1250µm) — but this specific
percentage was reverse-engineered to match the known clinical range, not independently
derived. Confirmed the finding is robust across all four tested r_EE percentiles
(50/70/80/90%) once the brightness floor binds.

**Illumination literature review** (separate deep research pass, `Illumination.pdf`/
`.docx` in project root) — found the honest answer is that NO literature-validated
*percentage* threshold exists; the real, citable threshold is **absolute**: ~300
photopic trolands (Van Nes & Bouman 1967, Weber/de Vries-Rose transition) or ~3-5 cd/m²
(CIE 191:2010 photopic/mesopic boundary). This is the still-open item: the 6.25-9%
number has never been reconciled against this absolute threshold.

**stage_array / array_photometry.py** — multi-hole array photometry. **Key finding**:
sparse (KR-patent-style) pitch has a real zero-brightness failure mode — worst-case
pupil alignment can have **zero holes** under the pupil at all (continuum approximation
completely hides this). Dense (CN-patent-style) pitch gives a 23× brightness gain over
a single hole of the same size.

**singleilluminate/** — LISTED, not independently re-verified this session (built per
an earlier scoped prompt: single-hole-only illumination app, explicit seam left for
array integration later — `join_with_system.py` suggests the join step may have since
been attempted; not confirmed here).

---

## 3. Human Vision / Acuity Prediction (VERIFIED, with an important negative result)

**Stage 3 Human Vision** — MTF/OTF, two CSF models (4 cpd / 8 cpd peaks, both flagged
"heuristic," fit only to peak location), photometry (Trolands), three acuity models
(MTF-cutoff, VSX-approx, Rose-DeVries), Strehl, Pareto fronts. **Confirmed anomaly**:
Strehl ratio is genuinely (not artifactually) non-monotonic at these aperture scales —
a 10× finer sweep showed MORE oscillation, not less.

**Model Comparison** — audited the project's OWN deprecated closed-form formulas
against the exact numerical pipeline. RSS combination formula diverges by 64.8% mean
(192.8% max) at the retina plane. **The single most important finding project-wide**:
using r_EE(50%) to predict real clinical acuity (Wang 2009 dataset) overestimates blur
by ~7×; FWHM (core-width, not cumulative-energy) tracks it to ~1.6×.

**Stage 4 Human Vision** — troland-based illuminance, real Watson-Yellott pupil model
(constants independently verified correct, including a non-trivial continuity check at
age=20), neural adaptation. **Ran the actual validation test this all was building
toward**: Stage 4's VSOTF-adjusted predictor against the real Wang 2009 dataset (n=5).
**Result: FAILED.** R²=-2.84 to -6.39 (negative — worse than predicting the mean),
p=0.50-0.51 (not remotely significant) at every myopia level. A subsequent calibration
attempt, done correctly with leave-one-out cross-validation (not in-sample, which would
have overfit), also failed (R²=-0.54 to -0.59, Pearson r **flips sign** under LOO —
strong evidence the in-sample fit was noise). Independently confirmed by an external
check against a second real dataset (Kim et al. 2017): predicted 0.499 logMAR vs
observed 0.20±0.21 — a miss outside 1 SD.

**Honest conclusion, stated in `stage4_human_vision/RESULTS.md`**: *"this cannot be
properly validated with the clinical data currently available publicly."* Root causes
diagnosed, not hand-waved: n=5 is too small, the Wang dataset itself is non-monotonic
(0.28→0.31→**1.00**→0.40→0.50 across 5 apertures — a large, unexplained spike no
smooth model can fit), and no dataset anywhere has per-subject refractive error.

**`calibration.py` exists in stage4_human_vision/** — LISTED, appeared in the file tree
but not reviewed in this conversation; likely holds the calibration logic described
above (`calibration_per_M_stats.csv`, `calibration_pooled_stats.csv`,
`calibration_source_points.csv` are its outputs, all referenced in RESULTS.md).

---

## 4. Ghosting / Multi-Hole Array Theory (VERIFIED, actively evolving — the most recent work)

**`array_ghosting_theory/`** — built from scratch this session, went through three
honest revisions in sequence:

1. **First pass**: three-regime theory (Eq. 5) built from real citations (Gabor
   superlens, an independent US patent confirming the N_eff mechanism, Kim et al. 2017's
   directly-quoted real ghosting symptoms). Implemented and swept — found the CSF term
   was being evaluated 4+ octaves outside where the project's heuristic CSF was ever
   fit, producing physically impossible thresholds (up to 1,000,000) and never once
   triggering "danger zone."
2. **Second pass**: found and verified the REAL Barten (1999) CSF model (via the
   published `colour-science` package), sanity-checked it (0.6-3.6% threshold across a
   field-size range, physically sane), re-ran the identical sweep — **every previously-
   "safe" dense point reclassified as danger zone**, including the entire real CN
   patent pitch range. Now directionally consistent with Kim et al.'s real symptom
   reports.
3. **Third pass**: derived and checked the FULL HARMONIC SERIES (not just the
   fundamental frequency) of the multi-hole ghosting pattern. **Key finding**: the most
   dangerous harmonic is never the fundamental — it's whichever harmonic lands near
   1.9-2.3 cpd (the CSF peak), independent of pitch and robust across all tested myopia
   levels. **Generalizable conclusion**: for this near-eye geometry, any array dense
   enough to have N_eff>1 will almost inevitably have some harmonic land in the eye's
   most sensitive band — the "dense-but-safe" middle ground may not meaningfully exist;
   the only reliable safe zone is sparse enough that N_eff≤1.

This is the most mathematically rigorous and most recently-stress-tested piece of
theory in the whole project, and the one most directly demonstrating the
build→test→fail→fix→retest cycle a Physics Fight defense will need.

---

## 5. Patent & Literature Cross-Reference (VERIFIED)

Two real patents read directly (OCR'd where needed): **KR 10-2081511** (0.9mm effective
diameter, sits at the lower edge of the verified clinical bracket, described inventor
testing, no brightness analysis) and **CN 201716487U** (<0.4-0.8mm, a Chinese *utility
model* — administratively registered, not substantively examined — bare geometric
assertion, no brightness or ghosting analysis, plausibly shares this project's own
uncorrected blind spot).

---

## 6. Deliverables Already Produced

- **IYPT Theoretical Handbook 2** — 70-page docx/PDF (LaTeX version also exists,
  proper math typesetting, ~53 pages) consolidating Stages 1-3, Model Comparison,
  patents, error budget, roadmap.
- **`stage_v1_simulator/`** — an interactive app with more components than originally
  scoped (`eye_chart_blur.py`, `eye_diagram.py`, `light_acuity.py`, `sweep_ui.py`,
  `theory_browser.py`, `data_logger.py`) — LISTED, built across sessions, not fully
  re-verified in this summary.
- **Illumination literature review** — separate PDF/docx, the absolute-troland-vs-
  percentage finding referenced in Section 2 above.

---

## 7. What's Genuinely Open (the honest list, not a formality)

1. **The 6.25-9% brightness floor has never been reconciled against the absolute
   (~300 Td / ~3-5 cd/m²) threshold the illumination literature review found.** This is
   arguably the single highest-value remaining theoretical task — cheap, and directly
   connects two pieces of work that currently exist in parallel without touching.
2. **No acuity predictor (Stage 3 or Stage 4, heuristic or calibrated) has passed
   validation against real clinical data.** Confirmed, not assumed. More/better public
   data would fix this; no further model tuning will.
3. **The ghosting theory's Regime C prediction (dense arrays are dangerous) has zero
   experimental confirmation** — it's a real, citation-backed, internally-consistent
   theoretical prediction, and nothing more, until tested.
4. **Retina-plane FWHM and Strehl ratio are both confirmed unstable/non-monotonic** —
   neither should be used as a primary design metric without further work.
5. **The physical experiment has not yet been built or run.** Per earlier discussion,
   theory has now identified precisely where it cannot go further alone on at least
   three separate fronts (items 2, 3, and arguably 1) — this is no longer optional if
   the project wants to move past "here is what theory predicts" to "here is what is
   actually true."

---

## 8. Suggested Discussion Priorities

Given the above, three candidate directions for where to focus next, roughly in order
of cost vs. payoff:

- **(Cheapest, do first)** Reconcile item 7.1 — check whether the ~300 Td / 3-5 cd/m²
  absolute threshold, applied to this project's own aperture range at realistic scene
  luminances, actually recovers something close to the 6.25-9% figure, or contradicts
  it. This uses code that already exists in two different folders that have simply
  never been run against each other.
- **(Medium cost, highest scientific payoff)** Design the physical experiment now,
  informed by everything above — specifically targeting items 2 and 3, with per-subject
  refractive error recorded (the one fixable flaw every public dataset shares) and at
  least one intermediate/dense-pitch sample to test the ghosting prediction directly.
- **(Lower priority right now)** Further Stage 4 model refinement — per the honest
  conclusion in Section 3, this has already been shown not to be where the problem
  lives; more tuning without more data is unlikely to change the outcome.
