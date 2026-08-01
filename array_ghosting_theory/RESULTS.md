# Ghosting Regime Classifier: Implementation Results

Implements THEORY.md's Eq. (5) three-regime ghosting-perceptibility criterion, replacing
the old crude `s < r_EE(P)*d_gap/v_r` check. Full implementation history below, in the
order things were actually found/fixed -- kept rather than only showing the final state,
since the corrections themselves are part of the theoretical record.

**Files in this folder**: `ghosting_regime.py` (Eq. 5 classifier), `contrast.py` +
`metrics_mtf.py` (heuristic CSF and MTF, mirrored verbatim from
`stage3_human_vision`), `contrast_barten.py` (real Barten 1999 CSF, see UPDATE below),
`harmonic_analysis.py` (harmonic-series extension, see UPDATE 2 below),
`ghosting_sweep.csv` / `ghosting_sweep_barten.csv` / `ghosting_sweep_harmonic.csv` (the
three successive sweeps), `ghosting_regime_map.png` / `ghosting_regime_map_barten.png` /
`harmonic_margin_profile.png` (plots), `THEORY.md` (the derivation these implement).

## Pass 1 (heuristic CSF, fundamental frequency only): no Regime C found, for a specific, identified reason

36-point sweep: apertures [300,400,700,1000]um x pitches [700,900,1200,1500,2000,2500,
3200,4000,4800]um, M=4D, d_gap=12mm, 550nm, D_pupil=4000um, grid_N=1024, square packing.
Every point came back A (16/36) or B (20/36) -- zero Regime C. Traced to: every
Regime-B point had ghosting frequency f0<0.3 cpd (physically correct -- near-eye mm-
scale pitch genuinely produces a coarse, sub-1-cpd pattern), evaluated against the
project's own heuristic CSF models (`contrast.py`, peak-matched to 4/8 cpd, never fit
or validated below their peak) -- which returned a physically impossible threshold
(16,337 to 1,000,000, i.e. >100% contrast needed) this far outside their fitted range,
making Regime B trivially satisfied regardless of the real MTF value.

## Pass 2: the real Barten (1999) model reverses the result

Found and verified a working implementation of the real Barten (1999) CSF model (P.G.J.
Barten, *Contrast Sensitivity of the Human Eye and Its Effects on Image Quality*, 1999;
simplified form: Barten, *Proc. SPIE* 5294, 231-238, 2003), via the published
`colour-science` Python package (`pip install colour-science`). Stated valid range:
0.2-50 cycles/degree -- overlapping this project's actual ghosting frequencies
(0.10-0.30 cpd). New module: `contrast_barten.py`. Sanity-checked first (threshold
0.6%-3.6% across a 2-60 degree field-size range, near-luminance-independent at this
frequency -- physically sane, unlike the heuristic's artifact).

Re-ran the identical 36-point sweep (`ghosting_sweep_barten.csv`,
`ghosting_regime_map_barten.png`; monocular correction sqrt(2) applied per source
documentation; L=10000 cd/m^2, field=10 degrees):

| Regime | Pass 1 (heuristic CSF) | Pass 2 (real Barten CSF) |
|---|---|---|
| A (sparse, N_eff<=1) | 16 | 16 (unchanged) |
| B (dense, CSF says safe) | 20 | **0** |
| C (danger zone) | 0 | **20** |

**Every previously-"safe" dense point reclassified as danger zone -- including the
entire real CN patent pitch range (700-1200um).** This is now directionally consistent
with Kim et al. (2017)'s directly-quoted clinical finding that multiple-pinhole (MPH)
glasses cause significantly more double/triple-vision and honeycomb/grating symptoms
than single-pinhole glasses (see THEORY.md Sec 2.2) -- the theory no longer needs an
unresolved gap to explain that finding away.

## Pass 3: the fundamental frequency isn't even the most dangerous one -- the harmonic series matters

Passes 1-2 only ever tested the FUNDAMENTAL ghosting frequency f0=1/delta_r. But a
finite train of N shifted PSF copies is a genuinely periodic signal with harmonic
content at every n*f0 (n=1,2,3,...), not a single sinusoid -- derived properly in
`harmonic_analysis.py`'s docstring (finite-N Dirichlet-kernel caveat stated there, not
hidden: the equal-amplitude-per-harmonic idealization used here is an upper bound at
low N_eff, close to exact at N_eff>~10).

**Computed the full harmonic margin profile (MTF(n*f0)/CSF_threshold(n*f0)) for n=1
to 40 at every dense-pitch point, and found the worst-case harmonic is NEVER n=1.**
Representative case (a_hole=400um, pitch=900um, M=4D): fundamental-alone margin is
75.6 (already >1, i.e. already "danger zone" per Pass 2) -- but the actual worst
harmonic is **n=9, at 2.09 cpd, with a margin of 329.2 -- 4.4x more dangerous than the
fundamental alone predicted.** See `harmonic_margin_profile.png`.

**Why, and why this generalizes**: MTF decreases smoothly and monotonically with
frequency; the Barten CSF's sensitivity peak sits in a fixed absolute frequency band
(~2-5 cpd) regardless of pitch. Multiplying these gives a margin curve whose peak sits
at that same fixed absolute frequency -- pitch only determines WHICH harmonic index n
happens to land there, not whether one does. Confirmed by re-running the full 36-point
sweep with harmonic analysis (`ghosting_sweep_harmonic.csv`): **the worst-case margin at
a given aperture is essentially constant across every dense pitch tested** (~329 for
a_hole=300/400um, ~273 for 700um, ~219 for 1000um, regardless of pitch -- only the
harmonic index n that achieves it changes, from n=4 at the sparsest dense pitch tested
to n=20 at the densest). **Also confirmed robust across myopia** (M=1-8D, same
aperture/pitch): worst harmonic stays at 1.86-2.33 cpd throughout, margin increasing
mildly with M (303 at M=1D to 364 at M=8D).

### The strongest, most generalizable finding from this whole exercise

**For this project's near-eye geometry (d_gap~12mm, v_r~22-24mm), any array dense
enough to have N_eff>1 (i.e. outside Regime A) will almost inevitably have SOME
harmonic of its ghosting comb land near the eye's peak contrast sensitivity band
(~2-5 cpd), regardless of the specific pitch chosen.** This means the "dense-but-safe"
window (Regime B) that Pass 1's broken CSF model wrongly reported as occupying the
entire dense-pitch range is not just wrong in degree -- it may not meaningfully exist
at all at this geometry, once harmonics are properly accounted for. The real, useful
design lever is Regime A (N_eff<=1, sparse enough that there's rarely a second hole to
ghost against at all) -- not "dense enough to blur the ripple away," which the
harmonic analysis suggests is much harder to achieve than the fundamental-only
analysis implied.

## What this does NOT yet establish (unchanged from Pass 2, still true)

- Whether the CN patent's specific design produces documented ghosting complaints --
  no clinical source found for that exact product.
- The field-size (10 deg) and luminance (10000 cd/m^2) assumptions are stated and
  checked for robustness, but remain assumptions.
- **Most importantly**: whether real human perception of a computed high-margin
  harmonic, in this specific defocused, near-eye, small-array viewing geometry,
  actually matches the Barten model's prediction is still an experimental question.
  The model was built and validated for ordinary display/print viewing conditions.
- The finite-N equal-amplitude idealization (`harmonic_analysis.py`'s stated caveat)
  means the harmonic margins reported here are upper bounds at low N_eff (2-4),
  closer to exact at high N_eff (>10) -- most of the CN-patent-range points are in the
  high-N_eff, more-trustworthy regime; the sparser dense points (N_eff=2-4) less so.

## For the report

This is now a substantially stronger result than either earlier pass: not just "a
theory that replaces a broken formula," but a theory that (1) reversed its own
preliminary conclusion once a better citation was found and verified, (2) extended
itself to check an assumption (fundamental-only) that turned out to matter a lot, and
(3) arrived at a single, clean, generalizable physical statement (the CSF-peak/margin
argument above) rather than a table of case-by-case numbers. The remaining gap is
exactly the same one stated in THEORY.md Sec 5 from the start: confirm this against a
real intermediate/dense-pitch sample in the planned experiment.
