"""
Sweep & Explore: (1) a static gallery of stage3_integrated's precomputed plots/tables
(never recomputed live), (2) interactive exploration of stage3_integrated's precomputed
CSVs with user-chosen metric/axis/plot-type, and (3) a live sweep runner for custom
aperture/M/wavelength/gap grids -- addressing the "current model has limited
functionality" gap: previously this tab could only show fixed pre-rendered images.

Literature comparison still renders literature.py's CITATIONS dict directly (imported,
never hand-copied).
"""

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweep_ui

_STAGE3_INTEGRATED_OUT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "stage3_integrated", "outputs"))
_STAGE3HV_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage3_human_vision"))
if _STAGE3HV_DIR not in sys.path:
    sys.path.insert(0, _STAGE3HV_DIR)

CATEGORIES = {
    "Optical transfer function": ["mtf_curves.png", "mtf50_extended.png"],
    "Contrast sensitivity": ["csf_comparison.png"],
    "Photometry / illuminance": ["illuminance_troland.png"],
    "Visual acuity": ["acuity_models_combined.png"],
    "Strehl ratio investigation": ["strehl_investigation.png"],
    "Encircled energy": ["ee_all_percentiles.png"],
    "Retina-plane FWHM": ["retina_fwhm_ring_hopping.png"],
    "Pareto fronts": ["pareto_all_M_overlay.png"],
    "Sensitivity heatmaps": ["sensitivity_heatmaps_aperture_M.png", "sensitivity_heatmap_wavelength_aperture.png"],
    "Validation": ["validation_tolerance_bands.png"],
}

TABLES = {
    "Optimum aperture by metric (constrained, all T_min)": "constrained_optimum_all_metrics.csv",
    "Validation statistics": "table_validation_statistics.csv",
    "Uncertainty propagation": "table_uncertainty_propagation.csv",
    "Error budget (extended)": "table_error_budget_extended.csv",
    "Literature citations (rendered from literature.py directly)": "table_literature_citations.csv",
}

# Precomputed sweep datasets available for interactive exploration -- every CSV
# stage3_integrated/stage3a/stage2_fixed actually produced, not just the merged one.
PRECOMPUTED_DATASETS = {
    "Combined grid (550nm/12mm, full metric set, 105pts)": "combined_grid_550nm_12mm.csv",
    "Wavelength/gap coverage (450/650nm + 15mm gap subset)": "wavelength_gap_sweep.csv",
    "Fine Strehl investigation (100um steps, M=4/8D)": "fine_strehl_sweep.csv",
    "Retina-plane FWHM (full grid)": "retina_fwhm_sweep.csv",
}

METRIC_COLUMNS_BY_DATASET = {
    "combined_grid_550nm_12mm.csv": ["r_EE_50_um", "r_EE_70_um", "r_EE_80_um", "r_EE_90_um",
                                      "rms_spot_radius_um", "strehl_ratio", "mtf50_cpd", "mtf10_cpd",
                                      "throughput_area_ratio", "relative_retinal_illuminance",
                                      "retinal_illuminance_troland", "snellen_denom_mtf50", "snellen_denom_mtf10"],
    "wavelength_gap_sweep.csv": ["r_EE_50_um", "r_EE_80_um", "r_EE_90_um", "rms_spot_radius_um",
                                 "strehl_ratio", "mtf50_cpd", "throughput_area_ratio"],
    "fine_strehl_sweep.csv": ["strehl_ratio", "r_EE_50_um", "mtf50_cpd"],
    "retina_fwhm_sweep.csv": ["fwhm_radius_um", "crossing_count"],
}


def _static_gallery():
    if not os.path.isdir(_STAGE3_INTEGRATED_OUT):
        st.error(f"stage3_integrated/outputs not found at {_STAGE3_INTEGRATED_OUT} -- "
                 f"run `python3 stage3_integrated/run_full_theory_sweep.py` and "
                 f"`generate_plots.py`/`generate_tables.py` first.")
        return
    category = st.selectbox("Category", list(CATEGORIES.keys()))
    for fname in CATEGORIES[category]:
        path = os.path.join(_STAGE3_INTEGRATED_OUT, fname)
        if os.path.exists(path):
            st.image(path, caption=fname, use_column_width=True)
        else:
            st.warning(f"{fname} not found -- run stage3_integrated/generate_plots.py")


def _tables():
    table_label = st.selectbox("Table", list(TABLES.keys()))
    path = os.path.join(_STAGE3_INTEGRATED_OUT, TABLES[table_label])
    if os.path.exists(path):
        df = pd.read_csv(path)
        st.dataframe(df, use_container_width=True)
        st.download_button("Download CSV", df.to_csv(index=False).encode(),
                            file_name=TABLES[table_label], mime="text/csv")
    else:
        st.warning(f"{TABLES[table_label]} not found -- run stage3_integrated/generate_tables.py")


def _literature():
    import literature
    st.markdown("Rendered directly from `stage3_human_vision/literature.py`'s "
                 "`CITATIONS` dict -- cannot drift out of sync with the source.")
    rows = []
    for key, entry in literature.CITATIONS.items():
        rows.append({"key": key, "type": entry["type"], "statement": entry["statement"],
                     "source": entry["source"], "fidelity": entry["fidelity"]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def _interactive_explore():
    st.caption("Browses stage3_integrated's precomputed sweep CSVs with your own choice "
               "of metric, axis, and plot type -- data is real, plots are generated on "
               "demand (no simulation is re-run).")
    dataset_label = st.selectbox("Dataset", list(PRECOMPUTED_DATASETS.keys()))
    fname = PRECOMPUTED_DATASETS[dataset_label]
    path = os.path.join(_STAGE3_INTEGRATED_OUT, fname)
    if not os.path.exists(path):
        st.warning(f"{fname} not found -- run stage3_integrated/run_full_theory_sweep.py first.")
        return
    df = pd.read_csv(path)

    available_metrics = [c for c in METRIC_COLUMNS_BY_DATASET.get(fname, df.columns) if c in df.columns]
    metric_col = st.selectbox("Metric", available_metrics, format_func=lambda c: sweep_ui.METRIC_LABELS.get(c, c))
    plot_type = st.radio("Plot type", ["Line (vs aperture, grouped)", "Heatmap", "Pareto front"], horizontal=True)

    group_col = "M_diopters" if "M_diopters" in df.columns else ("wavelength_nm" if "wavelength_nm" in df.columns else None)

    if plot_type == "Line (vs aperture, grouped)":
        fig = sweep_ui.plot_metric_vs_aperture_grouped(df, metric_col, group_col=group_col or "M_diopters")
        st.pyplot(fig)
    elif plot_type == "Heatmap":
        y_col = st.selectbox("Heatmap Y axis", [c for c in ["M_diopters", "wavelength_nm", "z_gap_mm"] if c in df.columns])
        fig = sweep_ui.plot_heatmap(df, metric_col, y_col=y_col)
        st.pyplot(fig)
    else:
        if group_col is None or group_col not in df.columns:
            st.info("This dataset has no M/wavelength grouping column for a Pareto front.")
        else:
            group_val = st.selectbox(f"{group_col} value", sorted(df[group_col].dropna().unique()))
            illum_col = "throughput_area_ratio" if "throughput_area_ratio" in df.columns else "relative_retinal_illuminance"
            fig = sweep_ui.plot_pareto_front_ui(df, metric_col, illum_col, group_val, group_col=group_col)
            st.pyplot(fig)

    with st.expander("Raw data"):
        st.dataframe(df, use_container_width=True)
        st.download_button("Download this dataset (CSV)", df.to_csv(index=False).encode(), file_name=fname)


def _run_new_sweep():
    st.caption("Runs a LIVE sweep at grid_N=512 (fast preview resolution -- see "
               "Live Explorer tab for the accuracy/speed tradeoff). Reuses the same "
               "compute path as every other tab; no new physics.")

    c1, c2 = st.columns(2)
    with c1:
        aperture_choice = st.multiselect("Apertures (µm)", sweep_ui.DEFAULT_APERTURES_UM,
                                          default=[100, 200, 300, 400, 600, 750, 1000, 1500, 2000])
        wavelength_nm = st.slider("Wavelength (nm)", 400, 700, 550, step=5, key="sweep_wl")
    with c2:
        M_values = st.multiselect("Myopia levels M (D)", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0],
                                   default=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0])
        d_gap_mm = st.slider("Gap (mm)", 5.0, 25.0, 12.0, step=0.5, key="sweep_gap")

    D_pupil_um = st.number_input("Natural pupil diameter (µm)", value=4000.0, key="sweep_pupil")
    n_points = len(aperture_choice) * len(M_values)
    st.caption(f"{n_points} configurations -- estimated ~{n_points * 0.6:.0f}s at grid_N=512.")

    if st.button("Run sweep", type="primary"):
        if n_points == 0:
            st.error("Select at least one aperture and one M value.")
            return
        if n_points > 300:
            st.error(f"{n_points} configurations is too large for an interactive sweep -- narrow your selection.")
            return
        progress = st.progress(0.0, text="Starting...")

        def _cb(done, total, elapsed):
            progress.progress(done / total, text=f"{done}/{total} ({elapsed:.0f}s elapsed)")

        df = sweep_ui.run_custom_sweep(sorted(aperture_choice), sorted(M_values), wavelength_nm,
                                        d_gap_mm, D_pupil_um, grid_N=512, progress_callback=_cb)
        progress.progress(1.0, text="Done.")
        st.session_state["custom_sweep_df"] = df
        n_fail = (~df["junction_check_passed"]).sum()
        st.success(f"Sweep complete: {len(df)} points" + (f", {n_fail} failed validation" if n_fail else ""))

    df = st.session_state.get("custom_sweep_df")
    if df is None:
        return

    st.subheader("Explore your sweep results")
    available_metrics = [c for c in sweep_ui.METRIC_LABELS if c in df.columns]
    metric_col = st.selectbox("Metric", available_metrics, format_func=lambda c: sweep_ui.METRIC_LABELS.get(c, c),
                               key="custom_sweep_metric")
    plot_type = st.radio("Plot type", ["Line (vs aperture, grouped by M)", "Heatmap", "Pareto front"],
                          horizontal=True, key="custom_sweep_plot_type")

    if plot_type == "Line (vs aperture, grouped by M)":
        st.pyplot(sweep_ui.plot_metric_vs_aperture_grouped(df, metric_col))
    elif plot_type == "Heatmap":
        st.pyplot(sweep_ui.plot_heatmap(df, metric_col))
    else:
        group_val = st.selectbox("M value", sorted(df["M_diopters"].unique()), key="custom_sweep_pareto_m")
        st.pyplot(sweep_ui.plot_pareto_front_ui(df, metric_col, "throughput_area_ratio", group_val))

    st.download_button("Download sweep results (CSV)", df.to_csv(index=False).encode(),
                        file_name="custom_sweep_results.csv")


def render():
    section = st.sidebar.radio("Sweep & Explore section",
                                ["Run New Sweep (live)", "Explore Precomputed Data", "Static Gallery",
                                 "Tables", "Literature (live)"])
    if section == "Run New Sweep (live)":
        _run_new_sweep()
    elif section == "Explore Precomputed Data":
        _interactive_explore()
    elif section == "Static Gallery":
        _static_gallery()
    elif section == "Tables":
        _tables()
    else:
        _literature()
