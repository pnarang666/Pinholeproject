# Pinhole Project — Comprehensive System Analysis & Architecture Guide

## 1. Project Context & High-Level Objective
The **Pinhole Project** is a research-grade Fourier-optics simulation and theoretical/experimental framework designed to solve the **IYPT 2027 Problem**:
> *"Investigate the optimal arrangement of pinholes in an opaque film to produce sunglasses that reduce light intensity and help correct short-sightedness."*

This is a **dual-objective optimization problem**:
- **R1 (Optical Correction)**: Minimize retinal blur for a myopic eye viewing distant objects (governed by hole diameter $a_{\text{hole}}$).
- **R2 (Intensity Attenuation)**: Achieve a specified light transmission target (sunglasses function, governed by open-area fraction $T$, hole count $N$, and pitch $s$).
- **Derived Constraints (R3–R7)**: No ghosting/double-imaging between adjacent holes ($s < r_{\text{EE}} \cdot d_{\text{gap}} / v_r$), field-of-view vignetting across gaze angles, visual acuity conversion (Snellen/logMAR), and experimental validation via an artificial eye rig.

---

## 2. Optics & Physical Modeling Architecture

```
[ Plane Wave / Input Field ]
            │
            ▼
[ Circular Pinhole Mask U0(x,y) ]  (Diameter a_hole)
            │
            ▼
[ 1st ASM Propagation (gap d_gap) ]  (Exact Scalar Angular Spectrum Method)
            │
            ▼
[ Corneal Plane Field U_cornea ]    (Stage 1 / Stage 1_v2 Analyzer)
            │
            ▼
[ Pupil Clipping Mask (D_pupil) ]
            │
            ▼
[ Thin Lens Phase Shift (P0 = 60D) ]
            │
            ▼
[ 2nd ASM Propagation (dist v_r) ]  (Axial Myopia Model: v_r = L_ax = n'/(P0 - M))
            │
            ▼
[ Retinal Intensity I_retina(x,y) ]  (Stage 2 Retinal Point Spread Function)
            │
            ▼
[ Human Vision & Metrics Pipeline ]  (Stage 3: RMS radius, r_EE, MTF, Photometry, CSF, Acuity)
```

### Core Physics Principles
1. **Corneal Propagation (Stage 1 / Stage 1_v2)**:
   - Uses the exact scalar **Angular Spectrum Method (ASM)** with Matsushima & Shimobaba band-limiting to eliminate grid-aliasing artifacts.
   - Evaluates the gap Fresnel number $N_F = a_{\text{hole}}^2 / (4 \lambda d_{\text{gap}})$ to classify near-field vs. transition vs. far-field regimes.
   - Eliminates ring-hopping detection artifacts via sub-bin parabolic refinement and stopping at genuine local minima.

2. **Eye Imaging & Retinal Propagation (Stage 2)**:
   - **Axial Myopia Model**: Fixed eye power $P_0 = 60\text{ D}$; myopia $M$ diopters expands axial length $L_{\text{ax}} = n' / (P_0 - M)$, pushing the retina to $v_r = L_{\text{ax}}$.
   - **Defocus via 2nd ASM**: Replaces simple FFT (which falsely projects to back focal plane $f$) with a 2nd ASM propagation over distance $v_r$. Geometric defocus falls out automatically from wave optics without needing artificial Root-Sum-Square (RSS) approximations!
   - Validated against closed-form Airy encircled energy $EE(x) = 1 - J_0^2(x) - J_1^2(x)$ at zero defocus ($M=0, d_{\text{gap}}=0$).

3. **Human Vision, Photometry & Pareto Optimization (Stage 3 & 3a)**:
   - Evaluates multiple metrics: Encircled energy radius $r_{\text{EE}}(P)$, **RMS spot radius**, Strehl ratio, MTF50/10 cutoffs.
   - Photometric chain: Scene luminance ($10,000\text{ cd/m}^2$) $\rightarrow$ Retinal irradiance $\rightarrow$ Photon flux density ($S \propto \sqrt{\Phi}$).
   - Acuity prediction via MTF cutoffs ($\text{MAR} = 30 / f_{\text{cutoff}}$) and core FWHM.

---

## 3. Key Findings & Scientific Breakthroughs

### A. The "Discrepancy Resolution" (RMS Radius vs. $r_{\text{EE}}$)
- Pure blur metrics ($r_{\text{EE}}(50\%)$, MTF50) predict an optimal pinhole diameter of **$300\text{--}400\,\mu\text{m}$**.
- Commercial/clinical pinhole glasses use **$800\text{--}1200\,\mu\text{m}$** (or $940\text{--}1750\,\mu\text{m}$ for clinical occluders).
- **Discovery**: **RMS spot radius** is the single metric whose optimum ($964\,\mu\text{m}$) closely tracks clinical products (gap of only $54\,\mu\text{m}$). RMS radius weights intensity by $r^2$, heavily penalizing broad, faint Fresnel-ring skirts produced by small apertures.

### B. Strehl Ratio is Ill-Posed in Defocused Near-Fields
- Peak retinal intensity oscillates with propagation distance $v_r$ due to Fresnel zone interference ($I(0,z) = 4I_0 \sin^2(\pi N_F/2)$).
- Consequently, Strehl ratio exceeds 1.0 for **55%** of tested configurations, rendering it an unstable optimization metric for pinhole eye systems.

### C. Classical RSS Approximation ($r_{\text{total}} = \sqrt{r_{\text{geo}}^2 + r_{\text{diff}}^2}$) Divergence
- Handbooks' deprecated closed-form formula $r_{\text{total}}$ diverges from exact wave propagation by **up to 192%** (worst at mild myopia $M=1\text{D}$).
- Blur sources combine by complex field convolution, not root-sum-square quadrature.

### D. Multi-Objective Pareto Front
- Almost every aperture from $300\,\mu\text{m}$ to $2000\,\mu\text{m}$ is Pareto-optimal when trading off blur ($r_{\text{EE}}$) vs. light throughput. Commercial designs prioritize brightness/transmittance over absolute minimum blur.

---

## 4. Codebase Directory Map

| Directory / File | Status & Purpose |
|---|---|
| `stage1_v2/` | **Corneal Fresnel Field Analyzer** (Streamlit dashboard + `physics.py`). Primary tool for gap-stage analysis. |
| `stage1/` | Unmodified reference build of Stage 1 (kept for historical reproducibility). |
| `stage2/` | **Retinal Propagation & Myopia Model** (`sweep_myopia.py`, `phase2_retina.py`, `validation_gate.py`). |
| `stage3_human_vision/` | **Human Vision & Photometry** (`metrics.py`, `photometry.py`, `contrast.py`, `pareto.py`, `run_stage3.py`). |
| `stage3a/` | Multi-percentile encircled energy & array pitch constraint optimizations (`transmission.py`, `combine_and_select.py`). |
| `model_comparison/` | Model 1 vs. Model 2 vs. Model 3 (classical formulas) benchmarking and clinical acuity checks. |
| `fresner1.py`–`4.py`, `test1.py` | Early single-file exploratory scripts and interactive matplotlib sliders. |
| `IYPT_Pinhole_*.md` | Official problem statement, master formula set, and pipeline reference documents. |

---

## 5. Next Steps & Roadmap

1. **Multi-Hole Array Optimization (R2 + R3 Joint Solution)**:
   - Combine $a_{\text{hole}}$ selection with array pitch $s$ and open-area fraction $T$ to satisfy light attenuation while respecting the no-ghosting bound $s < r_{\text{EE}} \cdot d_{\text{gap}} / v_r$.
2. **Polychromatic Pass**:
   - Aggregate 5-wavelength spectrum ($400\text{--}700\text{ nm}$) weighted by photopic luminosity function $V(\lambda)$.
3. **Gaze-Angle & Vignetting Model (R4/R5)**:
   - Model lateral offset between natural pupil and pinhole mask under eye rotation angle $\phi$.
4. **Experimental Rig Verification (R6)**:
   - Build physical test bench (converging lens + sensor stage) with USAF 1951 chart to validate MTF and acuity predictions.
