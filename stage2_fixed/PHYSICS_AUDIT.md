# Physics audit of the optical engine (stage2_fixed)

## What this audit was for

A structured brief (items A-F below) alleged one confirmed bug (A, previously found
and fixed on a separate branch, `fix/lens-wavelength-consistency` -- re-verified and
re-fixed here independently, as this branch was cut from `Iteration2Aug` directly, not
from that other branch), one related inconsistency (B), one unchecked numerical
concern (C), one gate-circularity issue to document but not fix (D), and four
defensible-but-undocumented design choices to state explicitly (E1-E4). The brief
asked for independent verification of every item before any code change, permission to
reject any item found wrong, and a search for additional issues not listed.

This file reports what was actually verified, what changed, what didn't, and what was
found along the way.

## Branch note

`fix/physics-audit` was cut from `Iteration2Aug` (commit `41814c0`), the branch that
holds this project's real, current history -- not from `main`, which turned out on
inspection to be a near-empty stub (just the repository's initial commit). This matches
where the earlier `fix/lens-wavelength-consistency` branch was also cut from. The two
branches are independent (neither is an ancestor of the other); item A's fix is applied
fresh here, not inherited.

## Item A -- lens phase / retina propagation wavelength mismatch

**CONFIRMED, and fixed.** Independently re-derived via two methods before touching any
code:

1. *Stationary-phase focus-location argument*: for lens phase `exp(-i k_L r^2/(2f))`
   followed by propagation at wavenumber `k_prop`, the true geometric focus sits at
   `z* = f*(k_prop/k_L)`. Pre-fix, `k_L` was the vacuum wavenumber while `k_prop` was
   `n_prime` times larger (from `propagate_to_retina`'s own correction), giving
   `z* = f_eye*n_prime` instead of `f_eye` -- a ~33.6% axial focus error.
2. *Medium-agnostic optical-path-length argument*: for a refracting system with object
   index 1 and image index `n_prime`, the correct phase screen is
   `exp(-i k_vacuum P (r^2)/2)`, independent of surrounding media. Substituting
   `f_eye = n_prime/P0` shows this requires `k = k_vacuum*n_prime` in the lens phase --
   exactly `wavelength/n_prime`, matching `propagate_to_retina`'s convention.

Both derivations agree with each other and with the brief. `validation_gate.py`'s own
closed-form comparison already computed `effective_wavelength = wavelength/n_prime`
independently, confirming the convention was known project-wide and simply not
threaded through the lens call.

**Fix**: `effective_wavelength` resolved once in `run_pipeline_point()`, passed to both
`lens_phase()` and `propagate_to_retina()` (the latter with
`refractive_index_correction=False`, since the correction is already applied -- keeps
its own ternary a documented no-op rather than a second, independently-editable copy).
No signature changes to either function (a caller outside this file,
`stage3_human_vision/metrics.py`, calls both directly with the pre-fix pattern and has
the identical unfixed bug -- see the downstream list).

**Verified**: `refractive_index_correction=True` path changes (r_EE_50 at a=300um/M=2D:
23.42um -> 16.85um); `False` path is bit-identical before and after (confirmed by
direct pre/post file diff and re-run, not merely "should be" -- see F.2 below), and
matches the exact same fix applied independently on `fix/lens-wavelength-consistency`
to the digit (22.556187675986086um).

## Item B -- validate_junction receives the wrong wavelength

**CONFIRMED, and fixed.** `run_pipeline_point()` passed the raw vacuum `wavelength` to
`junction.validate_junction()`, which uses it for two internal diagnostics: the
Matsushima band-limit re-propagation check, and a divergence-based wraparound estimate.
Since the real propagation (post item A) runs at `wavelength/n_prime`, and
`fx_limit ~ 1/wavelength`, testing at the vacuum wavelength produces a SMALLER
(more restrictive) `fx_limit` than the true propagation would have -- over-predicting
suppression. Direction confirmed as conservative, not corrupting: a larger vacuum
wavelength can only make the gate MORE likely to (incorrectly) flag a problem, never
less.

**Fix**: pass `effective_wavelength` (the same one item A resolved) to
`validate_junction()` instead.

**Quantified**: `fx_limit` differs by exactly the `n_prime` factor between the two
wavelengths (e.g. a=150um/M=1D: `2.388e5` vs `3.190e5` 1/m, a 33.6% difference,
confirming the mechanism). However, the actual band-limit suppression fraction is
`0.0000%` either way across every R1-sweep config directly checked (a=75/150/2000um x
M=1/8D) -- so this fix restores real headroom and improves correctness for future,
more demanding configurations, but changes no pass/fail verdict and no reported number
in this project's own current sweeps.

## Item C -- lens-phase Nyquist sampling, unchecked

**CONFIRMED as a real, previously-unchecked numerical concern; added as a new,
non-gating diagnostic.** Independently derived: the lens phase's local spatial
frequency grows linearly with radius (`d(phase)/dr = -k*r/f_eye`); requiring less than
`pi` radians of phase change per pixel (a standard 2-samples-per-cycle Nyquist
criterion) gives

```
r_max_lens = wavelength * f_eye / (2 * dx)
```

At defaults (`550nm/1.336`, `f_eye~22.27mm`, `dx=6mm/2048~2.93um`) this evaluates to
**1564.4um**, confirming the brief's ~1.6mm figure exactly. `D_pupil_um=4000` (pupil
radius 2000um) exceeds this at EVERY point in EVERY sweep at these settings, since
`r_max_lens` doesn't depend on `a_hole` at all -- the outer pupil annulus (1.56mm to
2.0mm) genuinely carries an under-sampled lens phase, at every aperture this project
has tested.

**Quantified, not assumed** (this project's own two requested test points, plus the
values `validate_lens_sampling()` now reports live for every run):

| a_hole | fraction of cornea-plane energy beyond r_max_lens |
|---|---|
| 300um | 0.0053% |
| 2000um | 0.0515% |

**Design decision, stated explicitly**: NOT wired into `junction_check_passed`. Since
`r_max_lens < D_pupil/2` at every point under these settings (a structural fact of the
grid/pupil defaults, not aperture-dependent), a hard gate would reject every point
uniformly rather than flagging the ones where it actually matters -- and the quantified
impact at this project's own tested apertures is small. Added as
`validate_lens_sampling()`, called from `run_pipeline_point()`, exposed as
`result["lens_sampling_check"]` in the same pass/fail + `suggested_grid_N` reporting
style as the existing checks, so it stays visible (and a future, more extreme
configuration -- much larger aperture, larger pupil, or coarser grid -- can be checked
rather than assumed fine) without silently blocking every sweep this project already
runs.

## Item D -- gate circularity

**CONFIRMED, documented, not "fixed" (correctly, per the brief -- there is no bug in
the gate's check logic itself).** `validation_gate.py` runs at `d_gap=0`, `M=0`, where
`myopia_axial` gives `v_r = L0 = f_eye` by construction (zero defocus). At exact focus,
a lens-power scaling error (item A) partly shows up as the wave's TRUE focus shifting
away from where `propagate_to_retina` evaluates it (a focal-PLANE error), rather than
as a distortion of the in-focus pattern's SHAPE -- which is specifically what the gate
compares against the closed-form Airy formula. This is why the gate passed at existing
tolerances despite item A's bug being present pre-fix (F.1/F.2 below).

Added a documentation-only note to `validation_gate.py`'s module docstring stating this
plainly: the gate validates pattern shape at exact focus, is not sensitive to a pure
lens-power scaling error in the general case, and must not be treated as the only
physics check on this pipeline. No check logic or tolerance changed.

## Item E -- design choices, verified and documented

**E1 (reduced-eye geometry) -- CONFIRMED.** `pupil_clip`, `lens_phase`, and the start of
the retinal propagation all operate on `cornea_result`'s single plane -- no anterior
chamber distance (~3.6mm in a real eye), no cornea/lens power split (roughly 2/3 vs 1/3
of P0 in reality). This is the standard "reduced eye" schematic simplification (matches
e.g. Gullstrand-Emsley), and is what makes a single `P0=60D` a meaningful number at
all -- but every pupil/lens-plane distance in this module is a modeling convenience,
not an anatomical one. Documented in `phase2_retina.py`'s module docstring.

**E2 (encircled_energy normalizes to grid-captured, not emitted, power) -- CONFIRMED.**
`encircled_energy()`'s `total_power = cum_power[-1]` sums only what's captured on the
grid at measurement time. The existing wraparound check is peak-relative (compares edge
intensity to peak), not an energy integral, and cannot by itself bound how much real
energy left the window. Documented in `encircled_energy()`'s docstring (it previously
had none) and `radial_profile()`'s. **Added**, per the brief, an integrated escape
estimate: `phase2_retina.energy_escape_estimate()`, exposed as
`result["energy_escape_estimate"]`, comparing the aperture's analytic input power
(`pi*(a_hole/2)^2`, exact for a uniform circular aperture) against grid-captured power
at the cornea and retina planes. At the two apertures already tested for item C
(`D_pupil_um=4000`, so neither is physically pupil-clipped), the escaped fraction is
effectively zero and slightly NEGATIVE (`-0.0023%` to `-0.1154%`) -- a small, expected
artifact of rasterizing a binary circular mask onto a discrete pixel grid (the sampled
area can slightly over- or under-count the true circle area), not real energy gain.
Consistent with items B and C's own negligible-impact findings at these same apertures.

**E3 (radial_profile vs. encircled_energy domain mismatch) -- CONFIRMED.**
`radial_profile()`'s domain is the circle inscribed in the window (`r_max =
dx*min(center, N-1-center)`); `encircled_energy()` bins out to `R.max()`, the CORNER
distance (~1.41x further for a square grid). Threshold radii (FWHM, 1/e^2, custom
threshold -- all derived from `radial_profile`) and `r_EE(P)` are therefore measured
over genuinely different domains: high percentiles of `r_EE(P)` can draw on
corner-only energy no threshold-crossing search can ever reach, and the corner region
is also the least-validated part of the grid. Documented in both functions' docstrings.

**E4 (unmodeled effects) -- all four CONFIRMED absent from the core optical model, and
listed in one place** (`phase2_retina.py`'s module docstring): longitudinal chromatic
aberration (P0 is fixed per run, independent of the wavelength argument -- running
several wavelengths as separate fields, as some later stages do, is not the same as
modeling dispersion within one field); higher-order aberrations (`lens_phase` is a pure
quadratic/defocus term only); Stiles-Crawford apodization (`pupil_clip` is a binary
hard-edged mask -- a separate, independent Stiles-Crawford term exists only in
`stage4_human_vision/csf.py`'s own retinal-illuminance calculation, not in this
project's core PSF); finite aperture thickness / vignetting
(`stage1_v2.circular_aperture` is an infinitely-thin binary 0/1 mask).

## Additional issue search (per the brief's request)

One hypothesis was checked and explicitly REJECTED, not fixed: whether `v_r` (and
`f_eye`) should depend on `d_gap`, since the pinhole physically sits a finite distance
(e.g. 12mm) from the cornea, not at infinity. Re-derivation: the pinhole is a
diffracting APERTURE STOP inserted into an otherwise-plane-wave path from the true
optical object (whatever distant scene is being viewed) at infinity -- it modulates the
wave's transverse structure but does not change the fact that the object vergence
feeding the eye's own lens equation is zero. `v_r = n_prime/(P0-M)`, independent of
`d_gap`, is therefore correct as written. No code changed for this.

No other new physics bugs were found in this pass. One separate, non-physics issue was
re-confirmed present (carried over from the earlier `fix/lens-wavelength-consistency`
branch's own audit, now independently reconfirmed on this branch's own code -- see
F.4 and the downstream list below): an import-order bug that silently shadows
`R7acuity`'s intended `stage2_fixed/` import with the deprecated `stage2/` copy.

## F. Regression

### F.1 -- pre-fix baseline

`validation_gate.py`: **PASS** (r_EE_50 1.14%, r_EE_80 4.56%, r_EE_90 0.55%; tolerances
2/8/2%). R1 sweep (15 apertures x M=[1,2,3,4,5,6,8]D, 550nm, 12mm gap): reproduced the
documented optimum exactly -- 300um for M=1-4D, 400um for M=5-8D. Saved to
`outputs/prefix_baseline_audit/`.

### F.2 -- post-fix validation gate

**PASS**, at the same, unchanged tolerances. Errors *improved*: r_EE_50 1.14% ->
0.30%, r_EE_80 4.56% -> 0.38%, r_EE_90 0.55% -> 0.94% -- the expected direction if
the fix is correct (the zero-defocus numeric focus now aligns more precisely with the
closed-form Airy assumption). `refractive_index_correction=False` confirmed
bit-identical after ALL of items A/B/C/E (not just A) via direct file diff and re-run.
No tolerance changed anywhere.

### F.3 -- post-fix R1 sweep: the documented optimum does not survive

| M (D) | opt. aperture: pre -> post | change | r_EE(50%) at opt: pre -> post | change |
|---|---|---|---|---|
| 1 | 300 -> 700 um  | **+133.3%** | 23.04 -> 7.33 um  | -68.2% |
| 2 | 300 -> 750 um  | **+150.0%** | 22.65 -> 8.01 um  | -64.6% |
| 3 | 300 -> 600 um  | **+100.0%** | 22.29 -> 10.57 um | -52.6% |
| 4 | 300 -> 500 um  | +66.7%      | 21.99 -> 12.02 um | -45.4% |
| 5 | 400 -> 500 um  | +25.0%      | 20.83 -> 13.29 um | -36.2% |
| 6 | 400 -> 400 um  | 0.0%        | 19.79 -> 14.47 um | -26.9% |
| 8 | 400 -> 400 um  | 0.0%        | 18.16 -> 17.87 um | -1.6%  |

Identical, to the micron and the tenth of a percent, to the same measurement made
independently on `fix/lens-wavelength-consistency` -- confirms the result is robust and
reproducible, not an artifact of one particular run. The pattern across M is physically
coherent: the bug is a fixed absolute focal-shift error (`f_eye*(n_prime-1)`, ~7.5mm,
independent of M), which is a large fraction of the eye's total defocus budget at low
M and proportionally negligible once real axial elongation dominates at high M.

One observation, stated plainly and not overinterpreted: the corrected optimum
(400-750um) sits closer to the independently-derived brightness-constrained optimum
(900-1250um, `stage3a`) and the clinical bracket (940-1750um) than the old 300-400um
figure did. This narrows part of the gap the brightness-floor analysis was built to
explain, but does not close it -- re-deriving how much of that gap was ever
attributable to this bug is a separate analysis this file does not attempt.

Items B, C, and E's additive changes do not move any R1 sweep number -- confirmed
directly (identical values to `fix/lens-wavelength-consistency`'s A-only fix) -- since
none of them change any value `lens_phase` or `propagate_to_retina` actually receive.

No aperture recommendation is made anywhere in this file.

### F.4 -- acuity model smoke tests

`stage4_human_vision/tests/test_stage4.py`: all 7 tests pass, but none of them
exercise `phase2_retina.py` at all -- a real pass, not meaningful evidence about this
fix specifically.

`R7acuity/run_validation.py` (this branch's actual script; the `core/` +
`run_validation_unified.py` refactor referenced in the original brief is separate,
uncommitted work-in-progress not part of this branch's committed history -- see
"Branch note" above): ran clean, no exceptions. R^2 = -24.622 / -28.056 / -19.100 for
M=0/2/5D -- **bit-for-bit identical** to `RESULTS.md`'s documented pre-fix numbers
(confirmed additionally by `git status` showing zero diff in `R7acuity/outputs/` after
this run overwrote them with identical content).

**This is not evidence the fix doesn't matter for R7acuity.** Re-confirmed directly
(independently of the earlier finding on `fix/lens-wavelength-consistency`) via
`sys.modules['phase2_retina'].__file__`: importing `stage4_human_vision.validation`
(which `run_validation.py`, like the other branch's `run_validation_unified.py`, does
first) runs `stage4_human_vision/__init__.py` -> `pipeline.py`, which inserts the
**deprecated** `stage2/` (not `stage2_fixed/`) into `sys.path` and imports
`phase2_retina` there -- caching it under the bare module name before
`R7acuity/ideal_observer.py`'s own, correctly-targeted `stage2_fixed/` import ever
runs. Python's import cache silently reuses the `stage2/` copy from then on.
`stage2/phase2_retina.py` independently confirmed to carry the identical unfixed
lens/wavelength bug (plus, per this project's own README, the two other bugs already
fixed when `stage2_fixed/` was created from it). So `R7acuity`'s and
`stage4_human_vision/pipeline.py`'s own published negative validation results have
never actually been evaluated against `stage2_fixed/` at all -- this remains the
single highest-priority follow-up item, not fixed here (out of this audit's scope).

No sigma, efficiency, or other locked parameter was retuned.

## Prioritized downstream list (stale numbers / open issues, not re-run here)

1. **`R7acuity`/`stage4_human_vision` import-shadowing bug** -- re-confirmed present on
   this branch too (F.4). Highest priority: means two of the project's own published
   negative validation results have never run against `stage2_fixed/`.
2. **`stage3_human_vision/metrics.py`** -- calls `lens_phase()`/`propagate_to_retina()`
   directly with the pre-fix calling pattern (raw `wavelength` into `lens_phase`). Has
   the identical item-A bug, unfixed. (This file imports the deprecated `stage2/`, not
   `stage2_fixed/`, so it is internally self-consistent but carries `stage2/`'s full
   bug list.)
3. **`stage3a/multi_EE_sweep.csv`** -- the exact CSV this audit's baseline matches;
   stale relative to `stage2_fixed/`'s corrected numbers by exactly this file's F.3
   table. Every downstream number computed from it (including the "6.25-9% brightness
   floor" and "900-1250um" figures) should be re-derived before being treated as
   current.
4. **`stage3_integrated`** -- `generate_tables.py` imports `stage2_fixed/` directly
   (will reflect the fix next run); `combine_metrics.py`/`generate_plots.py` read
   `stage3a`'s and `stage3_human_vision`'s CSVs (stale per items 2-3).
5. **`model_comparison`** -- `acuity_check.py` and `stage2_runner.py` both import the
   deprecated `stage2/`, not `stage2_fixed/` -- same root cause as item 1, affecting the
   "5-way reference-point reconciliation" on its own "this project's numerical optimum"
   leg.
6. **`array_ghosting_theory`** -- correctly imports `stage2_fixed/` with no shadowing
   risk (no `stage4_human_vision` import in its chain). Will get materially different
   MTF/PSF inputs next run, feeding directly into the ghosting regime (A/B/C)
   classification and harmonic margin analysis -- plausibly large enough at low-to-
   moderate M to shift some points across a regime boundary; not checked here.
7. **`master_compilation`/`stage_v1_simulator`** -- both import `stage2_fixed/`
   directly for live computation (will reflect the fix next run); cached
   CSVs/spreadsheets they display are stale per items 2-6.
8. **Prose documents**: `PROJECT_STATUS.md` (the "300µm (M=1-4D) to 400µm (M=5-8D)"
   headline number), `pinhole_project_analysis.md`, `Pinhole_Project_Feature_Catalog.tex`,
   and the IYPT Theoretical Handbook all state the old figure. Text updates only.

None of the above were re-run in this task, per its explicit scope -- this list is for
a follow-up task to prioritize, not a claim about what their corrected numbers would be.

## Summary

Items A and B were confirmed real bugs and fixed with minimal, signature-preserving
changes. Item C was confirmed a real, previously-unchecked numerical concern and added
as a new, non-gating diagnostic, quantified rather than assumed (well under 0.1% of
cornea-plane energy affected at this project's own tested apertures). Item D was
documented, not changed -- there is no bug in the gate's own logic, only an
undocumented blind spot. Item E's four design choices were all verified true of the
actual code and documented in place, with E2 additionally gaining a new, small,
non-gating energy-accounting diagnostic per the brief. One additional hypothesis was
checked and explicitly rejected (object-distance dependence in `v_r`). The regression
confirms the gate still passes (with improved errors) and the `False` path is
untouched, while the R1 sweep's headline optimum moves substantially and
physically-coherently at low-to-moderate myopia. The most consequential finding of the
whole audit is not on this list of six items at all: a separate, real import-order bug
means this project's two acuity-validation efforts have never actually tested against
`stage2_fixed/`, so their published failures should be treated as unconfirmed against
the intended optics pipeline until that is fixed and both are re-run.
