"""
Thin orchestration wrapper for the Streamlit app: one run_pipeline_point() call plus
stage3_human_vision's metrics/photometry/visual_acuity functions, for ONE point. No
physics logic lives here -- everything is a call into stage2_fixed or
stage3_human_vision, exactly the same import-boundary rule stage2_fixed/
pipeline_junction.py already established for stage1_v2.

Measured timing (this machine): grid_N=512 ~0.18s, grid_N=2048 ~5s -- see
streamlit_app.py for how this drives the interactive-vs-high-accuracy split.
"""

import os
import sys
import time

import numpy as np

_STAGE2_FIXED_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage2_fixed"))
_STAGE3HV_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage3_human_vision"))
for _d in (_STAGE2_FIXED_DIR, _STAGE3HV_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import phase2_retina as p2  # noqa: E402
import pipeline_junction as junction  # noqa: E402
import myopia_axial  # noqa: E402
import metrics  # noqa: E402
import photometry  # noqa: E402
import visual_acuity  # noqa: E402
import contrast  # noqa: E402

EE_PERCENTILES = (0.50, 0.70, 0.80, 0.90)


def compute_point(a_hole_um, wavelength_nm, M_diopters, d_gap_mm, D_pupil_um,
                   P0=60.0, n_prime=1.336, refractive_index_correction=True,
                   grid_N=512, window_L_mm=6.0):
    """
    Returns a dict with the raw field (I_retina, dx), every scalar metric this
    project has defined, and the actual wall-clock compute time -- so the UI can
    always show real elapsed time next to the number, never a hidden/assumed one.
    """
    t0 = time.time()

    a_hole = a_hole_um * 1e-6
    wavelength = wavelength_nm * 1e-9
    d_gap = d_gap_mm * 1e-3

    result = p2.run_pipeline_point(
        a_hole=a_hole, wavelength=wavelength, d_gap=d_gap, grid_N=grid_N, window_L_mm=window_L_mm,
        M_diopters=M_diopters, P0=P0, n_prime=n_prime, D_pupil_um=D_pupil_um,
        refractive_index_correction=refractive_index_correction,
    )

    out = {
        "a_hole_um": a_hole_um, "wavelength_nm": wavelength_nm, "M_diopters": M_diopters,
        "d_gap_mm": d_gap_mm, "D_pupil_um": D_pupil_um, "grid_N": grid_N, "window_L_mm": window_L_mm,
        "junction_check_passed": result["junction_check_passed"],
        "junction_fail_reason": result["junction_fail_reason"],
        "compute_time_s": None,  # set at the end, includes every downstream metric too
    }
    if not result["junction_check_passed"]:
        out["compute_time_s"] = time.time() - t0
        return out

    I = result["I_retina"]
    dx = result["cornea_result"]["dx"]
    v_r = result["myopia"]["L_ax"]

    I_dl = metrics.get_diffraction_limited_reference(
        a_hole, wavelength, d_gap, D_pupil_um, P0=P0, n_prime=n_prime,
        refractive_index_correction=refractive_index_correction, grid_N=grid_N, window_L_mm=window_L_mm)
    m = metrics.compute_all_metrics(
        a_hole, wavelength, d_gap, M_diopters, D_pupil_um, P0=P0, n_prime=n_prime,
        refractive_index_correction=refractive_index_correction, grid_N=grid_N,
        window_L_mm=window_L_mm, precomputed_I_dl=I_dl)

    flux = photometry.photon_flux_at_retina(a_hole_um, v_r, wavelength)
    acuity = visual_acuity.acuity_from_mtf_cutoff(m["mtf50_cpd"], m["mtf10_cpd"])
    rel_ill = photometry.relative_retinal_illuminance(a_hole_um, D_pupil_um)

    # r_EE(70%) -- phase2_retina.retinal_encircled_energy only ever hardcodes 50/80/90
    # (unchanged, not modified here); this reuses the SAME junction.encircled_energy/
    # r_for_EE calls on the raw I_retina field it already returns, exactly the pattern
    # stage2_fixed/recompute_multi_EE.py already established for stage3a's data.
    N = I.shape[0]
    _, _, R, _ = junction.make_grid(N, N * dx)
    r_edges, EE, _ = junction.encircled_energy(I, R, dx)
    r_ee_70_um = junction.r_for_EE(r_edges, EE, 0.70) * 1e6

    # Rose-DeVries SNR-bound acuity and CSF-weighted visual Strehl (VSOTF, approximate
    # fidelity -- see visual_acuity.visual_strehl_approx docstring) -- both already
    # implemented in stage3_human_vision, just not previously wired into the live
    # single-point path.
    rd_mar = visual_acuity.snr_acuity_bound(flux["photon_flux_density_per_s_per_m2"])
    rd_snellen = visual_acuity.mar_to_snellen_denominator(rd_mar)

    # OTF (complex), not just MTF -- needed for the VSOTF calls below, which weight
    # Re(OTF) rather than |OTF| (see visual_acuity.visual_strehl_approx docstring).
    # mtf_actual/mtf_dl (|OTF|) are still derived here for the existing MTF-vs-CSF
    # overlay plot in streamlit_app.py, which is unaffected by this change.
    f_cpum, otf_actual = metrics.otf_radial(I, dx)
    f_cpd = metrics.cycles_per_um_to_cycles_per_degree(f_cpum, v_r)
    f_cpum_dl, otf_dl = metrics.otf_radial(I_dl, dx)
    f_cpd_dl = metrics.cycles_per_um_to_cycles_per_degree(f_cpum_dl, v_r)
    mtf_actual = np.abs(otf_actual)
    mask = (f_cpd > 0) & (f_cpd <= 60)
    mask_dl = (f_cpd_dl > 0) & (f_cpd_dl <= 60)
    vsotf_photopic = visual_acuity.visual_strehl_approx(
        f_cpd[mask], otf_actual[mask], f_cpd_dl[mask_dl], otf_dl[mask_dl], csf_model="photopic_4cpd")
    vsotf_mannos = visual_acuity.visual_strehl_approx(
        f_cpd[mask], otf_actual[mask], f_cpd_dl[mask_dl], otf_dl[mask_dl], csf_model="mannos_sakrison_8cpd")

    out.update(m)
    out.update(flux)
    out.update(acuity)
    out["relative_retinal_illuminance"] = rel_ill
    out["r_EE_70_um"] = r_ee_70_um
    out["rose_devries_mar_arcmin"] = rd_mar
    out["rose_devries_snellen_denom"] = rd_snellen
    out["visual_strehl_photopic"] = vsotf_photopic
    out["visual_strehl_mannos_sakrison"] = vsotf_mannos
    out["mtf_freq_cpd"] = f_cpd
    out["mtf_values"] = mtf_actual
    out["I_retina"] = I
    out["dx_m"] = dx
    out["v_r_m"] = v_r
    out["L0_mm"] = result["myopia"]["L0"] * 1e3
    out["f_eye_mm"] = result["myopia"]["f_eye"] * 1e3
    out["compute_time_s"] = time.time() - t0
    return out


def myopia_guard(M_diopters, P0):
    """Clean warning (not a crash) for myopia_axial's M_diopters<P0 requirement."""
    if M_diopters >= P0:
        return f"M_diopters ({M_diopters:.1f}D) must be less than P0 ({P0:.1f}D) -- reduce M or raise P0."
    return None
