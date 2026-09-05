# Array_Design

Everything in this project that bears on **multi-hole pinhole array** design, in one
place. Created 2026-08-14 by consolidating two folders that had been developed
separately and never run against each other, plus a reference copy of the single-hole
result every array design starts from.

Read `ANALYSIS.md` for what is wrong or missing with all of this, and
`RECOMMENDATION.md` for the current best-defensible design region. Neither is a
manufacturing specification — no array-specific prediction in here has been tested
against a physical sample.

---

## What is in each subfolder, and where it came from

### `photometry/` — how much light gets through, and how many holes are active
Moved verbatim from the project root's `stage_array/` (`git mv`, history preserved).
The brightness / N_eff model: it counts, by exact discrete lattice enumeration rather
than an area-fraction average, how many holes are inside the pupil as the pupil moves
over the hole lattice, and converts that to retinal illuminance.

| file | what it is |
|---|---|
| `array_photometry.py` | the model. Unmodified except for path references and one **SUPERSEDED** banner on `no_ghost_max_pitch()` (see below). |
| `array_illuminance_results.csv` | N_eff / E_rel for the two real patent pitches + a fine-pitch case |
| `array_sweep_full.csv` | 360-row aperture × pitch × {square, hex} N_eff sweep |
| `noghost_constraint.csv` | **stale, kept as the record**: pre-lens-wavelength-fix blur radii *and* the superseded pitch formula |
| `noghost_constraint_corrected.py` / `.csv` | added here: the same table with post-fix blur radii and the corrected geometry |

### `ghosting/` — whether the copies each hole makes are perceptible
Moved verbatim from the project root's `array_ghosting_theory/`. The full Pass 1 → 2 → 3
history is preserved in `RESULTS.md` exactly as it was written, including the two
conclusions later overturned; Pass 4 is appended, not substituted.

| file | what it is |
|---|---|
| `THEORY.md` | the derivation, unchanged, **plus an appended Addendum** recording that its Eq. (1) is wrong |
| `RESULTS.md` | Passes 1–3 unchanged, **plus an appended Pass 4** |
| `ghosting_regime.py` | the A/B/C classifier as Passes 1–3 ran it (legacy Eq. 1). Left runnable and unmodified apart from import paths. |
| `harmonic_analysis.py` | harmonic-series extension, unmodified apart from import paths |
| `metrics_mtf.py`, `contrast.py`, `contrast_barten.py` | radial MTF; the project's heuristic CSF; the real Barten (1999) CSF (needs `pip install colour-science`) |
| `ghosting_sweep*.csv` | the three original sweeps (Passes 1, 2, 3) |
| `ghosting_regime_map*.png`, `harmonic_margin_profile.png` | the Pass 1–3 plots `RESULTS.md` cites. They had never been committed anywhere in the project; recovered from `~/Downloads` (timestamps match the Pass 1–3 CSVs) and placed here. Pre-fix, legacy-formula — historical. |
| **added here** | |
| `ghost_separation.py` | both separation formulas + the first-principles derivation of each |
| `delta_r_derivation_check.py` / `.csv` | ray-trace, wave-optics and M=0 verification of which one is right |
| `corrected_regime.py` | A/B/C classification with a selectable separation model + a PSF cache; self-checks against `ghosting_regime.py` and `harmonic_analysis.py` |
| `rerun_corrected_sweep.py` | the Pass-4 side-by-side re-run |
| `ghosting_sweep_corrected_formula.csv`, `ghosting_myopia_robustness_corrected.csv` | its outputs |

### `single_hole_reference/` — the starting constraint
A **copy** (not a move — `stage2_fixed/` and `singleilluminate/` stay exactly where they
are) of the corrected R1 sweep, i.e. the single-hole diameter result every array design
builds on. Source: `stage2_fixed/outputs/postfix_sweep_audit/` and
`stage2_fixed/outputs/before_after_optimum_comparison_audit.csv`, both produced *after*
the lens-wavelength fix (`stage2_fixed/LENS_WAVELENGTH_FIX.md`).

Per-M blur optimum in that file — **400–750 µm**, decreasing with myopia, not the
superseded 300–400 µm:

| M (D) | 1 | 2 | 3 | 4 | 5 | 6 | 8 |
|---|---|---|---|---|---|---|---|
| optimum diameter (µm) | 700 | 750 | 600 | 500 | 500 | 400 | 400 |
| r_EE_50 there (µm) | 7.3 | 8.0 | 10.6 | 12.0 | 13.3 | 14.5 | 17.9 |

### Top level — the joint analysis added by this consolidation

| file | what it is |
|---|---|
| `joint_design_space.py` | all three constraints on one (diameter × pitch) plot at M = 1, 4, 8 D |
| `joint_design_space.png`, `..._M1/M4/M8.png`, `..._grid.csv` | its outputs. Re-run figures only with `--replot`. |
| `alignment_fractions.png` / `.csv` | what the pupil actually sees (0 / 1 / ≥2 holes) as it moves, square vs hex |
| `pupil_sensitivity.csv` | how the pitch limits move with pupil diameter |
| `array_psf_envelope.py` / `.csv` | the multi-hole retinal PSF (THEORY.md Eq. 2), computed for the first time |
| `array_psf_shift_invariance_check.csv` | the check that Eq. (2)'s "identical, merely shifted copies" assumption holds |
| `multi_hole_blur_sweep.py` / `.csv` | `array_psf()` swept over the full (aperture × pitch × myopia × alignment × packing) grid, not just six spot checks — the true multi-hole blur ANALYSIS.md F4/I1 needed |
| `ghosting_risk.py` / `ghosting_risk_sweep_{square,hex}.csv` | a continuous risk = P(N_eff≥2) × perceptual margin, replacing Regime A's reliance on the alignment minimum (ANALYSIS.md F2) — reported alongside, not instead of, the binary A/B/C classification |
| `optimise.py` / `optimise_grid.csv`, `optimise_best_per_M_packing.csv`, `optimise_sensitivity.csv` | a joint (aperture, pitch) optimiser combining blur + brightness + ghosting risk into one named, weighted cost, with a sensitivity sweep over every weight — see RECOMMENDATION.md's Addendum for what it found |

---

## How the three pieces relate

A distant point of light reaches the retina through **every hole that is inside the
pupil at that instant**. That single sentence generates all three constraints, and they
are coupled through one quantity — **N_eff**, the number of holes in the pupil:

```
             hole diameter  a                          pitch  s
                    |                                      |
        ┌───────────┴────────────┐            ┌────────────┴─────────────┐
        │  DIAMETER  (blur)      │            │  N_eff = how many holes  │
        │  single-hole r_EE(P)   │            │  are in the pupil now    │
        │  minimised at 400-750µm│            └────┬────────────────┬────┘
        └───────────┬────────────┘                 │                │
                    │                     N_eff = 0│                │N_eff ≥ 2
                    │                     BRIGHTNESS│                │GHOSTING
                    │                     view goes │                │copies at
                    │                     black     │                │Δr = s·M/(P0−M)
                    └─────── only describes ────────┘                │
                             the array's blur                        │
                             while N_eff ≤ 1  ←──────────────────────┘
```

* **Diameter** sets the blur of *one* hole: too small and diffraction dominates, too
  large and defocus does. `single_hole_reference/` fixes that trade at 400–750 µm.
* **Pitch** does not affect one hole's blur at all. It sets N_eff, and N_eff decides
  which of the other two constraints bites: at large pitch the pupil is sometimes empty
  (dark), at small pitch it always holds several holes (ghosting).
* The two failure modes are driven by **opposite ends of the same distribution** —
  brightness by the fewest holes, ghosting by the most — and the pupil alignment that
  decides which you get is set by where the wearer's eye happens to be, not by the
  designer. `alignment_fractions.png` is the honest picture of that trade.
* The coupling back to diameter: the single-hole optimum is only the *array's* blur
  while at most one hole is active. With several active, the blur is set by the
  illuminated hole cluster instead and is 7–17× worse (`array_psf_envelope.csv`) —
  which is why the diameter band is drawn dashed rather than solid over most of the
  pitch axis in `joint_design_space.png`.

---

## Running it

```bash
# settle the formula question (~25 s)
cd ghosting && python3 delta_r_derivation_check.py
# Pass 4 side-by-side sweep (~40 s)
python3 rerun_corrected_sweep.py
# the multi-hole PSF (~2 min)
cd .. && python3 array_psf_envelope.py
# the joint design space (~2.5 min; --replot skips the optics and redraws only)
python3 joint_design_space.py
```

Every one of these prints the resolved path of `phase2_retina` and asserts it is
`stage2_fixed/`'s post-lens-wavelength-fix copy before computing anything. They need
`numpy`, `pandas`, `matplotlib`, and `colour-science`.

## What this consolidation changed outside this folder

Only paths, never logic: `master_dashboard/wrappers.py` + `registry.py` and
`master_compilation/compile_master_results.py` + `dashboard.py` referenced
`stage_array/` and `array_ghosting_theory/` by name and were repointed here (the
`master_dashboard` array-ghosting tab was re-run after the move and still works).
`stage1_v2`, `stage2_fixed`, `stage3a`, `stage3_human_vision`, `stage4_human_vision`,
`R7acuity`, `model_comparison`, `brightness_reconciliation` and `singleilluminate` were
not touched.
