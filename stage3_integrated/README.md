# Stage 3 Integrated -- Comprehensive Theoretical Reference Dataset (Phase A)

Combines `stage3a/`'s brightness-constrained-optimum logic with `stage3_human_vision/`'s
full metric set on one shared sweep grid, and answers three open questions the prior
modules flagged but hadn't checked directly. **No recommendation is made here** -- this
is a comparison/reference dataset, not an optimizer.

Does not modify `stage1_v2/`, `stage2/`, `stage2_fixed/`, `stage3a/`, or
`stage3_human_vision/`. Reads their already-computed CSVs and imports their functions
(never re-derives physics) -- see each function's docstring for exactly which source
module it draws from.

## Cross-check performed first

`stage3a/transmission.py::relative_illuminance()` and `stage3_human_vision/
photometry.py::relative_retinal_illuminance()` (== `metrics.py::throughput_area_ratio()`)
were compared numerically at four test points (75/400/1200/4000 um) -- **exact
agreement at every point**. Standardized on `stage3_human_vision`'s version going
forward (fuller citation trail in `literature.py`); `stage3a/transmission.py` is
retired in favor of it, not deleted.

## The shared grid

`combine_metrics.py` merges `stage3_human_vision/outputs/phase3_full_metrics.csv`
(MTF50/10, Strehl, RMS radius, photometry, acuity -- 105 points, 15 apertures x 7 M,
550nm/12mm) with `stage3a/multi_EE_sweep.csv` (r_EE at 50/70/80/90%, same 105-point
grid) -> `outputs/combined_grid_550nm_12mm.csv` (105 rows, 32 columns). Merge validated
to produce exactly 105 rows (fails loudly if the two source grids ever drift apart).

## Three questions investigated directly (not assumed)

### 1. Does a brightness floor still explain the gap across ALL metrics, not just 4?

**Yes -- more strongly than stage3a found.** `constrained_optimum_all_metrics.csv`
applies stage3a's `a*_practical(M, T_min) = argmin{E_rel>=T_min} metric` logic to
**10 metrics** (r_EE at 4 percentiles, RMS radius, Strehl, MTF50, two MTF-cutoff acuity
predictions, throughput). At T_min=6.25%, **8 of 10 metrics converge to exactly 1000um
at every one of the 7 tested myopia levels** -- only Strehl (already known unstable)
and throughput (trivially degenerate alone) diverge. This extends stage3a's
"brightness floor matters more than metric choice" finding from 4 metrics to 10.

### 2. Is Strehl's non-monotonicity genuine or a 15-point sampling artifact?

**Genuine**, confirmed by `run_full_theory_sweep.py`'s `sweep_2_fine_strehl()`: a 10x
finer aperture grid (100um steps vs. the original ~100-250um variable steps) at
M=4D/8D revealed **6-7 local maxima with up to 8.4x peak-to-peak swings** --
*more* oscillation at finer resolution, not less (a sampling artifact would smooth out
at finer resolution; this got richer instead). See `outputs/strehl_investigation.png`.
Confirms `stage3_human_vision`'s original finding (peak intensity vs. propagation
distance is genuinely oscillatory in this Fresnel-regime system) and extends it: the
oscillation is dense enough that even a 100um-resolution sweep doesn't fully resolve it.

### 3. Does Stage 1's cornea-plane FWHM ring-hopping also occur at the retina plane?

**Yes, and it's worse.** `run_full_theory_sweep.py`'s `sweep_1_retina_fwhm()` applies
`stage1_v2/physics.py::locate_threshold_crossing` (the already-improved,
central-lobe-restricted algorithm) to the retina-plane PSF across the full grid.
At M=4D, FWHM jumps from **4.7um (a_hole=1500um) to 154.7um (1750um) to 11.0um
(2000um)** -- a >30x spike between adjacent, closely-spaced test apertures. The
`crossing_count` column confirms why: retina-plane PSFs in this regime have far more
rings (up to 13 crossings) than the cornea-plane profiles the original algorithm was
validated against, so even the improved algorithm's "stop at the first local minimum"
rule doesn't prevent the *global peak itself* from relocating between rings as
aperture changes. **FWHM is not a reliable single-value metric at the retina plane for
this system** -- see `outputs/retina_fwhm_ring_hopping.png`.

## Outputs (per-plot/table source traceability)

| Output | Source module | Notes |
|---|---|---|
| `mtf_curves.png` | `metrics.py::mtf_radial` (via `phase2_retina.py`) | radial MTF(f) at 3 representative M, a_hole=400um |
| `mtf50_extended.png` | `combined_grid...csv` + `wavelength_gap_sweep.csv` | MTF50 vs aperture, by M and by wavelength |
| `otf_phase.png` | `metrics.py::otf_radial`/`ptf_radial` | \|OTF\| vs Re(OTF) and the phase transfer function (PTF) -- OTF as its own quantity, distinct from MTF, never plotted before |
| `csf_comparison.png` | `contrast.py::csf_photopic_peak`, `csf_mannos_sakrison` | both variants, never merged |
| `illuminance_troland.png` | `combined_grid...csv` (`photometry.py` columns) | relative + absolute (Td), scene luminance stated on-plot |
| `acuity_models_combined.png` | `visual_acuity.py` (all 3 models) | the combined view that didn't exist before |
| `strehl_investigation.png` | `fine_strehl_sweep.csv` (this module) | coarse vs. 10x finer grid, side by side |
| `ee_all_percentiles.png` | `combined_grid...csv` (r_EE 50/70/80/90) | |
| `retina_fwhm_ring_hopping.png` | `retina_fwhm_sweep.csv` (this module) | new finding, see above |
| `pareto_all_M_overlay.png` | `pareto.py::build_default_pareto`, all 7 M | |
| `sensitivity_heatmaps_aperture_M.png` | `combined_grid...csv`, 4 metrics | |
| `sensitivity_heatmap_wavelength_aperture.png` | `combined_grid...csv` + `wavelength_gap_sweep.csv` | |
| `validation_predicted_vs_observed.png` | `stage3_human_vision/validate_against_literature.py` output | predicted vs observed LogMAR scatter (one panel per M), against `literature.get('ideal_pinhole_wang_2009')` -- the RMSE/MAE/R^2/Pearson r "Validation" pipeline stage |
| `validation_tolerance_bands.png` | `stage2_fixed/validation_gate.py` | visualizes r_EE(80%) ill-conditioning near the first null |
| `table_literature_citations.csv` | `stage3_human_vision/literature.py::CITATIONS` | rendered directly, never hand-copied |
| `table_validation_statistics.csv` | `stage2_fixed/validation_gate.py` | |
| `table_uncertainty_propagation.csv` | this module, using `photometry.py` defaults | ocular transmission 0.85-0.95 propagated into photon flux (NOT r_EE_50 -- documented why) |
| `table_validation_regression_stats.csv` | `stage3_human_vision/validate_against_literature.py` output | RMSE/MAE/R^2/Pearson r, one row per (M, predictor); re-exported, not recomputed |
| `table_error_budget_extended.csv` | `stage3_human_vision/comparison.py::error_budget`, extended | same schema, 2 new rows for findings 2-3 above |
| `constrained_optimum_all_metrics.csv` | `combine_metrics.py` | the main finding-1 table, now also covering FWHM and MTF50-based LogMAR |

## Running it

```
cd stage3_human_vision
python3 validate_against_literature.py  # ~2 min: RMSE/MAE/R^2/Pearson vs. published data (needed by generate_plots.py/generate_tables.py below)

cd ../stage3_integrated
python3 combine_metrics.py            # builds the shared 105-point grid (~instant, reuses existing data)
python3 run_full_theory_sweep.py       # ~20 min: 3 supplementary sweeps (or run "1"/"2"/"3" individually)
python3 generate_plots.py
python3 generate_tables.py
```

## Honest scope statement

The full metric set (MTF/Strehl/RMS/acuity/photometry) is computed at 550nm/12mm across
all 15 apertures x 7 M (105 points, from `stage3_human_vision`), plus a representative
8-aperture subset at 450nm/650nm and 15mm gap (`wavelength_gap_sweep.csv`) -- not the
full 15 x 3-wavelength x 2-gap grid, which would re-run the entire sweep 6x over. r_EE
alone (no MTF/Strehl/RMS) is available across the complete 630-point grid via
`stage2/outputs/r1_full_range_sweep.csv`, reused directly where sufficient (e.g. the
wavelength/gap sensitivity heatmap). Documented here, not hidden.
