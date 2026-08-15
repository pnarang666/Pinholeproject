# Current best-defensible array design region

**This is a theoretical region pending experimental confirmation, not a manufacturing
specification.** No array-specific prediction anywhere in this project has been checked
against a physical sample (`ANALYSIS.md` G4). It is stated as a bounded region with every
edge attributed to a named constraint, and it is deliberately **not** collapsed to a
single recommended aperture and pitch — no joint optimisation over (diameter, pitch) has
ever been run, here or earlier (`ANALYSIS.md` G1), so a single pair of numbers would be
an invention, not a result.

Everything below is conditioned on: **D_pupil = 4 mm**, d_gap = 12 mm, λ = 550 nm,
P0 = 60 D, axial myopia, on-axis viewing, and the corrected optics of `stage2_fixed`
(post lens-wavelength-fix). The pupil conditioning is the load-bearing one — see
"What moves the region" below.

---

## The region

| | M = 1 D | M = 4 D | M = 8 D |
|---|---|---|---|
| **hole diameter** | 700 – 1500 µm | 400 – 600 µm | 300 – 400 µm |
| **pitch** (square packing) | 3.94 – 4.4 mm | 3.94 – 4.4 mm | 3.94 – 4.4 mm |
| **pitch** (hex packing, preferred) | 4.00 – 4.5 mm | 4.00 – 4.5 mm | 4.00 – 4.5 mm |
| resulting blur r_EE_50 (one hole active) | ~7.3 µm | ~12.0 µm | ~17.9 µm |
| light reaching the retina, mean over eye positions (hex, across both the diameter and pitch ranges above) | 2.3 – 12.9 % | 0.7 – 2.1 % | 0.4 – 0.9 % |
| the same, square | 2.0 – 11.6 % | 0.7 – 1.9 % | 0.4 – 0.8 % |
| fraction of eye positions with **no** hole in the pupil | hex 8 – 26 %, square 18 – 35 % | same | same |

(The brightness rows span the diameter band as well as the pitch band, so their low end
is the smallest hole at the widest pitch. Retinal illuminance scales as the hole area,
so the diameter choice moves it ~3× across the M = 1 D band and ~2× across the others —
more than the pitch choice does.)

The diameter axis moves with myopia; **the pitch axis does not**, because the pitch
bounds come from pupil geometry (how many holes fit in a 4 mm circle) and pupil geometry
does not know about refractive error. That is the single most useful structural result of
putting the three constraints on one plot: *myopia shifts the region horizontally only*
(`joint_design_space.png`, three panels).

## Which constraint bounds which edge

| edge | bounded by | value and source |
|---|---|---|
| diameter, **lower** | **diffraction** — smaller holes blur more, not less | the rising left branch of r_EE_50(a) in `single_hole_reference/r1_multi_EE_sweep_postfix.csv` (post-fix `stage2_fixed` R1 sweep) |
| diameter, **upper** | **geometric defocus** — larger holes admit a wider defocused pencil | the rising right branch of the same curve; the +10 % tolerance sets where it is cut |
| pitch, **lower** | **GHOSTING** — below s_solo two holes can be in the pupil at once, and each makes its own displaced copy of the scene | s_solo = **3.94 mm** (square) / **4.00 mm** (hex) at D_pupil = 4 mm, measured in `joint_design_space.py::pitch_thresholds`; closed form s > D_pupil |
| pitch, **upper** | **BRIGHTNESS** — the wider the pitch, the more eye positions see no hole at all and the view goes momentarily black | P(0 holes) from `alignment_fractions.csv`: hex 5 % at 3.9 mm → 8 % at 4.0 mm → 16 % at 4.2 mm → 26 % at 4.5 mm (square 18 % at 3.9 mm → 29 % at 4.2 mm → 35 % at 4.4 mm). The 4.4–4.5 mm cut is a **tolerance choice**, not a physical wall — pick your own from that table. |

The lower pitch edge is hard: above s_solo the *maximum* N_eff over all pupil alignments
is 1, so a second copy cannot exist and ghosting is ruled out by geometry rather than by
a perceptual model. The upper pitch edge is soft and is the only place a designer has a
real dial to turn.

## Why hex, and by how much

Hex packing dominates square on every geometric measure (`ANALYSIS.md` G2): it keeps the
pupil covered up to a 21 % larger pitch (s_dark 3.49 mm vs 2.88 mm), it halves the width
of the unavoidable-compromise gap (514 µm vs 1059 µm), and at its best pitch the wearer
is in the wanted single-hole state **93 % of the time against 83 %**, with the blackout
rate cut from 13 % to 5 %. The caveat is stated in G2 and is not small: no ghosting
regime sweep, MTF/CSF margin or multi-hole PSF has been computed for hex at all — the
advantage above is packing geometry alone.

## Regions that look feasible on the plot and are not

**The "never dark" band, pitch 2.1 – 2.88 mm (square).** `joint_design_space.png` outlines
it because the classifier calls it Regime A and the worst-case N_eff never reaches 0.
Reject it, on two independently sufficient grounds:
* *Ghosting*: Regime A there is an artifact of reading the **minimum** N_eff
  (`ANALYSIS.md` F2). At 2.5 mm pitch, two or more holes are in the pupil at **82 %** of
  eye positions.
* *Blur*: this band is the **worst** part of the whole design space for acuity. At
  M = 4 D, a = 400 µm, s = 2.8 mm, the array's blur radius swings between 13.2 µm (eye
  centred on a hole) and **141.6 µm** (eye centred on a lattice-cell corner, 4 holes in
  the pupil) as the wearer merely looks around — against a full-open-pupil blur of
  142.9 µm. At that alignment the pinhole benefit is entirely gone while 98 % of the
  light is still being thrown away.

**The dense Regime B window at low myopia, pitch < ~1.4 mm at M = 1 D.** This one is
genuinely ghost-safe — the comb frequency (25.9 cpd at a = 400 µm, s = 900 µm) is past
the incoherent cutoff of the eye's own optics, so it cannot be imaged at all
(`ghosting/RESULTS.md` Pass 4 §3). Reject it on **blur** (`ANALYSIS.md` F4): with
13–25 holes in the pupil the retinal blur is 2.0–2.9× the single-hole value at M = 1 D
and 7–17× at M = 4–8 D, approaching the unaided full-pupil blur. It is ghost-free because
the copies have been smeared into each other, which is the same thing as having no
pinhole effect. It also disappears entirely by M = 4 D.

**Anywhere below the pitch = diameter line.** The holes would overlap; it is not an array.

## Status of the ghosting boundary specifically

Step 2 of this consolidation settled the formula the ghosting boundary rests on. The old
`Δr = s·v_r/d_gap` is wrong (it does not vanish for an emmetropic eye); the correct
separation is `Δr = s·M/(P0−M)`, confirmed by an independent ray trace, by a wave-optics
propagation through this project's own unmodified pipeline agreeing to within half a grid
pixel at every M, and by the M = 0 limit. **The recommended region's lower pitch edge does
not depend on that resolution at all** — s_solo is pure lattice-in-a-circle geometry, and
would sit at the same place under either formula.

What the resolution does change is how much confidence to place in the *rejections*
above, and there the picture improved: the corrected formula puts the relevant
frequencies at 2.9–8.3 cpd, inside the Barten (1999) CSF's stated 0.2–50 cpd validity
range and near its best-constrained peak, instead of the 0.1–0.3 cpd where Passes 1–3 were
extrapolating below the model's floor.

Three things about the ghosting boundary remain genuinely open:
1. **Worst-case vs typical.** Regime C is a binary verdict on a worst-case alignment. The
   honest quantity is a risk — P(≥2 holes) × perceptual margin — and it has not been
   computed (`ANALYSIS.md` I2). This affects how sharply the rejected 2.1–2.88 mm band
   should be rejected, not where the recommended region is.
2. **Whether the Barten model transfers.** It is calibrated for sharp, foveal, ordinary
   viewing, not for a defocused near-eye ripple. Unchanged from `THEORY.md` §5 and still
   unresolved by anything computational.
3. **Hex has never been run through the ghosting model** (G2), and hex is what this
   document prefers.

## What moves the region

**Pupil diameter, more than anything else** (`ANALYSIS.md` G5). Both pitch bounds scale
with D_pupil: s_solo is 1.97 mm at a 2 mm pupil and 5.91 mm at a 6 mm pupil. A 4 mm-pitch
array is ghost-free for a 4 mm pupil, ghost-capable for a 5 mm pupil in dim light, and
mostly black for a 2 mm pupil in bright sun. **No single pitch keeps N_eff = 1 across a
2–6 mm pupil range, for either packing.** Every number in this document is a
D_pupil = 4 mm number, and a design intended for real use across lighting conditions
cannot inherit them unconditionally.

**Grid resolution, on the diameter axis at low myopia.** Inside the M = 1 D band, r_EE_50
is *numerically identical* (7.327531 µm) at 700, 750, 1000 and 1250 µm in the R1 sweep —
that is the encircled-energy radial binning hitting its floor (≈2.5 grid pixels), not a
genuinely flat optimum. So the M = 1 D diameter is **unresolved between 700 and 1250 µm**
(1500 µm is a real 8 % worse and is in the band only because of the +10 % tolerance).
Since brightness scales as the hole area and blur is unresolved across that span, the
larger end of the band is the better bet at M = 1 D on present evidence — but that is an
argument from the absence of a resolved difference, and a finer grid could remove it.
M = 4 D and M = 8 D are not affected: their optima are resolved.

**A multi-hole blur optimum** (`ANALYSIS.md` I1) **has since been computed** — see the
Addendum below. It does not shift the bands above (they remain valid where they were
always valid: the N_eff ≤ 1 corner), but it does change what can be said about the rest
of the plot, including whether an N_eff > 1 design should be recommended at all.

---

## Addendum (2026-08-14, second pass): a scored optimum, and a direct answer on N_eff > 1

> **SUPERSEDED IN PART — see the third-pass Addendum below.** Two defects were found
> in the code this section's numbers came from (100% of the multi-hole blur sweep was
> silently dropping off-axis holes; the ghost-formula wiring had never been unit-
> tested). Once fixed, **the hex M≥4D finding below ("optimal" design accepts real
> ghosting risk) reverses** — hex's corrected optimum matches square's (safe,
> zero-risk). Left unedited below as the record of what was reported before that audit;
> read the third-pass Addendum for what is currently trusted.

Everything above is Step 3's feasible REGION, unchanged. This addendum reports what
happened when that region was turned into an actual scored surface —
`multi_hole_blur_sweep.py` (the true multi-hole blur, swept, not spot-checked),
`ghosting_risk.py` (a continuous risk replacing the binary Regime-A blind spot), and
`optimise.py` (a joint optimiser with every weighting named and its sensitivity
reported). Full derivation and numbers: `ANALYSIS.md`'s second-pass Addendum.

**Does an array with N_eff > 1 ever beat a single pinhole? Yes, unambiguously, at low
myopia — and even at higher myopia the "optimal" hex answer accepts real ghosting risk
rather than avoiding it.** At default weights, per (M, packing):

| M | packing | a (µm) | s (µm) | N_eff(worst) | regime | risk | blur×single | brightness |
|---|---|---|---|---|---|---|---|---|
| 1 D | hex | 600 | 700 | 27 | B (imperceptible) | ~0 | 2.4× | 66.9% |
| 1 D | square | 600 | 700 | 23 | B | ~0 | 2.3× | 57.7% |
| 2 D | hex | 600 | 700 | 27 | **C (danger)** | 38.6 | 4.1× | 66.9% |
| 2 D | square | 400 | 700 | 23 | C | 1.8 | 4.5× | 25.7% |
| 4 D | hex | 2000 | 2200 | 1 | A* | **136.6** | 4.1× | 74.2% |
| 4 D | square | 2000 | 4200 | 0 | A | 0 | 4.1× | 17.7% |
| 6–8 D | hex | 2000 | 2200 | 1 | A* | 98–116 | 5.4–6.1× | 74.2% |
| 6–8 D | square | 2000 | 4200 | 0 | A | 0 | 5.4–6.1× | 17.7% |

*hex's M ≥ 4 D "A" is exactly the Regime-A blind spot this document's own ghosting
section warns about (F2): N_eff_worst = 1 satisfies the binary rule, while the
continuous risk (98–137) says the same design is deep in danger-zone territory.

**At M = 1 D dense wins for free** (the ghost comb is past the eye's own perceptual
cutoff, risk ≈ 0). **At M = 2 D dense wins despite real, nonzero ghosting risk**, purely
because brightness (26–67%, against ~1% for a well-chosen single pinhole) overwhelms
every penalty term. Whether that trade is one you want is a value judgement this
document cannot make for you — which is exactly why the next paragraph exists.

**This conclusion is NOT robust, and is reported as such rather than smoothed over.**
The optimiser's own sensitivity sweep found the M = 4 D / square answer flips to the
dense, risky option at just **0.5× the default ghosting-risk weight, or 2× the default
brightness weight** — well inside any reasonable range of disagreement about how those
two things should trade off. The mechanism: brightness scales with N_eff × hole area
and reaches 17–75% across the design space, while the stated brightness reference
(1%, "roughly a well-chosen single pinhole") does not compress that range — so
brightness can dominate the score by a factor the other terms never approach. This is
stated as a finding about the **scoring model's calibration**, not the physics, and
should be read as: *the physics does not force a single answer here; the answer moves
with a value judgement about brightness vs. risk that this analysis explicitly declines
to make for you.*

**What did NOT move**: the region's own edges (diameter and pitch bounds above) are
unaffected — the optimiser searched *inside* that region (plus the N_eff > 1 zone the
region plot deliberately excludes) and its instability is about *where inside/beyond
it* to land, not about the region's boundaries themselves.

**Still theoretical, still unconfirmed**: every number above inherits every caveat
already stated in this document and in `ANALYSIS.md` — plus one new one:
`multi_hole_blur_sweep.py`'s blur numbers are a measured LOWER BOUND at every single
point swept (r_max_lens grid exclusion triggered at 100% of 1370 points), so the true
blur at N_eff > 1 is somewhat worse than tabulated above, not better.

---

## Addendum (2026-08-15, third pass): two defects fixed, and the hex finding above reverses

Two defects were found blocking trust in the second-pass Addendum's numbers, both
diagnosed by direct instrumentation rather than assumed (full derivation:
`ANALYSIS.md`'s third-pass Addenda):

1. **`r_max_lens` exclusion (100% of the 1370-point sweep).** Confirmed a pure grid-
   resolution limit, independent of every design parameter tested — `stage2_fixed`'s
   own pre-existing diagnostic had already flagged it as untested beyond single-hole
   use. Fixed by raising `grid_N` 2048→4096; re-verified with zero exclusions across a
   48-point scan including the worst case. A second, unrelated memory defect
   (unbounded PSF-field cache, 134MB/entry at the new grid resolution) was found and
   fixed while regenerating the sweep at scale — see `ANALYSIS.md` for that incident.
2. **The ghost-separation formula's validity.** Built an independent two-hole
   propagation harness (`array_optimization/stage0_ghost_validation/`) — a genuine
   joint-aperture coherent propagation plus an incoherent-sum reference, delta_r
   measured by peak detection, not formula lookup. Result: the corrected formula fits
   32 independently-measured points at R²=0.995 and passes the M=0 gate (measured
   separation = 1 grid pixel, the method's own floor); the legacy formula scores
   R²=-1701.7. `ghosting_risk.py`'s actual runtime wiring was then unit-tested (not
   assumed from the parameter's name) and found to already call the validated
   formula's own function exactly — no code change was needed there, only verification.

**What changed in the optimum table above**: only Defect 1 (blur), since Defect 2
required no code change. Regenerated end to end from the fixed code (old,
defect-carrying versions preserved at `Array_Design/*_legacy_gridN2048.csv`):

| M | packing | a (µm) | s (µm) | N_eff(worst) | risk | blur×single |
|---|---|---|---|---|---|---|
| 1 D | hex | 600 | 700 | 27 | ~0 | 3.5× |
| 1 D | square | 600 | 700 | 23 | ~0 | 3.5× |
| 2 D | hex | 600 | 700 | 27 | 38.6 | 6.3× |
| 2 D | square | 400 | 700 | 23 | 1.8 | 6.3× |
| 4 D | hex | 2000 | **4200** (was 2200) | **0** (was 1) | **0.0** (was 136.6) | 4.1× |
| 4 D | square | 2000 | 4200 | 0 | 0.0 | 4.1× |
| 6 D | hex | 2000 | **4200** (was 2200) | **0** (was 1) | **0.0** (was 116.4) | 5.4× |
| 6 D | square | 2000 | 4200 | 0 | 0.0 | 5.4× |
| 8 D | hex | 2000 | **4200** (was 2200) | **0** (was 1) | **0.0** (was 98.3) | 6.1× |
| 8 D | square | 2000 | 4200 | 0 | 0.0 | 6.1× |

**hex's M≥4D "optimal" answer no longer accepts ghosting risk — it now matches
square's safe, zero-risk design.** Traced to source, not just observed: at the point
hex used to pick (a=2000, s=2200), `blur_ratio` roughly *doubled* once previously-
excluded off-axis holes were correctly included (M=4D: 4.12→8.25×), making that design
cost more than the sparse alternative under the *same* weights that previously favoured
it. `risk` itself is numerically **identical** before and after (98.3–136.6 unchanged)
— the reversal is entirely a blur-side correction; the ghosting classification was
never wrong here, the blur feeding the cost function was.

**Revised answer to "does an N_eff>1 optimum exist?"**: yes, still, but now *only* at
M=1-2D (4/10 optima, down from 7/10) — at M=4-8D both packings now agree on the same
sparse answer, where they previously disagreed. The M=1-2D result and the sensitivity
finding (the M=4D/square answer still flips within a factor of 2-4 of default on
`w_ghost`/`w_bright`) are **unaffected by either defect** and stand exactly as the
second-pass Addendum reported.

**F2's own headline finding is also unaffected**: 541/1370 points across the full grid
still labelled "safe" while carrying risk >10× the CSF threshold, numerically identical
before and after — ghosting classification never depended on either defect.

This correction is reported plainly rather than smoothed over because the task
demanding this audit explicitly required it: a wrong intermediate number (the blur
value) had been dressed up as a physically meaningful finding ("hex accepts real
risk") that a closer, independently-verified computation does not support.
