# Coverage Analysis Report

## Correction (2026-08-17): M=1.0 winner display artifact, and a real seed-robustness caveat

A report that `effective_density_winner_per_M_cmin55.csv`'s M=1.0 winner
(`poisson_disk`, seed=7) showed `packing_density_per_area_um-2=0.0` /
`effective_density_per_area_um-2=0.0` **on its own recorded row** was
investigated. Traced precisely: **no join or merge exists anywhere in
`effective_density_ranking.py`** (it reads one CSV, does pure arithmetic on
existing columns). The `0.0` was a **pandas display artifact**: extracting a
single row from a mixed-dtype DataFrame as a Series (via `.T` or `.loc[idx]`
then `print()`) forces pandas to coerce that row to a common `object` dtype
for display, which can render a very small float (~1e-8) as `"0.0"` in the
same row as much larger values (e.g. `total_illuminated_area_um2_phi0≈4.1e6`)
— reproduced with a minimal 2-row example. **Direct scalar access
(`row['effective_density_per_area_um-2']`) and the actual written CSV always
held the correct value, `4.5601e-08`.** A defensive assertion (no row with
`n_active_holes_phi0>=1` may have `effective_density==0.0`) was added to
`add_effective_density()` regardless, and both runs (`c_min_um=0` and `55`)
pass it cleanly.

**`jittered_lattice` was checked and refuted as the M=1.0 winner**, not
assumed: its top raw-effective_density candidate (6.157e-7, ~13x higher) fails
the viability gate outright — `min_illuminated_area_um2_across_phi=0.0` (goes
fully dark at some tested gaze angle) — a real, correct exclusion, not a bug.
`poisson_disk` (seed=7, effective_density=4.560e-8) is confirmed the genuine
maximum among actual gate survivors.

**However — the seed-robustness check this project's own `rank_by_family.py`
already established (worst-case-across-seeds + `std > 1.0×|worst|` ⇒
`high_seed_variance`) flags this winner as fragile.** Checked across all 8
seeds of the identical (N=20, spacing_factor=1.2, M=1.0) design:
`ghost_margin_c_min_floored` ranges from **-0.138** (seed 0, a real failure)
to **+0.522** (seed 1); worst-case = -0.138, std = 0.220 →
**`high_seed_variance=True`**. Only 2 of 8 seeds (4 and 7) pass *both*
floored-margin checks simultaneously — seed 7 was not a representative
outcome, it was the lucky draw. `effective_density_ranking.py` ranks
individual seed realizations as independent rows (unlike
`rank_by_family.py`, which aggregates stochastic families by worst-case
seed) — a structural limitation of this ranking script worth stating
plainly: **for stochastic families, its winner is a best-seed pick, not a
seed-robust design.**

---

Built on the CONFIRMED FINDING that every prior margin-aware winner has exactly
one active hole at phi=0 (n_active_holes_phi0=1, n_active_pairs_phi0=0):
non-overlap requires spacing >= hole diameter, while simultaneous two-hole
"fusion" requires spacing well under that — the two constraints cannot both
hold in this dataset's tested regime. The array's real function is coverage
(some hole is always available as gaze/pupil position wanders), not
simultaneous multi-hole light-gathering.

New files only — nothing existing was edited:
- `array_calculation/compute_coverage_metrics.py` — blind_rate (sampled) +
  optical/c_min-floored ghost & vignetting margins.
- `array_evaluation/comparison_metric/effective_density_ranking.py` —
  effective_density ranking + margin-aware gating on the c_min-floored margins.

## Part 1 — blind_rate: does it reproduce Shen's closed-form floors?

**No.** Sampled directly (891 pupil positions per row: 11 gaze angles ×
9×9 wander grid within one lattice period), not assumed:

| test | phi=0 only | full ±25° gaze range | Shen's closed-form floor |
|---|---|---|---|
| single hole at origin | **0.000000** ✓ | 0.700337 (see note) | 0.0 |
| square, s≈d (near-touching) | **0.000000** | 0.000000 | 0.214602 (1−π/4) |
| hexagonal, s≈d (near-touching) | **0.000000** | 0.000000 | 0.093100 (1−π/(2√3)) |

The single-hole/phi=0 sanity check passes exactly, and a positive control
(sparse lattice, pitch=10,000µm ≫ pupil) correctly returns a high blind_rate
(0.893) at the same sampling resolution — confirming the sampler itself is
working, not silently always returning 0.

**Why square/hex don't reproduce the floor**: Shen's 1−π/4 and 1−π/(2√3) are
derived for a *point* aperture. This project's real pupil is 4000µm across —
roughly 5× the tested near-touching pitch (750µm) — so it straddles several
holes simultaneously from any position and essentially never goes fully dark.
The mismatch is the finite pupil size, not a sampling defect.

**Note on the single-hole full-gaze-range case (0.70, not 0)**: this is not a
failure — a lone hole cannot stay illuminated once gaze-induced pupil shift
moves the pupil ~5.7mm off-axis (`R_rot_mm=13.5`, `phi=±25°`). It independently
re-derives this task's own premise: coverage across the tested gaze range
needs *multiple* holes.

## Part 2 — c_min_um perceptual fusion floor

`--c_min_um` (default 0.0, current behaviour unchanged): resolvable threshold
becomes `max(c_resolvable_optical, c_min_um)`. Both optical-only and
c_min-floored ghost/vignetting margins are emitted as separate columns.
Verified: at `c_min_um=0`, 0/8501 rows differ from optical-only, exactly as
required. At `c_min_um=55`, 4809/8501 rows change value.

## Part 3 — effective_density replaces packing_density as ranking objective

`effective_density = n_active_holes_phi0 / hull_area` (hull_area recovered
algebraically from existing columns: `N_actual / packing_density_per_area_um-2`
— no new geometry computed). `packing_density_per_area_um-2` is kept in every
output file, unmodified, for direct comparison.

**Every current winner looks far worse under the honest metric** — reported
as instructed, not softened: mean `effective_density / packing_density` across
all 8501 candidates = **0.175**. The old density metric was, on average,
crediting designs with roughly **5.7× more "density" than they actually
deliver in light**, because it counted holes that structurally never admit
light. This is the correct outcome, not a defect in either metric — it is
exactly what "packing density counts geometry, effective density counts
function" should produce once most holes in a design are dark.

## Part 4/5 — winner per M, both runs

**(a) c_min_um=0 (strict optical criterion)** — 718/8501 survivors, all with
**exactly 1** active hole:

| M | family | N | spacing | n_active_holes | blind_rate | effective_density |
|---|---|---|---|---|---|---|
| 0.0 | hexagonal | 7 | pitch=2000, rot=30° | 1 | 0.173 | 1.81e-8 |
| 1.0 | ring_offset_concentric | 20 | ring_spacing=4000, holes/ring0=8 | 1 | 0.113 | 5.49e-9 |
| 2.0 | ring_offset_concentric | 20 | same | 1 | 0.107 | 5.89e-9 |
| 3.0 | ring_offset_concentric | 20 | same | 1 | 0.107 | 5.89e-9 |
| 4.0 | ring_offset_concentric | 20 | same | 1 | 0.105 | 6.02e-9 |
| 5.0 | ring_offset_concentric | 20 | same | 1 | 0.105 | 6.02e-9 |
| 6.0 | ring_offset_concentric | 20 | same | 1 | 0.103 | 6.11e-9 |
| 8.0 | ring_offset_concentric | 20 | same | 1 | 0.101 | 6.20e-9 |
| global | hexagonal | 7 | pitch=2000, rot=30° | 1 | 0.173 | 1.81e-8 |

**(b) c_min_um=55 (Shen's clinically-calibrated perceptual floor)** —
1188/8501 survivors (+470 vs. run (a)):

| M | family | N | spacing | n_active_holes | blind_rate | effective_density |
|---|---|---|---|---|---|---|
| **0.0** | **ring_offset_concentric** | 11 | ring_spacing=1000, holes/ring0=6 | **2** | 0.156 | 3.60e-8 |
| **1.0** | **poisson_disk** | 20 | spacing_factor=1.2 (seed 7) | **3** | 0.111 | 4.56e-8 |
| 2.0 | ring_offset_concentric | 20 | ring_spacing=4000, holes/ring0=8 | 1 | 0.107 | 5.89e-9 |
| 3.0 | ring_offset_concentric | 20 | same | 1 | 0.107 | 5.89e-9 |
| 4.0 | ring_offset_concentric | 20 | same | 1 | 0.105 | 6.02e-9 |
| 5.0 | ring_offset_concentric | 20 | same | 1 | 0.105 | 6.02e-9 |
| 6.0 | ring_offset_concentric | 20 | same | 1 | 0.103 | 6.11e-9 |
| 8.0 | ring_offset_concentric | 20 | same | 1 | 0.101 | 6.20e-9 |
| global | hexagonal | 7 | pitch=2000, rot=30° | 1 | 0.173 | 1.81e-8 |

### Does run (b) produce multi-active-hole winners where run (a) produced none?

**Yes — at M=0.0 and M=1.0.** Verified directly, not just by the changed row
count:

- **M=0.0**: winner has margin=+1.0 unchanged in both runs. What changed is
  the *required threshold* — it drops from 1.599 (optical, using the tiny
  3.66µm resolvable scale at M=0) to 0.107 once that same scale is floored to
  55µm. The design was always safe; it only clears the bar once the bar
  itself is computed against the floored scale.
- **M=1.0** (the cleaner case): the poisson_disk winner's real, computed
  margins **flip sign** — ghost margin goes from **-5.40** (optical, fails
  decisively) to **+0.26** (floored, passes); vignetting margin goes from
  **-6.72** to **+0.11**. This is a genuine safety-verdict reversal on 3
  simultaneously active holes, not a threshold artifact.

At every other M (2–8, global), both runs pick the identical single-active-hole
winner — Shen's floor changes nothing there, because those margins are already
`+inf` (structurally zero active pairs, unaffected by any threshold).

## Known scope boundaries

- `effective_density_ranking.py` gates against `ghost_margin_c_min_floored` /
  `vignetting_margin_c_min_floored`, which required computing the required
  threshold against the *same* floored resolvable scale as the margin itself
  — reusing `gates.py`'s sourced constants (`MARGIN_SAFETY_MULTIPLE`,
  `GHOST_DELTA_R_UNCERTAINTY_UM`), not its `gate_*`/`ghost_margin_threshold`
  functions directly (those read the optical-only column). `gates.py` itself
  is untouched.
- `FINAL_WINNER_PER_M.csv` (prior task, square/hexagonal/rectangular only,
  optical-only margins) was not regenerated — it remains a separate, valid
  answer to a differently-scoped question.
- `n_active_holes_phi0` (used for effective_density) is the existing phi=0
  snapshot column, not a new phi/wander-integrated active-hole count — kept
  this way for direct traceability to the CONFIRMED FINDING's own terminology.
