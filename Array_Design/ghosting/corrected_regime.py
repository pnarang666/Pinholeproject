"""
A/B/C ghosting classification with a SELECTABLE ghost-separation model, plus a PSF
cache. Added during the Array_Design consolidation (Step 2); ghosting_regime.py is
left exactly as Passes 1-3 ran it.

Why this module exists rather than an edit to ghosting_regime.py:
  1. delta_r_derivation_check.py showed the legacy separation formula is wrong (see
     ghost_separation.py for the derivation). Both models must stay runnable
     side-by-side to report what actually changed, so neither is edited away.
  2. The single-hole PSF depends on (a_hole, M, wavelength, d_gap, D_pupil) and NOT on
     pitch -- verified by reading phase2_retina.run_pipeline_point's signature, which
     takes no pitch argument. ghosting_regime.classify_ghosting_regime() nevertheless
     re-runs the whole wave-optics chain for every pitch, so a 4-aperture x 9-pitch
     sweep pays for 36 propagations instead of 4. Caching on (a_hole, M, optics) makes
     the aperture x pitch x myopia grids in joint_design_space.py affordable. The
     cached quantity is the pipeline result itself -- no physics is recomputed
     differently here.

What is NOT reimplemented: the PSF/MTF (phase2_retina + metrics_mtf), the CSF
(contrast_barten), N_eff (photometry/array_photometry), and the harmonic margin
definition (harmonic_analysis) are all imported and called. Only Eq. (5)'s comparison
-- three `if`s -- appears here, and self_check() asserts it reproduces
ghosting_regime.classify_ghosting_regime()'s legacy answer exactly.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "photometry"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "stage2_fixed"))

import phase2_retina as p2  # noqa: E402
from array_photometry import n_holes_exact_sweep_alignment  # noqa: E402
from contrast_barten import csf_threshold_barten  # noqa: E402
from metrics_mtf import mtf_radial, interp_mtf_at_freq  # noqa: E402
import ghost_separation as gs  # noqa: E402

EYE_RESOLUTION_LIMIT_CPD = 60.0  # same cap harmonic_analysis.py uses
N_HARMONICS_MAX = 40             # same default harmonic_analysis.py uses

_PSF_CACHE = {}
_NEFF_CACHE = {}


def n_eff_cached(pitch_um, D_pupil_um, packing, n_offsets):
    """Memoised array_photometry.n_holes_exact_sweep_alignment (a pure function of its
    four arguments -- verified by reading it: no state, no randomness). Caching only;
    the counting itself is that module's, unchanged. Matters because the design-space
    grids call it once per (aperture, pitch, M) while it depends on pitch alone."""
    key = (pitch_um, D_pupil_um, packing, n_offsets)
    if key not in _NEFF_CACHE:
        _NEFF_CACHE[key] = n_holes_exact_sweep_alignment(
            pitch_um, D_pupil_um, packing=packing, n_offsets=n_offsets)
    return _NEFF_CACHE[key]


def assert_corrected_optics():
    """Runtime provenance gate: the loaded phase2_retina must be stage2_fixed's
    post-lens-wavelength-fix copy. Called by every driver script in this folder."""
    f = os.path.abspath(sys.modules["phase2_retina"].__file__)
    assert os.path.basename(os.path.dirname(f)) == "stage2_fixed", \
        f"phase2_retina resolved to {f} -- expected stage2_fixed/"
    src = open(f).read()
    assert "field = lens_phase(field, dx, effective_wavelength, f_eye)" in src, \
        f"{f} is the PRE-lens-wavelength-fix code (lens_phase not given the effective wavelength)"
    return f


def psf_for(a_hole_um, M_diopters, wavelength_nm=550.0, d_gap_mm=12.0, D_pupil_um=4000.0,
            P0=60.0, n_prime=1.336, grid_N=2048, window_L_mm=6.0,
            refractive_index_correction=True):
    """Runs (or returns cached) phase2_retina.run_pipeline_point and its radial MTF.
    Returns None if the junction gate rejected the point -- never a silent substitute."""
    key = (a_hole_um, M_diopters, wavelength_nm, d_gap_mm, D_pupil_um, P0, n_prime,
           grid_N, window_L_mm, refractive_index_correction)
    if key in _PSF_CACHE:
        return _PSF_CACHE[key]

    result = p2.run_pipeline_point(
        a_hole=a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9, d_gap=d_gap_mm * 1e-3,
        grid_N=grid_N, window_L_mm=window_L_mm, M_diopters=M_diopters, P0=P0,
        n_prime=n_prime, D_pupil_um=D_pupil_um,
        refractive_index_correction=refractive_index_correction)
    if not result["junction_check_passed"]:
        _PSF_CACHE[key] = {"ok": False, "reason": result["junction_fail_reason"]}
        return _PSF_CACHE[key]

    dx = result["cornea_result"]["dx"]
    f_centers, mtf_1d = mtf_radial(result["I_retina"], dx)
    _PSF_CACHE[key] = {
        "ok": True, "f_centers_cpum": f_centers, "mtf_1d": mtf_1d,
        "v_r_um": result["myopia"]["L_ax"] * 1e6,
        "v_f_um": result["myopia"]["f_eye"] * 1e6,
        "r_EE_50_um": result["retina_EE"]["r_EE_50"] * 1e6,
        "r_EE_80_um": result["retina_EE"]["r_EE_80"] * 1e6,
        "reason": None,
    }
    return _PSF_CACHE[key]


def delta_r_um(pitch_um, psf, d_gap_mm, separation_model):
    if separation_model == "corrected":
        return gs.delta_r_corrected_um(pitch_um, psf["v_r_um"], psf["v_f_um"])
    if separation_model == "legacy":
        return gs.delta_r_legacy_um(pitch_um, psf["v_r_um"], d_gap_mm * 1e3)
    raise ValueError("separation_model must be 'corrected' or 'legacy'")


def margin_detail(a_hole_um, pitch_um, M_diopters, separation_model="corrected",
                   wavelength_nm=550.0, d_gap_mm=12.0, D_pupil_um=4000.0, P0=60.0,
                   n_prime=1.336, grid_N=2048, window_L_mm=6.0,
                   scene_luminance_cdm2=10000.0, field_deg=10.0):
    """
    THEORY.md Eq. (5)'s perceptibility-margin computation, WITHOUT the N_eff<=1 early
    return classify() applies below -- i.e. "what would the fundamental/harmonic margin
    be AT this (a, s, M), independent of how often 2+ holes are actually in the pupil".

    Split out of classify() (which used to inline all of this) so ghosting_risk.py can
    ask for a margin on its own terms: F2 found Regime A is decided on the alignment
    MINIMUM (right for brightness, wrong for ghosting -- a pitch with N_eff_worst<=1
    can still have 2+ holes in the pupil most of the time), so a continuous risk needs
    the margin available regardless of what N_eff_worst happens to be. classify() still
    gates on N_eff_worst<=1 for its own A/B/C answer; this function does not gate at
    all, and is the single implementation both now call -- verified identical to the
    pre-split classify() by self_check() below, which still passes unchanged.

    Returns a dict: ok (bool), reason, delta_r_um, f0_cpd, mtf_f0, csf_threshold_f0,
    fundamental_margin, worst_n, worst_margin, worst_f_cpd. Margins are 0.0 (not None)
    when there is genuinely no comb to perceive (M=0 under the corrected model, or f0
    beyond the eye's resolution limit) -- a real, meaningful zero, not a missing value.
    """
    psf = psf_for(a_hole_um, M_diopters, wavelength_nm, d_gap_mm, D_pupil_um, P0,
                  n_prime, grid_N, window_L_mm)
    if not psf["ok"]:
        return {"ok": False, "reason": f"junction check failed: {psf['reason']}",
                "delta_r_um": None, "f0_cpd": None, "mtf_f0": None,
                "csf_threshold_f0": None, "fundamental_margin": None,
                "worst_n": None, "worst_margin": None, "worst_f_cpd": None}

    d_r = delta_r_um(pitch_um, psf, d_gap_mm, separation_model)
    if d_r <= 0:  # M=0 under the corrected model: no separation at all, no comb exists
        return {"ok": True, "delta_r_um": 0.0, "f0_cpd": None, "mtf_f0": None,
                "csf_threshold_f0": None, "fundamental_margin": 0.0,
                "worst_n": None, "worst_margin": 0.0, "worst_f_cpd": None,
                "reason": "delta_r=0 (no defocus): every hole's image coincides, no ghost comb"}

    f0_cpum, f0_cpd = gs.f0_from_delta_r(d_r, psf["v_r_um"])

    ns, freqs, margins = [], [], []
    for n in range(1, N_HARMONICS_MAX + 1):
        f_cpd = n * f0_cpd
        if f_cpd > EYE_RESOLUTION_LIMIT_CPD:
            break
        mtf_val = interp_mtf_at_freq(psf["f_centers_cpum"], psf["mtf_1d"], n * f0_cpum)
        thresh = csf_threshold_barten(f_cpd, scene_luminance_cdm2, field_deg)
        ns.append(n); freqs.append(f_cpd)
        margins.append(mtf_val / thresh if thresh > 0 else float("inf"))

    if not ns:  # even the fundamental is past the eye's resolution limit
        return {"ok": True, "delta_r_um": d_r, "f0_cpd": f0_cpd, "mtf_f0": None,
                "csf_threshold_f0": None, "fundamental_margin": 0.0,
                "worst_n": None, "worst_margin": 0.0, "worst_f_cpd": None,
                "reason": f"f0={f0_cpd:.1f} cpd exceeds the eye's resolution limit "
                          f"({EYE_RESOLUTION_LIMIT_CPD:g} cpd): comb unresolvable"}

    mtf_f0 = interp_mtf_at_freq(psf["f_centers_cpum"], psf["mtf_1d"], f0_cpum)
    csf_f0 = csf_threshold_barten(f0_cpd, scene_luminance_cdm2, field_deg)
    margins = np.asarray(margins)
    worst_idx = int(np.argmax(margins))

    return {
        "ok": True, "delta_r_um": d_r, "f0_cpd": f0_cpd, "mtf_f0": mtf_f0,
        "csf_threshold_f0": csf_f0, "fundamental_margin": float(margins[0]),
        "worst_n": ns[worst_idx], "worst_margin": float(margins[worst_idx]),
        "worst_f_cpd": freqs[worst_idx],
        "reason": ("fundamental below CSF threshold" if margins[0] < 1.0
                   else "fundamental above CSF threshold -- danger zone"),
    }


def classify(a_hole_um, pitch_um, M_diopters, separation_model="corrected",
             wavelength_nm=550.0, d_gap_mm=12.0, D_pupil_um=4000.0, P0=60.0,
             n_prime=1.336, grid_N=2048, window_L_mm=6.0, packing="square",
             n_offsets=15, scene_luminance_cdm2=10000.0, field_deg=10.0):
    """
    THEORY.md Eq. (5), with the ghost separation supplied by `separation_model`.

    Returns regime_fundamental (Pass 2's rule: B if MTF(f0) < CSF_threshold(f0)) AND
    regime_harmonic (Pass 3's rule: B only if EVERY harmonic n*f0 up to the eye's
    resolution limit is below threshold) -- reported separately rather than collapsed,
    because which one is used is exactly what changed between Pass 2 and Pass 3.
    """
    n_min, n_mean, n_max_align = n_eff_cached(pitch_um, D_pupil_um, packing, n_offsets)
    base = {"a_hole_um": a_hole_um, "pitch_um": pitch_um, "M_diopters": M_diopters,
            "separation_model": separation_model, "N_eff_worst": n_min,
            "N_eff_mean": n_mean, "N_eff_best": n_max_align}
    if n_min <= 1:
        return {**base, "regime_fundamental": "A", "regime_harmonic": "A",
                "delta_r_um": None, "f0_cpd": None, "mtf_f0": None,
                "csf_threshold_f0": None, "fundamental_margin": None,
                "worst_n": None, "worst_margin": None, "worst_f_cpd": None,
                "reason": "N_eff(worst-case alignment)<=1: no second hole simultaneously active"}

    detail = margin_detail(a_hole_um, pitch_um, M_diopters, separation_model,
                           wavelength_nm, d_gap_mm, D_pupil_um, P0, n_prime, grid_N,
                           window_L_mm, scene_luminance_cdm2, field_deg)
    if not detail["ok"]:
        return {**base, "regime_fundamental": None, "regime_harmonic": None,
                **{k: v for k, v in detail.items() if k != "ok"}}
    if detail["mtf_f0"] is None:
        # delta_r=0 or f0 beyond resolution: margin is a real 0.0, both rules say B.
        return {**base, "regime_fundamental": "B", "regime_harmonic": "B",
                **{k: v for k, v in detail.items() if k != "ok"}}

    is_b_fundamental = detail["fundamental_margin"] < 1.0
    is_b_harmonic = detail["worst_margin"] < 1.0
    return {
        **base, **{k: v for k, v in detail.items() if k != "ok"},
        "regime_fundamental": "B" if is_b_fundamental else "C",
        "regime_harmonic": "B" if is_b_harmonic else "C",
    }


def self_check(verbose=True):
    """Asserts this module's legacy path reproduces ghosting_regime.py's own answer
    (regime + f0 + MTF(f0) + CSF threshold) rather than assuming the refactor is
    faithful. Uses one Regime-A and one Regime-C point."""
    import ghosting_regime as gr
    ok = True
    for a_um, s_um, M in [(400.0, 900.0, 4.0), (400.0, 3200.0, 4.0)]:
        ref = gr.classify_ghosting_regime(a_hole_um=a_um, pitch_um=s_um, D_pupil_um=4000.0,
                                          wavelength_nm=550.0, d_gap_mm=12.0, M_diopters=M)
        mine = classify(a_um, s_um, M, separation_model="legacy")
        same_regime = ref["regime"] == mine["regime_fundamental"]
        same_neff = ref["N_eff_worst"] == mine["N_eff_worst"]
        same_f0 = (ref["f0_cpd"] is None and mine["f0_cpd"] is None) or \
                  abs(ref["f0_cpd"] - mine["f0_cpd"]) < 1e-9
        same_mtf = (ref["mtf_f0"] is None and mine["mtf_f0"] is None) or \
                   abs(ref["mtf_f0"] - mine["mtf_f0"]) < 1e-12
        good = same_regime and same_neff and same_f0 and same_mtf
        ok = ok and good
        if verbose:
            print(f"  self_check a={a_um:.0f}um s={s_um:.0f}um M={M:.0f}D: "
                  f"ghosting_regime={ref['regime']} corrected_regime(legacy)="
                  f"{mine['regime_fundamental']} -> {'MATCH' if good else 'MISMATCH'}")
    assert ok, "corrected_regime.classify(legacy) does not reproduce ghosting_regime.py"
    return ok


if __name__ == "__main__":
    print(f"phase2_retina in use: {assert_corrected_optics()}")
    self_check()
