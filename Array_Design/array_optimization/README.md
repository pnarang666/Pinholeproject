# array_optimization/

A staged pipeline built on top of `Array_Design/`'s validated array-design modules,
after auditing and fixing two defects that were found to block trusting the numbers
`Array_Design/`'s second-pass Addendum reported (`ANALYSIS.md`'s third-pass Addendum
has the full diagnosis of both). This folder does not re-derive any physics — every
stage wraps or directly reuses `Array_Design/`'s own modules, now fixed.

## The two defects this pipeline exists to have fixed before being trusted

**Defect 1 — `r_max_lens` excluding 100% of the prior multi-hole blur sweep.**
Diagnosed by direct instrumentation (not assumed): `r_max_lens` is a pure function of
the fixed simulation grid (wavelength, the emmetropic focal length, and pixel size),
identical across every aperture and myopia level tested, and was permanently smaller
than the eye's physical pupil radius at the old grid resolution — meaning holes in the
outer ~22% of the pupil were being *excluded*, not approximated, at every design point
tested. Not a crop-window bug, not a second units bug (both directly ruled out). Fixed
by raising `grid_N` 2048→4096 in `array_psf_envelope.py`, which pushes the limit past
the pupil radius with margin; re-verified with zero exclusions across a 48-point scan
including the worst case (largest aperture at the pupil edge).

**Defect 2 — the ghost-separation formula, unconfirmed against a real measurement.**
Two candidate formulas were in circulation; neither had been checked against an actual
propagated intensity pattern, only against each other algebraically. `stage0/` below
built an independent two-hole propagation (not a reuse of either formula's own code)
and measured the peak separation directly by peak detection. Result: the corrected
formula (`delta_r = s*M/(P0-M)`) fits 32 independently-measured points at R²=0.995 and
passes the M=0 gate (measured separation = 1 grid pixel, the method's own floor); the
legacy formula (`delta_r = s*v_r/d_gap`) scores R²=-1701.7 — categorically wrong, not
just imprecise. `ghosting_risk.py`'s actual runtime wiring was then unit-tested (not
assumed from the parameter's name) and found to already call the validated formula's
own function exactly.

## Folder structure

```
array_optimization/
  stage0_ghost_validation/   Defect 2's independent validation harness + its outputs.
                              RUN THIS FIRST — see "How to run Stage 0" below.
  stage1_field_sim/           CLI wrapper around the fixed field engine
                              (Array_Design/array_psf_envelope.py). Includes a runtime
                              gate that refuses to run if grid_N is too coarse to
                              represent the full pupil (Defect 1's exact condition).
  stage2_classification/      CLI wrapper around the fixed classifier
                              (Array_Design/ghosting_risk.py). The continuous risk is
                              the SOLE decision input from here on; the old binary
                              A/B/C gate is deprecated for decision-making (still
                              computed and shown for reference, never gated on).
  stage3_decision/            NEW: packing choice, transmission, Pareto front, margin
                              flag, ranked candidates. Built only after Stage 0-2 were
                              verified against the regenerated (Defect-1-and-2-fixed)
                              sweep data — see "Why Stage 3 waited" below.
```

**Why the engine files were not physically moved here**: `array_psf_envelope.py`,
`ghosting_risk.py`, and `corrected_regime.py` still live in `Array_Design/` and
`Array_Design/ghosting/` because several other, already-working scripts there
(`multi_hole_blur_sweep.py`, `optimise.py`, `joint_design_space.py`) import them from
their current locations. Relocating them would mean updating every one of those call
sites under this task's own time constraints, for no functional benefit — the stage
folders here import them via `sys.path`, exactly as every other cross-reference in
this project already does. This is a stated architecture choice, not an oversight.

## How to run Stage 0 standalone, and verify it passes before anything else

```bash
cd stage0_ghost_validation
python3 validate_ghost_formula.py --help          # all CLI params, see below
python3 validate_ghost_formula.py                 # full sweep, ~13-15 min at grid_N=4096
```

**What "PASS" means, and where to see it**: the script prints an `=== M=0 gate ===`
section. It must print `M=0 -> delta_r~0 check: PASS`. If it prints `FAIL`, the script
stops itself before fitting any formula and dumps full diagnostic state (grid
resolution, per-point measurements) — **do not proceed past a FAIL**, per this
project's own stated policy: an M=0 failure means the propagator or peak-detector is
wrong, not that a formula needs adjusting, and fitting formulas to unreliable
measurements would not be meaningful. A PASS also prints an R² table for all three
candidate formulas (legacy, corrected, free empirical fit) — the corrected formula
should be the clear winner (R² > 0.99) before any other stage is trusted.

Every numeric parameter is CLI-configurable (no hardcoding): `--P0`, `--n_prime`,
`--D_pupil_um`, `--wavelength_nm`, `--d_gap_mm`, `--a_hole_um`, `--grid_N`,
`--window_L_mm`, `--M_list`, `--pitch_list_um`. Re-running Stage 0 with a different
`--grid_N` (e.g. to check convergence) or a different eye model (`--P0`, `--n_prime`)
re-validates the formula under those conditions rather than assuming today's numbers
transfer.

## Full pipeline run instructions

```bash
# 0. Validate the ghost formula (once; re-run if any optics parameter changes)
cd stage0_ghost_validation && python3 validate_ghost_formula.py
# check PASS before continuing (see above)

# 1. Field engine sanity check (one design point; the real sweep is
#    Array_Design/multi_hole_blur_sweep.py, which stage1 wraps)
cd ../stage1_field_sim && python3 field_sim.py --a_hole_um 400 --pitch_um 900 --M_diopters 4

# 2. Classifier sanity check (one design point; the real sweep is
#    Array_Design/ghosting_risk.py, which stage2 wraps)
cd ../stage2_classification && python3 classify.py --a_hole_um 400 --pitch_um 900 --M_diopters 4

# 3. The actual sweep + decision output (after 0-2 all pass)
cd ../../  # back to Array_Design/
python3 multi_hole_blur_sweep.py     # ~70-75 min at grid_N=4096, measured, not
                                      # projected -- see ANALYSIS.md's Defect-1
                                      # Addendum for why this is slower than
                                      # grid_N=2048's ~14 min, and for a MEMORY
                                      # DEFECT found and fixed the first time this
                                      # was run at grid_N=4096 (an unbounded PSF
                                      # cache drove the host machine into full swap
                                      # and a 100%-full disk -- fixed with a
                                      # size-capped cache; re-run confirmed stable
                                      # memory throughout, peaking under 4GB)
python3 optimise.py                  # ~10-11 min, adds ghosting risk + brightness
                                      # to the sweep's grid
python3 array_optimization/stage3_decision/decide.py   # seconds
```

Stage 3's `array_candidates.csv` is the pipeline's final output. Verified end-to-end
result (2026-08-15): 274 unique (aperture, pitch, packing) candidates; 90 pass the hard
safety gate; **20 on the Pareto front**, spanning 400-2000µm aperture / 17.3-109.5µm
blur / 0.57-20.6% transmission, all `N_eff_worst_across_M=0` (structurally ghost-free)
and `objective_sensitive=False`.

## What `recommended_for_prototyping: true` guarantees, and what it does NOT

**Guarantees**: the design's pitch is AT OR BEYOND its own no-ghost pitch ceiling
(`s_solo`, the pitch above which the maximum possible N_eff over every pupil alignment
is 1 — a structural, geometry-only guarantee, not a statistical one) by at least the
stated margin (default: `margin_fraction_of_ceiling >= 1.0`, i.e. the bare ceiling
itself — see stage3's own `--margin_threshold` flag to require a buffer above it, e.g.
`1.3` for 30% headroom). See `decide.py`'s own `DEFAULT_MARGIN_THRESHOLD` comment for
why this direction was chosen deliberately: the requesting brief's "flag >70% as
insufficient margin" phrasing was ambiguous, and the first implementation had it
backwards (verified wrong by inspection, not merely asserted — see ANALYSIS.md). Also
guaranteed: worst-case-across-M continuous ghosting risk below the safe threshold
(`stage2_classification.RISK_SAFE_THRESHOLD`, currently 1.0 — the point where the
probability-weighted worst-harmonic margin crosses the CSF detection threshold), and
transmission/blur sitting on the Pareto front among designs meeting both conditions.

**Does NOT guarantee**:
- **Hole-diameter manufacturing tolerance.** Every number in this pipeline assumes
  hole diameters are produced exactly as specified. No sensitivity analysis to
  realistic manufacturing variance (laser-drilling or etching tolerance on a 300-2000µm
  feature) has been run anywhere in this project. A design flagged
  `recommended_for_prototyping: true` could fail its own margin if manufactured holes
  drift even a few percent from spec — this is an open gap, not a checked-and-passed
  condition. Only *pitch* margin is checked; *diameter* margin is not.
- **The stated blur metric is r_EE_80.** It is r_EE_50 (alignment-mean,
  worst-case-across-M) in the current `array_candidates.csv`, column-named `r_EE_80_um`
  to match this task's requested schema literally — `multi_hole_blur_sweep.py` never
  recorded r_EE_80, and adding it means a third ~70-minute re-run of that sweep, not
  done here. Stated in `decide.py`'s own docstring; this pipeline's clearest next
  concrete improvement if a stricter (broader-encircled-energy) blur metric matters for
  a manufacturing decision.
- **Blur/acuity fitness for a specific patient.** Stage 3 ranks on transmission and
  blur relative to other surviving designs, not against any clinical acuity target.
- **Physical validation of any kind.** No array-specific prediction anywhere in this
  project (including the Defect 1/2 fixes reported here) has been checked against a
  built sample. `recommended_for_prototyping: true` means "worth building a prototype
  of," not "already confirmed to work."
- **A specific transmission target (e.g. OD 0.6-0.8 / T 15-25%, a typical sunglass-lens
  spec).** No document in this project states a numeric %T or OD target for Stage 3 to
  gate on (the master pipeline doc's R2 states the *requirement* qualitatively —
  "achieve a target light-attenuation spec" — without a number), and `decide.py` only
  uses `T` as an unconstrained Pareto-maximization axis, never a filtered target window.
  Checked directly (`GAPS_CLOSED.md` Gap 4): of the 20 recommended designs, **only 3
  fall inside T 15-25%** (2 inside OD 0.6-0.8 exactly); the rest range down to 0.57%
  transmission — far darker than a typical sunglass spec. If a specific transmission
  target is later fixed, re-filter `array_candidates.csv` against it explicitly; do not
  assume `recommended_for_prototyping=True` already implies it.
- **A single resolved answer via a weighted objective.** `optimise.py`'s own
  sensitivity analysis found a scalar (blur/brightness/ghosting-weighted) objective's
  M=4-8D answer flips within a factor of 2-4 of default weightings
  (`Array_Design/RECOMMENDATION.md`'s third-pass Addendum) — Stage 3 does not use that
  scalar objective at all (see "Why a Pareto front, not a weighted score" in
  `decide.py`'s own docstring) precisely to avoid inheriting that instability, and
  instead flags any RECOMMENDED design whose safety rests on a statistical (not
  structural) margin as `objective_sensitive=True`. In the current run, none of the 20
  recommended designs carry that flag — all rest on the structural (N_eff_worst=0)
  guarantee, not the statistical one.

## vignetting.py — Chapter 13 field-of-view geometry (standalone-testable)

Implements the closed-form pupil-hole vignetting geometry already derived in
`IYPT_Pinhole_Theoretical_Handbook_2.pdf` Chapter 13 (§13.1 pupil displacement under eye
rotation, §13.2 circle-overlap area) — the physics is not re-derived here, only
implemented and validated. **Pure ray/aperture geometry, no dependency on
`array_psf_envelope.py` / `phase2_retina.py` / the ASM propagator** — deliberately
decoupled so this module cannot introduce a coupling bug into the wave-optics chain, and
so a purely geometric question doesn't pay for a wave-propagation's cost. It does reuse
`Array_Design/photometry/array_photometry.hole_lattice()` (the same lattice-enumeration
primitive Stage 2's own dependency chain already uses) for hole positions.

**Must be validated before being applied — run standalone first:**

```bash
cd array_optimization
python3 vignetting.py --validate    # geometry validation only (~4s): phi=0 -> full hole
                                     # area, large-phi -> exactly 0, explicit boundary
                                     # (Delta=Rp-Rh, Delta=Rp+Rh) no-NaN checks, and an
                                     # independent Monte Carlo cross-check. Must print
                                     # "validation verdict: PASS" before trusting anything below.
python3 vignetting.py --apply       # runs --validate first; refuses to proceed on FAIL.
                                     # Re-ranks the 20 Stage-3 candidates under
                                     # gaze-angle-averaged transmission/N_eff (~7s).
```

Outputs: `vignetting_validation.csv`/`.png` (the validation evidence itself),
`array_candidates_prevignetting_legacy.csv` (the pre-vignetting 20, preserved unmodified
per this project's audit-trail discipline), `array_candidates_field_averaged.csv` (the
re-ranked result).

**Result of the current run**: field-averaging over gaze angle (±25° swept, uniform
placeholder usage-weighting over ±15° — see caveat below) does **not** change which
designs are on the Pareto front — all 20 static (φ=0) recommendations remain recommended
under field-averaging. This is a genuine robustness finding, not a null result: it is
checked, not assumed, and the module also surfaces a real, non-obvious secondary effect —
several designs whose worst-case pupil alignment sees literally zero light at straight-
ahead gaze (`N_eff_worst_static_phi0=0`, this project's known "P_dark" property) see
**non-zero** average light once that same wearer's natural gaze range is integrated over
(`N_eff_worst_field_averaged` up to ~0.72) — i.e. eye movement can partially fill in an
otherwise-dark pupil alignment, not just vignette a bright one. See the module's own
docstring for why population-mean transmission is expected, on separate mathematical
grounds (translation-invariance of a mean over one full lattice period), to sit close to
its static value regardless of design — that near-invariance is a property of the
population-mean statistic, not evidence that gaze angle has no effect on any individual
wearer.

**w(φ), the gaze-usage distribution — UNSOURCED PLACEHOLDER, stated plainly.** No
document in this project (or the handbook) specifies a natural gaze-scanning-during-
scene-viewing distribution. `vignetting.py` defaults to uniform weighting over ±15°
(`--gaze_half_range_deg`) because no citable alternative was found — treat every
field-averaged number here as illustrating the *method*, not as a validated physical
claim, until a cited distribution replaces it.

**Not yet built** (deliberately, per this task's own scope limit): a single combined
acuity+transmission+ghosting-risk score. `vignetting.py` stops at validated geometry +
re-ranking the existing 20 — building a combined metric was deferred pending whether
vignetting actually changed anything (it didn't, for the Pareto front), so it remains
lower priority than if the top recommendation had flipped.

## Defect audit trail

Every regenerated output in this pipeline has its pre-fix (defect-carrying) version
preserved under an explicit `_legacy` name in `Array_Design/` (never deleted or
overwritten):

| current (fixed) | legacy (defect-carrying) |
|---|---|
| `Array_Design/multi_hole_blur_sweep.csv` | `Array_Design/multi_hole_blur_sweep_legacy_gridN2048.csv` |
| `Array_Design/optimise_grid.csv` | `Array_Design/optimise_grid_legacy_gridN2048.csv` |
| `Array_Design/optimise_best_per_M_packing.csv` | `Array_Design/optimise_best_per_M_packing_legacy_gridN2048.csv` |
| `Array_Design/optimise_sensitivity.csv` | `Array_Design/optimise_sensitivity_legacy_gridN2048.csv` |

See `ANALYSIS.md`'s third-pass Addendum for the full diagnosis and the old-vs-new
headline numbers side by side.
