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

    # -----------------------------------------------------------------------
    # Module 10 validation (DESIGN.md's 5 target validation sets, checked here
    # against the paper's OWN reference data/figures, not the formula's own output)
    # -----------------------------------------------------------------------

    "watson_yellott_2012_winn_table_and_figures": {
        "type": "published",
        "statement": "Two real reference checks against Watson & Yellott (2012) itself, "
                     "used in tests/test_stage4.py: (1) their Table 1, Winn et al. "
                     "(1994)'s own measured linear fits (slope, intercept of pupil "
                     "diameter vs age) at 5 luminances (9/44/220/1100/4400 cd/m^2), "
                     "monocular, 10deg field, N=91 subjects, ages 17-83 -- real "
                     "empirical data, not a formula output. This project's "
                     "watson_yellott_pupil_mm() reproduces it with RMSE=0.115mm, "
                     "MAE=0.096mm, max error=0.237mm across a 25-point (5 luminance x "
                     "5 age) sweep. (2) Their Figure 17 interactive-demonstration "
                     "annotation (L=1 cd/m^2, field diameter=60deg, age=40, eyes=2: "
                     "'Unified' curve=4.839mm) -- reproduced EXACTLY (diff=0.0004mm).",
        "source": "Watson, A. B., & Yellott, J. I. (2012). A unified formula for "
                  "light-adapted pupil size. Journal of Vision 12(10):12. "
                  "DOI: 10.1167/12.10.12. Full text verified directly (open-access "
                  "copy via UC eScholarship, https://escholarship.org/uc/item/4fh0726w). "
                  "Every equation (10, 17-21, 24) and parameter this project's pupil.py "
                  "uses was checked against the paper's own printed equations and "
                  "matches exactly, including the reference age y0=28.58 and monocular/"
                  "binocular attenuation M(1)=0.1/M(2)=1.",
        "fidelity": "high for the two checks actually used (Winn table: real, "
                    "independent empirical data, though the paper's own age-slope "
                    "term was fit to approximate it, so a close match mainly confirms "
                    "correct code, not independent new physiological support; Figure "
                    "17: exact formula-fidelity match to the paper's own worked "
                    "example). IMPORTANT DISCREPANCY FOUND AND RESOLVED: the paper's "
                    "OTHER interactive demo widget, Figure 18 ('Pupil calculator'), "
                    "shows L=1, field diameter=60deg, age=30, eyes=2 -> 3.828mm. Since "
                    "the paper's own formula (Eq 19-20) is provably linear in age at "
                    "fixed L/field/eyes, and Figure 17 independently and exactly "
                    "confirms 4.839mm at age=40 for the identical L/field/eyes "
                    "condition, age=30 is mathematically required to give "
                    "4.839 + 10*0.02801 = 5.119mm (matching this project's code "
                    "exactly) -- NOT 3.828mm. This means Figure 18's own calculator "
                    "widget is internally inconsistent with the rest of the same "
                    "paper, not that this project's code is wrong. Figure 18's value "
                    "was investigated (re-read directly twice, page indexing double-"
                    "checked to rule out a transcription error) and excluded from the "
                    "test suite for this reason -- documented here rather than "
                    "silently discarded, per this project's discipline for anomalies "
                    "like the NeuroQuantology rejection earlier.",
    },

    "mannos_sakrison_1974_formula": {
        "type": "published",
        "statement": "H(f) = 2.6(0.0192 + 0.114f) * exp[-(0.114f)^1.1], f in cycles/"
                     "degree. This project's mannos_sakrison_csf() implements this "
                     "formula exactly (config's mannos_scale/offset/slope/exponent = "
                     "2.6/0.0192/0.114/1.1 are precisely these coefficients) -- "
                     "verified as an exact algebraic match (max diff = 0.0 across "
                     "600 test frequencies). Peak frequency = 7.89 cpd, matching the "
                     "commonly-cited ~8 cpd figure for this specific model.",
        "source": "Mannos, J. L., & Sakrison, D. J. (1974). The effects of a visual "
                  "fidelity criterion on the encoding of images. IEEE Transactions "
                  "on Information Theory, 20(4), 525-536.",
        "fidelity": "PARTIAL -- the exact formula and coefficients (2.6, 0.0192, "
                    "0.114, 1.1) were confirmed via multiple independent, mutually "
                    "consistent secondary reproductions in the image-quality-metrics "
                    "literature (this specific closed form is extremely widely "
                    "reproduced verbatim across many unrelated papers, which is why "
                    "it is trusted here despite not being independently confirmable "
                    "from a single authoritative source), NOT against the 1974 "
                    "primary paper directly -- a 1974 IEEE journal article, not "
                    "freely available online and not accessed in this pass. The "
                    "PEAK FREQUENCY match (~8cpd) is a real, meaningful, commonly-"
                    "cited fact about this model, independently useful even without "
                    "primary-source access. Cutoff frequency is criterion-sensitive: "
                    "a 10%-of-peak criterion gives 35.7cpd (close to the commonly-"
                    "cited ~30cpd figure), but 1%/5%/50%-of-peak criteria give "
                    "54.2/41.5/20.3cpd respectively -- reported as a range, not a "
                    "single pass/fail number, since the 'correct' criterion is itself "
                    "ambiguous across sources.",
    },

    "barten_1999_full_model_via_colour_science": {
        "type": "published",
        "statement": "The FULL Barten (1999) CSF model (not this project's "
                     "simplified form) was reimplemented directly from the "
                     "colour-science open-source library's verified, doctested "
                     "source (colour.contrast.barten1999), and cross-checked against "
                     "this project's barten_simplified_csf(). At L=100 cd/m^2, "
                     "field=20deg: normalized-shape Pearson r=0.990 between the two "
                     "models; peak frequency 3.68 cpd (this project's simplified "
                     "form) vs 2.68 cpd (full model); cutoff (S=1) 53.2 cpd vs "
                     "50.0 cpd. At L=1000: peak 4.00 vs 3.30 cpd, cutoff 58.9 vs "
                     "53.6 cpd. Six embedded reference values (full-model output at "
                     "1/2/4/8/16/32 cpd, L=100, field=20deg) are used in "
                     "tests/test_stage4.py's barten_simplified peak/cutoff-range "
                     "test's supporting analysis; see MODULE10_VALIDATION.md for the "
                     "full sweep and discussion.",
        "source": "Barten, P. G. J. (1999). Contrast Sensitivity of the Human Eye "
                  "and Its Effects on Image Quality. SPIE. DOI: 10.1117/3.353254. "
                  "Reimplemented from colour-science (github.com/colour-science/"
                  "colour, colour/contrast/barten1999.py), an open-source, actively "
                  "maintained library whose own module cites Barten (1999), Barten, "
                  "P. G. J. (2003) 'Formula for the contrast sensitivity of the "
                  "human eye' (SPIE Proc. 5294:231-238), and ITU-R Report BT.2246-4. "
                  "This project's reimplementation was verified bit-for-bit against "
                  "the library's own doctested example "
                  "(contrast_sensitivity_function_Barten1999(4) = 360.8691122...).",
        "fidelity": "high for the reimplementation itself (exact doctest match); "
                    "PARTIAL for how representative it is of the literal 1999 SPIE "
                    "book, which was not directly accessed (a paywalled book, not a "
                    "freely available paper) -- relying instead on a well-established, "
                    "cross-referenced, open-source scientific library as 'a standard "
                    "reproduction', consistent with this project's existing fidelity "
                    "discipline for hard-to-access primary sources (e.g. Sheedy 1984, "
                    "Rabin 1994 elsewhere in this file). This project's OWN "
                    "barten_simplified_csf() is confirmed to be a DIFFERENT, simpler "
                    "closed form (a*f*exp(-bf)*sqrt(1+c*exp(bf))), not the full model "
                    "above -- its own docstring already said 'simplified'/'inspired "
                    "by', confirmed accurate by this comparison, not just an "
                    "unverified disclaimer. Several config fields (barten_k, "
                    "barten_temporal_integration_s, barten_x0_deg, barten_xmax_deg, "
                    "barten_nmax, barten_sigma0_deg) are declared in constants.json "
                    "but NEVER used by barten_simplified_csf() -- likely vestigial "
                    "from an earlier intent to wire up the full model. One value, "
                    "barten_sigma0_deg=0.5, also appears to be a unit mismatch versus "
                    "the full model's own sigma_0 default of 0.5 ARCMIN (=0.00833 "
                    "degrees, not 0.5 degrees) -- noted here since it is currently "
                    "unused/inert but would need fixing if the full model is ever "
                    "wired up.",
    },

}


CITATIONS["blackwell_1946_contrast_threshold"] = {
    "type": "published",
    "statement": "Blackwell (1946) measured contrast detection threshold for "
                 "uniform achromatic discs across 7 angular sizes (0.595 to 360 "
                 "arcmin) and background luminances from 3.426e-5 to 3426 cd/m^2, "
                 "N=19 trained observers, ~90,000 observations (his own Table 7), "
                 "smoothed into his Table 8. For small (point-source-like) targets, "
                 "Ricco's Law holds (contrast threshold C times target area A is "
                 "constant = R, a function of background luminance B only). Crumey "
                 "(2014) fit R_phot(B) = (r3*B^-0.25 + r4)^2, r3=1.772e-4, "
                 "r4=7.167e-5, directly to Blackwell's own Table 8 (his Eqs. 21, 24, "
                 "27), and states 'the Blackwell table 8 values ... will be taken as "
                 "definitive'. This project reimplemented that fit directly: at a "
                 "0.595 arcmin target (Blackwell's smallest), C=2.63 (B=1 cd/m^2), "
                 "0.69 (B=100), 0.39 (B=3000) -- monotonically decreasing with "
                 "luminance, i.e. Weber's-law-consistent direction, as expected.",
    "source": "Blackwell, H. R. (1946). Contrast thresholds of the human eye. "
              "Journal of the Optical Society of America, 36(11), 624-643. "
              "Not freely available online (pre-digital-era JOSA issue, no PMC "
              "copy found) -- NOT accessed directly. Reimplemented from: Crumey, A. "
              "(2014). Human contrast threshold and astronomical visibility. "
              "MNRAS 442(3):2600-2619, arXiv:1405.4209 (open access, verified "
              "directly, full text) -- a peer-reviewed paper whose stated purpose "
              "is specifically to fit analytic functions to Blackwell's own Table 8 "
              "for downstream use, and which explicitly identifies Blackwell's "
              "Table 8 (not a re-derived or unit-converted version) as its source.",
    "fidelity": "PARTIAL / DATA FOUND BUT NOT DIRECTLY USABLE FOR THIS PROJECT'S "
                "CURRENT CODE, stated precisely: the primary 1946 source could not "
                "be accessed (investigated: PubMed/Semantic Scholar entries exist "
                "but link to no free full text; one third-party site "
                "(bbastrodesigns.com) offers 'another interpretation' of the data "
                "already converted to astronomical magnitude units, which was NOT "
                "used here to avoid stacking an unverifiable third-party unit "
                "conversion on top of an already-secondary source). Crumey (2014) "
                "is a rigorous, transparent, directly-verified secondary source "
                "that works in Blackwell's native units (cd/m^2, contrast, "
                "steradians) and states its coefficients came from regression "
                "directly against Table 8, which is why it is used and trusted "
                "here despite not being the primary paper itself. HOWEVER: "
                "Blackwell's task (single achromatic disc detection, threshold as "
                "a function of disc AREA and background LUMINANCE) is a "
                "fundamentally different psychophysical paradigm from the "
                "periodic-grating contrast sensitivity function (threshold as a "
                "function of SPATIAL FREQUENCY at fixed luminance) that "
                "stage4_human_vision/csf.py actually implements -- exactly the "
                "'careful task-mismatch caveat' DESIGN.md's Module 10 anticipated "
                "for this specific citation. Converting between disc-detection-"
                "area thresholds and grating-spatial-frequency thresholds requires "
                "an additional area-to-frequency equivalence model that this "
                "project does not have a cited source for, and one was NOT "
                "fabricated to force a comparison. CONCLUSION: this data point is "
                "real, verified, and usable as a benchmark for depth of DIFFERENT "
                "future work (e.g. a disc/letter-detection model), but does NOT "
                "currently validate barten_simplified_csf() or "
                "mannos_sakrison_csf() -- reported honestly as not-yet-bridgeable "
                "rather than silently forcing an unjustified numeric comparison.",
    "data": {
        "target_diameter_arcmin": 0.595,
        "target_area_sr": 2.3527514364161395e-08,
        "background_cdm2": [1, 10, 100, 1000, 3000],
        "contrast_threshold": [2.6325, 1.2475, 0.6932, 0.4525, 0.3886],
        "formula": "C = R_phot(B) / A, R_phot(B) = (1.772e-4*B^-0.25 + 7.167e-5)^2",
    },
}

CITATIONS["psychtoolbox_radiometric_troland_crosscheck"] = {
    "type": "first_principles",
    "statement": "Cross-checked this project's TWO independent code paths for "
                 "retinal light level -- illuminance.py's photometric troland "
                 "computation (Td = L * A_pupil_mm2) and photon_noise.py's "
                 "radiometric W/m^2 computation -- against the standard "
                 "photometric<->radiometric identity at 555nm: E_retina(W/m^2) = "
                 "Td / (683e6 * v_r_m^2). Result: relative difference = 1.9e-16 "
                 "(floating-point precision) -- exact agreement. This is DESIGN.md "
                 "Module 1's 'cross-check photometric Td against radiometric "
                 "retinal irradiance conversion at 555nm', beyond the pre-existing "
                 "test_troland_definition() which only checked the troland "
                 "DEFINITION identity (Td=L*A) in isolation, not a cross-check "
                 "against an independent radiometric standard.",
    "source": "Km=683 lm/W: the CIE/SI-defined peak photopic luminous efficacy, "
              "exact at 555nm by definition of the CIE 1924 V(lambda) photopic "
              "luminosity function (codified in the 1979 SI redefinition of the "
              "candela). Geometric form (retinal irradiance = radiance * "
              "pupilArea / eyeLength^2): confirmed directly against Psychtoolbox-3's "
              "RadianceAndPupilAreaEyeLengthToRetIrradiance.m source "
              "(github.com/Psychtoolbox-3/Psychtoolbox-3, PsychRadiometric "
              "toolbox), fetched and read directly -- the exact 'Wyszecki and "
              "Stiles conventions as referenced by Psychtoolbox radiometric "
              "conversions' DESIGN.md's Module 1 names as a primary source. "
              "Default eye length used for the numeric check (17mm) matches "
              "Psychtoolbox's own Gullstrand-model option (their overall default "
              "is LeGrand, 16.6832mm; both are standard schematic-eye values -- "
              "the identity is exact for any eyeLength since it appears on both "
              "sides of the comparison, so this choice does not affect the result).",
    "fidelity": "high -- exact algebraic identity, confirmed both symbolically "
                "(photon_noise.py's F-number-based formula was shown by hand to "
                "algebraically reduce to Psychtoolbox's pupilArea/eyeLength^2 "
                "form once F=v_r/D_stop is substituted in) and numerically (1.9e-16 "
                "relative difference, i.e. floating-point roundoff only). "
                "Psychtoolbox's own docs note their conversion deliberately "
                "excludes ocular transmission ('more conveniently folded into the "
                "spectral absorptance' separately) -- this project's photon_noise.py "
                "correctly does the same (transmission is a separate, explicit "
                "multiplicative factor), so ocular_transmission=1.0 was used for "
                "this specific check to compare like with like.",
}


def get(key):
    if key not in CITATIONS:
        raise KeyError(f"No citation entry for {key!r} -- add it to "
                       f"stage4_human_vision/literature.py first.")
    return CITATIONS[key]
