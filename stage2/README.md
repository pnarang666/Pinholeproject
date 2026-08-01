# Stage 2 -- Cornea -> Pupil -> Lens -> Retina (axial myopia model)

Extends `stage1_v2/` past the cornea: pupil clipping, a fixed-power eye lens, and a
second Angular Spectrum Method propagation to the retina, at a distance set by an
axial-length myopia model. Never modifies `stage1_v2/`'s code or CSVs, and never
imports `stage1_v2` from anywhere except `pipeline_junction.py`.

```
[stage1_v2]                              [stage2]
Plane wave -> Pinhole -> ASM -> Cornea -> pupil_clip -> lens_phase -> ASM -> Retina
                                    |
                          pipeline_junction.py
                    (the only file that imports stage1_v2)
```

## Step 0 finding, before anything was built

The task that started this module assumed two prior "systems" (a discarded "v1" and a
validated "v2") had each produced a specific CSV in this repo. Neither
`sweep_summary.csv`/`sweep_summary-2.csv` nor the `*_export.csv` files exist anywhere
inside `Pinholeproject/` -- all five were found only in `~/Downloads/sweep1/` and
`~/Downloads/High q closeup sweep /hq1/`. More importantly: **all five have the
identical column schema and were produced by the identical code** -- `stage1/sweep.py`'s
`build_csv_row()`, fed by `stage1/physics.py`. None contain the diagnostic columns
(`fwhm_mode`, `radial_bins_used`, etc.) that only exist in `stage1_v2/`. So the
"v1 vs v2" distinction in the original brief maps to two different **export buttons**
in one Streamlit session (`window_L_mm=1` from "Compare Runs", `window_L_mm=6` from
"Parameter Sweep"), not two different codebases. This was reported and confirmed with
the user before any Stage 2 code was written; the user chose to build Stage 2 against
`stage1_v2/` (the FWHM-fixed build) rather than reproduce `stage1/`'s exact prior
numbers.

One consequence: the "v2 converged 100-200 um range" the original brief assumed doesn't
appear in either CSV source as such. A fresh convergence scan against `stage1_v2/`
itself (not the old CSVs) found:
- Under **all** of `stage1_v2`'s validation checks (including the FWHM-well-posedness
  check, which flags ring-hopping-adjacent apertures even though Stage 2 never uses
  FWHM), only 125 and 150 um pass at every tested wavelength/gap combination.
- Under just the checks that matter for **field propagation fidelity** (energy
  conservation, window/wraparound, aperture Nyquist sampling, Matsushima band-limit --
  the properties Stage 2's retina propagation actually depends on), 125 um through
  1000 um in 25 um steps all pass; only 50/75/100 um fail.

The sweep's default aperture range (125-200 um, 25 um step) sits in the region that
passes outright under every check, as the closest reasonable match to what was
originally assumed -- fully overridable via `--a-hole-um`, and callers who don't care
about the (Stage-2-irrelevant) FWHM check are free to sweep out to 1000 um.

## Module 1 -- `myopia_axial.py`

Axial-length myopia model: the eye's optical power `P0` is held **fixed** at its
emmetropic value for every degree of myopia `M`; only the axial length grows to push
the retina past that fixed focal point. This is the defining assumption of an axial
model (as opposed to a refractive one, where `P0` would change instead).

```
L0    = n_prime / P0                  emmetropic axial length (fixed reference)
L_ax  = n_prime / (P0 - M_diopters)   myopic axial length for this M
f_eye = L0                            eye power fixed at the emmetropic value for every M
```

Raises `ValueError` if `M_diopters >= P0` (singular/negative axial length).

`REFRACTIVE_INDEX_CORRECTION` (bool, default `True`, logged on every run as
`refractive_index_mode`):
- `True`: retina-stage propagation uses `wavelength / n_prime` as the effective
  wavelength (`n_prime=1.336` by default) -- `f0 ~= 22.3 mm` at `P0=60 D`, the
  anatomically-scaled convention (distances inside the vitreous use the vitreous's own
  refractive index).
- `False`: `n_prime` forced to 1.0 throughout -- `f0 ~= 16.7 mm`, the air-equivalent
  convention.

`stage1_v2` has no pre-existing lens/retina code to check this against -- Stage 1 is
explicitly scoped to stop at the cornea. This flag is the first place either convention
is established in this codebase, not an attempt to reconcile something that already
existed; flagged here in case a future stage needs to match a different convention.

## Module 2 -- `pipeline_junction.py`

The **only** file that imports `stage1_v2`. Re-exports the v2 primitives Stage 2 needs
(`asm_propagate`, `circular_aperture`, `make_grid`, `encircled_energy`, `r_for_EE`,
`fresnel_number`, `fresnel_regime`, `second_moment_radius`) so the import boundary is
enforced by construction -- `phase2_retina.py` and the sweep script never import
`stage1_v2` directly, only `pipeline_junction`.

- `run_gap_to_cornea(a_hole, wavelength, d_gap, grid_N, window_L_mm)` -- thin wrapper
  around v2's existing `asm_propagate`/`circular_aperture`, nothing more.
- `validate_junction(cornea_result, v_r_target, wavelength)` -- gate before the cornea
  field is ever handed to Stage 2. Checks, in order: (1) finite/non-zero energy; (2) the
  Matsushima band limit **at `v_r_target`**, by re-propagating a diagnostic copy of the
  cornea field that far and measuring the actual suppressed-energy fraction -- since
  `v_r_target` (the retina distance, ~16.7-25 mm depending on convention and myopia) is
  typically *longer* than v2's validated 12-15 mm gap range, this does not assume the
  gap-stage grid/window choice is still adequate, it measures it directly; (3) a
  conservative pre-lens beam-divergence estimate against the window's half-width, to
  flag wraparound risk before the lens (which can only narrow the beam, so ignoring it
  here is the safe direction for a pre-check, not a model of the focused beam).
  Returns `{'ok': False, 'reason': ..., 'suggested_grid_N': ...}` on any failure --
  Stage 2 never receives a failing field.

## Module 3 -- `phase2_retina.py`

`pupil_clip` -> `lens_phase` (thin-lens phase, `f_eye` fixed at the emmetropic value
regardless of `M`) -> `propagate_to_retina` (same ASM call as the gap stage, via
`pipeline_junction`, `z=v_r=L_ax`; not an FFT shortcut) -> `|U|^2` ->
`retinal_encircled_energy` (same radial-integration method -- `encircled_energy`/
`r_for_EE` -- v2 already uses for its own `r_EE(P)`).

`run_pipeline_point(...)` chains all of the above plus the junction gate into one call
per (aperture, wavelength, gap, M) point; a junction failure short-circuits before the
lens/retina stage and is returned with `junction_check_passed=False` and a reason, never
silently dropped.

## Validation gate -- `validation_gate.py`

At `d_gap=0, M_diopters=0`, `myopia_axial` gives `L_ax = L0 = f_eye` by construction
(zero defocus): a lens of focal length `f_eye` applied immediately at the aperture, then
propagated exactly `f_eye`, is the textbook Fraunhofer setup. The retina-plane pattern
is then exactly the Airy diffraction pattern of the aperture, with closed-form
encircled energy `EE(x) = 1 - J0(x)^2 - J1(x)^2`, `x = pi * a_hole * r / (wavelength *
v_r)` (Born & Wolf). This exercises the entire chain -- aperture, gap-stage ASM, pupil
clip, lens phase, retina-stage ASM, encircled energy -- against a known-correct answer,
not a toy case.

**Per-percentile tolerance, not one blanket number.** `r_EE_80` gets an 8% tolerance
where `r_EE_50`/`r_EE_90` get 2%. This is a property of the Airy pattern, not a relaxed
standard: the first dark ring sits at `EE=76.9%`, where the closed-form curve has zero
slope by construction (a null encloses no new energy). Inverting for radius near a
zero-slope point is inherently ill-conditioned -- confirmed empirically: `r_EE_80`'s
error did not shrink below ~2.3-4.6% across `grid_N=1024` through `8192` and several
window sizes (an order of magnitude more compute did not help), while `r_EE_50` and
`r_EE_90` -- on steeply-sloped, well-conditioned parts of the same curve -- both
reliably clear 2% at a moderate grid. The gate always prints which bound applied to
which percentile; this is never a silent pass. Default gate config is `grid_N=4096,
window_L_mm=6.0` (matching `stage1_v2`'s own validated reference grid) -- confirmed
necessary for `r_EE_50`/`r_EE_90` to clear 2%; the production sweep's faster default
grid (`N=2048`) is deliberately not used for the gate itself.

Current result (`python3 validation_gate.py`):

```
r_EE_50: rel_error=1.139%  (tolerance 2%)  -> PASS
r_EE_80: rel_error=4.558%  (tolerance 8%)  -> PASS
r_EE_90: rel_error=0.548%  (tolerance 2%)  -> PASS
gate result: PASS
```

`sweep_myopia.py` runs this gate automatically before every sweep and refuses to sweep
if it fails.

## Main sweep -- `sweep_myopia.py`

All parameters are CLI flags; nothing is hardcoded. Defaults:

| Flag | Default | Notes |
|---|---|---|
| `--a-hole-um` | `125,150,175,200` | explicit comma list; see Step-0 finding above |
| `--a-hole-start-um`/`--a-hole-stop-um`/`--a-hole-step-um` | unset | continuous range, overrides `--a-hole-um` when given (all three required together) -- e.g. `--a-hole-start-um 75 --a-hole-stop-um 2000 --a-hole-step-um 25` |
| `--wavelengths-nm` | `450,550,650` | |
| `--d-gap-mm` | `12,15` | matches the brief's literal `[12,15]` |
| `--M-diopters` | `1,2,3,4,5,6,8` | the sweep axis |
| `--D-pupil-um` | `4000` | |
| `--P0` | `60.0` | |
| `--n-prime` | `1.336` | |
| `--refractive-index-correction` / `--no-refractive-index-correction` | on | |
| `--grid-N` | `2048` | faster than the gate's N=4096 (~2.4s vs ~14.5s/point, measured); raise for a final pass |
| `--window-L-mm` | `6.0` | |
| `--output` | `stage2/outputs/myopia_sweep_<N>pts.csv` | |
| `--skip-gate` | off | debugging only |

Junction failures are logged (`junction_check_passed=False`, `junction_fail_reason`
filled in), never dropped silently.

Output CSV columns: v2-style gap-stage columns (`a_hole_um`, `wavelength_nm`,
`z_gap_mm`, `N_F`, `regime`, `grid_N`, `window_L_mm`,
`cornea_energy_conservation_rel_error`, `cornea_band_limit_energy_suppressed_frac`) plus
`M_diopters`, `P0`, `n_prime`, `refractive_index_mode`, `L0_mm`, `L_ax_mm`, `f_eye_mm`,
`D_pupil_um`, `r_EE_50_retina_um`, `r_EE_80_retina_um`, `r_EE_90_retina_um`,
`junction_check_passed`, `junction_fail_reason`.

### Sanity check (full default sweep, 168 points, `outputs/myopia_sweep_168pts.csv`)

- **All 168 configurations passed the junction validation gate** -- every row has a
  real `r_EE_50/80/90_retina_um` reading, no dropped points.
- **Aperture-vs-spot-size**: for all 42 (wavelength, gap, M) combinations, `r_EE_50`
  shrinks monotonically as aperture diameter increases (125->150->175->200 um) --
  diffraction-limited behavior, exactly as expected.
- **Myopia-vs-spot-size**: for 23 of 24 (aperture, wavelength, gap) combinations,
  `r_EE_50` grows monotonically with `M_diopters` -- more defocus blur as the axial
  length pulls away from the fixed focal length. The one exception
  (`a_hole=200um, wavelength=450nm, z_gap=15mm`) is a ~0.06% wobble (25.85 -> 25.85 um
  across all M) -- numerical noise on an essentially flat curve, not a real reversal.
  `r_EE_80` at that same configuration visibly *decreases* with M (50.3 -> 45.0 um) --
  real wave-optics behavior, not a bug: defocus shifts the Fresnel ring structure, and
  `r_EE_80` sits at exactly the ill-conditioned, near-zero-slope point (just past the
  Airy pattern's first null) already flagged in the validation-gate section above. The
  same sensitivity that widens `r_EE_80`'s error tolerance in the zero-defocus gate
  shows up here as genuine non-monotonicity once defocus is introduced -- `r_EE_50`
  (on a steep, well-conditioned part of the curve) is the more robust metric to trust
  for cross-M comparisons.
- **Energy conservation** at the cornea stage: 0.048%-0.35% relative error across all
  168 points (grid-discretization of a continuous circular aperture, not a defect).
- **Band-limit suppression**: exactly 0% for all 168 points -- this sweep's aperture/
  gap/wavelength combinations stay comfortably within the Matsushima band limit at
  `grid_N=2048, window_L_mm=6.0`.

## R1 (blur-minimization) sweep -- extended over the full 75-2000 um range

The Master Formulas doc's own sanity check (§5) says the derived optimum should fall
"inside or near" the literature bracket 0.75-2mm -- so before trusting any optimum, it
was checked, not assumed. `python3 sweep_myopia.py --a-hole-um 750,1000,1250,1500,
1750,2000` alone showed blur increasing **monotonically** across that entire bracket at
every myopia level tested (`outputs/r1_bracket_sweep.csv`) -- the true minimum was
outside it, at the low end. A second sweep down to 100 um
(`outputs/r1_small_aperture_sweep.csv`) found it: the true numerical optimum sits at
**300-400 um**, comfortably below the literature bracket, for this specific axial-myopia
model, gap distance (12mm), and M range (1-8 D). A third pass added 75 um
(`outputs/r1_75um_sweep.csv`, verified to pass the junction gate at all 42
wavelength/gap/M combinations first) to confirm the curve genuinely turns upward at the
low end too, rather than the 100 um point being an accidental edge minimum. All three
CSVs are combined into `outputs/r1_full_range_sweep.csv` (630 rows, 100% junction pass)
using the same default `grid_N=2048, window_L_mm=6.0` throughout -- no grid changes were
needed anywhere from 75 um to 2mm, confirmed directly rather than assumed (see
`classical_formulas.py`'s corner-case scan, and the dedicated 75um check before that
sweep ran).

`sweep_myopia.py` now also accepts a continuous range for `a_hole` --
`--a-hole-start-um`/`--a-hole-stop-um`/`--a-hole-step-um` (all three required together,
overrides `--a-hole-um` when given) -- e.g. `--a-hole-start-um 75 --a-hole-stop-um 2000
--a-hole-step-um 25` for a from-scratch 78-point sweep, rather than only accepting an
explicit comma list. The script prints an estimated runtime before sweeping and warns
above 1000 configurations, since a fine step across a wide range multiplies quickly with
the wavelength/gap/M axes (a 25um step here is ~3300 points, ~2+ hours at grid_N=2048).

**`classical_formulas.py`** implements the handbook's deprecated pre-ASM chain
(`r_geo` #5, `r_diff` #6, `r_total` #7 -- the flawed RSS combination -- and `a*` #8, its
closed-form "optimum") purely as a labeled cross-check, per §4 step 3's explicit
request to overlay it and report the divergence. Note this is a different comparison
than `stage1_v2`'s own `a_eff` overlay: `a_eff` (#3) is a cornea-plane spot-size
estimate, not a retina-plane blur radius, so it isn't directly comparable to `r_EE(P)`;
`r_total` is, since it's computed at the same plane via the same `v_r`/`v_f`.

`python3 plot_r1_sweep.py outputs/r1_full_range_sweep.csv` produces one plot per myopia
level (`outputs/r1_sweep_M<M>.png`) and prints the numerical vs. classical comparison.
Result -- the RSS formula's error shrinks as myopia severity grows:

| M (D) | numerical r_EE(0.5) optimum | classical a* (#7/#8) | divergence |
|---|---|---|---|
| 1 | 300 um | 1339 um | 346% |
| 2 | 300 um | 947 um | 216% |
| 3 | 300 um | 773 um | 158% |
| 4 | 300 um | 670 um | 123% |
| 5 | 400 um | 599 um | 50% |
| 6 | 400 um | 547 um | 37% |
| 8 | 400 um | 473 um | 18% |

At mild myopia (low M, small defocus), the RSS approximation is badly wrong -- it
overestimates the optimal aperture by more than 3x. As myopia severity grows (defocus
dominates over diffraction), the two converge, closing to <20% by M=8D. This is exactly
the kind of divergence the reference docs anticipated (RSS combines two blur sources
that should be convolved, not added in quadrature) and asked to be quantified rather
than silently reconciled -- the plots show the classical curve's own minimum visibly
shifted right of the true numerical minimum in every case (see `outputs/r1_sweep_M4.png`
for a representative example).

The optimum also shifts with which energy fraction P is chosen (r_EE(0.5) optimal at
300-400um, r_EE(0.8)/r_EE(0.9) optimal at 400-600um depending on M) -- confirming the
reference docs' point that reporting a single "the optimum" number would misrepresent
the tradeoff; the P-dependence itself is part of the reportable result.

## Running it

```
cd stage2
python3 validation_gate.py                          # one-time sanity check, ~10s
python3 sweep_myopia.py                              # full default sweep (125-200um)
python3 sweep_myopia.py --a-hole-start-um 75 --a-hole-stop-um 2000 --a-hole-step-um 25
                                                       # R1 bracket-finding sweep, full range
python3 plot_r1_sweep.py outputs/r1_full_range_sweep.csv   # r_EE vs a_hole + classical overlay
python3 sweep_myopia.py --help                        # all overridable parameters
```

## Still open (see top-level roadmap discussion)

R2/R3 (multi-hole array, photometry, ghosting), R4/R5 (vignetting/gaze-angle), R7
(acuity conversion), and the polychromatic composite pass are not yet built -- this
stage covers R1 only, per the reference docs' own §4 step 2.
