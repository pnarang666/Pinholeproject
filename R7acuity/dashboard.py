"""
Standalone Streamlit dashboard for R7acuity -- the independent Watson & Ahumada
(2008) template-matching ideal-observer acuity model. Separate from
stage_v1_simulator (which hosts stage4_human_vision/acuity.py's dashboard tab);
this is its own app since R7acuity is architecturally independent, per the task
brief.

Run: streamlit run R7acuity/dashboard.py
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from R7acuity.ideal_observer import compute_neural_images, run_trial, DEFAULT_GRID_N, DEFAULT_WINDOW_L_MM  # noqa: E402
from R7acuity.optotype import ORIENTATIONS  # noqa: E402
from R7acuity.threshold import (find_threshold_mar, mar_to_logmar, mar_to_snellen_denominator,  # noqa: E402
                                closed_form_approximations, REFERENCE_CONDITION)

st.set_page_config(page_title="R7acuity -- Ideal Observer Model", page_icon="\U0001F441", layout="wide")

DISCRETE_APERTURES_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
OUT_DIR = os.path.join(_HERE, "outputs")

# Locked once by R7acuity/run_validation.py's calibrate_noise_sigma() -- see
# outputs/sigma_calibration_log.csv for the calibration trace. NOT re-tuned here.
_SIGMA_PATH = os.path.join(OUT_DIR, "calibrated_sigma.txt")


@st.cache_data(show_spinner=False)
def load_calibrated_sigma():
    if os.path.exists(_SIGMA_PATH):
        with open(_SIGMA_PATH) as fh:
            return float(fh.read().strip())
    return None


@st.cache_data(show_spinner="Running Stage 2's real optics + neural filtering...")
def cached_neural_images(a_hole_um, wavelength_nm, M_diopters, d_gap_mm, mar_arcmin,
                          scene_luminance_cdm2, field_diameter_deg, grid_N, window_L_mm, D_pupil_um):
    return compute_neural_images(
        a_hole_um=a_hole_um, wavelength_nm=wavelength_nm, M_diopters=M_diopters, d_gap_mm=d_gap_mm,
        mar_arcmin=mar_arcmin, scene_luminance_cdm2=scene_luminance_cdm2,
        field_diameter_deg=field_diameter_deg, grid_N=grid_N, window_L_mm=window_L_mm,
        D_pupil_um=D_pupil_um)


@st.cache_data(show_spinner="Running Monte Carlo threshold search (this can take a minute)...")
def cached_threshold_sweep(a_hole_um, wavelength_nm, M_diopters, d_gap_mm, scene_luminance_cdm2,
                           field_diameter_deg, sigma, mar_values, n_trials, grid_N, window_L_mm, D_pupil_um):
    condition = dict(a_hole_um=a_hole_um, wavelength_nm=wavelength_nm, M_diopters=M_diopters,
                      d_gap_mm=d_gap_mm, scene_luminance_cdm2=scene_luminance_cdm2,
                      field_diameter_deg=field_diameter_deg, grid_N=grid_N, window_L_mm=window_L_mm,
                      D_pupil_um=D_pupil_um)
    rng = np.random.default_rng(0)
    threshold_mar, slope, proportions = find_threshold_mar(condition, sigma, mar_values, n_trials=n_trials, rng=rng)
    return threshold_mar, slope, proportions


@st.cache_data(show_spinner=False)
def load_validation_status():
    """Same pattern as stage_v1_simulator/light_acuity.py's load_validation_caveat()
    -- read the actual validation output at runtime, never hardcode a pass/fail
    string."""
    path = os.path.join(OUT_DIR, "validation_regression_stats.csv")
    if not os.path.exists(path):
        return ("R7acuity's validation has not been run yet -- run "
                "`python3 -m R7acuity.run_validation` first. Treat any acuity "
                "number below as unvalidated until that exists.")
    df = pd.read_csv(path)
    rec = df[(df["predictor"] == "logmar_r7_ideal_observer") & (df["kind"] == "in_sample")]
    if len(rec) == 0:
        return "Validation output found but has no 'logmar_r7_ideal_observer' row -- treat as unvalidated."
    r2_lo, r2_hi = rec["r2"].min(), rec["r2"].max()
    p_lo, p_hi = rec["pearson_p_value"].min(), rec["pearson_p_value"].max()
    passed = (r2_lo > 0) and (p_hi < 0.05)
    m_values = sorted(rec["M_diopters"].unique())
    if passed:
        return (f"VALIDATED against clinical data (Wang 2009 'Ideal Pinhole', n=5 apertures): "
                f"R²={r2_lo:.2f}-{r2_hi:.2f}, p={p_lo:.3f}-{p_hi:.3f} across M={m_values}D. "
                f"In-sample and leave-one-out are identical for this model (no parameter is fit "
                f"to Wang 2009 -- see R7acuity/validation.py). n=5 even via a clean, no-fit "
                f"comparison is still a small sample -- read this as suggestive, not proof.")
    return (f"NOT validated with statistical significance against clinical data "
            f"(R²={r2_lo:.2f} to {r2_hi:.2f}, p={p_lo:.2f}-{p_hi:.2f} vs Wang 2009 'Ideal "
            f"Pinhole' clinical pinhole-acuity data across M={m_values}D). Treat the acuity "
            f"number below as exploratory, not clinically predictive. See R7acuity/RESULTS.md "
            f"for the full analysis and stage4_human_vision/RESULTS.md for how this compares "
            f"to the other model family tested on the same data.")


def sidebar_controls():
    st.sidebar.header("Condition")
    a_hole_um = st.sidebar.select_slider("Aperture diameter (µm)", options=DISCRETE_APERTURES_UM, value=1000)
    wavelength_nm = st.sidebar.slider("Wavelength (nm)", 400, 700, 550, step=5)
    M_diopters = st.sidebar.slider("Myopia M (D)", 0.0, 12.0, 0.0, step=0.5)
    d_gap_mm = st.sidebar.slider("Pinhole-to-cornea gap (mm)", 5.0, 25.0, 12.0, step=0.5)
    D_pupil_um = st.sidebar.number_input("Natural pupil diameter (µm)", value=4000.0)
    scene_luminance_cdm2 = st.sidebar.number_input("Scene luminance (cd/m²)", min_value=0.1, value=10000.0, step=100.0)
    field_diameter_deg = st.sidebar.slider("Adapting field diameter (deg)", 1.0, 60.0, 20.0, step=1.0)
    high_accuracy = st.sidebar.checkbox(
        "Use calibrated resolution (grid_N=2048) -- required for numbers to match "
        "the locked sigma calibration", value=True)
    grid_N = DEFAULT_GRID_N if high_accuracy else 512
    if not high_accuracy:
        st.sidebar.warning("grid_N=512 is NOT the resolution sigma was calibrated at -- "
                           "use for fast visual exploration only, not for reading threshold numbers.")
    return dict(a_hole_um=a_hole_um, wavelength_nm=wavelength_nm, M_diopters=M_diopters,
                d_gap_mm=d_gap_mm, D_pupil_um=D_pupil_um, scene_luminance_cdm2=scene_luminance_cdm2,
                field_diameter_deg=field_diameter_deg, grid_N=grid_N, window_L_mm=DEFAULT_WINDOW_L_MM)


def tab_live_trial(params, sigma):
    st.subheader("Live trial: noisy stimulus vs. clean template")
    mar_arcmin = st.slider("Letter size (MAR, arcmin)", 0.2, 20.0, 3.0, step=0.1, key="live_mar")
    true_orientation = st.selectbox("True orientation presented", ORIENTATIONS, key="live_orientation")

    ni = cached_neural_images(params["a_hole_um"], params["wavelength_nm"], params["M_diopters"],
                              params["d_gap_mm"], mar_arcmin, params["scene_luminance_cdm2"],
                              params["field_diameter_deg"], params["grid_N"], params["window_L_mm"],
                              params["D_pupil_um"])

    if st.button("Draw new noise sample"):
        st.session_state["live_seed"] = st.session_state.get("live_seed", 0) + 1
    rng = np.random.default_rng(st.session_state.get("live_seed", 0))
    decided, correct = run_trial(ni, true_orientation, sigma, rng)

    zoom = max(int(0.5 * 5 * mar_arcmin / ni["arcmin_per_pixel"]), 20)
    center = params["grid_N"] // 2
    lo, hi = max(center - zoom, 0), min(center + zoom, params["grid_N"])

    col1, col2 = st.columns(2)
    with col1:
        fig, ax = plt.subplots(figsize=(4, 4))
        stimulus = ni["S"][true_orientation] + rng.normal(0.0, sigma, size=ni["S"][true_orientation].shape)
        ax.imshow(stimulus[lo:hi, lo:hi], cmap="gray")
        ax.set_title(f"Noisy stimulus (true={true_orientation})")
        ax.axis("off")
        st.pyplot(fig)
        plt.close(fig)
    with col2:
        fig2, ax2 = plt.subplots(figsize=(4, 4))
        ax2.imshow(ni["templates"][true_orientation][lo:hi, lo:hi], cmap="gray")
        ax2.set_title("Clean template (reference)")
        ax2.axis("off")
        st.pyplot(fig2)
        plt.close(fig2)

    st.metric("Model decision", decided, delta="CORRECT" if correct else "INCORRECT")


def tab_psychometric(params, sigma):
    st.subheader("Psychometric function: proportion correct vs. letter size")
    st.caption("Never shown in this project before -- direct visualization of the Monte Carlo "
               "decision process's own performance curve.")
    mar_values = np.array([0.5, 0.8, 1.3, 2.0, 3.2, 5.0, 8.0, 13.0, 20.0])
    n_trials = st.slider("Trials per size", 50, 500, 200, step=50, key="psychometric_trials")

    if st.button("Run psychometric sweep", type="primary"):
        threshold_mar, slope, proportions = cached_threshold_sweep(
            params["a_hole_um"], params["wavelength_nm"], params["M_diopters"], params["d_gap_mm"],
            params["scene_luminance_cdm2"], params["field_diameter_deg"], sigma, tuple(mar_values),
            n_trials, params["grid_N"], params["window_L_mm"], params["D_pupil_um"])
        st.session_state["psychometric_result"] = (mar_values, proportions, threshold_mar, slope)

    if "psychometric_result" in st.session_state:
        mar_values, proportions, threshold_mar, slope = st.session_state["psychometric_result"]
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(mar_values, proportions, color="#2a78d6", label="Monte Carlo proportion correct", zorder=3)
        smooth_mar = np.logspace(np.log10(mar_values.min()), np.log10(mar_values.max()), 200)
        fitted = 0.25 + 0.75 / (1 + np.exp(-slope * (np.log10(smooth_mar) - np.log10(threshold_mar))))
        ax.plot(smooth_mar, fitted, color="#e34948", label="fitted psychometric function")
        ax.axhline(0.625, color="gray", linestyle=":", label="criterion (62.5%, midway chance-ceiling)")
        ax.axvline(threshold_mar, color="gray", linestyle="--", label=f"threshold = {threshold_mar:.2f} arcmin")
        ax.set_xscale("log")
        ax.set_xlabel("Letter size, MAR (arcmin)")
        ax.set_ylabel("Proportion correct (4AFC)")
        ax.set_ylim(0, 1.05)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        st.pyplot(fig)
        plt.close(fig)

        c1, c2, c3 = st.columns(3)
        c1.metric("Threshold MAR", f"{threshold_mar:.2f} arcmin")
        c2.metric("logMAR", f"{mar_to_logmar(threshold_mar):.3f}")
        c3.metric("Snellen", f"20/{mar_to_snellen_denominator(threshold_mar):.0f}")


def tab_comparison(params):
    st.subheader("Closed-form comparison (internal cross-check, not the primary model)")
    st.caption("logMAR ~= 25*log10(Strehl) and logMAR ~= (50/3)*log10(VSOTF) -- coefficients "
               "as specified in this model's brief; see R7acuity/literature.py's "
               "closed_form_approximations_unverified_coefficients entry for the honest "
               "fidelity note (general concept confirmed in the literature, exact coefficients "
               "not independently re-derived from a primary source).")
    result = closed_form_approximations(
        a_hole_um=params["a_hole_um"], wavelength_nm=params["wavelength_nm"], M_diopters=params["M_diopters"],
        d_gap_mm=params["d_gap_mm"], D_pupil_um=params["D_pupil_um"],
        scene_luminance_cdm2=params["scene_luminance_cdm2"], field_diameter_deg=params["field_diameter_deg"],
        grid_N=params["grid_N"], window_L_mm=params["window_L_mm"])
    c1, c2 = st.columns(2)
    c1.metric("Strehl ratio", f"{result['strehl_ratio']:.3f}")
    c1.metric("logMAR from Strehl (25*log10(M))", f"{result['logmar_from_strehl']:.3f}")
    c2.metric("VSOTF", f"{result['vsotf']:.3f}")
    c2.metric("logMAR from VSOTF (50/3*log10|VSOTF|)", f"{result['logmar_from_vsotf']:.3f}")


def main():
    st.title("R7acuity -- Watson & Ahumada (2008) Ideal-Observer Acuity Model")
    st.caption("An independent model family from stage4_human_vision/acuity.py, built to test "
               "whether that model's clinical validation failure is a data problem or a model "
               "problem. See R7acuity/README.md for the architectural comparison.")

    sigma = load_calibrated_sigma()
    if sigma is None:
        st.error("No calibrated sigma found -- run `python3 -m R7acuity.run_validation` first "
                 "(this calibrates noise sigma against a diffraction-limited reference condition "
                 "BEFORE any clinical data is used, then validates against Wang 2009).")
        return

    st.info(f"**Validation status:** {load_validation_status()}")

    params = sidebar_controls()
    tabs = st.tabs(["Live Trial", "Psychometric Function", "Closed-Form Comparison"])
    with tabs[0]:
        tab_live_trial(params, sigma)
    with tabs[1]:
        tab_psychometric(params, sigma)
    with tabs[2]:
        tab_comparison(params)


if __name__ == "__main__":
    main()
