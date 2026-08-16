# Rotation Sweep Findings

## The question this task answers

Does any rotated square/hexagonal/rectangular candidate beat `jittered_lattice`'s
current winning density among structurally-safe survivors, once lattice
orientation (relative to this project's own established anisotropic-gaze finding)
is actually tested instead of assumed fixed at one arbitrary angle?

## Headline result

**No -- and the reversal is total, not marginal: `jittered_lattice` now wins at
ZERO of 9 M-scopes** (it previously won 5 of 9: M=1, 2, 3, 6, 8). A **rotated**
`square` or `hexagonal` lattice now wins at 6 of 9 scopes (M=1, 2, 3, 6, 8,
global); `archimedean_spiral` still wins M=4/5; `rectangular` still wins M=0.
**This is a real, reportable change to the Metric-1 winner list, not a rounding
effect** -- confirmed by direct inspection of the underlying gate values, not
just the summary density numbers (see "Mechanism," below).

## Per-M comparison: old winner vs. new (rotation-inclusive) winner

| M | old winner | old density (um^-2) | new winner | new density (um^-2) | change |
|---|---|---:|---|---:|---|
| 0.0 | rectangular (rot=0, unchanged) | 2.9630e-07 | rectangular (rot=0) | 2.9630e-07 | same winner |
| 1.0 | jittered_lattice | 9.4864e-08 | **square (rot=45deg)** | 1.1111e-07 | **WINNER CHANGED, +17.1%** |
| 2.0 | jittered_lattice | 1.0126e-07 | **square (rot=45deg)** | 1.1111e-07 | **WINNER CHANGED, +9.7%** |
| 3.0 | jittered_lattice | 1.0126e-07 | **square (rot=45deg)** | 1.1111e-07 | **WINNER CHANGED, +9.7%** |
| 4.0 | archimedean_spiral | 2.3085e-07 | archimedean_spiral | 2.3085e-07 | same winner |
| 5.0 | archimedean_spiral | 2.3085e-07 | archimedean_spiral | 2.3085e-07 | same winner |
| 6.0 | jittered_lattice | 1.0471e-07 | **square (rot=45deg)** | 1.1111e-07 | **WINNER CHANGED, +6.1%** |
| 8.0 | jittered_lattice | 1.0614e-07 | **square (rot=45deg)** | 1.1111e-07 | **WINNER CHANGED, +4.7%** |
| global | square (rot=0) | 2.5000e-07 | **hexagonal (rot=30deg)** | 2.8868e-07 | **WINNER CHANGED, +15.5%** (see caveat) |

Full per-row detail: `comparison_metric/metric1_max_density_per_M.csv` (new) vs.
`comparison_metric/metric1_max_density_per_M_PREROTATION_legacy.csv` (old).

## How far behind is `jittered_lattice` now, even where it lost?

Comparing the new winner's density against `jittered_lattice`'s OWN best
structurally-safe density at each M (not just "did it win," but "by how much"):

| M | new winner leads jittered_lattice's own best by |
|---|---:|
| 0.0 | +15.1% |
| 1.0 | +17.1% |
| 2.0 | +9.7% |
| 3.0 | +9.7% |
| 4.0 | +123.5% |
| 5.0 | +123.5% |
| 6.0 | +6.1% |
| 8.0 | +4.7% |
| global | +122.7% |

`jittered_lattice` is not close anywhere -- the smallest margin (M=8) is still a
4.7% lead for the new winner, and at M=4/5/global the gap is over 100%
(`archimedean_spiral`/`hexagonal` were always well ahead there; rotation only
changed who's ahead at the other 6 scopes).

## Mechanism -- confirmed by direct inspection, not inferred from the summary alone

**Density itself never changes with rotation** (rotating a rigid lattice changes
neither its packing density nor its ghost margin, which depends only on pairwise
distance). What changes is **which candidates pass the safety gates** --
specifically `worst_case_vignetting_margin`, exactly as this task's own premise
predicted (orientation relative to the anisotropic gaze axis matters for
vignetting, not for ghosting).

**M=1, 2, 3, 6, 8 (square, pitch=3000um, N=50) -- clean, robust, unaffected by any
numerical edge case.** Direct check of the underlying rows:

```
rotation_deg   worst_case_vignetting_margin   structurally_safe
0.0            -5.939 / -7.050 (varies by M)  False
15.0           -7.050                          False
30.0           -7.050                          False
45.0           +inf                            True   <-- flips to safe
```

`N_actual` for this candidate is **perfectly stable across all 4 rotation angles**
(20/20/20/20, 50/50/50/50, 100/100/100/100 -- verified directly) -- this pitch
(3000um) is far from the hole diameter (a_hole=1250um at M=1D, ratio=0.417), so no
overlap-rejection boundary is anywhere near being touched. This is a genuine
geometric effect: rotating the lattice by 45 degrees moves specific hole positions
enough that no pair of holes is ever simultaneously active under the pupil across
the full gaze sweep (`worst_case_vignetting_margin` goes to a clean `+inf`, not a
marginal small-positive value), where at 0/15/30 degrees a pair does become active
at some tested gaze angle and produces a firmly negative margin. **High
confidence finding.**

**M=global (hexagonal, pitch=2000um, rotation=30deg) -- real, but flagged as
numerically fragile.** Here `pitch_um` (2000) exactly equals `a_hole_um` (2000,
the largest acuity-optimal aperture across the M range, used for global-scope
overlap validity per this project's own established convention) -- **exact
tangency, ratio=1.0**, a case this project's own `compute_density.py` already
documents as fragile: `reject_overlapping()`'s strict `d2 > a_hole_um**2` test
sits exactly on a floating-point knife-edge at exact tangency. Direct check
confirms `N_actual` for this candidate actually VARIES across rotation angles at
the same N_requested (e.g. N_requested=20 gives N_actual=7, 9, 7, 9 at
rotation=0/15/30/45 respectively) -- a symptom of rotation's own floating-point
rounding (irrational `cos`/`sin` values) nudging which near-tied points survive
the exact-tangency boundary, not a bug in the rotation transform itself (verified
elsewhere -- see next section -- that rotation preserves `N_actual` exactly away
from this boundary). **The M=global winner-change is real for the specific
rotation angles tested** (rotation=30deg genuinely reaches `structurally_safe=True`
with `worst_case_vignetting_margin=+inf` at this pitch), **but it should be read
as "a numerically narrow window this project's own known exact-tangency edge case
opened up," not as a broad, robustly-safe orientation** the way the M=1-8 finding
is. Recommend re-checking this specific candidate at a pitch slightly off exact
tangency (e.g. 1990 or 2010um) before treating it as a settled design choice.

## Step 1 order requirement: rotation_deg=0.0 exact-reproduction, confirmed before the sweep ran

Per this task's explicit ORDER requirement, `spot_check_generators.py` was
extended and run BEFORE the rotation sweep: `rotation_deg=0.0` reproduces the
pre-rotation-support output bit-for-bit (`np.array_equal`, not just
`np.allclose`) for all three families, and `rotation_deg=30.0` was independently
verified to (a) actually change coordinates, (b) preserve `N_actual` exactly, and
(c) preserve every pairwise distance exactly -- all PASS. (The one place `N_actual`
does vary with rotation in the real sweep, described above, is the pre-existing
exact-tangency edge case, confirmed by direct inspection to be a floating-point
boundary effect specific to `pitch_um==a_hole_um`, not a contradiction of this
check -- the spot-check's own N=50/pitch=900/a_hole=400 case is nowhere near that
boundary.)

## What was changed, and what was preserved

- `generators/base_generator.py`: added `rotate_points(coords_um, rotation_deg)`
  (shared helper, avoids duplicating the same rotation matrix in 3 files).
  `reject_overlapping`, `recenter_on_centroid`, `finalize` unchanged.
- `generators/square.py`, `generators/hexagonal.py`, `generators/rectangular.py`:
  added `rotation_deg=0.0` parameter, applied before `bg.finalize()`. Core lattice
  construction (meshgrid, radial sort) unchanged.
- `sweep/run_rotation_sweep.py` (new): re-swept ONLY square/hexagonal/rectangular,
  ONLY adding rotation_deg in {0, 15, 30, 45} on the EXISTING N/spacing grid
  (`DEFAULT_N_LIST`, `DEFAULT_LATTICE_SPACING_LIST`, `DEFAULT_RECTANGULAR_RATIO_LIST`
  -- all unchanged from `run_sweep.py`'s own defaults). No other family touched or
  re-run.
- `sweep_results.csv`: original preserved as `sweep_results_PREROTATION_legacy.csv`
  (6395 rows, untouched). Existing square/hexagonal/rectangular rows retroactively
  tagged with `;rotation_deg=0.0` in their `spacing_params` string (text-only, no
  numeric column touched -- safe because of the step-1 equivalence proof). New
  rows for rotation in {15, 30, 45} appended. **No duplicate (family, N,
  spacing_params, rotation_deg=0) rows** -- verified by exact-duplicate count
  matching the number of existing tagged rows precisely (702), not assumed;
  a first attempt at this check found a real bug (an `M`-column string/float dtype
  mismatch from the CSV round-trip silently broke `drop_duplicates()`, caught
  because the dedup count didn't match the expected value and was investigated
  before proceeding, not ignored). Final: 8933 rows (5693 untouched
  other-family rows + 3240 square/hexagonal/rectangular rows across all 4
  rotation angles).
- `sweep_results_with_density.csv`: re-run via the UNMODIFIED
  `degeneracy_filter.py`/`compute_density.py`. Previous version preserved as
  `sweep_results_with_density_PREROTATION_legacy.csv`. 432 rows excluded by the
  degeneracy filter (108 designs x 4 rotation angles -- the SAME 108
  (family,N,spacing) combinations already known to be degenerate from the earlier
  degeneracy-cleanup task, now recurring once per rotation angle since the
  degeneracy criteria -- point-count floor and unit-cell feasibility ratio -- are
  both rotation-invariant by construction). `open_area_fraction <= 1.0001`
  assertion: **passed, zero violations**, 8501 surviving rows.
- `comparison_metric/metric1_max_density_per_M.csv`: re-run via the UNMODIFIED
  `gates.py`/`metrics.py` (Metric 1 only, via the new
  `comparison_metric/run_metric1_only.py`, which does not touch Metric 2).
  Previous version preserved as `metric1_max_density_per_M_PREROTATION_legacy.csv`.
- Untouched, as required: every other family's data (`concentric`,
  `fibonacci_spiral`, `golden_angle`, `archimedean_spiral`,
  `ring_offset_concentric`, `poisson_disk`, `jittered_lattice`),
  `array_optimization/`, and every Phase 2 confirmation file.

## Reproduction

```bash
cd Array_Design/array_geometry_lab
python3 spot_check_generators.py               # step 1 gate -- must pass first
python3 sweep/run_rotation_sweep.py             # step 2-3
cd comparison_metric
python3 compute_density.py                      # step 4
python3 run_metric1_only.py                     # step 5
```
