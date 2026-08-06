# Lens-phase / retina-propagation wavelength mismatch: diagnosis, fix, and impact

## What this run was for

A brief alleged that `phase2_retina.run_pipeline_point()` applied the eye's lens
phase using the raw vacuum wavelength while propagating the same field to the
retina using `wavelength/n_prime` (the vitreous's effective wavelength) whenever
`refractive_index_correction=True` (the project default). The brief asked for
independent verification before any code was touched, and to STOP rather than fix
anything if the analysis turned out to be wrong.

This file reports what was actually verified, what changed, what didn't, and what
was discovered along the way that the original brief did not anticipate.

## Step 0: independent verification (before touching any code)

Confirmed directly from the code (not assumed from the brief):

- `myopia_axial.axial_length_for_myopia()`: `f_eye = L0 = n_prime/P0` — a
  vergence-equation distance (`REFRACTIVE_INDEX_CORRECTION` docstring: "distances
  inside the vitreous are measured with the vitreous's own refractive index"),
  ~22.27mm at P0=60D, n_prime=1.336. `REFRACTIVE_INDEX_CORRECTION = True` is the
  module-level default, and `validation_gate.run_validation_gate()`'s default is
  also `refractive_index_correction=True` — this is the project's normal operating
  configuration, not an edge case.
- `lens_phase(field, dx, wavelength, f_eye)` computed `k = 2*pi/wavelength` from
  whatever `wavelength` it was given.
- `run_pipeline_point()` called `lens_phase(field, dx, wavelength, f_eye)` with the
  raw input `wavelength` (vacuum), but called
  `propagate_to_retina(field, dx, wavelength, v_r, refractive_index_correction, n_prime)`,
  which internally computed `effective_wavelength = wavelength/n_prime` before
  propagating. Confirmed: the two functions received different physical
  wavelengths from the same call site whenever `refractive_index_correction=True`.

**Independent physics derivation** (two separate methods, cross-checked against
each other):

1. *Stationary-phase focus-location argument.* For a lens phase
   `exp(-i k_L x^2/(2f))` followed by Fresnel propagation at wavenumber `k_prop`,
   the quadratic phase vanishes (true geometric focus) at
   `z* = f * (k_prop / k_L)`. With the pre-fix code, `k_L = k_vacuum` and
   `k_prop = n_prime * k_vacuum` (from `propagate_to_retina`'s own correction), so
   `z* = f_eye * n_prime`, not `f_eye` — a ~33.6% axial focus error at
   `n_prime=1.336`, regardless of aperture size.
2. *Medium-agnostic optical-path-length argument.* For a refracting system with
   object-space index 1 (air) and image-space index `n'` (vitreous) and dioptric
   power `P`, the physically correct thin-element phase screen is
   `exp(-i k_vacuum P (x^2+y^2)/2)` (from the true optical-path-length difference,
   independent of which media surround the element). Substituting `f_eye=n'/P0`,
   this equals `exp(-i (k_vacuum n') (x^2+y^2)/(2 f_eye))` — i.e. the lens phase
   must use `k = k_vacuum * n'` (equivalently, `wavelength/n'`), exactly matching
   `propagate_to_retina`'s own convention.

Both methods agree with each other and with the brief's claim. **Verdict: the
brief's analysis is correct.** Proceeded to fix, per the brief's instructions.

## Step 1: pre-fix baseline

Captured before any code change, on branch `fix/lens-wavelength-consistency`:

- `validation_gate.py` (a_hole=150um, wavelength=550nm, grid_N=4096,
  window_L_mm=6.0, `refractive_index_correction=True`, M=0, d_gap=0): **PASS**.
  r_EE_50 error 1.14% (tol 2%), r_EE_80 error 4.56% (tol 8%), r_EE_90 error 0.55%
  (tol 2%). Saved: `outputs/prefix_baseline/validation_gate_output.txt`.
- R1 sweep (`recompute_multi_EE.py`, 15 apertures x M=[1,2,3,4,5,6,8]D, 550nm,
  12mm gap, `refractive_index_correction=True`): reproduced the documented optimum
  **exactly** — 300um for M=1-4D, 400um for M=5-8D — and matched the pre-existing
  `stage3a/multi_EE_sweep.csv` to floating-point precision (max abs diff 4e-13
  um). Saved: `outputs/prefix_baseline/multi_EE_sweep.csv`.

(One process note, corrected before it could contaminate anything: the first
attempt at this baseline sweep was run as a background job, and the fix was
applied to the source file *while that job was still running* — since each M
value spawns a fresh `python3` subprocess that re-imports the file from disk,
the later M values in that first run silently picked up the post-fix code. This
was caught by a sanity check (`stage3a/multi_EE_sweep.csv` was still supposed to
match exactly and initially showed a 48.6um discrepancy), the contaminated run
was discarded, and the baseline was re-captured cleanly with no code changes in
flight. Mentioned here only as a process note; the baseline actually used and
committed is the clean re-run.)

## Step 2: the fix

Changed only `stage2_fixed/phase2_retina.py`. `run_pipeline_point()` now resolves
`effective_wavelength = (wavelength / n_prime) if refractive_index_correction else
wavelength` **once**, and passes it to both `lens_phase()` and
`propagate_to_retina()` (the latter called with `refractive_index_correction=False`
explicitly, since the correction has already been applied — this keeps
`propagate_to_retina`'s own internal ternary a documented no-op from this call site
rather than a second, independently-editable copy of the same formula that could
silently drift out of sync again in the future, which is exactly the failure mode
that produced this bug).

Neither `lens_phase()` nor `propagate_to_retina()` had their **signatures**
changed, deliberately: `stage3_human_vision/metrics.py` calls both functions
directly (bypassing `run_pipeline_point()`) with the same pre-fix calling pattern,
and a signature change would have silently broken that caller. That file has the
identical bug, unfixed — see the downstream list below.

`myopia_axial.py`, `pipeline_junction.py`, and `stage1_v2/physics.py` were not
touched.

## Step 3: verification that nothing broke

- `validation_gate.py` post-fix: **PASS**, at the same, unchanged tolerances.
  Errors *shrank*, not just stayed within bounds: r_EE_50 1.14% -> 0.30%, r_EE_80
  4.56% -> 0.38%, r_EE_90 0.55% -> 0.94%. This is the expected direction if the
  fix is physically correct — the zero-defocus numeric focus now lands closer to
  where the closed-form Airy formula assumes it is. Saved:
  `outputs/postfix_validation_gate_output.txt`.
- `refractive_index_correction=False`: confirmed **bit-identical** pre- and
  post-fix at 3 representative configs (a=300um/M=2D, a=1000um/M=5D, and the
  validation-gate config itself), by directly diffing the pre-fix and post-fix
  file content and re-running both — e.g. r_EE_50 = `2.2556187675986086e-05` m,
  exact match to the last printed digit, at a=300um/M=2D. As a methodology check,
  confirmed the `True` path at the *same* config does change substantially
  (r_EE_50 23.42um -> 16.85um) — so the bit-identical `False` result is a genuine
  finding, not a test that would have passed either way.
- No tolerance was changed anywhere in this work.

## Step 4: quantified impact (R1 sweep, before vs. after)

**The documented "300um (M1-4D) / 400um (M5-8D)" result does not survive.**

| M (D) | opt. aperture: pre -> post | change | r_EE(50%) at opt: pre -> post | change |
|---|---|---|---|---|
| 1 | 300 -> 700 um  | **+133.3%** | 23.04 -> 7.33 um  | -68.2% |
| 2 | 300 -> 750 um  | **+150.0%** | 22.65 -> 8.01 um  | -64.6% |
| 3 | 300 -> 600 um  | **+100.0%** | 22.29 -> 10.57 um | -52.6% |
| 4 | 300 -> 500 um  | +66.7%      | 21.99 -> 12.02 um | -45.4% |
| 5 | 400 -> 500 um  | +25.0%      | 20.83 -> 13.29 um | -36.2% |
| 6 | 400 -> 400 um  | 0.0%        | 19.79 -> 14.47 um | -26.9% |
| 8 | 400 -> 400 um  | 0.0%        | 18.16 -> 17.87 um | -1.6%  |

Full data: `outputs/postfix_sweep/multi_EE_sweep.csv`,
`outputs/before_after_optimum_comparison.csv`.

**This is a large, real correction, not noise.** The pattern across M is
physically coherent, not arbitrary: the bug is a *fixed absolute* focal-shift
error (`f_eye * (n_prime - 1)`, ~7.5mm, independent of M). At low myopia the
retina sits close to the emmetropic focus, so this fixed error is a large
fraction of the eye's total defocus budget; at high myopia (M=6-8D), real axial
elongation already dominates and the same fixed absolute error becomes
proportionally negligible — consistent with the effect shrinking monotonically
from +150% at M=2D to 0% at M=6-8D.

**One observation, stated plainly and not overinterpreted:** the corrected
pure-blur optimum (400-750um) sits noticeably closer to both the
brightness-constrained optimum (900-1250um, `stage3a`) and the clinical bracket
(940-1750um) than the old 300-400um figure did. This narrows part of the gap that
the brightness-floor analysis (`stage3a/README.md`, `PROJECT_STATUS.md` Section 2)
was built to explain — but it does not close it, and re-deriving what fraction of
that gap was ever attributable to this bug versus a genuine missing-brightness
constraint is a real, separate analysis this file does not attempt. Flagged below
for follow-up, not claimed here.

No aperture recommendation is made anywhere in this file.

## Step 5: downstream model smoke tests

**`stage4_human_vision/tests/test_stage4.py`**: all 7 tests pass. However, on
inspection none of these tests exercise `phase2_retina.py` at all (they test
`pupil.py`, `csf.py`, `illuminance.py`, `visual_strehl.py`, `acuity.py`, and
`validation.py` as pure standalone functions) — this is a real pass, but not
meaningful evidence about the fix specifically.

**`R7acuity/run_validation_unified.py`**: ran to completion, no exceptions. The
resulting R^2/Pearson values are **bit-for-bit identical** to the pre-fix numbers
already documented in `RESULTS.md` (raw: R^2 = -24.62 / -28.06 / -19.10 for
M=0/2/5D; efficiency-corrected eta=0.01: -1.241 / -2.258 / +0.446; eta=0.08:
-8.204 / -10.312 / -4.786 — every digit matches).

**This identical result is not evidence that the fix doesn't matter for R7acuity.
It is evidence of a second, separate, pre-existing bug, found while checking:**
`R7acuity/core/ideal_observer.py` correctly inserts `stage2_fixed/` into
`sys.path` and does `import phase2_retina` — but `run_validation_unified.py`'s
own top-of-file imports do `from stage4_human_vision.validation import
regression_stats` *first*. Importing any `stage4_human_vision` submodule runs
`stage4_human_vision/__init__.py`, which does `from .pipeline import
run_stage4_point`; `pipeline.py` inserts the **deprecated** `stage2/` (not
`stage2_fixed/`) into `sys.path` and does `import phase2_retina` there. Python
caches modules by bare name in `sys.modules`, so by the time
`R7acuity/core/ideal_observer.py` runs its own `import phase2_retina`, Python
finds `'phase2_retina'` already cached and silently reuses the `stage2/` copy —
never re-searching `sys.path`, never reaching `stage2_fixed/` at all. Verified
directly: `sys.modules['phase2_retina'].__file__` resolves to
`.../stage2/phase2_retina.py` when imported in this exact order.

Confirmed `stage2/phase2_retina.py` (the deprecated original) has the **same**
unfixed lens/wavelength bug (`lens_phase` takes raw `wavelength`,
`propagate_to_retina` does its own independent correction) — plus, per this
project's own README, the two other bugs that were found and fixed when
`stage2_fixed/` was created from it (the energy-conservation redundancy and the
wraparound-margin sign error). So `R7acuity`'s already-published Wang-2009
failure, and `stage4_human_vision/pipeline.py`'s own headline failure (both of
which import through this same `stage2/` path), have never actually been
evaluated against this project's own most-correct optics stage
(`stage2_fixed/`) — a materially bigger finding than "did this one fix move the
number."

This import order is entry-point-specific, not universal: `R7acuity/dashboard.py`
imports `R7acuity.core.ideal_observer` *before* anything from
`stage4_human_vision`, so it does not hit this shadowing and would correctly use
`stage2_fixed/`.

**Plain answer to "does the change plausibly matter for the documented
failures":** unknown, and this run cannot answer it — it never actually touched
the fixed code. Given the R1 sweep shows large retina-plane changes at exactly
the M values R7acuity and `stage4_human_vision` test (M=0/2/5D — up to the +150%
range at M=2D), it is plausible the fix would matter substantially once the
import-shadowing bug is separately fixed and both are re-run against
`stage2_fixed/` for real — but that is a hypothesis for the next task, not a
result of this one. No sigma, efficiency value, or other locked parameter was
retuned.

## Prioritized downstream list (stale numbers / newly-discovered issues, not re-run here)

1. **`R7acuity` import-shadowing bug** (`stage4_human_vision/__init__.py` ->
   `pipeline.py` -> `stage2/`, shadowing `R7acuity/core/ideal_observer.py`'s
   intended `stage2_fixed/` import). Newly discovered in this task. Highest
   priority: it means `R7acuity/RESULTS.md`'s published negative validation
   result, and `stage4_human_vision/RESULTS.md`'s own headline negative result,
   have both been silently running against the deprecated, still-buggy `stage2/`
   the entire time, not `stage2_fixed/`. Fixing the import order (or making
   `stage4_human_vision/pipeline.py` point at `stage2_fixed/`) and re-running
   both validations is now arguably the single highest-value next step in the
   whole project.
2. **`stage3_human_vision/metrics.py`** — calls `lens_phase()` /
   `propagate_to_retina()` directly with the exact pre-fix calling pattern (raw
   `wavelength` into `lens_phase`). Has the identical bug, unfixed, still live
   (this file does correctly import `stage2/`, so it is at least internally
   consistent with itself — but that `stage2/` copy carries this bug plus the
   two others `stage2_fixed/` already fixed). Affects RMS radius, Strehl, MTF
   computed anywhere downstream of this file (`stage_v1_simulator`,
   `stage4_human_vision/pipeline.py`'s own MTF-based acuity chain).
3. **`stage3a/multi_EE_sweep.csv`** — the exact CSV this task's baseline was
   validated against; stale relative to `stage2_fixed/`'s corrected numbers
   (magnitude: matches this file's Step 4 table exactly, since it's the same
   sweep). `stage3a`'s own scripts (`transmission.py`,
   `combine_and_select.py`, `plot_blur_then_constraint.py`) read this CSV rather
   than calling `phase2_retina` live, so nothing there is *broken*, but every
   number it reports (including the "6.25-9% brightness floor" and
   "900-1250um brightness-constrained optimum" figures) was computed against the
   old, buggy blur numbers and should be re-derived before being treated as
   current.
4. **`stage3_integrated`** — `generate_tables.py` imports `stage2_fixed/`
   directly (will get corrected numbers next run); `combine_metrics.py` and
   `generate_plots.py` work from `stage3a`'s and `stage3_human_vision`'s CSVs
   (stale per items 2-3 above). Magnitude: likely large for anything derived
   from the R1-sweep-adjacent blur numbers (M<=4D especially), smaller for
   purely brightness/CSF-derived quantities.
5. **`model_comparison`** — `acuity_check.py` and `stage2_runner.py` both import
   `stage2/` (confirmed directly), not `stage2_fixed/`. Stale not because it
   consumed the now-fixed file, but because it independently runs the
   *still-buggy* `stage2/` copy — same root cause as item 1. The model
   comparison's "5-way reference-point reconciliation" (this project's own
   optimum vs. the deprecated closed-form vs. Rayleigh vs. clinical vs.
   commercial) is affected on its own "this project's own numerical optimum"
   leg.
6. **`array_ghosting_theory`** (`ghosting_regime.py`, `harmonic_analysis.py`) —
   correctly imports `stage2_fixed/` with no shadowing risk (no
   `stage4_human_vision` import anywhere in its chain, verified). Will get
   materially different MTF/PSF inputs next run, which feed directly into the
   ghosting regime (A/B/C) classification and the harmonic margin analysis —
   given the R1 sweep's magnitude at low-to-moderate M, this is plausibly large
   enough to shift some points across a regime boundary, but that has not been
   checked here.
7. **`master_compilation`** (`dashboard.py`, `master_results.xlsx`) and
   **`stage_v1_simulator`** (`live_compute.py`) — both import `stage2_fixed/`
   directly for live computation (will reflect the fix next run); any cached
   CSVs/spreadsheet sheets they display are stale per items 2-6.
8. **Prose/reference documents**: `PROJECT_STATUS.md` (Section 1's "300µm
   (M=1-4D) to 400µm (M=5-8D)" headline number), `pinhole_project_analysis.md`,
   `Pinhole_Project_Feature_Catalog.tex`, and the IYPT Theoretical Handbook
   (docx/PDF/LaTeX) all state the old 300-400um figure as the R1 sweep result.
   Textual updates only, no code involved.

None of the above were re-run in this task, per its explicit scope — this list
is for a follow-up task to prioritize, not a claim about what their corrected
numbers would be.

## Summary

The brief's diagnosis was independently verified correct via two different
physics derivations before any code was changed. The fix is a minimal,
signature-preserving change to `stage2_fixed/phase2_retina.py` only. It does not
break the zero-defocus validation gate (errors improved) and does not change the
`refractive_index_correction=False` path at all (confirmed bit-identical). It
substantially changes the R1 sweep's pure-blur optimum at low-to-moderate myopia
(up to +150% at M=2D, vanishing by M=6-8D) — a real, physically-explained
correction, not noise, and one that moves the previously-reported optimum
meaningfully closer to (though still short of) the independently-derived
brightness-constrained and clinical ranges. Along the way, a second, unrelated,
and arguably more consequential bug was found: `R7acuity` and
`stage4_human_vision`'s own published validation failures have never actually
been evaluated against `stage2_fixed/` at all, due to an import-order collision
that silently redirects them to the deprecated `stage2/` copy. That bug is
reported, not fixed, here.
