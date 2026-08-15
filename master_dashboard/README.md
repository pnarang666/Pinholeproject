# Master Dashboard

A single interactive dashboard that runs **live sweeps** across every stage of this
project, rather than only viewing precomputed CSVs (unlike
`master_compilation/dashboard.py`, `R7acuity/dashboard.py`,
`singleilluminate/streamlit_app.py`, and `stage_v1_simulator/`, each of which either
views precomputed results or covers one stage).

## Running it

```bash
python3 -m streamlit run master_dashboard/app.py
```

(`streamlit run master_dashboard/app.py` also works if `streamlit`'s own console
script is on your `PATH`; `python3 -m streamlit` is more portable across
environments.)

## Architecture: a registry, not a tab per stage

`registry.py` holds one dict, `REGISTRY`, mapping a stage key to its real entry
point, parameter widgets, and output shape. `app.py` contains **no stage-specific
code at all** — it reads the sidebar widgets, the runtime estimate, the plot type,
and the CSV export purely from whichever `REGISTRY` entry is selected. `wrappers.py`
holds one thin function per stage that *calls* that stage's own existing compute
function(s) — none of them reimplement physics, a model, or a metric.

```
master_dashboard/
  registry.py             the REGISTRY dict + point-count/runtime estimator
  wrappers.py              one thin wrapper function per stage, calling real code
  app.py                   generic Streamlit UI -- reads registry.py, nothing stage-specific
  _verify_all_stages.py    exercises every stage's sweep_fn + plot dispatch with a
                            minimal parameter set -- run this after any change
  README.md                this file
```

## Adding a new stage

1. Write one function in `wrappers.py`: `sweep_my_stage(params: dict, progress_cb) ->
   pd.DataFrame`. It should call your stage's own real compute function(s) in a loop
   over whatever `params` selects — never reimplement the physics itself. If your
   stage needs `stage2_fixed/`'s optics, insert `stage2_fixed` (never `stage2/`) into
   `sys.path` **inside** this function (see any existing optics-touching wrapper for
   the pattern) — imports are scoped per-function specifically so one stage's import
   order can never affect another's in the same running dashboard.
2. Add one entry to `REGISTRY` in `registry.py`: `label`, `modules`, `uses_optics`,
   `sweep_fn` (your new function), `params` (widget specs — reuse `_APERTURE_PARAM`,
   `_M_PARAM`, etc. where they fit), `plot_type` (one of `line_vs_aperture`,
   `heatmap`, `regime_map`, `table_only`), `y_metrics`, `cost_per_point_s` (profile
   once — run your sweep on a couple of points and divide), and `notes` (anything a
   reader needs to know, especially anything you had to route around).
3. Run `python3 master_dashboard/_verify_all_stages.py` — it exercises every
   registered stage's `sweep_fn` and plot dispatch with a minimal parameter set and
   reports pass/fail per stage. Add your new stage's minimal test params to that
   script's `MINIMAL_OVERRIDES` dict.
4. `app.py` needs no changes. That's the whole addition.

## The rule: `stage2_fixed/`, never `stage2/` -- with exactly one deliberate,
## isolated exception

This project fixed a real bug (see `PHYSICS_AUDIT.md` and both `RESULTS.md` files'
"corrected optics" sections) where importing things in the wrong order silently
resurrected a deprecated, still-buggy copy of the optics pipeline
(`stage2/phase2_retina.py`) instead of the corrected one (`stage2_fixed/
phase2_retina.py`) — via Python's own module-name caching in `sys.modules`. Every
stage registered here was individually grepped for `stage2` imports before being
wired in:

- **Direct and safe**: `stage2_fixed`, `stage1_v2`, `stage3_human_vision` (its own
  `metrics.py` was the file this project's fix repointed), `stage3_integrated`,
  `stage4_human_vision` (`pipeline.py` was the file this project's fix repointed),
  `Array_Design/ghosting`, `Array_Design/photometry`, `R7acuity` (its `ideal_observer.py`
  correctly targets `stage2_fixed/`, and must be imported as a proper package —
  `import R7acuity.ideal_observer`, not a bare `sys.path` insert — since its own
  internal modules use relative imports).
- **Deliberately NOT called**: `model_comparison/stage2_runner.py` imports the
  deprecated `stage2/` directly (verified by grep, `_STAGE2_DIR = ... "stage2"`).
  The Model Comparison tab instead reuses this dashboard's own `stage2_blur`
  wrapper (`stage2_fixed/`) for the "exact" leg, and only
  `model_comparison/approximation_runner.py`'s pure-algebra RSS formula (no optics
  dependency at all) for the "approximate" leg.
- **No optics dependency, not applicable**: `stage3a` (its own
  `combine_and_select.py` script defaults to reading a *stale* precomputed CSV —
  also routed around, see below), `brightness_reconciliation`, `singleilluminate`.
- **The one deliberate exception**: the `stage2_deprecated` tab ("⚠️ [DEPRECATED]
  Stage 2") runs the broken `stage2/` pipeline ON PURPOSE, for side-by-side
  reference/comparison against the corrected Stage 2 tab (see "Overlay" below). It
  is the only place in this file that ever loads `stage2/`. Because `stage2/` and
  `stage2_fixed/` both define `phase2_retina.py`, `myopia_axial.py`, and
  `pipeline_junction.py` under the same bare names, a plain `sys.path` insert would
  risk *permanently* shadowing the corrected copy that every other tab depends on
  for the rest of the running process. `wrappers._isolated_stage2_deprecated_import()`
  instead swaps those three names in and out of `sys.modules` for the duration of
  one sweep call only, and asserts (fatal, not silent) that the corrected pipeline
  is back in place before returning — see that function's own docstring for the
  full mechanism. `_verify_all_stages.py` exercises this stage in the middle of the
  full 12-stage sequence specifically to catch any leakage into neighboring stages.

Every optics-touching tab displays, live, which `phase2_retina.py` is actually
loaded (`wrappers.verify_phase2_retina_source()`, checking `sys.modules` directly —
not assumed from which directory was inserted). The persistent "Project Physics
Status" panel at the top of every page re-runs this same check on every page load
and computes the corrected-vs-superseded blur-only optimum range **live from the
actual output CSVs on disk** (`new_sweeps/blur_sweep.csv` vs.
`stage2_fixed/outputs/prefix_baseline_audit/multi_EE_sweep.csv`) — never a
hardcoded string, so it cannot silently go stale the way `PROJECT_STATUS.md`'s own
prose has.

## Other things routed around, not silently hidden

- **`stage3a/combine_and_select.py`** defaults to reading `../stage2/outputs/
  r1_full_range_sweep.csv` — a stale CSV computed against the deprecated optics.
  Not used. The Stage 3a tab computes fresh blur data via this dashboard's own
  `stage2_blur` wrapper instead, then applies `stage3a.transmission
  .relative_illuminance()` (reused verbatim) under a live `T_min` slider.
- **`R7acuity/corrections/` and `R7acuity/core/`** (the registered-strategy plugin
  system, e.g. `raw` vs. `efficiency`-corrected) are **empty** on this branch —
  confirmed by listing the directories, not assumed. That system exists only as
  separate, uncommitted work on a different, unmerged line of development. The
  R7acuity tab uses the flat-layout functions that *do* exist
  (`R7acuity/ideal_observer.py`, `R7acuity/threshold.py`).
- **R7acuity's ideal-observer Monte Carlo calibration currently crashes** against
  the corrected optics (`calibrate_noise_sigma()` raises `AssertionError` — see
  `R7acuity/RESULTS.md`'s corrected-optics section for the full characterization).
  The R7acuity tab attempts this fresh every time it's opened and displays the
  crash plainly if it happens — never hidden, never silently falling back to a
  stale cached number. What the tab's sweep/plot *does* show is the closed-form
  Strehl/VSOTF cross-check (`closed_form_approximations()`, which needs no
  calibration), clearly labeled as that and never presented as R7's real
  ideal-observer answer.

## Custom graphs: free axis picker, chart-style variety, overlay comparison

For `line_vs_aperture` and `heatmap` stages, the plot's X-axis, Y-axis (and, for
`line_vs_aperture`, color-by) are free dropdowns populated from whichever columns
the sweep actually returned — not limited to the registry's own `y_metrics` list.
`regime_map` stays fixed-shape (aperture vs. pitch, colored by regime) since it's a
domain-specific plot, not a generic metric pair.

Any `line_vs_aperture` stage with a real color_by dimension (e.g. myopia M) gets a
"Chart style" picker with three views of the same data:
- **Line chart** — the original view, one line per color_by value.
- **Heatmap** — the same (x_col, color_by) grid as a `pivot_table` heatmap, reusing
  `plot_heatmap()` (previously only wired to `stage3_integrated`).
- **Optimal `x_col` vs `color_by`** — `compute_optimum_table()` finds, for each
  color_by value (e.g. each M), the x_col that minimizes y_col: "which aperture
  minimizes this blur metric, per myopia level." Never silently reports an
  arbitrary tie: if multiple x_col values achieve the exact same minimum (this
  project's own recurring failure mode — r_EE(50%), and even r_EE(70%)/r_EE(80%),
  pin to the same grid/histogram-bin-width floor for well-focused, large-aperture
  conditions, confirmed at M=0/1 in Stage 2's own data), that row is flagged
  `saturated=True` with the full `tied_range`, and drawn as a hollow triangle
  instead of a filled circle on the chart — a shape encoding, orthogonal to the
  color/linestyle already used for primary-vs-overlay identity below.

Any two cached sweeps from the same session that share both the chosen X and Y
columns — any stage, any parameters, e.g. the deprecated Stage 2 tab vs. the
corrected one, or the same stage at two different myopia ranges — can be overlaid
on one chart via the "Overlay another cached sweep" picker beneath the axis
selectors (available for Line chart and Optimal-vs-M; not for Heatmap, which
doesn't compose two grids onto one image). Color still encodes `color_by`'s
magnitude (identical hue = identical value in either series); linestyle (solid vs.
dashed) encodes which series is which, so the two encodings never conflict.
Session-cached sweeps carry a human-readable label (`_param_summary()` in
`app.py`) for this picker; the cache itself is still keyed by the exact `(stage,
parameter tuple)`, unchanged.

## Constraints this dashboard follows (do not relax)

- Every wrapper calls real, existing stage code — no physics, model, or metric is
  reimplemented anywhere in `master_dashboard/`.
- No existing stage folder's own code was modified to build this dashboard.
- Every optics-touching tab verifies and displays which `phase2_retina.py` is
  loaded, live, every time.
- No tab retunes, recalibrates, or resets any locked/pre-registered model constant
  (R7acuity's sigma, any efficiency correction, Barten CSF constants, ...) — the
  parameter widgets are for *input conditions* (aperture, M, wavelength, gap,
  luminance, pitch, $T_{min}$), never a model's own internal calibrated constants.
- No "recommended aperture" output anywhere, on any tab.
- Runtime is estimated (`points × cost_per_point_s`) and shown *before* running;
  any sweep estimated over ~30s requires an explicit confirmation checkbox before
  the "Run Sweep" button becomes clickable — a wide accidental range never
  silently hangs the app.
- Results are cached within the session by the exact `(stage, parameter tuple)` —
  re-viewing an already-run range is instant, never recomputed.

## Known scope limits (stated, not hidden)

- Several stages' underlying functions (`run_pipeline_point`, `run_sweep`,
  `run_stage4_point`, `classify_ghosting_regime`, ...) accept exactly ONE
  wavelength / gap / natural-pupil-diameter per call — those parameters are
  single-choice (`select`) widgets in this dashboard, not sweepable ranges, because
  making them sweepable would mean silently only ever using the first selected
  value (a real bug caught by `_verify_all_stages.py` during this dashboard's own
  build — see registry.py's `_WAVELENGTH_PARAM` comment). Only Stage 1
  (`sweep_stage1`, which genuinely loops over all three) and `singleilluminate`
  (whose own `run_single_hole_sweep` genuinely accepts a list of pupil diameters)
  expose these as true multiselect sweep dimensions.
- `stage3_integrated`'s merge is a left-join on `(a_hole_um, M_diopters)` between
  this dashboard's own `stage3a_brightness` and `stage3_human_vision` wrapper
  outputs — correct as long as both legs are run at the same wavelength/gap/pupil
  (the UI does not currently prevent selecting different values per leg, since they
  share one parameter panel).
- `_verify_all_stages.py` exercises every stage's real `sweep_fn` and plot-dispatch
  function directly, with a minimal parameter set — confirmed 12/12 passing,
  including live `stage2_fixed` resolution for every optics-touching stage
  (`stage2_deprecated` included, immediately after its own sweep restores it). The
  app has also been exercised end-to-end through the actual running UI via the
  Chrome browser extension (widget interactions, the runtime confirm-gate flow, the
  deprecated-optics badge, the axis picker, and the overlay comparison) — not just
  this isolated script.
