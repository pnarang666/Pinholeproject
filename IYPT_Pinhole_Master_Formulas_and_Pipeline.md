# IYPT Pinhole Sunglasses — Master Formula Set, Simulation Architecture, and Processing Pipeline

## 0. Critical correction before anything else

Your submitted blueprint has one architectural bug that matters more than any single formula, because fixing it eliminates most of the earlier approximation chain (geometric blur formula, RSS combination, separate encircled-energy convolution step) rather than adding to it.

**The bug**: Step "Fraunhofer Focal FFT Engine → Propagates to Retinal Plane" is not correct as stated. A single 2D FFT after the lens quadratic-phase multiplication gives you the field at the lens's **own back focal plane** (distance f from the lens, or equivalently the far field for collimated/infinite-conjugate input). The retina sits at v_r, and for a myopic eye v_r ≠ f (that mismatch is the entire disease). A plain FFT does not know about v_r — it silently assumes you want the field exactly at focus. If you feed it into your pipeline as-is, you will get the sharp Airy pattern at the *wrong plane* (the eye's actual focal point, not the retina), which is precisely the plane where the geometric-defocus blur is defined to be zero. You'd be computing a diffraction pattern with no defocus in it at all — the opposite of what the problem needs.

**The fix**: after the lens phase multiplication, do **another Fresnel/ASM propagation**, not an FFT, over the actual physical distance v_r from the lens to the retina. This single change means:

- Geometric blur (old formula r_geo) is no longer a separate formula you compute and combine — it falls out automatically as a *consequence* of propagating the wrong-focal-length wavefront the wrong distance. The defocus is built into the physics, not bolted on.
- The RSS combination (old formula r_total = √(r_geo² + r_diff²)) is no longer needed — you never separated the two blur sources to begin with, so there's nothing to recombine.
- The "convolve Airy PSF with geometric defocus disk" step from the previous derivation is also superseded — that convolution was your best *approximation* to what this exact two-stage ASM propagation now computes directly.

Net effect: replace ASM → pupil clip → lens phase → **ASM(distance = v_r)** → intensity, in place of ASM → pupil clip → lens phase → FFT. This is a one-line change in the pipeline but it is the difference between a model that's structurally wrong at the plane that matters and one that's physically exact (within scalar diffraction theory) end to end.

---

## 1. Problem Statement

> "Investigate the optimal arrangement of pinholes in an opaque film to produce sunglasses that reduce light intensity and help correct short-sightedness." (IYPT 2027)

Dual objective, not single-variable:
- **R1** — minimize retinal blur for a myopic eye viewing distant objects (governed by hole diameter)
- **R2** — achieve a target light-attenuation spec (governed by hole count/open-area fraction)
- Plus derived constraints: no visible ghosting between holes (R3), acceptable field of view (R4), acceptable performance across eye rotation/gaze angle (R5), experimental validation (R6), and translation of blur into an actual visual-acuity claim (R7).

---

## 2. Full Formula Set

### 2.1 Image formation (fixes v_f, the eye's actual focal distance)
**1/v_f = 1/f − 1/u**
Solid, standard thin-lens result. u = object distance, f = eye's actual (pathological, too-short) focal length, v_f = where the eye actually focuses.

### 2.2 Regime selection — Fresnel number
**N_F = a²/(λz)**
Computed separately for (a) the pinhole-to-cornea gap (a = a_hole, z = d_gap) and (b) any other propagation stage in the model. N_F ≫ 1 → near field; N_F ≪ 1 → far field. This number tells you which formula below is legitimate to use at each stage — always compute it before choosing.

### 2.3 Near-field (Fresnel) propagation — Angular Spectrum Method
$$\hat U(f_x,f_y,0) = \mathcal F\{U(x,y,0)\}$$
$$H(f_x,f_y,z) = \exp\left(i\frac{2\pi}{\lambda}z\sqrt{1-\lambda^2(f_x^2+f_y^2)}\right),\quad f_x^2+f_y^2 \le 1/\lambda^2 \text{ (else } H=0\text{, evanescent cutoff)}$$
$$U(x,y,z) = \mathcal F^{-1}\{\hat U(f_x,f_y,0)\cdot H(f_x,f_y,z)\}$$
$$I(x,y,z) = |U(x,y,z)|^2$$
This is exact (within the scalar, non-vector-field approximation) for **any** z, near or far field — it is the correct general-purpose propagator and should be your default engine rather than switching between near/far-field closed forms, which are special cases of this.

### 2.4 Lens transformation
$$U_{\text{after lens}}(x,y) = U_{\text{before}}(x,y)\cdot\exp\left(-i\,\frac{k}{2f}(x^2+y^2)\right),\quad k = 2\pi/\lambda$$
Uses the eye's actual (pathological) f, not a corrected/ideal f — you are modeling the myopic eye as-is, with the pinhole as the only correction mechanism.

### 2.5 Field at the retina — CORRECTED (replaces plain FFT)
Apply §2.3 (ASM) again, propagation distance = v_r (fixed anatomical distance, ~24 mm eye axial length or ~17 mm depending on your reduced-eye convention — pick one and state it), **not** an FFT assuming the retina sits at the lens's focal plane. Retinal intensity: I_retina(x,y) = |U(x,y,v_r)|².

### 2.6 Analytical reference case — circular aperture, ideal far field only
Valid **only** as a limiting check (collimated aperture directly imaged at true focus, no propagation gap), not as your production model:
$$I(\theta) = I_0\left(\frac{2J_1(ka\sin\theta)}{ka\sin\theta}\right)^2,\qquad r_{\text{diff}} = 1.22\frac{\lambda v_r}{a}$$
Use this only to sanity-check your full ASM pipeline reduces to the Airy result when v_f = v_r (i.e., no defocus) and d_gap → 0. If it doesn't converge to this in that limiting case, your ASM implementation has a bug.

### 2.7 Encircled energy (Fraunhofer closed form, for the same limiting check)
$$EE(x) = 1 - J_0^2(x) - J_1^2(x),\quad x = \pi a r/(\lambda v_r)$$
EE ≈ 0.838 at the first null (x = 3.8317) — confirms a null-radius alone misrepresents energy content. In the general (defocused, near-field-input) case there is no closed form; compute EE numerically by radially integrating I_retina from §2.5.

### 2.8 Effective aperture / quadrature estimate — DEPRECATED
$$a_{\text{eff}} \approx \sqrt{a_{\text{hole}}^2 + (2.44\lambda d_{\text{gap}}/a_{\text{hole}})^2}$$
Keep only as a cheap back-of-envelope cross-check against your §2.3–2.5 numerical result — do not use it as the reported design number. It cannot capture the oscillatory near-field (Fresnel ringing) behavior your own on-axis formula below shows exists.

### 2.9 On-axis Fresnel intensity (shows why §2.8 is inadequate)
$$I(0,z) = 4I_0\sin^2(\pi N_F/2)$$
Oscillates between 0 and 4I₀ as N_F varies — confirms the gap propagation is not a smooth, monotonic spreading that a quadrature sum can represent.

### 2.10 Multi-hole ghosting constraint
$$\Delta r_{\text{retina}} \approx s\cdot v_r/d_{\text{gap}}, \qquad \text{no-ghost condition: } s < r_{\text{EE}}(P)\cdot d_{\text{gap}}/v_r$$
r_EE(P) now obtained numerically from your corrected pipeline's output (§2.5–2.7), not from the old r_total formula.

### 2.11 Photometry
$$T = N\cdot(\pi a_{\text{hole}}^2/4)/A_{\text{total}}, \qquad I_{\text{out}} = T\cdot I_{\text{in}}$$
Solve for N given a_hole fixed by the R1 optimization and T set by the R2 attenuation target.

### 2.12 Still undeveloped — required to close R4, R5, R7
- **Vignetting (R4/R5)**: overlap area of two offset circular apertures (pupil, radius D_pupil/2, vs. pinhole, radius a_hole/2, laterally offset by eye rotation angle φ times vertex distance) — standard circle–circle intersection area formula, not yet written down for this problem.
- **Acuity conversion (R7)**: angular blur = r_EE(P)/v_r → compare against ~1 arcmin normal-eye resolution limit → Snellen/logMAR equivalent. Without this the report never actually claims "corrected short-sightedness" in measurable terms.
- **Polychromatic**: every λ-dependent stage above (§2.3's H, §2.4, §2.6, §2.7, §2.9) is monochromatic. Either run the full pipeline at 3–5 representative wavelengths across 400–700 nm weighted by the photopic luminosity function V(λ) and sum intensities incoherently, or justify a single representative λ with a stated sensitivity bound.

---

## 3. Simulation Architecture (corrected)

```
[ Input Scene / Point or Extended Source ]
           │
           ▼
[ Arbitrary Mask Definition U0(x,y) ]        (Circular, Slit, Hex Grid, N-hole array — your Engine 1 mask library)
           │
           ▼
[ ASM Propagation, distance = d_gap ]        (§2.3 — replaces closed-form a_eff estimate, §2.8)
           │
           ▼
[ Pupil Clipping Mask ]                      (multiply by disk of diameter D_pupil, laterally offset for R5 gaze-angle studies)
           │
           ▼
[ Lens Quadratic Phase, using eye's actual f ]   (§2.4)
           │
           ▼
[ ASM Propagation, distance = v_r ]          (§2.5 — CORRECTED stage, replaces the FFT-to-focal-plane bug)
           │
           ▼
[ Retinal Intensity I(x,y) = |U|² ]
           │
           ▼
[ Radial integration → EE(r) curve → r_EE(P) ]   (§2.7, numerical)
           │
           ▼
[ Sweep a_hole, N, pitch, d_gap, u ]  →  [ Pareto plot: r_EE(P) vs. T ]
```

Retain your existing Engine 1 (arbitrary mask, FFT-based) and Engine 2 (ASM near-field visualizer) as building blocks — they are not wrong in themselves, they were simply wired together in the wrong order at one junction (FFT instead of ASM at the retinal stage). Both are directly reusable once that junction is fixed.

---

## 4. Processing Plan — how to actually run this to solve the problem

1. **Validate the engine before trusting any output.** Set d_gap → 0, v_r = v_f (no myopia, no gap) and confirm the pipeline reproduces the ideal Airy pattern (§2.6) and its closed-form EE (§2.7) to within numerical tolerance. If it doesn't match, the bug is in your code, not the physics — fix before proceeding.
2. **Single-hole sweep (R1).** Fix myopia severity (choose v_f via §2.1 from a stated diopter value), fix d_gap, sweep a_hole across a range bracketing the literature bracket (0.75–2.0 mm) plus finer values below it. For each a_hole, run the full pipeline, extract r_EE(0.5), r_EE(0.8), r_EE(0.9). Plot all three against a_hole — this replaces the closed-form a* formula with an actual numerical optimum, and shows whether "optimal" depends on which energy fraction you care about.
3. **Cross-check against deprecated formulas.** Overlay the old r_total (RSS) curve and the old a_eff quadrature estimate on the same plot as the numerical result. Report where they diverge and by how much — this is a legitimate, useful result for the write-up (quantifying when the cheap formulas are acceptable approximations vs. not), not a discarded step.
4. **Multi-hole array (R2 + R3).** Fix a_hole at the R1 optimum. Sweep N and pitch. For each configuration, compute T (§2.11) and check the no-ghost constraint (§2.10) using the r_EE(P) value from step 2 at that a_hole. Identify the (N, pitch) region satisfying both a target T and the no-ghost bound.
5. **Gaze-angle / vignetting sweep (R4/R5).** Introduce lateral pupil-mask offset in the pipeline (simulating eye rotation φ) and re-run the retinal intensity computation to quantify brightness falloff / partial clipping across the field of view. Derive the circle-overlap formula (§2.12) analytically first, then use it as a fast check against the full numerical sweep.
6. **Polychromatic pass.** Re-run steps 2–5 at 3–5 wavelengths spanning the visible band, weight by V(λ), sum incoherently. Confirm whether the monochromatic-derived optimum shifts meaningfully.
7. **Acuity translation (R7).** Convert the final chosen design's r_EE(P) into angular blur and a logMAR/Snellen-equivalent statement — this is what turns the whole exercise into an answer to "does it correct short-sightedness," which is the actual verb in the problem statement.
8. **Experimental correlation (R6).** Build the artificial-eye rig (converging lens + adjustable sensor offset), image a resolution chart through fabricated hole films at the array parameters identified in steps 2–5, extract MTF, and compare against the simulated r_EE(P)/EE curves. Divergence between simulation and measurement at this stage is itself a finding — report it rather than silently reconciling it.

---

## 5. Open Risks

- The corrected pipeline (§0, §2.5) is the whole point of the redo — do not skip step 1's validation, since a silently wrong retinal-plane propagation invalidates every downstream number without necessarily looking wrong in a plot.
- Numerical resolution/grid sampling in the FFT-based ASM steps must satisfy the sampling theorem for your smallest feature (the pinhole radius) and largest propagation distance (v_r) simultaneously — undersampling here produces aliasing that can masquerade as physically meaningful diffraction structure. Check grid spacing against λ, z, and aperture size before trusting fine ring structure in any output.
- Report the P-dependence of your optimum (§4 step 2) rather than collapsing to one number, and report the gap between deprecated closed-form estimates and the full numerical result (§4 step 3) explicitly rather than omitting the comparison once you have the "better" numbers.
