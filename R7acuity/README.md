# R7acuity: an independent visual acuity model

## What this is

A visual acuity predictor built on a completely different architecture from
`stage4_human_vision/acuity.py`: a **template-matching ideal-observer Monte Carlo
simulation** (Watson & Ahumada, 2008 -- see `literature.py` for full, directly-
verified citation detail), not a **frequency-cutoff closed-form formula**.

This exists to answer one specific question: `stage4_human_vision/acuity.py`
fails clinical validation against the Wang (2009) "Ideal Pinhole" dataset (R^2
strongly negative, confirmed via leave-one-out cross-validation --
`stage4_human_vision/RESULTS.md`), and that failure was diagnosed as a **data**
problem (n=5, one non-monotonic clinical outlier, no per-subject refractive
error) rather than a **model** problem. A single model's failure on noisy,
small-N data can't distinguish those two explanations by itself. If a
*structurally unrelated* model, built from different first principles, ALSO
fails on the exact same data in the exact same way, that's real evidence for
the data-scarcity diagnosis. If it *doesn't* fail, that's real evidence the
diagnosis was wrong, or incomplete. Either outcome is useful; see `RESULTS.md`
for which one actually happened.

## Architecture, and how it differs from stage4_human_vision/acuity.py

| | `stage4_human_vision/acuity.py` | `R7acuity` |
|---|---|---|
| Core idea | Deterministic formula: MAR = 30/MTF-cutoff-frequency, adjusted by VSOTF and an SNR term | Monte Carlo simulation of an ideal observer performing a real 4-alternative forced-choice letter-identification task |
| Optotype | None (works directly on MTF/VSOTF scalars) | Tumbling-E, 4 orientations, rendered as actual images |
| Decision process | None modeled | Explicit: noisy image -> cross-correlation against templates -> argmax decision -> correct/incorrect |
| Noise | Folded into an SNR-based multiplicative MAR adjustment | Explicit additive Gaussian pixel noise, calibrated once against a reference condition |
| Threshold | Read directly off MTF50/MTF10 cutoff frequencies | Found by fitting a psychometric function to simulated percent-correct data across letter sizes |
| Free parameters tuned on Wang 2009 | A short-lived calibration attempt was tried and **failed** honest leave-one-out validation (`stage4_human_vision/RESULTS.md` Section 4c) | **None.** The only free parameter (noise sigma) is locked against an independent reference condition *before* Wang 2009 is ever touched (see below) |

Both models ultimately reuse the SAME validated upstream optics
(`stage2_fixed/phase2_retina.py`'s real retinal PSF) and, where applicable, the
same validated CSF/VSOTF machinery -- the comparison is specifically about the
**acuity-prediction logic** on top of that shared, already-validated physics,
not a re-litigation of the optics itself.

**Constraint honored throughout this folder**: no file here imports, calls, or
duplicates logic from `stage4_human_vision/acuity.py`.

## Pipeline (see literature.py for full citation detail on every step)

1. **Optotype** (`optotype.py`): tumbling-E, 4 orientations, standard 5x5-unit
   design (Watson & Ahumada's own convention: stroke width = MAR, overall
   letter size = 5*MAR).
2. **Optical filtering** (`ideal_observer.py`): convolve each clean E with the
   REAL simulated retinal PSF for the given aperture/myopia condition, reusing
   `stage2_fixed/phase2_retina.py` directly -- this is where this project's
   actual validated optics enters the model, not a Zernike-synthesized one.
3. **Neural filtering** (`ntf.py`): NTF(f) = CSF(f)/MTF_diffraction-limited(f),
   where CSF is the REAL Barten (1999) model (reimplemented here and verified
   bit-for-bit against the `colour-science` library's own doctested reference
   value -- the identical verification already used in
   `stage4_human_vision/MODULE10_VALIDATION.md`; not `stage4_human_vision/csf.py`'s
   `barten_simplified_csf`, confirmed to be a different, simpler form there).
4. **Noise**: additive zero-mean Gaussian noise, sigma locked once (see below).
5. **Decision** (`ideal_observer.py`): nearest-template classification via
   maximum cross-correlation against 4 CLEAN (unblurred) templates -- the "real
   observer" variant named in Leroux et al. (2024), a deliberate departure from
   Watson & Ahumada's own default (matched/blurred templates), per this
   project's brief.
6. **Threshold-finding** (`threshold.py`): Monte Carlo trials across a range of
   letter sizes, psychometric function fit (chance=25% for 4AFC, criterion=
   62.5% = midway to ceiling), threshold size converted to MAR/logMAR/Snellen.

## Noise calibration: done once, before any clinical data

`threshold.calibrate_noise_sigma()` bisects the noise sigma so that a
**diffraction-limited, emmetropic, 3mm-aperture reference condition** (standing
in for a healthy 3mm natural pupil -- simulated via this project's own real
optics at `a_hole_um=3000`, `M_diopters=0`, which introduces no other
aberration) predicts a threshold of approximately 1.0 arcmin MAR (20/20). This
runs, and is locked, **before** `run_validation.py` ever looks at Wang 2009.
Tuning sigma against clinical data instead would repeat the exact overfitting
error `stage4_human_vision/RESULTS.md`'s leave-one-out discussion already
caught and avoided -- see `outputs/sigma_calibration_log.csv` for the full
calibration trace, run exactly once.

## Running it

```bash
# 1. Calibrate sigma + validate against Wang 2009 (takes a while -- Monte Carlo
#    simulation at the real optics' validated grid_N=2048 resolution; this is a
#    one-time cost, cached to outputs/ for the dashboard to read afterward)
python3 -m R7acuity.run_validation

# 2. Explore interactively
streamlit run R7acuity/dashboard.py
```

Outputs land in `R7acuity/outputs/`: `calibrated_sigma.txt`,
`sigma_calibration_log.csv`, `validation_predicted_vs_observed.csv`,
`validation_regression_stats.csv`.

## Honesty constraints this folder follows (same discipline as elsewhere in this project)

- Every citation in `literature.py` was verified directly against the actual
  source (a full patent text, open-access papers) -- not accepted from a
  secondhand paraphrase. One citation attribution given in this model's own
  brief (author name) was found to be incorrect on direct verification and is
  corrected, not silently used, in `literature.py`.
- No parameter is tuned after seeing the Wang 2009 result. Sigma is locked
  first; the model is then run once and reported however it comes out.
- No "recommended aperture" output anywhere in this folder.
- `RESULTS.md` reports the validation outcome in whichever direction it
  actually went, with the significance bar (R^2>0 and p<0.05) applied exactly,
  not loosened to manufacture a pass.
