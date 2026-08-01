# Stage 4 Results: first end-to-end run

This is the first time `stage4_human_vision/` has been run beyond its unit tests. It
covers, in order: (1) running the pipeline end-to-end and checking it doesn't break,
(2) validating the recommended acuity predictor against real clinical data, and (3) a
full production sweep with plots. See `stage4_human_vision/CHANGES.md` for the one code
fix made along the way and the known limitations surfaced while doing this.

## 1. Running it (see CHANGES.md for full detail)

- `tests/test_stage4.py`: 7/7 pass.
- Stress sweep: 15 apertures (matching `stage3a/multi_EE_sweep.csv`) x M=1-8D (8 values)
  x scene luminance 10000/3162/1000/316/100 cd/m^2 (log-spaced), grid_N=512 -- 600
  points, **zero exceptions, zero junction-check failures, zero NaN/Inf**, and
  `solve_pupil_and_retinal_illuminance` converged in 5-9 iterations everywhere (cap is
  20). No fix was needed for this part.

## 2. Validation against clinical data: NOT statistically validated

Ran the recommended predictor (`acuity.py`'s `mtf10_vsotf_adjusted` logMAR, the
VSOTF+SNR-adjusted model DESIGN.md recommends as Stage 4's headline output) against
the same dataset Stage 3 used: `literature.get('ideal_pinhole_wang_2009')`, 5 real
clinical apertures (500/750/1000/1200/1500um), sensitivity across M=[0,2,5]D (the
paper's summary table has no per-point M, same limitation Stage 3 already documented).

| M (D) | predictor | n | R^2 | Pearson r | p-value |
|---|---|---|---|---|---|
| 0 | Stage 4 recommended | 5 | -6.39 | 0.395 | 0.510 |
| 0 | Stage 3 mtf10 (reference) | 5 | -6.68 | 0.395 | 0.510 |
| 2 | Stage 4 recommended | 5 | -4.98 | 0.393 | 0.513 |
| 5 | Stage 4 recommended | 5 | -2.84 | 0.405 | 0.499 |

**Verdict: fails the stated bar (R^2>0 and p<0.05) at every M tested.** R^2 is
strongly negative everywhere and p is 0.50-0.51 -- nowhere near significant. This is
essentially the same failure Stage 3 already reported; Stage 4's VSOTF/SNR adjustment
nudges R^2 slightly less-negative than raw MTF10 (-6.39 vs -6.68 at M=0) but does not
change the conclusion. Full numbers, including the mtf10-only and mtf50-only
sub-models for context, are in `outputs/validation_regression_stats.csv` and
`outputs/validation_predicted_vs_observed.csv`; scatter plot in
`outputs/validation_predicted_vs_observed.png`.

Checked whether the assumed scene luminance (the paper reports "15 foot-candles",
which needs an uncited target-reflectance assumption to convert to cd/m^2, so the
package's own photopic default of 10000 cd/m^2 was used instead) was load-bearing: reran
at 10/100/1000 cd/m^2 and R^2/p barely move (R^2 stays in -5.8 to -5.9, p stays ~0.44
at M=0 across that whole range). So the luminance assumption is not why this fails.

**Best read on why**, in order of how much I'd weight each:
1. **Systematic overestimate, not just weak correlation**: the scatter
   (`outputs/validation_predicted_vs_observed.png`) shows every single predicted point
   sits above the diagonal -- Stage 4 predicts worse (higher) logMAR than observed at
   every one of the 15 (aperture, M) combinations tested. That's a calibration/bias
   problem on top of whatever correlation exists, and it's a big part of why R^2 is so
   deeply negative (R^2 penalizes bias, not just correlation weakness) -- an
   uncalibrated heuristic combination (`acuity.py`'s VSOTF/SNR adjustment has no fitted
   offset or scale against real data, per DESIGN.md's own "requires empirical
   calibration" caveat) will tend to show exactly this pattern.
2. **The clinical curve itself is non-monotonic in a way no smooth optics model can
   fit with 5 points**: observed logMAR is 0.28, 0.31, **1.00**, 0.40, 0.5 at
   500/750/1000/1200/1500um -- a large spike at 1000um that reverses at 1200um. With
   only 5 points, R^2 is extremely sensitive to a single point like this, and it drags
   every candidate predictor (Stage 3's three and Stage 4's) toward the same failure
   regardless of which frequency-domain metric is used underneath.
3. **The dataset has no per-point M** (documented in `literature.py`'s own fidelity
   note) -- comparing one simulated M against subjects with a mix of real, unstated
   refractive errors adds irreducible noise no model refinement here can remove.
4. **n=5 per M is a very small sample** -- even a real, moderate correlation would
   struggle to clear p<0.05 at n=5.
5. Less likely to be the main driver, but worth naming: this is a genuine
   near-field/Fresnel diffraction regime (a physical pinhole occluder close to the
   cornea), which is further from the well-behaved far-field regime where MTF-based
   acuity prediction is usually validated in the literature Stage 4 cites.

Given (1)-(3) would sink *any* smooth predictor built from this project's optics on
this specific dataset, this reads as a dataset/task-mismatch problem more than "still
the wrong metric" -- so, per the brief, a fourth predictor was not chased.

## 3. Production sweep

Standard aperture grid (`stage3a/multi_EE_sweep.csv`'s 15 apertures) x M=1,2,3,4,5,6,8D
(matches `DEFAULT_M_VALUES` already used by the existing dashboards) x scene luminance
10000/1000/100 cd/m^2, grid_N=2048 (this project's "validated resolution", matching
`stage3_integrated`'s own precomputed grid) -- 315 points, 0 junction failures. Raw
data: `outputs/stage4_full_sweep.csv`.

### Headline finding: pinhole restriction alone crosses photopic into mesopic

This is the one genuinely new capability Stage 3 didn't have (no pupil/luminance model
at all -- "relative throughput" only). The pupil-illuminance fixed-point iteration
couples natural pupil size to the *retinal* illuminance actually delivered through the
pinhole, not to the raw scene luminance. Concretely (`equivalent_adapting_luminance_cdm2`
in the sweep CSV, M=4D column shown):

| aperture | scene 10000 cd/m^2 | scene 1000 cd/m^2 | scene 100 cd/m^2 |
|---|---|---|---|
| 75um | 1.50 cd/m^2 (mesopic) | 0.11 cd/m^2 (mesopic) | 0.010 cd/m^2 (mesopic) |
| 400um | 115.3 cd/m^2 (photopic) | 5.4 cd/m^2 (mesopic) | 0.35 cd/m^2 (mesopic) |
| 2000um | 6779 cd/m^2 (photopic) | 395 cd/m^2 (photopic) | 17.6 cd/m^2 (photopic) |

Even at the brightest scene luminance tested (10000 cd/m^2, unambiguously photopic),
a small enough pinhole (75-150um) drives the modeled equivalent adapting luminance
into the mesopic range (<~3 cd/m^2) purely through aperture restriction -- confirming
this sweep does cross photopic->mesopic, and *why* it does. Full plot:
`outputs/pupil_and_td_vs_aperture.png`.

Caveat on how to read this: the fixed-point coupling itself (`equivalent_luminance =
trolands / natural_pupil_area`, in `illuminance.py`) is a first-principles
construction, not a formula from a cited paper -- Watson & Yellott (2012) is cited for
pupil-diameter-given-luminance, not for this specific feedback definition. It is
physiologically motivated (the pupillary light reflex responds to actual retinal
flux, which a persistent pinhole genuinely reduces) but whether real pupils/retinal
adaptation state fully re-equilibrate to it within a typical clinical test's
timescale (seconds) is untested here. Read the reported "natural pupil diameter" as
"this model's self-consistent equilibrium value for continuous wear of this exact
pinhole," not "your pupil size in this room."

### Predicted logMAR's luminance-sensitivity (UPDATED in Section 4 below)

*This subsection originally reported that predicted logMAR "barely moves with
luminance" because of `acuity.py`'s old uncited `**0.05` SNR exponent. That term has
since been replaced (Section 4) with a cited additive brightness correction, and this
finding is now different -- see Section 4 for the current numbers. Left here,
struck through in spirit rather than deleted, so the history of what changed and why
stays visible.*

~~Despite the large equivalent-luminance swing above, `outputs/logmar_vs_aperture.png`
(3 luminance panels, faceted, one line per M) are visually near-identical across all
three scene luminances. This traces to `acuity.py`: the VSOTF and SNR corrections use
small exponents (`** 0.1` and `** 0.05`), so a >100x change in retinal illuminance
moves predicted logMAR by only a few percent. Pupil and illuminance respond correctly
and strongly to luminance; the final acuity number, by design, does not.~~

One unrelated, pre-existing behavior visible in the same plot: predicted logMAR
*improves* (decreases) with higher M at a fixed aperture. This comes from Stage 2/3's
existing cycles/um -> cycles/degree conversion (`cycles_per_um_to_cycles_per_degree`,
reused unchanged) -- higher myopia means a longer eye (`v_r`), so the same physical
retinal blur maps to fewer degrees of visual angle. This is inherited from the
already-validated Stage 2/3 optics chain, not introduced by Stage 4, and out of scope
to change here per the brief (Stage 2/3 folders are frozen).

### VSOTF / Strehl exceed 1.0, more so at high M

`outputs/vsotf_vs_aperture.png` shows VSOTF reaching ~3.7 at M=8D. This is the same
already-documented Fresnel near-field oscillation finding called out elsewhere in the
project (`stage_v1_simulator`'s Live Explorer tab, `stage3_integrated/README.md`), not
new to Stage 4 -- just more visible here because VSOTF amplifies whatever the
underlying OTF ratio does. Not fixed, per the same reasoning as those existing notes.

### Pareto fronts (M=1,4,8D)

`outputs/pareto_front_M{1,4,8}.png` use the full 4-objective vector DESIGN.md
specifies (minimize RMS blur, maximize Td, maximize VSOTF, minimize logMAR),
plotted on blur/Td axes. Two things worth knowing before reading them:

- The fronts look jagged/non-monotonic in the blur-Td plane. That's expected and
  correct: a point can be non-dominated on the full 4-objective vector (e.g. it wins
  on VSOTF or logMAR) even if it's not optimal in the 2D blur/Td projection shown.
  This is not a plotting bug -- it's what a true multi-objective front looks like
  projected onto two of its four axes.
- The front is close to luminance-invariant: nearly the same set of apertures is
  non-dominated at 10000/1000/100 cd/m^2, with the whole front shifted up or down by
  roughly the luminance ratio. This falls out of Td being proportional to
  `scene_luminance x stop_area`, and the stop being the aperture (not the natural
  pupil) at every tested point except the very largest aperture / brightest scene
  corner. In other words: at this Stage, scene brightness changes *how much* light
  reaches the retina, but doesn't reshuffle *which aperture* is Pareto-preferred.

### CSF-weighted MTF

`outputs/csf_weighted_mtf_vs_aperture.png`: a real, modest luminance dependence via
Barten (peak weighted-MTF area drops from ~2650 at 10000 cd/m^2 to ~2350 at 100 cd/m^2
at the M=8D optimum) -- smaller than the pupil/Td swing but a genuine coupling, unlike
VSOTF/logMAR above.

## 4. Second pass: literature search, a cited brightness correction, and an honest calibration attempt

Section 2 found the acuity predictor fails validation and traced the root cause (in
`acuity.py`/`photon_noise.py` directly) to two things: no calibration step anywhere,
and only n=5 real clinical points (no per-subject M) to calibrate against. This
section searched for more data, replaced the worst-offending uncited term, and then
tried -- carefully, honestly -- to calibrate against what's actually available.

### 4a. Literature search results

Full citation entries with verification notes are in the new
`stage4_human_vision/literature.py`. Summary:

- **Additional pinhole-aperture-vs-acuity datasets beyond Wang 2009**: found two real
  ones. Kim et al. (2017, J Korean Med Sci, N=36) tested a single 900um pinhole and
  reported mean logMAR=0.20+/-0.21 at a mean spherical equivalent of -2.7+/-2.3D
  (group aggregate, not per-subject) -- **usable** as one additional real anchor point,
  used below as a genuine external check. Abdul et al. (2009, S Afr Optom, N=4
  children) tested 1.5mm/2mm pinholes at near, under two lighting levels, and their
  own conclusion was that pinhole size "did not alter the results sufficiently" --
  **not usable** for calibrating an aperture-dependence this project cares about (near
  vision in accommodating children, M-notation not logMAR, and ~zero aperture-size
  signal in their own data). A third lead (a NeuroQuantology 2022 paper) was read in
  full and **rejected**: an earlier web-search summary claimed it reported specific
  logMAR-vs-diopter numbers, but the actual paper contains no such data at all --
  flagged in `literature.py` specifically so this dead end isn't re-discovered later.
- **Brightness-acuity slope**: Tidbury, Czanner & Newsham (2016) verified directly
  (full text) -- 0.060 logMAR per log10(illuminance), p<0.001, N=28, steepening with
  myopia. Sheedy, Bailey & Raasch (1984) corroborates (~0.0664 logMAR/decade, derived
  from their "one letter per doubling of luminance" finding) but could only be
  partially verified (paywalled, no PMC copy; consistent secondary sourcing only).
- **Plateau/knee**: Van Nes & Bouman (1967) verified directly against the primary
  abstract -- exactly the "~300 td Weber-onset knee" the task described: threshold
  modulation is illuminance-independent above 300 td, and scales as td^-0.5 below it.
  Rabin (1994)'s citation and DOI were confirmed and one concrete data point
  corroborated via secondary source (116->0.23 cd/m^2 gives 3x VA loss, consistent
  with an accelerating/plateau-then-drop shape), but the exact "~20/20 from 100 to 1
  cd/m^2" framing could not be independently verified against the (paywalled) primary
  text -- treated as a reasonable approximation of the same shape, not a confirmed
  number.

### 4b. The brightness correction (replaces the old uncited SNR term)

`acuity.py`'s `**0.05` SNR exponent (scaled predicted MAR as luminance^0.0125 -- a
~6% effect across the whole tested range) is replaced by an additive logMAR
correction, applied in log space per the cited studies' own units:

```
correction = 0 if Td >= 300
           = 0.060 * log10(300 / Td) if Td < 300
```

Old term preserved unchanged as `logmar_vsotf_snr_legacy` (not deleted). Effect size,
a_hole=400um/M=4D (the M=4D optimum aperture): recommended logMAR moves from 0.414
(10000 cd/m^2, Td=1257) to 0.497 (100 cd/m^2, Td=12.6) -- a real ~0.08 logMAR
brightness effect, versus the legacy term's 0.399 to 0.403 (~0.004, essentially flat).
This is a real, cited, and directionally-correct improvement, but see 4d below for
why it did not fix the validation failure -- the fix targeted the wrong-sized problem
relative to the actual gap between predicted and observed values.

Because the knee is at 300 td (not a low scene-luminance value), and Td depends on
aperture area too, the correction is visible mainly at small-to-mid apertures where
Td dips below 300 even at bright scene luminance, and negligible at large apertures
where Td stays above 300 at every luminance tested (see updated
`outputs/logmar_vs_aperture.png` -- look closely at apertures <~900um across the
three luminance panels, rather than expecting a uniform shift across the whole plot).

### 4c. Calibration attempt: honestly, it does not validate

Fit `logmar_calibrated = a*logmar_recommended + b` against Wang 2009's 5 apertures
(sensitivity across M=0,2,5D, matching Section 2's setup). Per the brief, this used
**leave-one-out cross-validation**, not an in-sample fit-and-score, because n=5 would
trivially overfit:

| M (D) | kind | R^2 | Pearson r | p |
|---|---|---|---|---|
| 0 | in-sample (fit on all 5, scored on same 5) | 0.156 | 0.395 | 0.510 |
| 0 | **leave-one-out (honest)** | **-0.586** | **-0.352** | 0.562 |
| 2 | in-sample | 0.154 | 0.393 | 0.513 |
| 2 | **leave-one-out (honest)** | **-0.590** | **-0.372** | 0.537 |
| 5 | in-sample | 0.164 | 0.405 | 0.499 |
| 5 | **leave-one-out (honest)** | **-0.544** | **-0.353** | 0.560 |
| pooled (5 apertures x 3 M, grouped by aperture) | in-sample | 0.132 | 0.364 | 0.183 |
| pooled | **grouped leave-one-out (honest, this is the deployed fit's real score)** | **-0.566** | **-0.460** | **0.085** |

(Full numbers: `outputs/calibration_per_M_stats.csv`, `outputs/calibration_pooled_stats.csv`.)

The in-sample R^2 looks deceptively reasonable (0.13-0.16) -- exactly the overfitting
trap the brief warned about. The honest leave-one-out R^2 is **negative** in every
case, and the Pearson r even **flips sign** under leave-one-out (from ~+0.39 in-sample
to ~-0.35 to -0.46 held-out) -- a clear sign the fitted line itself is not stable with
a sample this small; which 4-of-5 points you fit on changes the answer's direction,
not just its magnitude.

**External check** (Kim et al. 2017, the one additional real anchor from 4a, used as
a genuine held-out test rather than more within-sample cross-validation, per the
brief): the pooled calibration (fit on all 15 Wang-2009 points, a=0.409, b=0.059)
predicts logMAR=0.499 at 900um/M=2.7D; Kim et al. report 0.20+/-0.21. Residual +0.30
logMAR, **outside 1 SD** of the observed value. This independently confirms the
leave-one-out result: the calibration does not generalize past the sample it was
built from.

**Verdict, using the exact stated bar (R^2>0 AND p<0.05 on held-out data): FAILS.**
Every held-out evaluation is R^2<0; the best p-value achieved (pooled grouped LOO,
p=0.085) is still not below 0.05. Per the brief, this was fit once and not tuned
further afterward.

### 4d. All predictors, side by side (M=0D shown; full table in `outputs/validation_regression_stats.csv`)

| predictor | R^2 (in-sample) | Pearson r | p |
|---|---|---|---|
| logmar_mtf10 (Stage 3-equivalent) | -6.68 | 0.395 | 0.510 |
| logmar_mtf50 (Stage 3-equivalent) | -11.72 | 0.375 | 0.534 |
| logmar_vsotf_snr_legacy (old Stage 4, pre-fix) | -6.39 | 0.395 | 0.510 |
| logmar_recommended (new Stage 4, brightness-corrected) | -6.68 | 0.395 | 0.510 |
| logmar_calibrated (new Stage 4 + linear calibration, **in-sample only**) | 0.124 | 0.395 | 0.510 |

The `logmar_calibrated` row's R^2=0.124 in this table is the misleading in-sample
number -- included here only so the file has all five predictors in one place. The
number that actually matters is 4c's leave-one-out result (R^2=-0.566, p=0.085,
FAILS). `logmar_recommended`'s R^2/p are numerically identical to `logmar_mtf10`'s at
M=0D here specifically because Td=1963-17671 stays above the 300 td knee at every
Wang-2009 aperture under the 10000 cd/m^2 assumption used for this table (so the
brightness correction contributes zero at these specific points) -- this is not a
bug, see 4b.

### 4e. Best honest read, updated

Section 2's list of reasons still holds (systematic overestimate, a non-monotonic
5-point clinical curve, no per-subject M, n=5, near-field task mismatch). What 4a-4c
add: this is not simply "the SNR term was uncited, fix it and it validates" -- fixing
that term with a properly-cited replacement (4b) made a real, defensible, directionally-
correct change to the model, and a subsequent honest calibration attempt (4c) still
fails cleanly on held-out data, independently corroborated by a genuine external
data point. That strengthens, rather than weakens, the Section 2 conclusion: the
gap between this model and the one real usable clinical dataset is not primarily a
miscalibrated constant that a linear correction can absorb -- it is dominated by
sample size (n=5), the clinical curve's own non-monotonicity, and missing per-subject
refractive data, none of which more model-side tuning can fix.

**Honest final conclusion: this cannot be properly validated with the clinical data
currently available publicly.** More/better real data (a modern replication of Wang
2009 with per-subject refraction across a real aperture sweep, at N>>5) is what this
needs, not a fourth predictor or a differently-parametrized calibration term.

## How much to trust this

The optics, pupil, illuminance, and photon-noise layers are internally consistent,
converge cleanly, and (Section 3) produce a new, real capability (photopic->mesopic
crossing) Stage 3 never had. Section 4b's brightness correction is a real, cited
improvement to how the model behaves, and is now visible in the sweep (small-to-mid
apertures, `outputs/logmar_vs_aperture.png`). But per Sections 2 and 4, **the final
predicted-acuity number -- with or without the Section 4c calibration -- has no
statistically significant grounding against real clinical data on held-out
evaluation**. Read the sweep's blur/Td/VSOTF outputs as internally-consistent
relative comparisons; do not read the logMAR/Snellen numbers (recommended,
legacy, OR calibrated) as clinically predictive. This caveat is carried into the
dashboard as a permanent, visible note next to the acuity readout, not just left in
this file -- and per Section 4c's result, that note's honest-failure wording was
kept as-is, not replaced with a success message.
