# Final Answer Report

Scope: square, hexagonal, rectangular families only (this project's three
regular-lattice families with a well-defined closed-form packing geometry).
Every other family's theoretical data and prior evaluation outputs remain
untouched in `array_data/` for reference — they are simply not candidates for
this final ranking, per the task's own restriction.

Produced by `array_evaluation/comparison_metric/final_winner.py`, using
`array_evaluation/comparison_metric/gates.py`'s updated margin-aware gates and
this project's existing, unmodified `metrics.metric1_max_density()` ranking
(single densest gate-survivor per M). Full numeric detail: `array_data/
evaluation_results/FINAL_WINNER_PER_M.csv`.

## Why the thresholds are what they are (not >0)

Every prior "winner" that turned out to be a boundary case — blackout designs,
a hexagonal candidate at margin=-16.6 sitting right next to designs that passed
— shared one root cause: gates required `margin > 0`, not `margin > a real
threshold`. Fixed as follows, in `gates.py`:

- **Ghost/vignetting margin threshold** = `2.0 × (2 × 1.46484375um) / resolvable_blur_um`,
  computed per row. `1.46484375um` is the grid pixel size from this project's own
  `array_optimization/stage0_ghost_validation/validate_ghost_formula.py` M=0
  validation run (`grid_N=4096`, `window_L_mm=6.0`) — the same physical-optics
  simulation `ghost_formula.py` was validated against. That file's own comment
  states the resulting two-peak-separation measurement tolerance is `±2 pixels`
  ("a peak-detection method resolves position to about ±1 pixel per peak, so ±2
  pixels for a two-peak separation is the natural, grid-justified tolerance; not
  an arbitrarily chosen round number") — this is the known measurement
  uncertainty in `delta_r_actual`, the quantity both margins are built from. The
  task's own requested `2×` safety multiple is applied on top of that, so a
  margin must clear its own known positional noise floor by a further factor of
  2 before counting as a real pass.
- **Viability threshold** = `0.20 × pi × (a_hole_um/2)²` at every tested phi
  (checked via `min_illuminated_area_um2_across_phi`, already the worst case
  across the whole tested phi — and, for global-scope rows, M — range) — as
  given in the task brief.

Both thresholds vary row to row (`resolvable_blur_um` and `a_hole_um` both
depend on M and the candidate), so they are computed per row, not as one fixed
number — see `FINAL_WINNER_PER_M.csv`'s own `*_threshold` columns.

## Winner per M

| M | family | N | spacing | ghost/vignetting margin | viability (illuminated area) |
|---|---|---|---|---|---|
| 0.0 | square | 9 (of 20 requested) | `pitch_um=2000.0, rotation_deg=0.0` | actual=**+inf**, required≥1.599 | 1.987e6 vs 6.283e5 um² required (**3.16×**) |
| 1.0 | square | 100 | `pitch_um=3000.0, rotation_deg=45.0` | actual=**+inf**, required≥0.928 | 1.227e6 vs 2.454e5 um² required (**5.00×**) |
| 2.0 | square | 100 | `pitch_um=3000.0, rotation_deg=45.0` | actual=**+inf**, required≥0.726 | 4.418e5 vs 8.836e4 um² required (**5.00×**) |
| 3.0 | square | 100 | `pitch_um=3000.0, rotation_deg=45.0` | actual=**+inf**, required≥0.517 | 4.418e5 vs 8.836e4 um² required (**5.00×**) |
| 4.0 | square | 50 | `pitch_um=3000.0, rotation_deg=45.0` | actual=**+inf**, required≥0.483 | 2.821e5 vs 5.655e4 um² required (**4.99×**) |
| 5.0 | square | 50 | `pitch_um=3000.0, rotation_deg=45.0` | actual=**+inf**, required≥0.359 | 2.821e5 vs 5.655e4 um² required (**4.99×**) |
| 6.0 | square | 50 | `pitch_um=3000.0, rotation_deg=45.0` | actual=**+inf**, required≥0.375 | 1.721e5 vs 3.927e4 um² required (**4.38×**) |
| 8.0 | square | 50 | `pitch_um=3000.0, rotation_deg=45.0` | actual=**+inf**, required≥0.336 | 9.539e4 vs 2.513e4 um² required (**3.80×**) |
| global | square | 9 (of 20 requested) | `pitch_um=2000.0, rotation_deg=0.0` | actual=**+inf**, required≥1.599 | 1.987e6 vs 6.283e5 um² required (**3.16×**) |

**On the `+inf` ghost/vignetting margins**: this is not the old defect returning.
`+inf` here means zero active (close enough to ghost) hole pairs exist for this
candidate — a structural fact about the geometry, not a data artifact — and it
only counts as safe because the viability check (illuminated area, a completely
independent gate) is *also* satisfied with 3.2×–5.0× headroom, confirmed above.
An `+inf`-margin design with near-zero illuminated area (the old "opaque lens"
failure mode) would still fail this gate exactly as it did before.

## One sentence per M confirming this is not a boundary case

- **M=0.0**: Zero active ghost pairs at this spacing (structurally, not
  numerically, safe) and illuminated area is 3.16× the required floor — not a
  near-miss on either check.
- **M=1.0**: Zero active ghost pairs and illuminated area is 5.00× the required
  floor, the largest margin of any M slot — solidly clear.
- **M=2.0**: Zero active ghost pairs and illuminated area is 5.00× the required
  floor — solidly clear.
- **M=3.0**: Zero active ghost pairs and illuminated area is 5.00× the required
  floor — solidly clear.
- **M=4.0**: Zero active ghost pairs and illuminated area is 4.99× the required
  floor — solidly clear.
- **M=5.0**: Zero active ghost pairs and illuminated area is 4.99× the required
  floor — solidly clear.
- **M=6.0**: Zero active ghost pairs and illuminated area is 4.38× the required
  floor — solidly clear.
- **M=8.0**: Zero active ghost pairs and illuminated area is 3.80× the required
  floor, the smallest headroom of any M slot but still well clear of 1×.
- **global**: Same candidate as M=0.0 (its own generation aperture is M=0's, the
  largest in the tested range) — same 3.16× illuminated-area headroom applies.

## Known scope boundary (not fixed here, by design)

`structurally_safe` (a column baked into `array_data/theoretical_data/` at
`array_calculation/sweep/run_sweep.py` time) and `compare/rank_by_family.py`'s
own ranking still use the old `margin > 0` definition — that column is computed
in `array_calculation/`, and this task's instruction was scoped to
"array_evaluation gates" only. `FINAL_WINNER_PER_M.csv` and this report are the
authoritative margin-aware answer; `family_ranking.csv` was not regenerated and
should not be read as reflecting these new thresholds.
