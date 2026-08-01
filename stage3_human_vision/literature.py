"""
Citation database for Phase 3. Every equation implemented anywhere in stage3_human_vision
traces to an entry here, tagged by TYPE:

  "first_principles" -- derived directly from physics/radiometry that does not need a
                         literature citation to be correct (energy conservation, Fourier
                         optics definitions of MTF, RMS radius, F-number). A standard
                         textbook reference is still given for traceability.
  "published"         -- a specific named model/result from the literature searched for
                          this phase. Implemented as faithfully as a short web search
                          snippet allows; where the ORIGINAL paper's exact numerical
                          parametrization was not directly available, that is stated
                          explicitly in the citation's `fidelity` field.
  "heuristic"          -- a simplified stand-in used ONLY where reproducing the full
                          published model exactly was not feasible from search results
                          alone (e.g. the full multi-parameter Barten CSF model). Clearly
                          separated so no reader mistakes a heuristic for a validated
                          published curve.

This file is DATA, not computation -- see photometry.py/visual_acuity.py/contrast.py/
metrics.py for where these are actually used.
"""

CITATIONS = {

    "strehl_ratio": {
        "type": "first_principles",
        "statement": "Strehl ratio S = I_peak(actual PSF) / I_peak(diffraction-limited "
                     "PSF, same aperture/wavelength/no aberration).",
        "source": "Strehl (1902); standard definition, e.g. Born & Wolf, Principles of "
                   "Optics.",
        "fidelity": "exact -- universally agreed definition, no free parameters.",
    },
    "marechal_criterion": {
        "type": "published",
        "statement": "Strehl ratio S >= 0.8 (Marechal criterion) is the conventional "
                     "threshold for 'diffraction-limited' performance, corresponding "
                     "to an RMS wavefront error below ~lambda/14.",
        "source": "Marechal (1947); summarized in ResearchGate: 'Marechal condition and "
                   "the effect of aberrations on Strehl intensity', and 'Understanding "
                   "Strehl Ratio in Optical Systems' (Optics for Hire).",
        "fidelity": "exact -- this is the standard, widely-cited numerical threshold.",
    },
    "marechal_approximation": {
        "type": "published",
        "statement": "For small wavefront errors, S ~= exp(-sigma^2), sigma = RMS "
                     "wavefront error in radians.",
        "source": "Marechal (1947) approximation, as commonly used in astronomical "
                   "optics (see ResearchGate: 'Limitations and applicability of the "
                   "Marechal approximation').",
        "fidelity": "approximate by construction (valid for sigma up to ~2 rad per the "
                    "source) -- used here only for order-of-magnitude error-budget "
                    "estimates, not as a precision correction.",
    },
    "mtf_from_psf": {
        "type": "first_principles",
        "statement": "MTF(fx,fy) = |FFT2D(PSF)(fx,fy)| / |FFT2D(PSF)(0,0)|, radially "
                     "averaged to MTF(f). MTF50/MTF10 are the frequencies where "
                     "MTF(f)=0.5 / 0.1.",
        "source": "Standard Fourier optics; e.g. Goodman, Introduction to Fourier "
                   "Optics.",
        "fidelity": "exact -- no free parameters.",
    },
    "otf_from_psf": {
        "type": "first_principles",
        "statement": "OTF(fx,fy) = FFT2D(PSF)(fx,fy) / FFT2D(PSF)(0,0), radially "
                     "averaged to a complex OTF(f) -- the same normalized-FFT-of-PSF "
                     "construction as mtf_from_psf above, but keeping the complex "
                     "value (magnitude AND phase) instead of discarding phase and "
                     "keeping only |OTF|=MTF. PTF(f) = angle(OTF(f)).",
        "source": "Standard Fourier optics; e.g. Goodman, Introduction to Fourier "
                   "Optics.",
        "fidelity": "exact -- no free parameters. Note: metrics.mtf_radial() bins "
                    "|OTF| per radial bin (its own long-standing, unchanged "
                    "behavior); metrics.otf_radial() bins the complex value per bin "
                    "(real/imag averaged separately, then recombined). The two "
                    "orders of operation (magnitude-then-average vs. "
                    "average-then-magnitude) are not identical in general, though "
                    "they agree closely for this project's azimuthally-symmetric "
                    "PSFs -- kept as two separate functions rather than derived from "
                    "one another so neither's numeric history is silently disturbed.",
    },
    "fwhm_core_width": {
        "type": "first_principles",
        "statement": "Full-width-half-max (FWHM) radius: the radius at which the "
                     "azimuthally-averaged radial intensity profile first drops to "
                     "50% of its peak value.",
        "source": "Standard optical/imaging core-width metric; already implemented "
                   "as stage1_v2/physics.py::locate_threshold_crossing (frac_of_peak"
                   "=0.5) / physics.py::fwhm_radius, reused here rather than "
                   "reimplemented.",
        "fidelity": "exact as a definition; KNOWN NUMERICAL INSTABILITY in this "
                    "project's Fresnel near-field regime -- the profile's peak/"
                    "crossing can hop between rings for adjacent aperture values a "
                    "few um apart (see stage3_integrated/README.md, cornea- and "
                    "retina-plane ring-hopping findings). metrics.fwhm_radius() "
                    "always returns the crossing mode and crossing_count alongside "
                    "the radius so this instability stays visible to callers.",
    },
    "airy_diameter": {
        "type": "first_principles",
        "statement": "Airy diffraction-limited first-null diameter = 2 x 1.22 x "
                     "lambda x v_r / a_hole for a circular aperture.",
        "source": "Airy (1835); standard diffraction theory.",
        "fidelity": "exact.",
    },
    "f_number": {
        "type": "first_principles",
        "statement": "F/# = v_r / a_hole (image-space f-number for a single circular "
                     "aperture acting as the system stop).",
        "source": "Standard photographic-optics definition.",
        "fidelity": "exact.",
    },
    "rms_spot_radius": {
        "type": "first_principles",
        "statement": "RMS spot radius = sqrt( sum(I * r^2) / sum(I) ), the "
                     "second-moment / rms radius of the intensity distribution.",
        "source": "Standard optical metric; already implemented as "
                   "stage1_v2/physics.py::second_moment_radius, reused here rather "
                   "than reimplemented.",
        "fidelity": "exact.",
    },
    "throughput_area_ratio": {
        "type": "first_principles",
        "statement": "Optical throughput (power fraction admitted by a single "
                     "sub-aperture relative to the full natural pupil) = "
                     "(a_hole / D_pupil)^2.",
        "source": "Energy conservation for a uniformly-illuminated circular aperture; "
                   "generalizes the project's own earlier photometry formula "
                   "T = N*(pi*a_hole^2/4)/A_total (IYPT_Pinhole_Master_Formulas_and_"
                   "Pipeline.md Sec 2.11) to a single hole (N=1).",
        "fidelity": "exact.",
    },
    "troland_retinal_illuminance": {
        "type": "published",
        "statement": "Retinal illuminance (Td) = scene luminance (cd/m^2) x entrance "
                     "pupil area (mm^2). 1 Td = the retinal illuminance from a 1 cd/m^2 "
                     "surface through a 1 mm^2 pupil.",
        "source": "Troland (1916, as 'photon'; renamed troland later); Wikipedia "
                   "'Troland', Illuminating Engineering Society 'troland' definition.",
        "fidelity": "exact -- standard photometric unit definition. Does not correct "
                    "for the Stiles-Crawford effect (see stiles_crawford entry).",
    },
    "photopic_luminous_efficacy": {
        "type": "published",
        "statement": "CIE standard photopic luminous efficacy = 683 lm/W at 555 nm, "
                     "used to convert between radiometric (W) and photometric (lm/cd) "
                     "units.",
        "source": "CIE 1924 photopic luminosity function, international standard.",
        "fidelity": "exact at 555nm; the project's other tested wavelengths (450/650nm) "
                    "use the standard V(lambda) photopic curve, which is NOT flat -- "
                    "see photometry.py for how this is applied.",
    },
    "csf_photopic_peak": {
        "type": "published",
        "statement": "Human photopic contrast sensitivity function (CSF) is band-pass, "
                     "peaking around 4 cycles/degree, dropping off at both lower and "
                     "higher spatial frequencies; foveal cutoff (CSF->1, i.e. contrast "
                     "threshold ~100%) around 50-60 cpd.",
        "source": "NCBI Bookshelf 'Contrast Sensitivity Function' overview; multiple "
                   "reviews cite the ~4 cpd photopic peak (some report 2-5 cpd, others "
                   "5-8 cpd for related tasks).",
        "fidelity": "approximate -- this project implements a SIMPLIFIED parametric "
                    "band-pass curve matched to the PEAK LOCATION (~4 cpd) and general "
                    "shape reported in the literature, NOT the full multi-parameter "
                    "Barten (1999) CSF model, which requires additional physiological "
                    "parameters beyond what a literature search alone can safely "
                    "reproduce. Labeled 'heuristic_csf' wherever used -- see contrast.py.",
    },
    "mannos_sakrison_csf": {
        "type": "published",
        "statement": "Alternative CSF parametrization (Mannos & Sakrison) peaking at "
                     "~8 cycles/degree, normalized to a maximum of 1 -- used in image "
                     "compression/coding literature.",
        "source": "Mannos & Sakrison, as summarized in 'Contrast sensitivity vs spatial "
                   "frequency -- the last word' (kasson.com) and related CSF reviews.",
        "fidelity": "approximate -- offered as a second CSF variant per the brief's "
                    "request to implement multiple accepted models where more than one "
                    "exists; peak location differs from the 4 cpd photopic figure "
                    "above, reflecting genuine variation across published CSF studies.",
    },
    "rose_devries_law": {
        "type": "published",
        "statement": "In the mesopic/low-light (DeVries-Rose) regime, contrast "
                     "sensitivity (and detection SNR) scales as sqrt(retinal "
                     "illuminance); in the photopic (Weber) regime, contrast threshold "
                     "is approximately constant (independent of illuminance).",
        "source": "Rose (1946, 1948); DeVries; summarized in 'Mechanisms and Meaning "
                   "of DeVries-Rose Adaptation' (Donner & Fagerholm, 1996) and 'The "
                   "Rose model, revisited' (JOSA A, 1999).",
        "fidelity": "the SCALING LAW (SNR ~ sqrt(flux)) is reproduced exactly per Rose's "
                    "original photon-counting argument (first-principles Poisson "
                    "statistics); the specific luminance thresholds separating "
                    "scotopic/mesopic/photopic regimes are approximate, standard "
                    "textbook values, not re-derived from Rose's original data.",
    },
    "weber_contrast": {
        "type": "first_principles",
        "statement": "Weber contrast C = (L_target - L_background) / L_background.",
        "source": "Standard definition; e.g. schorsch.com 'Contrast' glossary, IES "
                   "'luminance contrast'.",
        "fidelity": "exact.",
    },
    "blackwell_1946": {
        "type": "published",
        "statement": "Blackwell (1946) measured contrast-detection thresholds "
                     "(50% detection probability) as a function of target angular "
                     "size and background luminance from ~90,000 observations -- the "
                     "classical reference dataset for human contrast-threshold vs. "
                     "luminance, still used in lighting/visibility engineering.",
        "source": "Blackwell, H.R. (1946), 'Contrast Thresholds of the Human Eye'; "
                   "summarized in arXiv:1405.4209 ('Human Contrast Threshold and "
                   "Astronomical Visibility').",
        "fidelity": "cited for context only -- Blackwell's task (detecting a "
                    "uniform circular target against a uniform background) differs "
                    "from this project's task (resolving a retinal PSF/optotype), so "
                    "this project does NOT claim to apply Blackwell's specific "
                    "threshold curves quantitatively; it is referenced as the "
                    "well-established anchor for 'visual contrast threshold "
                    "literature exists and looks like this', per the brief's request "
                    "to document it.",
    },
    "visual_acuity_cutoff_frequency": {
        "type": "published",
        "statement": "20/20 (normal) visual acuity corresponds to a minimum angle of "
                     "resolution (MAR) of 1 arcmin, equivalent to resolving ~30 "
                     "cycles/degree; foveal photoreceptor (Nyquist) sampling limit is "
                     "~60 cpd. At 30 cpd, the eye's own optical MTF is reported as "
                     "~0.4 for a 2mm pupil, dropping to ~0.16 for a 5.8mm pupil.",
        "source": "Norman Koren, 'Understanding resolution and MTF'; StatPearls "
                   "'Contrast Sensitivity'.",
        "fidelity": "the MAR<->cpd conversion is an exact geometric identity (2 arcmin "
                    "per cycle => 30 cpd at 1 arcmin MAR); the specific MTF values "
                    "(0.4 at 2mm, 0.16 at 5.8mm pupil) are reported figures used here "
                    "ONLY as external validation reference points, not re-derived.",
    },
    "visual_strehl_vsx": {
        "type": "published",
        "statement": "Visual Strehl ratio in the Spatial domain (VSX): the eye's PSF "
                     "and the diffraction-limited PSF (same pupil) are each weighted "
                     "by a neural weighting function (the inverse Fourier transform of "
                     "the neural contrast sensitivity function), and VSX is the ratio "
                     "of the two weighted-PSF peak values. Shown to correlate with "
                     "subjective best focus and visual performance.",
        "source": "Thibos, Hong, Bradley, Cheng (2004), 'Statistical variation of "
                   "aberration structure...' and follow-on work; summarized in "
                   "'Computational Aspects of the Visual Strehl Ratio' (ResearchGate) "
                   "and 'Normative best-corrected values of the visual image quality "
                   "metric VSX...' (PubMed).",
        "fidelity": "CONCEPT reproduced, in the VSOTF (frequency-domain) form: "
                    "visual_acuity.visual_strehl_approx() weights the REAL PART of "
                    "the actual and diffraction-limited OTF (metrics.otf_radial()) "
                    "by a neural CSF and compares the two CSF-weighted integrals -- "
                    "matching Iskander (2006) 'Computational aspects of the visual "
                    "Strehl ratio' more closely than an earlier version of this "
                    "function did (which weighted raw MTF magnitude, |OTF|, instead "
                    "of Re(OTF), a coarser stand-in). Still approximate: (1) this "
                    "project's neural weighting function is the SIMPLIFIED heuristic "
                    "CSF model above (csf_photopic_peak), not Thibos/Iskander's "
                    "validated interferometric neural CSF; (2) this project "
                    "normalizes against its own M=0 (zero-defocus) PSF/OTF as the "
                    "'diffraction-limited' reference, rather than the literature's "
                    "CSF-volume normalization. Labeled 'visual_strehl_*' (VSOTF) "
                    "everywhere it is computed, and should not be treated as a "
                    "bit-exact reproduction of the clinical VSOTF/VSX metric.",
    },
    "stiles_crawford": {
        "type": "published",
        "statement": "Light entering the pupil off-axis (near the pupil margin) is "
                     "less effective at stimulating photoreceptors than light entering "
                     "near the pupil center (the Stiles-Crawford effect of the first "
                     "kind) -- apodizes the effective pupil, somewhat suppressing the "
                     "contribution of a large natural pupil's edge relative to a "
                     "small, centered pinhole.",
        "source": "Stiles & Crawford (1933); standard textbook effect.",
        "fidelity": "NOT numerically modeled in this project (optional per the brief) "
                    "-- noted qualitatively in the error budget only, since it would "
                    "require an additional apodization parameter this project has not "
                    "sourced a specific numerical model for.",
    },
    "ocular_higher_order_aberrations": {
        "type": "published",
        "statement": "Typical (non-pinhole-corrected) human eye higher-order aberration "
                     "RMS wavefront error is ~0.33-0.38 micron over a naturally dilated "
                     "6mm pupil in healthy young adults; this shrinks sharply for "
                     "smaller (or artificially stopped-down) pupils since higher-order "
                     "Zernike terms scale steeply with aperture radius.",
        "source": "Multiple studies summarized via ScienceDirect/PMC reviews of ocular "
                   "wavefront aberrometry (e.g. mean HOA RMS 0.334 +/- 0.192 micron "
                   "across labs; ~0.38 micron over 6mm pupil, ages 18-40).",
        "fidelity": "the 6mm-pupil figure is a directly reported literature value; "
                    "the claim that it 'shrinks sharply' for a pinhole-scale aperture "
                    "is a qualitative, well-established optical fact (aberration "
                    "scaling with aperture) applied here for the error budget, not a "
                    "specific re-derived numerical scaling law for THIS eye model.",
    },
    "ideal_pinhole_wang_2009": {
        "type": "published",
        "statement": "Mean visual acuity (LogMAR) measured through single circular "
                     "pinhole apertures of 0.5/0.75/1.0/1.2/1.5mm diameter: "
                     "0.28/0.31/1.0/0.4/0.5 LogMAR respectively.",
        "source": "'The Ideal Pinhole', IOVS 2009 (ARVO), "
                   "https://iovs.arvojournals.org/article.aspx?articleid=2366370 -- "
                   "13 subjects (11 myopic, 1 hyperopic, 1 emmetropic), refractive "
                   "errors recorded, VA checked with/without correction, Snellen "
                   "projection chart at 20 feet, 15 foot-candles illumination. "
                   "Values confirmed directly against the primary source (not just "
                   "the paraphrase already quoted in model_comparison/README.md).",
        "fidelity": "the aperture->LogMAR values themselves are directly reported "
                    "figures, not re-derived. IMPORTANT LIMITATION: the paper's "
                    "summary table does NOT separate results by individual subject "
                    "refractive error (M, diopters) or by corrected/uncorrected "
                    "state -- this project's model requires a specific M per point, "
                    "which the paper does not cleanly provide. Used in "
                    "validate_against_literature.py as a SENSITIVITY comparison "
                    "across several representative M values (0/2/5D), reporting "
                    "RMSE/MAE/R^2/Pearson r at each rather than picking a single M "
                    "(which would risk silently cherry-picking the best-looking fit "
                    "-- exactly what this project's other comparisons already avoid "
                    "doing, e.g. model_comparison/acuity_check.py's own single-point "
                    "M-matching caveat).",
        "data": {
            "aperture_um": [500, 750, 1000, 1200, 1500],
            "logmar": [0.28, 0.31, 1.0, 0.4, 0.5],
        },
    },
}


def get(key):
    if key not in CITATIONS:
        raise KeyError(f"No citation entry for {key!r} -- add it to literature.py "
                        f"before using it elsewhere in stage3_human_vision.")
    return CITATIONS[key]


def print_bibliography():
    for key, entry in CITATIONS.items():
        print(f"[{entry['type']}] {key}")
        print(f"  {entry['statement']}")
        print(f"  Source: {entry['source']}")
        print(f"  Fidelity: {entry['fidelity']}")
        print()


if __name__ == "__main__":
    print_bibliography()
