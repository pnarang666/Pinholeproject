# array_geometry_lab/

A geometry-focused exploration of pinhole-array **layouts** (square, hex, concentric
rings, Fibonacci/golden-angle spirals), sitting alongside `array_optimization/` — **not
modifying it, and not importing from it**. Every physics primitive this folder needs
(the ghost-separation formula, the Chapter 13 vignetting geometry) is a verbatim **copy**
of the already-validated code in `array_optimization/`, checked bit-identical against
the original validation datasets (`VALIDATION.md`) before any generator code was trusted.

## What this folder does NOT do

**No brightness. No transmission. No blur recomputation.** This is a hard design
constraint, not an omission:

- Hole diameter is a **fixed input**, `a_hole(M)`, read live every run from
  `new_sweeps/per_M_optimum_map.csv`'s `acuity_optimal_um` column — never a search
  variable, never hardcoded. If that file's values change, this pipeline picks up the
  change automatically on the next run.
- Blur itself is not recomputed. Where a "resolvable" reference size is needed (to
  define ghost margin), it is **looked up**, not computed: `r_EE(50%)` at exactly
  `a_hole(M)`, from `new_sweeps/blur_sweep.csv` (see `evaluation/ghost_margin.py`'s own
  docstring for why this specific lookup, not a diffraction-limited-acuity derivation,
  was chosen).
- No transmission or open-area fraction is computed anywhere in this folder. If you're
  looking for `T`, brightness, or a combined blur+brightness+ghosting objective, that's
  `Array_Design/array_optimization/`'s job, not this folder's.

This folder answers exactly one question, for a fixed hole size: **given this many
holes arranged in this pattern at this spacing, how much ghosting and vignetting margin
does the geometry alone provide?**

## Folder structure

This project is split into three strictly-separated layers -- physics, judgment, and
storage -- so a change to a threshold or ranking formula (layer 2) can never be
mistaken for a change to the underlying geometry (layer 1), and vice versa.

```
array_geometry_lab/
  array_calculation/    LAYER 1 -- physics/geometry only. generators/, engine/
                         (copied ghost_formula.py, vignetting_overlap.py), margins/
                         (active_pairs.py, ghost_margin.py, vignetting_robustness.py --
                         formerly this folder's top-level evaluation/), degeneracy_filter.py,
                         compute_density.py, clean_sweep_results.py, sweep/run_sweep.py,
                         sweep/run_rotation_sweep.py, and the Part 1-3 verification gates
                         (validate_copies.py, spot_check_generators.py,
                         test_part3_small_case.py). See its own README.md.
  array_evaluation/     LAYER 2 -- judgment only. comparison_metric/ (gates.py,
                         metrics.py, run_comparison.py, run_metric1_only.py) and
                         compare/rank_by_family.py. Reads layer 1's CSVs, never
                         recomputes physics. check_no_calculation_imports.py
                         mechanically enforces that. See its own README.md.
  array_data/            LAYER 3 -- storage only, no code. theoretical_data/ (layer 1's
                         output) and evaluation_results/ (layer 2's output). See its
                         own README.md.
```

Figures/report generation (`figs_exploration/`, `handbook_figs/`, `report_figs/`,
`report_tables/`, the `.tex` handbook/report sources, `generate_exploration_figures.py`,
`generate_final_report_data.py`) remain at this root -- a documentation/publication
concern with fixed relative `\includegraphics` paths, not part of the three-layer split.

## How to run Part 1's validation gate standalone

```bash
cd array_geometry_lab/array_calculation
python3 validate_copies.py
```

Must print `OVERALL VALIDATION GATE: PASS`. If it doesn't, **stop** — do not trust any
generator or evaluation output until the copy is fixed and this passes again. Re-run
this any time `engine/*.py` or the corresponding `array_optimization/` original changes;
there is no import-time link that would otherwise catch drift automatically.

## How to run the full sweep

```bash
cd array_geometry_lab/array_calculation
python3 validate_copies.py                 # Part 1 gate (fast, ~1s)
python3 spot_check_generators.py            # Part 2 spot-check (fast, ~1s)
python3 test_part3_small_case.py            # Part 3 smoke test (fast, ~1s)
python3 sweep/run_sweep.py                  # Part 4: full sweep -> ../array_data/theoretical_data/sweep_results.csv
python3 sweep/run_rotation_sweep.py         # adds rotation_deg for square/hexagonal/rectangular
python3 compute_density.py                  # adds packing_density -> sweep_results_with_density.csv

cd ../array_evaluation
python3 comparison_metric/run_comparison.py # gates + both metrics -> ../array_data/evaluation_results/
python3 compare/rank_by_family.py           # Part 4b: per-family ranking + plot
```

`run_sweep.py --help` lists every CLI-configurable range (N list, per-family spacing
lists, pupil diameter, P0). Every output CSV/PNG is legacy-preserved
(`_legacy1`, `_legacy2`, ...) before being overwritten — re-running never silently loses
a prior run's numbers.

## What `--scope=global`'s `a_hole_um` ambiguity means

`ghost_margin.py` runs in two modes, and **both are always computed and reported** — this
folder does not pick one for you:

- **`per_M`**: one row per (candidate, M). The geometry is regenerated at that specific
  M's own `a_hole(M)` — a design evaluated the way it would actually be built for a
  wearer at exactly that myopia level.
- **`global`**: one row per candidate, representing its worst case across the *entire*
  M=0–8D range tested. To make this well-defined, the geometry (hole positions) is
  generated **once**, using the **largest** `a_hole(M)` in the tested range as the
  overlap-rejection constraint — conservative, since a layout valid (non-overlapping) at
  the largest hole diameter is automatically valid at every smaller one. That **same**
  fixed set of positions is then re-evaluated at every M, using each M's own `a_hole(M)`
  only for the resolvable-blur lookup (not for regenerating the geometry).

**This means a `global`-scope row does not correspond to one buildable physical
object.** A real pair of glasses has one hole diameter. `global` answers "if this exact
hole *layout* were paired with whatever hole size is acuity-optimal for a given wearer's
M, what's the worst case across the population of wearers this layout might see?" — a
useful robustness question, but the `a_hole_um` column on the `global` row (and the
`a_hole_um_AMBIGUOUS` field in `ghost_margin.evaluate_global()`'s own output) is
explicitly flagged as *not* a single manufacturing answer. Deciding which one real
diameter to build a `global`-ranked design at is a decision this pipeline deliberately
does not make.

## Key design decisions, stated explicitly (not left implicit)

- **Concentric rings**: hole count per ring scales with ring circumference (constant
  angular spacing across rings), not a fixed count per ring — see `concentric.py`'s
  docstring for why.
- **`fibonacci_spiral` and `golden_angle` are the same formula.** Verified identical
  coordinates in `spot_check_generators.py`. `golden_angle.py` re-exports
  `fibonacci_spiral.generate()` rather than duplicating it, tagging its own `family`
  metadata field so sweep/ranking output can still distinguish the two requested names
  even though the numbers are always tied.
- **Overlap handling is rejection, not repositioning.** A candidate hole closer than
  `a_hole_um` to an already-accepted one is dropped, not moved — moving it would quietly
  change the pattern being tested. A design that requests more holes than physically fit
  returns fewer holes than requested (`N_actual < N_requested`), reported honestly.
- **Ghost margin's "resolvable" reference** is `r_EE(50%)` at the acuity-optimal
  aperture, looked up from `new_sweeps/blur_sweep.csv` — not a diffraction-limited-MAR
  derivation from `logmar_at_acuity_opt` (tried first, produced a degenerate ~1um
  threshold that every design fails trivially). See `ghost_margin.py`'s docstring.
- **The comparison plot uses the median (not max) margin across each family's tested
  spacing values at a given N.** Max was tried first and pinned every family at the
  display cap for every N (a wide-enough spacing is almost always trivially safe among
  a handful of tested values) — median only saturates when a *majority* of tested
  spacings are trivially safe, so it shows real per-family structure. See
  `rank_by_family.py`'s `plot_margin_vs_N()` docstring.

## Honest reporting

`compare/rank_by_family.py` prints every `(family, M)` combination with **zero**
structurally-safe candidates explicitly (not silently dropped from the ranking) — in the
current default sweep, `fibonacci_spiral` and `golden_angle` (the same pattern) produce
zero safe candidates at M=1–8D and under `global` scope, at the default spacing/N ranges
tested. That is a real finding about this parameter range, not a pipeline gap — widen
`--spiral_c_list` and re-run to check whether it holds at wider spacing.
