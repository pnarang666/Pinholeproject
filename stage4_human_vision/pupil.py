"""Watson-Yellott pupil model."""

import math

from .config import load_default_config


def monocular_attenuation(eyes, config=None):
    config = config or load_default_config()
    return config.pupil.binocular_attenuation if int(eyes) == 2 else config.pupil.monocular_attenuation


def effective_corneal_flux_density(luminance_cdm2, field_area_deg2, eyes, config=None):
    config = config or load_default_config()
    return max(luminance_cdm2, 1e-9) * max(field_area_deg2, 1e-9) * monocular_attenuation(eyes, config)


def field_area_deg2(field_diameter_deg):
    radius_deg = max(field_diameter_deg, 1e-9) / 2.0
    return math.pi * radius_deg * radius_deg


def stanley_davies_pupil_mm(flux_density, config=None):
    config = config or load_default_config()
    p = config.pupil
    ratio = math.pow(max(flux_density, 1e-9) / p.stanley_davies_numerator, p.stanley_davies_exponent)
    return p.stanley_davies_max_mm - p.stanley_davies_span_mm * (ratio / (ratio + p.stanley_davies_offset))


def age_slope_mm_per_year(flux_density, config=None):
    config = config or load_default_config()
    p = config.pupil
    d_sd = stanley_davies_pupil_mm(flux_density, config)
    return p.age_slope_intercept - p.age_slope_dsd_coeff * d_sd


def equivalent_age_years(age_years, config=None):
    config = config or load_default_config()
    p = config.pupil
    if age_years >= 20.0:
        return age_years
    return p.young_age_offset + p.young_age_exp_coeff * math.exp(-age_years / p.young_age_exp_denominator)


def watson_yellott_pupil_mm(luminance_cdm2, field_diameter_deg, age_years, eyes=2, config=None):
    """
    Watson & Yellott (2012) unified pupil model.

    The implementation follows the paper's simplified formulas for ages >= 20 and
    uses the paper's equivalent-age extension for younger ages.
    """
    config = config or load_default_config()
    p = config.pupil
    age_equiv = equivalent_age_years(age_years, config)
    flux_density = effective_corneal_flux_density(
        luminance_cdm2=luminance_cdm2,
        field_area_deg2=field_area_deg2(field_diameter_deg),
        eyes=eyes,
        config=config
    )
    d_ref = stanley_davies_pupil_mm(flux_density, config)
    diameter = d_ref + (age_equiv - p.reference_age_years) * age_slope_mm_per_year(flux_density, config)
    return max(p.minimum_diameter_mm, min(p.maximum_diameter_mm, diameter))
