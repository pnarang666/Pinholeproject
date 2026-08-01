"""Retinal illuminance and pupil-illumination coupling."""

import math

from .config import load_default_config
from . import pupil as pupil_model


def pupil_area_mm2(diameter_mm):
    radius_mm = diameter_mm / 2.0
    return math.pi * radius_mm * radius_mm


def effective_stop_mm(natural_pupil_diameter_mm, pinhole_diameter_mm):
    return min(max(natural_pupil_diameter_mm, 1e-9), max(pinhole_diameter_mm, 1e-9))


def retinal_illuminance_trolands(scene_luminance_cdm2, stop_diameter_mm):
    return max(scene_luminance_cdm2, 0.0) * pupil_area_mm2(stop_diameter_mm)


def solve_pupil_and_retinal_illuminance(
        scene_luminance_cdm2,
        pinhole_diameter_mm,
        field_diameter_deg,
        age_years,
        eyes=2,
        config=None):
    config = config or load_default_config()
    max_iter = config.pipeline.pupil_iteration_max_iter
    tol_mm = config.pipeline.pupil_iteration_tol_mm

    pupil_mm = pupil_model.watson_yellott_pupil_mm(
        luminance_cdm2=scene_luminance_cdm2,
        field_diameter_deg=field_diameter_deg,
        age_years=age_years,
        eyes=eyes,
        config=config
    )

    iterations = 0
    equivalent_luminance = scene_luminance_cdm2
    trolands = retinal_illuminance_trolands(scene_luminance_cdm2, effective_stop_mm(pupil_mm, pinhole_diameter_mm))

    for iterations in range(1, max_iter + 1):
        stop_mm = effective_stop_mm(pupil_mm, pinhole_diameter_mm)
        trolands = retinal_illuminance_trolands(scene_luminance_cdm2, stop_mm)
        equivalent_luminance = trolands / max(pupil_area_mm2(pupil_mm), 1e-9)
        new_pupil_mm = pupil_model.watson_yellott_pupil_mm(
            luminance_cdm2=equivalent_luminance,
            field_diameter_deg=field_diameter_deg,
            age_years=age_years,
            eyes=eyes,
            config=config
        )
        if abs(new_pupil_mm - pupil_mm) <= tol_mm:
            pupil_mm = new_pupil_mm
            break
        pupil_mm = new_pupil_mm

    stop_mm = effective_stop_mm(pupil_mm, pinhole_diameter_mm)
    area_mm2 = pupil_area_mm2(pupil_mm)
    stop_area_mm2 = pupil_area_mm2(stop_mm)
    trolands = retinal_illuminance_trolands(scene_luminance_cdm2, stop_mm)
    return {
        "natural_pupil_diameter_mm": pupil_mm,
        "natural_pupil_area_mm2": area_mm2,
        "effective_stop_diameter_mm": stop_mm,
        "effective_stop_area_mm2": stop_area_mm2,
        "retinal_illuminance_photopic_td": trolands,
        "retinal_illuminance_mesopic_td": trolands,
        "retinal_illuminance_scotopic_td": trolands,
        "equivalent_adapting_luminance_cdm2": equivalent_luminance,
        "iterations": iterations
    }
