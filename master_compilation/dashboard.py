"""
Master results dashboard -- loads master_compilation/master_results.xlsx (built by
compile_master_results.py, which must be run first) and provides an interactive view
across every stage's findings in one place, plus a live single-point calculator reusing
existing project code (stage2/stage3a) for quick sanity checks against the compiled
sweeps.

Run: streamlit run master_compilation/dashboard.py
Requires: streamlit, pandas, plotly, openpyxl (pip install if missing)

Does NOT recompute any of the heavy sweeps (Stage 2/3/4 physics, the ghosting harmonic
analysis) -- this is a viewer over already-compiled results, consistent with the
fast/precomputed-first pattern used throughout stage_v1_simulator. The one exception is
the "Live Point Check" tab, which does one cheap Stage 2 propagation on demand (a few
seconds), clearly separated from the precomputed-sweep tabs.
"""
import os
import sys

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MASTER_XLSX = os.path.join(ROOT, "master_compilation", "master_results.xlsx")

st.set_page_config(page_title="Pinhole Project -- Master Results Dashboard", layout="wide")
st.title("Pinhole Sunglasses Project -- Master Results Dashboard")
st.caption("Consolidated view across all stages. Run `python3 master_compilation/compile_master_results.py` "
           "first (and re-run it after any sweep changes) to refresh the underlying data.")

if not os.path.exists(MASTER_XLSX):
    st.error(f"master_results.xlsx not found at {MASTER_XLSX}. Run "
             "`python3 master_compilation/compile_master_results.py` from the project root first.")
    st.stop()


@st.cache_data
def load_all_sheets(path, mtime):
    """mtime is passed in purely so the Streamlit cache invalidates automatically
    whenever the underlying xlsx file changes on disk, without the user needing to
    manually clear the cache."""
    xl = pd.ExcelFile(path, engine="openpyxl")
    return {name: xl.parse(name) for name in xl.sheet_names}


mtime = os.path.getmtime(MASTER_XLSX)
sheets = load_all_sheets(MASTER_XLSX, mtime)
st.sidebar.success(f"Loaded {len(sheets)} sheets from master_results.xlsx\n\n"
                    f"Last compiled: {pd.Timestamp.fromtimestamp(mtime):%Y-%m-%d %H:%M}")

tab_names = ["Overview / Provenance", "Blur + Illumination Grid", "Model Comparison (RSS vs Exact)",
             "Stage 4 Acuity Validation", "Ghosting Regime Map", "Brightness Reconciliation",
             "Raw Sheet Browser", "Live Point Check"]
tabs = st.tabs(tab_names)

# ---------------------------------------------------------------------------
with tabs[0]:
    st.header("What's in this workbook")
    if "INDEX_Provenance" in sheets:
        st.dataframe(sheets["INDEX_Provenance"], use_container_width=True)
    else:
        st.warning("No INDEX_Provenance sheet found -- was compile_master_results.py run with the current version?")
    st.markdown("""
    **How to read this dashboard:** each tab below corresponds to one sheet, chosen
    deliberately because the underlying data has a genuinely different shape (aperture x
    myopia vs. aperture x pitch vs. luminance-only) -- they are NOT merged into one flat
    table, to avoid silent NaN-filled rows or misaligned joins.
    """)

# ---------------------------------------------------------------------------
with tabs[1]:
    st.header("Master Blur + Illumination Grid (550nm, 12mm gap)")
    df = sheets.get("Master_Grid_Blur_Illum")
    if df is None:
        st.warning("Sheet not found.")
    else:
        M_values = sorted(df["M_diopters"].unique())
        metric_options = [c for c in ["r_EE_50_um", "r_EE_80_um", "r_EE_90_um", "rms_spot_radius_um",
                                        "strehl_ratio", "mtf50_cpd", "percent_illumination"] if c in df.columns]
        col1, col2 = st.columns(2)
        metric = col1.selectbox("Metric", metric_options, index=0)
        selected_M = col2.multiselect("Myopia levels (D)", M_values, default=M_values)
        plot_df = df[df["M_diopters"].isin(selected_M)]
        fig = px.line(plot_df.sort_values("a_hole_um"), x="a_hole_um", y=metric, color="M_diopters",
                       markers=True, log_x=True, title=f"{metric} vs aperture, by myopia level")
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("Show raw data"):
            st.dataframe(df, use_container_width=True)

# ---------------------------------------------------------------------------
with tabs[2]:
    st.header("Model Comparison: Exact Numerics vs. the Deprecated RSS Formula")
    df = sheets.get("Model_Comparison_RSS_vs_Exact")
    if df is None:
        st.warning("Sheet not found.")
    else:
        st.markdown("**Chapter 7 finding**: the old closed-form RSS combination diverges "
                     "from the exact numerical result by a mean of 64.8% (max 192.8%) at the retina plane.")
        M_sel = st.selectbox("Myopia level (D)", sorted(df["M_diopters"].unique()), key="mc_M")
        wl_sel = st.selectbox("Wavelength (nm)", sorted(df["wavelength_nm"].unique()), key="mc_wl")
        sub = df[(df["M_diopters"] == M_sel) & (df["wavelength_nm"] == wl_sel)].sort_values("a_hole_um")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sub["a_hole_um"], y=sub["stage2_r_EE_50_um"], name="Exact (Stage 2 r_EE 50%)", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=sub["a_hole_um"], y=sub["approx_r_total_um"], name="Deprecated RSS approximation", mode="lines+markers"))
        fig.update_layout(xaxis_type="log", xaxis_title="aperture (um)", yaxis_title="blur radius (um)",
                           title=f"Exact vs. RSS approximation, M={M_sel}D, {wl_sel}nm")
        st.plotly_chart(fig, use_container_width=True)
        fig2 = px.line(sub, x="a_hole_um", y="rel_diff_r_total_vs_r_EE50_pct", markers=True, log_x=True,
                        title="RSS relative divergence (%) vs. aperture")
        st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
with tabs[3]:
    st.header("Stage 4 Acuity Validation Against Real Clinical Data (Wang 2009)")
    df = sheets.get("Stage4_Wang2009_Validation")
    if df is None:
        st.warning("Sheet not found.")
    else:
        st.markdown("**Validation bar: R² > 0 AND p < 0.05. Neither luminance condition clears it -- "
                     "see `stage4_human_vision/LUMINANCE_RECONCILIATION.md` for why correcting "
                     "the luminance assumption does not fix this.**")
        fig = px.bar(df, x="M_diopters", y="r2", color="luminance_context", barmode="group",
                     title="R² by myopia level and luminance condition (negative = worse than predicting the mean)")
        fig.add_hline(y=0, line_dash="dash", line_color="black")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

# ---------------------------------------------------------------------------
with tabs[4]:
    st.header("Ghosting Regime Map (Real Barten CSF + Full Harmonic Series)")
    df = sheets.get("Ghosting_Regime_Aperture_x_Pitch")
    if df is None:
        st.warning("Sheet not found.")
    else:
        color_map = {"A": "#1baf7a", "B": "#eda100", "C": "#e34948"}
        fig = px.scatter(df, x="pitch_um", y="a_hole_um", color="regime",
                          color_discrete_map=color_map, log_x=True,
                          hover_data=["N_eff_worst", "worst_n_harmonic", "worst_margin"],
                          title="A=sparse/safe, B=dense/filtered, C=danger zone (harmonic-corrected)")
        fig.add_vrect(x0=3200, x1=4800, fillcolor="purple", opacity=0.08, annotation_text="KR patent range")
        fig.add_vrect(x0=700, x1=1200, fillcolor="blue", opacity=0.08, annotation_text="CN patent range")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Finding**: every dense-pitch point (N_eff>1) classifies as danger zone once the "
                     "real Barten CSF and full harmonic series are used -- including the entire real CN "
                     "patent pitch range. See `array_ghosting_theory/RESULTS.md`.")
        st.dataframe(df, use_container_width=True)

# ---------------------------------------------------------------------------
with tabs[5]:
    st.header("Brightness Floor Reconciliation: Percentage vs. Absolute (Troland) Thresholds")
    df = sheets.get("Brightness_Reconciliation")
    if df is None:
        st.warning("Sheet not found.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["scene_luminance_cdm2"], y=df["min_aperture_um_van_nes_bouman_floor"],
                                   name="Van Nes & Bouman (1967) strict floor", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=df["scene_luminance_cdm2"], y=df["min_aperture_um_CIE_floor_low"],
                                   name="CIE 191:2010 floor (low)", mode="lines", line=dict(dash="dot")))
        fig.add_trace(go.Scatter(x=df["scene_luminance_cdm2"], y=df["min_aperture_um_CIE_floor_high"],
                                   name="CIE 191:2010 floor (high)", mode="lines", line=dict(dash="dot")))
        fig.add_hrect(y0=900, y1=1250, fillcolor="orange", opacity=0.1, annotation_text="reverse-engineered floor")
        fig.add_hrect(y0=940, y1=1750, fillcolor="gray", opacity=0.08, annotation_text="clinical bracket")
        fig.update_layout(xaxis_type="log", yaxis_type="log", xaxis_title="scene luminance (cd/m^2)",
                           yaxis_title="minimum aperture to clear floor (um)",
                           title="At ~300 cd/m^2 (realistic clinical luminance), Van Nes & Bouman's floor "
                                 "lands near the reverse-engineered range; at this project's own bright-"
                                 "daylight default (10000), it does not.")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

# ---------------------------------------------------------------------------
with tabs[6]:
    st.header("Raw Sheet Browser")
    sheet_choice = st.selectbox("Sheet", list(sheets.keys()))
    st.dataframe(sheets[sheet_choice], use_container_width=True)
    st.download_button("Download this sheet as CSV", sheets[sheet_choice].to_csv(index=False),
                        file_name=f"{sheet_choice}.csv")

# ---------------------------------------------------------------------------
with tabs[7]:
    st.header("Live Point Check (single Stage 2 propagation, ~2-5s)")
    st.caption("Sanity-checks one point against the precomputed sweeps above. Does NOT recompute any "
               "full sweep -- if this disagrees with the Master Grid tab at the same parameters, that's "
               "a real discrepancy worth investigating, not expected behavior.")
    try:
        sys.path.insert(0, os.path.join(ROOT, "stage2_fixed"))
        sys.path.insert(0, os.path.join(ROOT, "stage3a"))
        import phase2_retina as p2
        import transmission as illum

        c1, c2, c3 = st.columns(3)
        a_hole = c1.select_slider("Aperture (um)", options=[75,100,150,200,300,400,500,600,700,750,1000,1250,1500,1750,2000], value=1000)
        M = c2.slider("Myopia (D)", 1.0, 8.0, 4.0, 0.5)
        D_pupil = c3.number_input("Pupil diameter (um)", value=4000.0)

        if st.button("Compute"):
            with st.spinner("Running Stage 2 propagation..."):
                result = p2.run_pipeline_point(
                    a_hole=a_hole*1e-6, wavelength=550e-9, d_gap=12e-3, grid_N=1024, window_L_mm=6.0,
                    M_diopters=M, P0=60.0, n_prime=1.336, D_pupil_um=D_pupil, refractive_index_correction=True)
                if result["junction_check_passed"]:
                    e_rel = illum.relative_illuminance(a_hole, D_pupil)
                    cols = st.columns(3)
                    cols[0].metric("r_EE(50%)", f"{result['retina_EE']['r_EE_50']*1e6:.2f} um")
                    cols[1].metric("r_EE(80%)", f"{result['retina_EE']['r_EE_80']*1e6:.2f} um")
                    cols[2].metric("Relative illuminance", f"{e_rel*100:.3f}%")
                else:
                    st.error(f"Junction check failed: {result['junction_fail_reason']}")
    except ImportError as e:
        st.error(f"Could not import stage2_fixed/stage3a modules: {e}. This tab requires running "
                 "the dashboard from within the project's own environment.")
