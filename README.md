# Pinhole Sunglasses -- IYPT optical simulation project

Research-grade Fourier-optics simulation for the pinhole-sunglasses IYPT problem:
plane wave -> circular pinhole -> free-space propagation -> corneal plane.

## Where things are

- **`stage1_v2/`** -- current, recommended tool. A Streamlit instrument ("Corneal
  Fresnel Field Analyzer") that characterizes the field at the cornea: intensity/phase
  maps, radial profile, encircled energy, and six selectable effective-radius
  definitions (never a single hardcoded "best pinhole" answer). Includes an accuracy fix
  for a real FWHM measurement bug found in `stage1/` -- see `stage1_v2/README.md` for
  the full diagnosis and fix. **Use this one unless you specifically need to reproduce
  `stage1/`'s exact prior numbers.**
- **`stage1/`** -- the original build of the same tool, kept intact and unmodified for
  reference/reproducibility. Has a known issue: FWHM / 1/e² / custom-threshold radii can
  jump tens of microns between adjacent aperture diameters that differ by 1 µm, a
  numerical artifact of Fresnel-ring competition in the old crossing-detection method
  (fixed in `stage1_v2/`).
- **`stage2/`** -- extends `stage1_v2/` past the cornea: pupil clipping, a fixed-power
  eye lens, and a second ASM propagation to the retina, at a distance set by an
  axial-length myopia model (eye power held fixed at the emmetropic value; only axial
  length grows with myopia `M`). Validated against the closed-form Airy encircled-energy
  formula before any sweep runs. See `stage2/README.md`.
- **`stage2_fixed/`** -- byte-identical copy of `stage2/` with two bug fixes (an
  energy-conservation comparison bug, a wraparound-check margin documented as a
  first-pass safety inflation rather than a validated bound). See `stage2_fixed/CHANGES.md`.
  `stage3a/`, `stage3_human_vision/`, and later stages import from here, not `stage2/`.
- **`stage3_human_vision/`** -- human-vision-constrained optimization on top of
  `stage2_fixed/`: new optical metrics (RMS radius, FWHM, Strehl, OTF/PTF, MTF50/10), a
  photometric chain (scene luminance -> retinal illuminance -> photon flux), contrast-
  sensitivity/acuity models (including LogMAR and OTF-based Visual Strehl/VSOTF), and
  multi-objective Pareto analysis. Investigates why Stage 2's pure-blur optimum
  (300-450um) differs from published/commercial pinhole designs (800-1200um); finds
  that RMS spot radius (not r_EE or MTF50) is the metric whose optimum actually tracks
  real-world designs closely, and that Strehl ratio is ill-posed for this system
  (confirmed via direct test: peak retinal intensity oscillates with propagation
  distance rather than having one well-defined focus). Also validates predicted LogMAR
  against a published multi-point clinical dataset (RMSE/MAE/R^2/Pearson r, swept
  across several myopia levels rather than a single forced fit) -- see
  `stage3_human_vision/README.md`.
- **`stage3a/`** -- a quick, cheap hypothesis test: does a brightness/illuminance floor
  alone explain the gap between blur-only optimization and real-world designs? Finds
  yes -- a ~6-9% relative-illuminance floor alone moves the optimum into the clinical
  bracket (940-1750um), uniformly across all tested myopia levels. See `stage3a/README.md`.
- **`stage3_integrated/`** -- combines `stage3a` + `stage3_human_vision` on one shared
  grid; extends the brightness-floor finding to 10 metrics (8 converge to ~1000um), and
  confirms two prior findings directly rather than assuming them: Strehl's
  non-monotonicity is genuine ring interference (a 10x finer grid reveals *more*
  oscillation, not less), and the cornea-plane FWHM ring-hopping instability also
  appears (worse) at the retina plane. See `stage3_integrated/README.md`.
- **`stage_v1_simulator/`** -- the interactive Streamlit dashboard tying everything
  together: live single-point exploration (full metric set: EE at 4 percentiles, RMS,
  Strehl, MTF, photometry, 3 independent acuity models), a blur-demonstration
  animation, a live custom-sweep runner, and an explorer for every precomputed
  `stage3_integrated` dataset. Run with `streamlit run stage_v1_simulator/streamlit_app.py`.
  See `stage_v1_simulator/README.md`.
- **`data_collection/`** -- a consolidated copy of every CSV/table/plot produced by
  `stage3_human_vision/`, `stage3a/`, and `stage3_integrated/`, organized by stage and
  file type for easy browsing. See `data_collection/README.md`.
- **`model_comparison/`** -- separate analysis comparing Stage 1 vs Stage 2 vs the
  reference handbooks' deprecated closed-form formulas against each other and against
  researched clinical/commercial/literature values. See `model_comparison/README.md`.
- **`fresner1.py` .. `fresner4.py`, `test1.py`** -- earlier, single-file exploratory
  scripts that preceded the `stage1` Streamlit tool (batch sweep + a matplotlib-slider
  interactive version). Kept as-is; superseded by `stage1_v2/` for anything beyond
  historical reference.
- **`outputs/`** -- plots and CSVs generated by the `fresner*.py` scripts.
- **`IYPT_Pinhole_*`** -- problem statement, theoretical handbook, and master
  formulas/pipeline reference documents this simulation is built against.

## Running the current tool

```
cd stage_v1_simulator
streamlit run streamlit_app.py
```

The original cornea-only analyzer is still available separately:
```
cd stage1_v2
streamlit run app.py
```

Requires `numpy`, `scipy`, `pandas`, `matplotlib`, `streamlit` (all already used
elsewhere in this project).

## Scope

`stage1`/`stage1_v2` model **only** plane wave -> pinhole -> exact scalar Angular
Spectrum Method -> corneal plane; they never model the eye lens, vitreous, retina, or
image formation, and never output a single "optimal pinhole diameter." `stage2`
extends the chain to the retina via a myopia model, but still only ever imports
`stage1_v2` through `stage2/pipeline_junction.py` -- neither stage's code or CSVs are
modified by the other.
