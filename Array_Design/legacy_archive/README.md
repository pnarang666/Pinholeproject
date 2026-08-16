# Legacy Archive — Superseded and Invalid Datasets

Every file in this archive is **retained for audit trail, not for use**. Each was
superseded by a specific, identified defect. Do not cite numbers from any file in
here without reading the failure reason for its folder first.

Archived 2026-08-16. Verified at archive time: no script in the project *reads*
any of these files as input (scripts reference "legacy" only in docstrings and as
*write* targets when creating fresh backups), so relocating them does not break
any pipeline.

---

## 01_gridN2048_artifact/ — computed at insufficient grid resolution

**Defect:** the wave-optics propagation grid was set to `grid_N = 2048`, which
produced an `r_max_lens` exclusion artifact that triggered on **100% of sweep
points**. Corrected default is `grid_N = 4096`.

**How it was caught:** three finalists with *different* aperture sizes
(2000 µm, 1250 µm) reported the **identical** blur value to 11 decimal places
(`7.32753141126`). Real single-hole diffraction cannot give the same blur radius
for different apertures — the shared value is the fingerprint of an
aperture-independent grid artifact dominating the measurement. Independently
confirmed by recomputing the same case at both resolutions: the 2048 value is
exactly **2×** the 4096 value for the largest apertures.

**Files:** `optimise_grid_`, `optimise_sensitivity_`, `optimise_best_per_M_packing_`,
`multi_hole_blur_sweep_`, `blur_sweep_` (all `_legacy_gridN2048`).

**Status:** all regenerated at `grid_N = 4096`. Blur numbers in these files are
wrong by up to 100% for apertures ≥ 1250 µm.

---

## 02_legacy_ghost_formula/ — built on a disproven ghost-separation formula

**Defect:** used `Δr = s · v_r / d_gap`, which does **not** vanish at M = 0. This
is disqualifying by pure geometry, not by measurement: a correctly focused lens
must converge light entering at any pinhole position to the same retinal point,
so ghost separation at M = 0 is necessarily exactly zero.

**Replacement:** `Δr = s · M / (P₀ − M)`, which vanishes at M = 0 by construction.

**Evidence:** validated against direct two-hole coherent wave-optics propagation
with peak detection (no formula assumed). Corrected formula **R² = 0.995**;
legacy formula **R² = −1701.7**. A negative R² means the legacy formula performed
*worse than predicting the mean every time* — it is not marginally wrong, it is
non-predictive.

**Files:** `ghosting_sweep_legacy.csv`, `ghosting_sweep_barten_legacy.csv`,
`ghosting_sweep_harmonic_legacy.csv`, `noghost_constraint_legacy.csv`.

**Status:** every ghosting regime classification, harmonic margin result, and
no-ghost pitch constraint in these files is unreliable.

---

## 03_insufficient_alignment_sampling/ — n_offsets = 15

**Defect:** the alignment-offset ensemble was sampled at only 15 offsets, too
coarse to resolve worst-case alignment reliably. Regenerated at **n_offsets = 61**.

**Files:** `ghosting_sweep_corrected_formula_legacy_n15.csv`,
`ghosting_myopia_robustness_corrected_legacy_n15.csv`.

**Status:** these use the *correct* ghost formula (unlike folder 02) but
under-sample alignment. Worst-case margins may be optimistic.

---

## 04_pre_vignetting/ — no gaze-angle correction, or unsourced gaze weighting

**Two distinct defects:**

`array_candidates_prevignetting_legacy.csv` — computed at fixed straight-ahead
gaze only (φ = 0). Later work established that **ghost-safety at φ = 0 does not
imply safety across gaze angle**: across geometry families, 37.8%–88.9% of
φ = 0-safe designs *fail* once gaze rotation is integrated. Any safety claim in
this file covers one eye position, not real use.

`array_candidates_field_averaged_uniform_placeholder_legacy.csv` — used a
placeholder uniform gaze-usage distribution w(φ) over ±15°, explicitly unsourced.
Superseded by a literature-grounded Gaussian (σ ≈ 6°, justified against measured
saccade-amplitude statistics of ~4.4° ± 1.3° during natural scene viewing).

**Status:** superseded, but note the field-averaged robustness conclusion held
under *both* distributions — that finding survives, these specific numbers do not.

---

## 05_superseded_sweep_iterations/ — intermediate development snapshots

**Defect:** ordinary iteration. These are `legacy1`–`legacy6` snapshots taken
during development of the geometry-lab sweep, before the family set, seed
handling, and column schema stabilised. Includes the corresponding
`family_ranking_margin_vs_N` plots, one of which was **entirely blank** — caused
by `max()`-aggregation across spacing values always resolving to `+inf`, since
trivially-safe wide spacings dominate. Fixed by switching to median aggregation.

**Status:** no single identified physics defect; simply superseded by later, more
complete runs. Retained for development history only.

---

## 06_degeneracy_contaminated/ — physically impossible packing densities

**Defect:** 412 of 6615 rows (6.2%, present in 8 of 10 families) reported an
**open-area fraction greater than 1.0** — i.e. the holes covered more area than
the region containing them, which is physically impossible.

**Two independent root causes**, both required fixing:

1. *Unit-cell families* (square, rectangular, hexagonal): severe
   overlap-rejection collapse (e.g. `N_requested = 20 → N_actual = 1`) left no
   repeating tiling for the `N × unit_cell_area` formula to describe, yet the
   formula still returned a number. Critically, this depends only on the
   hole-size-to-spacing ratio and is **independent of N**, so a minimum-hole-count
   filter alone could never have caught it.
2. *Hull/circle families*: bounding area was computed from hole **centers**,
   omitting each boundary hole's own physical radius. Demonstrated with a real
   7-hole non-overlapping case that still reported an open-area fraction of 1.587.
   Fixed with a Minkowski/offset-buffer correction.

**Real-world impact — this was not cosmetic:** the contaminated metric reported
the M = 0 and global-scope winners as `hexagonal, N_actual = 1` — a **single
stray hole**, ranked as the densest design in the entire study.

**Files:** `sweep_results_PRECLEAN_legacy.csv`,
`sweep_results_with_density_PRECONTAMINATED_legacy.csv`,
`metric1_max_density_per_M_PRECONTAMINATED_legacy.csv`,
`metric2_pareto_front_per_M_PRECONTAMINATED_legacy.csv`,
`degenerate_rows_excluded_legacy1–3.csv`.

---

## 07_pre_rotation/ — incomplete parameter space

**Defect:** every deterministic lattice family (square, hexagonal, rectangular)
was swept at a **single fixed orientation**. No rotation parameter existed
anywhere in the sweep. This mattered because the project's own gaze-weighting
work established that natural eye movement is anisotropic (horizontal saccades
dominate), so lattice orientation relative to the dominant gaze axis is a
physically motivated free parameter that was never explored.

**Resolution:** rotation added at 0°/15°/30°/45°, growing the dataset from 6395
to 8933 rows (3240 rotation-tagged). Rotation proved **not** to be a no-op:
across 810 parameter groups with multiple rotations tested, metrics changed in
**76%** of them — most likely via `N_actual`, since different holes survive the
aperture and overlap constraints at different orientations.

**Status:** these files explore an incomplete design space. Any claim of the form
"family X is the best geometry" derived from them is unsafe, because rotated
variants of rival families were never candidates.

---

# ⚠️ KNOWN-INVALID FILES STILL IN PLACE (deliberately not archived)

The following are **currently active** files that a 2026-08-16 audit proved
wrong. They were **left in place on purpose**, because the pending fix pipeline
archives them itself under its own `_legacy` naming step — moving them now would
break that step and destroy the before/after comparison.

**Do not cite these. They are wrong.**

### `array_geometry_lab/comparison_metric/metric1_max_density_per_M.csv`
### `array_geometry_lab/comparison_metric/metric2_pareto_front_per_M.csv`

**Defect A — the density metric is apples-to-oranges.** Lattice families use
`N × unit_cell_area`; hull families use convex-hull area. Controlled test on
*identical* arrangements shows hull-based families receive a systematic
**1.56×–2.25× advantage**, worst at small N — and every winner has N between 9
and 50. Recomputing all 1731 gate-passing designs on one consistent metric
changes the outcome completely: `jittered_lattice` wins drop from **5 of 8 to
0 of 8**, and `square` (pitch 3000 µm, rotation 45°) rises to **7 of 8**.

**Defect B — both safety gates reward blindness.** Gate 1 (ghost) and Gate 2
(vignetting) test only for the *absence* of ghosting. A design where zero holes
are illuminated has zero hole pairs, therefore infinite margin on both gates,
therefore scores as maximally safe. The literal optimum of the current objective
is an opaque lens. Confirmed consequence: the M = 4 and M = 5 winners
(`archimedean_spiral`, N = 50, c = 2000 µm, a_hole = 600 µm) are **blackout
designs** — nearest hole center sits 2311.6 µm from the optical axis with a
300 µm radius, giving an inner edge at 2011.6 µm against a 2000 µm pupil radius:
an 11.6 µm gap, and therefore **exactly 0.0 µm² of transmitted area at straight-
ahead gaze**. The wearer sees nothing.

**Defect C — the active-hole test treats holes as zero-radius points.**
`evaluation/active_pairs.py::active_hole_indices()` marks a hole active only if
its *center* falls inside the pupil. This both under-counts (a hole 90%
overlapping the pupil whose center sits just outside counts as fully inactive)
and over-counts (center just inside, barely overlapping, counts as fully active).
Every `n_active_holes` and `n_active_pairs` value — and therefore every ghost
margin and every gate outcome in the dataset — inherits this approximation.

---

## Archive inventory

| Folder | Files | Failure mode |
|---|---|---|
| 01_gridN2048_artifact | 5 | Grid resolution artifact, blur wrong by up to 100% |
| 02_legacy_ghost_formula | 4 | Disproven formula, R² = −1701.7 |
| 03_insufficient_alignment_sampling | 2 | n_offsets = 15, worst case under-sampled |
| 04_pre_vignetting | 2 | No gaze correction / unsourced w(φ) |
| 05_superseded_sweep_iterations | 14 | Development snapshots, schema unstable |
| 06_degeneracy_contaminated | 7 | Open-area fraction > 1, impossible densities |
| 07_pre_rotation | 3 | Orientation never explored |
| **Total** | **37** | |
