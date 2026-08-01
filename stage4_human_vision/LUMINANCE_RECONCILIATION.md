# Luminance Re-Sweep: Does Correcting the Scene Luminance Assumption Fix Stage 4's Failed Acuity Validation?

## Background

`brightness_reconciliation/FINDINGS.md` found that Stage 3/4's default scene luminance
assumption (10,000 cd/m^2, "bright daylight") is almost certainly the wrong value for
comparing against clinical acuity data, since clinical testing is done under much
dimmer standardized lighting. This raised an open question: **did that same wrong
luminance assumption contribute to Stage 4's failed acuity validation
(R^2=-2.84 to -6.39 against Wang 2009, reported in RESULTS.md)?**

## What was actually found: Wang 2009's real testing luminance is stated in the paper

`literature.py`'s `ideal_pinhole_wang_2009` citation entry records that the study used
"15 foot-candles illumination" -- an actual reported value, not an assumption. Converted
properly (15 fc = 161.5 lux; assuming a diffuse chart reflectance rho=0.85, a standard
mid-range assumption): **L = 43.7 cd/m^2**. This replaces the assumed 100-300 cd/m^2
range used in `brightness_reconciliation/` with the paper's own stated condition.

## The test: re-ran Stage 4's exact validation setup at this real luminance

Reproduced the original validation first (confirms faithful reproduction of the earlier
reported numbers, small differences from grid_N=1024 here vs 2048 in the original run):

| M | R^2 (original, L=10,000) | R^2 (this re-run, L=10,000) |
|---|---|---|
| 0D | -6.39 (reported) | -6.68 (reproduced) |
| 2D | -4.98 (reported) | -5.24 (reproduced) |
| 5D | -2.84 (reported) | -3.04 (reproduced) |

Then re-ran the identical setup at the real Wang 2009 luminance (L=43.7 cd/m^2):

| M | R^2 at L=10,000 (bright, wrong for this comparison) | R^2 at L=43.7 (real Wang 2009 condition) |
|---|---|---|
| 0D | -6.68 | **-7.88** |
| 2D | -5.24 | **-6.30** |
| 5D | -3.04 | **-3.82** |

## Result: correcting the luminance makes the validation WORSE, not better

**This rules out the luminance-mismatch hypothesis as an explanation for Stage 4's
validation failure.** The mechanism is understood, not just observed: `acuity.py`'s
`brightness_logmar_correction()` adds a positive (worse-acuity) penalty whenever
retinal illuminance falls below the 300 Td knee. Dropping scene luminance from 10,000
to 43.7 cd/m^2 pushes every tested aperture below that knee, uniformly adding predicted
blur across the board -- and since the model was already systematically OVER-predicting
blur relative to the real observations (see RESULTS.md's original diagnosis), adding
more predicted blur made the systematic bias larger, not smaller.

## What this does and does not mean

**Does NOT mean**: the earlier `brightness_reconciliation/` finding was wrong. That
reconciliation was about a DIFFERENT question -- whether the reverse-engineered
brightness-floor PERCENTAGE (6.25-9%) for the OPTIMUM APERTURE matches an absolute
physiological threshold. That finding (Van Nes & Bouman's 300 Td floor landing near
900-1250um at ~300 cd/m^2) stands independently of this result.

**Does mean**: the luminance assumption is NOT the missing piece for Stage 4's acuity
PREDICTOR specifically. The root causes already diagnosed in RESULTS.md -- small N (5),
the Wang dataset's own non-monotonic spike (0.28->0.31->1.00->0.40->0.50, with the
1000um point a clear outlier no smooth model can fit), and no dataset anywhere
recording per-subject refractive error -- remain the actual, sufficient explanation.
This luminance check closes off one more candidate cause rather than opening a new
fix, which is itself useful: it means the honest conclusion in RESULTS.md ("cannot be
properly validated with currently available public data") does not have an easy escape
hatch through a luminance correction, reinforcing that better/more clinical data
(with per-subject M) remains the only real path forward, not further parameter tuning.

## Reproducibility

Ran via a full local mirror of stage4_human_vision + its stage2_fixed/stage3_human_vision
dependencies (grid_N=1024 for speed; a grid_N=2048 re-run would be expected to
reproduce this qualitative conclusion, since the R^2 change direction is driven by the
brightness correction term, not grid resolution). Two environment-only fixes applied to
the mirror during this run, noted for completeness (do not affect the real project
files): `np.trapz` -> `np.trapezoid` (numpy version compatibility), and stage4's local
`types.py` renamed to avoid shadowing Python's standard library `types` module in a
flat (non-package) import context.
