# Stage 4 Design: Human Vision and Visual Performance Module

## Status

This document is a design-review gate for Stage 4. No Stage 4 implementation should begin until this design is reviewed.

Scope rule: Stage 4 starts **after** the Stage 2 retinal PSF and encircled-energy outputs. The validated optical propagation chain remains unchanged:

Scene -> Pinhole aperture -> ASM propagation -> Cornea -> Eye lens -> ASM propagation -> Retina -> Retinal PSF -> **Stage 4**

## Why Stage 4 is Needed

The current repo already computes retinal optical image quality, and `stage3_human_vision` adds a first pass at human-vision metrics. However, several Stage 3 components are explicitly approximate:

- retinal illuminance assumes the pinhole itself is the effective pupil stop
- pupil size is fixed rather than physiology-driven
- CSF models are simplified peak-matched curves rather than full physiological models
- VSOTF is approximate rather than literature-faithful
- acuity prediction is mainly thresholded from MTF
- adaptation and uncertainty analysis are incomplete

That is enough for exploratory analysis, but not enough for a defensible biological-vision layer. Stage 4 upgrades those approximations into a modular, cited, validation-oriented layer.

## Design Goals

- Preserve the validated optics pipeline and all existing Stage 2 outputs.
- Keep every biological module independently enableable.
- Replace heuristic constants with cited configuration values.
- Separate first-principles optics from physiological models.
- Make every approximation explicit.
- Support validation, uncertainty propagation, and multi-objective optimization.

## Proposed Architecture

Create a new package `stage4_human_vision/` rather than rewriting `stage3_human_vision/`. Stage 3 can remain as a benchmark and fallback.

```text
stage4_human_vision/
  DESIGN.md
  __init__.py
  config.py
  constants.yaml
  types.py
  pipeline.py
  pupil.py
  illuminance.py
  adaptation.py
  optical_quality.py
  csf.py
  visual_strehl.py
  photon_noise.py
  acuity.py
  optimize.py
  validation.py
  sensitivity.py
  datasets.py
  citations.py
  tests/
```

### Interface Boundary

Stage 4 should consume a typed `RetinalOpticsResult` generated from the existing Stage 2 pipeline:

- retinal PSF / retinal intensity image
- pixel pitch at retina
- wavelength
- aperture diameter
- aperture-eye distance
- myopia / retina position metadata
- encircled energy outputs already computed upstream

Stage 4 should return a typed `VisualPerformanceResult` containing:

- retinal illuminance in photopic/mesopic/scotopic Td
- pupil diameter and area
- RMS spot radius
- Strehl ratio
- OTF / MTF / MTF50
- CSF and CSF-weighted MTF
- VSOTF
- photon flux and SNR
- MAR / logMAR / Snellen predictions
- validation metadata
- uncertainty metadata

## Module-by-Module Design

### 1. Retinal Illuminance

Why needed:
The current brightness percentage is not physiologically meaningful. Trolands are the standard bridge from scene luminance and pupil state to retinal light level.

Chosen model:
- retinal illuminance in trolands: `Td = L * A_pupil_mm2`
- support photopic and scotopic trolands directly
- support mesopic by carrying both photopic and scotopic luminance channels and deferring the mesopic interpretation to the downstream CSF/adaptation model

Primary sources:
- Illuminating Engineering Society definition of troland
- Wyszecki and Stiles conventions as referenced by Psychtoolbox radiometric conversions

Alternatives considered:
- continue using relative throughput only
- use retinal irradiance only in W/m^2 without a troland representation

Why this model:
- standard in vision science
- directly connects to pupil physiology and adaptation
- comparable to literature on acuity and contrast sensitivity vs retinal illuminance

Limitations:
- trolands are a conventional retinal illuminance measure, not full retinal irradiance
- do not automatically include ocular media transmission or Stiles-Crawford apodization
- mesopic vision is not captured by a single scalar as cleanly as photopic/scotopic

Validation:
- unit tests on dimensional consistency
- compare against known Td examples from standard definitions
- cross-check photometric Td against radiometric retinal irradiance conversion at 555 nm

Expected impact on optimum aperture:
- larger apertures gain importance under low luminance because visual performance becomes illumination-limited sooner

### 2. Pupil Model

Why needed:
Using the pinhole diameter as the effective pupil ignores the natural pupil state and removes a key physiological feedback loop between luminance and retinal illuminance.

Chosen model:
- Watson-Yellott unified pupil model for light-adapted pupil diameter
- inputs: adapting luminance, age, field size, monocular/binocular condition
- output: natural pupil diameter
- effective entrance pupil for retinal illuminance becomes `min(natural pupil, pinhole aperture)` only if the geometry truly makes the pinhole the limiting stop; otherwise the model should explicitly carry both
- fixed-point iteration between pupil diameter and retinal illuminance until convergence

Primary source:
- Watson and Yellott (2012), "A unified formula for light-adapted pupil size"

Alternatives considered:
- Moon-Spencer
- De Groot-Gebhard
- Stanley-Smith

Why this model:
- modern unification of major historical pupil formulas
- explicitly includes age, field size, and binocular state
- widely cited and purpose-built for luminance-dependent pupil prediction

Limitations:
- light-adapted model, not a full transient pupillary dynamics model
- requires an operational definition of adapting field luminance
- interaction with a near-eye pinhole stop must be documented carefully

Validation:
- reproduce literature curves across luminance, age, and field size
- verify numerical convergence of pupil-illuminance iteration
- compare predicted pupil sizes against values reported in Watson-Yellott figures

Expected impact on optimum aperture:
- modest under bright photopic conditions where the natural pupil is already small
- larger under mesopic conditions because pupil dilation increases the relative throughput penalty of a small pinhole

### 3. Neural Brightness Adaptation

Why needed:
Retinal illuminance alone does not equal perceived brightness. A separate adaptation stage is needed if the output claims perceptual image quality.

Chosen model:
- optional Naka-Rushton adaptation layer
- response form: `R = R_max * I^n / (I^n + I_50^n)`
- adaptation state carried through a luminance-dependent semi-saturation parameter
- this module affects perceptual brightness reporting and can optionally inform CSF regime selection

Primary sources:
- Naka-Rushton family of adaptation models
- Hood and Finkelstein review framework for light adaptation

Alternatives considered:
- no brightness adaptation layer
- pure Weber-Fechner mapping
- histogram-based image adaptation heuristics

Why this model:
- canonical model for early visual response saturation and adaptation
- parameterized, interpretable, and common across retinal physiology literature

Limitations:
- not a full spatiotemporal retinal adaptation model
- parameters vary by experiment and retinal locus
- should not be overclaimed as a full perceptual brightness predictor

Validation:
- reproduce qualitative saturation and gain-shift behavior across luminance
- sensitivity-test parameter ranges from cited literature
- ensure disabling the module yields identical upstream optical metrics

Expected impact on optimum aperture:
- mainly affects perceptual brightness metrics and mesopic tradeoff interpretation, not optical blur directly

### 4. Optical Quality Metrics

Why needed:
RMS spot radius, Strehl, OTF, and MTF are the bridge from wave optics to downstream neural weighting.

Chosen model:
- reuse current Stage 3 Fourier-optics definitions where already exact
- keep RMS spot radius
- keep MTF / OTF from normalized FFT of the PSF
- keep MTF50
- retain Strehl but classify it as potentially ill-posed in the near-field regime unless a defensible diffraction-limited reference is defined

Alternatives considered:
- replace Strehl completely
- move to wavefront-aberration-derived metrics only

Why this model:
- these metrics are already present and mostly first-principles
- they need stabilization and documentation, not reinvention

Limitations:
- Strehl depends on the chosen reference PSF
- radial averaging may hide anisotropy if future models introduce it

Validation:
- analytic checks with synthetic Gaussian and Airy-like PSFs
- energy conservation and OTF(0)=1 tests
- regression checks against existing Stage 3 outputs

Expected impact on optimum aperture:
- little change for RMS and MTF
- Strehl may remain unstable and should not dominate optimization unless validated

### 5. Contrast Sensitivity

Why needed:
Raw optical MTF is not visual performance. Human observers weight spatial frequencies non-uniformly.

Chosen model:
- implement three CSF families:
  - Mannos-Sakrison for legacy image-quality comparison
  - Watson-style analytical CSF as a lightweight baseline
  - Barten 1999 as the primary recommended physiological model
- Barten should be the recommended default because it includes luminance dependence and is the most physiologically grounded of the requested candidates
- output raw CSF, peak sensitivity, and cutoff frequency
- compute CSF-weighted MTF by multiplying retinal MTF by neural CSF on a shared cycles/degree axis

Primary sources:
- Barten (1999)
- Mannos and Sakrison (1974)
- Watson analytical CSF references as available during implementation review

Alternatives considered:
- keep Stage 3 peak-matched heuristic CSFs

Why this model:
- Barten is the best fit to the brief's "accepted physiological model" requirement
- the other two models are useful comparison baselines because they are common in engineering image-quality literature

Limitations:
- Barten requires physiological parameters that must be documented and configured
- CSF models depend on luminance, field size, temporal assumptions, and task

Validation:
- reproduce published CSF curve shapes and peak shifts with luminance
- compare predicted cutoff frequency against known photopic ranges
- benchmark each implemented CSF against sampled literature curves

Expected impact on optimum aperture:
- likely shifts the optimum upward relative to pure blur minimization because tiny apertures preserve some high-frequency contrast optically but starve the visual system of luminance

### 6. Visual Strehl

Why needed:
VSOTF is a more defensible visual quality metric than optical Strehl because it weights the OTF by neural sensitivity.

Chosen model:
- implement VSOTF using the literature definition based on the real part of the OTF and a neural weighting function derived from the CSF
- normalize against an explicitly defined diffraction-limited reference for the same pupil and sampling conditions
- default weighting should use the selected CSF model, with Barten-based weighting preferred

Primary source:
- Iskander (2006), computational aspects of the visual Strehl ratio
- Thibos and related VSX / VSOTF literature

Alternatives considered:
- keep the current approximate Stage 3 VSOTF
- use MTF-magnitude weighting instead of real OTF weighting

Why this model:
- closest to a clinically used optical-plus-neural metric
- directly useful for optimization

Limitations:
- reference definition remains important in this near-field regime
- 1D radial VSOTF is an approximation to the full 2D formulation

Validation:
- verify reduction to 1.0 for matched reference optics
- compare trends against published VSOTF sensitivity to defocus where feasible
- regression-test against Stage 3 approximate VSOTF with documented expected differences

Expected impact on optimum aperture:
- likely more stable than plain Strehl and more conservative than MTF50 alone

### 7. Photon Noise

Why needed:
At small apertures, performance may be photon-limited rather than blur-limited.

Chosen model:
- convert retinal irradiance to photon flux
- estimate expected photon count over configurable retinal integration area and exposure time
- Poisson shot noise: `sigma = sqrt(N)`
- SNR: `N / sqrt(N) = sqrt(N)` for shot-noise-limited counting

Primary sources:
- Rose / DeVries photon-noise scaling
- ideal-observer retinal signal-quality literature

Alternatives considered:
- keep only relative `sqrt(flux)` scaling

Why this model:
- physically grounded
- directly tied to luminance and aperture
- makes integration-area and exposure-time assumptions explicit

Limitations:
- does not include neural noise, eye motion, or detector inefficiency unless added later
- absolute SNR depends on assumed integration aperture, exposure time, and quantum efficiency

Validation:
- dimensional tests
- verify Poisson scaling numerically
- compare order-of-magnitude retinal photon rates against textbook ranges

Expected impact on optimum aperture:
- pushes the optimum toward larger apertures in dim scenes

### 8. Visual Acuity Prediction

Why needed:
The project needs a human-performance output, not only optics metrics.

Chosen model:
- support multiple predictors, but recommend a calibrated logMAR model driven by CSF-weighted optical quality
- keep exact conversions among MAR, logMAR, and Snellen
- candidate predictors to compare:
  - MTF cutoff to MAR
  - VSOTF-to-logMAR regression
  - blur-angle / core-width model
- implementation should report confidence intervals using bootstrap uncertainty from parameter and scene-condition variation

Primary sources:
- visual acuity conversion identities
- VSOTF and defocus-acuity correlation literature
- published pinhole-acuity datasets already used in the repo plus additional datasets identified during implementation

Alternatives considered:
- MTF50-only acuity
- FWHM-only acuity

Why this model:
- the brief asks for the most defensible model, which implies comparison rather than assumption
- VSOTF-based or CSF-weighted predictors are more biologically plausible than raw MTF thresholds

Limitations:
- any acuity mapping beyond geometric conversions requires empirical calibration
- calibration quality depends on dataset compatibility with this simulation

Validation:
- compare predictors using RMSE, MAE, R^2, and Pearson correlation against literature datasets
- keep a sensitivity table across myopia levels and luminance conditions
- choose default predictor only after comparative validation

Expected impact on optimum aperture:
- likely broadens the optimum into a performance plateau rather than a single sharp minimum

### 9. Multi-Objective Optimization

Why needed:
The present `blur + brightness` framing is too narrow for human performance.

Chosen model:
- objective vector:
  - minimize blur metric
  - maximize retinal illuminance
  - maximize CSF-weighted transfer or VSOTF
  - minimize predicted logMAR
- use Pareto-front analysis rather than scalarized weighting by default
- support user-defined scalar utility only as an optional post-analysis layer

Alternatives considered:
- weighted-sum objective only

Why this model:
- avoids baking subjective priorities into the optimizer
- better matches the pinhole tradeoff structure already observed in the repo

Limitations:
- front interpretation still depends on operating condition
- objective correlations may make the front narrow in some regimes

Validation:
- compare Stage 2 blur-only optima, Stage 3 Pareto fronts, and Stage 4 fronts
- ensure fronts move plausibly with luminance and myopia

Expected impact on optimum aperture:
- likely shows that optimum aperture is condition-dependent rather than unique

### 10. Validation

Why needed:
The brief explicitly requires benchmarked agreement statistics and plots.

Chosen strategy:
- validate each module separately where possible, then validate the full chain

Target validation sets:
- retinal illuminance: standards-based consistency checks and radiometric cross-checks
- pupil: Watson-Yellott reproduced curves
- CSF: Barten / Mannos-Sakrison reference curves
- acuity: published pinhole-acuity datasets including the Wang "Ideal Pinhole" dataset already referenced in the repo
- contrast threshold: Blackwell 1946 as a contextual threshold benchmark, with careful task-mismatch caveats
- pinhole optics: existing repo comparisons plus external pinhole diameter / acuity studies

Reported statistics:
- RMSE
- MAE
- R^2
- Pearson correlation

Plots:
- predicted vs observed acuity
- predicted vs observed contrast sensitivity
- pupil diameter vs luminance
- CSF overlay plots
- Pareto fronts

Limitations:
- not all literature tasks match the simulated task exactly
- some validations will remain trend-validations rather than strict pointwise validations

Expected impact on optimum aperture:
- validation should narrow which metrics are trustworthy enough to influence the recommended design diameter

### 11. Sensitivity Analysis

Why needed:
The optimum is unlikely to be robust to luminance, pupil, myopia, and geometry. The brief explicitly asks for uncertainty estimates.

Chosen method:
- one-at-a-time local sensitivity
- Latin-hypercube or Monte Carlo global sensitivity for key uncertain physiological parameters
- report confidence bands on predicted acuity and Pareto fronts

Input dimensions:
- wavelength
- natural pupil size / age / field size
- myopia
- aperture diameter
- aperture-eye distance
- scene luminance
- ocular transmission
- CSF model parameters
- adaptation parameters

Outputs:
- normalized sensitivity coefficients
- uncertainty intervals
- rank ordering of dominant contributors

Validation:
- convergence tests on Monte Carlo uncertainty estimates
- reproducibility tests with fixed random seeds

Expected impact on optimum aperture:
- likely shows scene luminance and myopia as dominant drivers, with wavelength secondary and pupil/age condition-dependent

## Recommended Defaults

These should become configurable, not hardcoded:

- pupil model: Watson-Yellott
- CSF model: Barten 1999
- visual metric for optimization: VSOTF plus predicted logMAR, with RMS spot radius retained as an optical comparator
- brightness adaptation: Naka-Rushton, disabled by default until validated
- shot-noise model: enabled, with configurable exposure time and integration area

## Implementation Strategy

1. Add `stage4_human_vision/` as a new package.
2. Introduce typed result objects and `constants.yaml`.
3. Port stable first-principles optics metrics from Stage 3 with regression tests.
4. Implement pupil and illuminance together because they are coupled.
5. Implement CSF and VSOTF together on a shared frequency axis.
6. Implement photon noise and acuity prediction after luminance handling is stable.
7. Add validation harnesses and only then enable multi-objective optimization.

## Test Plan

- unit tests for all pure functions
- regression tests against Stage 2 and stable Stage 3 outputs
- numerical-stability tests for FFT-derived metrics
- convergence tests for pupil-illuminance iteration
- validation-statistic smoke tests on packaged datasets

## Key Risks

- The near-field nature of the retinal PSF may keep classical Strehl fragile.
- A literature-faithful Barten implementation requires careful parameter bookkeeping.
- Absolute acuity prediction will remain dataset-limited unless enough compatible experimental data are assembled.
- Mesopic handling is more complex than simply interpolating between photopic and scotopic scalars.

## Design Decision Summary

- Build Stage 4 as a new package layered on top of Stage 2, not by rewriting Stage 3.
- Upgrade approximations only where the literature support is strong enough to justify the added complexity.
- Use Watson-Yellott for pupil size, Barten for CSF, Naka-Rushton for optional adaptation, and VSOTF as the primary optical-neural metric candidate.
- Preserve alternative models for comparison instead of forcing a single winner before validation.

## Sources to Anchor the Implementation Review

- Watson, A. B., and Yellott, J. I. (2012). A unified formula for light-adapted pupil size. DOI: 10.1167/12.10.12.
- Illuminating Engineering Society. Troland definition.
- Barten, P. G. J. (1999). Contrast Sensitivity of the Human Eye and Its Effects on Image Quality.
- Mannos, J. L., and Sakrison, D. J. (1974). The effects of a visual fidelity criterion on the encoding of images.
- Iskander, D. R. (2006). Computational Aspects of the Visual Strehl Ratio. DOI: 10.1097/01.opx.0000195563.82891.3b.
- Blackwell, H. R. (1946). Contrast Thresholds of the Human Eye. DOI: 10.1364/JOSA.36.000624.
- Rose / DeVries photon-noise and threshold-scaling literature.

## Review Questions

1. Should Stage 4 be implemented as a new `stage4_human_vision` package, leaving `stage3_human_vision` frozen for comparison?
2. Is Barten acceptable as the default CSF, with Mannos-Sakrison and Watson retained only as comparison models?
3. Should the brightness-adaptation layer remain optional and disabled by default until full validation is added?
4. Should VSOTF and predicted logMAR be the primary optimization metrics, with RMS spot radius retained only as an optical reference?
