# R7acuity: results

## What this run was for

`stage4_human_vision/acuity.py` (a closed-form, MTF-cutoff-based acuity predictor)
fails clinical validation against the Wang (2009) "Ideal Pinhole" dataset (n=5
apertures per M, leave-one-out R^2 negative in every case -- see
`stage4_human_vision/RESULTS.md` Section 4c). That failure was diagnosed there as
predominantly a **data** problem (n=5, one non-monotonic clinical point, no
per-subject refractive error) rather than a **model** problem specific to a
frequency-cutoff formula. A single model's failure on small, noisy data can't by
itself distinguish those two explanations.

R7acuity is a structurally unrelated architecture -- a Monte Carlo template-matching
ideal-observer simulation (Watson & Ahumada, 2008), not a closed-form formula --
built specifically to provide a second, independent test. It reuses the same
validated optics (`stage2_fixed/phase2_retina.py`) but nothing else from
`stage4_human_vision/acuity.py`. Its one free parameter (noise sigma) was locked
against an independent, non-clinical reference condition **before** this run ever
touched Wang 2009 (see `README.md` and `threshold.calibrate_noise_sigma()`).

This file reports what actually happened, run once, with no parameter changed
afterward -- regardless of which direction the result went.

## Step 1: noise-sigma calibration (done first, against the reference condition only)

Reference condition: diffraction-limited, emmetropic (M=0D), 3mm aperture
(`a_hole_um=3000`), target threshold 1.0 arcmin MAR (20/20). Full bisection log in
`outputs/sigma_calibration_log.csv`; final value in `outputs/calibrated_sigma.txt`.

```
bracket search: sigma=0.000100 -> threshold=0.0556 arcmin
bracket search: sigma=1.000000 -> threshold=13.3088 arcmin
... (12 log-space bisection steps) ...
CALIBRATED sigma=0.027415 -> reference threshold=1.0050 arcmin (target 1.0)
```

**LOCKED sigma = 0.027415.** Achieved reference threshold 1.0050 arcmin against a
target of 1.0 arcmin -- close convergence. This value is not touched again anywhere
below.

## Step 2: Wang 2009 predictions (`outputs/validation_predicted_vs_observed.csv`)

5 apertures x M=[0, 2, 5]D (matching `stage4_human_vision`'s own comparison grid),
observed values imported directly from `stage3_human_vision/literature.py`'s
`ideal_pinhole_wang_2009` entry (never copied by hand).

| M (D) | aperture (um) | observed logMAR | R7 threshold (arcmin) | R7 logMAR |
|---|---|---|---|---|
| 0 | 500  | 0.28 | 0.150 | -0.825 |
| 0 | 750  | 0.31 | 0.150 | -0.825 |
| 0 | 1000 | 1.00 | 0.835 | -0.078 |
| 0 | 1200 | 0.40 | 0.070 | -1.155 |
| 0 | 1500 | 0.50 | 0.070 | -1.155 |
| 2 | 500  | 0.28 | 0.150 | -0.825 |
| 2 | 750  | 0.31 | 0.150 | -0.825 |
| 2 | 1000 | 1.00 | 0.150 | -0.825 |
| 2 | 1200 | 0.40 | 0.070 | -1.155 |
| 2 | 1500 | 0.50 | 0.150 | -0.825 |
| 5 | 500  | 0.28 | 0.150 | -0.825 |
| 5 | 750  | 0.31 | 0.150 | -0.825 |
| 5 | 1000 | 1.00 | 0.835 | -0.078 |
| 5 | 1200 | 0.40 | 0.150 | -0.825 |
| 5 | 1500 | 0.50 | 0.150 | -0.825 |

## Step 3: regression stats (`outputs/validation_regression_stats.csv`)

In-sample and leave-one-out are identical here by construction -- no parameter is
fit to Wang 2009 (see `validation.in_sample_equals_leave_one_out_here()`'s
docstring), unlike `stage4_human_vision/calibration.py`, which fits a,b to the data
and needs LOO specifically to avoid an overfit-looking in-sample number. Both
labels are shown in the CSV; the numbers are the same.

| M (D) | predictor | n | R^2 | Pearson r | p |
|---|---|---|---|---|---|
| 0 | **R7 ideal-observer** | 5 | **-24.62** | 0.787 | 0.114 |
| 0 | closed-form (Strehl) | 5 | -3.60 | NaN\* | NaN\* |
| 0 | closed-form (VSOTF) | 5 | -3.60 | NaN\* | NaN\* |
| 2 | **R7 ideal-observer** | 5 | **-28.06** | 0.187 | 0.764 |
| 2 | closed-form (Strehl) | 5 | -723.04 | 0.253 | 0.681 |
| 2 | closed-form (VSOTF) | 5 | -23.24 | 0.435 | 0.464 |
| 5 | **R7 ideal-observer** | 5 | **-19.10** | 0.956 | **0.011** |
| 5 | closed-form (Strehl) | 5 | -883.11 | -0.083 | 0.894 |
| 5 | closed-form (VSOTF) | 5 | -203.60 | 0.157 | 0.801 |

\* At M=0D the Strehl/VSOTF closed-form predictors are numerically constant
(1.0 and 0.0 respectively) across all 5 apertures -- comparing each aperture's PSF
against its *own* diffraction-limited reference at zero defocus makes Strehl
trivially 1.0 regardless of aperture in this optics model, so there is no variance
for Pearson r to measure (undefined, reported as NaN, not a computation error).

## BOTTOM LINE

**R7 ideal-observer model: R^2 range [-28.06, -19.10], p range [0.011, 0.764]
across M=[0, 2, 5]D. DOES NOT clear the stated bar (R^2>0 AND p<0.05) at every M
tested.** This is a genuine, honest second failure -- not a bug that was chased or
patched. No parameter (sigma, NTF construction, the mar-value search range) was
changed after this result was seen.

The two closed-form cross-checks fail far more severely (R^2 as low as -883),
confirming these were correctly treated in `literature.py` as low-fidelity,
brief-specified formulas rather than a serious alternative to the Monte Carlo
model.

## Honest discussion: how this compares to stage4_human_vision, and why it likely failed

**This is not simply "the same failure again" -- it is a worse R^2, with a
different, identifiable failure signature, and that distinction matters.**

1. **Direct comparison of magnitudes.** stage4_human_vision's own numbers (RESULTS.md
   Section 2 and 4c): the raw, uncalibrated predictor scores R^2 = -6.39 to -6.68
   (p~0.50-0.51); its honestly-calibrated, leave-one-out score is R^2 = -0.544 to
   -0.590 (p=0.54-0.56), and the pooled grouped-LOO score (its single best honest
   number) is R^2=-0.566, p=0.085. R7's R^2 here (-19.1 to -28.1) is substantially
   **more negative** than either of stage4's numbers. A second model failing *more
   severely* than the first is a different, and weaker, form of evidence for
   "any model would fail on this data" than a second model failing by a
   *comparable* margin would have been -- this should be stated plainly rather than
   rounded up to "confirms the same story."

2. **The specific failure mode here is a severe, systematic optimistic bias, not
   primarily noise sensitivity to one clinical outlier.** R7's predicted logMAR
   clusters tightly around -0.83 to -1.16 for most conditions (i.e. predicting
   roughly 20/3 to 20/7 Snellen-equivalent acuity) against observed values of
   0.28-1.00 logMAR (20/38 to 20/200) -- the model predicts dramatically *better*
   acuity than was ever clinically observed, at almost every condition, regardless
   of aperture or defocus. That is why R^2 (which penalizes a constant offset
   between predicted and observed, unlike Pearson r) is so deeply negative even
   though Pearson r is positive, and for M=5D even nominally significant
   (r=0.956, p=0.011) -- the *ranking* across apertures is partly right at M=5D,
   but the *absolute scale* is off by roughly a full logMAR unit almost everywhere.

3. **A specific, checkable numerical artifact contributes to this.** Several
   entries above hit `threshold.fit_psychometric_threshold`'s optimizer bound
   exactly: e.g. `0.070` arcmin corresponds exactly to
   `10**(log10(min(MAR_SEARCH_RANGE_ARCMIN)) - 1.0) = 10**(log10(0.7)-1.0) =
   0.070`, the hard lower bound of the curve-fit's search space
   (`threshold.py`'s `bounds` argument), not a value the data actually
   constrained. This happens when the model's simulated proportion-correct is
   already at ceiling across the *entire* sampled range
   (`MAR_SEARCH_RANGE_ARCMIN = [0.7, 1.2, 2.0, 3.5, 6.0, 10.0, 17.0]` arcmin) for
   a given condition, so the psychometric fit has no data below 0.7 arcmin to
   localize a smaller true threshold and instead saturates at the bound. **This
   was noticed live, while the run was in progress, and deliberately left
   unchanged**: widening the search range now, having already seen that it
   produces bound-hits, would be exactly the kind of post-hoc tuning the brief
   explicitly prohibited, even though the intent (giving the psychometric fit
   better support) is methodological rather than result-driven. The numbers above
   are reported exactly as produced by the pre-registered search range.

4. **The more likely root cause, independent of (3): a single-point-calibrated,
   noise-limited-only ideal observer should not be expected to hold an absolute
   performance scale across very different optical conditions.** Sigma was
   locked against exactly one reference condition (3mm, emmetropic,
   diffraction-limited). Real human acuity reflects additional sources of
   inefficiency beyond pure photon/neural noise at the retina -- criterion
   variability, oculomotor and fixational noise, attentional lapses -- that this
   model does not include at all (per the brief's architecture, which specifies
   only additive Gaussian noise calibrated once). An ideal observer of this kind
   is a *best-case* bound on performance by construction; without a
   condition-independent efficiency factor scaling it down to real observer
   performance (which the brief did not call for and this project did not add),
   it will tend to predict better-than-clinical acuity broadly, exactly the
   pattern seen in (2). This is offered as this project's own analytical
   interpretation, not as a claim backed by an independently re-verified
   numeric citation for this project's specific parameter regime.

**Net honest read:** this second, structurally independent model also fails the
stated bar on the same n=5 Wang-2009 dataset, which is consistent with -- and adds
to -- the data-scarcity diagnosis (no model tested so far, across two very
different architectures, both honestly validated with no post-hoc tuning, clears
R^2>0/p<0.05 on this dataset). But it fails by a *larger* margin and with a
*different* signature (systematic optimistic bias / ceiling-saturation) than
stage4_human_vision did, most plausibly because a single-reference-calibrated,
noise-only ideal observer does not carry a valid absolute performance scale across
widely different optical conditions without an efficiency correction this model
does not include. Both explanations -- data scarcity, and architecture-specific
scale transfer -- are real and not mutually exclusive; this run does not let one be
cleanly separated from the other, and that limitation is itself part of the honest
result.

No aperture recommendation is made anywhere in this file or elsewhere in this
folder.

---

## Re-run against corrected optics: these results were never actually testing stage2_fixed/

**Everything above this line was computed against the WRONG optics module.** This
section documents why, and what happened when that was fixed.

### The bug

`R7acuity/ideal_observer.py` correctly inserts `stage2_fixed/` into `sys.path` and
does `import phase2_retina` -- but `run_validation.py`'s own top-level imports do
`from stage4_human_vision.validation import regression_stats` *first*. Importing any
`stage4_human_vision` submodule runs `stage4_human_vision/__init__.py`, which does
`from .pipeline import run_stage4_point`; `pipeline.py` (before this fix) inserted the
**deprecated** `stage2/` directory into `sys.path` and imported `phase2_retina` there.
Python caches imported modules by their bare name in `sys.modules`, so by the time
`ideal_observer.py`'s own `import phase2_retina` ran, Python found `'phase2_retina'`
already cached and silently reused the `stage2/` copy -- never re-searching `sys.path`,
never reaching `stage2_fixed/` at all.

Verified directly, not assumed: `sys.modules['phase2_retina'].__file__` resolved to
`.../stage2/phase2_retina.py` when imported in `run_validation.py`'s actual order.
`stage2/phase2_retina.py` independently confirmed to carry the identical
lens-phase/retina-propagation wavelength bug fixed in `stage2_fixed/`
(`PHYSICS_AUDIT.md` item A) -- plus, per this project's own `stage2_fixed/CHANGES.md`,
the wraparound-margin documentation issue already corrected there (that one turned out
to be comment-only, no computed value differs; the item-A wavelength bug is the one
that actually changes numbers).

**Consequence: every R^2/RMSE/Pearson number in every section above this line was
computed against `stage2/`'s retinal PSF, not `stage2_fixed/`'s.** They are preserved
above, unedited, as the honest historical record of what was actually run -- not
deleted or silently corrected.

### The fix

Fixed at the source, in `stage4_human_vision/pipeline.py` (repointed its `sys.path`
insertion at `stage2_fixed/`), not by reordering `run_validation.py`'s own imports --
reordering is fragile to whichever script happens to import things in a different
order next; fixing the actual source of the shadowed module fixes it for every caller,
including ones not yet written. Verified after the fix: `sys.modules['phase2_retina']
.__file__` now resolves to `stage2_fixed/phase2_retina.py` from `run_validation.py`'s
own import order. Full detail in `PHYSICS_AUDIT.md` and `stage4_human_vision/RESULTS.md`
(this same fix, documented from that side too).

### What happened when R7acuity was finally run against the real, corrected optics

**`calibrate_noise_sigma()` crashes.** Not "the numbers moved" -- the very first step,
which every number in this file depends on, no longer completes:

```
AssertionError: target 1.0 not bracketed by [0.05559412519746301,
0.05559412519746301] at sigma in [0.0001, 1.0] -- widen the search bracket
```

Independently characterized by direct probing (not just reading the crash trace) at
the reference condition (3mm aperture, M=0, diffraction-limited, the same condition
this project's sigma was always calibrated against):

| sigma | threshold (arcmin) | proportion correct, every tested size (0.25-4.0 arcmin) |
|---|---|---|
| 0.0001 | 0.0556 | 1.0 at all 9 sizes |
| 0.001 -- 5.0 | 0.0556 (identical) | 1.0 at all 9 sizes |
| 20.0 | 0.0251 | 1.0 at 8/9 sizes, 0.97 at one |

Across **nearly 5 orders of magnitude of noise** (sigma 0.0001 to 5.0), the model
scores perfectly at *every* tested letter size, all the way down to 0.25 arcmin (four
times finer than 20/20) -- performance only begins to degrade at sigma=20, roughly
**730x** the sigma this project had locked (0.027415). The reported threshold pins to
the search range's own lower bound (0.0556 arcmin) because the psychometric fit never
sees a proportion below 1.0 anywhere in its sampled range -- not a measured threshold,
a floor artifact.

A second, single-number illustration: the **original, never-retuned** locked
sigma=0.027415 (the exact value calibrated pre-fix, achieving 1.0050 arcmin -- ~20/20
-- against the old, buggy optics) now predicts, at the identical reference condition
against the corrected optics, a search-floor-pinned **0.0556 arcmin (~20/1)** -- an
~18x shift in predicted acuity from the optics fix alone, with the noise model
completely unchanged.

**Why this happens, physically**: item A's bug affected every aperture, not just the
small pinholes this project's own R1 sweep tested (`PHYSICS_AUDIT.md` F.3, up to +150%
optimum-aperture change at M=2D) -- and its *absolute* geometric-blur impact scales
with aperture radius, so at the reference condition's much larger 3mm aperture, the
pre-fix focal-plane error produced substantially *more* blur than at the small pinhole
apertures the R1 sweep covered. Post-fix, a 3mm aperture correctly focused is very
close to its true diffraction limit at this eye model's image distance (~22mm,
F/#~7.4) -- sharp enough that an ideal (noise-limited-only) observer reads even a
0.25-arcmin letter essentially perfectly unless the noise is pushed to an
implausible extreme.

**This crash was not worked around.** The pre-registered calibration search bracket
(`sigma in [0.0001, 1.0]`) was not widened, and no other locked parameter was
retuned, to force a number through -- per this task's explicit constraint, and because
doing so specifically *because* the corrected optics revealed the original bracket no
longer works would itself be exactly the kind of post-hoc tuning this project's
discipline has avoided throughout. **The crash, and the ceiling-performance
characterization above, is the result.** The Wang-2009 comparison this file's earlier
sections report was never re-attempted against the corrected optics, because there is
no honestly-calibrated sigma to attempt it with.

### What this means for the data-scarcity vs. architecture-scale-transfer question

The earlier sections of this file argued R7's severe over-optimism (R^2 as low as
-28.06) was "most plausibly" a single-reference-calibrated, noise-only ideal observer
not carrying a valid absolute performance scale across widely different optical
conditions (see "Honest discussion" point 4, above). **This result is direct, strong
evidence for exactly that diagnosis** -- not just plausible now, but demonstrated: the
model's noise floor, locked at one specific (previously mis-optics'd) reference
condition, does not generalize even to a *different aperture at the same M* once the
optics it was implicitly calibrated against are corrected. Whether R7's whole
architecture (single-condition noise calibration, no efficiency-style scale
correction baked into the core simulation) can ever produce a well-calibrated absolute
threshold across this project's full aperture range is now a more open question than
before, not a more settled one -- and re-deriving a new calibration procedure (e.g. a
wider or differently-anchored search, or a reference condition chosen to be less
extreme) is exactly the kind of decision that must be made deliberately and pre-
registered again, not backed into by widening a bracket until a crash stops happening.

No aperture recommendation is made anywhere in this section either.
