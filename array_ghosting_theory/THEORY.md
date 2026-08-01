# Theory of Multi-Aperture Ghosting in Pinhole Eyewear: Reconciling Geometric Optics, Fourier Theory, and Real-World Evidence

*Citation-fidelity labels: **[EXACT]** = first-principles/exact identity, **[PUBLISHED]** = a specific cited result applied as originally derived, **[SYNTHESIS]** = a novel combination of citations not itself published as a unified result, **[UNTESTED]** = requires physical/psychophysical confirmation this document cannot provide.*

See `RESULTS.md` for the implementation of Eq. (5) below and a real, honest finding about where it currently breaks down (the CSF term).

## 1. Setup and Motivation

A multi-hole array, distance d_gap from the cornea, images a distant scene point through every hole admitting light into the pupil simultaneously. Each hole produces a copy of the same single-hole PSF, laterally shifted on the retina by ordinary parallax. This project's existing criterion (`stage_array/array_photometry.py`) treats adjacent holes at pitch s as producing retinal images separated by

    delta_r ~= s * v_r / d_gap                                    (1)   [EXACT]

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
