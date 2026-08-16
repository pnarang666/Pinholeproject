# array_evaluation/

**Layer 2: judgment only.** Reads the theoretical data `../array_calculation/`
produced (from `../array_data/theoretical_data/`), applies safety gates and ranking
formulas, and writes result/ranking CSVs to `../array_data/evaluation_results/`.

This layer never recomputes a physical quantity, and never generates or regenerates
hole geometry from scratch (it does not import `array_calculation/generators/` or
`array_calculation/engine/`). The one exception, `compare/rank_by_family.py`, is
allowed to *aggregate* already-computed per-seed margin values (worst-case-across-
seeds) -- that is a statistical rollup of numbers layer 1 already produced, not a new
physics calculation.

## What lives here

```
comparison_metric/
  gates.py             Named, composable, toggleable boolean gates (gate_ghost_safety,
                        gate_vignetting_safety, gate_viability). Combined by AND in
                        apply_gates(); which gates run is CLI-configurable.
  metrics.py            Two ranking formulas, both operating on gate survivors only:
                        metric1_max_density (single winner per M), metric2_pareto_front
                        (density vs. binding-margin Pareto front per M).
  run_comparison.py     Orchestrates: load -> gate -> rank -> write both metric CSVs.
  run_metric1_only.py   Metric 1 only, for faster reruns that don't need the front.
compare/
  rank_by_family.py     Per-family ranking by ghost-margin robustness, restricted to
                        structurally_safe candidates; also collapses stochastic
                        families' per-seed rows to a worst-case-across-seeds row.
```

## What this layer may do
- Read CSVs from `../array_data/theoretical_data/`.
- Apply thresholds/gates (all CLI-configurable, never hardcoded as the only option).
- Rank/compare already-computed rows (max, Pareto front, sort by margin).
- Write result CSVs to `../array_data/evaluation_results/`.

## What this layer may NOT do
- **Never import a generator or propagation routine from `array_calculation/`**
  (no `generators/`, no `engine/`, no `margins/active_pairs.py` /
  `ghost_margin.py` / `vignetting_robustness.py`, no `degeneracy_filter.py`,
  no `compute_density.py`). If a script here needs a new physical quantity, that
  quantity must be added in `array_calculation/` and re-exported through a CSV
  column -- never computed in this layer.
- No weighted composite score as a *default* output. `metrics.py`'s two metrics are
  reported separately (density, binding margin) — never blended into one number
  automatically.

### Mechanical enforcement

`check_no_calculation_imports.py` (this folder) statically scans every `.py` file
under `array_evaluation/` for `import`/`from` statements naming a
`array_calculation/`-layer module (by filename, since imports here are flat
`sys.path`-based, not packages) and fails loudly if it finds one. Run it any time a
new file is added to this layer:

```bash
python3 array_evaluation/check_no_calculation_imports.py
```

## Running it

```bash
cd array_evaluation
python3 comparison_metric/run_comparison.py           # gates + both metrics
python3 comparison_metric/run_comparison.py --gates ghost_safety,vignetting_safety
python3 compare/rank_by_family.py                     # per-family ranking + plot
```

Every output CSV/PNG is legacy-preserved (`_legacyN`) before being overwritten.
