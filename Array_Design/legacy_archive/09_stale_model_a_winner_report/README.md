# 09_stale_model_a_winner_report/ — superseded by pipeline regeneration

**Archived:** 2026-09-17.

**Defect:** `EVALUATION_MODEL_DECISION.pdf` (dated 2026-08-18, three copies found
at project root, `Array_Design/`, and `Array_Design/array_geometry_lab/final
reports/`, all archived here) reports Model A's per-M winner as
`ring_offset_concentric, N=20, r_s=4000um` for M=1 through M=8. This no longer
matches the pipeline's actual output.

**Current live data** (`array_data/evaluation_results/`):
- `metric1_max_density_per_M.csv` — modified 2026-09-12
- `FINAL_WINNER_PER_M.csv` — modified 2026-09-12 (agrees with metric1)
- `PRIMARY_WINNER_PER_M.csv` (Model B, gaze-weighted) — modified 2026-09-13

Both post-date this report by roughly a month and show a different family
winning at every M: **square** (Model A/metric1) and **hexagonal at
pitch=4000um** (Model B/PRIMARY) — `ring_offset_concentric` does not appear as
a winner anywhere in the current output.

**Likely mechanism (consistent with, not confirmed identical to, folder
06's Defect A):** in the current data, every Model A winner has
`n_active_holes_phi0 = 1` and a very small `N_actual`/hull area, i.e. the
ranking metric (`N_actual / hull_area`) is maximized by the smallest, tightest
cluster of points rather than by genuine packing efficiency — square lattices
achieve a small hull more easily than ring-based families, which must spread
points across expanding radii by construction. This matches the "apples to
oranges" density defect folder 06 already documented and predicted would push
square to a 7-of-8 win once fixed. This report's `ring_offset_concentric`
result may be an intermediate pipeline state between the 06 fix and the
current one — **not independently re-traced**, flagged here as a plausible
explanation only, not a confirmed root cause.

**Status:** do not cite this report's winner table. Read the current CSVs in
`array_data/evaluation_results/` directly, or the (also potentially stale —
not checked as part of this archiving pass) `ALL_MODELS_WINNER_COMPARISON.pdf`
if working with the seven-model comparison specifically.
