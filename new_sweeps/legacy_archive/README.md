# Legacy Archive — Superseded and Invalid Datasets (new_sweeps/)

Every file in this archive is **retained for audit trail, not for use**. Each was
superseded by a specific, identified defect. Do not cite numbers from any file in
here without reading the failure reason below first.

Archived 2026-09-12. Verified at archive time: `new_sweeps/blur_sweep.csv` (the
project's single ASM theory source table) is NOT affected by the defect below —
it was already corrected on 2026-08-16 (see `new_sweeps/TIMELINE.txt`). Only the
acuity/logMAR sweep and everything derived from it were stale.

---

## 01_acuity_gridN2048_artifact/ — computed on the pre-fix diffraction grid

**Defect:** `new_sweeps/run_acuity_sweep.py` calls
`stage4_human_vision.pipeline.run_stage4_point(...)` without passing `grid_N`,
so it silently used that function's own default, `grid_N=2048`. This is the
exact same grid-resolution artifact that `new_sweeps/run_blur_sweep.py` fixed
on 2026-08-16 (r_EE values ~2x too large for large apertures) — but
`run_acuity_sweep.py`'s own call site was never updated to match, because it is
a separate script calling a separate (though related) physics pipeline. The
underlying `stage4_human_vision/pipeline.py` default itself was deliberately
NOT changed (7 other files depend on that default; fixing it project-wide was
out of scope for this fix) — only this one call site was corrected.

**How it was caught:** while building fresh result charts, `table1_optimum_summary.csv`
(this archive) reported r_EE_50=7.33µm at a_hole=700µm, M=0 — but the corrected
`blur_sweep.csv` gives 6.9175µm for that exact same point. A real point cannot
have two different values; the mismatch is the fingerprint of the acuity-side
pipeline still running on the stale 2048 grid while the blur-side pipeline had
already moved to 4096.

**Fix:** `run_acuity_sweep.py` now passes `grid_N=4096` explicitly. Corrected
2026-09-12; see `new_sweeps/TIMELINE.txt`.

**Files in `csv/`:**
- `acuity_sweep_stage4_gridN2048.csv` — the stale acuity/logMAR sweep itself.
- `table1_optimum_summary_gridN2048.csv`, `per_M_optimum_map_gridN2048.csv` —
  optimum-aperture summaries derived from the stale sweep above.
- `optimum_comparison.csv`, `table2_representative_apertures.csv` — further
  derived tables (via `generate_plots.py`), same root cause.

**Files in `figures/`:**
- `fig_M0.png` … `fig_M8.png` — per-M blur-vs-acuity-optimum comparison charts
  (via `generate_per_M_maps.py`), built from the stale acuity sweep.
- `fig3_acuity_logmar_vs_aperture.png`, `fig4_optimum_comparison.png`,
  `fig5_r7_ceiling.png` — acuity-dependent, same root cause.
- `fig1_blur_ree50_vs_aperture.png`, `fig1b/c/d_blur_ree7/8/90_vs_aperture.png`,
  `fig2_blur_rms_vs_aperture.png` — these do NOT depend on the acuity bug
  above; they are archived because they were rendered by the same
  `generate_plots.py` run on 2026-08-08, i.e. from `blur_sweep.csv` as it
  existed BEFORE the 2026-08-16 grid fix. Stale by timing, not a separate bug.

**Superseded by:** `new_sweeps/figures/corrected_model_results/` (fresh charts,
built from the corrected `blur_sweep.csv` and the re-run, corrected
`acuity_sweep_stage4.csv`) — see that folder's own contents for the current,
citable numbers.
