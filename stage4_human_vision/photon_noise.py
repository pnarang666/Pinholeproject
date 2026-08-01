"""Photon flux and shot-noise estimates."""

import math

from .config import load_default_config


def photon_energy_j(wavelength_m, config=None):
    config = config or load_default_config()
    return config.photon_noise.planck_constant_j_s * config.photon_noise.speed_of_light_m_s / wavelength_m


def retinal_irradiance_w_m2(scene_luminance_cdm2, stop_diameter_m, v_r_m, ocular_transmission=None, wavelength_m=None, config=None):
    config = config or load_default_config()
    ocular_transmission = ocular_transmission or config.photon_noise.ocular_transmission
    if wavelength_m is None:
        wavelength_m = 555e-9
    photopic_luminous_efficacy = 683.0
    radiance_w_sr_m2 = scene_luminance_cdm2 / photopic_luminous_efficacy
    f_number = v_r_m / max(stop_diameter_m, 1e-12)
    return math.pi * radiance_w_sr_m2 * ocular_transmission / (4.0 * f_number * f_number)


def photon_flux_and_snr(scene_luminance_cdm2, stop_diameter_m, v_r_m, wavelength_m, config=None):
    config = config or load_default_config()
    irradiance = retinal_irradiance_w_m2(
        scene_luminance_cdm2=scene_luminance_cdm2,
        stop_diameter_m=stop_diameter_m,
        v_r_m=v_r_m,
        ocular_transmission=config.photon_noise.ocular_transmission,
        wavelength_m=wavelength_m,
        config=config
    )
    energy = photon_energy_j(wavelength_m, config)
    flux_density = irradiance / max(energy, 1e-30)
    integration_area_m2 = config.photon_noise.integration_area_mm2 * 1e-6
    expected_photons = (
        flux_density
        * integration_area_m2
        * config.photon_noise.integration_time_s
        * config.photon_noise.quantum_efficiency
    )
    noise_sigma = math.sqrt(max(expected_photons, 0.0))
    return {
        "retinal_irradiance_w_m2": irradiance,
        "photon_flux_density_per_s_m2": flux_density,
        "expected_photons": expected_photons,
        "shot_noise_sigma": noise_sigma,
        "snr": expected_photons / noise_sigma if noise_sigma > 0 else 0.0
    }
