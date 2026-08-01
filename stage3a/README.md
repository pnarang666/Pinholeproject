# Stage 3a -- Brightness-Constrained Optimum Aperture (quick test, not full Phase 3)

Tests one specific, cheap hypothesis before building the full human-vision framework:
is the gap between Stage 2's blur-only optimum (300-400um) and the real clinical/
commercial range explained *just* by the fact that a 300-400um pinhole is too dim to be
usable? Does NOT touch Stage 1 or Stage 2 -- reads `stage2/outputs/r1_full_range_sweep.csv`
directly, adds one new quantity (relative retinal illuminance), and re-derives the
optimum under a brightness floor instead of pure blur minimization.

## Verified clinical/commercial reference range (before assuming a target number)

Searched rather than assumed. Review of Optometry, citing a dedicated clinical pinhole-
size study: **0.94-1.75mm is most effective, with most commercial instruments ~1.2mm**.
Broader commercial range across manufacturers: 0.8-2.0mm. This is the bracket used below,
not an arbitrary "800-1200um" figure.

## `transmission.py`

`relative_illuminance(a_hole_um, D_pupil_um)` -- retinal illuminance as a fraction of
normal (full natural pupil) illuminance, for a single circular aperture in front of the
eye: `E_rel = (min(a_hole, D_pupil) / D_pupil)^2`.

This is NOT Master Formulas Sec2.11's `T = N*(pi*a_hole^2/4)/A_total` -- that formula
answers "what fraction of a multi-hole frame's area is open" (an R2/R3 array-photometry
question); this module answers "how much light reaches the retina relative to normal
viewing" for the single-aperture geometry Stage 1/2 actually simulate. Different
question, deliberately not forked from the array formula.

Diffraction redistributes power spatially but does not destroy it, so relative
illuminance depends on the RAW aperture area (`a_hole`), not any diffraction-broadened
spot-size estimate (`a_eff` from `classical_formulas.py`) -- using `a_eff` here would be
a category error.

## `combine_and_select.py`

For each myopia level M and a range of brightness floors `T_min`, computes:

```
a*_practical(M, T_min) = argmin_{a_hole : E_rel(a_hole) >= T_min} r_EE_50(a_hole, M)
```

i.e. the smallest-blur aperture that still passes at least `T_min` fraction of normal
light. `T_min=0` reproduces Stage 2's original pure-blur optimum exactly (sanity check).

### Result (550nm, 12mm gap slice)

```
T_min      a*_practical (all M=1-8D)
0.0%  ->   300-400 um   (= Stage 2's original blur-only result, unconstrained)
0.5%  ->   300-400 um
1.0%  ->   400 um
2.0%  ->   600 um
3.0%  ->   700 um
6.25% ->   1000 um   <-- inside the clinical bracket
9.0%  ->   1250 um   <-- inside the clinical bracket
12.25%->   1500 um   <-- upper edge of clinical bracket
16.0% ->   1750 um
25.0% ->   2000 um
```

**A brightness floor of roughly 6-9% of full-pupil illuminance alone moves the
optimum from 300-400um into the exact 0.94-1.75mm clinical bracket, uniformly across
all myopia levels tested (M=1-8D).** For reference, this is the same order of magnitude
as light loss from ordinary sunglass tinting or moderate pupil constriction in bright
daylight -- not an extreme constraint.

### What this result does and does not establish

**Does establish:** the size of the gap between blur-only optimization and the real-
world range is fully explainable in *magnitude* by a plausible brightness constraint --
you do not need exotic mechanisms (ocular aberrations, neural contrast processing,
broadband effects, etc.) to close a gap this size. That's a legitimate, reportable,
quantified finding on its own.

**Does NOT establish:** that 6-9% relative illuminance is the actual physiological
threshold where photopic acuity starts degrading -- that number was found by asking
"what T_min reproduces the known clinical range," not derived independently from a
photopic-vision brightness threshold in the literature. Confirming *that* is real
Phase 3 work (a properly-cited illuminance-vs-acuity model, e.g. from photopic vision
science -- Rose-DeVries-type relationships), not this quick check. This script tells you
which hypothesis is worth spending Phase 3's time on; it does not replace Phase 3.

## Extension: r_EE(50/70/80/90) compared, with and without the brightness floor

The original `r1_full_range_sweep.csv` only ever had 50/80/90% baked in (`retinal_
encircled_energy()` in `stage2/phase2_retina.py` hardcodes those three). 80% and 90%
sit progressively closer to the Airy pattern's first-null ill-conditioning already
flagged in `stage2/validation_gate.py`. Added 70% as a real mid-point, computed by
`../stage2_fixed/recompute_multi_EE.py` directly from the raw retinal intensity field
`phase2_retina.run_pipeline_point()` already returns (never saved before) -- no changes
to any Stage 2 file, no re-derivation from the cached scalar columns. Full 15-aperture
x 7-M grid (`multi_EE_sweep.csv`, 105 points), 550nm/12mm slice.

**Unconstrained (blur-only) optimum by percentile:**

```
M(D)   a*_50   a*_70   a*_80   a*_90
1        300     300     400     400
2        300     300     400     400
3        300     300     400     400
4        300     300     400     500
5        400     300     400     500
6        400     300     500     500
8        400     400     500     600
```

Choosing r_EE(80%) or r_EE(90%) as the design criterion instead of r_EE(50%) already
nudges the blur-only optimum somewhat higher (400-600um vs 300-400um) -- but still well
short of the clinical bracket.

**With the brightness floor applied (T_min=6.25%, `stage3a_multi_percentile_constrained.
csv`): all four percentiles converge to the same answer, 1000um, at every myopia level.**
This is not a coincidence -- once the illuminance floor pushes the aperture past where
every percentile's blur curve bottoms out, blur is monotonically increasing in all four
simultaneously, so the constraint boundary dominates rather than the metric choice. The
practical implication: **the brightness floor matters far more than which encircled-
energy percentile you optimize against.** Report r_EE(50%) as primary (best-conditioned)
and note this convergence as evidence the result is not sensitive to that choice, rather
than running a separate multi-percentile debate.

Regenerate/extend via:
```
cd ../stage2_fixed
python3 recompute_multi_EE.py <M_diopters>      # one M at a time, ~80s/call
cd ../stage3a
# then re-run the constrained-optimum block in combine_and_select.py against
# multi_EE_sweep.csv instead of r1_full_range_sweep.csv
```

## Running it

```
cd stage3a
python3 combine_and_select.py                                  # 550nm, 12mm gap
python3 combine_and_select.py --wavelength 650 --gap 15         # check other slices
```
