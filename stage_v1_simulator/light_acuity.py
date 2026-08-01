"""
Light & Acuity tab: wires stage4_human_vision's pupil/illuminance/CSF/VSOTF/acuity
layer into this app. Reuses the SAME aperture/myopia/wavelength/gap sidebar sliders
every other tab uses (sidebar_controls(), passed in as `params` -- not duplicated
here) and adds only the sliders Stage 4 itself needs: scene luminance (log scale),
age, adapting field diameter, and monocular/binocular viewing.

Live compute follows the same fast/high-accuracy split as the rest of this app
(grid_N=512 default ~0.5s, grid_N=2048 button ~10s -- see streamlit_app.py's Live
Explorer tab for the same pattern). The metric-vs-aperture plot is loaded from
stage4_human_vision/outputs/stage4_full_sweep.csv (Stage 4's own precomputed sweep,
run once end-to-end -- see stage4_human_vision/RESULTS.md), never recomputed live;
the live point is marked on top of it, same convention as this app's existing
precomputed-vs-live-point overlay in Live Explorer.

No "recommended aperture" output here or anywhere else in this app.
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

from stage4_human_vision import run_stage4_point, load_default_config  # noqa: E402

CONFIG = load_default_config()
STAGE4_OUT = os.path.join(_ROOT, "stage4_human_vision", "outputs")
SWEEP_CSV = os.path.join(STAGE4_OUT, "stage4_full_sweep.csv")
VALIDATION_CSV = os.path.join(STAGE4_OUT, "validation_regression_stats.csv")

PRECOMPUTED_M_VALUES = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
PRECOMPUTED_LUMINANCE = [10000.0, 1000.0, 100.0]

CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7", "#e87ba4", "#008300"]

METRIC_OPTIONS = {
    "Predicted logMAR (recommended model)": ("logmar_recommended", "logMAR"),
    "VSOTF": ("vsotf", "VSOTF"),
    "CSF-weighted MTF area (Barten)": ("barten_weighted_mtf_area", "weighted MTF area"),
    "Retinal illuminance (Td)": ("retinal_illuminance_photopic_td", "Td"),
}


@st.cache_data(show_spinner="Running Stage 4 (pupil/illuminance/CSF/VSOTF/acuity)...")
def cached_stage4_point(a_hole_um, wavelength_nm, M_diopters, d_gap_mm, D_pupil_um, P0,
                         refractive_index_correction, scene_luminance_cdm2,
                         field_diameter_deg, age_years, eyes, grid_N, window_L_mm=6.0):
    return run_stage4_point(
        a_hole_um=a_hole_um, wavelength_nm=wavelength_nm, d_gap_mm=d_gap_mm,
        M_diopters=M_diopters, D_pupil_um=D_pupil_um, P0=P0,
        refractive_index_correction=refractive_index_correction,
        scene_luminance_cdm2=scene_luminance_cdm2,
        field_diameter_deg=field_diameter_deg, age_years=age_years, eyes=eyes,
        grid_N=grid_N, window_L_mm=window_L_mm, config=CONFIG,
    )


@st.cache_data(show_spinner=False)
def load_sweep_csv():
    if not os.path.exists(SWEEP_CSV):
        return None
    return pd.read_csv(SWEEP_CSV)


@st.cache_data(show_spinner=False)
def load_validation_caveat():
    """Pulls the actual R^2/p range for the recommended predictor straight from
    stage4_human_vision's own validation output, so this caveat can't drift out of
    sync with a re-run of the validation script."""
    if not os.path.exists(VALIDATION_CSV):
        return ("Stage 4's clinical validation output was not found -- run "
                "stage4_human_vision's validation script first. Treat any acuity "
                "number below as unvalidated until that exists.")
    df = pd.read_csv(VALIDATION_CSV)
    rec = df[df["predictor"] == "logmar_recommended"]
    if len(rec) == 0:
        return ("Stage 4's clinical validation output has no 'logmar_recommended' "
                "row -- treat any acuity number below as unvalidated.")
    r2_lo, r2_hi = rec["r2"].min(), rec["r2"].max()
    p_lo, p_hi = rec["pearson_p_value"].min(), rec["pearson_p_value"].max()
    passed = (r2_lo > 0) and (p_hi < 0.05)
    if passed:
        return (f"Validated against clinical data (Wang 2009 'Ideal Pinhole', n=5 apertures): "
                f"R²={r2_lo:.2f}-{r2_hi:.2f}, p={p_lo:.3f}-{p_hi:.3f} across M={sorted(rec['M_diopters'].unique())}D.")
    return (f"NOT validated with statistical significance against clinical data "
            f"(R²={r2_lo:.2f} to {r2_hi:.2f}, p={p_lo:.2f}-{p_hi:.2f} vs Wang 2009 'Ideal Pinhole' "
            f"clinical pinhole-acuity data across M={sorted(rec['M_diopters'].unique())}D -- R²<0 and "
            f"p>>0.05 at every M tested). Treat the acuity number below as exploratory, not clinically "
            f"predictive. A cited brightness correction and a calibration attempt were "
            f"tried and also failed honest leave-one-out validation -- see "
            f"stage4_human_vision/RESULTS.md Sections 2 and 4 for the full analysis.")


def _nearest(value, options):
    return min(options, key=lambda o: abs(o - value))


def render(params):
    st.sidebar.header("Light & Acuity controls")
    st.sidebar.caption("Reuses the aperture/myopia/wavelength/gap sliders above.")

    log_lum = st.sidebar.slider("Scene luminance (log₁₀ cd/m²)", -1.0, 4.5, 4.0, step=0.1,
                                 key="light_loglum",
                                 help="-1 = 0.1 cd/m² (deep mesopic) ... 4.5 ≈ 31600 cd/m² (very bright).")
    scene_luminance_cdm2 = 10.0 ** log_lum
    st.sidebar.caption(f"= {scene_luminance_cdm2:,.1f} cd/m²")

    age_years = st.sidebar.slider("Observer age (years)", 10, 80, int(CONFIG.pipeline.default_age_years),
                                   step=1, key="light_age")
    field_diameter_deg = st.sidebar.slider("Adapting field diameter (deg)", 1.0, 60.0,
                                            float(CONFIG.pipeline.default_field_diameter_deg), step=1.0,
                                            key="light_field")
    eyes = st.sidebar.radio("Viewing condition", [2, 1],
                             format_func=lambda n: "Binocular" if n == 2 else "Monocular",
                             key="light_eyes")

    col_grid, col_btn = st.columns([2, 1])
    with col_grid:
        st.caption("Default interactive grid: **N=512** (fast preview, ~0.5s). "
                   "Use the button for a validated high-accuracy point (matches "
                   "the precomputed sweep's resolution).")
    with col_btn:
        high_accuracy = st.button("Compute at high accuracy (grid_N=2048, ~10s)", key="light_hiacc")
    grid_N = 2048 if high_accuracy else 512

    result = cached_stage4_point(
        params["a_hole_um"], params["wavelength_nm"], params["M_diopters"], params["d_gap_mm"],
        params["D_pupil_um"], params["P0"], params["refractive_index_correction"],
        scene_luminance_cdm2, field_diameter_deg, age_years, eyes, grid_N,
    )

    if not result.junction_check_passed:
        st.error(f"Junction validation failed: {result.metadata.get('junction_fail_reason')}")
        return

    st.markdown(f"**grid_N = {grid_N}**")

    pupil = result.pupil
    illum = result.illuminance
    vsotf = result.visual_strehl["vsotf"]
    barten_area = result.csf["weighted_mtf"]["barten"]["area"]
    acuity = result.acuity

    st.markdown("**Pupil and retinal illuminance**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Natural pupil (Watson-Yellott)", f"{pupil['natural_pupil_diameter_mm']:.2f} mm",
              help="This model's fixed-point-converged pupil size for CONTINUOUS wear of this "
                   "exact pinhole -- coupled to the pinhole-restricted retinal illuminance, not "
                   "just the raw scene luminance. Not the same as the 'Natural pupil diameter' "
                   "input in the sidebar above, which instead feeds Stage 2/3's optics reference "
                   "and is not physiologically modeled. See stage4_human_vision/CHANGES.md.")
    c2.metric("Effective stop", f"{pupil['effective_stop_diameter_mm']:.2f} mm",
              help="min(natural pupil, pinhole aperture) -- almost always the pinhole itself "
                   "in this aperture range.")
    c3.metric("Retinal illuminance", f"{illum['retinal_illuminance_photopic_td']:.1f} Td")
    c4.metric("Equivalent adapting luminance", f"{illum['equivalent_adapting_luminance_cdm2']:.2f} cd/m²",
              help="What ambient luminance would give an unobstructed eye this same retinal Td. "
                   "<~3 cd/m² is mesopic -- a small pinhole can cross this even under a bright scene.")

    st.markdown("**Visual quality**")
    d1, d2, d3 = st.columns(3)
    d1.metric("CSF-weighted MTF area (Barten)", f"{barten_area:.1f}")
    d2.metric("VSOTF", f"{vsotf:.3f}",
              help="Can exceed 1.0 in this near-field regime -- same documented Fresnel-regime "
                   "finding as Strehl elsewhere in this app, not a bug specific to this number.")
    d3.metric("Predicted acuity", f"20/{acuity['snellen_denominator']:.0f}  (logMAR {acuity['logmar']:.3f})")

    st.warning("**Clinical validation status:** " + load_validation_caveat())

    st.subheader("Precomputed sweep, live point marked")
    metric_label = st.selectbox("Metric", list(METRIC_OPTIONS.keys()), key="light_metric")
    metric_col, metric_short = METRIC_OPTIONS[metric_label]

    sweep_df = load_sweep_csv()
    if sweep_df is None:
        st.info(f"Precomputed sweep not found at {SWEEP_CSV} -- run stage4_human_vision's "
                f"production sweep first (see RESULTS.md Section 3).")
        return

    nearest_M = _nearest(params["M_diopters"], PRECOMPUTED_M_VALUES)
    nearest_lum = _nearest(scene_luminance_cdm2, PRECOMPUTED_LUMINANCE)
    st.caption(f"Showing precomputed curve nearest to your sliders: M={nearest_M:.0f}D, "
               f"luminance={nearest_lum:.0f} cd/m² (your exact live point is still computed "
               f"and plotted at its own live values above).")

    g = sweep_df[np.isclose(sweep_df["M_diopters"], nearest_M) &
                 np.isclose(sweep_df["scene_luminance_cdm2"], nearest_lum) &
                 sweep_df["junction_check_passed"]].sort_values("a_hole_um")

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.plot(g["a_hole_um"], g[metric_col], "o-", color=CATEGORICAL[0],
            label=f"precomputed sweep (M={nearest_M:.0f}D, {nearest_lum:.0f} cd/m²)")
    ax.plot(params["a_hole_um"], result_metric_value(result, metric_col), "*", color=CATEGORICAL[3],
            markersize=20, markeredgecolor="black",
            label=f"your live point (M={params['M_diopters']:.1f}D, {scene_luminance_cdm2:.0f} cd/m²)")
    ax.set_xlabel("aperture diameter (µm)")
    ax.set_ylabel(metric_short)
    ax.set_title(f"{metric_label} vs aperture")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def result_metric_value(result, metric_col):
    lookup = {
        "logmar_recommended": result.acuity["logmar"],
        "vsotf": result.visual_strehl["vsotf"],
        "barten_weighted_mtf_area": result.csf["weighted_mtf"]["barten"]["area"],
        "retinal_illuminance_photopic_td": result.illuminance["retinal_illuminance_photopic_td"],
    }
    return lookup[metric_col]
