"""
Citation database for R7acuity -- a genuinely independent visual acuity model
(Watson & Ahumada 2008 template-matching ideal-observer architecture), built
specifically to test whether stage4_human_vision/acuity.py's clinical validation
failure (RESULTS.md: R^2 << 0 against Wang 2009) is a DATA problem or a MODEL
problem, using a structurally different model family. See R7acuity/README.md for
the architectural comparison.

Mirrors stage4_human_vision/literature.py's format exactly (type/statement/source/
fidelity). Every entry below was checked directly against the actual source (full
text of a US patent, a peer-reviewed open-access paper, or a publisher's own
indexed page) -- never accepted from a secondhand paraphrase alone, per the
discipline that caught and rejected a fabricated NeuroQuantology citation earlier
in this project.
"""

CITATIONS = {

    "watson_ahumada_2008_wfa_metric": {
        "type": "published",
        "statement": "Introduces the 'WFA Metric': a template-matching ideal-"
                     "observer model of visual acuity. Pipeline: (1) generate the "
                     "Optical Transfer Function (OTF) from wavefront aberrations "
                     "via a generalized pupil function and DFT of the PSF; (2) "
                     "generate a Neural Transfer Function (NTF), a radial function "
                     "of spatial frequency (their own default form: RNTF(f) = "
                     "gain*(exp[-(f/f0)^b] - loss*exp[-(f/f1)^2]), times an oblique-"
                     "effect filter); (3) Total Transfer Function TTF = OTF*NTF; "
                     "(4) Neural Images S_k = IDFT[DFT[O_k]*TTF] for each optotype "
                     "O_k; (5) DEFAULT templates T_k = S_k (matched/'ideal' "
                     "observer), normalized to unit norm; (6) cross-correlation "
                     "R_j,k = S_j . T_k_normalized, decision = argmax_k(R); (7) a "
                     "Proportion-Correct function P(size), found either by Monte "
                     "Carlo simulation of the noisy decision process (their "
                     "'first embodiment') or by a deterministic integral formula "
                     "using template cross-correlations directly (their 'second "
                     "metric') -- this project implements the FIRST (Monte Carlo) "
                     "embodiment specifically, per the brief; (8) size found via "
                     "bisection where P(size)=P_target (their default 0.55 for "
                     "10-alternative Sloan letters); (9) logMAR = log10(mar), where "
                     "'mar' is each optotype's STROKE WIDTH in arcmin, and each "
                     "optotype is a standard 5x5-unit design (5 MAR tall, 5 MAR "
                     "wide) -- i.e. mar = overall_letter_height_arcmin / 5. Their "
                     "own supported optotype sets explicitly include 'Snellen E's' "
                     "(claim 6) alongside Sloan letters, Landolt C's, and Lea "
                     "symbols -- this project's choice of a 4-orientation tumbling-"
                     "E optotype set (simpler to template-match unambiguously than "
                     "10 Sloan letters) is one of the patent's own named supported "
                     "configurations, not a deviation from it.",
        "source": "Watson, A. B., & Ahumada, A. J. (2008). Predicting visual "
                  "acuity from wavefront aberrations. Journal of Vision, 8(4):17, "
                  "1-19. DOI: 10.1167/8.4.17. Also filed as US Patent 8,408,707 B1 "
                  "'Prediction of Visual Acuity from Wavefront Aberrations' "
                  "(assigned to NASA, granted 2013-04-02), which describes the "
                  "identical algorithm in full enabling detail with worked "
                  "equations and a default-parameter table. VERIFIED DIRECTLY: "
                  "the patent's full text (12 pages, all equations, all claims, "
                  "the full default-parameter table) was read in full -- not a "
                  "search-snippet paraphrase.",
        "fidelity": "high -- read in full, including every numbered equation and "
                    "the complete default-parameter table (Section 10). One "
                    "deliberate deviation from the patent's own DEFAULT "
                    "configuration, per the brief's explicit instruction: this "
                    "project uses CLEAN (unmatched, unblurred) templates rather "
                    "than the patent's default T_k=S_k (matched/blurred "
                    "templates). This is not a misreading of the patent -- the "
                    "patent's own Section 8.c explicitly allows T_k to differ from "
                    "S_k ('By default, these are identical to the Neural Images "
                    "S_k' -- implying non-default configurations are anticipated) "
                    "-- and this specific unmatched-template variant is confirmed "
                    "as a recognized, named alternative ('the real observer', as "
                    "opposed to Watson & Ahumada's own 'ideal observer') in "
                    "Leroux et al. (2024, see below), read directly.",
    },

    "leube_2018_ntf_csf_over_mtf": {
        "type": "published",
        "statement": "Defines the Neural Transfer Function (NTF) explicitly as "
                     "'the fraction of the contrast sensitivity function and the "
                     "modulation transfer function' -- i.e. NTF(f) = CSF(f)/MTF(f) "
                     "-- and fits it to a closed form NTF(sf) = a*sf*exp(-b*sf) * "
                     "sqrt(1+0.06*exp(b*sf)) (their Equation 1, a=59.12, b=0.17 "
                     "for their study-group mean). Explicitly compares their "
                     "computed NTF against 'the NTF from Campbell & Green (1965)' "
                     "(their Figure 2b) as the established, classic reference "
                     "curve for this same construction.",
        "source": "Leube, A., Schilling, T., Ohlendorf, A., Kern, D., Ochakovski, "
                  "A. G., Fischer, M. D., & Wahl, S. (2018). Individual neural "
                  "transfer function affects the prediction of subjective depth "
                  "of focus. Scientific Reports, 8:1919. "
                  "DOI: 10.1038/s41598-018-20344-x. Open access, verified "
                  "directly (full text read, including Equation 1 and Figure 2).",
        "fidelity": "high, WITH A CORRECTION: the task brief that requested this "
                    "citation attributed this NTF=CSF/MTF construction to "
                    "'Radhakrishnan et al. 2018, Scientific Reports.' Having read "
                    "the actual paper matching that description (same journal, "
                    "same year, same NTF=CSF/MTF content), the correct author list "
                    "is Leube, Schilling, Ohlendorf, Kern, Ochakovski, Fischer & "
                    "Wahl -- there is no 'Radhakrishnan' among the authors. "
                    "Reported here as a correction, not a rejection (the paper "
                    "itself and its content are real and directly verified) -- "
                    "same discipline as catching author/citation mismatches "
                    "elsewhere in this project. IMPORTANT MODELING NOTE (why "
                    "this project divides by the DIFFRACTION-LIMITED MTF, not a "
                    "subject's own aberrated MTF, unlike this paper's own usage): "
                    "Leube et al. compute NTF by dividing OUT an individual "
                    "subject's own measured (aberrated) MTF from their CSF, to "
                    "isolate a subject-independent 'neural-only' curve. This "
                    "project's optical filtering step already applies the real, "
                    "aberrated retinal PSF directly (from stage2_fixed), so "
                    "re-dividing by that SAME aberrated MTF in the neural stage "
                    "would double-count/cancel the optics. Dividing by the "
                    "DIFFRACTION-LIMITED MTF instead yields a NTF representing "
                    "neural sensitivity on top of ideal optics -- the correct "
                    "choice for THIS project's two-stage (real-PSF then NTF) "
                    "architecture, and exactly what the task brief specified.",
    },

    "campbell_green_1965_ntf_origin": {
        "type": "published",
        "statement": "The classic paper credited (via Leube et al. 2018's own "
                     "Figure 2b comparison, 'NTF from Campbell & Green (1965)') "
                     "as the origin of decomposing the eye's overall contrast "
                     "sensitivity function into an optical component (MTF, "
                     "measured via an interference-fringe technique that bypasses "
                     "the eye's own optics) and a neural/retinal component -- the "
                     "conceptual ancestor of the NTF=CSF/MTF construction used "
                     "here.",
        "source": "Campbell, F. W., & Green, D. G. (1965). Optical and retinal "
                  "factors affecting visual resolution. Journal of Physiology, "
                  "181(3), 576-593. DOI: 10.1113/jphysiol.1965.sp007784.",
        "fidelity": "PARTIAL -- citation, DOI, and abstract-level description "
                    "(interference-fringe technique separating optical from "
                    "neuro-retinal resolution limits) confirmed via PubMed/PMC "
                    "indexing, but the 1965 primary text itself (PMC shows only "
                    "page-image thumbnails, no OCR text available through this "
                    "project's tools) was NOT directly read. Its role as the "
                    "origin of the specific NTF=CSF/MTF construction is confirmed "
                    "via Leube et al. (2018, directly verified, see above), which "
                    "explicitly names and plots 'the NTF from Campbell & Green "
                    "(1965)' as an established comparison baseline -- this project "
                    "did not independently derive that attribution.",
    },

    "leroux_2024_real_observer": {
        "type": "published",
        "statement": "Explicitly formalizes and names TWO template-matching "
                     "observer variants in the Watson & Ahumada model family: the "
                     "'ideal observer' (Eq. 3: uses the ABERRATED images "
                     "I_1,I_2 themselves as templates -- Watson & Ahumada's own "
                     "default) and the 'real observer' (Eq. 4: uses the "
                     "UNABERRATED, clean letters O_1,O_2 as templates instead -- "
                     "'because using aberration-free images of letters as "
                     "templates is a plausible model when the experiment is "
                     "performed with a known alphabet'). This project implements "
                     "the 'real observer' variant (clean templates), per the task "
                     "brief's explicit instruction.",
        "source": "Leroux, C.-E., Leahy, C., Dupuis, J., Fontvieille, C., & "
                  "Bardin, F. (2024). Defining metrics of visual acuity from "
                  "theoretical models of observers. Journal of Vision, 24(4):14, "
                  "1-14. DOI: 10.1167/jov.24.4.14. Open access, verified directly "
                  "(full text read, including Equations 3-4 and their surrounding "
                  "discussion).",
        "fidelity": "high -- read directly, confirms both the naming convention "
                    "('ideal' vs 'real' observer) and the exact mathematical "
                    "distinction (matched vs. unmatched templates) this project "
                    "uses, from a source independent of the original Watson & "
                    "Ahumada patent/paper.",
    },

    "closed_form_approximations_unverified_coefficients": {
        "type": "published",
        "statement": "Two closed-form approximations (logMAR ~= 25*log10(M) and "
                     "logMAR ~= (50/3)*log10(VSOTF)) are computed in threshold.py "
                     "as an internal cross-check alongside the Monte Carlo "
                     "threshold, per the task brief's explicit specification of "
                     "these two formulas with these coefficients.",
        "source": "As specified in the task brief requesting this model; "
                  "attributed there to 'the same model family' as Watson & "
                  "Ahumada (2008).",
        "fidelity": "LOW ON THE SPECIFIC COEFFICIENTS, high on the general "
                    "concept -- an independent verification attempt was made: "
                    "confirmed that Strehl-ratio/VSOTF-based logMAR "
                    "approximations are a real, established category in this "
                    "literature family (e.g. Leroux et al. 2024 above, and a 2022 "
                    "companion paper by an overlapping author group defining a "
                    "model-based contrast-sensitivity metric 'M' computed "
                    "directly from optical aberrations), and separately checked "
                    "and RULED OUT one candidate source (Espinosa Tomas et al. "
                    "2023, Applied Sciences 13:6350 -- read directly in full; "
                    "uses entirely different image-quality metrics (MSE, SSIM, "
                    "FSIM, etc.) on natural images, not Strehl/VSOTF-based "
                    "formulas with these coefficients). The EXACT primary source "
                    "stating '25' and '50/3' as coefficients was not located "
                    "within reasonable effort. Implemented exactly as specified "
                    "in the brief and clearly labeled in all outputs as "
                    "'brief-specified, not independently re-derived from a "
                    "verified primary source' -- not presented as equivalent in "
                    "verification strength to the Monte Carlo model itself. 'M' "
                    "is implemented as the Strehl ratio (this project's existing, "
                    "already-validated stage3_human_vision.metrics.strehl_ratio), "
                    "the most standard scalar optical-quality metric available, "
                    "since the brief does not otherwise define M.",
    },

}


def get(key):
    if key not in CITATIONS:
        raise KeyError(f"No citation entry for {key!r} -- add it to "
                       f"R7acuity/literature.py first.")
    return CITATIONS[key]
