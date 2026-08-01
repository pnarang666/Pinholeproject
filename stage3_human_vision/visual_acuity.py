"""
Visual acuity prediction models. Multiple candidate approaches, per the brief's
explicit request to investigate several rather than assume one:

  1. MAR/Snellen from MTF cutoff frequency (first-principles geometric conversion +
     an MTF-threshold criterion).
  2. VSX-style "visual Strehl" using this project's simplified CSF as the neural
     weighting function (literature.get('visual_strehl_vsx'), approximate fidelity).
  3. Rose-DeVries / photon-noise-limited SNR acuity bound.

None of these is asserted as "the" correct model -- metrics.py:main and comparison.py
investigate which one (if any) tracks published experimental data best, per the
brief's "investigate, don't assume" instruction.
"""

import numpy as np

import literature
import contrast

ARCMIN_PER_RAD = (180 / np.pi) * 60
NORMAL_MAR_ARCMIN = 1.0  # literature.get('visual_acuity_cutoff_frequency'), 20/20 reference


def mar_to_snellen_denominator(mar_arcmin):
    """literature.get('visual_acuity_cutoff_frequency'): MAR(arcmin) = denom/20."""
    return 20.0 * mar_arcmin


def logmar_from_mar(mar_arcmin):
    """
    literature.get('visual_acuity_cutoff_frequency'): logMAR = log10(MAR in arcmin) --
    the standard logarithmic acuity scale used throughout the clinical literature this
    project compares against (0.0 = 20/20; positive = worse than 20/20; e.g. 20/200 =
    logMAR 1.0). An exact geometric/definitional identity, not a fitted or approximate
    conversion. Previously this project only ever quoted OTHER studies' logMAR values
    in comments/citations (e.g. model_comparison/acuity_check.py); this is the first
    place this project computes its OWN predicted logMAR.
    """
    return np.log10(np.maximum(np.asarray(mar_arcmin, dtype=float), 1e-6))


def mar_from_angular_blur(radius_m, v_r_m):
    """
    literature.get('visual_acuity_cutoff_frequency'): MAR (arcmin) from a retinal
    blur radius (m), via angular blur = radius / v_r (small-angle, exact geometric
    conversion at the retina's own posterior nodal distance). Promotes the formula
    model_comparison/acuity_check.py::angular_blur_arcmin already uses inline (that
    script is left unmodified -- it is an intentionally-frozen Phase 2 reference,
    same rule as stage1/ -- this is a fresh, reusable copy for Phase 3+ callers, not
    a refactor of that script).
    """
    return (radius_m / v_r_m) * ARCMIN_PER_RAD


def cutoff_cpd_to_mar(cutoff_cpd):
    """
    literature.get('visual_acuity_cutoff_frequency'): a resolvable grating of cutoff_cpd
    cycles/degree corresponds to a minimum-angle-of-resolution of
    MAR(arcmin) = 30 / cutoff_cpd (since 20/20 = 1 arcmin MAR <-> 30 cpd cutoff, an
    exact geometric identity: 1 cycle = 2 arcmin of grating period, so cutoff_cpd = 60 /
    (2*MAR) = 30/MAR).
    """
    cutoff_cpd = np.maximum(np.asarray(cutoff_cpd, dtype=float), 1e-6)
    return 30.0 / cutoff_cpd


def acuity_from_mtf_cutoff(mtf50_cpd, mtf10_cpd):
    """
    Predicts MAR/Snellen from this project's own MTF50 and MTF10 (metrics.py). Two
    variants are returned since there is no single universally-agreed MTF threshold
    for acuity prediction -- MTF50 is a common general image-quality criterion; MTF10
    approximates a near-detection-limit criterion, closer to (but not identical to)
    a contrast-threshold-based definition. Both are first-principles geometric
    conversions (cutoff_cpd_to_mar); the CHOICE of threshold (50% vs 10%) is a
    modeling assumption, not itself from a specific cited acuity study.
    """
    mar_from_50 = cutoff_cpd_to_mar(mtf50_cpd)
    mar_from_10 = cutoff_cpd_to_mar(mtf10_cpd)
    return {
        "mar_arcmin_mtf50": mar_from_50, "snellen_denom_mtf50": mar_to_snellen_denominator(mar_from_50),
        "mar_arcmin_mtf10": mar_from_10, "snellen_denom_mtf10": mar_to_snellen_denominator(mar_from_10),
        "logmar_mtf50": logmar_from_mar(mar_from_50), "logmar_mtf10": logmar_from_mar(mar_from_10),
    }


def visual_strehl_approx(freqs_cpd, otf_values, freqs_cpd_dl, otf_values_dl,
                          csf_model="photopic_4cpd"):
    """
    literature.get('visual_strehl_vsx'), APPROXIMATE fidelity (see that citation entry
    for exactly what is and is not reproduced from Thibos et al./Iskander's validated
    VSOTF metric).

    VSOTF concept: weight the actual OTF and the diffraction-limited OTF by the
    neural CSF, then compare their (CSF-weighted) areas -- rather than raw peak PSF
    intensities (plain Strehl), this asks "how much of the optically-transmitted
    contrast survives at the spatial frequencies human vision actually uses."

    `otf_values`/`otf_values_dl` are the COMPLEX radially-averaged OTF (from
    metrics.otf_radial()) -- the REAL PART is what's weighted here, per the published
    VSOTF formulation, NOT |OTF| (MTF magnitude). This is an upgrade from an earlier
    version of this function that took MTF magnitude directly (a coarser
    approximation); using Re(OTF) is closer to the published definition, though still
    approximate for the reasons in literature.py's fidelity note (this project's
    simplified CSF; normalized against this project's own M=0 PSF reference rather
    than the literature's CSF-volume normalization).
    """
    csf_actual = contrast.CSF_MODELS[csf_model](freqs_cpd)
    csf_dl = contrast.CSF_MODELS[csf_model](freqs_cpd_dl)
    re_otf_actual = np.real(np.asarray(otf_values))
    re_otf_dl = np.real(np.asarray(otf_values_dl))
    weighted_actual = np.trapz(re_otf_actual * csf_actual, freqs_cpd)
    weighted_dl = np.trapz(re_otf_dl * csf_dl, freqs_cpd_dl)
    return weighted_actual / weighted_dl if weighted_dl > 0 else 0.0


def snr_acuity_bound(photon_flux_density, reference_flux_density=1e16, reference_mar_arcmin=1.0):
    """
    literature.get('rose_devries_law'): a photon-noise-limited MAR bound, assuming
    resolvable detail scales inversely with the Rose-DeVries relative sensitivity
    (MAR ~ 1/sensitivity ~ 1/sqrt(flux/flux_ref)). This is a first-principles scaling
    argument from Rose's photon-counting model, calibrated so that
    reference_flux_density maps to reference_mar_arcmin (i.e. it reports RELATIVE
    change in the photon-noise floor as illumination changes with aperture, not an
    absolute clinical MAR prediction).
    """
    sensitivity = contrast.rose_devries_relative_sensitivity(photon_flux_density, reference_flux_density)
    if sensitivity <= 0:
        return np.inf
    return reference_mar_arcmin / sensitivity
