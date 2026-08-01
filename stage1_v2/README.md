# Stage 1 v2 -- Corneal Fresnel Field Analyzer (accuracy fix)

This is a fork of [`../stage1/`](../stage1/), kept fully independent so the original tool
stays intact. It exists to fix a real measurement bug found in the original: **FWHM (and
the related 1/e² and custom-threshold radii) could jump by tens of microns between two
aperture diameters that differ by 1 µm**, even though the underlying field changes
smoothly. Everything else -- the ASM propagator, the Streamlit UI, encircled energy,
sweeps, exports -- is unchanged from `stage1/`.

If you just want to run the tool:

```
cd stage1_v2
streamlit run app.py
```

## The bug, in one sentence

The original `fwhm_radius()` walked outward from the profile's peak and reported the
**first** radial sample below half-max. Once a diffraction pattern has more than one
Fresnel ring of comparable brightness (routine once the Fresnel number `N_F` is
`O(1)`-`O(10)`, i.e. exactly the pinhole-sunglasses regime), a fixed threshold gets
crossed multiple times as radius increases, and which ring is "the first crossing" can
flip on a sub-1% change in peak intensity -- which itself changes continuously as you
sweep aperture diameter or gap. Reported symptom: FWHM jumping ~35 µm -> ~64 µm between
190 µm and 193 µm apertures at `λ=550 nm, z=12 mm`, confirmed reproducible and traced to
this exact mechanism (see `diagnosis` notes below).

Two more, smaller issues compounded it:

1. **No sub-bin interpolation.** The crossing radius was reported as a raw bin center,
   adding a staircase on top of the ring-hopping jump.
2. **The reference "peak" intensity was itself measured too low.** A histogram bin
   average over the first annulus smooths a sharp on-axis diffraction spike down --
   confirmed ~2.5x low in one tested configuration -- which then understates 100% and
   biases every peak-referenced radius outward.

## What changed in `physics.py`

### 1. `locate_threshold_crossing()` replaces the old first-crossing search

Walks outward from the peak and stops at whichever comes first:

- the intensity crosses the threshold -- interpolated to sub-bin precision, or
- a **genuine** local minimum, confirmed by a real, prominent rise over the next few
  samples (not a sub-percent noise wiggle) -- reported as a labeled **lower bound**, not
  a crossing, because the central lobe turned back up into the next ring before ever
  reaching that threshold.

This locks the measurement to *one physical feature* (the central lobe), so it varies
continuously with the swept parameter instead of hopping between whichever ring happens
to sit nearest the threshold at that instant. The minimum's own location is refined with
a parabolic (3-point) fit, not just taken as the raw bin center, since the true minimum
is often broad and shallow enough that the discrete "which bin is lowest" flips between
two adjacent, nearly-tied samples on a tiny parameter change.

Verified end to end on the exact sweep that originally exposed the bug (`λ=550 nm,
z=12 mm`, aperture 183-220 µm, 1 µm steps): the maximum step-to-step change is now
**~2 µm**, down from the original ~28 µm, everywhere the profile's global peak stays on
the optical axis. `fwhm_mode` / `one_over_e2_mode` / `threshold_radius_mode` in the CSV
export and the app's readouts tell you which case applied.

**One discontinuity this deliberately does not smooth over**: the radial profile's
global maximum can itself relocate from the central spot to an outer ring as parameters
sweep through a real hot-spot/hot-ring transition (confirmed at ~200 µm in the same test
sweep). That is genuine physics, not a sampling artifact, and it was already flagged by
the existing "central-peak assumption" validation check -- this fix does not touch that
check, and does not try to paper over a real regime change.

### 2. `radial_profile()` now samples by interpolation, not histogram binning

The old version binned the 2D grid into annuli and averaged (`bincount`/`digitize`).
Two failure modes came with that:

- A coarse bin count blurs a Fresnel shoulder and biases the measured peak low.
- A bin width finer than the native pixel spacing can leave some near-axis annuli with
  **zero actual samples**; the `count==0 -> 1` fallback then silently reports those bins
  as intensity 0 -- a fabricated value, not a resolved one (confirmed: this produced a
  spurious, constant, near-zero "FWHM" when bins were naively made finer).

The new version samples the raw 2D intensity along `n_theta` angular rays at each radius
(bilinear interpolation, native pixel spacing) and averages over angle. At `r=0` every
angle maps to the same point, so the profile's center value is *exactly* the true
center-pixel intensity -- no smoothing-down of a sharp peak, and no empty-bin risk at any
radius, since interpolation is always defined. This is also noticeably **faster** than
the histogram approach (the dominant cost there was `np.digitize` over the full 2D
array), so `run_configuration()` is faster end to end despite doing more accurate work
(measured ~1.12 s vs ~1.54 s at N=2048 on this machine).

`encircled_energy()` is untouched and still histogram-based -- EE(P) is a cumulative
power integral, and a per-annulus power sum is the correct tool for that; it was never
part of this bug (confirmed smooth across the same sweep that exposed the FWHM jump).

### 3. New diagnostics, exposed everywhere a radius is reported

- `effective_radius_detail(run, definition, ...)` returns `{radius, mode,
  crossing_count}` for `fwhm` / `1/e2` / `threshold`. `mode` is one of `"crossed"`,
  `"local_min_above_threshold"`, `"never_crossed"`.
- A new validation check, **"Central-lobe half-max crossing (FWHM well-posedness)"**,
  reports whether FWHM crossed cleanly and how many times the profile crosses half-max
  overall; if it's a lower bound, it says so and points at `r_EE(P)` or the second-moment
  radius as robust alternatives.
- The Streamlit app prefixes a lower-bound reading with "≥" and adds a one-line caption
  explaining why, in both the metric tiles and the plot legend.
- `sweep.py`'s CSV export gains `fwhm_mode`, `one_over_e2_mode`, `threshold_radius_mode`,
  `halfmax_crossing_count`, and `radial_bins_used` columns, so a lower-bound or
  ring-ambiguous reading is never exported as an unqualified number.

## What did *not* change

The ASM propagator, Matsushima band-limit anti-aliasing, Fresnel number/regime
classification, `r_EE(P)`, second-moment radius, equivalent-area radius, the Streamlit
tab layout, sweep engine, and export formats are all identical to `stage1/`. If you
diffed the two folders, the only substantive changes are inside `physics.py`'s radial
profile / effective-radius section, plus the small amount of `app.py`/`sweep.py`
plumbing needed to surface the new `mode` field.

## Files

Same four modules as `stage1/`: `physics.py` (core propagator + effective-radius
toolkit), `plotting.py` (unchanged), `sweep.py` (CSV schema extended), `app.py` (Single
Run / Compare Runs / Parameter Sweep / Diagnostics & Help tabs, extended readouts).
