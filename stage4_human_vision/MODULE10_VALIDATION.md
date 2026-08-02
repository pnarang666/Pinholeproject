# Module 10 Validation Audit: the 5 target validation sets, checked against real data

## Why this audit, and why now

DESIGN.md's Module 10 ("Validation") named 5 target validation sets. Before this
pass, only one was actually done: acuity vs. Wang 2009, which failed decisively
(R^2 strongly negative, p~0.5, confirmed via leave-one-out cross-validation --
RESULTS.md, LUMINANCE_RECONCILIATION.md). That failure was diagnosed as a DATA
problem (n=5, one clinical outlier, no per-subject refractive error) rather than a
MODEL problem. But a single noisy, confounded end-to-end clinical comparison cannot,
by itself, distinguish "the underlying physics (pupil model, CSF model) is right and
the data just can't show it" from "the underlying physics is also wrong." The other
4 validation sets are what actually answer that question, independent of Wang 2009's
noise -- which is why they matter MORE after that failure, not less.

Every reference number below traces to a real, checkable source, verified directly
(full text, primary source code, or the publisher's own indexed abstract) -- never
accepted from a secondhand paraphrase or AI-generated search summary alone. This
discipline caught and rejected a fabricated citation earlier in this project (a
NeuroQuantology paper that a search summary claimed had specific numbers it does not
actually contain) and caught a real anomaly in this pass too (see Set 2 below).

## Summary

| # | Validation set | DESIGN.md's own ask | Status |
|---|---|---|---|
| 1 | Retinal illuminance | "standards-based consistency checks and radiometric cross-checks" | **PASS** -- exact (1.9e-16 relative diff) |
| 2 | Pupil (Watson-Yellott) | "reproduce literature curves... compare against values reported in Watson-Yellott figures" | **PASS** -- RMSE=0.115mm vs real data; exact match vs formula demo |
| 3 | CSF (Barten/Mannos-Sakrison) | "benchmark each implemented CSF against sampled literature curves" | **MIXED** -- Mannos-Sakrison: exact formula match. Barten: confirmed simplified (not the full model), r=0.98-0.99 shape correlation, real ~1cpd peak offset |
| 4 | Acuity (Wang 2009 + pinhole optics) | "published pinhole-acuity datasets" | **FAIL** (already reported, RESULTS.md Section 2/4) |
| 5 | Contrast threshold (Blackwell 1946) | "contextual threshold benchmark, with careful task-mismatch caveats" | **DATA FOUND, NOT BRIDGEABLE** -- real Blackwell data obtained and verified, but measures a different psychophysical paradigm than anything currently implemented |

Only Set 4 is a clean fail. Set 1 is a clean pass. Sets 2 and 3 are real, substantive
passes with honestly-reported caveats. Set 5 is the genuinely ambiguous one: not
a pass, not a fail, but a real limitation of what can currently be checked.

---

## Set 1: Retinal illuminance (radiometric cross-check)

**What existed before this pass**: `test_troland_definition()` -- checks only that
`retinal_illuminance_trolands(L, D) == L * pi * (D/2)^2`, i.e. the troland
DEFINITION applied to itself. This cannot catch an error in how troland-based
illuminance relates to anything external; it would pass even if the whole troland
concept were wired in backwards relative to the rest of the codebase.

**What DESIGN.md actually asked for** (its own words, confirmed by reading
DESIGN.md directly, not from memory): "unit tests on dimensional consistency;
compare against known Td examples from standard definitions; **cross-check
photometric Td against radiometric retinal irradiance conversion at 555 nm**."

**What was done**: `illuminance.py` (photometric: Td = L * A_pupil) and
`photon_noise.py` (radiometric: W/m^2 via an F-number-based formula) are two
INDEPENDENT code paths in this project that both describe retinal light level, but
had never been cross-checked against each other or an external standard. Derived
and verified the standard identity `E_retina(W/m^2) = Td / (683e6 * v_r_m^2)`
(Km=683 lm/W is the CIE/SI-defined peak luminous efficacy, exact at 555nm), with
its geometric form confirmed directly against Psychtoolbox-3's own
`RadianceAndPupilAreaEyeLengthToRetIrradiance.m` source -- the exact "Wyszecki and
Stiles conventions as referenced by Psychtoolbox radiometric conversions" DESIGN.md
names as its primary source for this module.

**Result**: exact agreement, 1.9e-16 relative difference (floating-point precision
only). New test: `test_photometric_td_matches_radiometric_retinal_irradiance_at_555nm`.
Full citation: `literature.py`'s `psychtoolbox_radiometric_troland_crosscheck`.

**What this establishes**: this project's two independent retinal-light-level code
paths are exactly, provably self-consistent with each other and with an external,
independently-sourced standard. It does NOT test whether 683 lm/W or the troland
concept itself is the right physical model (that's settled science, not something
this project is proposing) -- it tests whether THIS CODE correctly implements it,
which it does.

---

## Set 2: Pupil model (Watson & Yellott 2012)

**What existed before this pass**: `test_watson_yellott_shrinks_with_luminance()`
-- a directional check only (dimmer implies larger pupil). Says nothing about
whether the MAGNITUDE is right.

**What was done**: obtained and read the full text of Watson & Yellott (2012)
directly (open-access copy, UC eScholarship). Confirmed every equation (10, 17-21,
24) and parameter (reference age y0=28.58, monocular/binocular attenuation
M(1)=0.1/M(2)=1, Stanley-Davies coefficients) this project's `pupil.py` uses
matches the paper's own printed equations exactly. Built two real, quantitative
checks:

1. **Winn et al. (1994) reference table** (Table 1 of Watson & Yellott, N=91 real
   subjects, monocular, 10-degree field, 5 luminances): 25-point sweep (5
   luminances x 5 ages) against this project's `watson_yellott_pupil_mm()`.
   **RMSE=0.115mm, MAE=0.096mm, max error=0.237mm.** Real empirical data, though the
   paper's own age-slope term was explicitly fit to approximate it, so this mainly
   confirms correct code (no transcription bugs), not fully independent
   physiological support -- stated plainly, not oversold.
2. **Figure 17 demonstration** (the paper's own interactive-demo, arrow-annotated
   value: L=1 cd/m^2, field diameter=60deg, age=40, eyes=2 -> 4.839mm):
   reproduced to **0.0004mm** (essentially exact).

**A real anomaly found and resolved**: the paper's OTHER demo widget (Figure 18's
"Pupil calculator", same condition but age=30) reads 3.828mm. Since the paper's
formula is provably linear in age at fixed L/field/eyes (their Eq. 19-20), and
Figure 17 independently confirms 4.839mm at age=40, linearity REQUIRES age=30 to
give 4.839 + 10*0.02801 = 5.119mm -- exactly this project's output, not 3.828mm.
Re-read the Figure 18 image twice and double-checked PDF page indexing to rule out
a transcription error on this project's side. Conclusion: Figure 18's own
calculator widget is internally inconsistent with the rest of the same paper.
Documented in `literature.py` rather than silently dropped or silently "fixed" by
matching the wrong number.

New tests: `test_watson_yellott_matches_winn_1994_reference_table`,
`test_watson_yellott_matches_figure17_demonstration`. Full citation:
`literature.py`'s `watson_yellott_2012_winn_table_and_figures`.

---

## Set 3: Contrast sensitivity (Barten 1999, Mannos-Sakrison 1974)

**What existed before this pass**: `test_csf_models_positive()` -- checks only
that both CSF functions return non-negative values. Passes trivially for almost
any monotonic-ish function; does not check shape, peak, or scale.

### Mannos-Sakrison: exact formula match

Found the exact published formula (`H(f) = 2.6(0.0192+0.114f)exp[-(0.114f)^1.1]`)
reproduced identically across multiple independent, unrelated image-quality-metrics
papers -- strong evidence of a stable, correctly-transmitted formula, though the
1974 IEEE primary paper itself (not freely available) was not directly read.
This project's `mannos_sakrison_csf()` matches it **exactly** (max diff = 0.0
across 600 test frequencies) -- config's `mannos_scale/offset/slope/exponent`
literally ARE this formula's coefficients. Peak frequency = 7.89 cpd, matching the
commonly-cited ~8 cpd figure for this specific model. New test:
`test_mannos_sakrison_matches_published_formula_and_peak`.

### Barten: confirmed simplified, not the full model -- honestly, as the code already said

First, per the task's explicit instruction to confirm rather than assume: is
`barten_simplified_csf()` the real Barten (1999) model? **No.** Confirmed two ways:

- Its own docstring already said "Barten-inspired simplified CSF engineering
  form... a simplification of Barten's 1999 model" -- an honest label that
  pre-dated this audit.
- Several `barten_*` config fields (`barten_k`, `barten_temporal_integration_s`,
  `barten_x0_deg`, `barten_xmax_deg`, `barten_nmax`, `barten_sigma0_deg`) are
  declared in `constants.json` but **never used** by the actual function -- only
  `barten_c` is used. These names and several of their default values (X_max=12,
  N_max=15) exactly match the real Barten model's own standard parameter names and
  defaults, strongly suggesting they were meant for a fuller implementation that
  was never wired up. One, `barten_sigma0_deg=0.5`, also appears to be a latent
  unit bug (the real model's sigma_0 default is 0.5 ARCMIN = 0.00833 degrees, not
  0.5 degrees) -- harmless since currently unused, but noted for if the full model
  is ever wired up.

Reimplemented the REAL Barten (1999) model directly from the `colour-science`
open-source library's source (`colour/contrast/barten1999.py`), an actively
maintained, cross-referenced library citing Barten (1999), Barten (2003), and ITU-R
BT.2246-4. Verified the reimplementation bit-for-bit against the library's own
doctested example (`contrast_sensitivity_function_Barten1999(4) = 360.8691122...`).
Compared against this project's simplified form at L=10/100/1000 cd/m^2,
field=20deg:

| L (cd/m^2) | ours: peak / cutoff (cpd) | real Barten: peak / cutoff (cpd) | normalized-shape r |
|---|---|---|---|
| 10 | 2.90 / 39.85 | 1.90 / 43.55 | 0.979 |
| 100 | 3.70 / 53.23 | 2.70 / 50.04 | 0.990 |
| 1000 | 4.00 / 58.93 | 3.30 / 53.63 | 0.994 |

Shape correlation is high (r=0.98-0.99) and both models' peak/cutoff frequencies
fall in the commonly-cited photopic ranges (peak ~2-6 cpd, cutoff ~30-70 cpd) --
but there is a real, consistent ~1 cpd peak-frequency offset between the simplified
form and the actual Barten model, reported honestly rather than rounded away. New
test: `test_barten_simplified_peak_and_cutoff_in_known_photopic_ranges` (checks the
commonly-cited-range property, which is real and meaningful, without claiming exact
equivalence to a model the code was never claiming to be). Full citations:
`literature.py`'s `mannos_sakrison_1974_formula` and
`barten_1999_full_model_via_colour_science`.

---

## Set 4: Acuity (already reported)

No new work in this pass -- see RESULTS.md Sections 2 and 4, and
LUMINANCE_RECONCILIATION.md. Summary for completeness: fails the R^2>0/p<0.05 bar
on held-out data even after a cited brightness-correction fix and a leave-one-out-
validated calibration attempt. Diagnosed as a small-N/non-monotonic-clinical-data
problem, not (per Sets 1-3 above) evidence that the underlying pupil or CSF physics
is wrong.

---

## Set 5: Contrast threshold (Blackwell 1946)

**Investigated whether Blackwell's actual data is accessible**: the 1946 JOSA
paper itself is not freely available (pre-digital-era issue, no PMC copy found).
However, a real, rigorous, directly-verified secondary source exists: Crumey
(2014, MNRAS, arXiv:1405.4209, open access, read in full), whose stated purpose is
specifically to fit analytic functions directly to Blackwell's own Table 8 (not a
re-derived or unit-converted version) for downstream reuse. Reimplemented Crumey's
photopic Ricco's-law fit (`R_phot(B) = (1.772e-4*B^-0.25 + 7.167e-5)^2`, his
Eqs. 24/27) and confirmed it behaves correctly (positive, monotonically decreasing
contrast threshold with increasing background luminance -- Weber's-law-consistent
direction) at a real target size (0.595 arcmin, Blackwell's smallest tested).

**Why this is not a pass or a fail, but a real limitation**: Blackwell's paradigm
(single achromatic disc detection, threshold as a function of disc AREA and
background LUMINANCE) is a fundamentally different psychophysical task from the
periodic-grating contrast sensitivity function (threshold as a function of SPATIAL
FREQUENCY) that `csf.py` actually implements -- exactly the "careful task-mismatch
caveat" DESIGN.md's own Module 10 entry anticipated for this specific citation.
Converting between the two requires an area-to-spatial-frequency equivalence model
that this project has no cited source for. One was deliberately NOT fabricated to
force a comparison (that would violate the "no new constant without a citation"
discipline just as much as inventing a numeric constant would). A third-party site
offering "another interpretation" of Blackwell's data in astronomical magnitude
units was found but deliberately not used, to avoid stacking an unverifiable
additional unit conversion on top of an already-secondary source.

**Disposition**: real, verified reference data is now documented in `literature.py`
(`blackwell_1946_contrast_threshold`) for future use (e.g. if a disc/letter-
detection model is ever added to this project), but no test was added claiming to
validate `csf.py` against it, since that would not actually be true.

---

## What this changes about how much to trust Stage 4

Before this pass, the only end-to-end signal was Wang 2009's failure, which is
consistent with either "the model is wrong" or "the data is too weak to tell."
After this pass: the pupil model and the Mannos-Sakrison CSF are both confirmed,
with real quantitative checks against real published reference data, to be
correctly and faithfully implemented. The simplified Barten CSF is confirmed to be
a reasonable, real-Barten-correlated (r=0.98-0.99) approximation, honestly labeled
as such, with a small but real characterized offset. The radiometric/photometric
illuminance plumbing is exactly self-consistent with an external standard. None of
this VALIDATES the acuity prediction itself (that still fails, per Set 4) -- but it
substantially narrows where a problem could be hiding: it is not in the pupil
model, not in the CSF formulas' faithfulness to their sources, and not in the
troland/radiometric plumbing. That leaves the acuity-prediction layer itself
(`acuity.py`'s VSOTF/brightness combination, still uncalibrated beyond the failed
Section 4c attempt) and the clinical validation data (still n=5, still
non-monotonic, still missing per-subject refraction) as the two places the real
uncertainty actually lives -- exactly where RESULTS.md already said to look, now
with more evidence rather than less.
