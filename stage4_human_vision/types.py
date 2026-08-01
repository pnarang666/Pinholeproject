"""Typed containers for Stage 4 inputs and outputs."""

from typing import Dict, Optional

try:
    from dataclasses import dataclass, field
except ImportError:  # pragma: no cover
    dataclass = None
    field = None


def _dataclass(cls):
    return dataclass(cls) if dataclass is not None else cls


@_dataclass
class RetinalInput(object):
    psf: object
    dx_m: float
    wavelength_m: float
    v_r_m: float
    aperture_diameter_m: float
    scene_luminance_cdm2: float
    field_diameter_deg: float
    age_years: float
    eyes: int
    diffraction_reference_psf: Optional[object] = None


@_dataclass
class VisualPerformanceResult(object):
    junction_check_passed: bool
    optical_quality: Dict[str, object]
    pupil: Dict[str, float]
    illuminance: Dict[str, float]
    adaptation: Dict[str, float]
    csf: Dict[str, object]
    visual_strehl: Dict[str, float]
    photon_noise: Dict[str, float]
    acuity: Dict[str, object]
    metadata: Dict[str, object]
