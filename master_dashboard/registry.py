"""
The single registry mapping every dashboard stage to its real entry point, parameter
widgets, and output shape. Adding a 12th stage is ONE new dict entry here (plus, if
needed, one thin wrapper function in wrappers.py) -- app.py never changes.

Each entry:
  label            -- shown in the sidebar stage selector
  modules           -- real module paths this stage touches (shown in the UI, and
                        used by the physics-status panel to decide whether to run the
                        sys.modules['phase2_retina'] check for this stage)
  uses_optics       -- whether this stage calls stage2_fixed (directly or via another
                        stage's module) -- gates whether the physics-status caption
                        renders for this tab
  sweep_fn          -- wrappers.py callable: sweep_fn(params: dict, progress_cb) -> DataFrame
  params            -- ordered dict of widget specs (see WIDGET KINDS below)
  plot_type         -- one of PLOT_TYPES, used by app.py to pick a renderer
  y_metrics         -- candidate output column(s) to plot (first is the default)
  cost_per_point_s  -- rough seconds/point, profiled once, for the runtime estimate
  notes             -- shown in an expander in the UI (caveats, what was routed
                        around and why) -- never silently omitted

WIDGET KINDS (params dict values):
  multiselect -- {"kind":"multiselect","options":[...],"default":[...],"label":str}
                 contributes its selected-length to the point-count estimate
  slider      -- {"kind":"slider","min":,"max":,"step":,"default":,"label":str}
                 a single scalar input, does not multiply the point count
  select      -- {"kind":"select","options":[...],"default":,"label":str}
                 a single scalar choice, does not multiply the point count
"""
import wrappers as w

PLOT_TYPES = {"line_vs_aperture", "heatmap", "regime_map", "table_only"}

_APERTURE_PARAM = {
    "kind": "multiselect", "options": w.STANDARD_APERTURES_UM,
    "default": w.STANDARD_APERTURES_UM, "label": "Aperture $a_{hole}$ (µm)",
}
_M_PARAM = {
    "kind": "multiselect", "options": w.STANDARD_M_VALUES,
    "default": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0], "label": "Myopia M (D)",
}
_WAVELENGTH_PARAM = {
    # Stage 1 (sweep_stage1) genuinely loops over multiple wavelengths -- everywhere
    # else, the underlying stage function (run_pipeline_point, run_sweep,
    # run_stage4_point, ...) takes ONE wavelength per call, so those entries use
    # _WAVELENGTH_PARAM_SCALAR below instead. Keeping this distinction explicit
    # (rather than a single param silently truncated to params[0]) is what a fresh
    # multiselect-vs-scalar bug in this exact spot already caught once -- see
    # _verify_all_stages.py.
    "kind": "multiselect", "options": [450.0, 550.0, 650.0], "default": [550.0],
    "label": "Wavelength (nm)",
}
_GAP_PARAM = {
    "kind": "multiselect", "options": [6.0, 9.0, 12.0, 15.0, 18.0], "default": [12.0],
    "label": "Pinhole–cornea gap (mm)",
}
_PUPIL_PARAM = {
    # singleilluminate's own run_single_hole_sweep() genuinely accepts a LIST of
    # pupil diameters (its own D_PUPIL_VALUES_UM sweep dimension) -- kept multiselect
    # there. Elsewhere, use _PUPIL_PARAM_SCALAR (single value per underlying call).
    "kind": "multiselect", "options": [3000.0, 4000.0, 5000.0], "default": [4000.0],
    "label": "Natural pupil diameter (µm)",
}
_WAVELENGTH_PARAM_SCALAR = {
    "kind": "select", "options": [450.0, 550.0, 650.0], "default": 550.0,
    "label": "Wavelength (nm)",
}
_GAP_PARAM_SCALAR = {
    "kind": "select", "options": [6.0, 9.0, 12.0, 15.0, 18.0], "default": 12.0,
    "label": "Pinhole–cornea gap (mm)",
}
_PUPIL_PARAM_SCALAR = {
    "kind": "select", "options": [3000.0, 4000.0, 5000.0], "default": 4000.0,
    "label": "Natural pupil diameter (µm)",
}

REGISTRY = {

    "stage1": {
        "label": "Stage 1 — Cornea-plane diffraction",
        "modules": ["stage1_v2"],
        "uses_optics": False,
        "sweep_fn": w.sweep_stage1,
        "params": {
            "a_hole_um": _APERTURE_PARAM,
            "d_gap_mm": _GAP_PARAM,
            "wavelength_nm": _WAVELENGTH_PARAM,
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["r_EE_50_um", "r_EE_80_um", "r_EE_90_um", "second_moment_um"],
        "color_by": "d_gap_mm",
        "cost_per_point_s": 0.6,
        "notes": ("Pure diffraction, pinhole to cornea only -- no eye, no myopia. "
                  "Never touches stage2/stage2_fixed at all."),
    },

    "stage2_blur": {
        "label": "Stage 2 — Full blur-optimization (corrected R1 sweep)",
        "modules": ["stage2_fixed"],
        "uses_optics": True,
        "sweep_fn": w.sweep_stage2_blur,
        "params": {
            "a_hole_um": _APERTURE_PARAM,
            "M_diopters": _M_PARAM,
            "wavelength_nm": _WAVELENGTH_PARAM_SCALAR,
            "d_gap_mm": _GAP_PARAM_SCALAR,
            "D_pupil_um": _PUPIL_PARAM_SCALAR,
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["r_EE_50_um", "r_EE_70_um", "r_EE_80_um", "r_EE_90_um", "rms_radius_um"],
        "color_by": "M_diopters",
        "cost_per_point_s": 4.3,
        "notes": ("This project's corrected optics (PHYSICS_AUDIT.md items A/B). "
                  "r_EE(50%) saturates at its own histogram bin width "
                  "(≈2.5× grid spacing) for well-focused, large-aperture "
                  "conditions -- prefer RMS radius there (see new_sweeps/"
                  "Fresh_Sweep_Analysis.pdf for the documented case)."),
    },

    "stage2_deprecated": {
        "label": "⚠️ [DEPRECATED] Stage 2 — Pre-fix broken optics (reference only)",
        "modules": ["stage2 (DEPRECATED)"],
        "uses_optics": True,
        # Tells app.py to render the red "known-broken, on purpose" badge instead of
        # the normal green stage2_fixed check (which would otherwise misreport this
        # DELIBERATE use of stage2/ as a regression). See wrappers.py's
        # _isolated_stage2_deprecated_import() for how this stays contained to only
        # this one tab -- every other tab is unaffected and still verified live.
        "deprecated_optics": True,
        "sweep_fn": w.sweep_stage2_deprecated,
        "params": {
            "a_hole_um": _APERTURE_PARAM,
            "M_diopters": _M_PARAM,
            "wavelength_nm": _WAVELENGTH_PARAM_SCALAR,
            "d_gap_mm": _GAP_PARAM_SCALAR,
            "D_pupil_um": _PUPIL_PARAM_SCALAR,
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["r_EE_50_um", "r_EE_70_um", "r_EE_80_um", "r_EE_90_um", "rms_radius_um"],
        "color_by": "M_diopters",
        "cost_per_point_s": 4.3,
        "notes": ("⚠️ KNOWN-BROKEN, kept only for reference/comparison -- never the "
                  "recommended pipeline, never used by any other tab in this "
                  "dashboard. Same params and output columns as Stage 2 (corrected) "
                  "on purpose, so a run here can be overlaid against a Stage 2 "
                  "(corrected) run for direct comparison using the 'overlay another "
                  "cached sweep' picker below the chart. What's actually wrong with "
                  "it: the lens-phase/retina-propagation step does not use the same "
                  "effective (n_prime-corrected) wavelength as the retina "
                  "propagation itself -- fixed in stage2_fixed/phase2_retina.py's "
                  "run_pipeline_point (see PHYSICS_AUDIT.md item A, RESULTS.md). "
                  "Expect meaningfully different r_EE numbers from Stage 2 "
                  "(corrected) at the same parameters -- that divergence IS the "
                  "point of this tab, not a bug in the tab itself."),
    },

    "stage3a_brightness": {
        "label": "Stage 3a — Brightness-constrained optimum",
        "modules": ["stage2_fixed", "stage3a"],
        "uses_optics": True,
        "sweep_fn": w.sweep_stage3a_brightness,
        "params": {
            "a_hole_um": _APERTURE_PARAM,
            "M_diopters": _M_PARAM,
            "D_pupil_um": _PUPIL_PARAM_SCALAR,
            "T_min": {"kind": "slider", "min": 0.0, "max": 0.25, "step": 0.005,
                      "default": 0.0625, "label": "Minimum relative illuminance $T_{min}$"},
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["a_star_um", "r_EE_50_um"],
        "color_by": None,
        "cost_per_point_s": 4.3,  # dominated by the underlying fresh blur sweep
        "notes": ("stage3a/combine_and_select.py's own script defaults to reading a "
                  "STALE precomputed ../stage2/outputs/r1_full_range_sweep.csv "
                  "(pre-fix, deprecated optics) -- not used here. This tab computes "
                  "fresh blur data via stage2_fixed directly, then applies "
                  "stage3a.transmission.relative_illuminance() (reused verbatim) "
                  "under a live, UI-adjustable $T_{min}$."),
    },

    "stage3_human_vision": {
        "label": "Stage 3 Human Vision — MTF / CSF / Strehl / photometry",
        "modules": ["stage2_fixed", "stage1_v2", "stage3_human_vision"],
        "uses_optics": True,
        "sweep_fn": w.sweep_stage3_human_vision,
        "params": {
            "a_hole_um": _APERTURE_PARAM,
            "M_diopters": _M_PARAM,
            "wavelength_nm": _WAVELENGTH_PARAM_SCALAR,
            "d_gap_mm": _GAP_PARAM_SCALAR,
            "D_pupil_um": _PUPIL_PARAM_SCALAR,
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["r_EE_50_um", "rms_spot_radius_um", "strehl_ratio", "mtf50_cpd",
                      "mtf10_cpd", "fwhm_radius_um"],
        "color_by": "M_diopters",
        "cost_per_point_s": 6.0,
        "notes": ("Calls stage3_human_vision.run_metrics_sweep.run_sweep() directly "
                  "-- this stage's own existing sweep function, not re-looped here. "
                  "Strehl ratio is confirmed non-monotonic/can exceed 1.0 in this "
                  "system's near-field regime -- not a bug, see that module's own "
                  "docstring."),
    },

    "stage3_integrated": {
        "label": "Stage 3 Integrated — Combined grid & sensitivity",
        "modules": ["stage2_fixed", "stage1_v2", "stage3_human_vision", "stage3a"],
        "uses_optics": True,
        "sweep_fn": w.sweep_stage3_integrated,
        "params": {
            "a_hole_um": _APERTURE_PARAM,
            "M_diopters": _M_PARAM,
            "wavelength_nm": _WAVELENGTH_PARAM_SCALAR,
            "d_gap_mm": _GAP_PARAM_SCALAR,
            "D_pupil_um": _PUPIL_PARAM_SCALAR,
            "T_min": {"kind": "slider", "min": 0.0, "max": 0.25, "step": 0.005,
                      "default": 0.0625, "label": "Minimum relative illuminance $T_{min}$"},
        },
        "plot_type": "heatmap",
        "y_metrics": ["r_EE_50_um", "strehl_ratio", "mtf50_cpd", "E_rel"],
        "color_by": "M_diopters",
        "cost_per_point_s": 6.0,  # dominated by the stage3_human_vision leg
        "notes": ("Built by merging THIS dashboard's own stage3a_brightness and "
                  "stage3_human_vision wrappers on (aperture, M) -- both real-physics "
                  "outputs; the merge itself is a pandas join, not new physics."),
    },

    "stage4_acuity": {
        "label": "Stage 4 Human Vision — Pupil / illuminance / acuity",
        "modules": ["stage2_fixed", "stage3_human_vision", "stage4_human_vision"],
        "uses_optics": True,
        "sweep_fn": w.sweep_stage4_acuity,
        "params": {
            "a_hole_um": _APERTURE_PARAM,
            "M_diopters": _M_PARAM,
            "wavelength_nm": _WAVELENGTH_PARAM_SCALAR,
            "d_gap_mm": _GAP_PARAM_SCALAR,
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["logmar", "mar_arcmin", "vsotf", "retinal_illuminance_td"],
        "color_by": "M_diopters",
        "cost_per_point_s": 13.0,
        "notes": ("First stage whose acuity prediction actually runs against "
                  "stage2_fixed/ (the import-shadowing fix -- see RESULTS.md's "
                  "corrected-optics section and PHYSICS_AUDIT.md). The Wang-2009 "
                  "validation summary shown below this tab's sweep is READ from the "
                  "already-computed outputs/wang2009_validation_postfix_stats.csv, "
                  "not recomputed live on every slider change."),
    },

    "r7acuity": {
        "label": "R7acuity — Ideal-observer Monte Carlo",
        "modules": ["stage2_fixed", "R7acuity"],
        "uses_optics": True,
        "sweep_fn": w.r7acuity_closed_form_sweep,
        "params": {
            "a_hole_um": {**_APERTURE_PARAM, "default": [300, 500, 750, 1000, 1250, 1500]},
            "M_diopters": {**_M_PARAM, "default": [0.0, 2.0, 5.0]},
            "wavelength_nm": _WAVELENGTH_PARAM_SCALAR,
            "d_gap_mm": _GAP_PARAM_SCALAR,
            "D_pupil_um": _PUPIL_PARAM_SCALAR,
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["logmar_from_strehl", "logmar_from_vsotf", "strehl_ratio", "vsotf"],
        "color_by": "M_diopters",
        # Was wrongly set to 0.3 (assumed "closed-form = cheap"). Live-browser-tested
        # via the actual UI (not just the isolated wrapper call) and found running at
        # ~8.5s/point, ~28x the original estimate -- R7acuity/threshold.py's own
        # closed_form_approximations() calls get_real_psf() AND
        # get_diffraction_limited_reference() per point (TWO full ASM propagations,
        # roughly 2x stage2_blur's own per-point cost) despite the "closed-form" name
        # -- it is closed-form only in how it COMBINES Strehl/VSOTF into a logMAR
        # number, not in how it gets those inputs. Fixed here after a live UI test
        # showed "Estimated runtime: 5s" still running well past a minute -- exactly
        # the kind of mismatch that looks like a hang, not a fast tool.
        "cost_per_point_s": 8.5,
        "notes": ("R7acuity/corrections/ and R7acuity/core/ (the registered-strategy "
                  "plugin system) are EMPTY on this branch -- confirmed, not "
                  "committed here; this tab uses the flat-layout functions that DO "
                  "exist. The real ideal-observer Monte Carlo path "
                  "(calibrate_noise_sigma) currently CRASHES against the corrected "
                  "optics -- attempted fresh at the top of this tab and shown "
                  "plainly, not hidden. What this sweep plots is the closed-form "
                  "Strehl/VSOTF cross-check ONLY (needs no calibration) -- labeled "
                  "as such, never presented as R7's real ideal-observer answer."),
    },

    "model_comparison": {
        "label": "Model Comparison — RSS vs. exact divergence",
        "modules": ["stage2_fixed", "model_comparison"],
        "uses_optics": True,
        "sweep_fn": w.sweep_model_comparison,
        "params": {
            "a_hole_um": _APERTURE_PARAM,
            "M_diopters": _M_PARAM,
            "wavelength_nm": _WAVELENGTH_PARAM_SCALAR,
            "d_gap_mm": _GAP_PARAM_SCALAR,
            "D_pupil_um": _PUPIL_PARAM_SCALAR,
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["divergence_pct", "r_EE_50_exact_um", "r_total_rss_um"],
        "color_by": "M_diopters",
        "cost_per_point_s": 4.3,
        "notes": ("model_comparison/stage2_runner.py imports the DEPRECATED stage2/ "
                  "directly (verified by grep) -- NOT called anywhere in this tab. "
                  "The ‘exact’ leg reuses this dashboard's own "
                  "stage2_blur wrapper (stage2_fixed/); only "
                  "model_comparison/approximation_runner.py's pure-algebra RSS "
                  "formula (no optics dependency) is reused directly."),
    },

    "array_ghosting": {
        "label": "Array Ghosting — A/B/C regime & harmonic margins",
        "modules": ["stage2_fixed", "Array_Design/ghosting", "Array_Design/photometry"],
        "uses_optics": True,
        "sweep_fn": w.sweep_array_ghosting,
        "params": {
            "a_hole_um": {**_APERTURE_PARAM, "default": [300, 500, 750, 1000]},
            "pitch_um": {"kind": "multiselect",
                         "options": [400, 600, 800, 1200, 1600, 2000, 3000, 4800],
                         "default": [600, 1200, 2000, 3000], "label": "Array pitch $s$ (µm)"},
            "M_diopters": {**_M_PARAM, "default": [2.0]},
            "wavelength_nm": _WAVELENGTH_PARAM_SCALAR,
            "d_gap_mm": _GAP_PARAM_SCALAR,
            "D_pupil_um": _PUPIL_PARAM_SCALAR,
            "packing": {"kind": "select", "options": ["square", "hex"], "default": "square",
                        "label": "Array packing"},
        },
        "plot_type": "regime_map",
        "y_metrics": ["regime", "N_eff_worst", "worst_harmonic_margin"],
        "color_by": "regime",
        # Was 4.5 (base classify_ghosting_regime() cost only). Live-browser-tested with
        # the widget's own default (aperture=500, default pitch/M) and found 4 points in
        # 27s (~6.75s/point average), not the estimated 18s -- 3 of those 4 points landed
        # in Regime C, each triggering wrappers.sweep_array_ghosting()'s extra
        # harmonic_analysis.harmonic_margin_profile() call (see that function's own
        # "only computed for points already classified Regime C" note two lines below --
        # Regime C is this stage's actual regime of interest, not a rare edge case, so
        # most real sweeps here will pay this cost on most points, not just some).
        "cost_per_point_s": 7.0,
        "notes": ("Requires the colour-science package (installed for this "
                  "dashboard -- it is a pre-existing dependency of "
                  "Array_Design/ghosting/contrast_barten.py's real Barten (1999) "
                  "CSF model, not a new one introduced here). Harmonic margin "
                  "profile is only computed for points already classified Regime C, "
                  "matching the stage's own real cost-saving convention."),
    },

    "brightness_reconciliation": {
        "label": "Brightness Reconciliation — Absolute vs. percentage threshold",
        "modules": ["brightness_reconciliation"],
        "uses_optics": False,
        "sweep_fn": w.sweep_brightness_reconciliation,
        "params": {
            "scene_luminance_cdm2": {"kind": "multiselect",
                                      "options": [10, 30, 100, 200, 300, 1000, 3000, 10000, 25000],
                                      "default": [10, 30, 100, 300, 1000, 10000],
                                      "label": "Scene luminance (cd/m²)"},
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["min_aperture_CIE_low_um", "min_aperture_CIE_high_um",
                      "min_aperture_van_nes_bouman_um"],
        "color_by": None,
        "cost_per_point_s": 0.05,
        "notes": ("Pure photometric math, no optics call at all -- "
                  "brightness_reconciliation/reconcile.py's own functions, reused "
                  "verbatim."),
    },

    "singleilluminate": {
        "label": "Single Illuminate — Single-hole illumination",
        "modules": ["singleilluminate"],
        "uses_optics": False,
        "sweep_fn": w.sweep_singleilluminate,
        "params": {
            "a_hole_um": _APERTURE_PARAM,
            "D_pupil_um": _PUPIL_PARAM,
        },
        "plot_type": "line_vs_aperture",
        "y_metrics": ["percent_illumination"],
        "color_by": "D_pupil_um",
        "cost_per_point_s": 0.05,
        "notes": ("Calls singleilluminate.run_illumination_sweep."
                  "run_single_hole_sweep() directly -- this stage's own existing "
                  "sweep function. Single-hole only by this module's own explicit "
                  "design (see its module docstring) -- no array row_type exists."),
    },
}


def estimate_points(stage_key, selected_params):
    """Product of every multiselect param's selected length -- sliders/selects (single
    scalar inputs) don't multiply the count."""
    entry = REGISTRY[stage_key]
    n = 1
    for key, spec in entry["params"].items():
        if spec["kind"] == "multiselect":
            n *= max(len(selected_params.get(key, spec["default"])), 1)
    return n


def estimate_runtime_s(stage_key, selected_params):
    return estimate_points(stage_key, selected_params) * REGISTRY[stage_key]["cost_per_point_s"]
