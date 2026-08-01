"""
Standalone Stage 4 Streamlit dashboard.

Run:
    streamlit run stage4_human_vision/app.py
"""

import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from stage4_human_vision import load_default_config, run_stage4_point  # noqa: E402
from stage4_human_vision.citations import get_citations  # noqa: E402
from stage4_human_vision.optimize import pareto_front  # noqa: E402
from stage4_human_vision.validation import regression_stats  # noqa: E402


st.set_page_config(page_title="Stage 4 Vision Dashboard", page_icon="👁", layout="wide")

CONFIG = load_default_config()
DISCRETE_APERTURES_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
DEFAULT_M_VALUES = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
STAGE3_INTEGRATED_OUT = os.path.abspath(os.path.join(ROOT, "stage3_integrated", "outputs"))


@st.cache_data(show_spinner="Running Stage 4 simulation...")
def cached_stage4_point(a_hole_um, wavelength_nm, M_diopters, d_gap_mm, scene_luminance_cdm2,
                        field_diameter_deg, age_years, eyes, adaptation_enabled,
                        D_pupil_um, grid_N, window_L_mm):
    t0 = time.time()
    result = run_stage4_point(
        a_hole_um=a_hole_um,
        wavelength_nm=wavelength_nm,
        d_gap_mm=d_gap_mm,
        M_diopters=M_diopters,
        scene_luminance_cdm2=scene_luminance_cdm2,
        field_diameter_deg=field_diameter_deg,
        age_years=age_years,
        eyes=eyes,
        adaptation_enabled=adaptation_enabled,
        D_pupil_um=D_pupil_um,
        grid_N=grid_N,
        window_L_mm=window_L_mm
    )
    return result, time.time() - t0


@st.cache_data(show_spinner=False)
def load_stage3_dataset(filename):
    path = os.path.join(STAGE3_INTEGRATED_OUT, filename)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def sidebar_controls(prefix):
    a_hole_um = st.sidebar.select_slider("Aperture diameter (µm)", options=DISCRETE_APERTURES_UM,
                                         value=400, key=prefix + "a")
    wavelength_nm = st.sidebar.slider("Wavelength (nm)", 400, 700, 550, step=5, key=prefix + "wl")
    myopia = st.sidebar.slider("Myopia M (D)", 0.0, 12.0, 4.0, step=0.5, key=prefix + "m")
    d_gap_mm = st.sidebar.slider("Pinhole-to-cornea gap (mm)", 5.0, 25.0, 12.0, step=0.5, key=prefix + "gap")
    D_pupil_um = st.sidebar.number_input("Natural pupil diameter (µm)", value=4000.0, key=prefix + "pupil")
    scene_luminance_cdm2 = st.sidebar.number_input("Scene luminance (cd/m²)", min_value=0.1,
                                                   value=CONFIG.pipeline.default_scene_luminance_cdm2,
                                                   step=100.0, key=prefix + "lum")
    field_diameter_deg = st.sidebar.slider("Adapting field diameter (deg)", 1.0, 60.0,
                                           float(CONFIG.pipeline.default_field_diameter_deg), step=1.0,
                                           key=prefix + "field")
    age_years = st.sidebar.slider("Observer age (years)", 10, 80, int(CONFIG.pipeline.default_age_years),
                                  step=1, key=prefix + "age")
    eyes = st.sidebar.radio("Viewing condition", [2, 1],
                            format_func=lambda n: "Binocular" if n == 2 else "Monocular",
                            key=prefix + "eyes")
    adaptation_enabled = st.sidebar.checkbox("Enable adaptation", value=True, key=prefix + "adapt")
    return {
        "a_hole_um": a_hole_um,
        "wavelength_nm": wavelength_nm,
        "M_diopters": myopia,
        "d_gap_mm": d_gap_mm,
        "D_pupil_um": D_pupil_um,
        "scene_luminance_cdm2": scene_luminance_cdm2,
        "field_diameter_deg": field_diameter_deg,
        "age_years": age_years,
        "eyes": eyes,
        "adaptation_enabled": adaptation_enabled
    }


def render_live_simulation():
    st.sidebar.header("Live Simulation Controls")
    params = sidebar_controls("live_")
    high_accuracy = st.sidebar.checkbox("High accuracy (grid_N=2048)", value=False, key="live_hiacc")
    grid_N = 2048 if high_accuracy else 512

    result, compute_time_s = cached_stage4_point(
        params["a_hole_um"], params["wavelength_nm"], params["M_diopters"], params["d_gap_mm"],
        params["scene_luminance_cdm2"], params["field_diameter_deg"], params["age_years"],
        params["eyes"], params["adaptation_enabled"], params["D_pupil_um"], grid_N, 6.0
    )

    st.markdown("**grid_N={}** | **compute time {:.3f}s**".format(grid_N, compute_time_s))
    if not result.junction_check_passed:
        st.error("Junction validation failed: {}".format(result.metadata.get("junction_fail_reason", "unknown")))
        return

    optical = result.optical_quality
    pupil = result.pupil
    illuminance = result.illuminance
    adaptation = result.adaptation
    csf = result.csf
    photon_noise = result.photon_noise
    acuity = result.acuity
    visual_strehl = result.visual_strehl

    st.subheader("Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Predicted acuity", "20/{:.0f}".format(acuity["snellen_denominator"]))
    c2.metric("logMAR", "{:.3f}".format(acuity["logmar"]))
    c3.metric("VSOTF", "{:.3f}".format(visual_strehl["vsotf"]))
    c4.metric("Photon SNR", "{:.2f}".format(photon_noise["snr"]))

    st.subheader("Pupil and Illuminance")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Natural pupil", "{:.2f} mm".format(pupil["natural_pupil_diameter_mm"]))
    p2.metric("Effective stop", "{:.2f} mm".format(pupil["effective_stop_diameter_mm"]))
    p3.metric("Photopic Td", "{:.1f}".format(illuminance["retinal_illuminance_photopic_td"]))
    p4.metric("Adaptation response", "{:.3f}".format(adaptation["normalized_response"]))
    st.caption("Iteration count: {} | Equivalent adapting luminance: {:.2f} cd/m²".format(
        illuminance["iterations"], illuminance["equivalent_adapting_luminance_cdm2"]))

    st.subheader("Optical Quality and Noise")
    o1, o2, o3, o4 = st.columns(4)
    o1.metric("RMS spot radius", "{:.2f} µm".format(optical["rms_spot_radius_um"]))
    o2.metric("Strehl ratio", "{:.3f}".format(optical.get("strehl_ratio", float("nan"))))
    o3.metric("MTF50", "{:.2f} cpd".format(optical["mtf50_cpd"]))
    o4.metric("MTF10", "{:.2f} cpd".format(optical["mtf10_cpd"]))
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("Retinal irradiance", "{:.3e} W/m²".format(photon_noise["retinal_irradiance_w_m2"]))
    n2.metric("Photon flux density", "{:.3e}".format(photon_noise["photon_flux_density_per_s_m2"]))
    n3.metric("Expected photons", "{:.3e}".format(photon_noise["expected_photons"]))
    n4.metric("Shot-noise σ", "{:.3e}".format(photon_noise["shot_noise_sigma"]))

    freq = np.array(optical["mtf_frequency_cpd"])
    mtf = np.array(optical["mtf"])
    otf_real = np.array(optical["otf_real"])
    otf_imag = np.array(optical["otf_imag"])
    ptf = np.array(optical["ptf_rad"])

    left, right = st.columns(2)
    with left:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(freq, mtf, color="#2a78d6", label="MTF")
        for model_name, model_data in csf["models"].items():
            vals = np.array(model_data["values"])
            vals = vals / vals.max() if vals.max() > 0 else vals
            ax.plot(freq, vals, linestyle="--", label="CSF: {}".format(model_name))
        ax.set_xlim(0, min(60.0, float(freq.max()) if len(freq) else 60.0))
        ax.set_xlabel("Spatial frequency (cpd)")
        ax.set_ylabel("Normalized value")
        ax.set_title("MTF and CSF")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        st.pyplot(fig)
        plt.close(fig)

    with right:
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        for model_name, weighted in csf["weighted_mtf"].items():
            ax2.plot(freq, weighted["weighted_mtf"], label="{}".format(model_name))
        ax2.set_xlim(0, min(60.0, float(freq.max()) if len(freq) else 60.0))
        ax2.set_xlabel("Spatial frequency (cpd)")
        ax2.set_ylabel("Weighted MTF")
        ax2.set_title("CSF-weighted MTF")
        ax2.grid(alpha=0.3)
        ax2.legend(fontsize=8)
        st.pyplot(fig2)
        plt.close(fig2)

    left2, right2 = st.columns(2)
    with left2:
        fig3, ax3 = plt.subplots(figsize=(6, 4))
        ax3.plot(freq, otf_real, label="Re(OTF)", color="#1baf7a")
        ax3.plot(freq, otf_imag, label="Im(OTF)", color="#e34948")
        ax3.set_xlim(0, min(60.0, float(freq.max()) if len(freq) else 60.0))
        ax3.set_xlabel("Spatial frequency (cpd)")
        ax3.set_ylabel("OTF")
        ax3.set_title("OTF components")
        ax3.grid(alpha=0.3)
        ax3.legend(fontsize=8)
        st.pyplot(fig3)
        plt.close(fig3)

    with right2:
        fig4, ax4 = plt.subplots(figsize=(6, 4))
        ax4.plot(freq, ptf, color="#4a3aa7")
        ax4.set_xlim(0, min(60.0, float(freq.max()) if len(freq) else 60.0))
        ax4.set_xlabel("Spatial frequency (cpd)")
        ax4.set_ylabel("Phase (rad)")
        ax4.set_title("PTF")
        ax4.grid(alpha=0.3)
        st.pyplot(fig4)
        plt.close(fig4)

    st.subheader("CSF model comparison")
    rows = []
    for model_name, model_data in csf["models"].items():
        rows.append({
            "model": model_name,
            "peak_sensitivity": model_data["peak_sensitivity"],
            "peak_frequency_cpd": model_data["peak_frequency_cpd"],
            "cutoff_frequency_cpd": model_data["cutoff_frequency_cpd"],
            "weighted_area": csf["weighted_mtf"][model_name]["area"]
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with st.expander("Raw Stage 4 result"):
        st.json({
            "optical_quality": optical,
            "pupil": pupil,
            "illuminance": illuminance,
            "adaptation": adaptation,
            "visual_strehl": visual_strehl,
            "photon_noise": photon_noise,
            "acuity": acuity,
            "metadata": result.metadata
        })


def run_sweep_rows(apertures_um, M_values, wavelength_nm, d_gap_mm, D_pupil_um,
                   scene_luminance_cdm2, field_diameter_deg, age_years, eyes,
                   adaptation_enabled, grid_N, progress_callback=None):
    rows = []
    total = len(apertures_um) * len(M_values)
    done = 0
    t0 = time.time()
    for a_um in apertures_um:
        for M in M_values:
            result, _ = cached_stage4_point(
                a_um, wavelength_nm, M, d_gap_mm, scene_luminance_cdm2, field_diameter_deg,
                age_years, eyes, adaptation_enabled, D_pupil_um, grid_N, 6.0
            )
            row = {
                "a_hole_um": a_um,
                "M_diopters": M,
                "junction_check_passed": result.junction_check_passed
            }
            if result.junction_check_passed:
                row.update({
                    "rms_spot_radius_um": result.optical_quality["rms_spot_radius_um"],
                    "strehl_ratio": result.optical_quality.get("strehl_ratio", np.nan),
                    "mtf50_cpd": result.optical_quality["mtf50_cpd"],
                    "mtf10_cpd": result.optical_quality["mtf10_cpd"],
                    "retinal_illuminance_photopic_td": result.illuminance["retinal_illuminance_photopic_td"],
                    "vsotf": result.visual_strehl["vsotf"],
                    "snr": result.photon_noise["snr"],
                    "logmar": result.acuity["logmar"],
                    "snellen_denominator": result.acuity["snellen_denominator"]
                })
            rows.append(row)
            done += 1
            if progress_callback:
                progress_callback(done, total, time.time() - t0)
    return pd.DataFrame(rows)


def plot_metric_vs_aperture(df, metric_col):
    fig, ax = plt.subplots(figsize=(8, 5))
    groups = sorted(df["M_diopters"].dropna().unique())
    colors = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7", "#e87ba4", "#008300"]
    for i, g in enumerate(groups):
        sub = df[np.isclose(df["M_diopters"], g)].sort_values("a_hole_um")
        ax.plot(sub["a_hole_um"], sub[metric_col], "o-", color=colors[i % len(colors)], label="M={}".format(g))
    ax.set_xlabel("Aperture diameter (µm)")
    ax.set_ylabel(metric_col)
    ax.set_title("{} vs aperture".format(metric_col))
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    return fig


def plot_heatmap(df, metric_col):
    pivot = df.pivot_table(index="M_diopters", columns="a_hole_um", values=metric_col)
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(pivot.values, aspect="auto", origin="lower", cmap="viridis",
                   extent=[pivot.columns.min(), pivot.columns.max(), pivot.index.min(), pivot.index.max()])
    ax.set_xlabel("Aperture diameter (µm)")
    ax.set_ylabel("Myopia M (D)")
    ax.set_title("{} heatmap".format(metric_col))
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    return fig


def plot_pareto(df):
    valid = df[df["junction_check_passed"]].copy()
    rows = valid[["a_hole_um", "M_diopters", "rms_spot_radius_um", "retinal_illuminance_photopic_td",
                  "vsotf", "logmar"]].to_dict("records")
    front = pareto_front(rows, maximize=["retinal_illuminance_photopic_td", "vsotf"], minimize=["rms_spot_radius_um", "logmar"])
    front_df = pd.DataFrame(front).sort_values("rms_spot_radius_um")
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(valid["rms_spot_radius_um"], valid["retinal_illuminance_photopic_td"], color="lightgray", label="all points")
    ax.plot(front_df["rms_spot_radius_um"], front_df["retinal_illuminance_photopic_td"], "o-", color="#e34948", label="Pareto front")
    for _, row in front_df.iterrows():
        ax.annotate("{}µm / M{}".format(int(row["a_hole_um"]), row["M_diopters"]),
                    (row["rms_spot_radius_um"], row["retinal_illuminance_photopic_td"]),
                    fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("RMS spot radius (µm), minimize")
    ax.set_ylabel("Photopic retinal illuminance (Td), maximize")
    ax.set_title("Stage 4 Pareto front")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig, front_df


def render_sweep_and_pareto():
    st.sidebar.header("Sweep Controls")
    apertures = st.sidebar.multiselect("Apertures (µm)", DISCRETE_APERTURES_UM,
                                       default=[100, 200, 300, 400, 600, 750, 1000, 1500, 2000],
                                       key="sweep_ap")
    M_values = st.sidebar.multiselect("Myopia levels (D)", DEFAULT_M_VALUES, default=DEFAULT_M_VALUES, key="sweep_m")
    wavelength_nm = st.sidebar.slider("Wavelength (nm)", 400, 700, 550, step=5, key="sweep_wl")
    d_gap_mm = st.sidebar.slider("Gap (mm)", 5.0, 25.0, 12.0, step=0.5, key="sweep_gap")
    D_pupil_um = st.sidebar.number_input("Natural pupil diameter (µm)", value=4000.0, key="sweep_pupil")
    scene_luminance_cdm2 = st.sidebar.number_input("Scene luminance (cd/m²)", min_value=0.1, value=1000.0,
                                                   step=100.0, key="sweep_lum")
    field_diameter_deg = st.sidebar.slider("Field diameter (deg)", 1.0, 60.0, 20.0, step=1.0, key="sweep_field")
    age_years = st.sidebar.slider("Age (years)", 10, 80, 30, step=1, key="sweep_age")
    eyes = st.sidebar.radio("Viewing condition", [2, 1],
                            format_func=lambda n: "Binocular" if n == 2 else "Monocular",
                            key="sweep_eyes")
    adaptation_enabled = st.sidebar.checkbox("Enable adaptation", value=True, key="sweep_adapt")

    n_points = len(apertures) * len(M_values)
    st.caption("{} configurations".format(n_points))
    if st.button("Run Stage 4 sweep", type="primary"):
        if n_points == 0:
            st.error("Select at least one aperture and one M value.")
            return
        if n_points > 250:
            st.error("Interactive Stage 4 sweep capped at 250 points.")
            return
        status = st.empty()
        progress = st.progress(0)
        status.text("Starting sweep...")

        def _cb(done, total, elapsed):
            progress.progress(done / float(total))
            status.text("{}/{} ({:.0f}s elapsed)".format(done, total, elapsed))

        df = run_sweep_rows(apertures, M_values, wavelength_nm, d_gap_mm, D_pupil_um,
                            scene_luminance_cdm2, field_diameter_deg, age_years, eyes,
                            adaptation_enabled, 512, progress_callback=_cb)
        progress.progress(1.0)
        status.text("Done.")
        st.session_state["stage4_sweep_df"] = df

    df = st.session_state.get("stage4_sweep_df")
    if df is None:
        return

    st.subheader("Sweep Results")
    metric = st.selectbox("Metric", ["rms_spot_radius_um", "strehl_ratio", "mtf50_cpd", "mtf10_cpd",
                                     "retinal_illuminance_photopic_td", "vsotf", "snr", "logmar", "snellen_denominator"])
    kind = st.radio("Plot type", ["Line", "Heatmap", "Pareto"], horizontal=True)
    if kind == "Line":
        st.pyplot(plot_metric_vs_aperture(df[df["junction_check_passed"]], metric))
    elif kind == "Heatmap":
        st.pyplot(plot_heatmap(df[df["junction_check_passed"]], metric))
    else:
        fig, front_df = plot_pareto(df)
        st.pyplot(fig)
        st.dataframe(front_df, use_container_width=True)
    st.dataframe(df, use_container_width=True)
    st.download_button("Download sweep CSV", df.to_csv(index=False).encode(), file_name="stage4_sweep.csv")


def render_validation_and_datasets():
    st.subheader("Validation and Data")
    dataset = st.selectbox("Reference dataset", ["combined_grid_550nm_12mm.csv", "phase3_full_metrics.csv"])
    df = load_stage3_dataset(dataset) if dataset == "combined_grid_550nm_12mm.csv" else None
    if dataset == "phase3_full_metrics.csv":
        path = os.path.join(ROOT, "stage3_human_vision", "outputs", dataset)
        df = pd.read_csv(path) if os.path.exists(path) else None
    if df is None:
        st.warning("Dataset not found.")
        return
    st.dataframe(df.head(50), use_container_width=True)

    if "mtf50_cpd" in df.columns and "mtf10_cpd" in df.columns:
        stats = regression_stats(df["mtf50_cpd"].fillna(0).tolist(), df["mtf10_cpd"].fillna(0).tolist())
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("RMSE", "{:.3f}".format(stats["rmse"]))
        s2.metric("MAE", "{:.3f}".format(stats["mae"]))
        s3.metric("R²", "{:.3f}".format(stats["r2"]))
        s4.metric("Pearson r", "{:.3f}".format(stats["pearson_r"]))

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(df["mtf50_cpd"], df["mtf10_cpd"], alpha=0.7, color="#2a78d6")
        ax.set_xlabel("MTF50 (cpd)")
        ax.set_ylabel("MTF10 (cpd)")
        ax.set_title("Reference dataset scatter")
        ax.grid(alpha=0.3)
        st.pyplot(fig)
        plt.close(fig)


def render_citations():
    st.subheader("Model citations")
    citations = get_citations()
    rows = []
    for key, entry in citations.items():
        row = {"id": key}
        row.update(entry)
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def main():
    st.title("Stage 4 Human Vision Dashboard")
    st.caption("Standalone Streamlit app for the Stage 4 biological vision layer. "
               "This app is separate from the original simulator.")
    tabs = st.tabs(["Live Simulation", "Sweep and Pareto", "Validation and Data", "Citations"])
    with tabs[0]:
        render_live_simulation()
    with tabs[1]:
        render_sweep_and_pareto()
    with tabs[2]:
        render_validation_and_datasets()
    with tabs[3]:
        render_citations()


if __name__ == "__main__":
    main()
