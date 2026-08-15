# Theory of Multi-Aperture Ghosting in Pinhole Eyewear: Reconciling Geometric Optics, Fourier Theory, and Real-World Evidence

*Citation-fidelity labels: **[EXACT]** = first-principles/exact identity, **[PUBLISHED]** = a specific cited result applied as originally derived, **[SYNTHESIS]** = a novel combination of citations not itself published as a unified result, **[UNTESTED]** = requires physical/psychophysical confirmation this document cannot provide.*

See `RESULTS.md` for the implementation of Eq. (5) below and a real, honest finding about where it currently breaks down (the CSF term).

## 1. Setup and Motivation

A multi-hole array, distance d_gap from the cornea, images a distant scene point through every hole admitting light into the pupil simultaneously. Each hole produces a copy of the same single-hole PSF, laterally shifted on the retina by ordinary parallax. This project's existing criterion (`stage_array/array_photometry.py`, now `Array_Design/photometry/array_photometry.py` — moved, not modified) treats adjacent holes at pitch s as producing retinal images separated by

    delta_r ~= s * v_r / d_gap                                    (1)   [EXACT]

> **Eq. (1) is now known to be WRONG — see the Addendum at the end of this file
> (Array_Design Step 2, 2026-08-14). The label [EXACT] on it did not survive an
> independent re-derivation. Nothing else above or below has been edited; read the
> Addendum before using any number that depends on Eq. (1).**

and calls a design "ghost-free" if delta_r is smaller than the single-hole blur radius r_EE(P). Checked against two real, sold patents (KR 10-2081511, pitch 3.2-4.8mm; CN 201716487U, pitch 0.7-1.2mm; both d_gap~12mm, v_r~22-24mm), this predicts severe violations (30x-400x) for BOTH -- the contradiction motivating this investigation.

## 2. Literature Review

**2.1 Lenslet-array merging theory (Gabor superlens, 1941/2014):** the closest existing precedent for a quantitative multi-channel merging condition -- mismatched, non-integer-ratio pitches in a two-array relay cause channels to "unite to form superfocal lines much smaller in number than the number of microlenses." [PUBLISHED], but this is a two-array relay forming a real image, not a single occluder imaged by the eye's own optics -- cited as evidence this class of problem is solvable, not as a directly transferable formula.

**2.2 Direct evidence ghosting is real -- the most important finding here:** Kim, Park, Park & Chun (2017, J Korean Med Sci 32(5):850-857 -- already in this project's stage4_human_vision/literature.py) directly reports, in real subjects wearing real multi-pinhole glasses: "discomfort from after-images such as honeycomb images, horizontal grating, and double or triple vision" [PUBLISHED, direct quote], significantly worse than single-pinhole glasses. This overturns the original framing -- the question isn't "why don't real products show any ghosting," they DO report it. The real question is why the two specific patents don't address it, and under what conditions it becomes severe.

**2.3 An independent real-world statement of the actual mechanism:** a separate US patent ("Method for facilitating pinhole effect...") states, independent of anything in this project: "If two pinholes are separated by less than the diameter of the pupil aperture, two pencils of ray... form two retinal images. Further, too large of a separation will result in dead spots... while too small... will produce multiple images." [PUBLISHED, direct quote]. This is a discrete precondition (are >=2 holes simultaneously illuminating the pupil), not a continuous comparison -- exactly the N_eff quantity `array_photometry.py` already computes via discrete lattice enumeration. That connection was previously unrecognized as independently corroborated in real patent literature.

**2.4 Periodic-artifact visibility (screen-door effect):** display engineering's standard treatment confirms the right framework -- express periodicity as cycles/degree, determine modulation depth, compare against the human CSF threshold at that frequency [PUBLISHED] -- while confirming a cruder acuity-only rule (like this project's original one) is also a common first-pass approximation in that adjacent field, not a mistake unique to this project.

## 3. Derivation

**3.1 Multi-hole image formation [EXACT]:** for macroscopically-separated holes under ordinary incoherent (daylight) illumination, mutual coherence between paths is negligible (Goodman, Statistical Optics) -- intensities add, not fields:

    I_retina(r) = sum_i I_single_hole(r - i*delta_r) = I_single_hole(r) * Comb_delta_r(r)     (2)

**3.2 The Fourier consequence the crude formula omits entirely [EXACT, convolution theorem]:**

    I_retina_hat(f) = MTF(f) * Comb_{1/delta_r}(f)                                            (3)

The ripple's fundamental frequency f0 = 1/delta_r is attenuated by the single-hole MTF (already computed by this project's Stage 1/3 code). A dense array (small s, large f0) pushes the ripple past where MTF has already rolled off near zero -- smoothing multiple copies into one continuous blur regardless of how badly the old formula is "violated."

**3.3 The discrete precondition [PUBLISHED, Sec 2.3]:** if N_eff <= 1 for a given pupil alignment, there's only one term in the sum -- no periodic structure exists to attenuate or perceive. This is why the sparse KR pitch (worst-case N_eff=0, found earlier in this project) rarely ghosts: most of the time there's no second hole active to ghost against, a different mechanism than MTF smoothing.

**3.4 A refined three-regime criterion [SYNTHESIS]:**

    Imperceptible if:  N_eff(worst-case) <= 1              (Regime A)
                  OR    MTF(f0) < CSF^-1(f0)                (Regime B)

Regime C -- intermediate pitch, N_eff small but >1, f0 not yet high enough -- is the predicted danger zone, giving a candidate mechanism for Kim et al.'s reported symptoms.

## 4. Reconciliation

| Design | Pitch | N_eff | Regime | Matches evidence? |
|---|---|---|---|---|
| KR 10-2081511 | 3.2-4.8mm | 0/1.23 | A | Consistent -- patent never discusses ghosting |
| CN 201716487U | 0.7-1.2mm | 23-28 | B (untested, see RESULTS.md) | Plausible, not independently confirmed |
| Kim et al. 2017 MPH | pitch unstated | likely C | Danger zone | Directly matches real reported symptoms |

This does NOT cleanly vindicate both patents -- it replaces one crude formula with three separately-justified mechanisms, and correctly locates where real problems are actually reported.

## 5. What Theory Alone Cannot Settle

1. Standard CSF thresholds (calibrated for sharp, foveal, normal-viewing-distance gratings) applied to a defocused near-eye ripple pattern is an extrapolation. [UNTESTED] -- **CONFIRMED AS A REAL PROBLEM, not just a worry, by the implementation: see RESULTS.md.**
2. Regime B's applicability to the CN patent has no independent clinical confirmation either way. [UNTESTED]
3. Kim et al.'s "honeycomb/grating" descriptions may reflect consciously seeing the array's physical structure, not strictly the PSF-copy mechanism derived here. [UNTESTED]
4. The exact A/C and B/C boundaries are computable with existing project code but need a CSF model valid below 1 cpd before the B/C split specifically can be trusted (see RESULTS.md) -- the A boundary is solid now.

## 6. Implementation Plan (status: steps 1-3 done, see RESULTS.md; step 4 not started)

1. DONE -- compute f0 and single-hole MTF(f0) using existing MTF machinery.
2. DONE -- `ghosting_regime.py` implements Eq. (5).
3. DONE -- swept (aperture, pitch) across both patents and the intermediate zone; produced `ghosting_regime_map.png`. Found Regime C never triggers with the current CSF implementation -- see RESULTS.md for why.
4. NOT STARTED -- the actual experiment: include a real intermediate-pitch sample and ask subjects if they perceive doubling. Still the one measurement nothing here substitutes for -- and now more clearly necessary, since the CSF-based half of the theory can't currently be trusted to answer the question on its own.

---

## Addendum (Array_Design consolidation, Step 2 — 2026-08-14): Eq. (1) is wrong, and what replaces it

Nothing above has been deleted. This section states what an independent re-derivation
found, so Sections 1–6 can still be read as the record of what was believed at the time.

**The failure.** Eq. (1), `delta_r = s*v_r/d_gap`, does not vanish for an emmetropic
eye. Substituting M=0 (so v_r = v_f = n'/P0 = 22.27 mm) with d_gap = 12 mm gives
`delta_r = 1.86*s` — ghost copies 1.86 pitches apart in an eye with no defocus at all.
A perfectly focused eye images a distant point to one point no matter how many holes
admit light, so any correct expression must vanish there. Eq. (1) does not, so it is
not the separation of ghost images of a distant scene point. (`v_r/d_gap` is the
transverse magnification for an object located *at* the array plane — a different
quantity, and one that is not realised here either, since a 12 mm object distance in
front of a 60 D eye gives a virtual image, nowhere near conjugate to the retina.)

**The replacement.** For a distant on-axis object every ray reaching the eyewear is
parallel to the axis, so the ray admitted by a hole at height h is still at height h at
the eye's refracting plane — d_gap cannot enter. The lens sends every axis-parallel ray
through the rear focal point, so that ray follows `y(z) = h(1 - z/v_f)` and at the
retina (z = v_r) sits at `-h(v_r - v_f)/v_f`. Hence

    delta_r = s * |v_r - v_f| / v_f = s * M / (P0 - M)             (1')  [EXACT]

which vanishes at M=0, contains no d_gap, and uses exactly the defocus factor this
project's own Formula #5 (`r_geo`, stage2/classical_formulas.py) already used. It also
makes `delta_r / blur_diameter = s / a_stop` — the standard statement that a defocus
blur is a scaled image of the aperture — whereas Eq. (1) made that purely geometric
ratio depend on myopia, which it cannot.

**Verification, not assertion.** `delta_r_derivation_check.py` in this folder checks
(1') three ways: a paraxial ray transfer that assumes neither formula; a wave-optics
propagation of a displaced hole through stage2_fixed's own unmodified pipeline; and the
M=0 limit. The measured retinal centroid tracks (1') to within half a grid pixel at
every M from 0 to 8 D — at M=0 it measures −0.13 µm where Eq. (1) predicts 837 µm.

**Consequences for Sections 3–4 above.** Eq. (2), Eq. (3) and the three-regime criterion
Eq. (5) are unaffected in form — only the value of `delta_r` feeding them changes, by a
factor of 14× (M = 8 D) to 111× (M = 1 D). `RESULTS.md`'s Pass 4 reports what that does to the
classification (short version: the A/B/C tallies at M=4 D do not move, the "harmonics
matter more than the fundamental" finding of Pass 3 does not survive, and Regime B turns
out to be real at low myopia). Section 5's list of what theory alone cannot settle is
unchanged and still applies.

**One further limit of Section 3.3 found in the same pass**, independent of Eq. (1):
Regime A is decided on the *minimum* N_eff over pupil alignments. Minimum is the correct
worst case for brightness (fewest holes = darkest) but the wrong one for ghosting (most
holes = worst ghosting). At D_pupil = 4 mm square packing, s = 2.1–2.8 mm has
N_eff(min) = 1 — classified A, "no second hole to ghost against" — while 60–99% of pupil
alignments actually have two or more holes inside the pupil
(`Array_Design/alignment_fractions.png`).
