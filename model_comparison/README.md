# Model Comparison -- Stage 1 vs Stage 2 vs the Old Handbook Approximation

Three independent implementations of "how blurry is the retinal image for a given
pinhole aperture," compared against each other and against real-world reference data
(clinical pinhole-occluder literature, commercial pinhole-glasses specs, and an
independent formula from pinhole-camera photography literature). Reuses `stage1_v2/`
and `stage2/` code as-is via import (same rule `stage2/pipeline_junction.py` already
follows) -- no physics is reimplemented, and neither folder's code or CSVs are modified.

## The three models

| | What it computes | Where the code lives |
|---|---|---|
| **Model 1** (`stage1_runner.py`) | Exact scalar ASM propagation, pinhole -> cornea. No eye, no myopia. | wraps `stage1_v2/physics.py` |
| **Model 2** (`stage2_runner.py`) | Exact ASM x2 + lens phase, pinhole -> cornea -> pupil -> lens -> retina, with the axial-myopia model. | wraps `stage2/phase2_retina.py` |
| **Model 3** (`approximation_runner.py`) | The OLD closed-form formula chain from both reference handbooks: `a_eff` (#3), `r_geo`/`r_diff`/`r_total` (#5-#7, the flawed RSS combination), `a*` (#8). Pure algebra, no simulation. | wraps `stage2/classical_formulas.py` |

`run_comparison.py` merges Model 2 (already computed, `stage2/outputs/r1_full_range_sweep.csv`,
630 points) with Model 3 evaluated fresh on the identical grid, and separately merges
Model 1 (`stage2/outputs/stage1_sweep_summary.csv`, 231 points, cornea-only so no myopia
axis) with Model 3's `a_eff`. `plot_comparison.py` produces all the comparison figures.

## Finding 1 -- the old formula's accuracy depends entirely on which stage it's used at

Quantified relative divergence from the exact numerical result, across every point in
each grid:

| Comparison | mean divergence | max divergence |
|---|---|---|
| Cornea plane: `a_eff/2` vs. Model 1's exact `r_EE(80%)` | **13.8%** | 23.7% |
| Retina plane: `r_total` vs. Model 2's exact `r_EE(50%)` | **64.8%** | 192.8% |

`a_eff` was originally designed as a cornea-plane spot-size estimate (handbook §2.8) --
and at the cornea, it tracks the exact result reasonably well (`outputs/comparison_cornea.png`),
consistently ~14-24% high but with the same overall shape. The much larger failure
happens when the same formula family is repurposed for the full retina-blur
optimization via the RSS combination (`r_total`, #7) -- exactly the step both reference
docs call "physically wrong" (blur sources should be convolved, not root-sum-squared).
`outputs/comparison_retina_M1.png`/`M4.png`/`M8.png` show this directly: the RSS curve's
own minimum sits well to the right of the true numerical minimum, worst at mild myopia.

**Root cause, confirmed by direct calculation, not just inference**: `a_eff =
sqrt(a_hole² + (2.44λd_gap/a_hole)²)` is itself non-monotonic at small apertures -- the
diffraction term dominates and shrinks rapidly as `a_hole` grows from very small values,
producing a spurious secondary dip around 100-150µm (visible in `outputs/comparison_retina_M4.png`)
that has nothing to do with the real optimum and would mislead anyone reading the old
formula's curve at face value. This is a property of the old formula chain itself
(verified numerically in `approximation_runner.py`'s output at a_hole=75-200µm), not an
implementation bug on this project's part.

## Finding 2 -- none of the three physics models land anywhere near commercial/clinical designs, and that's expected, not an error

Searched for real-world reference values (see citations below) and plotted them
alongside all three models (`outputs/comparison_optimum_vs_rayleigh.png`):

| Source | Aperture diameter |
|---|---|
| **Model 2** (this project's numerical optimum, r_EE 50%) | 300-400 µm |
| **Model 3** (closed-form a*, this project) | 473-1339 µm (varies with M) |
| **Rayleigh pinhole-camera formula** (independent literature, `d=1.9√(fλ)`, using `v_r` as the analog focal length) | 210-225 µm |
| Clinical pinhole occluders (optometry) | 940-1750 µm, ~1200 µm typical |
| Commercial pinhole glasses | 900-1200 µm |

All three **physics-based** results (Model 2, Model 3 at higher M, and the independent
Rayleigh formula) cluster in the 200-700 µm range -- notably smaller than any commercial
or clinical product. This is a real, consistent gap, but the most likely explanation is
scope, not a bug: **every physics model here optimizes R1 (blur) alone.** Commercial
and clinical designs are constrained by R2 (light throughput -- a 300µm hole passes
~16x less light than a 1.2mm hole, since power scales as diameter²) and practical
usability (R4/R5 -- field of view, ease of aligning the eye with a tiny hole), none of
which this project has built yet. The reference handbooks explicitly warn that treating
R1 and R2 as one variable is "the most common failure mode" for this problem -- this
comparison is direct numerical evidence of exactly that gap, not proof that the
numerical model is wrong. **Correction proposed**: build the R2 photometry constraint
(`T = N·(πa_hole²/4)/A_total`, handbook §2.11, already derived but not yet coded) and
re-optimize jointly, rather than assuming the pure-R1 optimum should match a product
designed for a different, multi-objective spec.

## Finding 3 -- a genuine metric-selection error in the acuity comparison (`acuity_check.py`)

Both reference handbooks prescribe the R7 acuity conversion as literally "angular blur
= r_EE(P)/v_r, compare against ~1 arcmin." Applying that literally, using this project's
usual `r_EE(50%)` metric, at the same condition a clinical study measured
(**1.2mm aperture, ~5D myopia -> reported ~20/30 Snellen, 0.17 logMAR**):

```
r_EE(50%) = 73.8 um  ->  10.45 arcmin  ->  implied Snellen ~ 20/209
FWHM radius = 16.9 um ->  2.39 arcmin  ->  implied Snellen ~ 20/48
```

`r_EE(50%)` predicts acuity nearly **7x worse** than the clinical measurement. This is a
genuine error in metric choice, confirmed by recomputing with a different metric: FWHM
(a core-width measure) lands within roughly 1.6x of the clinical figure -- both worse
than `r_EE(50%)`'s ~7x gap. The reason: `r_EE(50%)` is a cumulative-**energy** radius,
so it counts diffuse peripheral light spread across faint outer Fresnel rings that does
not meaningfully impair letter recognition, while FWHM only measures the width of the
bright, legibility-relevant core.

**This does not mean `r_EE(P)` is the wrong metric everywhere** -- for the R1 objective
(where the question is genuinely "how is optical power distributed"), `r_EE(P)` is
correct and is what both handbooks specify. It is specifically the wrong choice when
*repurposed* for an acuity/R7 claim without modification. **Correction proposed**: any
future R7 acuity conversion should use a core-width metric (FWHM, or better, a proper
MTF/contrast-threshold criterion at the relevant spatial frequency for a Snellen
optotype) rather than `r_EE(50%)`, and should not be assumed accurate to better than
~2x given this project models diffraction + defocus only -- no higher-order ocular
aberrations, no neural/contrast-sensitivity effects, which real visual acuity also
depends on. Reproducible via `python3 acuity_check.py`.

## Literature and commercial comparison -- citations

- Clinical pinhole occluder diameter: effective range 0.94-1.75mm, ~1.2mm typical
  instrument aperture. ["A Peek at the Pinhole" (Review of Optometry)](https://www.reviewofoptometry.com/article/a-peek-at-the-pinhole);
  ["The Ideal Pinhole" (IOVS/ARVO, 2009)](https://iovs.arvojournals.org/article.aspx?articleid=2366370)
  -- reports mean acuities of 0.28/0.31/1.0/0.4/0.5 logMAR for 0.5/0.75/1.0/1.2/1.5mm apertures.
- Commercial pinhole glasses: hole diameter ~1.0-1.2mm, hole spacing 2-4mm.
  [PINHOLE DETAILS (myopia.org)](http://www.myopia.org/pinholedetails.htm)
- Clinical acuity-vs-diopter figure used in Finding 3: 1.2mm aperture -> 20/30 Snellen
  (0.17 logMAR) for refractive error up to 5.5D.
  ["Assessment of Pinhole for Visual Acuity Recoverment in Patients with Myopia"](https://www.researchgate.net/publication/360685893_Assessment_of_Pinhole_for_Visual_Acuity_Recoverment_in_Patients_with_Myopia)
- Rayleigh pinhole-camera optimal-diameter formula, `d = k√(fλ)`, k=1.56-1.9 (1.9 used
  here, Rayleigh's own 1891 value).
  [Pinhole Design -- what Lord Rayleigh really said (AlternativePhotography.com)](https://www.alternativephotography.com/pinhole-design-what-lord-rayleigh-really-said/)
- MAR/Snellen conversion (MAR in arcmin = Snellen denominator / numerator; 20/20 = 1
  arcmin) used throughout `acuity_check.py`.
  [Evaluation of Visual Acuity (StatPearls/NCBI)](https://www.ncbi.nlm.nih.gov/books/NBK564307/)

## Running it

```
cd model_comparison
python3 run_comparison.py       # merges Model 2 + Model 1 (reused) with Model 3 (fresh)
python3 plot_comparison.py      # all comparison figures -> outputs/
python3 acuity_check.py         # the r_EE(50%) vs FWHM acuity metric check
```

## What this does NOT claim

This comparison does not conclude the numerical models (Stage 1/Stage 2) are wrong --
every divergence found here has a specific, checked mechanism (RSS-vs-convolution for
Finding 1, missing R2/R4/R5 constraints for Finding 2, cumulative-energy-vs-core-width
metric choice for Finding 3). No fix here should mean silently reconciling numbers to
match a reference value without understanding why they differ -- that instruction comes
directly from both reference handbooks, and is followed here.
