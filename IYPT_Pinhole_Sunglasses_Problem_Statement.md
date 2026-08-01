# IYPT Problem: Pinhole Sunglasses — Problem Statement, Requirements, and Consolidated Research

## 1. Official Problem Statement (IYPT 2027)

> "Investigate the optimal arrangement of pinholes in an opaque film to produce sunglasses that reduce light intensity and help correct short-sightedness."

This is a **dual-objective optimization problem**, not a single-variable one. It is not asking you to explain the pinhole effect (that is prerequisite background); it is asking you to *design* an array — meaning your final deliverable must be a specification (hole diameter, hole count, pitch, pattern) with a stated performance tradeoff curve, not a single "optimal aperture" number.

Two independent requirements are embedded in the statement, and treating them as one variable is the most common failure mode:

- **R1 — Optical correction**: reduce the blur experienced by a myopic eye viewing distant objects.
- **R2 — Intensity attenuation**: reduce total transmitted light intensity by a target amount (sunglasses function).

These are governed by different design variables (hole diameter controls R1; total open area / hole count controls R2), and the core finding of a strong report is *how much freedom exists to satisfy R2 without degrading R1*, and where that freedom runs out.

---

## 2. Requirements Breakdown

| ID | Requirement | Governing variable(s) | Status |
|----|---|---|---|
| R1 | Minimize retinal blur for a myopic eye at distant vision | hole diameter a_hole | Model built, needs numerical refinement (§4) |
| R2 | Achieve a specified light transmission/attenuation target | N, a_hole, pitch | Formula defined, not yet solved jointly with R1 |
| R3 | Avoid visible double-imaging (ghosting) between adjacent holes | pitch s | Constraint derived, not yet combined with R2 |
| R4 | Maintain acceptable field of view / peripheral vision | array coverage, hole layout | Not yet modeled |
| R5 | Maintain acceptable performance across gaze angles (eye rotation vs fixed frame) | vertex distance, pupil-hole overlap | Vignetting model identified, not yet derived |
| R6 | Result must be validated experimentally, not just derived | artificial eye rig, resolution target, photometer | Design sketched, not built |
| R7 | Report must connect blur radius to an actual visual-acuity claim | acuity conversion | Not yet modeled |

A complete solution requires closing R2 through R7, all currently open or partially open.

---

## 3. Theoretical Framework — Formula Inventory (as developed so far)

### 3.1 Image formation
1. Thin lens equation: **1/v_f = 1/f − 1/u** — establishes where the myopic eye actually focuses, for object distance u. *(Solid.)*

### 3.2 Pre-eye propagation (pinhole film → cornea, gap d_gap)
2. Fresnel number of the gap: **N_F,gap = R_hole² / (λ d_gap)**, R_hole = a_hole/2 — the regime selector; must be computed before choosing a diffraction model. *(Solid.)*
3. Quadrature estimate of effective spot size: **a_eff ≈ √[a_hole² + (2.44λd_gap/a_hole)²]** — *heuristic only*, breaks down near the actual optimum aperture where the correction is ~15–20%, not negligible.
4. Effective aperture after natural pupil clipping: **a_stop = min(a_eff, D_pupil)**. *(Logic solid; depends on fixing #3.)*

### 3.3 Eye imaging (aperture a_stop → retina, distance v_r)
5. Geometric blur radius: **r_geo = (a_stop/2)·|v_r − v_f|/v_f** *(Solid, paraxial.)*
6. Fraunhofer diffraction — first-null radius: **r_diff = 1.22 λ v_r / a_stop** *(Solid but incomplete — a null radius, not an energy-based size.)*
7. Combined blur, RSS: **r_total = √(r_geo² + r_diff²)** — *identified as physically wrong*; true combination is a convolution, not a sum of radii.
8. Optimal aperture (from flawed #7): **a\* = √(2.44 λ v_r v_f / |v_r − v_f|)** — needs re-derivation once §3.4/§3.5 replace #7.

### 3.4 Fraunhofer diffraction — exact intensity and encircled energy
- Airy intensity: **I(r) = I₀ [2J₁(x)/x]²**, x = πar/(λv_r)
- Encircled energy (closed form): **EE(x) = 1 − J₀²(x) − J₁²(x)**
- At the first null (x = 3.8317): EE ≈ 0.838 — i.e., the "blur radius" in formula #6 only captures 83.8% of the energy; the rest sits in visible rings that degrade contrast independent of resolution.
- Design metric: define **r_EE(P)** = radius enclosing energy fraction P (e.g., P = 0.5, 0.8, 0.9), inverted numerically from EE(x). Use this instead of r₁ as the working diffraction blur size.

### 3.5 Fresnel (near-field) diffraction — the actual pre-lens regime
- On-axis intensity: **I(0,z) = 4I₀ sin²(πN_F/2)** — oscillatory, not monotonic; confirms simple quadrature blending (formula #3) is inadequate near your working N_F.
- Off-axis exact form (Lommel functions): **I(r,z) = I₀[U₁²(u,v) + U₂²(u,v)]**, with u = 2πN_F, v = 2πRr/(λz), U₁, U₂ defined via Bessel-function series — exact but impractical by hand; intended to be solved numerically.
- Practical method: **angular spectrum propagation** (FFT of aperture field × free-space transfer function → inverse FFT) to get the exact complex field at the cornea for any N_F. No closed-form encircled energy in the near field — must integrate the propagated intensity numerically.

### 3.6 Corrected effective-aperture pipeline (replaces §3.2–3.3 shortcuts)
1. Propagate the physical hole's field over d_gap using angular-spectrum Fresnel propagation → complex field at cornea.
2. Feed that field (not an idealized top-hat) into the eye lens's Fraunhofer imaging → retinal diffraction PSF via Fourier transform.
3. Convolve that PSF with the geometric defocus disk (radius r_geo) — physically correct, replacing RSS formula #7.
4. Compute EE(P) on the convolved result → r_EE(P) is the honest total blur-radius metric.
5. Minimize r_EE(P) over a_hole numerically — closed-form a\* is unlikely to survive this; report a swept curve, not a single value.

### 3.7 Multi-hole array — ghosting constraint (R3)
- Retinal image shift between two holes separated by pitch s: **Δr_retina ≈ s · v_r / d_gap**
- No-ghosting condition: **s < r_EE(P) · d_gap / v_r**

### 3.8 Photometry (R2)
- Open-area transmission fraction: **T = N·(πa_hole²/4) / A_total**
- Transmitted intensity: **I_out = T · I_in**
- Solve for N given a_hole fixed by §3.6 and a target T from a stated attenuation spec.

### 3.9 Still not derived (required to close R4–R7)
- **R4/R5 vignetting**: overlap area of two offset circular apertures (pupil vs. hole) as a function of eye rotation angle φ and vertex distance — standard circle-overlap geometry, not yet written down.
- **R7 acuity conversion**: retinal blur radius → angular blur (divide by v_r) → compare against ~1 arcmin normal-eye resolution criterion → Snellen/logMAR equivalent claim.
- **Polychromatic correction**: all λ-dependent formulas above (#3, #6, #8, §3.4, §3.5) are monochromatic; need either photopic-weighted (V(λ)) averaging or a stated sensitivity bound across 400–700 nm.
- **Clinical parametrization**: convert myopia severity from diopters (D = 1/far-point distance) into v_f via the lens equation, so a_hole(u) can be reported against clinical myopia grade rather than an abstract u.

---

## 4. Experimental Plan (R6)

**Artificial eye rig**: converging lens (f ≈ 15–20 mm) with sensor/screen mounted behind the paraxial focal plane by a controlled offset (simulates chosen myopia diopter). Fixed accommodation state — no biological variability.

**Variables to sweep**:
- a_hole (single-hole trials, several diameters bracketing the theoretical optimum)
- N and pitch (array trials, fixed a_hole at its optimum, vary layout)
- d_gap (confirm whether pre-lens propagation correction is measurable, per §3.2/§3.5)
- u / simulated myopia severity

**Measurements**:
- Image sharpness: USAF 1951 resolution chart, MTF extraction via slanted-edge/line-target method (OpenCV/numpy pipeline)
- Transmitted intensity: lux meter or photodiode behind the rig, calibrated against §3.8
- Ghosting check: visual/photographic confirmation of single vs. double imaging at varying pitch, cross-checked against §3.7's predicted threshold

**Output**: Pareto plot of blur metric (r_EE(P)) vs. transmission (T) across candidate array designs, identifying the design meeting the R2 attenuation target at minimum blur cost — this plot is the deliverable, not a single formula.

---

## 5. Known Sanity-Check Data (from literature, for validating your model)

- Aperture < 0.75 mm: significant diffraction blurring reported clinically.
- Aperture > 2.0 mm: no meaningful diffraction-related degradation reported.
- Your derived a\*/a_hole optimum should fall inside or near this bracket; if it doesn't, re-examine assumptions before trusting the model.

---

## 6. Open Risks / Things to Resolve Before Finalizing

- Confirm whether the RSS-based effective aperture (§3.2, formula #3) or the full angular-spectrum propagation (§3.5) is *necessary* for your actual d_gap and a_hole range, or whether the discrepancy is small enough to justify the cheaper formula with a stated error bound — check numerically, don't assume.
- P-dependence of a\*: report the optimal aperture for at least P = 0.5, 0.8, 0.9 rather than presenting one number as "the" optimum.
- Whether R2's attenuation target is achievable at all within the no-ghosting pitch constraint (§3.7) — if not, this is a genuine physical limit worth reporting as a finding.
- Coherence assumption: convolution in §3.6 step 3 is valid only for spatially incoherent, extended-source imaging (your actual viewing condition) — state this explicitly, it is what justifies treating geometric and diffraction blur as separably convolved at all.
