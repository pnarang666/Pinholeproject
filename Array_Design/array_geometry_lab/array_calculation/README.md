# array_calculation/

**Layer 1: physics and geometry only.** Generates hole layouts and computes the raw,
continuous quantities that describe them (ghost separation, vignetting/illumination
overlap, packing density). This layer never applies a threshold, never decides
pass/fail, and never ranks anything — that is `../array_evaluation/`'s job.

## What lives here

```
generators/       10 layout families (square, hexagonal, concentric, spirals, ...)
                   + base_generator.py (shared overlap-rejection/recentering logic).
engine/            Copied (not imported) physics primitives: ghost_formula.py,
                   vignetting_overlap.py. Self-contained, zero dependency on
                   array_optimization/'s internals. Validated by validate_copies.py.
margins/           (formerly this folder's top-level "evaluation/") active_pairs.py
                   (pupil-footprint overlap/illumination geometry), ghost_margin.py,
                   vignetting_robustness.py. Renamed out of the way of the new
                   top-level array_evaluation/ so the two "evaluation" senses (raw
                   margin geometry vs. judged pass/fail ranking) can't be confused.
degeneracy_filter.py   Single source of truth for (a) excluding physically-degenerate
                   point sets and (b) the one family-agnostic packing_density formula
                   (buffered convex hull) used for every family.
compute_density.py Adds packing_density to every row of sweep_results.csv -- a raw
                   geometric quantity, no threshold involved -- writing
                   sweep_results_with_density.csv.
clean_sweep_results.py   Applies degeneracy_filter.py to the root sweep_results.csv.
sweep/             run_sweep.py (the full parameter sweep), run_rotation_sweep.py.
validate_copies.py, spot_check_generators.py, test_part3_small_case.py
                   Verification gates for this layer -- run before trusting any
                   downstream number.
```

## What this layer may do
- Generate hole coordinates for any family/parameter combination.
- Compute continuous physical quantities: ghost separation (`delta_r`), illumination/
  overlap area and fraction, packing density.
- Read/write CSVs under `../array_data/theoretical_data/`.

## What this layer may NOT do
- No booleans, no pass/fail, no gates, no thresholds baked into a *default* output
  column, no ranking. (`active_frac_threshold` is the one existing exception, used
  internally to decide which hole pairs get enumerated for the ghost-margin
  calculation itself -- it is a modeling input to a physics calculation, not a
  judgment about whether a candidate is "good"; see `margins/active_pairs.py`'s own
  docstring.)
- Never import anything from `../array_evaluation/` (gates, metrics, ranking). This
  layer must run standalone.

## Running it

```bash
cd array_calculation
python3 validate_copies.py            # Part 1 gate
python3 spot_check_generators.py       # Part 2 gate
python3 test_part3_small_case.py       # Part 3 gate
python3 sweep/run_sweep.py             # full sweep -> ../array_data/theoretical_data/sweep_results.csv
python3 sweep/run_rotation_sweep.py    # adds rotation_deg for square/hexagonal/rectangular
python3 compute_density.py             # adds packing_density -> sweep_results_with_density.csv
```

Every output CSV is legacy-preserved (`_legacyN`) before being overwritten, per this
project's existing convention.
