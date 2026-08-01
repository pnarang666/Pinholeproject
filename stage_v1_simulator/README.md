# Stage v1 Simulator -- Interactive Wrapper (Phase B)

A 4-tab Streamlit app wrapping `stage3_integrated/`'s precomputed theory dataset with
live single-point exploration and a qualitative blur-demonstration animation. Does not
modify `stage1_v2/`, `stage2/`, `stage2_fixed/`, `stage3a/`, `stage3_human_vision/`, or
`stage3_integrated/` -- only imports from `stage2_fixed` and `stage3_human_vision`
(`live_compute.py`), and reads `stage3_integrated/outputs/` (`theory_browser.py`).

**No "recommended aperture" output anywhere in this app.** Every tab is exploration,
demonstration, or a display of precomputed comparison data -- never a recommendation.

**Companion app note (added, code untouched)**: `singleilluminate/streamlit_app.py`
is now available as a lighter-weight, illumination-only companion app -- no wave-optics
computation, so it never needs this app's fast/accurate-mode split. Follow-up flagged,
not done here: Tab 1 (Live Explorer)'s illuminance readout currently recomputes
`stage3a`'s `(a_hole/D_pupil)^2` formula directly in `live_compute.py`; it should
eventually call `singleilluminate/illumination_model.py::percent_illumination()`
instead, so this app and `singleilluminate` share one illumination code path rather
than two independently-maintained copies of the same formula. Not refactored here --
this is a note for a future session, not a silent change to this app's code.

## Tabs

1. **Live Explorer** -- sliders for every parameter (aperture snapped to
   `stage3_integrated`'s own discrete grid so live points compare directly). Full
   factor set displayed, grouped: **blur/EE** (r_EE at all 4 percentiles, RMS radius,
   Airy diameter), **optical quality** (Strehl, MTF50/10, F-number), **photometry**
   (relative illuminance colored against a user-set T_min threshold, Trolands, photon
   flux density), and **acuity predictions** (3 independent models side by side --
   MTF50-cutoff, MTF10-cutoff, Rose-DeVries SNR bound -- plus CSF-weighted visual
   Strehl under both implemented CSF variants; never merged into one number). Also:
   retinal intensity heatmap, radial profile with all 4 r_EE percentiles marked, an
   MTF-vs-CSF overlay plot, the precomputed r_EE(50%) curve with the live point
   overlaid, and a schematic (explicitly non-anatomical) eye diagram.
2. **Blur Demonstration** -- a synthetic tumbling-E chart (explicitly labeled NOT a
   clinically calibrated optotype) convolved with the unit-volume-normalized retinal
   PSF. Single-point before/after/side-by-side, or an animated sweep across the full
   discrete aperture range -- frames are precomputed once on button press, then
   scrubbed/played from cache (never recomputed per frame).
3. **Sweep & Explore** -- five sections:
   - *Run New Sweep (live)*: configure your own aperture list, myopia levels,
     wavelength, and gap; runs live at `grid_N=512` (~0.5-0.6s/point measured) with a
     progress bar, then the SAME flexible plotting (line/heatmap/Pareto front, any
     computed metric) as the precomputed-data view below. This is the "sweep facility"
     -- previously sweeps were CLI-only; now they run and plot from inside the dashboard.
   - *Explore Precomputed Data*: the same flexible line/heatmap/Pareto plotting,
     applied to any of `stage3_integrated`'s actual sweep CSVs (the combined 105-point
     grid, the wavelength/gap subset, the fine-Strehl investigation, the retina-plane
     FWHM sweep) -- pick the metric and axis, not just a fixed pre-rendered image.
   - *Static Gallery*: the original fixed `stage3_integrated/outputs/*.png` plots.
   - *Tables*: `stage3_integrated`'s validation/uncertainty/error-budget/optimum tables.
   - *Literature (live)*: renders `stage3_human_vision/literature.py`'s `CITATIONS`
     dict directly -- never recomputes anything.
4. **Session Log** -- every live-computed point (Tabs 1-2) appended with full
   parameters, outputs, `grid_N`, and timestamp; exportable as CSV.

## Performance design (do not violate)

`run_pipeline_point()` at `grid_N=2048` measures ~5s on this machine; Streamlit reruns
the whole script on every widget interaction. Consequently:

- Interactive default is `grid_N=512` (~0.2-0.5s, measured), with the actual `grid_N`
  and last compute time always shown next to any number -- a fast preview is never
  silently presented as validated.
- A separate, explicit "Compute at high accuracy (grid_N=2048)" button is the only way
  to trigger the slow path -- no slider drag ever does.
- `st.cache_data` keyed on the full parameter tuple avoids recomputing identical points.
- The Sweep & Explore tab's *Static Gallery*/*Tables*/*Literature* sections never call
  any compute function -- only *Run New Sweep* does, on an explicit button press, and
  it too stays at `grid_N=512` (a 15x7 grid, 105 points, would take ~60s -- kept
  interactive by capping custom sweeps at 300 points and always showing a progress bar).

## Running it

```
cd stage_v1_simulator
streamlit run streamlit_app.py
```

**Prerequisite**: `stage3_integrated/outputs/` must already exist (run
`stage3_integrated/run_full_theory_sweep.py`, `generate_plots.py`, and
`generate_tables.py` first) -- the Sweep & Explore tab's precomputed sections and the
Live Explorer's precomputed-curve overlay both read from it, and will show a clear
warning (not a crash) if it's missing. **Run New Sweep** has no such prerequisite --
it computes everything itself, live.

## Files

| File | Role |
|---|---|
| `streamlit_app.py` | main app, all 4 tabs |
| `live_compute.py` | thin orchestration: one `run_pipeline_point()` call + `stage3_human_vision`'s metrics/photometry/visual_acuity functions, extended with r_EE(70%), Rose-DeVries SNR acuity, and CSF-weighted visual-Strehl (VSOTF approximate fidelity, weights Re(OTF) via `metrics.otf_radial`, both CSF variants) |
| `sweep_ui.py` | live sweep runner (`run_custom_sweep`) + parametrized plotting (line/heatmap/Pareto, any metric) shared by both the live-sweep and precomputed-data views |
| `eye_chart_blur.py` | tumbling-E chart generation + PSF convolution |
| `eye_diagram.py` | schematic (non-anatomical) eye distance diagram |
| `theory_browser.py` | Sweep & Explore tab: live sweep UI, interactive precomputed-data explorer, static gallery, tables, literature |
| `data_logger.py` | session CSV logging |

## What changed from the original Phase-B build

The original version's Theory Browser could only display `stage3_integrated`'s
fixed, pre-rendered PNGs, and Live Explorer only surfaced 3 of the ~20 metrics this
project actually computes per point. Both were expanded: sweeps can now be configured
and run live from the dashboard (not just via CLI scripts), any precomputed or
freshly-swept dataset can be explored with a user-chosen metric/axis/plot type (not
just fixed images), and Live Explorer now shows the complete factor set -- all 4 EE
percentiles, RMS radius, Airy diameter, Strehl, MTF50/10, F-number, relative
illuminance, Trolands, photon flux, and all 3 independent acuity-prediction models
plus CSF-weighted visual Strehl.
