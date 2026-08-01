"""
Citation database for Stage 4's calibration/validation literature search (triggered by
RESULTS.md's finding that the acuity predictor fails clinical validation: R^2 << 0,
p~0.5 against literature.get('ideal_pinhole_wang_2009') at every M tested).

Mirrors stage3_human_vision/literature.py's CITATIONS format exactly (type/statement/
source/fidelity, plus a `data` field where a usable dataset exists). Wang 2009 itself
is NOT duplicated here -- it remains the single source of truth in
stage3_human_vision/literature.py and is imported directly wherever needed, never
copied.

Every entry below was checked directly against the actual paper (full text, abstract,
or -- where paywalled -- the publisher's own indexed abstract) rather than accepted
from a secondhand paraphrase. Where that verification was incomplete, the `fidelity`
field says so explicitly instead of presenting an unverified number as confirmed.
"""

CITATIONS = {

    # -----------------------------------------------------------------------
    # Additional pinhole-aperture-vs-acuity datasets (Step 1, item 1)
    # -----------------------------------------------------------------------

    "single_pinhole_kim_2017": {
        "type": "published",
        "statement": "Single-pinhole spectacles with a 0.9mm aperture, tested on N=36 "
                     "subjects (mean age 33.1y, mean spherical equivalent -2.7 +/- 2.3 D, "
                     "range -6.0 to +0.75 D -- group aggregate, not per-subject), gave a "
                     "mean uncorrected distance visual acuity (logMAR) of 0.20 +/- 0.21 "
                     "with the pinhole in place.",
        "source": "Kim WS, Park IK, Park YK, Chun YS (2017). 'Comparison of Objective "
                  "and Subjective Changes Induced by Multiple-Pinhole Glasses and "
                  "Single-Pinhole Glasses.' J Korean Med Sci 32(5):850-857. "
                  "DOI: 10.3346/jkms.2017.32.5.850. Verified directly (full text, PMC5383620).",
        "fidelity": "USABLE as one additional real (aperture, approx-M, acuity) data "
                    "point, at a=900um -- a size Wang 2009 did not test (nearest "
                    "neighbors are 750um and 1000um). IMPORTANT LIMITATIONS: refractive "
                    "error is a GROUP mean +/- SD, not per-subject (same structural gap "
                    "as Wang 2009, not resolved by this dataset); acuity is a group "
                    "mean +/- SD, not individual data points, so it can be used as ONE "
                    "additional (a_hole, M, logMAR) anchor for a held-out sanity check, "
                    "not as N additional independent points for the regression itself. "
                    "Vertex/pinhole-to-eye distance for spectacle-mounted pinholes is not "
                    "stated exactly but is consistent with this project's existing "
                    "d_gap_mm=12mm assumption (typical spectacle vertex distance).",
        "data": {
            "aperture_um": [900],
            "M_diopters_mean": -2.7,
            "M_diopters_sd": 2.3,
            "M_diopters_range": [-6.0, 0.75],
            "logmar_mean": 0.20,
            "logmar_sd": 0.21,
            "n": 36,
        },
    },

    "pinhole_lighting_abdul_2009": {
        "type": "published",
        "statement": "Near visual acuity (0.4m) through 1.5mm and 2mm pinholes, in 4 "
                     "child subjects (ages 7y10m-12y3m), under 460 lux vs 1 lux "
                     "illumination, with induced defocus via +/-1D-step trial lenses. "
                     "Pinhole size (1.5mm vs 2mm) made an 'insignificant' difference to "
                     "the results in both lighting conditions. Low illumination sharply "
                     "reduced the amount of defocus tolerated before VA dropped (e.g. "
                     "Subject 1: VA held at 6/6 up to +5D added power at 460 lux, but "
                     "began degrading by +3D at 1 lux).",
        "source": "Abdul N, Meyer N, van Bosch M, van Zyl A, Viljoen M, Carlson AS "
                  "(2009). 'The effect of pinholes of different sizes on visual acuity "
                  "under different refracting states and ambient lighting conditions.' "
                  "S Afr Optom 68(1):38-48. Verified directly (full text PDF).",
        "fidelity": "NOT USABLE as an aperture-vs-acuity calibration point for this "
                    "project's model, despite being a real, directly-verified dataset. "
                    "Reasons: (1) near vision at 0.4m in accommodating children, not "
                    "distance vision with static uncorrected refractive error -- a "
                    "different task from what M_diopters models here; (2) acuity "
                    "reported in Lighthouse near-chart 'M-notation', not logMAR/Snellen "
                    "distance acuity; (3) only two aperture sizes tested (1.5mm, 2mm), "
                    "both far into this project's large-aperture/throughput-dominated "
                    "range, and the study's OWN conclusion is that pinhole size did not "
                    "matter there -- i.e. this dataset carries ~zero aperture-size signal "
                    "in the regime that matters for this project's diffraction-vs-"
                    "throughput tradeoff. Reported here as a found-but-rejected lead, "
                    "not silently dropped. It DOES independently corroborate the "
                    "brightness-sensitivity direction used below: low illumination "
                    "sharply reduces defocus/blur tolerance, consistent with Rabin "
                    "(1994) and Van Nes & Bouman (1967).",
    },

    "pinhole_neuroquantology_2022_REJECTED": {
        "type": "published",
        "statement": "N=40 myopic subjects; pinhole vs no-pinhole refractive error "
                     "comparison; single fixed occluder, no aperture-size sweep; no "
                     "logMAR/acuity values reported at all.",
        "source": "Samee N, et al. (2022). 'Assessment of Pinhole for Visual Acuity "
                  "Recoverment in Patients with Myopia.' NeuroQuantology 20(5):501-506. "
                  "DOI: 10.14704/nq.2022.20.5.NQ22201. Read directly, full text.",
        "fidelity": "REJECTED. An earlier web search summary claimed this paper reported "
                    "'0.17 logMAR with refractive error up to 5.5D and 1.16 logMAR with "
                    "7-11D at a 1.2mm aperture.' Reading the actual paper directly found "
                    "NO such numbers anywhere in it -- it does not test multiple aperture "
                    "sizes and reports no logMAR values at all, only pre/post-pinhole "
                    "refractive error (diopters) and pupil size. That search summary was "
                    "unsupported by the primary source and is not used anywhere in this "
                    "project. Kept here, marked REJECTED, specifically so this dead end "
                    "is not silently re-discovered and re-trusted later. Additionally, "
                    "NeuroQuantology is a low-editorial-rigor venue (this paper's own "
                    "prose is barely-edited machine-translation-quality English), which "
                    "would have been a reason for caution even if the numbers had been "
                    "real.",
    },

    # -----------------------------------------------------------------------
    # Brightness/luminance -> acuity slope literature (Step 1, items 2-3)
    # -----------------------------------------------------------------------

    "tidbury_2016_illuminance_slope": {
        "type": "published",
        "statement": "A one log10-unit increase in chart illuminance (lux) improves "
                     "logMAR acuity by 0.060 (p<0.001) at emmetropia, measured across "
                     "15 illuminance levels from 50 to 8000 lux, N=28 subjects (age "
                     "21-60). The slope STEEPENS with induced myopia: 0.06 (emmetropia), "
                     "0.07 (-0.5D), 0.10 (-1.0D), 0.12 (-1.5D) logMAR per log10-unit. "
                     "Recommends VA testing be done between 400-600 lux to limit any "
                     "illuminance-driven effect to <=0.012 logMAR.",
        "source": "Tidbury LP, Czanner G, Newsham D (2016). 'Fiat Lux: the effect of "
                  "illuminance on acuity testing.' Graefes Arch Clin Exp Ophthalmol "
                  "254:1091-1097. DOI: 10.1007/s00417-016-3329-7. Verified directly "
                  "(full text, PMC4884565).",
        "fidelity": "high -- verified directly against full text, exact coefficient and "
                    "p-value confirmed (Table 3: log(illuminance) beta = -0.060, "
                    "SE=0.006). CAVEAT: measured in illuminance (lux, light falling on "
                    "the chart), not luminance (cd/m^2, light leaving the chart toward "
                    "the eye) or retinal illuminance (Td). Converting between these "
                    "needs a chart-reflectance constant this project does not have a "
                    "cited value for. The SLOPE (logMAR per log10-unit) is invariant "
                    "under that missing conversion, since a constant reflectance factor "
                    "is only an additive shift in log-log space -- only the absolute "
                    "threshold/knee position would shift, which is instead anchored "
                    "using Van Nes & Bouman (1967) below, since that citation IS "
                    "natively in trolands.",
    },

    "sheedy_bailey_raasch_1984_slope": {
        "type": "published",
        "statement": "Over the photopic range 40-600 cd/m^2, log(MAR) vs log(luminance) "
                     "is approximately linear; a doubling of chart luminance improves "
                     "acuity by about one letter on a five-letter row. Using the "
                     "standard logMAR chart convention (5 letters/row = 0.1 logMAR, "
                     "i.e. 0.02 logMAR/letter) and log10(2)=0.301, this implies a slope "
                     "of ~0.02/0.301 = 0.0664 logMAR per log10-unit of luminance -- "
                     "consistent with Tidbury (2016)'s 0.060-0.12 range measured a "
                     "different way (illuminance, not chart luminance).",
        "source": "Sheedy JE, Bailey IL, Raasch TW (1984). 'Visual acuity and chart "
                  "luminance.' Am J Optom Physiol Opt 61(9):595-600.",
        "fidelity": "PARTIAL. The 40-600 cd/m^2 range and the 'one letter per doubling' "
                    "finding were confirmed consistently across multiple independent "
                    "secondary summaries (ResearchGate abstract page, Semantic Scholar, "
                    "general search indexing) that agree verbatim, which is why this is "
                    "used rather than discarded -- but the primary full text is "
                    "paywalled (a 1984 journal, not in PMC) and could not be directly "
                    "read, so the exact subject N and any finer methodological detail "
                    "are NOT independently confirmed here. The 0.0664 logMAR/decade "
                    "figure is THIS project's own derivation from the 'one letter per "
                    "doubling' statement, not a number printed verbatim in the source. "
                    "Used only as a corroborating cross-check on Tidbury's directly-"
                    "verified 0.060 -- Tidbury is the value actually wired into code.",
    },

    "rabin_1994_plateau": {
        "type": "published",
        "statement": "High-contrast visual acuity and small-letter contrast sensitivity "
                     "(SLCS) both degrade as luminance drops, but at very different "
                     "rates: reducing luminance from 116 cd/m^2 to 0.23 cd/m^2 produced "
                     "a 3x reduction in VA but a 17x reduction in SLCS. VA is far more "
                     "resistant to low luminance than contrast sensitivity is.",
        "source": "Rabin J (1994). 'Luminance effects on visual acuity and small letter "
                  "contrast sensitivity.' Optom Vis Sci 71(11):685-688. "
                  "DOI: 10.1097/00006324-199411000-00003.",
        "fidelity": "PARTIAL. Citation, DOI, and the 116->0.23 cd/m^2 / 3x-VA / 17x-SLCS "
                    "figures are corroborated by an independent secondary summary; the "
                    "full primary text is paywalled and was not directly read, so this "
                    "project could NOT independently verify the specific '~20/20 from "
                    "100 down to 1 cd/m^2' plateau framing quoted in the task -- that "
                    "framing is treated here as a reasonable round-number approximation "
                    "of the same qualitative shape (VA far more plateau-like than SLCS "
                    "at low luminance), not a verbatim-confirmed number. The concrete "
                    "116->0.23 cd/m^2 datapoint DOES independently support an "
                    "accelerating (non-log-linear) degradation at low luminance: a "
                    "constant 0.06-0.067 logMAR/decade slope applied across that full "
                    "2.7-decade range would predict only ~0.16-0.18 logMAR of total "
                    "degradation (~1.4-1.5x MAR), far less than the observed 3x -- "
                    "confirming the rate of degradation increases at low luminance, "
                    "consistent with a plateau-then-drop shape rather than one constant "
                    "slope across the whole range. The precise knee location is instead "
                    "anchored on Van Nes & Bouman (1967) below, which WAS verified "
                    "directly and is natively in trolands.",
    },

    "van_nes_bouman_1967_weber_knee": {
        "type": "published",
        "statement": "Spatial contrast sensitivity measured across mean retinal "
                     "illuminances B0 from well below to well above 300 troland. For "
                     "B0 > 300 td, threshold modulation M is a constant fraction of B0 "
                     "(Weber-Fechner law -- sensitivity becomes illuminance-independent "
                     "above this point). For B0 < 300 td, threshold modulation M "
                     "increases in proportion to B0^(-1/2) (de Vries-Rose law -- "
                     "sensitivity degrades faster as illuminance drops further).",
        "source": "Van Nes FL, Bouman MA (1967). 'Spatial Modulation Transfer in the "
                  "Human Eye.' J Opt Soc Am 57(3):401-406. Verified directly against "
                  "the publisher's (Optica Publishing Group) own indexed abstract.",
        "fidelity": "high -- the exact '300 td' transition point and both regime "
                    "exponents (Weber above, de Vries-Rose/B0^-1/2 below) were confirmed "
                    "directly from the primary abstract's own stated equations. This is "
                    "the citation used to anchor WHERE Stage 4's brightness-acuity "
                    "correction turns on (300 td, natively in this project's own unit), "
                    "rather than the round '100 cd/m^2' scene-luminance number in the "
                    "task description, which needs a pupil-area assumption to convert "
                    "to Td and was not independently pinned down as precisely.",
    },

}


def get(key):
    if key not in CITATIONS:
        raise KeyError(f"No citation entry for {key!r} -- add it to "
                       f"stage4_human_vision/literature.py first.")
    return CITATIONS[key]
