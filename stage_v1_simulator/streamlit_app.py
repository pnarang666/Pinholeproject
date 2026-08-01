"""
Stage v1 Simulator -- Streamlit app wrapping stage3_integrated's precomputed theory
dataset plus live single-point exploration and a blur-demonstration animation.

No "recommended aperture" output anywhere in this app -- exploration/demonstration
only. Every displayed number traces to an existing module's actual computation.

Run: streamlit run stage_v1_simulator/streamlit_app.py
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_logger
import eye_chart_blur as ecb
import eye_diagram
import light_acuity
import live_compute as lc
import theory_browser

_STAGE1_V2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage1_v2"))
if _STAGE1_V2_DIR not in sys.path:
    sys.path.insert(0, _STAGE1_V2_DIR)
import physics as v2_physics  # noqa: E402 -- radial_profile, for the radial plot only

st.set_page_config(page_title="Stage v1 Simulator -- Pinhole Sunglasses", page_icon="\U0001F441", layout="wide")

DISCRETE_APERTURES_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
STAGE3_INTEGRATED_OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage3_integrated", "outputs"))


@st.cache_data(show_spinner="Computing...")
def cached_compute(a_hole_um, wavelength_nm, M_diopters, d_gap_mm, D_pupil_um,
                    refractive_index_correction, grid_N, window_L_mm):
    result = lc.compute_point(a_hole_um, wavelength_nm, M_diopters, d_gap_mm, D_pupil_um,
                               refractive_index_correction=refractive_index_correction,
                               grid_N=grid_N, window_L_mm=window_L_mm)
    # I_retina (ndarray) can't be st.cache_data-hashed cleanly across reruns in all
    # versions, but IS picklable, so this is fine; kept explicit rather than silently
    # relying on default hashing behavior.
    return result


@st.cache_data(show_spinner=False)
def load_precomputed_r_ee50_curve():
    path = os.path.join(STAGE3_INTEGRATED_OUT, "combined_grid_550nm_12mm.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def sidebar_controls(key_prefix=""):
    a_hole_um = st.select_slider("Aperture diameter (µm)", options=DISCRETE_APERTURES_UM, value=400,
                                  key=f"{key_prefix}a_hole",
                                  help="Discrete values matching stage3_integrated's precomputed sweep, "
                                       "so live points compare directly against it.")
    wavelength_nm = st.slider("Wavelength (nm)", 400, 700, 550, step=5, key=f"{key_prefix}wl")
    P0 = st.number_input("Emmetropic eye power P0 (D)", value=60.0, key=f"{key_prefix}P0")
    M_diopters = st.slider("Myopia severity M (D)", 0.0, float(P0 - 1), 4.0, step=0.5, key=f"{key_prefix}M")
    guard = lc.myopia_guard(M_diopters, P0)
    if guard:
        st.warning(guard)
    d_gap_mm = st.slider("Pinhole-to-cornea gap (mm)", 5.0, 25.0, 12.0, step=0.5, key=f"{key_prefix}gap")
    D_pupil_um = st.number_input("Natural pupil diameter (µm)", value=4000.0, key=f"{key_prefix}pupil")
    refractive_index_correction = st.checkbox("Refractive-index correction (anatomical, n'=1.336)",
                                               value=True, key=f"{key_prefix}nprime")
    return dict(a_hole_um=a_hole_um, wavelength_nm=wavelength_nm, M_diopters=M_diopters,
                d_gap_mm=d_gap_mm, D_pupil_um=D_pupil_um,
                refractive_index_correction=refractive_index_correction, P0=P0)


def tab_live_explorer():
    st.sidebar.header("Live Explorer controls")
    params = sidebar_controls("live_")
    T_min_pct = st.sidebar.slider("Minimum acceptable relative illuminance, T_min (%)", 0.0, 25.0, 6.25, step=0.25)

    col_grid, col_btn = st.columns([2, 1])
    with col_grid:
        st.caption("Default interactive grid: **N=512** (fast preview, ~0.2-0.5s). "
                    "Use the button for a validated high-accuracy point.")
    with col_btn:
        high_accuracy = st.button("Compute at high accuracy (grid_N=2048, ~5s)")

    grid_N = 2048 if high_accuracy else 512
    result = cached_compute(params["a_hole_um"], params["wavelength_nm"], params["M_diopters"],
                             params["d_gap_mm"], params["D_pupil_um"],
                             params["refractive_index_correction"], grid_N, 6.0)

    st.markdown(f"**grid_N = {grid_N}** &nbsp;|&nbsp; **last compute time: {result['compute_time_s']:.3f}s** "
                f"&nbsp;|&nbsp; {'*(fast preview -- not validated resolution)*' if grid_N == 512 else '**(high-accuracy, validated resolution)**'}")

    if not result["junction_check_passed"]:
        st.error(f"Junction validation failed: {result['junction_fail_reason']}")
        return

    data_logger.log_point(st.session_state, result, "live_explorer")

    st.markdown("**Blur / encircled energy**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("r_EE(50%)", f"{result['r_EE_50_um']:.2f} µm")
    c2.metric("r_EE(70%)", f"{result['r_EE_70_um']:.2f} µm")
    c3.metric("r_EE(80%)", f"{result['r_EE_80_um']:.2f} µm")
    c4.metric("r_EE(90%)", f"{result['r_EE_90_um']:.2f} µm")
    c1b, c2b = st.columns(2)
    c1b.metric("RMS spot radius", f"{result['rms_spot_radius_um']:.2f} µm")
    c2b.metric("Airy diameter (diffraction limit)", f"{result['airy_diameter_um']:.2f} µm")

    st.markdown("**Optical quality**")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Strehl ratio", f"{result['strehl_ratio']:.3f}",
              help="Can exceed 1.0 in this system -- documented finding that Strehl "
                   "is ill-posed here (genuine Fresnel-regime oscillation, confirmed "
                   "not a sampling artifact). See stage3_integrated/README.md.")
    d2.metric("MTF50", f"{result['mtf50_cpd']:.2f} cpd")
    d3.metric("MTF10", f"{result['mtf10_cpd']:.2f} cpd")
    d4.metric("F-number", f"{result['f_number']:.1f}")

    st.markdown("**Photometry**")
    rel_ill_pct = result["relative_retinal_illuminance"] * 100
    color = "green" if rel_ill_pct >= T_min_pct else "red"
    e1, e2, e3 = st.columns(3)
    e1.markdown(f"Relative retinal illuminance<br><span style='color:{color}; font-size:1.5rem'>"
                f"{rel_ill_pct:.3f}%</span> (T_min={T_min_pct:.2f}%)", unsafe_allow_html=True)
    e2.metric("Retinal illuminance", f"{result['retinal_illuminance_troland']:.1f} Td")
    e3.metric("Photon flux density", f"{result['photon_flux_density_per_s_per_m2']:.2e} /s/m²")

    st.markdown("**Visual acuity predictions** (3 independent models -- not merged into one number)")
    f1, f2, f3 = st.columns(3)
    f1.metric("MTF50-cutoff", f"20/{result['snellen_denom_mtf50']:.0f}",
              help="Predicted Snellen denominator from the frequency where MTF drops to 50%.")
    f2.metric("MTF10-cutoff", f"20/{result['snellen_denom_mtf10']:.0f}",
              help="Predicted Snellen denominator from the frequency where MTF drops to 10% -- "
                   "closer to a detection-threshold criterion.")
    f3.metric("Rose-DeVries SNR bound", f"20/{result['rose_devries_snellen_denom']:.0f}",
              help="Photon-noise-limited acuity bound, relative to a fixed reference flux.")
    g1, g2 = st.columns(2)
    g1.metric("Visual Strehl, VSX-approx (photopic CSF)", f"{result['visual_strehl_photopic']:.3f}")
    g2.metric("Visual Strehl, VSX-approx (Mannos-Sakrison CSF)", f"{result['visual_strehl_mannos_sakrison']:.3f}")

    col_img, col_radial = st.columns(2)
    with col_img:
        I = result["I_retina"]
        dx = result["dx_m"]
        N = I.shape[0]
        extent_um = (N * dx / 2) * 1e6 * np.array([-1, 1, -1, 1])
        zoom_um = max(result["r_EE_90_um"] * 2.5, 50)
        fig, ax = plt.subplots(figsize=(5, 5))
        im = ax.imshow(I, extent=extent_um, cmap="inferno", origin="lower")
        ax.set_xlim(-zoom_um, zoom_um); ax.set_ylim(-zoom_um, zoom_um)
        ax.set_xlabel("x (µm)"); ax.set_ylabel("y (µm)")
        ax.set_title("Retinal intensity")
        plt.colorbar(im, ax=ax, fraction=0.046)
        st.pyplot(fig); plt.close(fig)

    with col_radial:
        r_centers, I_radial = v2_physics.radial_profile(I, None, dx)
        fig2, ax2 = plt.subplots(figsize=(5, 5))
        ax2.plot(r_centers * 1e6, I_radial, color="#2a78d6")
        ax2.set_xlim(0, zoom_um)
        for label, key, style in [("50%", "r_EE_50_um", ":"), ("70%", "r_EE_70_um", "-"),
                                   ("80%", "r_EE_80_um", "--"), ("90%", "r_EE_90_um", "-.")]:
            ax2.axvline(result[key], color="gray", linestyle=style, alpha=0.7, label=f"r_EE({label})")
        ax2.set_xlabel("radius (µm)"); ax2.set_ylabel("intensity")
        ax2.set_title("Radial profile"); ax2.legend(fontsize=8)
        st.pyplot(fig2); plt.close(fig2)

    st.subheader("MTF vs. contrast sensitivity function (this point)")
    import contrast as _contrast
    f_cpd = result["mtf_freq_cpd"]
    mtf_vals = result["mtf_values"]
    mask = (f_cpd > 0) & (f_cpd <= 40)
    fig_mtf, ax_mtf = plt.subplots(figsize=(9, 4))
    ax_mtf.plot(f_cpd[mask], mtf_vals[mask], color="#2a78d6", label="MTF (this point)")
    f_ref = np.linspace(0.5, 40, 200)
    ax_mtf.plot(f_ref, _contrast.csf_photopic_peak(f_ref) / _contrast.csf_photopic_peak(f_ref).max(),
                color="#1baf7a", linestyle="--", label="CSF, photopic (normalized, peak~4cpd)")
    ax_mtf.plot(f_ref, _contrast.csf_mannos_sakrison(f_ref) / _contrast.csf_mannos_sakrison(f_ref).max(),
                color="#eda100", linestyle="--", label="CSF, Mannos-Sakrison (normalized, peak~8cpd)")
    ax_mtf.set_xlabel("spatial frequency (cycles/degree)"); ax_mtf.set_ylabel("normalized value")
    ax_mtf.legend(fontsize=8); ax_mtf.grid(alpha=0.3)
    st.pyplot(fig_mtf); plt.close(fig_mtf)

    st.subheader("Precomputed r_EE(50/70/80/90%) vs aperture, with live point overlaid")
    st.caption("r_EE(50%) alone can understate blur -- it ignores the energy sitting in "
               "the Fresnel rings outside the core. Shown together with 70/80/90% so no "
               "single percentile is presented as *the* answer.")
    precomputed = load_precomputed_r_ee50_curve()
    if precomputed is not None:
        g = precomputed[np.isclose(precomputed["M_diopters"], round(params["M_diopters"]))].sort_values("a_hole_um")
        if len(g):
            fig3, ax3 = plt.subplots(figsize=(9, 4.5))
            for pct, col, color in [(50, "r_EE_50_um", "#2a78d6"), (70, "r_EE_70_um", "#1baf7a"),
                                     (80, "r_EE_80_um", "#eda100"), (90, "r_EE_90_um", "#4a3aa7")]:
                if col in g.columns:
                    ax3.plot(g["a_hole_um"], g[col], "o-", color=color, markersize=4,
                             label=f"r_EE({pct}%) precomputed")
                if col in result:
                    ax3.plot(params["a_hole_um"], result[col], "*", color=color, markersize=18,
                             markeredgecolor="black")
            ax3.plot([], [], "*", color="gray", markersize=14, markeredgecolor="black",
                     label=f"live point, all percentiles (grid_N={grid_N})")
            ax3.set_xlabel("aperture (µm)"); ax3.set_ylabel("blur radius (µm)")
            ax3.set_title(f"M={round(params['M_diopters'])}D, 550nm/12mm (precomputed slice)")
            ax3.legend(fontsize=8, ncol=2); ax3.grid(alpha=0.3)
            st.pyplot(fig3); plt.close(fig3)
        else:
            st.info("No precomputed curve at this exact integer M -- precomputed grid uses M in {1,2,3,4,5,6,8}.")
    else:
        st.info("Precomputed curve not found -- run stage3_integrated/combine_metrics.py first.")

    st.subheader("Schematic eye diagram")
    fig4 = eye_diagram.draw_eye_diagram(params["a_hole_um"], params["d_gap_mm"], result["L0_mm"],
                                         result["v_r_m"] * 1e3, result["f_eye_mm"], params["M_diopters"])
    st.pyplot(fig4); plt.close(fig4)


def tab_blur_demonstration():
    st.sidebar.header("Blur Demonstration controls")
    params = sidebar_controls("blur_")
    st.caption("Synthetic **tumbling-E chart** (NOT a clinically calibrated optotype -- "
               "a qualitative demonstration only). Convolved with the normalized "
               "(unit-volume) retinal PSF.")

    chart_um_per_px = st.slider("Chart scale (µm per chart pixel)", 2.0, 50.0, 15.0, step=1.0)
    chart, _ = ecb.make_tumbling_e_chart(size_px=256, n_rows=6, um_per_px=chart_um_per_px)

    mode = st.radio("Mode", ["Single point (toggle before/after)", "Animate across aperture range"], horizontal=True)

    if mode == "Single point (toggle before/after)":
        result = cached_compute(params["a_hole_um"], params["wavelength_nm"], params["M_diopters"],
                                 params["d_gap_mm"], params["D_pupil_um"],
                                 params["refractive_index_correction"], 512, 6.0)
        if not result["junction_check_passed"]:
            st.error(f"Junction validation failed: {result['junction_fail_reason']}")
            return
        data_logger.log_point(st.session_state, result, "blur_demo")

        blurred, info = ecb.convolve_chart_with_psf(chart, result["I_retina"], chart_um_per_px, result["dx_m"])
        st.caption(f"Conversion: {info['chart_um_per_px']:.1f} um/chart-px, "
                   f"{info['retina_um_per_px']:.3f} um/retina-px, zoom factor={info['zoom_factor']:.3f}")

        view = st.radio("View", ["Before", "After", "Side by side"], horizontal=True)
        if view == "Side by side":
            c1, c2 = st.columns(2)
            c1.image(chart, caption="Original chart", clamp=True, use_column_width=True)
            c2.image(blurred / blurred.max() if blurred.max() > 0 else blurred,
                      caption="Blurred (through this pinhole/eye)", clamp=True, use_column_width=True)
        elif view == "Before":
            st.image(chart, caption="Original chart", clamp=True, use_column_width=True)
        else:
            st.image(blurred / blurred.max() if blurred.max() > 0 else blurred,
                      caption="Blurred (through this pinhole/eye)", clamp=True, use_column_width=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("r_EE(50%)", f"{result['r_EE_50_um']:.2f} µm")
        c2.metric("r_EE(70%)", f"{result['r_EE_70_um']:.2f} µm")
        c3.metric("r_EE(80%)", f"{result['r_EE_80_um']:.2f} µm")
        c4.metric("Relative illuminance", f"{result['relative_retinal_illuminance']*100:.3f}%")

    else:
        if st.button("Precompute all frames and play"):
            frames, r_ee50s, r_ee70s, r_ee80s, rel_ills = [], [], [], [], []
            progress = st.progress(0.0, text="Precomputing frames...")
            for i, a_um in enumerate(DISCRETE_APERTURES_UM):
                result = cached_compute(a_um, params["wavelength_nm"], params["M_diopters"],
                                         params["d_gap_mm"], params["D_pupil_um"],
                                         params["refractive_index_correction"], 512, 6.0)
                if result["junction_check_passed"]:
                    blurred, _ = ecb.convolve_chart_with_psf(chart, result["I_retina"], chart_um_per_px, result["dx_m"])
                    frames.append(blurred / blurred.max() if blurred.max() > 0 else blurred)
                    r_ee50s.append(result["r_EE_50_um"]); r_ee70s.append(result["r_EE_70_um"])
                    r_ee80s.append(result["r_EE_80_um"]); rel_ills.append(result["relative_retinal_illuminance"])
                else:
                    frames.append(chart); r_ee50s.append(np.nan); r_ee70s.append(np.nan)
                    r_ee80s.append(np.nan); rel_ills.append(np.nan)
                progress.progress((i + 1) / len(DISCRETE_APERTURES_UM))
            st.session_state["anim_frames"] = frames
            st.session_state["anim_r_ee50"] = r_ee50s
            st.session_state["anim_r_ee70"] = r_ee70s
            st.session_state["anim_r_ee80"] = r_ee80s
            st.session_state["anim_rel_ill"] = rel_ills
            st.success(f"Precomputed {len(frames)} frames -- use the scrubber below.")

        if "anim_frames" in st.session_state:
            idx = st.slider("Frame (aperture index)", 0, len(DISCRETE_APERTURES_UM) - 1, 0,
                             format="", key="anim_scrubber")
            a_um = DISCRETE_APERTURES_UM[idx]
            st.image(st.session_state["anim_frames"][idx], caption=f"a_hole={a_um}um", clamp=True, width=400)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("r_EE(50%)", f"{st.session_state['anim_r_ee50'][idx]:.2f} µm")
            c2.metric("r_EE(70%)", f"{st.session_state['anim_r_ee70'][idx]:.2f} µm")
            c3.metric("r_EE(80%)", f"{st.session_state['anim_r_ee80'][idx]:.2f} µm")
            c4.metric("Relative illuminance", f"{st.session_state['anim_rel_ill'][idx]*100:.3f}%")


def tab_theory_browser():
    theory_browser.render()


def tab_light_and_acuity():
    params = sidebar_controls("light_")
    light_acuity.render(params)


def tab_session_log():
    st.subheader("Session Log -- every live-computed point this session")
    df = data_logger.get_log_df(st.session_state)
    st.dataframe(df, use_container_width=True)
    if len(df):
        st.download_button("Export session log (CSV)", data_logger.export_csv_bytes(st.session_state),
                            file_name="session_log.csv", mime="text/csv")
    else:
        st.info("No points computed yet this session -- use Live Explorer or Blur Demonstration.")


def main():
    st.title("Stage v1 Simulator -- Pinhole Sunglasses")
    st.caption("Exploration and demonstration only -- this app never outputs a "
               "'recommended aperture'. For the full theoretical comparison, precomputed "
               "data, and live custom sweeps, see the Sweep & Explore tab.")

    tabs = st.tabs(["Live Explorer", "Blur Demonstration", "Sweep & Explore", "Light & Acuity", "Session Log"])
    with tabs[0]:
        tab_live_explorer()
    with tabs[1]:
        tab_blur_demonstration()
    with tabs[2]:
        tab_theory_browser()
    with tabs[3]:
        tab_light_and_acuity()
    with tabs[4]:
        tab_session_log()


if __name__ == "__main__":
    main()
