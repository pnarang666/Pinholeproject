# Data Collection -- Stage 3 / Stage 3a / Stage 3 Integrated Sweep Outputs

A consolidated copy (not a move -- originals remain in place in their own stage
folders) of every CSV, table, and plot produced by the three human-vision-optimization
stages, organized by stage and by file type for easy browsing/download in one place.

**stage3a's plots were generated fresh for this collection** -- `combine_and_select.py`
and `plot_blur_then_constraint.py` existed as scripts but had never actually been run,
so no PNGs existed for stage3a before now. `stage3_human_vision` and `stage3_integrated`
data/plots were already computed and verified earlier in this project and are copied
here as-is, not recomputed.

## `stage3_human_vision/` -- human-vision-constrained metrics (105-point sweep, 550nm/12mm)

- `csv/metrics_sweep.csv` -- the raw PSF-level sweep (Strehl, MTF50/10, RMS radius, EE)
- `csv/phase3_full_metrics.csv` -- extended with photometry + acuity predictions
- `csv/optimum_by_metric_and_M.csv`, `stage2_only_optimum.csv`, `metric_correlation_summary.csv`, `error_budget.csv`
- `plots/` -- 9 plots: EE(80%), RMS, Strehl, MTF50 vs aperture; illumination vs aperture;
  optimum-vs-myopia by candidate metric; Pareto fronts at M=1/4/8D

**Headline finding**: RMS spot radius (not r_EE or MTF50) is the metric whose optimum
tracks real commercial/clinical designs closely; Strehl ratio is ill-posed in this
system's Fresnel regime.

## `stage3a/` -- brightness-constrained-optimum hypothesis test

- `csv/multi_EE_sweep.csv` -- r_EE at 50/70/80/90% across the full 105-point grid
- `csv/stage3a_constrained_optimum_wl550nm_gap12mm.csv` -- a*_practical(M, T_min)
- `csv/stage3a_multi_percentile_constrained.csv` -- convergence check across percentiles
- `plots/stage3a_fig1_blur_vs_brightness_wl550nm_gap12mm.png` -- blur vs aperture with
  illuminance overlay, M=4D
- `plots/stage3a_fig2_optimum_vs_Tmin_wl550nm_gap12mm.png` -- constrained optimum vs
  brightness floor, all 7 myopia levels
- `plots/stage3a_fig4_blur_then_constraint_Tmin0.0625.png` -- two-panel: unconstrained
  vs. brightness-floor-constrained blur curves side by side

**Headline finding**: a brightness floor of ~6-9% relative illuminance alone moves the
optimum from 300-400um into the exact clinical bracket (940-1750um), uniformly across
all tested myopia levels -- extended in `stage3_integrated/` to 10 metrics, 8 of which
converge to exactly 1000um under this floor.

## `stage3_integrated/` -- the full comparison dataset (Phase A of the integrated model)

- `csv/combined_grid_550nm_12mm.csv` -- the merged 105-point grid (stage3_human_vision + stage3a)
- `csv/constrained_optimum_all_metrics.csv` -- brightness-floor optimum for 10 metrics at once
- `csv/wavelength_gap_sweep.csv` -- 450/650nm and 15mm-gap coverage
- `csv/fine_strehl_sweep.csv` -- 100um-step Strehl investigation (M=4/8D)
- `csv/retina_fwhm_sweep.csv` -- retina-plane FWHM, full grid
- `tables/` -- validation statistics, uncertainty propagation, extended error budget,
  and the literature citation table (rendered directly from `literature.py`)
- `plots/` -- 11 plots: MTF curves + MTF50 extended, CSF comparison, illuminance/Trolands,
  combined acuity-model comparison, Strehl investigation (coarse vs. fine grid),
  EE at all 4 percentiles, retina-plane FWHM ring-hopping, Pareto fronts (all 7 M
  overlaid), **2 sensitivity heatmaps** (aperture x myopia, and wavelength x aperture),
  validation tolerance bands

**Headline findings**: Strehl's non-monotonicity is genuine (a 10x finer grid revealed
*more* oscillation, not less); the cornea-plane FWHM ring-hopping instability also
appears at the retina plane, and is worse there.

## Regenerating from scratch

```
cd stage3_human_vision && python3 run_stage3.py --resweep
cd ../stage3a && python3 combine_and_select.py && python3 plot_blur_then_constraint.py
cd ../stage3_integrated && python3 run_full_theory_sweep.py && python3 generate_plots.py && python3 generate_tables.py
```

Full runtime: ~6 min (stage3_human_vision) + ~instant (stage3a) + ~20 min
(stage3_integrated's supplementary sweeps) = roughly half an hour end to end.
