"""Configuration loaders for Stage 4 constants."""

import json
import os

try:
    from dataclasses import dataclass
except ImportError:  # pragma: no cover
    dataclass = None


def _dataclass(cls):
    return dataclass(cls) if dataclass is not None else cls


@_dataclass
class PupilConfig(object):
    reference_age_years: float
    monocular_attenuation: float
    binocular_attenuation: float
    stanley_davies_numerator: float
    stanley_davies_exponent: float
    stanley_davies_max_mm: float
    stanley_davies_span_mm: float
    stanley_davies_offset: float
    age_slope_intercept: float
    age_slope_dsd_coeff: float
    young_age_offset: float
    young_age_exp_coeff: float
    young_age_exp_denominator: float
    minimum_diameter_mm: float
    maximum_diameter_mm: float


@_dataclass
class AdaptationConfig(object):
    r_max: float
    semi_saturation_trolands: float
    exponent: float


@_dataclass
class CSFConfig(object):
    default_model: str
    watson_peak_cpd: float
    watson_bandwidth_octaves: float
    mannos_scale: float
    mannos_offset: float
    mannos_slope: float
    mannos_exponent: float
    barten_c: float
    barten_k: float
    barten_temporal_integration_s: float
    barten_x0_deg: float
    barten_xmax_deg: float
    barten_nmax: float
    barten_sigma0_deg: float


@_dataclass
class PhotonNoiseConfig(object):
    planck_constant_j_s: float
    speed_of_light_m_s: float
    ocular_transmission: float
    quantum_efficiency: float
    integration_time_s: float
    integration_area_mm2: float


@_dataclass
class AcuityConfig(object):
    cycles_per_degree_at_20_20: float


@_dataclass
class BrightnessAcuityConfig(object):
    """Cited separately from photon_noise -- see literature.py's
    tidbury_2016_illuminance_slope and van_nes_bouman_1967_weber_knee entries.
    Not the same source as photon_noise's constants, so kept in its own block."""
    logmar_per_log10_illuminance: float
    weber_knee_td: float


@_dataclass
class PipelineConfig(object):
    default_scene_luminance_cdm2: float
    default_field_diameter_deg: float
    default_age_years: float
    default_eyes: int
    default_pupil_mode: str
    pupil_iteration_max_iter: int
    pupil_iteration_tol_mm: float


@_dataclass
class Stage4Config(object):
    citations: dict
    pupil: PupilConfig
    adaptation: AdaptationConfig
    csf: CSFConfig
    photon_noise: PhotonNoiseConfig
    acuity: AcuityConfig
    brightness_acuity: BrightnessAcuityConfig
    pipeline: PipelineConfig


def _constants_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "constants.json")


def load_default_config():
    with open(_constants_path(), "r") as fh:
        raw = json.load(fh)
    return Stage4Config(
        citations=raw["citations"],
        pupil=PupilConfig(**raw["pupil"]),
        adaptation=AdaptationConfig(**raw["adaptation"]),
        csf=CSFConfig(**raw["csf"]),
        photon_noise=PhotonNoiseConfig(**raw["photon_noise"]),
        acuity=AcuityConfig(**raw["acuity"]),
        brightness_acuity=BrightnessAcuityConfig(**raw["brightness_acuity"]),
        pipeline=PipelineConfig(**raw["pipeline"])
    )
