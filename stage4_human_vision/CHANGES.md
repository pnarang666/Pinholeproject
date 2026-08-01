# Changes to stage4_human_vision/ made while running it end-to-end for the first time

## Pass 2: literature search + replacing the uncited brightness/SNR term

Triggered by RESULTS.md's finding that the acuity predictor fails clinical validation
(R^2 << 0, p~0.5 at every M tested). Full literature search results and fidelity notes
are in the new `stage4_human_vision/literature.py`; see `RESULTS.md` for the honest
validation outcome of what's described below.

1. **acuity.py, `predict_acuity()`** — replaced the uncited `sqrt(snr)/10` **0.05
   exponent term with an additive logMAR correction cited to Tidbury, Czanner &
   Newsham (2016) for the slope (0.060 logMAR/log10-illuminance-unit, verified
   directly against full text) and Van Nes & Bouman (1967) for the 300 td knee
   below which the correction switches on (verified directly against the primary
   abstract). New function `brightness_logmar_correction()`. The OLD exponent-based
   term is kept, unchanged, as the `vsotf_snr_legacy` entry in the returned
   `models` dict (and `recommended_model` is renamed from `mtf10_vsotf_adjusted` to
   `mtf10_vsotf_brightness_adjusted` to describe what it now does) — nothing was
   silently replaced; both are available for the Step 3/4 regression comparison.
   `pipeline.py`'s call site now threads `retinal_illuminance_photopic_td` through
   to `predict_acuity`, which was already computed a few lines earlier for the
   photon-noise calculation but wasn't previously passed to acuity at all.
2. **config.py / constants.json** — new `BrightnessAcuityConfig` block
   (`logmar_per_log10_illuminance`, `weber_knee_td`), kept separate from
   `photon_noise`'s config block since it's cited from different sources. Two new
   `citations` entries (`tidbury_2016_illuminance_slope`,
   `van_nes_bouman_1967_weber_knee`) for the two numbers actually wired into code.
   Sheedy/Bailey/Raasch (1984) and Rabin (1994) are documented as corroborating
   literature in `literature.py` but are not separately in `constants.json` since no
   numeric constant is taken directly from them (their primary texts were also only
   partially verifiable — see `literature.py`'s fidelity notes on each).
   Effect size: at a_hole=400um, M=4D, the new recommended predictor now moves from
   logMAR 0.836 (10000 cd/m^2) to 0.918 (100 cd/m^2) — a real, cited luminance
   sensitivity — versus the legacy term's 0.821 to 0.824 (essentially flat).
3. **calibration.py (new module)** — `fit_linear_calibration()`,
   `leave_one_out_predictions()`, `leave_one_group_out_predictions()`. Ordinary-
   least-squares fitting and honest cross-validation mechanics only; reuses
   `validation.py`'s `regression_stats()` for all reported statistics rather than
   duplicating a stats function. Used to fit `logmar_calibrated = a*logmar_recommended
   + b` against Wang 2009 (n=5, sensitivity across M=0/2/5D). **Result: fails
   validation.** In-sample R^2 looked positive (0.13-0.16) but leave-one-out R^2 is
   negative in every case (-0.54 to -0.59; pooled grouped-leave-one-out: -0.566,
   p=0.085), and Pearson r flips sign between in-sample and held-out. An external
   check against Kim et al. (2017)'s real N=36 data point also misses by +0.30 logMAR
   (outside 1 SD). Per the brief this was fit once, reported honestly, and NOT tuned
   further to force a better number. Full detail: RESULTS.md Section 4c.
4. **outputs/stage4_full_sweep.csv, outputs/validation_*.csv, outputs/*.png** —
   regenerated. `logmar_recommended` and `snellen_denominator` updated in place (same
   fields, new formula); `logmar_vsotf_snr_legacy` and `logmar_calibrated` added as new
   columns; `logmar_mtf10`/`logmar_mtf50` untouched (unaffected by this change). The
   315-row sweep was updated by recomputing `predict_acuity()` directly from each
   row's already-saved `mtf10_cpd`/`mtf50_cpd`/`vsotf`/`snr`/`retinal_illuminance_photopic_td`
   columns rather than re-running the full optics pipeline — spot-checked identical
   (to floating point) against a full re-run of `run_stage4_point()` on a sample row
   first, since nothing upstream of `acuity.py` changed in this pass.

Immediately below is the original (Pass 1) changelog from first running Stage 4
end-to-end:

1. **validation.py, `regression_stats()`** — added the Pearson p-value (and an `n`
   count), previously missing. The function computed RMSE/MAE/R^2/Pearson r but
   never a significance test, which blocks the one thing Stage 4's own DESIGN.md
   promises ("Reported statistics: RMSE, MAE, R^2, Pearson correlation" validated
   against literature). Mirrors `stage3_human_vision/validation_stats.py`'s existing
   approach: `scipy.stats.pearsonr`, with the same `n<3` / constant-series guard
   returning NaN instead of a fabricated significance value. Argument order
   (`observed, predicted`) is unchanged and is the OPPOSITE of stage3's
   `regression_stats(predicted, observed)` — a pre-existing cross-package
   inconsistency, not introduced here; callers in both packages were already
   written for their own order, so this was left alone rather than "fixed" in a
   way that would silently flip stage3's own call sites.

No other code in stage4_human_vision/ was changed. The end-to-end stress sweep
(15 apertures x 8 myopia levels x 5 luminance levels, 600 points, grid_N=512) found
zero exceptions, zero junction-check failures, zero NaN/Inf outputs, and the
pupil-illuminance fixed-point iteration converged in 5-9 iterations (cap is 20)
at every point tested — no fix was needed there.

## Known limitations surfaced while running this (not bugs, not fixed, documented instead)

- `illuminance.py`'s `retinal_illuminance_mesopic_td` and `_scotopic_td` are
  currently identical copies of the photopic troland value, not independently
  modeled — matching DESIGN.md's own stated limitation ("mesopic handling is
  more complex than simply interpolating between photopic and scotopic
  scalars"). The luminance-dependence that actually reaches the outputs comes
  through Barten's CSF, which takes `luminance_cdm2` directly, and through the
  photon-noise SNR term — not through a separate photopic/scotopic split. This
  is a known approximation, not something this pass fixed.
- **UPDATED in Pass 2**: `acuity.py`'s VSOTF adjustment to MAR still uses a small
  hardcoded, uncited exponent (`** 0.1`), which was NOT changed in Pass 2 — only
  the SNR/brightness term was replaced (see Pass 2 item 1 above). The VSOTF
  exponent is a separate, smaller open item: it makes the recommended predictor
  a little less sensitive to VSOTF than it might otherwise be, but was out of
  scope for this pass (the brief specifically targeted the SNR/luminance term).
  If revisited, it should get the same treatment: find a citable source for the
  exponent (or a functional form) rather than tuning it to fit data, given how
  small the Wang 2009 sample is (see RESULTS.md Section 4c on why fitting
  anything to n=5 is fragile).
- Strehl ratio and VSOTF both exceed 1.0 at several sweep points. This is the
  same already-documented Fresnel near-field oscillation finding called out
  elsewhere in the project (e.g. `stage_v1_simulator`'s Live Explorer tab,
  `stage3_integrated/README.md`) — not new to Stage 4, and not fixed here since
  it's a property of the underlying near-field optics, not a Stage 4 defect.
- `illuminance.py`'s pupil-illuminance fixed-point iteration couples the
  reported "natural pupil diameter" to the *pinhole-restricted* retinal
  illuminance, not to raw scene luminance (`equivalent_luminance = trolands /
  natural_pupil_area`, iterated). This means a small pinhole under a bright
  scene reports a substantially dilated "natural pupil" (e.g. 6.1mm at 75um /
  10000 cd/m^2, vs 2.4mm at 2000um / the same 10000 cd/m^2) — see RESULTS.md
  Section 3 for the full table. This is physiologically motivated (the pupil
  reflex responds to actual retinal flux, which a persistent pinhole reduces)
  but the specific feedback formula is a first-principles construction, not
  itself a cited equation (only Watson & Yellott's pupil-given-luminance
  formula is cited). Not changed here — changing the coupling would itself be
  an uncited modeling decision — but documented since a dashboard user could
  otherwise misread "natural pupil" as "your pupil size in this room."
