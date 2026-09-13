# 08_stale_acuity_aperture_artifact/ — computed with a_hole(M) sourced from the stale acuity sweep

**Retained for audit trail, not for use.** Superseded by a specific, identified defect.

Archived 2026-09-13.

**Defect:** `new_sweeps/run_acuity_sweep.py` silently used `stage4_human_vision.pipeline`'s
own `grid_N=2048` default (never updated to match `run_blur_sweep.py`'s 2026-08-16 fix
to `grid_N=4096`) — see `new_sweeps/legacy_archive/01_acuity_gridN2048_artifact/README.md`
for the full defect writeup. Every file in this folder is a candidate/ranking/winner
table computed by this lab's own pipeline (`sweep/run_sweep.py` onward) while
`new_sweeps/per_M_optimum_map.csv`'s `acuity_optimal_um` column — read live by
`array_calculation/margins/ghost_margin.py::load_acuity_optimal_aperture()` and used
as the actual `a_hole(M)` fed into every candidate's hole generation — was still
computed from that stale, pre-fix acuity sweep.

**Fix:** `new_sweeps/run_acuity_sweep.py` corrected 2026-09-12 (see that folder's own
TIMELINE.txt), acuity sweep re-run, `per_M_optimum_map.csv` regenerated, then this
entire lab's pipeline re-run end-to-end in the same order as
`array_geometry_lab/README.md`'s "How to run the full sweep": `validate_copies.py`
(PASS) → `spot_check_generators.py` (PASS) → `test_part3_small_case.py` (PASS) →
`sweep/run_sweep.py` → `sweep/run_rotation_sweep.py` → `compute_density.py` →
`comparison_metric/run_comparison.py` → `compare/rank_by_family.py` →
`effective_density_ranking.py` (both `--c_min_um=0` and `--c_min_um=55`) →
`compute_gaze_weighted_metrics.py` → `gaze_weighted_ranking.py` → `final_winner.py` →
`paper_score.py` → `paper_soft_gates.py` → `shen_model/shen_evaluator.py`. All ran
clean (no errors) on the corrected data.

**IMPORTANT, verified directly (not assumed):** despite the bug, the actual
per-M **acuity-optimal aperture** (the discrete grid point `argmin(logMAR)` picks)
came out **identical** before and after the fix, for all 8 tested M values — the
grid-resolution bug inflated the raw blur/logMAR magnitudes but never flipped which
candidate aperture won. Direct proof: `diff` between this folder's
`gaze_weighted_winner_per_M_legacy1.csv` and the current (post-fix)
`../../array_geometry_lab/array_data/evaluation_results/gaze_weighted_winner_per_M.csv`
returns **zero differences** (every column, byte-for-byte); same for
`FINAL_WINNER_PER_M_legacy1.csv` vs. the current file. `array_geometry_lab/
fabrication_package/`'s hole-coordinate CSVs and SVG masks were also regenerated and
diffed — also byte-identical.

**What this means:** the intermediate candidate pool (`sweep_results.csv`, 8501/9045
rows) DID contain different numbers under the bug (different `a_hole_um` per M
feeding into every candidate's geometry generation before this fix) — that
intermediate pool is what's archived here for a complete audit trail. But every
**end deliverable** this project has already reported or shipped (the gaze-weighted
winner-per-M table, the worst-case FINAL_WINNER_PER_M table, and the physical
fabrication masks) is confirmed unaffected. Nothing downstream needed to change as a
result of re-running this pipeline — the re-run was necessary to *prove* that, not
because the shipped answer was wrong.

**Files in `csv/`:** `sweep_results_legacy5.csv` (the full stale candidate pool, all
families), `gaze_weighted_metrics_legacy2.csv`, `metric1_max_density_per_M_legacy6.csv`,
`metric2_pareto_front_per_M_legacy6.csv`, `gaze_weighted_winner_per_M_legacy1.csv`,
`FINAL_WINNER_PER_M_legacy1.csv`, `family_ranking_legacy4.csv`,
`effective_density_winner_per_M_cmin0_legacy5.csv`,
`effective_density_winner_per_M_cmin55_legacy6.csv`,
`paper_score_all_candidates_legacy5.csv`, `paper_score_winner_per_M_legacy5.csv`,
`paper_score_vs_current_winner_legacy5.csv`, `paper_soft_gates_winner_per_M_legacy1.csv`,
`shen_model_results_legacy3.csv`, `shen_model_winner_per_M_legacy3.csv`.

**Files in `figures/`:** `family_ranking_margin_vs_N_legacy4.png`.

**Superseded by:** the current (non-`_legacy`) files of the same names throughout
`array_data/`, `shen_model/`, and `fabrication_package/`.
