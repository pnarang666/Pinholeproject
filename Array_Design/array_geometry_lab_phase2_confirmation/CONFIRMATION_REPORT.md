# Phase 2 Full-Physics Confirmation Report

Confirms (or diverges from) Phase 1's closed-form screening predictions for the 9 Metric-1 finalists by propagating each finalist's ACTUAL multi-aperture mask through `array_optimization`'s validated ASM engine (imported directly, not copied -- see `run_full_physics.py`) and directly measuring blur and ghost separation by peak detection, never falling back to the closed-form formula.

**Result: 9/9 finalists CONFIRMED, 0/9 DIVERGENT** (ghosting/vignetting/arraying classification). Separately, **3/9 finalists' Phase 1 blur reference (`blur_sweep.csv`) was found STALE** (grid_N=2048 vs. the corrected grid_N=4096 default) -- a distinct finding, not folded into the classification above; see Finding 2 below.

## Comparison table

| finalist | a_hole (um) | M | P1 ghost margin (phi=0) | P1 n_active_pairs | P2 n_included | P2 n_resolved_peaks | ghost agree | vign agree | array vs single r_EE_50 (um) | arraying agree | blur_sweep stale | class |
|---|---:|---:|---:|---:|---:|---:|:---:|:---:|---:|:---:|:---:|:---:|
| M0.0_rectangular | 2000 | 0 | inf | 0.0 | 1 | 1 | YES | YES | 3.664 vs 3.664 | YES | STALE | **CONFIRMED** |
| M1.0_jittered_lattice | 1250 | 1 | inf | 0.0 | 1 | 1 | YES | YES | 6.316 vs 6.316 | YES | STALE | **CONFIRMED** |
| M2.0_jittered_lattice | 750 | 2 | inf | 0.0 | 1 | 1 | YES | YES | 8.070 vs 8.070 | YES | ok | **CONFIRMED** |
| M3.0_jittered_lattice | 750 | 3 | inf | 0.0 | 1 | 1 | YES | YES | 11.343 vs 11.343 | YES | ok | **CONFIRMED** |
| M4.0_archimedean_spiral | 600 | 4 | inf | 0.0 | 0 | 0 | YES | YES | nan vs 12.144 | YES | ok | **CONFIRMED** |
| M5.0_archimedean_spiral | 600 | 5 | inf | 0.0 | 0 | 0 | YES | YES | nan vs 16.340 | YES | ok | **CONFIRMED** |
| M6.0_jittered_lattice | 500 | 6 | inf | 0.0 | 1 | 1 | YES | YES | 15.630 vs 15.630 | YES | ok | **CONFIRMED** |
| M8.0_jittered_lattice | 400 | 8 | inf | 0.0 | 1 | 1 | YES | YES | 17.446 vs 17.446 | YES | ok | **CONFIRMED** |
| Mglobal_square | 2000 | 0 | inf | nan | 1 | 1 | YES | YES | 3.664 vs 3.664 | YES | STALE | **CONFIRMED** |

## Methodology and tolerances

1. **Ghost separation** (structural + numeric): Phase 1 predicts structurally zero ghosting wherever fewer than 2 holes are simultaneously active under the pupil (`worst_case_ghost_margin=+inf`, `n_active_pairs_phi0=0`) -- confirmed if Phase 2 also never resolves 2+ distinct retinal peaks there. Where Phase 1 predicts a finite separation, tolerance = 2 grid pixels (`2*dx`), reusing `array_optimization/stage0_ghost_validation/validate_ghost_formula.py`'s own established, justified convention for peak-separation measurements, not a new invention.

2. **Vignetting** (structural, across phi): same logic as (1), applied at every phi in Phase 1's own `evaluation/vignetting_robustness.py::phi_grid()` (-25 to 25 deg, step 5 deg, 11 values) -- a strict superset of the task's named phi = 0/+-10/+-20/+-25, extended because Phase 1's only finalist with a non-infinite vignetting margin (rectangular, M=0D) has its one active pair at phi=+-5deg specifically, outside the named list.

3. **Blur** (implicit single-hole assumption): two SEPARATE checks, not conflated -- (3a) does arraying multiple holes change blur beyond a FRESH single-hole prediction at the SAME grid resolution (tolerance: 5% relative, half this project's own established +-10% R1-diameter-band feasibility tolerance, or 1 grid pixel, whichever is larger); (3b) is Phase 1's actual blur REFERENCE (`new_sweeps/blur_sweep.csv`) itself stale relative to the current, more accurate grid resolution -- see Finding 2.

## Findings

### Finding 1 -- ghosting and vignetting predictions CONFIRMED for all 9 finalists

Every finalist's structural ghost/vignetting prediction (0 or 1 active hole under the pupil at every tested phi, hence no possible resolvable ghost) was reproduced by real ASM propagation + peak detection: Phase 2 never resolved 2 distinct retinal peaks for any finalist, at any of the 11 gaze angles tested. The one finalist with a genuinely non-trivial case -- `rectangular` (M=0D), where 2 holes become simultaneously active at phi=+-5deg -- is a clean, exact confirmation of a boundary-case prediction: the corrected ghost formula gives Delta_r = s*M/(P0-M) = 0 IDENTICALLY at M=0 (independent of pair distance s), and the real propagation's own demagnification factor `(v_r-v_f)/v_f` was measured to be EXACTLY 0.0 at M=0D too -- so real off-axis holes produce ZERO retinal shift, and the two illuminated holes' copies land on exactly the same retinal position, resolving as 1 peak, not 2. This is not merely 'small enough to not matter' -- it is the same zero, confirmed independently by the full propagation.

### Finding 2 -- Phase 1's blur reference is stale for large apertures (a_hole >= 1250um in this finalist set)

- **M0.0_rectangular** (a_hole=2000um, M=0D): `blur_sweep.csv` (grid_N=2048) reports r_EE_50=7.328um; a fresh computation at grid_N=4096 (`array_psf_envelope.py`'s own corrected default, its Defect-1 fix) gives r_EE_50=3.664um -- a 100% difference, confirmed by directly recomputing `phase2_retina.run_pipeline_point` at both grid resolutions (see `compare_phase1_vs_phase2.py`'s own docstring). Far outside the '0.05-2.1%, ordinary grid-refinement convergence' `array_psf_envelope.py`'s own docstring reports for its spot-checked points -- which did not include apertures this large.
- **M1.0_jittered_lattice** (a_hole=1250um, M=1D): `blur_sweep.csv` (grid_N=2048) reports r_EE_50=7.328um; a fresh computation at grid_N=4096 (`array_psf_envelope.py`'s own corrected default, its Defect-1 fix) gives r_EE_50=6.316um -- a 16% difference, confirmed by directly recomputing `phase2_retina.run_pipeline_point` at both grid resolutions (see `compare_phase1_vs_phase2.py`'s own docstring). Far outside the '0.05-2.1%, ordinary grid-refinement convergence' `array_psf_envelope.py`'s own docstring reports for its spot-checked points -- which did not include apertures this large.
- **Mglobal_square** (a_hole=2000um, M=0D): `blur_sweep.csv` (grid_N=2048) reports r_EE_50=7.328um; a fresh computation at grid_N=4096 (`array_psf_envelope.py`'s own corrected default, its Defect-1 fix) gives r_EE_50=3.664um -- a 100% difference, confirmed by directly recomputing `phase2_retina.run_pipeline_point` at both grid resolutions (see `compare_phase1_vs_phase2.py`'s own docstring). Far outside the '0.05-2.1%, ordinary grid-refinement convergence' `array_psf_envelope.py`'s own docstring reports for its spot-checked points -- which did not include apertures this large.

**Diagnostic evidence this is a grid ARTIFACT, not just coarser-but-valid sampling**: 3 finalists with DIFFERENT apertures (M0.0_rectangular, M1.0_jittered_lattice, Mglobal_square) all report the EXACT SAME `blur_sweep.csv` r_EE_50 value (7.327531um, matching to 6 decimal places) at grid_N=2048. Real single-hole diffraction physics has no reason to give identical blur radii for different aperture sizes; a shared, aperture-independent value is the signature of `array_psf_envelope.py`'s own documented Defect-1 mechanism -- "r_max_lens ... is a pure function of the GRID (wavelength, f_eye, dx) ... independent of aperture, M, or pitch" -- dominating the measurement at grid_N=2048 for apertures large enough to be affected, rather than genuine aperture-dependent diffraction structure.

**This does not change any of these finalists' SAFE classification** (each affected finalist here is at M=0D or M=1D, where the predicted ghost separation from the corrected formula is either exactly 0 (M=0D) or small enough that Phase 2 measured no resolvable second peak regardless), but it means `new_sweeps/blur_sweep.csv` should be regenerated at grid_N=4096 before its blur reference is trusted for any M/aperture combination using apertures in this size range (>=1250um) or larger.

### Finding 3 -- a real bug found and fixed while building this confirmation pass itself

`run_full_physics.py`'s first implementation reused `array_psf_envelope.array_psf()`'s own auto-sized crop (margined by `single_r_EE_98_um`) for the roll-and-sum. For (a_hole_um=2000, M=0D) specifically, this crop badly truncated real PSF energy structure beyond its own r_EE_98 radius -- measured r_EE_50 swung from 2.28um (cropped) to the correct 3.66um (uncropped, matching `single_hole_psf()`'s own reported value exactly) depending on crop size, a discontinuity `array_psf_envelope.py`'s own `crop_vs_full_grid_check()` never caught because it does not test this specific (a_hole, M) pair. Fixed by removing the crop entirely for this script (only 9 finalists, not a large sweep -- cropping's whole motivation) -- see `run_full_physics.py::custom_array_psf()`'s own comment for the full diagnosis. Caught by directly comparing measured r_EE_50 against `single_hole_psf()`'s own reported value before trusting any Part 2 output, not assumed correct because the algorithm mirrors a validated function.

