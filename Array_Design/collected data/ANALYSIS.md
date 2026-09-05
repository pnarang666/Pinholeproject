# Array design: flaws, gaps and improvements

Written 2026-08-14 during the `Array_Design/` consolidation, covering the array design
system as a whole — `photometry/`, `ghosting/`, and the single-hole diameter result they
both build on. Every claim below is either reproduced by a script in this folder or
states plainly that it is not.

---

## FLAWS — things that are wrong, not things that are merely uncertain

### F1. The ghost-separation formula was wrong, and everything downstream inherited it
`THEORY.md` Eq. (1), `Δr = s·v_r/d_gap`, does not vanish for an emmetropic eye: at M = 0
it predicts ghost copies 1.86 pitches apart in an eye with no defocus at all. It is not
the separation of ghost images of a distant point. The correct expression, derived three
independent ways in `ghosting/ghost_separation.py` and verified numerically in
`ghosting/delta_r_derivation_check.py`, is

> **Δr = s·|v_r − v_f|/v_f = s·M/(P0 − M)**

— which vanishes at M = 0, contains no `d_gap` at all, and reuses exactly the defocus
factor of this project's own Formula #5. The wave-optics check propagates a displaced
hole through `stage2_fixed`'s unmodified pipeline and finds the retinal spot within half
a grid pixel of that prediction at every M from 0 to 8 D; at M = 0 it measures −0.13 µm
where Eq. (1) predicts 837 µm. The two disagree by 14× (M = 8 D) to 111× (M = 1 D).

**What it broke, specifically** (`ghosting/RESULTS.md` Pass 4, tables in full):
* **Pass 3's headline finding does not survive.** *"The worst-case harmonic is NEVER
  n = 1"*, with the worst harmonic 4.4× more dangerous than the fundamental, was an
  artifact: Eq. (1) placed f0 at 0.10–0.30 cpd, far below the CSF peak, so some harmonic
  had to land on it. With the corrected Δr the fundamental is already at 2.9–8.3 cpd and
  the worst harmonic is n = 1 at **20/20** dense points, with worst-margin ÷
  fundamental-margin = 1.000 exactly.
* **Pass 3's "Regime B may not meaningfully exist" does not survive either.** It does
  exist, at low myopia: at a = 400 µm, s = 900 µm, M = 1 D the ghost comb sits at 25.9 cpd,
  beyond the incoherent cutoff of the eye's own optics, so MTF(f0) = 0.
* **Pass 3's claimed robustness across myopia was a property of the wrong formula.** The
  real behaviour is steep and monotone: margin 0 → 38 → 237 → 320 → 343 for M = 1 → 8 D.
  The same array is safe for a −1 D wearer and firmly in the danger zone for a −8 D one.
* **What survived unchanged:** the A/B/C tallies at M = 4 D (16 A / 0 B / 20 C, identical
  across all three runs), and therefore Pass 2's central reversal — that the real Barten
  CSF moves the whole dense-pitch range from "safe" to "danger zone" — is unaffected.
* **`photometry/no_ghost_max_pitch()` inherits it too.** It inverts Eq. (1). The corrected
  inversion is `s_max = r_EE·(P0−M)/M`, with no `d_gap`. Recomputed in
  `photometry/noghost_constraint_corrected.csv`, where the interesting result is not that
  the limit moved but that **the constraint has no solution for any aperture in the
  corrected optimum band at M ≥ 4 D**: `s_max` comes out smaller than the hole diameter
  itself, so copies cannot be merged by blur overlap. That is not an accident — Eq. (4) of
  `ghost_separation.py` gives `Δr / blur_diameter = s / a_stop` exactly, so copies overlap
  only if the holes do. The exception is low myopia (at M = 1 D, a = 300–700 µm, `s_max`
  does exceed the hole diameter), which is the same window the ghosting classifier
  independently reports as Regime B — two different routes to the same conclusion.

*One thing the correction makes better, worth stating because it cuts the other way:*
Passes 1–3 flagged the CSF as the weak link because f0 = 0.1–0.3 cpd was at or below the
edge of Barten's stated 0.2–50 cpd validity. With the corrected Δr the relevant
frequencies are 2.9–8.3 cpd — comfortably inside it, and near the peak the model is best
constrained by. `THEORY.md` §5.1's "extrapolation" concern is substantially reduced.

### F2. Regime A tests the wrong tail of the N_eff distribution
`ghosting_regime.classify_ghosting_regime()` declares Regime A — *"no second hole
simultaneously active"* — when the **minimum** N_eff over pupil alignments is ≤ 1. The
minimum is the right worst case for **brightness** (fewest holes = darkest) and the wrong
one for **ghosting** (most holes = worst ghosting). Both uses read the same number.

Measured (`joint_design_space.py::alignment_fractions`, `alignment_fractions.png`), at
D_pupil = 4 mm, square packing:

| pitch (µm) | P(0 holes) | P(exactly 1) | P(≥2 holes) | classified |
|---|---|---|---|---|
| 2100 | 0.00 | 0.01 | **0.99** | A |
| 2500 | 0.00 | 0.18 | **0.82** | A |
| 2800 | 0.00 | 0.40 | **0.60** | A |
| 3200 | 0.03 | 0.71 | 0.26 | A |
| 4000 | 0.21 | 0.79 | 0.00 | A |

The s = 2500 µm column of the project's own 36-point sweep is labelled "A — no second
hole to ghost against" while having two or more holes in the pupil 82 % of the time.
Only pitches above **s_solo ≈ 3.94 mm** — where even the *maximum* N_eff is 1 — are
ghost-free by construction. This is a separate error from F1 and would have been there
with either formula.

### F3. The alignment sweep is under-resolved exactly where the design boundary sits
`n_holes_exact_sweep_alignment()` defaults to 25 offsets per axis; `ghosting_regime.py`
calls it with 15. Both are too coarse near the critical pitches, and both err optimistic:

| pitch (µm) | quantity | n_offsets 15 / 25 | n_offsets 41 / 61 / 121 |
|---|---|---|---|
| 2900 | min N_eff | **1** ("never dark") | **0** (goes dark) |
| 3900 | max N_eff | **1** ("never ghosts") | **2** (can ghost) |

The sampled offsets never land on the worst alignment (a lattice-cell corner) unless the
grid is fine enough. `joint_design_space.py` uses 61 throughout (61 and 121 agree at
every pitch tested) and says so; the stored CSVs in `photometry/` and `ghosting/` were
produced with the coarse defaults.

### F4. The single-hole diameter optimum does not describe an array with N_eff > 1
Nothing in this project had ever evaluated `THEORY.md` Eq. (2) — the multi-hole retinal
PSF — even though it has been written down since the ghosting theory was drafted. Every
blur and acuity number in the project (`stage2_fixed`'s R1 sweep, `stage3a`, `stage4`) is
a **single-hole** r_EE(P), and every array number treats the copies' existence without
asking how wide the summed pattern is.

Computed for the first time in `array_psf_envelope.py` (single-hole PSF from
`stage2_fixed`, summed over the holes actually inside the pupil at the copy displacement
of F1, encircled energy from `stage1_v2`'s own function):

| M (D) | pitch 700 µm | 900 µm | 1200 µm | 2000 µm | 2900 µm | full-pupil blur |
|---|---|---|---|---|---|---|
| 1 | 2.15× | 2.01× | 2.19× | 2.86× | 1.00× | 33.9 µm |
| 4 | 7.82× | 6.94× | 7.55× | 10.67× | 1.00× | 142.9 µm |
| 8 | 12.54× | 10.81× | 11.62× | 16.98× | 1.00× | 307.7 µm |

(ratio of the array's r_EE_50 to the single hole's, a = 400 µm). At M = 8 D, pitch 2 mm,
the array's blur is 303 µm against a full-open-pupil geometric blur of 308 µm: **the
pinhole benefit is essentially gone** while the wearer still pays 98 % of the light loss.
The ratio returns to exactly 1.00 as soon as only one hole is active. So the
"400–750 µm optimum diameter" is a statement about the N_eff ≤ 1 corner of the design
space only, and reading it off the diameter axis elsewhere overstates the design.

The assumption Eq. (2) rests on was checked, not assumed: across hole displacements the
grid can represent, each copy's r_EE_50 varies by 1.7 % and its centroid tracks the
corrected Δr to 0.44 grid pixels (`array_psf_shift_invariance_check.csv`).

### F5. `photometry/` and `ghosting/` had never been run against the same corrected optics
The lens-wavelength fix landed in `stage2_fixed` on **2026-08-06** (commit `28d796c`).
Every stored artifact in both folders predates it: `ghosting/ghosting_sweep*.csv` are
dated 2026-07-29, `photometry/*.csv` 2026-08-01. `photometry/noghost_constraint.csv`
carries the pre-fix radii directly (its a = 300 µm, M = 1 D entry is r_EE_50 = 23.04 µm,
the pre-fix value; post-fix it is 16.51 µm, and the optimum aperture moved 300 → 700 µm).
`array_photometry.py` itself has no optics dependency, so its N_eff and E_rel columns are
unaffected — but `noghost_constraint.csv` is the one place the two are joined, and it is
stale on both counts (F1 and this one).
`stage2_fixed/LENS_WAVELENGTH_FIX.md` item 6 predicted exactly this and said it "has not
been checked here". **This consolidation is the first time it was checked.** The
`master_dashboard` array-ghosting tab does compute live against post-fix optics, so it
could have produced corrected numbers interactively since 2026-08-09, but no result from
it was ever saved.

### F6. Smaller inconsistencies that only became visible with both folders open together
* **Three plots `RESULTS.md` cites had never been committed.** `ghosting_regime_map.png`,
  `ghosting_regime_map_barten.png` and `harmonic_margin_profile.png` are referenced as
  deliverables of Passes 1–3 but were in none of the project's folders. They were found
  in `~/Downloads`, with timestamps (29 Jul 21:52 / 22:15) matching the Pass 1–3 CSVs
  minute-for-minute, and have been **copied into `ghosting/`** so the record is complete.
  They are pre-lens-wavelength-fix, legacy-formula artifacts — historical, like the
  Passes they belong to, and superseded by `joint_design_space*.png`.
* **The Pass 1–3 sweeps are not reproducible from the folder's own code.** There was no
  sweep driver — only the per-point functions. The three CSVs were produced by scripts
  that were never saved. `rerun_corrected_sweep.py` now provides one.
* **`ghosting_regime.py`'s module docstring is stale.** Its prominent "KNOWN, TESTED
  LIMITATION" block still states that Regime C "was NEVER triggered across a full test
  sweep" — true in Pass 1, contradicted by Passes 2, 3 and 4, which found 20/36 points in
  Regime C. Left in place (it is part of the record) but it is the first thing a reader
  of that file sees.
* **`singleilluminate/` states six times that `stage_array/` "does not exist in this
  project"** and blocks its multi-hole illumination branch on that basis
  (`illumination_model.py`, `streamlit_app.py`, `run_illumination_sweep.py`,
  `join_with_system.py`, `README.md`). The module was restored on 2026-08-01 and now
  lives at `Array_Design/photometry/array_photometry.py`, exposing exactly the
  `relative_retinal_illuminance_array()` interface those files say they need. Not fixed
  here — `singleilluminate/` is outside this task's write scope — but the array branch of
  the illumination model is unblocked whenever someone wants it.
* **Square-only ghosting.** `photometry/array_sweep_full.csv` sweeps both square and hex
  packing, but every ghosting sweep ever run (Passes 1–4 and the design-space grids) is
  square. The packing comparison in this folder is therefore geometric only.

---

## GAPS — real missing pieces, stated as missing

### G1. No joint (diameter, pitch) optimisation has ever been run — and this task did not run one
`joint_design_space.py` produces a **feasible region**: the set of (a, s) that no
constraint rules out. It does not optimise anything. There is no objective function
combining blur, brightness and ghost visibility, no weighting between them, and
therefore no single best (a, s). `RECOMMENDATION.md` states a region for exactly this
reason. Anyone reading a single "recommended aperture and pitch" out of this folder is
reading something that was never computed.

### G2. Hexagonal vs square packing is now partly consolidated, and only partly
Both packings existed in `array_photometry.py` from the start and `array_sweep_full.csv`
swept both, but no comparison was ever drawn and the ghosting side never ran hex at all.
What this consolidation can now state (`alignment_fractions.csv`, `pupil_sensitivity.csv`):

| D_pupil = 4 mm | square | hex |
|---|---|---|
| s_dark (pitch above which the view can go black) | 2877 µm | **3487 µm** (+21 %) |
| s_solo (pitch above which 2 holes can never co-occur) | 3936 µm | 4001 µm |
| width of the unavoidable-compromise gap | 1059 µm | **514 µm** (half) |
| best achievable P(exactly one hole) | 0.83 @ 3700 µm | **0.93 @ 3900 µm** |
| P(0 holes) at that best pitch | 0.13 | **0.05** |

Hex is better on every one of these, for the geometric reason that its Voronoi cell has
a smaller circumradius (`s/√3` vs `s/√2`) so it covers the pupil at a larger pitch. What
is **still missing**: no ghosting regime sweep, no MTF/CSF margin, and no multi-hole PSF
has been computed for hex. The advantage above is packing geometry alone.

### G3. Vignetting and gaze angle (R4/R5) still have zero implementation anywhere
Confirmed by reading `phase2_retina.py`'s own PHYSICS_AUDIT E4 note: the aperture is an
infinitely thin binary mask, there is no membrane-thickness or oblique-angle vignetting,
and every stage is on-axis. This matters more for arrays than for a single hole, because
an array's holes are off-axis **by construction** — at pitch 4 mm the second ring of
holes sits 4–8 mm off axis, where both the obliquity factor and the physical thickness of
the occluder start to cut transmission, and where the corrected Δr derivation's own
scope note (on-axis object point) stops guaranteeing that all copies shift equally.

This consolidation also found a **concrete numerical blocker** for that work: at the
project's standard grid (grid_N = 2048, window 6 mm), the lens phase is only adequately
sampled out to **r_max_lens = 1564 µm**, which is *smaller than the 2000 µm pupil radius*
(`phase2_retina.validate_lens_sampling`, PHYSICS_AUDIT item C — documented as
informational and non-gating). `array_psf_envelope.py` walks straight into it: a hole
displaced 1799 µm off axis aliases and lands at a spurious −2729 µm instead of the
predicted −128 µm. Any direct off-axis array simulation needs a finer grid or wider
window first; the workaround used here (shifting the on-axis PSF, valid because Eq. (2)'s
shift assumption was verified) sidesteps it but cannot model vignetting.

### G4. No experimental confirmation exists for any array-specific prediction
Not one. The A/B/C boundaries, the corrected Δr, the N_eff-versus-alignment trade, the
F4 blur-envelope result, hex-versus-square — all are theory validated only against other
theory in this repo. The single external anchor remains Kim et al. (2017)'s reported
honeycomb/double-vision symptoms in real multi-pinhole wearers, which is qualitatively
consistent with Regime C but reports no pitch, so it cannot test a boundary.

### G5. Pupil diameter is an assumption the design cannot control, and the region moves with it
Every pitch limit scales with D_pupil (`pupil_sensitivity.csv`):

| D_pupil | 2 mm | 3 mm | 4 mm | 5 mm | 6 mm |
|---|---|---|---|---|---|
| s_dark, square | 1438 | 2158 | 2877 | 3597 | 4317 µm |
| s_solo, square | 1971 | 2954 | 3936 | 4923 | 5905 µm |

A real pupil moves across most of that span between bright sun and dusk. **No single
pitch keeps N_eff = 1 across a 2–6 mm pupil range** — for either packing — so an array
that is ghost-free in daylight goes dark at night, or vice versa. Every number in
`RECOMMENDATION.md` is conditioned on D_pupil = 4 mm, and that conditioning is doing more
work than any other assumption in this folder.

---

## IMPROVEMENTS — specific computations, in the order they would pay off

### I1. Replace the diameter axis with a multi-hole blur optimum (highest value)
F4 is the deepest problem: the diameter constraint is currently borrowed from a
single-hole sweep and is only valid in one corner of the plot. `array_psf_envelope.py`
already computes the array's true r_EE(P) — sweeping it over (a, s, M, alignment) instead
of the six spot-checks it currently runs would give a diameter optimum valid everywhere,
and would let `joint_design_space.py` draw a *blur* contour rather than a vertical band.
Cost: one propagation per (a, M) plus cheap summation per (s, alignment) — the same
caching `corrected_regime.py` already does. This is the single computation that would
most change the shape of the recommended region.

### I2. Resolve F1's remaining sensitivity — there isn't one, so spend the effort on F2 instead
The formula question is settled: two independent derivations, a ray trace, a wave-optics
measurement and the M = 0 limit all agree, and the wave-optics check is not a
recalculation of either formula but a direct measurement through the project's own
pipeline. Nothing about the design region now hinges on which formula is used.
What *does* remain ambiguous is **F2's worst-case-versus-typical question**, and it is a
modelling choice rather than a physics one: is a design that ghosts at 60 % of pupil
alignments acceptable? Replacing the binary worst-case rule with an alignment-weighted
expected margin (`P(N_eff ≥ 2) × margin`, both already computed) would make the B/C
boundary a continuous risk surface instead of a cliff, and is a few hours' work.

### I3. Run the ghosting sweep on hex packing
G2's advantage is currently geometric only. `corrected_regime.classify()` already takes
`packing="hex"`; re-running the design-space grid with it is a parameter change, and it
is the cheapest remaining way to strengthen or overturn a recommendation that currently
prefers hex on partial evidence.

### I4. Make pupil diameter the third axis
G5 shows the region moves further with D_pupil than with myopia. A (pitch × D_pupil)
map at fixed diameter, with the P(dark) and P(≥2) surfaces from
`alignment_fractions.py`, would show directly whether *any* fixed design is defensible
across a realistic pupil range, or whether the honest conclusion is that a fixed-pitch
array cannot be — which is currently the direction the numbers point.

### I5. Raise the grid before attempting R4/R5
G3's blocker (r_max_lens 1564 µm < pupil radius 2000 µm) is a prerequisite, not a
detail. `validate_lens_sampling()` already returns the `suggested_grid_N` needed.

### I6. The next experimental sample — an explicit update to the phase plan's recommendation
The earlier plan called for a **sparse-vs-dense array comparison**. That is still the
right experiment, and this consolidation sharpens it into a test that can actually
discriminate, plus one change of emphasis:

**Keep:** sparse vs dense remains the axis worth testing, because the two failure modes
are physically different (blackout vs ghosting) rather than two degrees of the same one.

**Update 1 — the sample set follows from the geometry, not from the patents.** The
informative pitches at D_pupil = 4 mm are **s ≈ 4.0 mm** (never ≥2 holes; the predicted
cost is a 21 % / 8 % blackout rate for square / hex), **s ≈ 2.5 mm** (never dark; ghosts
at 82 % of alignments), and a **dense s ≈ 0.9 mm control** (the CN-patent regime, where
F4 predicts the pinhole benefit is nearly gone). Two of those three are not near either
patent's pitch, which is where the earlier plan would have put them.

**Update 2 — the strongest discriminating prediction is now myopia-dependence, and it is
free to test.** Under the corrected Δr the *same* array is Regime B at −1 D and deep in
Regime C at −8 D (margin 0 → 343). One array plus trial lenses over a range of induced
myopia tests the corrected formula directly — a prediction the legacy formula does not
make, since it predicted near-constant margin across M.

**Update 3 — the measurement must include eye movement.** Every quantity that decides the
outcome depends on where the pupil sits relative to the lattice, and that changes
continuously as the wearer looks around. A static bench measurement through a fixed
artificial pupil measures one alignment out of a distribution and can report either
"perfectly clear" or "obvious double vision" from the same sample. Report the *fraction*
of gaze directions showing doubling or blackout, not a yes/no.

**Update 4 — a bench measurement can settle F4 without a human.** The multi-hole
blur-envelope prediction (7–17× the single-hole r_EE_50) is a physical-optics claim: a
camera focused at infinity behind the array, defocused by a known amount, measures it
directly. That is the cheapest experimental check in this whole folder and needs no
subjects, no CSF model, and no psychophysics.

---

## Addendum: from feasible region to a scored optimum (2026-08-14, second pass)

Everything above was written after Step 3's feasible-region plots. This addendum
covers a follow-up pass that turned that region into an actual scored surface: a true
multi-hole blur sweep (closing F4/I1), a continuous ghosting risk (closing F2/I2), and
a joint optimiser answering directly whether an N_eff>1 design is ever the best choice.
Nothing above is edited; this is appended, as the earlier report's own instructions
require.

### A bug found and fixed while building the blur sweep, stated plainly

`array_psf_envelope.array_psf()` measured each alignment's blur as encircled energy
around the **optical axis**, not around the summed pattern's own centroid. For a
single active hole (N_eff=1) that is not the centre lattice point, this reports
"distance from the axis" as blur -- a hole 1-2 lattice rows off centre showed r_EE_50
growing from 11um (matching the true single-hole value) up to 86um, purely from being
off-axis, with **zero actual change in image sharpness** (a single active hole produces
a sharp image, just laterally displaced -- the same reasoning
`q1_copies_are_shifted_replicas()` already applied per-hole, not yet applied to the
summed pattern). Found by tracing an unexpected optimiser result (why large,
geometrically non-optimal apertures were winning) back to its source, not by a
dedicated test -- a reminder that a wrong intermediate number can look like a
downstream modelling finding until traced. Fixed by recentring `I_sum` on its own
intensity centroid before measuring r_EE (`array_psf_envelope.py`, current version).
Re-running the full sweep and optimiser after the fix changed individual alignment
values but not the optimiser's chosen (aperture, pitch) at any (M, packing) -- the
error was diluted by alignment-averaging in the reported statistics, though it would
have mattered for any code reading `array_r_EE_50_min/max_um` directly rather than the
mean.

### F4 closed: the true multi-hole blur, swept (not spot-checked)

`multi_hole_blur_sweep.py` sweeps `array_psf()` (post-fix) over the R1 sweep's own 15
apertures x a pitch range x M=[1,2,4,6,8] x both packings x a 7x7 alignment grid per
point (1370 valid rows, `multi_hole_blur_sweep.csv`). Two new, load-bearing caveats
neither the original spot-check nor F4 itself stated numerically:

- **The alignment grid was cut from 11x11 to 7x7 mid-run**, after an unscoped first
  attempt (400-5400um pitch, 11x11) ran 40+ minutes without finishing. The pitch floor
  was also raised from 400 to 700um. Both cuts are stated in
  `multi_hole_blur_sweep.py`'s own header, not hidden: the removed region (very small
  aperture x very small pitch) is also the densest, most expensive, and least
  design-relevant corner of the grid.
- **r_max_lens exclusion (G3) triggers at 100% of the 1370 points swept, not a rare
  edge case.** Every row's blur is a genuine LOWER BOUND, since at least one
  geometrically-present hole was excluded as unrepresentable at this grid somewhere in
  its 49-alignment sample. This does not invalidate the comparisons (the same bias
  applies broadly across the sweep) but means no number here should be read as exact.

Largest measured ratio: **11.70x** single-hole blur (a=400um, s=2700um, M=8D, hex) --
in the same range F4's original six-point spot-check found (7-17x), now backed by a
1370-point sweep rather than six points, and with the axis-vs-centroid bug fixed.

### F2 closed: a continuous risk, and its own scale checked against the whole grid

`ghosting_risk.py` implements `risk = P(N_eff>=2) * worst-harmonic margin`, reusing
`corrected_regime.margin_detail()` (a new split of `classify()`'s own computation,
regression-checked against `classify()` itself, not assumed faithful) and
`alignment_fractions()` at n_offsets=61. Run across the full optimiser grid (1370
points): **541/1370 (39.5%) of ALL points are classified "safe" (Regime A) while
carrying risk>10** -- ten times past the CSF perceptibility threshold once weighted by
how often 2+ holes actually occur. This is F2's finding at the scale of the whole
design space, not two illustrative pitches.

### The optimiser's direct answer: does an N_eff>1 optimum exist?

`optimise.py` builds one cost per (aperture, pitch, M, packing) from four already-
computed, reused quantities (blur ratio, P_dark, ghosting risk, brightness), with every
weight named, defaulted, and justified in that file's own docstring (not repeated
here). At default weights, **per (M, packing):**

| M | packing | a (um) | s (um) | N_eff_worst | regime_binary | risk | blur_ratio | P_dark | E_rel_mean (%) |
|---|---|---|---|---|---|---|---|---|---|
| 1D | hex | 600 | 700 | 27 | B | 0.00 | 2.35 | 0.00 | 66.9 |
| 1D | square | 600 | 700 | 23 | B | 0.00 | 2.31 | 0.00 | 57.7 |
| 2D | hex | 600 | 700 | 27 | C | 38.6 | 4.06 | 0.00 | 66.9 |
| 2D | square | 400 | 700 | 23 | C | 1.82 | 4.46 | 0.00 | 25.7 |
| 4D | hex | 2000 | 2200 | 1 | A | 136.6 | 4.12 | 0.00 | 74.2 |
| 4D | square | 2000 | 4200 | 0 | A | 0.00 | 4.09 | 0.29 | 17.7 |
| 6D | hex | 2000 | 2200 | 1 | A | 116.4 | 5.43 | 0.00 | 74.2 |
| 6D | square | 2000 | 4200 | 0 | A | 0.00 | 5.43 | 0.29 | 17.7 |
| 8D | hex | 2000 | 2200 | 1 | A | 98.3 | 6.12 | 0.00 | 74.2 |
| 8D | square | 2000 | 4200 | 0 | A | 0.00 | 6.10 | 0.29 | 17.7 |

**Yes, unambiguously, at M=1-2D**: dense arrays (N_eff_worst 23-27) win outright, for
two different reasons at the two myopia levels. At M=1D the ghost comb genuinely sits
past the eye's own optical/perceptual cutoff (Regime B, risk~0) -- dense is free. At
M=2D it is NOT free (Regime C, risk up to 38.6) but wins anyway, purely because the
brightness reward (up to 67-75% retinal illuminance vs ~1% for a single well-chosen
pinhole) overwhelms every penalty term at default weights.

**At M=4-8D the answer depends on packing, and hex's own "optimum" reproduces F2's
blind spot exactly.** hex picks N_eff_worst=1 (barely -- not 0) at a risk of 98-137
(deep into danger-zone territory by the continuous metric) while the binary classifier
still calls it Regime A, because Regime A is decided on the *minimum* alignment, which
is exactly 1 there. The optimiser's own chosen "best" hex design is a live instance of
F2, not a hypothetical one. square instead lands on a genuinely zero-risk N_eff_worst=0
design, at the cost of a 29% blackout rate and much lower brightness (17.7% vs 74.2%).

**So: N_eff_worst>=1 at 7/10 optima, N_eff_worst>1 (multiple holes GUARANTEED active,
not just possible) at 4/10.** An array design is not a strictly worse choice than a
single pinhole under this objective -- at low myopia it is the clear winner, and even
at higher myopia the "optimal" hex answer embraces real ghosting risk rather than
avoiding it.

### The finding this task explicitly asked to surface either way: is the objective's calibration trustworthy?

**Brightness dominates most of the tested surface, and this is a property of how
BRIGHT_REF_PCT was set, not a discovery about the physics.** `optimise.py`'s own
sensitivity sweep (0.25x-16x default, one weight at a time, M=4D/square):

| weight varied | flips the M=4D/square answer at |
|---|---|
| w_ghost | **0.5x default or below** (reducing ghost-aversion) |
| w_bright | **2x default or above** (increasing brightness reward) |
| w_dark | 2x default or above |
| w_blur | 8x default or above |

w_ghost and w_bright each flip the answer within a factor of 2 of their stated
defaults -- the M=4D/square "optimum" is close to a decision boundary on two of four
axes, not a robust, wide-margin conclusion. The mechanism: `E_rel_mean_pct` scales
with N_eff (which can reach 25+) and hole area (which spans 75-2000um, a 700x area
range), so it ranges 0.02% to 75% across the grid -- a dynamic range the fixed
BRIGHT_REF_PCT=1.0% reference does not compress, letting brightness reach cost
contributions of -75 while blur_ratio stays O(1-12) and even risk is capped at 50. This
is reported as a finding about the OBJECTIVE's calibration, per the task's explicit
instruction not to hide a weight that materially changes the conclusion -- re-tuning
weights until a "nicer" answer appeared was deliberately not done.

---

## Addendum: Defect audit (2026-08-14, third pass) — Defect 1 diagnosed and fixed

Two defects were flagged as blocking trust in the second-pass Addendum's numbers before
any further sweep or decision output. This section covers Defect 1 (`r_max_lens`
excluding 100% of the 1370-point sweep); Defect 2 (the ghost-separation formula's
validation) follows in the next Addendum.

### Diagnosis, with instrumentation, not assertion

Traced at one representative point (a=400µm, s=900µm, M=4D, square) via direct
instrumentation of `array_psf_envelope.py`'s exclusion logic: `r_max_lens_um` measured
**1564.44µm identically across every (aperture, M) tested** (75µm to 2000µm apertures,
M=1-8D) — confirming it is a pure function of the fixed grid (wavelength, the emmetropic
`f_eye`, and `dx = window_L_mm/grid_N`), not of the design point at all. It is computed
inside `single_hole_psf()` *before* any crop decision exists, ruling out cause (a); its
units (micrometres throughout, at both the computation and the comparison site) were
directly re-verified, ruling out a second instance of cause (b) — the earlier µm/m bug
was in the crop-sizing arithmetic, a different code path entirely. At the traced point,
4 of 13 geometrically-present holes sat at r=1800µm from the axis, each excluded because
`r_hole + a/2 = 2000µm > r_max_lens = 1564.44µm` by exactly the pupil-edge margin — the
*same* four coordinates every time, at every aperture and M, since `r_max_lens` never
moves.

**This is closest to cause (c), but more precisely characterised than "the tested
design space is invalid."** The pupil really is 4mm in diameter (`D_PUPIL_UM`, a
physical parameter of this project's model eye) and a hole 1.8mm off-axis inside it is
a genuinely valid design point — light through it is real. What is invalid is the
*grid's ability to represent it*: `phase2_retina.validate_lens_sampling()` (pre-existing
in `stage2_fixed`, not written for this module) already documents that its own
non-gating check found `r_max_lens < pupil_radius` at every point *stage2_fixed's own
single-hole use ever tested* — and explicitly flagged this as untested for "a future,
more extreme configuration." This module's off-axis multi-hole shifts, reaching to the
full pupil radius rather than staying near-axis, are exactly that more extreme
configuration. **So the fix applied is not "re-bound the sweep to exclude invalid
geometry" (shrinking the pupil model to fit the grid) but "raise the grid to represent
the pupil that was already the stated design parameter"** — the more defensible of the
two remedies the original task offered, since the pitch/aperture range being tested was
never physically wrong.

### The fix, and its verification

`GRID_N` raised 2048 → 4096 (`WINDOW_L_MM` unchanged) in `array_psf_envelope.py`. This
moves `r_max_lens_um` to **3128.9µm**, comfortably past the 2000µm pupil radius even for
the largest tested aperture (2000µm) sitting exactly at the pupil edge
(`r_hole + a/2 = 3000µm < 3128.9µm`). Re-checked, not assumed: a scan of 48
representative (aperture, M, pitch) combinations spanning the full tested range,
including that worst case, found **zero exclusions** at the new grid (was 100% of
points at the old one). `crop_vs_full_grid_check()` re-passes at the new resolution
(0.06–0.93% crop-vs-full-grid agreement, same convention as before). Single-hole
`r_EE_50` shifts 0.05–2.1% between the two grid resolutions at spot-checked points —
ordinary grid-refinement convergence, inside this project's own ±10% tolerance
conventions, not a new discrepancy to chase.

**Cost**: ~16s/cold propagation (was ~6-7s), paid once per (aperture, M) via the
existing cache, not per sweep point — roughly 2.3-2.7× per-propagation cost, not the
~4.4× a naive FFT-scaling estimate would suggest.

Any multi-hole blur sweep run at `GRID_N=2048` (including the 1370-point
`multi_hole_blur_sweep.csv` this Addendum's own numbers were checked against) is
superseded by this fix and must be re-run — see the next Addendum for the regenerated
numbers, with the old (defect-carrying) file preserved under an explicit `_legacy`
name.

---

## Addendum: a memory defect found while regenerating the sweep at the Defect-1 fix (2026-08-14, third pass continued)

Found during Task 13's regeneration, not anticipated by the Defect 1 fix itself: the
first attempt to re-run `multi_hole_blur_sweep.py` at the new `grid_N=4096` default
drove the host machine into a full memory/disk crisis -- swap completely exhausted
(12.5GB used, 0 free), the root disk at 99-100% capacity, and the sweep process itself
stuck (0% CPU, "stuck" process state, RSS collapsed while holding 49GB of virtual
memory) roughly an hour into the run, well past its (already-revised-upward) ETA.

**Root cause, confirmed by direct measurement, not inferred**: `array_psf_envelope.py`'s
`single_hole_psf()` cache (`_PSF_FIELD_CACHE`) stores the full retinal intensity field
per unique (aperture, M) combination, uncapped. Each field is `grid_N x grid_N` float64
-- 33.5MB at the old `grid_N=2048`, but **134MB at the new default of 4096** (4x the
pixels). The sweep's own grid touches 75 unique (aperture, M) pairs; caching all of them
simultaneously, as the unbounded cache did, needs ~10GB just for this one cache -- a
cost the Defect-1 fix's own writeup did not check, because it only verified accuracy and
exclusion behaviour, not memory footprint at the new resolution.

**Fix**: `_PSF_FIELD_CACHE` is now a size-capped `OrderedDict` (FIFO eviction,
`_PSF_FIELD_CACHE_MAX_ENTRIES=20`), reasoned from the sweep's own access pattern (one
myopia level's worth of apertures is reused repeatedly, then never touched again once
that level's pitches are exhausted -- so only one M-level's apertures, at most 15 in
this project's own aperture list, need to stay resident at a time). Verified, not
assumed: cycling through 25 unique (aperture, M) combinations with real propagations
showed peak memory plateau at ~3.96GB once the cache filled to its 20-entry cap, and
staying there as further combinations were processed (cache length never exceeded 20).

**`corrected_regime.py`'s separate `_PSF_CACHE`** (used by the ghosting classifier, a
different cache from the one above) was checked for the same pattern and found NOT to
have it: it stores only the radial MTF profile (a 1D array of a few thousand floats)
and scalar quantities, never the raw 2D field -- confirmed by reading its actual stored
dict, not assumed from the surface similarity of "another PSF cache." No change made
there.

This is reported because it is exactly the kind of consequence the task's own
instructions asked to be caught rather than smoothed over: fixing Defect 1's numerical
limitation (grid resolution) introduced a new, unrelated engineering limitation (memory)
that only a real, full-scale re-run exposed. The sweep was restarted after this fix.

---

## Addendum: old vs new headline numbers, after both defects and the memory fix (2026-08-14, third pass concluded)

`multi_hole_blur_sweep.csv` and `optimise.py`'s outputs were regenerated end to end
from the fixed code (Defect 1: `grid_N=4096` + bounded cache; Defect 2: formula wiring
verified, no code change needed since it was already correct). Old (defect-carrying)
versions preserved at `*_legacy_gridN2048.csv`, never overwritten.

### What changed

**r_max_lens exclusion: 100% -> 0%.** Every one of the 1370 (aperture, pitch, myopia,
packing) points swept now completes with zero holes dropped as unrepresentable
(`multi_hole_blur_sweep.csv`'s own printed summary). Direct consequence: the largest
blur ratio found rose from **11.70x** (defect-carrying, itself a lower bound) to
**17.24x** single-hole blur (a=400um, s=2700um, M=8D, square) -- higher, not lower,
because holes that were being silently dropped are now correctly included.

**The optimiser's own answer changed at M=4-8D, hex packing -- and the earlier report
of it was wrong.** RECOMMENDATION.md's prior Addendum stated hex's "optimal" design at
M=4-8D was N_eff_worst=1 with a continuous risk of 98-137 (a live instance of the
Regime-A blind spot). That is **superseded**: with corrected blur, hex's optimum moves
to the SAME sparse, N_eff_worst=0, zero-risk design square already preferred
(a=2000um, s=4200um). Traced to source, not just observed: at the point hex used to
pick (a=2000, s=2200), `blur_ratio` **roughly doubled** once previously-excluded
off-axis holes were correctly included (M=4D: 4.116->8.250; M=6D: 5.433->10.657; M=8D:
6.116->11.951), while the sparse alternative's blur_ratio barely moved (4.116->4.103,
since it was never affected by the exclusion). `risk` itself is **numerically
identical** before and after (136.63, 116.45, 98.27 unchanged) -- ghosting
classification does not depend on `array_psf_envelope.py` at all, confirming the flip
is entirely a blur-side correction, not a ghosting-side one.

**What did NOT change**: F2's own headline finding -- 541/1370 points across the full
grid labelled "safe" (Regime A) while carrying risk >10x the CSF threshold -- is
**numerically identical** before and after (560/1370 at risk>1, 541/1370 at risk>10, in
both the legacy and corrected grids). This finding never depended on either defect: it
is a property of the alignment-counting / harmonic-margin machinery, untouched by the
grid-resolution fix (blur-only) or the formula-wiring check (already correct).

### Updated optimum table (default weights, corrected data)

| M | packing | a (µm) | s (µm) | N_eff(worst) | risk | blur_ratio |
|---|---|---|---|---|---|---|
| 1D | hex | 600 | 700 | 27 | ~0 | 3.49x |
| 1D | square | 600 | 700 | 23 | ~0 | 3.49x |
| 2D | hex | 600 | 700 | 27 | 38.6 | 6.26x |
| 2D | square | 400 | 700 | 23 | 1.8 | 6.34x |
| 4D | hex | 2000 | **4200** | **0** | **0.0** | 4.10x |
| 4D | square | 2000 | 4200 | 0 | 0.0 | 4.11x |
| 6D | hex | 2000 | **4200** | **0** | **0.0** | 5.44x |
| 6D | square | 2000 | 4200 | 0 | 0.0 | 5.44x |
| 8D | hex | 2000 | **4200** | **0** | **0.0** | 6.13x |
| 8D | square | 2000 | 4200 | 0 | 0.0 | 6.13x |

(bold = changed from the pre-fix table). **N_eff_worst>=1 now occurs at 4/10 optima
(down from 7/10), all of them at M=1-2D** -- at M=4-8D, both packings now agree on the
same sparse, zero-risk answer, where they previously disagreed. The M=1-2D result (dense
wins, for the same reasons as before: genuinely negligible risk at M=1D, brightness-
dominated at M=2D) is unaffected by either defect and stands as previously reported.

**Sensitivity finding is qualitatively unchanged**: the M=4D/square answer still flips
within a factor of 2-4 of default on `w_ghost`/`w_bright`/`w_dark` (only `w_blur`'s
threshold moved, from "stable across the whole tested range" to "flips at 8x" -- a
minor tightening, not a reversal). The brightness-domination finding
(`RECOMMENDATION.md`'s Addendum) stands as previously reported.

---

## Addendum: Stage 3 built, and a genuine ambiguity found and resolved in its own spec (2026-08-15)

`array_optimization/stage3_decision/decide.py` gates candidates on a hard safety
condition (worst-case-across-M ghosting risk below threshold, pitch margin to its own
no-ghost ceiling) then ranks survivors by Pareto dominance on (blur, transmission) --
not a weighted scalar cost, precisely because `optimise.py`'s own sensitivity finding
showed a scalar objective is under-constrained at M=4-8D. This does not collapse to a
single winner: the front reports every non-dominated candidate.

**A real bug found while building it, not shipped silently**: the requesting task's own
phrasing ("pitch as % of its own no-ghost ceiling, flag >70% as insufficient margin")
is ambiguous about direction, and the first implementation picked the wrong one --
requiring `margin_fraction <= 0.7` to pass excluded every structurally-safe design
(pitch at or beyond `s_solo`, fraction >= 1.0) while admitting dense, risky designs
(e.g. a=75um, s=700um, fraction=0.18, safely "under 70%" by that broken rule). Caught
because the output was nonsensical on inspection (the two "recommended" designs were
the smallest aperture at the smallest pitch, with 229um of blur) rather than trusted
because the code ran without error. Fixed to `margin_fraction >= threshold`
(default 1.0, i.e. the bare `s_solo` bound already established throughout this
project) -- see `decide.py`'s own `DEFAULT_MARGIN_THRESHOLD` comment for the full
reasoning, kept there since that is where a future reader will look when tuning it.

**Result after the fix**: 274 unique (aperture, pitch, packing) candidates; 90 pass the
hard safety gate; 20 on the Pareto front. All 20 recommended designs have
`N_eff_worst_across_M=0` (structurally ghost-free, not just statistically) and
`objective_sensitive=False` -- none of the current recommendations rest on the fragile
category RECOMMENDATION.md's third-pass Addendum found needed correcting once already.
Full table: `array_optimization/stage3_decision/array_candidates.csv`.

**Scope limitation carried forward, not hidden**: `r_EE_80_um` in that CSV is actually
r_EE_50 (alignment-mean, worst-case-across-M) -- `multi_hole_blur_sweep.py` never
recorded r_EE_80, and re-running that ~70-minute sweep a third time solely to add it
was not done here. Stated in `decide.py`'s own module docstring as this pipeline's next
concrete improvement if a stricter blur metric is needed.
