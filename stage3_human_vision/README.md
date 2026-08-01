# Phase 3 -- Human Vision Constrained Optimization of Pinhole Glasses

Extends Stage 1/Stage 2 with human-vision-constrained optimization: new optical
metrics (RMS radius, Strehl, MTF), a photometric chain (scene luminance -> retinal
illuminance -> photon flux), contrast-sensitivity/visual-acuity models, and a
multi-objective Pareto analysis -- investigating, rather than assuming, why Stage 2's
pure-blur optimum (300-450 um) differs from published/commercial pinhole designs
(800-1200 um).

**Does not modify Stage 1 or Stage 2.** Imports both only through their own public
modules (`stage1_v2/physics.py`, `stage2/phase2_retina.py`, `stage2/pipeline_junction.py`,
`stage2/myopia_axial.py`) -- no physics is reimplemented anywhere in this folder.

```
stage3_human_vision/
  literature.py        # citation database -- every equation traces here
  metrics.py            # RMS radius, FWHM, Strehl, OTF/PTF, MTF50/10, Airy diameter, F#, throughput
  photometry.py         # scene luminance -> retinal irradiance -> photon flux
  contrast.py           # CSF models, Weber contrast, Rose-DeVries
  visual_acuity.py      # MTF-cutoff acuity (MAR/Snellen/LogMAR), visual-Strehl (VSOTF, approx.), SNR bound
  pareto.py              # Pareto-dominance + rank-correlation utilities
  validation.py          # Stage2-only vs. Phase3 optima, clinical-range comparison
  validation_stats.py    # RMSE/MAE/R^2/Pearson r -- generic regression-agreement statistics
  comparison.py          # "which metric correlates best with experiment" + error budget
  run_metrics_sweep.py   # the PSF-level sweep (105 points, see below)
  run_stage3.py           # orchestrator -- run this
  validate_against_literature.py  # RMSE/MAE/R^2/Pearson vs. a published multi-point dataset
  README.md
  outputs/
```

## Headline finding

**The blur metric you choose determines whether the numerical optimum lands near
commercial designs or nowhere close to them -- and this project can now show which
metric does which, not just assert it.**

| Candidate metric | mean optimum | mean gap from clinical range (940-1750um) | fraction of M values landing inside it |
|---|---|---|---|
| minimize r_EE(80%) | 429 um | 511 um | 0% |
| minimize r_EE(50%) | 343 um | 597 um | 0% |
| **minimize RMS spot radius** | **964 um** | **54 um** | **71%** |
| maximize Strehl ratio | 1000 um | 189 um | 57% (but unstable -- see below) |
| maximize MTF50 | 329 um | 611 um | 0% |
| maximize throughput alone | 2000 um | 250 um | 0% (trivial -- always picks the largest tested aperture) |

Every "sharpest possible core" metric (r_EE, MTF50) pushes toward 300-500 um and never
lands inside the clinical/commercial range across any tested myopia level.
**RMS spot radius is the one candidate metric whose single-objective optimum tracks
real-world designs closely** (mean gap only 54 um, inside the range for 5 of 7 tested
M values) -- see `outputs/optimum_vs_myopia_by_metric.png`. This traces to a concrete,
checkable mechanism: RMS radius weights intensity by `r^2`, so it penalizes the broad,
faint Fresnel-ring energy that small apertures spread far from center much more
heavily than a percentile-energy metric (r_EE) does, pushing its optimum toward larger
apertures where less energy sits in those distant skirts.

This does **not** prove RMS radius is "the" correct design criterion -- it is reported
as the empirical correlation actually found, with the mechanism behind it identified,
per the brief's explicit instruction not to force or assume agreement.

## Finding: Strehl ratio is ill-posed in this regime (confirmed by direct test, not assumed)

Both reference handbooks list Strehl ratio as a candidate optimization metric. Before
using it, its own defining assumption was tested directly: is there a single,
well-behaved "best focus" plane this system converges toward? **No.** A direct scan of
peak retinal intensity vs. propagation distance `v_r` (holding aperture fixed at 750um)
found:

```
v_r=23mm: peak=76.1     v_r=27mm: peak=456.0     v_r=29mm: peak=1239.5     v_r=33mm: peak=304.3
```

Peak intensity is **oscillatory**, not single-peaked -- the same near-field Fresnel
physics as Stage 1's own on-axis formula `I(0,z) = 4*I0*sin^2(pi*N_F/2)`. Consequently,
using this system's own zero-defocus (M=0) condition as the conventional
"diffraction-limited reference" for a Strehl ratio can make the ACTUAL (defocused) PSF
look sharper than the "ideal" one -- **Strehl ratio exceeds 1.0 for 58 of 105 tested
configurations (55%)** in the sweep (`outputs/metrics_sweep.csv`,
`strehl_exceeds_unity` column). This is flagged everywhere it's computed
(`metrics.py::strehl_ratio` docstring), not hidden, and is why Strehl's entry in the
table above is annotated "unstable": its optimum bounces between 500um and 1750um
across adjacent myopia levels (`outputs/optimum_vs_myopia_by_metric.png`) rather than
moving smoothly, exactly as expected for a metric built on an ill-posed reference.
**Practical conclusion: prefer RMS radius or r_EE(P) over Strehl ratio for this
specific pinhole-eye system.**

## Photometry

`photometry.py` implements scene luminance -> radiance -> retinal irradiance (via the
standard image-irradiance/F-number relation `E = pi*N*tau/(4*F#^2)`, which is the
radiometric form of the troland relationship) -> photon flux density, plus the direct
`relative_retinal_illuminance = (a_hole/D_pupil)^2` result restated from
`metrics.throughput_area_ratio`. Verified to scale exactly with aperture AREA (a 3x
diameter increase gave exactly 9x irradiance, confirmed numerically) -- satisfying the
brief's explicit "do not assume constant illumination" requirement. At M=4D:

| a_hole | relative illuminance vs. natural 4mm pupil | retinal photon flux density |
|---|---|---|
| 400 um | 1.0% | 8.1e15 /s/m^2 |
| 1200 um | 9.0% | 7.3e16 /s/m^2 |
| 2000 um | 25.0% | 2.0e17 /s/m^2 |

A 400um pinhole (near the pure-blur optimum) admits **~100x less light** than the
natural pupil; a 1200um pinhole (near the commercial/clinical design point) still
admits only ~9%. Both function as real sunglasses (R2); the difference is a factor of
~9x in brightness between the two design philosophies.

## Human vision models

- **Contrast sensitivity**: two CSF variants (`contrast.py`), photopic peak ~4 cpd and
  Mannos-Sakrison peak ~8 cpd -- both simplified log-parabola curves matched to the
  literature's reported peak location and general shape (NOT the full multi-parameter
  Barten 1999 model; see `literature.py` fidelity notes).
- **Visual acuity**: MTF-cutoff-based prediction (`visual_acuity.acuity_from_mtf_cutoff`)
  via the exact geometric identity `MAR(arcmin) = 30/cutoff_cpd`, now also returned as
  LogMAR (`logmar_from_mar`, `logMAR = log10(MAR_arcmin)`) -- previously this project
  only ever quoted OTHER studies' LogMAR values in citations/comments; this is the
  first place it computes its own. At a_hole=400um, M=8D: MTF10-based prediction gives
  **~20/49** -- independently consistent with `model_comparison/acuity_check.py`'s
  FWHM-based prediction of **~20/48** at a comparable condition, computed via a
  completely different method (MTF cutoff vs. core-width angular blur, the latter now
  also available directly as `visual_acuity.mar_from_angular_blur`). MTF50-based
  prediction is far more pessimistic (~20/125), reproducing the same "energy/sharp-
  threshold metrics overstate blur's perceptual impact" pattern found in Phase 2.
- **Rose-DeVries / photon-noise SNR** (`contrast.rose_devries_relative_sensitivity`,
  `visual_acuity.snr_acuity_bound`): reproduces the `SNR ~ sqrt(flux)` scaling law
  exactly (first-principles Poisson statistics per Rose's original argument); not
  calibrated to Rose's absolute historical thresholds.
- **Visual Strehl (VSOTF) -- approximate**: `visual_acuity.visual_strehl_approx`
  reproduces the CONCEPT (CSF-weighted OTF comparison) from Thibos et al./Iskander's
  published, clinically-validated VSOTF metric, weighting the REAL PART of this
  project's own radially-averaged OTF (`metrics.otf_radial`) rather than raw MTF
  magnitude (an earlier version of this function used MTF magnitude as a coarser
  stand-in), and using this project's own simplified CSF as the neural weighting
  function -- explicitly not a bit-exact reproduction (see
  `literature.get('visual_strehl_vsx')` for the full fidelity note).

## Pareto analysis

`outputs/pareto_front_M{1,4,8}.png`: blur (r_EE 50%) vs. throughput at three myopia
levels. Finding: **almost every aperture from the blur-minimum (300um) up to the
largest tested (2000um) is Pareto-optimal** -- there is a genuine, monotonic
blur-vs-light tradeoff across that whole range, not a single dominant answer. This
reframes the "discrepancy" question: commercial/clinical designs at 900-1200um are not
necessarily wrong or optimizing a different (mis-specified) problem -- they may simply
sit at a different, defensible point on the same Pareto front, weighting light
throughput more heavily than pure blur-minimization does.

## Validation against published/commercial data (reusing Phase 2's citations)

Reuses `model_comparison/`'s researched values (clinical pinhole occluders 940-1750um,
~1200um typical; commercial pinhole glasses 900-1200um) rather than re-deriving them.
See `model_comparison/README.md` for the original search citations.

## Validation against literature -- RMSE/MAE/R^2/Pearson r (`validate_against_literature.py`)

Until now, every comparison against clinical/commercial data in this project was
qualitative ("how far is the optimum from the clinical range", `validation.py`) or a
rank correlation (`pareto.py::rank_correlation_with_reference`). Nothing computed a
direct regression-agreement statistic against a real multi-point dataset -- the
project's own theory documents call for a "Validation" stage (RMSE/MAE/R^2/Pearson)
that had no code behind it anywhere in the repo.

**Dataset**: `literature.get('ideal_pinhole_wang_2009')` -- "The Ideal Pinhole", IOVS
2009 (ARVO), fetched and confirmed directly against the primary source (not just the
paraphrase already quoted in `model_comparison/README.md`): 13 subjects, mean LogMAR
acuity through single pinhole apertures of 0.5/0.75/1.0/1.2/1.5mm = 0.28/0.31/1.0/0.4/
0.5 LogMAR. The paper's summary table does not report which single myopia level (M)
each point was measured at, so there is no one "correct" M to compare this project's
own M-parametrized model against.

**Method, not a forced fit**: `validate_against_literature.py` runs this project's own
pipeline at M = 0/2/5D against all 5 apertures, computes three candidate LogMAR
predictors per point (MTF50-cutoff, MTF10-cutoff, FWHM-based -- FWHM included because
`model_comparison/`'s own Finding 3 already showed it tracks a different clinical
LogMAR figure far better than `r_EE(50%)`), and reports `validation_stats.
regression_stats()` (RMSE/MAE/R^2/Pearson r) for every (M, predictor) combination as a
**sensitivity table**, never collapsing to a single "best" M -- picking whichever M
happens to maximize R^2 after the fact would be circular, exactly the kind of forced
agreement this project's other comparisons already avoid (see
`model_comparison/acuity_check.py`'s own M-matching caveat for the same reasoning
applied to a single point).

Run `python3 validate_against_literature.py` for the printed sensitivity table;
outputs `validation_predicted_vs_observed.csv` (raw points) and
`validation_regression_stats.csv` (the RMSE/MAE/R^2/Pearson r table) to `outputs/`.
`stage3_integrated/generate_plots.py::plot_validation_regression` renders this as a
predicted-vs-observed scatter (one panel per M).

## Error budget (`comparison.error_budget`, `outputs/error_budget.csv`)

| Contributor | Quantified? | Finding |
|---|---|---|
| Monochromatic vs. polychromatic | Yes | Optimum shifts only ~86 um (450-650nm), measured directly from Stage 2's own multi-wavelength sweep -- a minor contributor next to the several-hundred-um gap from commercial designs |
| Finite natural pupil | Yes | Already modeled explicitly (pupil_clip); not a residual error source since every tested aperture is far smaller than D_pupil |
| Diffraction (near-field/Fresnel) | Yes | This project's core physics -- not a residual/error term |
| Photometric limits | Yes | Modeled in photometry.py -- see table above |
| Ocular higher-order aberrations | No (literature-grounded estimate only) | ~0.33-0.38 micron RMS over a 6mm pupil in normal eyes (cited); expected much smaller at pinhole scale since HOA RMS scales steeply with aperture -- not independently re-derived for this aperture range |
| Accommodation | No | Not modeled; could partially compensate mild myopia, flattening (not eliminating) the blur-vs-M trend |
| Neural processing / letter recognition | No | The ~1.6x residual gap already found in Phase 2's FWHM-based acuity check is attributed here |
| Eye movements | No | Not modeled; static single-PSF simulation only |
| Stiles-Crawford effect | No (optional per brief) | Not modeled; would somewhat reduce the natural pupil's effective area, meaning this project's illuminance-advantage estimate for a centered pinhole is likely slightly optimistic |

## Running it

```
cd stage3_human_vision
python3 run_stage3.py              # reuses outputs/metrics_sweep.csv if present
python3 run_stage3.py --resweep     # forces a fresh ~6-minute PSF-level sweep
python3 validate_against_literature.py  # RMSE/MAE/R^2/Pearson vs. published data (~2 min, 15 points)
python3 literature.py               # prints the full citation bibliography
```

## Honest scope statement

The PSF-level sweep (105 points: 15 apertures x 7 myopia levels, one wavelength/gap)
is deliberately coarser than Stage 2's own 630-point `r_EE(P)`-only sweep, because
every point here costs an additional MTF-FFT and a second (M=0 reference) full ASM
propagation. A literal, maximally exhaustive interpretation of the brief (every listed
graph at fine resolution across aperture x wavelength x gap x M x pupil x illumination)
would require several thousand additional simulation points; this was scoped down to a
representative grid, documented here rather than silently narrowed. The two CSF models
implemented are simplified, peak-matched parametrizations, not the full Barten (1999)
model. The photon-flux/photometric chain uses a single representative daylight
luminance (10,000 cd/m^2); real daylight spans roughly 3,000-30,000+ cd/m^2 depending
on conditions (see `photometry.py`'s cited range) -- override `scene_luminance_cdm2`
to explore that range.
