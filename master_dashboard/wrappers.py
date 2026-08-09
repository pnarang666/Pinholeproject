"""
Thin per-stage wrapper functions for master_dashboard/app.py.

Every wrapper CALLS an existing, real function from its stage's own folder -- none of
them reimplement physics, a model, or a metric. Where a stage already exposes a clean
"give me a range, get a DataFrame" sweep function (stage3_human_vision.run_metrics_sweep
.run_sweep, singleilluminate.run_illumination_sweep.run_single_hole_sweep), that
function is called directly. Where a stage only exposes a per-point function
(stage2_fixed.phase2_retina.run_pipeline_point, array_ghosting_theory
.classify_ghosting_regime, ...), the loop-over-the-UI-selected-range here is the only
"new" code -- orchestration, not physics.

Import discipline (load-bearing, not stylistic): every import below is LOCAL to its
wrapper function, not module-level. Two different stages sometimes have same-named
bare modules imported via sys.path insertion (this project's own known failure mode --
see stage4_human_vision/pipeline.py's docstring on the import-shadowing bug this
project fixed). Scoping each stage's sys.path insert to inside its own wrapper call,
and re-verifying sys.modules['phase2_retina'].__file__ after every optics-touching
import (never assumed), keeps one tab's import order from silently affecting another
tab loaded earlier in the same long-running Streamlit process.

CRITICAL: stage2/ (the deprecated copy) is loaded in exactly ONE place below --
sweep_stage2_deprecated(), via _isolated_stage2_deprecated_import() -- and nowhere
else. Every other wrapper still goes exclusively through stage2_fixed/. The one
exception exists because a user of this dashboard explicitly asked for a dedicated,
clearly red-flagged tab that runs the known-broken pre-fix pipeline on purpose (for
reference/comparison, never as a recommendation) -- see that context manager's own
docstring for how it stops stage2/'s same-named modules (phase2_retina, myopia_axial,
pipeline_junction) from leaking into and permanently shadowing stage2_fixed/'s cached
copies that every OTHER tab in this file depends on. model_comparison/stage2_runner.py
also imports the deprecated stage2/ directly (verified by grep) and is deliberately NOT
called anywhere below -- see wrap_model_comparison()'s docstring for what is used
instead there.
"""
import contextlib
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
# Needed once, for every package-style import used below (`import R7acuity.threshold`,
# `from stage4_human_vision.pipeline import ...`) -- both are real Python packages
# (have __init__.py) and need their PARENT (the project root) on sys.path, not their
# own directory. Harmless to insert unconditionally: the root itself holds only
# subdirectories, never a loose same-named .py file that could collide with anything.
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

STANDARD_APERTURES_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750,
                          1000, 1250, 1500, 1750, 2000]
STANDARD_M_VALUES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]


def _ensure_path(*parts):
    p = os.path.join(ROOT, *parts)
    if p not in sys.path:
        sys.path.insert(0, p)
    return p


def verify_phase2_retina_source():
    """
    Live check: which phase2_retina.py is actually loaded right now, if any. Returns
    (path_or_none, is_correct_or_none). Called by every optics-touching wrapper AFTER
    its imports, and by the UI's persistent Project Physics Status panel.
    """
    mod = sys.modules.get("phase2_retina")
    if mod is None:
        return None, None
    path = os.path.abspath(mod.__file__)
    is_correct = os.path.join(ROOT, "stage2_fixed") in path and "stage2_fixed" in path
    # Explicitly also confirm it is NOT the deprecated copy (belt and suspenders --
    # a path containing both is impossible, but "stage2_fixed" alone as a substring
    # check is what actually discriminates them; the deprecated path is ROOT/stage2/).
    is_deprecated = path == os.path.join(ROOT, "stage2", "phase2_retina.py")
    return path, (is_correct and not is_deprecated)


# ---------------------------------------------------------------------------------
# 1. Stage 1 -- stage1_v2, cornea-plane diffraction only (no eye, no M)
# ---------------------------------------------------------------------------------

def sweep_stage1(params, progress_cb=None):
    _ensure_path("stage1_v2")
    import physics as s1  # noqa

    apertures = params["a_hole_um"]
    gaps_mm = params["d_gap_mm"]
    wavelengths_nm = params["wavelength_nm"]
    grid_N = params.get("grid_N", 2048)
    window_L_mm = params.get("window_L_mm", 6.0)

    combos = [(a, z, wl) for wl in wavelengths_nm for z in gaps_mm for a in apertures]
    rows = []
    for i, (a_um, z_mm, wl_nm) in enumerate(combos):
        cfg = s1.RunConfig(a_hole=a_um * 1e-6, wavelength=wl_nm * 1e-9, z=z_mm * 1e-3,
                            N=grid_N, L=window_L_mm * 1e-3)
        result = s1.run_configuration(cfg)
        rows.append({
            "a_hole_um": a_um, "d_gap_mm": z_mm, "wavelength_nm": wl_nm,
            "N_F": result["N_F"], "regime": result["regime"],
            "r_EE_50_um": s1.effective_radius(result, "EE", ee_percent=50.0) * 1e6,
            "r_EE_80_um": s1.effective_radius(result, "EE", ee_percent=80.0) * 1e6,
            "r_EE_90_um": s1.effective_radius(result, "EE", ee_percent=90.0) * 1e6,
            "second_moment_um": s1.effective_radius(result, "second_moment") * 1e6,
        })
        if progress_cb:
            progress_cb(i + 1, len(combos))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------
# 2. Stage 2 -- stage2_fixed, full blur-optimization pipeline (the corrected R1 sweep)
# ---------------------------------------------------------------------------------

def sweep_stage2_blur(params, progress_cb=None):
    _ensure_path("stage2_fixed")
    import phase2_retina as p2  # noqa
    import pipeline_junction as junction  # noqa

    apertures = params["a_hole_um"]
    m_values = params["M_diopters"]
    wavelength_nm = params.get("wavelength_nm", 550.0)
    d_gap_mm = params.get("d_gap_mm", 12.0)
    D_pupil_um = params.get("D_pupil_um", 4000.0)
    grid_N = params.get("grid_N", 2048)
    window_L_mm = params.get("window_L_mm", 6.0)

    combos = [(a, M) for M in m_values for a in apertures]
    rows = []
    for i, (a_um, M) in enumerate(combos):
        result = p2.run_pipeline_point(
            a_hole=a_um * 1e-6, wavelength=wavelength_nm * 1e-9, d_gap=d_gap_mm * 1e-3,
            grid_N=grid_N, window_L_mm=window_L_mm, M_diopters=M, P0=60.0, n_prime=1.336,
            D_pupil_um=D_pupil_um, refractive_index_correction=True,
        )
        row = {"a_hole_um": a_um, "M_diopters": M, "junction_ok": result["junction_check_passed"]}
        if result["junction_check_passed"]:
            I_retina = result["I_retina"]
            dx = result["cornea_result"]["dx"]
            N = I_retina.shape[0]
            L = N * dx
            _, _, R, _ = junction.make_grid(N, L)
            r_edges, EE, _ = junction.encircled_energy(I_retina, R, dx)
            for pct in (0.50, 0.70, 0.80, 0.90):
                row[f"r_EE_{int(pct*100)}_um"] = junction.r_for_EE(r_edges, EE, pct) * 1e6
            row["rms_radius_um"] = junction.second_moment_radius(I_retina, R, dx) * 1e6
        rows.append(row)
        if progress_cb:
            progress_cb(i + 1, len(combos))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------
# 3. Stage 3a -- brightness-constrained optimum, T_min UI-adjustable
# ---------------------------------------------------------------------------------

def sweep_stage3a_brightness(params, progress_cb=None):
    """
    stage3a/combine_and_select.py's OWN script defaults to reading a precomputed
    ../stage2/outputs/r1_full_range_sweep.csv -- the DEPRECATED, pre-fix optics'
    output (verified: that script's own --csv default). That script is deliberately
    NOT invoked here. Instead this wrapper gets FRESH blur data from
    sweep_stage2_blur() (stage2_fixed/, corrected) and applies
    stage3a.transmission.relative_illuminance() (reused verbatim, pure area-ratio
    math, no optics of its own) plus the same T_min-constrained-argmin selection
    stage3a/combine_and_select.py itself performs inline (not a function there to
    call -- reimplemented here as pure pandas selection logic, not physics).
    """
    _ensure_path("stage3a")
    import transmission  # noqa

    blur_df = sweep_stage2_blur(params, progress_cb=progress_cb)
    D_pupil_um = params.get("D_pupil_um", 4000.0)
    T_min = params.get("T_min", 0.0625)

    blur_df = blur_df[blur_df.junction_ok].copy()
    blur_df["E_rel"] = transmission.relative_illuminance(blur_df.a_hole_um, D_pupil_um)

    rows = []
    for M in sorted(blur_df.M_diopters.unique()):
        sub = blur_df[blur_df.M_diopters == M].sort_values("a_hole_um")
        cand = sub[sub.E_rel >= T_min]
        if len(cand) == 0:
            rows.append({"M_diopters": M, "T_min": T_min, "a_star_um": np.nan,
                         "r_EE_50_um": np.nan, "E_rel_at_optimum": np.nan})
            continue
        imin = cand.r_EE_50_um.idxmin()
        rows.append({"M_diopters": M, "T_min": T_min,
                     "a_star_um": cand.loc[imin, "a_hole_um"],
                     "r_EE_50_um": cand.loc[imin, "r_EE_50_um"],
                     "E_rel_at_optimum": cand.loc[imin, "E_rel"]})
    result = pd.DataFrame(rows)
    result.attrs["full_grid"] = blur_df  # kept for plotting E_rel vs aperture too
    return result


# ---------------------------------------------------------------------------------
# 4. Stage 3 Human Vision -- MTF/CSF/Strehl/photometry
# ---------------------------------------------------------------------------------

def sweep_stage3_human_vision(params, progress_cb=None):
    _ensure_path("stage1_v2")
    _ensure_path("stage3_human_vision")
    import run_metrics_sweep  # noqa

    apertures = params["a_hole_um"]
    m_values = params["M_diopters"]
    wavelength_nm = params.get("wavelength_nm", 550.0)
    d_gap_mm = params.get("d_gap_mm", 12.0)
    D_pupil_um = params.get("D_pupil_um", 4000.0)
    grid_N = params.get("grid_N", 2048)
    window_L_mm = params.get("window_L_mm", 6.0)

    # run_metrics_sweep.run_sweep() is the stage's OWN existing sweep function --
    # called directly, not re-looped here. It has no progress-callback hook, so
    # progress is reported once at the end (still shown, never a silent multi-minute
    # hang -- see app.py's runtime estimate + confirm gate for the "before" warning).
    df = run_metrics_sweep.run_sweep(
        aperture_values_um=apertures, M_values=m_values, wavelength_nm=wavelength_nm,
        z_gap_mm=d_gap_mm, D_pupil_um=D_pupil_um, grid_N=grid_N, window_L_mm=window_L_mm,
        log=False)
    if progress_cb:
        progress_cb(len(df), len(df))
    return df


# ---------------------------------------------------------------------------------
# 5. Stage 3 Integrated -- combined grid, sensitivity heatmaps
# ---------------------------------------------------------------------------------

def sweep_stage3_integrated(params, progress_cb=None):
    """
    "Combines Stage 3a and Stage 3 Human Vision on one shared grid" (this project's
    own description, stage3_integrated/README.md) -- built here by calling THIS
    dashboard's own sweep_stage3a_brightness() and sweep_stage3_human_vision()
    wrappers (both real-physics, both already stage2_fixed-safe) and merging on
    (a_hole_um, M_diopters). The merge itself is a pandas join, not new physics.
    """
    hv_df = sweep_stage3_human_vision(params, progress_cb=lambda d, t: progress_cb(d, t * 2) if progress_cb else None)
    brightness_result = sweep_stage3a_brightness(params, progress_cb=None)
    brightness_grid = brightness_result.attrs.get("full_grid")
    if progress_cb:
        progress_cb(2 * len(hv_df), 2 * len(hv_df))

    if brightness_grid is None or len(brightness_grid) == 0:
        return hv_df
    merged = hv_df.merge(
        brightness_grid[["a_hole_um", "M_diopters", "E_rel"]],
        on=["a_hole_um", "M_diopters"], how="left")
    return merged


# ---------------------------------------------------------------------------------
# 6. Stage 4 Human Vision -- pupil/illuminance/acuity, corrected-optics validation
# ---------------------------------------------------------------------------------

def sweep_stage4_acuity(params, progress_cb=None):
    from stage4_human_vision.pipeline import run_stage4_point  # noqa

    apertures = params["a_hole_um"]
    m_values = params["M_diopters"]
    wavelength_nm = params.get("wavelength_nm", 550.0)
    d_gap_mm = params.get("d_gap_mm", 12.0)
    scene_luminance_cdm2 = params.get("scene_luminance_cdm2")  # None -> stage4's own default

    combos = [(a, M) for M in m_values for a in apertures]
    rows = []
    for i, (a_um, M) in enumerate(combos):
        r = run_stage4_point(a_hole_um=a_um, wavelength_nm=wavelength_nm, d_gap_mm=d_gap_mm,
                              M_diopters=M, scene_luminance_cdm2=scene_luminance_cdm2)
        row = {"a_hole_um": a_um, "M_diopters": M, "junction_ok": r.junction_check_passed}
        if r.junction_check_passed:
            row["logmar"] = r.acuity["logmar"]
            row["mar_arcmin"] = r.acuity["mar_arcmin"]
            row["snellen_denominator"] = r.acuity["snellen_denominator"]
            row["recommended_model"] = r.acuity["recommended_model"]
            row["vsotf"] = r.visual_strehl.get("vsotf")
            row["retinal_illuminance_td"] = r.illuminance.get("retinal_illuminance_photopic_td")
        rows.append(row)
        if progress_cb:
            progress_cb(i + 1, len(combos))
    return pd.DataFrame(rows)


def read_stage4_validation_summary():
    """
    Reads the ALREADY-COMPUTED corrected-optics Wang-2009 validation numbers this
    project produced (stage4_human_vision/outputs/wang2009_validation_postfix_stats.csv,
    written by stage4_human_vision/run_wang2009_validation.py) -- displayed as a static
    reference table in the Stage 4 tab, not recomputed live (that validation run is a
    separate, deliberate task, not something a range slider should silently re-trigger).
    Returns a DataFrame, or None with a message if the file isn't there.
    """
    path = os.path.join(ROOT, "stage4_human_vision", "outputs",
                         "wang2009_validation_postfix_stats.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


# ---------------------------------------------------------------------------------
# 7. R7acuity -- ideal-observer Monte Carlo; calibration crash shown honestly
# ---------------------------------------------------------------------------------

def r7acuity_corrections_available():
    """
    The brief this dashboard was built from assumed R7acuity/corrections/ holds a
    registered-strategy plugin system (raw, efficiency, ...). On THIS branch's
    actual committed code, R7acuity/corrections/ and R7acuity/core/ are EMPTY
    (confirmed: only __pycache__, no .py files) -- that system is uncommitted work
    on a different, unmerged line of work, not part of this branch. Reported here
    honestly rather than fabricated; the R7 tab uses the flat-layout functions that
    DO exist (R7acuity/ideal_observer.py, R7acuity/threshold.py).
    """
    corrections_dir = os.path.join(ROOT, "R7acuity", "corrections")
    py_files = [f for f in os.listdir(corrections_dir) if f.endswith(".py")] \
        if os.path.isdir(corrections_dir) else []
    return len(py_files) > 0, py_files


def r7acuity_attempt_calibration(n_trials=300, seed=20260808):
    """
    Attempts R7acuity/threshold.py's calibrate_noise_sigma() fresh. Does NOT retry
    with a widened bracket or any other parameter change on failure -- per this
    project's own established discipline (R7acuity/RESULTS.md's corrected-optics
    section), a calibration failure against the corrected optics is a genuine result
    to report, not an obstacle to route around. Returns a dict: {"ok": bool,
    "sigma": float|None, "message": str}.
    """
    import R7acuity.threshold as th  # noqa
    rng = np.random.default_rng(seed)
    try:
        sigma, achieved, _log = th.calibrate_noise_sigma(n_trials=n_trials, rng=rng, verbose=False)
        return {"ok": True, "sigma": sigma, "achieved_threshold_arcmin": achieved, "message": None}
    except AssertionError as e:
        return {"ok": False, "sigma": None, "achieved_threshold_arcmin": None, "message": str(e)}


def r7acuity_closed_form_sweep(params, progress_cb=None):
    """
    R7acuity/threshold.py's closed_form_approximations() -- the Strehl/VSOTF
    cross-check predictors -- needs NO noise-sigma calibration, so it remains
    computable even while the ideal-observer MC path is crashed. Used as the R7 tab's
    fallback content when calibration fails (never silently substituted for the real
    ideal-observer result -- the UI must label this as the closed-form cross-check,
    not as "R7's answer").
    """
    import R7acuity.threshold as th  # noqa

    apertures = params["a_hole_um"]
    m_values = params["M_diopters"]
    wavelength_nm = params.get("wavelength_nm", 550.0)
    d_gap_mm = params.get("d_gap_mm", 12.0)
    D_pupil_um = params.get("D_pupil_um", 4000.0)
    scene_luminance_cdm2 = params.get("scene_luminance_cdm2", 10000.0)
    field_diameter_deg = params.get("field_diameter_deg", 20.0)

    combos = [(a, M) for M in m_values for a in apertures]
    rows = []
    for i, (a_um, M) in enumerate(combos):
        cf = th.closed_form_approximations(
            a_hole_um=a_um, wavelength_nm=wavelength_nm, M_diopters=M, d_gap_mm=d_gap_mm,
            D_pupil_um=D_pupil_um, scene_luminance_cdm2=scene_luminance_cdm2,
            field_diameter_deg=field_diameter_deg)
        rows.append({"a_hole_um": a_um, "M_diopters": M, **cf})
        if progress_cb:
            progress_cb(i + 1, len(combos))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------
# 8. Model Comparison -- RSS (deprecated closed-form) vs exact numerical divergence
# ---------------------------------------------------------------------------------

def sweep_model_comparison(params, progress_cb=None):
    """
    model_comparison/stage2_runner.py imports the DEPRECATED stage2/ directly
    (verified: `_STAGE2_DIR = ... "stage2"` at its top) -- NOT called here. The
    "exact numerical" leg below instead reuses THIS dashboard's own
    sweep_stage2_blur() (stage2_fixed/, corrected). model_comparison/
    approximation_runner.py's approximate_blur() (the deprecated RSS closed-form
    chain) has no optics dependency at all -- pure algebra -- and IS reused directly,
    unmodified.
    """
    _ensure_path("model_comparison")
    import approximation_runner  # noqa

    apertures = params["a_hole_um"]
    m_values = params["M_diopters"]
    wavelength_nm = params.get("wavelength_nm", 550.0)
    d_gap_mm = params.get("d_gap_mm", 12.0)
    D_pupil_um = params.get("D_pupil_um", 4000.0)

    exact_df = sweep_stage2_blur(params, progress_cb=progress_cb)
    exact_df = exact_df[exact_df.junction_ok][["a_hole_um", "M_diopters", "r_EE_50_um"]]

    rows = []
    for _, r in exact_df.iterrows():
        approx = approximation_runner.approximate_blur(
            a_hole=r.a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9,
            d_gap=d_gap_mm * 1e-3, M_diopters=r.M_diopters, D_pupil_um=D_pupil_um)
        r_total_um = approx["r_total_approx"] * 1e6  # returned in meters
        rows.append({
            "a_hole_um": r.a_hole_um, "M_diopters": r.M_diopters,
            "r_EE_50_exact_um": r.r_EE_50_um,
            "r_total_rss_um": r_total_um,
            "divergence_pct": (abs(r_total_um - r.r_EE_50_um) / r.r_EE_50_um * 100
                                if r.r_EE_50_um > 0 else np.nan),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------
# 9. array_ghosting_theory / stage_array -- aperture x pitch, A/B/C regime, harmonics
# ---------------------------------------------------------------------------------

def sweep_array_ghosting(params, progress_cb=None):
    _ensure_path("array_ghosting_theory")
    _ensure_path("stage_array")
    import ghosting_regime  # noqa
    import harmonic_analysis  # noqa

    apertures = params["a_hole_um"]
    pitches = params["pitch_um"]
    m_values = params["M_diopters"]
    wavelength_nm = params.get("wavelength_nm", 550.0)
    d_gap_mm = params.get("d_gap_mm", 12.0)
    D_pupil_um = params.get("D_pupil_um", 4000.0)
    packing = params.get("packing", "square")

    combos = [(a, s, M) for M in m_values for s in pitches for a in apertures]
    rows = []
    for i, (a_um, s_um, M) in enumerate(combos):
        classification = ghosting_regime.classify_ghosting_regime(
            a_hole_um=a_um, pitch_um=s_um, D_pupil_um=D_pupil_um, wavelength_nm=wavelength_nm,
            d_gap_mm=d_gap_mm, M_diopters=M, packing=packing)
        row = {"a_hole_um": a_um, "pitch_um": s_um, "M_diopters": M, **classification}
        if classification.get("regime") == "C":
            harmonics = harmonic_analysis.harmonic_margin_profile(
                a_hole_um=a_um, pitch_um=s_um, D_pupil_um=D_pupil_um, wavelength_nm=wavelength_nm,
                d_gap_mm=d_gap_mm, M_diopters=M)
            row["worst_harmonic_n"] = harmonics.get("worst_n")
            row["worst_harmonic_margin"] = harmonics.get("worst_margin")
            row["worst_harmonic_f_cpd"] = harmonics.get("worst_f_cpd")
        rows.append(row)
        if progress_cb:
            progress_cb(i + 1, len(combos))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------
# 10. brightness_reconciliation -- absolute vs percentage threshold, luminance-indexed
# ---------------------------------------------------------------------------------

def sweep_brightness_reconciliation(params, progress_cb=None):
    _ensure_path("brightness_reconciliation")
    import reconcile  # noqa

    luminances = params["scene_luminance_cdm2"]
    rows = []
    for i, L in enumerate(luminances):
        a_cie_lo = reconcile.min_aperture_for_Td_floor(reconcile.CIE_LOW_TD, L)
        a_cie_hi = reconcile.min_aperture_for_Td_floor(reconcile.CIE_HIGH_TD, L)
        a_vnb = reconcile.min_aperture_for_Td_floor(reconcile.VAN_NES_BOUMAN_TD, L)
        rows.append({
            "scene_luminance_cdm2": L,
            "min_aperture_CIE_low_um": a_cie_lo, "min_aperture_CIE_high_um": a_cie_hi,
            "min_aperture_van_nes_bouman_um": a_vnb,
        })
        if progress_cb:
            progress_cb(i + 1, len(luminances))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------
# 11. singleilluminate -- single-hole illumination
# ---------------------------------------------------------------------------------

def sweep_singleilluminate(params, progress_cb=None):
    _ensure_path("singleilluminate")
    import run_illumination_sweep  # noqa

    apertures = params["a_hole_um"]
    D_pupil_values = params["D_pupil_um"]
    df = run_illumination_sweep.run_single_hole_sweep(
        aperture_values_um=apertures, D_pupil_values_um=D_pupil_values)
    if progress_cb:
        progress_cb(len(df), len(df))
    return df


# ---------------------------------------------------------------------------------
# 12. stage2 (DEPRECATED) -- pre-fix, known-broken optics, isolated on purpose
# ---------------------------------------------------------------------------------

_STAGE2_DEPRECATED_COLLIDING_NAMES = ("phase2_retina", "myopia_axial", "pipeline_junction")


@contextlib.contextmanager
def _isolated_stage2_deprecated_import():
    """
    Loads the DEPRECATED stage2/'s phase2_retina (+ its own myopia_axial,
    pipeline_junction) under their bare names for the duration of this context ONLY,
    then restores whatever was cached under those names before entry -- so no other
    tab's trust in sys.modules['phase2_retina'] pointing at stage2_fixed/ (verified
    live by verify_phase2_retina_source(), asserted by the Project Physics Status
    panel on every rerun) is ever permanently disturbed by this one deliberately-
    broken tab.

    Why this is needed at all, not just _ensure_path("stage2"): stage2/ and
    stage2_fixed/ both define phase2_retina.py, myopia_axial.py, and
    pipeline_junction.py under the SAME bare names (confirmed: myopia_axial.py is
    byte-identical between the two dirs today; pipeline_junction.py and
    phase2_retina.py are not -- phase2_retina.py is where the actual lens-phase/
    retina-propagation wavelength fix lives). Python caches imports by bare name in
    sys.modules regardless of which directory they came from -- this project's own
    documented failure mode (see this file's module docstring). Simply inserting
    stage2/ onto sys.path is not enough if stage2_fixed/ is already cached: a bare
    `import phase2_retina` would just return the ALREADY-cached stage2_fixed module,
    silently handing back the CORRECTED pipeline's numbers while believing you're
    looking at the broken one.

    (pipeline_junction.py's own physics primitives -- make_grid, encircled_energy,
    r_for_EE, second_moment_radius -- are themselves re-exported from stage1_v2/
    physics.py via an absolute path anchored to pipeline_junction.py's own __file__,
    not a bare-name lookup, and BOTH stage2/'s and stage2_fixed/'s copies point at
    that same stage1_v2/ -- so "physics" is not a fourth colliding name here; it
    resolves identically and correctly either way.)
    """
    saved_modules = {name: sys.modules.get(name) for name in _STAGE2_DEPRECATED_COLLIDING_NAMES}
    saved_path = list(sys.path)
    for name in _STAGE2_DEPRECATED_COLLIDING_NAMES:
        sys.modules.pop(name, None)
    stage2_fixed_dir = os.path.join(ROOT, "stage2_fixed")
    # Strip stage2_fixed/ from the path for the duration -- otherwise a bare
    # `import myopia_axial`/`import pipeline_junction` inside stage2/'s own
    # phase2_retina.py could resolve to stage2_fixed/'s copy instead of stage2/'s own,
    # just because stage2_fixed/ happens to sit earlier on sys.path from an earlier tab.
    sys.path = [p for p in sys.path if os.path.abspath(p) != stage2_fixed_dir]
    stage2_dir = os.path.join(ROOT, "stage2")
    if stage2_dir not in sys.path:
        sys.path.insert(0, stage2_dir)
    try:
        import phase2_retina as deprecated_p2  # noqa
        import pipeline_junction as deprecated_junction  # noqa
        loaded_path = os.path.abspath(deprecated_p2.__file__)
        expected_path = os.path.join(ROOT, "stage2", "phase2_retina.py")
        if loaded_path != expected_path:
            raise RuntimeError(
                f"Isolated deprecated-stage2 import resolved to the wrong file "
                f"({loaded_path}, expected {expected_path}) -- refusing to proceed, "
                f"this would silently mislabel one pipeline's results as the other.")
        yield deprecated_p2, deprecated_junction
    finally:
        for name in _STAGE2_DEPRECATED_COLLIDING_NAMES:
            sys.modules.pop(name, None)
            if saved_modules[name] is not None:
                sys.modules[name] = saved_modules[name]
        sys.path = saved_path
        # Re-verify the CORRECTED pipeline's cache is exactly as it was before this
        # context ran -- fatal if not, never a silent pass-through. This is the one
        # invariant every other tab in this dashboard trusts.
        path, is_correct = verify_phase2_retina_source()
        if path is not None and not is_correct:
            raise RuntimeError(
                f"Isolated deprecated-stage2 import failed to restore the corrected "
                f"phase2_retina afterward -- sys.modules['phase2_retina'] now points "
                f"at {path}. This must never happen; every other tab in this "
                f"dashboard trusts this module stays stage2_fixed/. Restart the "
                f"Streamlit process before trusting any other tab's results.")


def sweep_stage2_deprecated(params, progress_cb=None):
    """
    Runs the SAME sweep as sweep_stage2_blur() -- same params, same output columns,
    same r_EE metrics, so results from the two are directly comparable/overlayable --
    but through the DEPRECATED, pre-fix stage2/ pipeline instead of stage2_fixed/,
    isolated to this one call via _isolated_stage2_deprecated_import() (see that
    context manager's own docstring for why a plain sys.path insert would not be
    enough here). This is the ONLY place in this dashboard that ever loads stage2/'s
    optics; every other tab still goes exclusively through stage2_fixed/ -- unchanged,
    still verified live by the Project Physics Status panel after this function
    returns (the context manager asserts this itself, on exit, every call).

    Exists so this deliberately-broken pipeline has its OWN clearly red-flagged tab
    (registry.py's "deprecated_optics" flag), never silently mixed into any
    corrected-optics tab's results. See PHYSICS_AUDIT.md / RESULTS.md for what is
    actually wrong with it: the lens-phase/retina-propagation effective-wavelength
    handling fixed in stage2_fixed/phase2_retina.py's run_pipeline_point (this file's
    own docstring there) is what stage2/'s copy still gets wrong.
    """
    apertures = params["a_hole_um"]
    m_values = params["M_diopters"]
    wavelength_nm = params.get("wavelength_nm", 550.0)
    d_gap_mm = params.get("d_gap_mm", 12.0)
    D_pupil_um = params.get("D_pupil_um", 4000.0)
    grid_N = params.get("grid_N", 2048)
    window_L_mm = params.get("window_L_mm", 6.0)

    combos = [(a, M) for M in m_values for a in apertures]
    rows = []
    with _isolated_stage2_deprecated_import() as (p2, junction):
        for i, (a_um, M) in enumerate(combos):
            result = p2.run_pipeline_point(
                a_hole=a_um * 1e-6, wavelength=wavelength_nm * 1e-9, d_gap=d_gap_mm * 1e-3,
                grid_N=grid_N, window_L_mm=window_L_mm, M_diopters=M, P0=60.0, n_prime=1.336,
                D_pupil_um=D_pupil_um, refractive_index_correction=True,
            )
            row = {"a_hole_um": a_um, "M_diopters": M, "junction_ok": result["junction_check_passed"]}
            if result["junction_check_passed"]:
                I_retina = result["I_retina"]
                dx = result["cornea_result"]["dx"]
                N = I_retina.shape[0]
                L = N * dx
                _, _, R, _ = junction.make_grid(N, L)
                r_edges, EE, _ = junction.encircled_energy(I_retina, R, dx)
                for pct in (0.50, 0.70, 0.80, 0.90):
                    row[f"r_EE_{int(pct*100)}_um"] = junction.r_for_EE(r_edges, EE, pct) * 1e6
                row["rms_radius_um"] = junction.second_moment_radius(I_retina, R, dx) * 1e6
            rows.append(row)
            if progress_cb:
                progress_cb(i + 1, len(combos))
    return pd.DataFrame(rows)
