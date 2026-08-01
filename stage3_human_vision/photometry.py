"""
Photometric chain: scene luminance -> corneal/retinal irradiance -> photon flux ->
relative retinal illuminance (pinhole vs. the natural, undilated pupil).

Does NOT assume constant illumination -- power admitted scales with aperture AREA
(a_hole^2), per literature.get('throughput_area_ratio'). Every equation here traces to
literature.py; free/unverified numeric choices (scene luminance level, ocular
transmission factor) are exposed as function arguments with a cited default range, not
hardcoded silently.
"""

import numpy as np

import literature
import metrics

H_PLANCK = 6.62607015e-34   # J*s (SI defined constant)
C_LIGHT = 299792458.0       # m/s (SI defined constant)
PHOTOPIC_LUMINOUS_EFFICACY_MAX = 683.0  # lm/W at 555nm -- literature.get('photopic_luminous_efficacy')

# Standard CIE 1931 photopic luminosity function V(lambda) at this project's 3 test
# wavelengths -- literature.get('photopic_luminous_efficacy'). These are the commonly
# tabulated values; consult the official CIE table (cie.co.at) directly if better than
# ~5% precision is ever needed.
V_LAMBDA = {450e-9: 0.038, 550e-9: 0.995, 650e-9: 0.107}

# Representative outdoor scene luminance (cd/m^2). Real daylight spans roughly
# 3,000-7,000 cd/m^2 (overcast) to 5,000-30,000+ cd/m^2 (direct sun) -- see README.md
# for search citations. This default is a commonly-used single "average daylight"
# figure, NOT a precise measurement; override via the scene_luminance_cdm2 argument.
DEFAULT_SCENE_LUMINANCE_CDM2 = 10000.0

# HEURISTIC (not a specific cited source -- see literature.py's classification
# scheme): approximate overall ocular-media (cornea+aqueous+lens+vitreous) power
# transmission for visible light, excluding the pupil/aperture stop itself. Real ocular
# transmission is wavelength- and age-dependent (lower in blue/violet due to lens
# yellowing); 0.90 is a round, order-of-magnitude stand-in, not a precision figure.
HEURISTIC_OCULAR_TRANSMISSION = 0.90

TYPICAL_NATURAL_PUPIL_DIAMETER_UM = 4000.0  # matches this project's own D_pupil_um default


def nearest_v_lambda(wavelength):
    nearest = min(V_LAMBDA.keys(), key=lambda wl: abs(wl - wavelength))
    return V_LAMBDA[nearest]


def photon_energy(wavelength):
    return H_PLANCK * C_LIGHT / wavelength


def radiance_from_luminance(luminance_cdm2, wavelength):
    """
    literature.get('photopic_luminous_efficacy'). Converts photometric luminance
    (cd/m^2) to radiometric radiance (W/sr/m^2) at a given wavelength.
    """
    v_lambda = nearest_v_lambda(wavelength)
    return luminance_cdm2 / (PHOTOPIC_LUMINOUS_EFFICACY_MAX * v_lambda)


def retinal_illuminance_troland(scene_luminance_cdm2, aperture_diameter_um):
    """
    literature.get('troland_retinal_illuminance'). For an extended, roughly uniform
    scene, retinal illuminance (Td) = scene luminance (cd/m^2) x aperture area (mm^2)
    -- independent of viewing distance. Uses `aperture_diameter_um` as the LIMITING
    aperture stop; valid when the pinhole is smaller than the natural pupil (true for
    every aperture this project tests, all << the 4mm default natural pupil).

    Does NOT apply the Stiles-Crawford apodization correction -- see
    literature.get('stiles_crawford'); noted qualitatively in the error budget only.
    """
    area_mm2 = np.pi * (aperture_diameter_um / 1000.0 / 2.0) ** 2
    return scene_luminance_cdm2 * area_mm2


def relative_retinal_illuminance(a_hole_um, D_pupil_um=TYPICAL_NATURAL_PUPIL_DIAMETER_UM):
    """
    literature.get('throughput_area_ratio'), restated in illuminance terms: relative
    retinal illuminance (pinhole vs. the full natural pupil) = (a_hole/D_pupil)^2,
    identical to metrics.throughput_area_ratio() -- reused directly, not
    re-derived, since it is the same physical ratio expressed two ways (this
    function exists as the natural entry point from the photometry side).
    """
    return metrics.throughput_area_ratio(a_hole_um * 1e-6, D_pupil_um * 1e-6)


def retinal_irradiance(a_hole_um, v_r_m, wavelength, scene_luminance_cdm2=DEFAULT_SCENE_LUMINANCE_CDM2,
                        ocular_transmission=HEURISTIC_OCULAR_TRANSMISSION):
    """
    Retinal irradiance (W/m^2) for an extended scene of a given luminance, imaged
    through an aperture of diameter a_hole acting as the system's limiting stop, at
    image distance v_r. Uses the standard radiometric image-irradiance ("camera
    equation") result for an object at infinity:

        E_retina = pi * N * tau / (4 * F#^2),  F# = v_r / a_hole

    where N is scene radiance (W/sr/m^2) and tau is ocular transmission. This is the
    same physical relationship the troland unit encodes (retinal_illuminance_troland
    above is its photometric-unit form); expressed radiometrically here so it can be
    converted to photon flux. F# is computed via metrics.f_number(), reusing that
    function rather than re-deriving it.
    """
    N = radiance_from_luminance(scene_luminance_cdm2, wavelength)
    F_number = metrics.f_number(a_hole_um * 1e-6, v_r_m)
    return np.pi * N * ocular_transmission / (4.0 * F_number ** 2)


def photon_flux_at_retina(a_hole_um, v_r_m, wavelength, scene_luminance_cdm2=DEFAULT_SCENE_LUMINANCE_CDM2,
                           ocular_transmission=HEURISTIC_OCULAR_TRANSMISSION):
    """
    Full chain: scene luminance -> radiance -> retinal irradiance (via the F-number
    camera-equation route above) -> photon flux density (photons / s / m^2 at the
    retina). Returns every intermediate value, not just the final number, so the
    chain is auditable rather than a black box.
    """
    E_retina = retinal_irradiance(a_hole_um, v_r_m, wavelength, scene_luminance_cdm2, ocular_transmission)
    photon_flux_density = E_retina / photon_energy(wavelength)  # photons / s / m^2

    return {
        "scene_luminance_cdm2": scene_luminance_cdm2,
        "radiance_W_sr_m2": radiance_from_luminance(scene_luminance_cdm2, wavelength),
        "retinal_illuminance_troland": retinal_illuminance_troland(scene_luminance_cdm2, a_hole_um),
        "retinal_irradiance_W_m2": E_retina,
        "photon_flux_density_per_s_per_m2": photon_flux_density,
        "ocular_transmission_used": ocular_transmission,
    }
