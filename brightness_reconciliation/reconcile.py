"""
Reconciles two independently-derived brightness thresholds that have never been
checked against each other:

1. The reverse-engineered PERCENTAGE floor (stage3a): T_min=6.25-9% of full natural-
   pupil illuminance moves the blur-only optimum (300-400um) into the verified
   clinical bracket (940-1750um). Found by asking "what floor reproduces the known
   range," not derived independently.

2. The ABSOLUTE (troland) floors from the illumination literature review: Van Nes &
   Bouman (1967)'s 300 Td Weber/de Vries-Rose transition (strict), and the CIE
   191:2010 photopic/mesopic boundary (~3-5 cd/m^2 adapting luminance, permissive),
   converted to an equivalent Td value via a natural 4mm pupil -- consistent with
   stage4_human_vision/illuminance.py's own equivalent_adapting_luminance definition.

Reuses stage3_human_vision/photometry.py's retinal_illuminance_troland() formula
directly (Td = scene_luminance_cdm2 * aperture_area_mm2) -- not re-derived.

KEY FINDING: the two thresholds only agree at a SPECIFIC assumed scene/chart
luminance -- and this project's own DEFAULT_SCENE_LUMINANCE_CDM2=10000 (bright
daylight, used throughout Stage 3/4's sweeps) is NOT that luminance. See
FINDINGS.md for the full reconciliation and its implications.
"""
import numpy as np

def retinal_illuminance_troland(scene_luminance_cdm2, aperture_diameter_um):
    """Verbatim from stage3_human_vision/photometry.py -- not re-derived."""
    area_mm2 = np.pi * (aperture_diameter_um / 1000.0 / 2.0) ** 2
    return scene_luminance_cdm2 * area_mm2

def min_aperture_for_Td_floor(Td_floor, scene_luminance_cdm2):
    """Inverts retinal_illuminance_troland: what aperture diameter (um) exactly
    reaches Td_floor at the given scene luminance."""
    return 2000.0 * np.sqrt(Td_floor / (np.pi * scene_luminance_cdm2))

D_PUPIL_MM = 4.0  # matches this project's own D_pupil default throughout
NATURAL_PUPIL_AREA_MM2 = np.pi * (D_PUPIL_MM / 2) ** 2

CIE_LOW_TD = 3.0 * NATURAL_PUPIL_AREA_MM2   # ~37.7 Td
CIE_HIGH_TD = 5.0 * NATURAL_PUPIL_AREA_MM2  # ~62.8 Td
VAN_NES_BOUMAN_TD = 300.0                    # strict Weber-onset knee

# Benchmark apertures already established elsewhere in this project
BLUR_ONLY_OPTIMUM_UM = (300, 400)
REVERSE_ENGINEERED_FLOOR_UM = (900, 1250)
CLINICAL_BRACKET_UM = (940, 1750)


if __name__ == "__main__":
    print(f"Natural pupil area (4mm): {NATURAL_PUPIL_AREA_MM2:.2f} mm^2")
    print(f"CIE photopic floor, Td-equivalent: {CIE_LOW_TD:.1f}-{CIE_HIGH_TD:.1f} Td")
    print(f"Van Nes & Bouman strict floor: {VAN_NES_BOUMAN_TD:.0f} Td\n")

    luminances = [10, 30, 100, 200, 300, 1000, 3000, 10000, 25000]
    print(f"{'Scene lum (cd/m2)':>18} {'CIE floor min aperture (um)':>28} {'Van Nes & Bouman min aperture (um)':>36}")
    for L in luminances:
        a_lo, a_hi = min_aperture_for_Td_floor(CIE_LOW_TD, L), min_aperture_for_Td_floor(CIE_HIGH_TD, L)
        a_vnb = min_aperture_for_Td_floor(VAN_NES_BOUMAN_TD, L)
        print(f"{L:18.0f} {f'{a_lo:.0f}-{a_hi:.0f}':>28} {a_vnb:36.0f}")
