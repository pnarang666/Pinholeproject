"""
Extends Eq. (3)/(5) from THEORY.md: the ghosting comb Comb_{delta_r}(r) has Fourier
content not just at f0=1/delta_r, but at every harmonic n*f0 (n=1,2,3,...), since a
periodic (or quasi-periodic, finite-N) train of shifted PSF copies is a genuine
periodic signal, not a single sinusoid. THEORY.md's Eq. (5) and RESULTS.md's first
sweep only ever evaluated the FUNDAMENTAL (n=1) -- this module checks all harmonics,
because a harmonic landing near the CSF's peak sensitivity (4-8 cpd) can be MORE
dangerous than the fundamental even if the fundamental itself is far from that peak.

Derivation: for N discrete, equally-spaced copies (a finite train, not an infinite
comb), the Fourier series of a rectangular pulse train of N impulses at spacing
delta_r has harmonics at f_n = n/delta_r for all integer n, with an envelope set by
the finite-N Dirichlet kernel -- but the PRESENCE of each harmonic at f_n = n*f0 is
independent of N (only its exact amplitude/width depends on N); this module conserves
the exact per-harmonic ATTENUATION (MTF(n*f0)) and PERCEPTIBILITY MARGIN
(MTF(n*f0)/CSF_threshold(n*f0)) using this project's own real, computed MTF curve
and the real Barten(1999) CSF -- not an idealized infinite-comb assumption -- so the
finite-N caveat only affects the idealized EQUAL-amplitude-at-every-harmonic
assumption, stated explicitly below, not the frequency locations themselves.

CAVEAT, stated not hidden: this treats every harmonic as having equal amplitude
before MTF filtering (the idealized infinite-comb limit) -- for small N_eff (2-4),
the finite-train Dirichlet envelope actually rolls off the amplitude of higher
harmonics well before MTF/CSF filtering does, so this module's harmonic margins are
an UPPER BOUND (worst case) on real perceptibility at low N_eff, not an exact value.
At large N_eff (>~10, most of the CN-patent-range points), the equal-amplitude
approximation is much closer to exact.

KEY FINDING (see RESULTS.md): the worst-case harmonic is NEVER n=1 across every
tested (aperture, pitch, M) combination -- it consistently lands at n such that
n*f0 sits near 1.9-2.3 cycles/degree, i.e. near the human CSF's peak sensitivity
band, REGARDLESS of pitch (pitch only changes WHICH harmonic index n happens to
land there). This makes the danger-zone classification much more ROBUST than a
fundamental-only analysis suggested: for any array dense enough to have N_eff>1
(i.e. outside Regime A), some harmonic of the resulting ghosting comb will almost
inevitably fall near the eye's most sensitive frequency band in this project's
near-eye geometry, essentially closing the "dense-but-safe" (Regime B) window
found empty in this project's actual tested range.
"""
import numpy as np
from ghosting_regime import ghost_ripple_frequency
from metrics_mtf import mtf_radial, interp_mtf_at_freq, cycles_per_um_to_cycles_per_degree
from contrast_barten import csf_threshold_barten
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stage2_fixed"))
import phase2_retina as p2


def harmonic_margin_profile(a_hole_um, pitch_um, D_pupil_um, wavelength_nm, d_gap_mm,
                             M_diopters, P0=60.0, n_prime=1.336,
                             refractive_index_correction=True, grid_N=2048,
                             window_L_mm=6.0, scene_luminance_cdm2=10000.0,
                             field_deg=10.0, n_max=40, eye_resolution_limit_cpd=60.0):
    """
    Returns a dict with arrays 'n' (harmonic order), 'f_cpd' (n*f0), 'mtf' (MTF at
    that frequency), 'csf_threshold' (Barten threshold at that frequency), and
    'margin' (mtf/csf_threshold -- >1 means that harmonic is predicted PERCEPTIBLE).
    Also returns 'worst_n', 'worst_margin', 'worst_f_cpd' -- the single most dangerous
    harmonic, which may NOT be n=1.
    """
    result = p2.run_pipeline_point(
        a_hole=a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9, d_gap=d_gap_mm * 1e-3,
        grid_N=grid_N, window_L_mm=window_L_mm, M_diopters=M_diopters, P0=P0,
        n_prime=n_prime, D_pupil_um=D_pupil_um, refractive_index_correction=refractive_index_correction,
    )
    if not result["junction_check_passed"]:
        return {"error": result["junction_fail_reason"]}

    I_retina = result["I_retina"]
    dx = result["cornea_result"]["dx"]
    v_r_um = result["myopia"]["L_ax"] * 1e6
    f_centers_cpum, mtf_1d = mtf_radial(I_retina, dx)
    f0_cpum, f0_cpd = ghost_ripple_frequency(pitch_um, d_gap_mm * 1e3, v_r_um)

    ns, freqs, mtfs, thresholds, margins = [], [], [], [], []
    for n in range(1, n_max + 1):
        f_cpd = n * f0_cpd
        if f_cpd > eye_resolution_limit_cpd:
            break
        f_cpum = n * f0_cpum
        mtf_val = interp_mtf_at_freq(f_centers_cpum, mtf_1d, f_cpum)
        thresh = csf_threshold_barten(f_cpd, scene_luminance_cdm2, field_deg)
        ns.append(n); freqs.append(f_cpd); mtfs.append(mtf_val); thresholds.append(thresh)
        margins.append(mtf_val / thresh if thresh > 0 else float("inf"))

    margins = np.array(margins)
    worst_idx = int(np.argmax(margins))
    return {
        "n": ns, "f_cpd": freqs, "mtf": mtfs, "csf_threshold": thresholds, "margin": margins.tolist(),
        "worst_n": ns[worst_idx], "worst_margin": float(margins[worst_idx]), "worst_f_cpd": freqs[worst_idx],
        "fundamental_margin": float(margins[0]),
    }
