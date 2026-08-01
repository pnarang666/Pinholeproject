"""Stage 4 orchestrator built on top of the existing Stage 2/3 pipeline."""

import os
import sys

_STAGE2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage2"))
_STAGE3_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage3_human_vision"))
for _path in (_STAGE2_DIR, _STAGE3_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import phase2_retina as stage2_retina  # noqa: E402
import metrics as stage3_metrics  # noqa: E402

from .acuity import predict_acuity
from .adaptation import adaptation_state
from .config import load_default_config
from .csf import evaluate_csf_models, weight_mtf_with_csf
from .illuminance import solve_pupil_and_retinal_illuminance
from .optical_quality import compute_optical_quality
from .photon_noise import photon_flux_and_snr
from .types import VisualPerformanceResult
from .visual_strehl import compute_vsotf


def run_stage4_point(
        a_hole_um,
        wavelength_nm,
        d_gap_mm,
        M_diopters,
        grid_N=2048,
        window_L_mm=6.0,
        scene_luminance_cdm2=None,
        field_diameter_deg=None,
        age_years=None,
        eyes=None,
        D_pupil_um=4000.0,
        P0=60.0,
        n_prime=1.336,
        refractive_index_correction=True,
        adaptation_enabled=True,
        config=None):
    config = config or load_default_config()
    scene_luminance_cdm2 = scene_luminance_cdm2 or config.pipeline.default_scene_luminance_cdm2
    field_diameter_deg = field_diameter_deg or config.pipeline.default_field_diameter_deg
    age_years = age_years or config.pipeline.default_age_years
    eyes = eyes or config.pipeline.default_eyes

    a_hole_m = a_hole_um * 1e-6
    wavelength_m = wavelength_nm * 1e-9
    d_gap_m = d_gap_mm * 1e-3

    stage2_result = stage2_retina.run_pipeline_point(
        a_hole=a_hole_m,
        wavelength=wavelength_m,
        d_gap=d_gap_m,
        grid_N=grid_N,
        window_L_mm=window_L_mm,
        M_diopters=M_diopters,
        P0=P0,
        n_prime=n_prime,
        D_pupil_um=D_pupil_um,
        refractive_index_correction=refractive_index_correction
    )

    if not stage2_result["junction_check_passed"]:
        return VisualPerformanceResult(
            junction_check_passed=False,
            optical_quality={},
            pupil={},
            illuminance={},
            adaptation={},
            csf={},
            visual_strehl={},
            photon_noise={},
            acuity={},
            metadata={
                "junction_fail_reason": stage2_result["junction_fail_reason"],
                "suggested_grid_N": stage2_result["suggested_grid_N"]
            }
        )

    psf = stage2_result["I_retina"]
    dx_m = stage2_result["cornea_result"]["dx"]
    v_r_m = stage2_result["myopia"]["L_ax"]
    diffraction_reference = stage3_metrics.get_diffraction_limited_reference(
        a_hole=a_hole_m,
        wavelength=wavelength_m,
        d_gap=d_gap_m,
        D_pupil_um=D_pupil_um,
        P0=P0,
        n_prime=n_prime,
        refractive_index_correction=refractive_index_correction,
        grid_N=grid_N,
        window_L_mm=window_L_mm
    )

    optical = compute_optical_quality(psf, dx_m, v_r_m, diffraction_reference_psf=diffraction_reference)
    pupil_and_illum = solve_pupil_and_retinal_illuminance(
        scene_luminance_cdm2=scene_luminance_cdm2,
        pinhole_diameter_mm=a_hole_um * 1e-3,
        field_diameter_deg=field_diameter_deg,
        age_years=age_years,
        eyes=eyes,
        config=config
    )
    adaptation = adaptation_state(
        pupil_and_illum["retinal_illuminance_photopic_td"],
        enabled=adaptation_enabled,
        config=config
    )
    csf_summary = evaluate_csf_models(
        optical["mtf_frequency_cpd"],
        luminance_cdm2=scene_luminance_cdm2,
        field_diameter_deg=field_diameter_deg,
        config=config
    )

    weighted_models = {}
    for name, summary in csf_summary.items():
        weighted_models[name] = weight_mtf_with_csf(optical["mtf_frequency_cpd"], optical["mtf"], summary["values"])

    default_csf = csf_summary[config.csf.default_model]
    visual_strehl = compute_vsotf(
        freq_cpd=optical["mtf_frequency_cpd"],
        otf_real=optical["otf_real"],
        ref_freq_cpd=optical["mtf_frequency_cpd"],
        ref_otf_real=compute_optical_quality(diffraction_reference, dx_m, v_r_m)["otf_real"],
        neural_weights=default_csf["values"]
    )
    photon_noise = photon_flux_and_snr(
        scene_luminance_cdm2=scene_luminance_cdm2,
        stop_diameter_m=pupil_and_illum["effective_stop_diameter_mm"] * 1e-3,
        v_r_m=v_r_m,
        wavelength_m=wavelength_m,
        config=config
    )
    acuity = predict_acuity(
        mtf10_cpd=optical["mtf10_cpd"],
        mtf50_cpd=optical["mtf50_cpd"],
        vsotf=visual_strehl["vsotf"],
        snr=photon_noise["snr"],
        retinal_illuminance_td=pupil_and_illum["retinal_illuminance_photopic_td"],
        config=config
    )
    return VisualPerformanceResult(
        junction_check_passed=True,
        optical_quality=optical,
        pupil={
            "natural_pupil_diameter_mm": pupil_and_illum["natural_pupil_diameter_mm"],
            "natural_pupil_area_mm2": pupil_and_illum["natural_pupil_area_mm2"],
            "effective_stop_diameter_mm": pupil_and_illum["effective_stop_diameter_mm"],
            "effective_stop_area_mm2": pupil_and_illum["effective_stop_area_mm2"]
        },
        illuminance=pupil_and_illum,
        adaptation=adaptation,
        csf={
            "models": csf_summary,
            "weighted_mtf": weighted_models,
            "recommended_model": config.csf.default_model
        },
        visual_strehl=visual_strehl,
        photon_noise=photon_noise,
        acuity=acuity,
        metadata={
            "scene_luminance_cdm2": scene_luminance_cdm2,
            "field_diameter_deg": field_diameter_deg,
            "age_years": age_years,
            "eyes": eyes,
            "M_diopters": M_diopters
        }
    )
