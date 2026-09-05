# comparison_metric/

> **Folder moved** (calculation/evaluation/data split): this folder now lives at
> `array_evaluation/comparison_metric/`. `degeneracy_filter.py`, `compute_density.py`,
> and `clean_sweep_results.py` (referenced below via `../`) now live in
> `array_calculation/`, and `sweep_results*.csv` / `metric{1,2}_*.csv` now live under
> `array_data/theoretical_data/` and `array_data/evaluation_results/` respectively --
> see `array_evaluation/README.md` and `array_data/README.md` for the current layout.
> The historical narrative below (paths, `../` references) describes the PRE-split
> layout and is kept as-is for its diagnostic content, not as a current path guide.

Gated density-vs-safety comparison over `sweep_results.csv` (theoretical geometry
sweep, all 10 families). Produces CSVs only -- no plotting in this pass; that comes
after these results are inspected.

## STATUS: RESOLVED -- density-formula defect fixed, pipeline re-run clean

A physically-impossible-density defect was found, root-caused to **two independent
formula bugs** (not one), both fixed, and the full pipeline re-run end to end. See
"Known defect and its fix" below for the complete diagnosis and the two corrections
applied. `sweep_results_with_density.csv`, `metric1_max_density_per_M.csv`, and
`metric2_pareto_front_per_M.csv` on disk now reflect the fixed pipeline; the
pre-fix versions are preserved as `*_PRECONTAMINATED_legacy.csv` next to each,
purely for before/after comparison -- do not use the `_PRECONTAMINATED_legacy`
files for anything else.

## Degeneracy exclusion now lives at the ROOT, not just inside this folder

**Important, found after the fix above was already verified working**: the
degeneracy filter (unit-cell feasibility check, hull/circle minimum-point and
near-degenerate checks) was, for a while, only ever applied INSIDE
`compute_density.py`'s own computation -- `../sweep_results.csv` itself, the file
every other script in this project reads, still carried all 6615 original rows
including the 220 degenerate ones. That was exactly the kind of recurrence this
whole effort was meant to prevent: any future script reading `sweep_results.csv`
directly (not through `compute_density.py`) would see the contaminated rows again.

This is now fixed by extracting the identical exclusion logic into
**`../degeneracy_filter.py`** (one shared `is_degenerate(row) -> (bool, reason)`
function, plus the area-formula helpers it depends on) and running
**`../clean_sweep_results.py`** once to make `../sweep_results.csv` itself clean at
the root (6395 rows; the full original 6615-row file is permanently archived as
`../sweep_results_PRECLEAN_legacy.csv`). `compute_density.py` now imports
`degeneracy_filter.py` instead of carrying its own private copy of this logic --
verified, via an order-independent key-based merge across every shared column (not
just row counts), to produce byte-for-byte equivalent results to the pre-extraction
version. See `../degeneracy_filter.py`'s own docstring for the full two-mechanism
writeup (previously duplicated in this file; now stated once, there).

**Practical effect**: `compute_density.py`, run against the now-pre-cleaned
`sweep_results.csv`, finds nothing left to exclude (0 rows, confirmed) -- its own
internal degeneracy check is now a defensive safety net for future contamination,
not the primary enforcement point. If `../sweep/run_sweep.py` is ever re-run to
regenerate `sweep_results.csv` from scratch, **re-run `python3
../clean_sweep_results.py` before trusting it for density work** -- a fresh sweep
output will contain degenerate rows again until cleaned.

## Pipeline order

Root-level cleaning (one-time, or after any fresh `sweep/run_sweep.py` run) must
happen before Part 1; Part 1 must run and pass its own sanity check before Parts
2-4 (Parts 2-3 are independent of each other; Part 4 needs both).

```bash
cd Array_Design/array_geometry_lab
python3 clean_sweep_results.py    # Root-level clean: archives the original as
                                   # sweep_results_PRECLEAN_legacy.csv, overwrites
                                   # the active sweep_results.csv with the
                                   # degeneracy_filter.py-clean subset
cd comparison_metric
python3 compute_density.py        # Part 1: writes ../sweep_results_with_density.csv
python3 run_comparison.py         # Parts 2-4: writes metric1_max_density_per_M.csv
                                   #            and metric2_pareto_front_per_M.csv
# optionally:
python3 run_comparison.py --gates ghost_safety,vignetting_safety   # (explicit default)
python3 run_comparison.py --gates ghost_safety                     # one gate only
```

`sweep_results.csv` is never modified BY compute_density.py or run_comparison.py
(only by `clean_sweep_results.py`, and only once its own count cross-check against
`../degenerate_rows_excluded.csv` passes -- it refuses to write anything otherwise).
`sweep_results_with_density.csv` is a derived file; `metric1_max_density_per_M.csv`
/ `metric2_pareto_front_per_M.csv` are output files. Re-running never overwrites the
upstream CSVs without first preserving a legacy copy.

## Part 1 -- `compute_density.py`: packing density, per family

Computes `packing_density_per_area_um-2 = N_actual / bounding_area_um2` for every row
of `sweep_results.csv`. `bounding_area_um2` is defined **differently per family**,
because "the area a pattern occupies" genuinely means different things for a
repeating lattice, a radial ring pattern, and an irregular/stochastic point set --
using one formula everywhere would either undercount the lattices (a convex hull
clips off the half-cell margin around boundary holes) or be undefined for the
irregular families (no unit cell exists).

| Families | Area definition | Why |
|---|---|---|
| `square`, `rectangular` | `N_actual * pitch_x_um * pitch_y_um` (square: `pitch_x=pitch_y=pitch_um`) | unit-cell area x count; exact for a repeating rectangular lattice |
| `hexagonal` | `N_actual * (sqrt(3)/2) * pitch_um**2` | closed-form hexagonal unit-cell area x count |
| `concentric`, `ring_offset_concentric` | `pi * r_outer**2`, `r_outer` = actual max radius of the realized (recentered) hole coordinates | radial pattern, not a repeating lattice -- no unit cell applies; `r_outer` is measured from the ACTUAL regenerated coordinates rather than re-derived from `ring_spacing_um * n_rings` internally, so it reflects the pattern's true realized footprint (including any overlap-rejection thinning of the outer ring) without duplicating `concentric.py`'s own ring-count formula externally |
| `fibonacci_spiral`, `golden_angle`, `archimedean_spiral`, `poisson_disk`, `jittered_lattice` | convex hull area of the actual generated coordinates (`scipy.spatial.ConvexHull`) | no closed-form cell area for irregular spacing; the hull is the tightest area that still honestly bounds every hole. For the two stochastic families this is computed **per seed** (density varies seed to seed since the realized hull shape itself varies) -- never averaged before the gates are applied |

The three unit-cell families need no coordinate regeneration (the formula is analytic
from `N_actual` + spacing alone). Every other family's coordinates are regenerated by
calling that family's own `generators/*.py generate()` with the exact
`(N_requested, a_hole_um, spacing_params, seed)` recorded in that row -- deterministic
given those inputs, so this reproduces the identical geometry `sweep/run_sweep.py`
itself evaluated, not an approximation. `compute_density.py` raises immediately if a
regenerated row's `N_actual` doesn't match the CSV's own value (would mean the
generator isn't reproducing the original row).

**Validated** (`compute_density.py`'s own printed sanity check): at the tightest
tested spacing where holes are not exactly tangent (`a_hole_um/pitch_um = 0.857`,
avoiding the exact-tangency tie-break in `base_generator.reject_overlapping()` that
otherwise discards ~half the lattice), the realized packing fraction is 0.577 for
`square` (theoretical max 0.785) and 0.666 for `hexagonal` (theoretical max 0.907) --
both exactly consistent with the `(a_hole_um/pitch_um)**2` scaling implied by the
formulas above, confirming the definitions are correct at THAT spacing, not just
"close enough." This check alone was insufficient to catch the defect described next,
because it only ever exercised one spacing regime -- see below.

### Known defect (found after the initial validation above) and its fix

**Confirmed, 2025-08 review**: 412 of 6615 rows (6.2%, in 8 of 10 families) had
`open_area_fraction = pi*(a_hole_um/2)**2 * packing_density_per_area_um-2 > 1.0` --
physically impossible (holes cannot cover more area than their own packing region).
This had already corrupted `metric1_max_density_per_M.csv`: the reported M=0.0 and
M=global "winner" was `hexagonal` at `N_actual=1` (a single leftover hole, not a
valid array) with `open_area_fraction=7.40`.

**Fix, step 1 -- a degeneracy filter** (implemented in `compute_row_density()`,
applied before any density value is written or used downstream): rows are now
**excluded entirely** (not given a NaN density and left in) whenever:
- unit-cell family (`square`/`rectangular`/`hexagonal`) and `N_actual < 4` -- a
  documented **modeling judgment call** (a 2x2 minimum tiling), not a physical
  constant;
- hull/enclosing-circle family and `N_actual < 3` -- a hard mathematical minimum
  (no hull or non-degenerate circle exists below 3 points); or
- hull/enclosing-circle family and the computed area is pathologically small
  relative to `N_actual * a_hole_um**2` (a near-collinear/near-coincident point set)
  -- another documented, deliberately loose modeling threshold.

Excluded rows are logged to `../degenerate_rows_excluded.csv` (family, N_requested,
N_actual, spacing_params, a_hole_um, seed, M, reason) -- auditable, not silent. This
filter is real and correctly removes genuinely-degenerate cases (122 rows on the
current sweep -- e.g. every previously-silent NaN case, `N_actual` of 1 or 2, is now
an explicit, logged exclusion instead of a silent NaN).

**Fix, step 3 -- the independent `open_area_fraction <= 1.0001` assertion, run
immediately after the filter: FAILED on the first attempt.** 398 of the remaining
6493 rows (6.1%) still violated physical validity after the degeneracy filter alone,
confirming a **second, different bug** existed, exactly as this project's own task
brief anticipated by requiring this assertion in the first place. Root cause,
diagnosed and confirmed with direct evidence (not guessed) before any fix was
attempted:

1. **Unit-cell families**: `open_area_fraction` for these three families reduces
   algebraically to a function of `a_hole_um / pitch_um` **alone** -- `N_actual`
   cancels out of `N_actual / (N_actual * cell_area)` entirely. Confirmed directly:
   at a fixed ratio, `open_area_fraction` was bit-identical across wildly different
   `N_actual` (9, 25, and 48, for one `square` case, all reading `1.227`) -- so
   **no `N_actual` floor of any size could fix this family's defect**, since the
   violation does not depend on `N_actual` at all. It occurs whenever the requested
   `pitch_um` is tight enough relative to `a_hole_um` that the *nominal, undisturbed*
   unit cell is already smaller than a single hole's own footprint -- i.e. the
   requested lattice spacing is not achievable as a genuine periodic tiling at that
   hole size, independent of how many points survive overlap-rejection.
2. **Enclosing-circle / convex-hull families**: the bounding area was computed from
   bare hole **centers**, which never includes the physical margin of the holes' own
   radius around the boundary. Confirmed directly with a real, legitimate case: a
   `concentric` row with `N_actual=7` where **every pairwise hole-center distance is
   >= `a_hole_um`** (i.e. a genuinely valid, non-overlapping configuration) still
   produced `open_area_fraction=1.587`, purely because `pi*r_outer**2` (centers only)
   omitted the ~1000um physical radius each hole disk extends beyond its center.
   This was a small-`N` boundary effect that shrinks as `N` grows but is severe for
   small realized point sets in general -- **not** simply "too few points" in the
   sense the degeneracy filter's point-count floor targets (the offending
   `N_actual=7` case comfortably cleared the `>=3` floor).

**Both mechanisms are now fixed** (in `compute_row_density()`,
`enclosing_circle_area()`, and `convex_hull_area()`):

1. **Unit-cell families**: a direct feasibility check, independent of `N_actual`,
   excludes any row where `hole_footprint_area = pi/4 * a_hole_um**2` exceeds the
   row's own `cell_area` (`area / N_actual`) -- i.e. the SAME criterion the physical
   assertion checks, applied as an exclusion up front rather than discovered only at
   the end. This is the direct fix for mechanism 1 above, not a proxy through
   `N_actual`.
2. **Enclosing-circle / convex-hull families**: both area functions now take
   `a_hole_um` and return a **buffered (Minkowski-offset) area** instead of the bare
   centers-only area -- `pi*(r_outer + a_hole_um/2)**2` for circles;
   `hull_area + hull_perimeter*(a_hole_um/2) + pi*(a_hole_um/2)**2` for hulls (the
   standard closed-form area of a convex shape grown outward by a constant radius).
   This is the geometrically correct definition of "area occupied by the physical
   hole disks," not a patch applied only to failing rows -- it is now the area
   definition for all seven of these families, always. Re-checked against the same
   `concentric N_actual=7` case above: `open_area_fraction` now reads a sane `0.728`.

**Result after both fixes**: re-running `compute_density.py` end to end, the
`open_area_fraction <= 1.0001` assertion **passed for all 6395 surviving rows on the
first re-run** -- no further violations, no third bug. 220 of 6615 rows (3.3%) were
excluded in total by the (now two-part) degeneracy filter, logged in
`../degenerate_rows_excluded.csv` with per-row reasons (point-count floor or
feasibility-ratio floor, distinguishable directly from the `reason` column).

### Permanent policy: minimum-N-actual viability is a per-family design requirement, not a one-off

**This defect is now a known failure class for this codebase, not a one-off bug.**
Any future family/generator added to this density pipeline MUST define, and justify
in a code comment, its own minimum-`N_actual` (and, if its area formula is
point-geometry-based rather than a closed-form unit cell, its own
near-degenerate-geometry check) **before** its rows are trusted for density
comparison -- and, as this defect demonstrates, a point-count floor alone is not
automatically sufficient: check algebraically whether the family's area formula can
produce an impossible `open_area_fraction` independent of `N_actual` (as the
unit-cell families do), and check whether the formula omits any physical margin that
matters at the family's typically-tested `N_actual` range (as the boundary-based
families do). The `open_area_fraction <= 1.0001` assertion in `compute_density.py`
must never be removed or weakened to "make the pipeline pass" -- it exists
specifically to catch exactly this class of defect, and did.

## Part 2 -- `gates.py`: pluggable safety gates

Two independent, named gate functions, combined by AND in `apply_gates()`:

- `gate_ghost_safety`: `worst_case_ghost_margin > 0`
- `gate_vignetting_safety`: `worst_case_vignetting_margin > 0`

Both are active by default (`DEFAULT_GATES`). **Confirmed against
`sweep_results.csv` before this module was written**: the two are not redundant --
among rows with `worst_case_ghost_margin == inf`, the fraction that also have
`worst_case_vignetting_margin <= 0` ranges from 36% (`concentric`) to 89%
(`fibonacci_spiral`/`golden_angle`) depending on family. Neither gate is a proxy for
the other; both are required by default and evaluated independently.

**No reproducibility/seed-variance gate exists here, by explicit scope decision.**
`family_ranking.csv`'s `high_seed_variance` column is not consulted anywhere in this
folder. Stochastic families' greater susceptibility to failing Gates 1/2 is expected
to show up naturally in `run_comparison.py`'s survivor-count report, not be
pre-filtered before the comparison runs. Adding a future gate (e.g.
reproducibility) is a one-function addition to `GATES` in `gates.py` -- nothing in
`metrics.py` or `run_comparison.py` needs to change.

## Part 3 -- `metrics.py`: two metrics over gate survivors

Both metrics assume the caller already ran `gates.apply_gates()`; neither gates
anything itself.

**Metric 1 (`metric1_max_density`)**: per `M` (and `'global'`), the single row with
the highest `packing_density_per_area_um-2`. A strict, single-winner view -- one row
answers "what's the densest safe design at this M."

**Metric 2 (`metric2_pareto_front`)**: per `M` (and `'global'`), the full 2D Pareto
front over `(packing_density_per_area_um-2, binding_margin)`, where
`binding_margin = min(worst_case_ghost_margin, worst_case_vignetting_margin)` per row
-- a candidate is only as safe as its weaker gate. A row is on the front if no other
row simultaneously has `>=` density AND `>=` binding margin, with at least one
strictly greater (standard 2D Pareto dominance, implemented directly, no external
library). The metric's whole purpose is to show the density/safety-margin tradeoff,
so the **entire front** is output, not one point.

`+inf` margins (zero active hole pairs -- a real, structurally-safe result, not
missing data) are replaced by a finite **sentinel** for this Pareto comparison only:
`10x` the largest finite margin value observed across the survivor set passed in.
Letting `+inf` itself into the comparison would make every infinite-margin row
trivially co-dominant on the margin axis regardless of density; the sentinel keeps
"structurally safe beats numerically safe" ordering (it's large enough that a
genuinely-infinite-margin row still outranks every finite-margin row) while staying
finite enough to participate in ordinary dominance comparison. The sentinel is
computed once per `run_comparison.py` invocation (from the whole gated survivor set,
not per-`M`) and is recorded in the output CSV's own
`binding_margin_sentinel_used` column, so it's never a hidden constant.

By construction, Metric 1's winner for a given `M` is **always** also on Metric 2's
front for that `M` (nothing can have both strictly-higher density and a
tied-or-better binding margin than the single highest-density survivor, since nothing
has higher density at all). `run_comparison.py` checks this explicitly for every `M`
and prints an unmissable warning if it ever fails -- it hasn't, across the full
default-gated run.

**Observed on the current (post-density-fix) dataset** (not a design assumption --
see `metric2_pareto_front_per_M.csv`): the front has 7 points at `M=0.0`, 4 at
`M=global`, and collapses to exactly 1 point at every other tested `M`
(1.0-8.0). The `M=0.0`/`global` fronts show a genuine density/margin tradeoff --
e.g. at `M=0.0`, `rectangular` (N_requested=20, density=2.96e-7, finite
`binding_margin=1.0`) is denser than `square`/`rectangular`'s `+inf`-margin rows
(density=2.50e-7) but has a weaker margin, and neither dominates the other, so both
remain on the front. At `M=1.0-8.0` the front is a single point because every
gate-surviving row at those `M` happens to have `+inf` margin (structurally safe by
zero active pairs, not numerically) -- with margin tied at the sentinel for
everyone, only density differs, collapsing the front to the density-maximizer alone.
This is consistent with `THEORETICAL_DATASET_EXPLORATION.tex`'s own finding that
safety is currently binary at most tested `M` (trivially-safe-by-zero-active-pairs,
or clearly unsafe, with little tested borderline territory) -- not an artifact of
the implementation. A synthetic 4-point check confirms `_pareto_front_2d` itself
returns multi-point fronts whenever the underlying data has an actual tradeoff,
exactly as seen at `M=0.0` and `M=global` above.

## Part 4 -- `run_comparison.py`: the runner

1. Loads `sweep_results_with_density.csv`.
2. Applies the active gates (`--gates`, default `ghost_safety,vignetting_safety`).
3. Prints survivor counts per family (before -> after gating, whole-dataset and
   per-`M` breakdowns) -- makes "stochastic families get filtered out naturally"
   checkable directly from the printout rather than asserted.
4. Runs Metric 1, writes `metric1_max_density_per_M.csv`.
5. Runs Metric 2, writes `metric2_pareto_front_per_M.csv`.
6. Prints, per `M`: Metric 1's winner (family, N, density) vs. Metric 2's front size,
   and the Metric-1-on-Metric-2-front consistency check described above.

### Impact of the density-formula fix (see "Known defect" above) on Part 4's output

Survivor counts, before (contaminated density formula) vs. after (fixed), default
gates, whole-dataset per family:

| family | before | after | delta |
|---|---:|---:|---:|
| archimedean_spiral | 26 | 26 | 0 |
| concentric | 78 | 73 | -5 |
| fibonacci_spiral | 15 | 14 | -1 |
| golden_angle | 15 | 14 | -1 |
| hexagonal | 43 | 33 | -10 |
| jittered_lattice | 736 | 663 | -73 |
| poisson_disk | 180 | 180 | 0 |
| rectangular | 135 | 113 | -22 |
| ring_offset_concentric | 70 | 65 | -5 |
| square | 45 | 35 | -10 |
| **total** | **1343 / 6615 (20.3%)** | **1216 / 6395 (19.0%)** | **-127** |

This drop is **expected and correct**: every removed row was either genuinely
degenerate (too few points to define an area at all) or was a "safe-and-dense"
result that only looked dense because of one of the two formula bugs -- removing them
is the fix working, not a regression. `poisson_disk` and `archimedean_spiral` are
unchanged because none of their gate-surviving rows happened to be degenerate or
formula-infeasible in this sweep.

**Metric 1 winners, before vs. after** (family / N_requested / N_actual / density):
at `M=0.0` and `M=global`, the pre-fix winner was `hexagonal` at `N_actual=1` with
`open_area_fraction=7.40` (impossible -- see "Known defect" above); post-fix, the
winners are `rectangular` (N_requested=20, N_actual=11) at `M=0.0` and `square`
(N_requested=20, N_actual=9) at `M=global`, both physically valid. Every one of the
9 corrected winners (one per `M`) has been checked explicitly against its family's
minimum-viable `N_actual` threshold from Part 1 (`>=4` unit-cell, `>=3`
hull/circle) -- **all 9 pass with room to spare** (`N_actual` 9-50 across the set,
well above each respective floor of 3 or 4). Full detail:
`metric1_max_density_per_M.csv`; pre-fix values for comparison are preserved in
`metric1_max_density_per_M_PRECONTAMINATED_legacy.csv` /
`metric2_pareto_front_per_M_PRECONTAMINATED_legacy.csv`.

## `../family_ranking.csv` -- confirmed UNAFFECTED by the density defect, does not need regenerating for this

`family_ranking.csv` (and the script that builds it, `../compare/rank_by_family.py`)
predates `comparison_metric/` entirely -- confirmed by file timestamp, it was last
built before `compute_density.py` existed at all. Checked directly, not assumed:

- `rank_by_family.py`'s only CSV dependency is `../sweep_results.csv`
  (`DEFAULT_IN_CSV`); it never reads `sweep_results_with_density.csv`.
- Its own source contains **zero** references to `density`, `packing`,
  `compute_density`, or `comparison_metric` anywhere (checked with `grep -rn` across
  the whole `compare/` directory, not just this one file).
- `family_ranking.csv`'s columns are exactly `sweep_results.csv`'s own columns
  (`worst_case_ghost_margin`, `worst_case_vignetting_margin`, `structurally_safe`,
  `n_active_pairs_phi0`, `n_active_holes_phi0`) plus seed-variance diagnostics
  (`ghost_margin_std_across_seeds`, etc.) -- there is no density-derived column to
  have been corrupted in the first place.

**Conclusion: `family_ranking.csv` was never contaminated by the density-formula
defect and does not need regenerating because of it.** Ghost/vignetting margins are
computed by a completely separate pipeline (`sweep/run_sweep.py` ->
`evaluation/ghost_margin.py` / `vignetting_robustness.py`) that has no dependency on
`compute_density.py`'s area formulas at all.

**Separate, honest caveat** (not the density bug, but worth stating so it isn't
mistaken for "all clear"): the `family_ranking.csv` currently on disk was built from
the OLD, pre-`clean_sweep_results.py` `sweep_results.csv` (6615 rows), so it still
lists some of the same rows now excluded from the active `sweep_results.csv` as
density-degenerate (e.g. its own `rank_within_M=1` row is `square`, `N_actual=1` --
the identical single-leftover-hole case flagged in "Known defect" above). Those
rows' `worst_case_ghost_margin`/`worst_case_vignetting_margin` values are NOT wrong
(a 1-hole array trivially has zero active pairs, so `+inf` margin is the correct
physics answer, not a bug) -- but whether a design that degenerate should count as
a meaningful "safe candidate" in a ranking is a separate judgment call from the
density-formula defect this task closed, and is left as-is here since it was not
part of this task's scope ("close this specific gap only, nothing else needs
changing"). Re-running `rank_by_family.py` against the now-cleaned
`sweep_results.csv` would produce a `family_ranking.csv` without those rows, if and
when that judgment call is made.

### CLI

```
--gates GATE1,GATE2   comma-separated gate names (default: ghost_safety,vignetting_safety)
--in_csv PATH         input CSV (default: ../sweep_results_with_density.csv)
```

Unknown gate names raise immediately with the list of known gates, rather than
silently ignoring the typo.
