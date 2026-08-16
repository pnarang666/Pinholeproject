# array_data/

**Layer 3: storage only. No code.** Every CSV/PNG produced by `../array_calculation/`
(theoretical data) and `../array_evaluation/` (result/ranking data) lives here.

```
theoretical_data/     Output of array_calculation/: sweep_results.csv (raw sweep,
                       every family/N/spacing/M point), sweep_results_with_density.csv
                       (+ packing_density), degenerate_rows_excluded.csv (audit log of
                       what compute_density.py/clean_sweep_results.py excluded and why).
                       Plus their _legacy/_PRECLEAN/_PREROTATION/_PRECONTAMINATED
                       predecessors -- nothing is ever silently overwritten.

evaluation_results/   Output of array_evaluation/: metric1_max_density_per_M.csv
                       (single densest gate-survivor per M), metric2_pareto_front_per_M.csv
                       (density-vs-margin Pareto front per M), family_ranking.csv +
                       family_ranking_margin_vs_N.png (per-family ranking by ghost-margin
                       robustness). Plus their _legacy predecessors.
```

Figures and LaTeX report tables generated from this data for the project's write-ups
(`figs_exploration/`, `handbook_figs/`, `report_figs/`, `report_tables/`,
`IYPT_Array_Handbook.tex` and friends) remain at `array_geometry_lab/`'s own root --
they are a documentation/publication concern with fixed relative `\includegraphics`
paths, not part of this calculation/evaluation/storage split.

## Regenerating everything from scratch

```bash
cd array_calculation
python3 sweep/run_sweep.py                        # -> theoretical_data/sweep_results.csv
python3 sweep/run_rotation_sweep.py                # adds rotation_deg rows
python3 compute_density.py                         # -> theoretical_data/sweep_results_with_density.csv

cd ../array_evaluation
python3 comparison_metric/run_comparison.py        # -> evaluation_results/metric{1,2}_*.csv
python3 compare/rank_by_family.py                  # -> evaluation_results/family_ranking.csv
```

Every write here is legacy-preserved (`_legacyN` suffix, auto-incrementing) by the
producing script before being overwritten -- this folder never loses a prior run's
numbers silently.
