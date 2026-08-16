# Audit Fixes Report

Fixes three confirmed defects in the geometry-comparison pipeline and regenerates
the full dataset once, in dependency order. All three defects were CONFIRMED (not
re-litigated) per the audit's own instruction; this report documents what was
changed, what was verified before/after each change, and the resulting new winner
list.

## Summary of outcome

**The old winner list was substantially an artifact of the three defects, not a
robust result.** After all three fixes: `archimedean_spiral`'s two winning slots
(M=4.0, M=5.0) -- confirmed genuine blackout designs -- are gone entirely (the
family has zero survivors at any M except 0.0 and global). `square` at
`pitch_um=3000, rotation_deg=45deg` now wins 7 of 8 per-M slots (M=1,2,3,4,5,6,8) --
**exactly matching the audit's own stated prediction**. `ring_offset_concentric`
takes M=0.0 (previously `rectangular`). Global scope now goes to `square`
(`pitch_um=2000, rotation_deg=0`), not the previous, numerically-fragile
exact-tangency `hexagonal` result. `jittered_lattice`, which won 5 of 9 scopes
before this session's rotation-gap fix and 0 of 9 after it, remains at 0 of 9 here
too. This is an honest, worse-looking-by-old-standards outcome, and it is the
correct one: the old numbers were inflated by a metric that rewarded darkness and
scored families inconsistently.

## Part 2 step 7 -- identical-arrangement verification (blocking gate, run before Part 3)

Required: at `N_requested=50` (the task's own parameters, `pitch_um=700`,
`a_hole_um=2000`, resolved to `N_actual=7` after overlap rejection -- see
"Step 14" below for why `N=7` requested directly gives a different, smaller
result), `jittered_lattice(jitter_fraction=0.0)`, `hexagonal` (any `rotation_deg`),
and `ring_offset_concentric` (`ring_spacing_um=700`, `holes_per_ring0=6`) must
produce bit-identical density.

**Result: PASSED.** All three families give `N_actual=7`. `hexagonal` and
`jittered_lattice(jitter=0)` produce bit-identical coordinates (exact match, not
merely close). `ring_offset_concentric`'s coordinates differ in absolute angular
position (a different starting-angle convention for ring 1) but are congruent (same
7-point shape: 1 center + 6 points equally spaced on a ring of the same radius) --
since convex hull area is rotation-invariant, all three give the **exact same
buffered-hull area, `27199108.745657913` um^2, to the last floating-point bit**.
`hexagonal` at `rotation_deg=30` also reproduces this exact value (rotation
invariance holds, as it must for a hull-area formula). This is the property the old
per-family-formula design could never have had by construction -- confirmed, not
assumed.

## Part 3 root cause -- N/A this session

(This item is carried over from an earlier, superseded version of this task; the
user's corrected context for this session confirmed the rotation sweep already
completed successfully in a prior session -- `sweep_results.csv` already had 8933
rows, 3240 rotation-tagged, before this session's work began. No rotation-sweep
failure existed to diagnose here.)

## Per-family survivor counts, before -> after each gate

| family | total rows | after ghost+vignetting (2 gates) | after all 3 gates | removed by `gate_viability` | % of 2-gate survivors removed |
|---|---:|---:|---:|---:|---:|
| archimedean_spiral | 135 | 27 | 12 | 15 | **55.6%** |
| concentric | 318 | 73 | 59 | 14 | 19.2% |
| fibonacci_spiral | 133 | 14 | 10 | 4 | 28.6% |
| golden_angle | 133 | 14 | 10 | 4 | 28.6% |
| hexagonal | 528 | 135 | 133 | 2 | 1.5% |
| jittered_lattice | 3792 | 701 | 530 | 171 | 24.4% |
| poisson_disk | 864 | 183 | 105 | 78 | 42.6% |
| rectangular | 1728 | 498 | 302 | 196 | 39.4% |
| ring_offset_concentric | 318 | 65 | 52 | 13 | 20.0% |
| square | 552 | 150 | 111 | 39 | 26.0% |
| **TOTAL** | **8501** | **1860** | **1324** | **536** | **28.8%** |

`gate_viability` alone removes 536 rows (28.8% of what the old two-gate objective
would have called safe) -- a large, real effect, not a rounding correction.
`archimedean_spiral` loses the largest fraction (55.6%) of its 2-gate survivors,
consistent with it being the family whose blackout design won two M-slots outright
under the old two-gate objective.

Row counts overall: `sweep_results.csv` regenerated from scratch at 8933 rows
(6615 base x 10 families + 3240 rotation-only additions for
square/hexagonal/rectangular, minus 702 exact duplicates); after
`degeneracy_filter.is_degenerate()` (Part 2's unified check),
`sweep_results_with_density.csv` has 8501 rows (432 excluded -- the same 108
degenerate (family, N, spacing) combinations recurring once per rotation angle,
confirmed unchanged from the prior session since the degeneracy criteria are
rotation-invariant by construction).

## OLD vs NEW Metric-1 winners, side by side

`n_active_holes`/`total_illuminated_area_um2` for the OLD winners were recomputed
directly with the NEW (Part 1, true partial-overlap) `active_pairs.py` logic on
their exact original parameters, since the old winner file predates that fix and
never recorded these columns.

| M | OLD winner | OLD density | OLD n_active_holes(phi0) | OLD total_illum_area_um2(phi0) | NEW winner | NEW density | NEW n_active_holes(phi0) | NEW total_illum_area_um2(phi0) |
|---|---|---:|---:|---:|---|---:|---:|---:|
| 0.0 | rectangular (N=20, pitch_x=1500/pitch_y=2250) | 2.963e-07 | 1 | 5.02e6 | **ring_offset_concentric** (N=100, rs=700/hpr0=6) | 2.318e-07 | 3.0 | 1.00e7 |
| 1.0 | square (N=50, pitch=3000, rot=45) | 1.111e-07 | 1 | 1.23e6 | square (N=100, pitch=3000, rot=45) | 1.186e-07 | 1.0 | 1.23e6 |
| 2.0 | square (N=50, pitch=3000, rot=45) | 1.111e-07 | 1 | 4.42e5 | square (N=100, pitch=3000, rot=45) | 1.224e-07 | 1.0 | 4.42e5 |
| 3.0 | square (N=50, pitch=3000, rot=45) | 1.111e-07 | 1 | 4.42e5 | square (N=100, pitch=3000, rot=45) | 1.224e-07 | 1.0 | 4.42e5 |
| 4.0 | **archimedean_spiral (N=50, c=2000)** | 2.308e-07 | **0** | **0.00 -- BLACKOUT** | **square (N=50, pitch=3000, rot=45)** | 1.237e-07 | 1.0 | 2.83e5 |
| 5.0 | **archimedean_spiral (N=50, c=2000)** | 2.308e-07 | **0** | **0.00 -- BLACKOUT** | **square (N=50, pitch=3000, rot=45)** | 1.237e-07 | 1.0 | 2.83e5 |
| 6.0 | square (N=50, pitch=3000, rot=45) | 1.111e-07 | 1 | 1.96e5 | square (N=50, pitch=3000, rot=45) | 1.248e-07 | 1.0 | 1.96e5 |
| 8.0 | square (N=50, pitch=3000, rot=45) | 1.111e-07 | 1 | 1.26e5 | square (N=50, pitch=3000, rot=45) | 1.260e-07 | 1.0 | 1.26e5 |
| global | hexagonal (N=20, pitch=2000, rot=30) | 2.887e-07 | 1 | 3.14e6 | **square** (N=20, pitch=2000, rot=0) | 1.558e-07 | NaN* | 3.57e6 |

*`n_active_holes_phi0` is `None`/NaN for `global`-scope rows by this pipeline's own
established design (see `sweep/run_sweep.py`'s schema comment) -- global scope has
no single unambiguous per-M active-hole count the way per_M rows do.
`total_illuminated_area_um2_phi0` for global rows IS always populated (Defect B's
fix), and confirmed non-zero here.

**The M=4.0/5.0 blackout is confirmed directly, not just asserted**: the OLD
winner (`archimedean_spiral`, N=50, `c_um=2000`, `a_hole_um=600`) was regenerated
and run through the new partial-overlap `active_pairs.py` -- `n_active_holes=0`,
`total_illuminated_area_um2=0.00` exactly, at phi=0. It is gone from the M=4/5
Metric-1 slots in the new run and the family has ZERO survivors at M=1 through
M=8 in the 3-gate survivor table above (only M=0.0 and global retain any
`archimedean_spiral` rows).

**Explicit confirmation, checked directly (not assumed): NO new winner has
`min_illuminated_area_um2_across_phi <= 0` at any tested phi.** All 9 rows in the
new `metric1_max_density_per_M.csv` were checked programmatically; the check
returns `False` (no row violates it) -- every new winner is illuminated at every
gaze angle this pipeline tests, not merely at phi=0.

## Does a rotated square/hexagonal/rectangular design now win? Compared against the audit's own prediction

**Yes, and it matches the audit's stated prediction closely.** The audit predicted
"square at pitch=3000, rotation_deg=45 taking 7 of 8 M levels." The actual result:
`square` at exactly `pitch_um=3000, rotation_deg=45deg` wins **7 of the 8 per-M
slots** (M=1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0) -- an exact match on both the design
and the count. The 9th per-M slot (M=0.0) goes to `ring_offset_concentric`
instead (not predicted specifically, but still a non-`jittered_lattice`,
non-blackout winner). Global scope goes to `square` at `pitch_um=2000,
rotation_deg=0` -- also not `jittered_lattice`. **`jittered_lattice` wins 0 of 9
scopes**, consistent with the audit's framing that the old hull-favoring metric
had been inflating its apparent competitiveness.

## Step 14 -- the N_actual=7-vs-1 discrepancy, investigated and resolved

**Finding: not a bug, and rotation_deg's addition did not change this behavior.**
The apparent discrepancy ("CSV reports N_actual=7 ... calling the generator
directly ... returns 1 hole") was reproduced directly, and traced to conflating two
different inputs: the CSV's `N_actual=7` at `pitch_um=700, a_hole_um=2000` comes
from rows with **`N_requested=50`** (an internal candidate lattice of ~50 points,
reduced to 7 survivors by overlap rejection). Calling
`hexagonal.generate(N=7, a_hole_um=2000, pitch_um=700)` **directly** requests only
7 points in the first place -- the generator's own internal candidate-lattice size
(`n_side = ceil(sqrt(N)) + 3`) is *much* smaller for `N=7` than for `N=50`, so far
fewer candidate points exist to survive overlap rejection, and it collapses to 1.
This is expected, correct behavior for two genuinely different requests (N_requested
is not the same quantity as N_actual), not a regression. Confirmed with
`N_requested=50` explicitly: `hexagonal`, `jittered_lattice(jitter=0)`, and
`ring_offset_concentric` all give `N_actual=7` exactly, matching the CSV -- see the
Part 2 step 7 verification above, which used this exact corrected call.

## A gap found and fixed during this task's own execution

`clean_sweep_results.py` overwrites `degenerate_rows_excluded.csv` (used for its
own internal cross-check) but, unlike `compute_density.py`'s own copy of that file,
had no preservation step for it. Running it in this task's Part 4 pipeline silently
destroyed the pre-audit 432-row exclusion log (from the prior session's last
`compute_density.py` run) with no way to recover it after the fact (the OLD
`degeneracy_filter.py` code that produced those specific 432 rows was also
overwritten in place, with no separately-versioned copy kept). **Fixed**:
`clean_sweep_results.py` now preserves `degenerate_rows_excluded.csv` via the same
auto-incrementing `_legacyN` convention every other script in this pipeline uses,
before overwriting it -- this specific loss cannot recur. Reported here plainly
rather than omitted; the lost file's own content is not otherwise load-bearing (it
was a derived audit artifact, and the counts/reasons from that era are already
summarized in the previous session's own `ROTATION_SWEEP_FINDINGS.md`, which is
unaffected).

## What changed, file by file

- **`evaluation/active_pairs.py`** (Defect C/2 fix): binary center-in-pupil test
  replaced with true partial circle-overlap area (imported from this folder's own
  validated `engine/vignetting_overlap.py`, not reimplemented). New:
  `hole_illumination_fractions()`, `total_illuminated_area_um2()`,
  `DEFAULT_ACTIVE_FRAC_THRESHOLD=0.5` (documented modeling choice, CLI-configurable
  via `--active_frac_threshold`), `verify_single_hole_sanity()` (the Part 1 step-4
  gate -- PASSED, run standalone via `python3 active_pairs.py`).
- **`evaluation/ghost_margin.py`**, **`evaluation/vignetting_robustness.py`**:
  thread `a_hole_um`/`active_frac_threshold` into the fixed `active_pairs()` calls;
  surface `total_illuminated_area_um2` and `min_illuminated_area_um2_across_phi`
  in their return dicts.
- **`sweep/run_sweep.py`**: new `--active_frac_threshold` CLI flag; emits
  `total_illuminated_area_um2_phi0` and `min_illuminated_area_um2_across_phi` for
  every row, INCLUDING `--scope=global` rows (Defect B/1's "228 NaN" fix -- the
  resolution for what "phi=0" and "across phi" mean for a design evaluated across
  multiple M values is stated explicitly in `evaluate_candidate()`'s own comment,
  not left ambiguous).
- **`degeneracy_filter.py`** (Defect A fix): removed the per-family
  unit-cell/enclosing-circle area formulas as DENSITY formulas; every family now
  uses `convex_hull_area()` (buffered convex hull) unconditionally.
  `unit_cell_area()` survives only as a fast, no-regeneration feasibility
  pre-check for square/hexagonal/rectangular. `MIN_N_ACTUAL_HULL=3` now applies to
  every family (the former unit-cell-specific floor of 4 is retired, not merely
  forgotten -- its own justification no longer applies once the unit-cell density
  formula is gone).
- **`comparison_metric/compute_density.py`**: `compute_row_density()` simplified
  to the single unconditional hull-area path; no more per-family branching.
- **`comparison_metric/gates.py`** (Defect B/1 fix): new `gate_viability()`, a
  third, independently-named, composable gate (`min_illuminated_area_um2_across_phi
  > 0`), added to `DEFAULT_GATES`. Explicitly a minimum-viability FLOOR, not a
  brightness/transmission objective -- stated in the gate's own docstring.
- **`comparison_metric/run_comparison.py`**: added `preserve_legacy()` for its own
  two output CSVs (previously had none at all).
- **`clean_sweep_results.py`**: hardcoded historical exclusion-count assertion
  (220/6395) converted from a hard `sys.exit` to a reported comparison -- it was
  tuned to the PRE-audit-fix classification and would have wrongly blocked this
  task's own intentional, verified change. Also gained the
  `degenerate_rows_excluded.csv` preservation step described above.
- **`test_part3_small_case.py`**: one call-site fix (`ap.active_pairs()` now
  requires `a_hole_um`).

## Files preserved (this session's own regeneration)

- `sweep_results_legacy1.csv` -- the 8933-row rotation-inclusive state from
  immediately before this audit task's own fresh re-sweep.
- `sweep_results_PRECLEAN_legacy.csv` -- the fresh 6615-row raw sweep, before
  degeneracy cleaning.
- `sweep_results_PREROTATION_legacy.csv` -- the freshly-cleaned 6395-row base,
  before rotation rows were re-added.
- `sweep_results_with_density_PRECONTAMINATED_legacy.csv` -- the pre-audit
  8501-row density file (old formula).
- `degenerate_rows_excluded_legacy1.csv` -- see the gap noted above (this
  specific copy is the 220-row post-clean state, not the true pre-task 432-row
  state, which was lost before the preservation fix landed).
- `comparison_metric/metric1_max_density_per_M_legacy1.csv`,
  `comparison_metric/metric2_pareto_front_per_M_legacy1.csv` -- the pre-audit
  winner/Pareto files (the ones compared against throughout this report).

## Scope discipline confirmed

`array_optimization/` and `array_geometry_lab_phase2_confirmation/` were not
touched BY THIS TASK (verified via `git status`: zero changes attributable to any
command run in this session). One unrelated pre-existing observation, noted for
transparency and not acted on (acting on it would itself mean touching the
excluded folder): `git status` shows two files already absent from
`array_optimization/` (`array_candidates_field_averaged_uniform_placeholder_legacy.csv`,
`array_candidates_prevignetting_legacy.csv`, both deleted relative to the last
commit). Neither file was referenced by any command this task ran; this matches the
same "files absent between sessions" pattern already observed and documented
earlier for `array_geometry_lab/`'s own legacy files, and is left exactly as found,
consistent with not touching that folder in either direction.

**Phase 2's confirmation results were computed
against the OLD winner list and are now stale** -- the winners it validated
(`rectangular` at M=0, `jittered_lattice` at several M, `archimedean_spiral` at
M=4/5, `square` at global) do not match the new winner list at all (only the M=1-8
`square` results are even the same family, and Phase 2 never tested THIS specific
`square` configuration). **Phase 2 needs a re-run against the new winners before
being trusted** -- not done in this task, per its own explicit scope limit.
`gate_viability` was NOT added as a brightness/transmission ranking objective --
it excludes strictly-zero-illumination designs only and does not compare or reward
illuminated-area magnitude among viable survivors, consistent with this project's
standing scope exclusion of brightness/transmission as an optimization target.
