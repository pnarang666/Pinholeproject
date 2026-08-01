"""
Corneal Fresnel Field Analyzer -- Stage 1 interactive instrument.

Plane wave -> circular pinhole -> exact scalar Angular Spectrum Method -> corneal plane.
Deliberately stops there: no eye lens, vitreous, retina, or image-formation model, and no
"best pinhole" estimate -- this only characterizes the field arriving at the cornea.

Run:
    streamlit run stage1/app.py
"""

import io
import os
import shutil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

import physics
import plotting
import sweep

st.set_page_config(page_title="Stage 1 -- Corneal Fresnel Field Analyzer",
                    page_icon="\U0001F52C", layout="wide")

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs", "stage1"))
os.makedirs(OUT_DIR, exist_ok=True)

RADIUS_DEF_KEYS = list(physics.EFFECTIVE_RADIUS_LABELS.keys())
REGIME_COLORS = {"Fraunhofer": "#2a78d6", "Transition": "#1baf7a", "Strong Fresnel": "#4a3aa7"}

st.markdown("""
<style>
.readout { font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.92rem; }
.regime-badge { display:inline-block; padding: 3px 12px; border-radius: 4px; font-weight:600;
                font-family: "SFMono-Regular", Consolas, monospace; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Propagating field (exact ASM)...")
def compute_result(a_hole, wavelength, z, N, L, band_limit):
    cfg = physics.RunConfig(a_hole=a_hole, wavelength=wavelength, z=z, N=N, L=L, band_limit=band_limit)
    return physics.run_configuration(cfg)


@st.cache_data(show_spinner="Running grid-convergence check (2x N)...")
def convergence_check(a_hole, wavelength, z, N_ref, L, band_limit, radius_def, ee_percent, threshold_percent):
    N_fine = N_ref * 2
    r_ref = physics.effective_radius(compute_result(a_hole, wavelength, z, N_ref, L, band_limit),
                                      radius_def, ee_percent=ee_percent, threshold_percent=threshold_percent)
    r_fine = physics.effective_radius(compute_result(a_hole, wavelength, z, N_fine, L, band_limit),
                                       radius_def, ee_percent=ee_percent, threshold_percent=threshold_percent)
    rel_err = abs(r_fine - r_ref) / r_fine if r_fine else float("nan")
    return N_fine, r_ref, r_fine, rel_err


def npy_bytes(arr):
    buf = io.BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


def sidebar_controls():
    st.sidebar.header("Pinhole -> Cornea (Stage 1)")
    st.sidebar.caption("Plane wave -> circular pinhole -> exact ASM -> corneal plane. "
                        "Stops at the cornea; no lens, vitreous, retina, or image formation.")

    st.sidebar.subheader("Aperture & propagation")
    a_hole_um = st.sidebar.slider("Aperture diameter (µm)", 50, 2000, 428, step=2)
    wavelength_nm = st.sidebar.slider("Wavelength (nm)", 400, 700, 550, step=5)
    z_gap_mm = st.sidebar.slider("Propagation distance to cornea (mm)", 1.0, 40.0, 12.0, step=0.5)

    st.sidebar.subheader("Grid / numerics")
    N = st.sidebar.selectbox("Grid size N", [256, 512, 1024, 2048, 4096], index=2)
    L_mm = st.sidebar.number_input("Simulation window L (mm)", min_value=1.0, max_value=40.0,
                                    value=6.0, step=0.5)
    band_limit = st.sidebar.checkbox("Apply Matsushima anti-aliasing band-limit", value=True,
                                      help="Suppresses angular-spectrum orders that would alias against "
                                           "the frequency grid. Still the exact scalar ASM kernel -- this "
                                           "only removes a sampling artifact, not a physics approximation.")

    st.sidebar.subheader("Effective radius reporting")
    ee_percent = st.sidebar.slider("Encircled-energy percentage P (%)", 1, 99, 80)
    threshold_percent = st.sidebar.slider("Custom intensity threshold (% of peak)", 1, 99, 10)
    radius_defs = st.sidebar.multiselect(
        "Radius definitions to display",
        options=RADIUS_DEF_KEYS,
        default=["EE", "second_moment"],
        format_func=lambda k: physics.EFFECTIVE_RADIUS_LABELS[k],
    )

    return dict(a_hole=a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9, z=z_gap_mm * 1e-3,
                N=N, L=L_mm * 1e-3, band_limit=band_limit, ee_percent=float(ee_percent),
                threshold_percent=float(threshold_percent), radius_defs=radius_defs)


MODE_CAPTIONS = {
    "local_min_above_threshold": "Lower bound -- the central lobe turns back up into the "
                                  "next Fresnel ring before ever reaching this level.",
    "never_crossed": "Lower bound -- never reaches this level within the simulation window.",
}


def compute_effective_radii(result, radius_defs, ee_percent, threshold_percent):
    """Returns {label: {"radius": m, "mode": str|None}}. mode is None for EE/second-moment/
    equivalent-area, which have no crossing ambiguity to flag."""
    radii = {}
    for d in radius_defs:
        label = physics.EFFECTIVE_RADIUS_LABELS[d]
        detail = physics.effective_radius_detail(result, d, ee_percent=ee_percent,
                                                   threshold_percent=threshold_percent)
        mode = detail.get("mode")
        radii[label] = {"radius": detail["radius"], "mode": mode if mode != "n/a" else None}
    return radii


def render_regime_badge(result):
    color = REGIME_COLORS[result["regime"]]
    st.markdown(
        f"<span class='regime-badge' style='background:{color}22;color:{color};border:1px solid {color};'>"
        f"N_F = {result['N_F']:.2f} -- {result['regime']}</span>",
        unsafe_allow_html=True,
    )


def render_validation(result):
    for check in result["validation"]:
        if check["ok"]:
            st.success(f"**{check['name']}**: {check['detail']}", icon="✅")
        else:
            st.warning(f"**{check['name']}**: {check['detail']}", icon="⚠️")


def single_run_tab(params):
    result = compute_result(params["a_hole"], params["wavelength"], params["z"],
                             params["N"], params["L"], params["band_limit"])
    radii = compute_effective_radii(result, params["radius_defs"], params["ee_percent"], params["threshold_percent"])

    render_regime_badge(result)
    cols = st.columns(4)
    cols[0].metric("Energy conservation err.", f"{result['energy_conservation_error']:.2e}")
    cols[1].metric("Peak intensity", f"{result['I_peak']:.3f}")
    cols[2].metric("On-axis intensity", f"{result['I_onaxis']:.3f}")
    cols[3].metric("Total energy", f"{result['total_power']:.3e}")

    plot_radii = {}
    if radii:
        st.markdown("**Effective corneal illumination radius**")
        rcols = st.columns(len(radii))
        for c, (label, info) in zip(rcols, radii.items()):
            r_um = info["radius"] * 1e6
            is_lower_bound = info["mode"] in MODE_CAPTIONS
            prefix = "≥ " if is_lower_bound else ""
            c.metric(label, f"{prefix}{r_um:.2f} µm")
            if is_lower_bound:
                c.caption(MODE_CAPTIONS[info["mode"]])
            plot_radii[prefix + label] = info["radius"]

    fig = plotting.fig_single_run(result, effective_radii=plot_radii, target_P=params["ee_percent"])
    st.pyplot(fig)

    with st.expander("Validation & diagnostics", expanded=False):
        render_validation(result)
        if st.button("Run grid-convergence check (2x N, slower)"):
            primary_def = params["radius_defs"][0] if params["radius_defs"] else "EE"
            N_fine, r_ref, r_fine, rel_err = convergence_check(
                params["a_hole"], params["wavelength"], params["z"], params["N"], params["L"],
                params["band_limit"], primary_def, params["ee_percent"], params["threshold_percent"])
            label = physics.EFFECTIVE_RADIUS_LABELS[primary_def]
            msg = (f"{label}: N={params['N']} -> {r_ref * 1e6:.3f} µm; "
                   f"N={N_fine} -> {r_fine * 1e6:.3f} µm; relative change = {rel_err * 100:.3f}%")
            if rel_err < 0.01:
                st.success(msg, icon="✅")
            else:
                st.warning(msg + " -- consider a finer production grid.", icon="⚠️")

    st.markdown("**Export**")
    ex_cols = st.columns(5)
    cfg = result["cfg"]
    tag = f"a{cfg.a_hole * 1e6:.0f}um_z{cfg.z * 1e3:.1f}mm_wl{cfg.wavelength * 1e9:.0f}nm_N{cfg.N}"
    row = sweep.build_csv_row(result, params["ee_percent"], params["threshold_percent"])
    csv_bytes = pd.DataFrame([row]).to_csv(index=False).encode()
    ex_cols[0].download_button("summary.csv", csv_bytes, file_name=f"summary_{tag}.csv", mime="text/csv")
    ex_cols[1].download_button("Intensity.npy", npy_bytes(result["I"]), file_name=f"Intensity_{tag}.npy")
    ex_cols[2].download_button("Phase.npy", npy_bytes(result["phase"]), file_name=f"Phase_{tag}.npy")
    ex_cols[3].download_button("Field.npy", npy_bytes(result["Uz"]), file_name=f"Field_{tag}.npy")
    fig_buf = io.BytesIO()
    fig.savefig(fig_buf, format="png", dpi=300, bbox_inches="tight")
    ex_cols[4].download_button("figure.png (300dpi)", fig_buf.getvalue(),
                                file_name=f"figure_{tag}.png", mime="image/png")
    plt.close(fig)

    st.markdown("---")
    run_label = st.text_input("Label for this run (used in Compare tab)", value=tag, key="run_label_input")
    if st.button("Add this run to Compare"):
        st.session_state.setdefault("comparison_runs", [])
        st.session_state["comparison_runs"].append({
            "label": run_label, "result": result,
            "row": sweep.build_csv_row(result, params["ee_percent"], params["threshold_percent"]),
        })
        st.success(f"Added '{run_label}' to comparison ({len(st.session_state['comparison_runs'])} runs stored).")


def compare_tab(params):
    runs = st.session_state.get("comparison_runs", [])
    if not runs:
        st.info("No runs added yet. Use 'Add this run to Compare' on the Single Run tab.")
        return

    st.write(f"{len(runs)} run(s) in comparison.")
    df = pd.DataFrame([r["row"] for r in runs])
    st.dataframe(df, use_container_width=True)

    labels = [r["label"] for r in runs]
    results = [r["result"] for r in runs]

    c1, c2 = st.columns(2)
    with c1:
        fig1 = plotting.fig_compare_radial(results, labels)
        st.pyplot(fig1)
        plt.close(fig1)
    with c2:
        fig2 = plotting.fig_compare_ee(results, labels)
        st.pyplot(fig2)
        plt.close(fig2)

    radius_cols = [c for c in df.columns if "radius_um" in c or "r_EE" in c]
    radius_col = st.selectbox("Bar-chart metric", radius_cols)
    fig3 = plotting.fig_compare_bar(labels, df[radius_col].tolist(), radius_col)
    st.pyplot(fig3)
    plt.close(fig3)

    st.download_button("Download comparison table (CSV)", df.to_csv(index=False).encode(),
                        file_name="comparison_runs.csv", mime="text/csv")

    if st.button("Clear comparison"):
        st.session_state["comparison_runs"] = []
        st.experimental_rerun()


def sweep_tab(params):
    st.subheader("Sweep ranges")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Aperture diameter (µm)**")
        d_start = st.number_input("start", value=200.0, key="d_start")
        d_stop = st.number_input("stop", value=1000.0, key="d_stop")
        d_step = st.number_input("step", value=25.0, key="d_step")
    with c2:
        st.markdown("**Propagation distance z (mm)**")
        z_start = st.number_input("start", value=5.0, key="z_start")
        z_stop = st.number_input("stop", value=25.0, key="z_stop")
        z_step = st.number_input("step", value=0.5, key="z_step")
    with c3:
        st.markdown("**Wavelengths (nm, comma-separated)**")
        wl_text = st.text_input("values", value="450,550,650", key="wl_text")

    diam_values = [v * 1e-6 for v in sweep.range_values(d_start, d_stop, d_step)]
    gap_values = [v * 1e-3 for v in sweep.range_values(z_start, z_stop, z_step)]
    wavelength_values = sweep.parse_wavelength_list(wl_text)

    n_configs = len(diam_values) * len(gap_values) * len(wavelength_values)
    est = sweep.estimate_sweep(n_configs, params["N"])
    st.caption(f"{n_configs} configurations -- rough estimate: "
               f"{est['est_seconds']:.0f} s compute, "
               f"{est['bytes_per_field_set'] / 1e6:.1f} MB per saved field set.")

    save_fields = st.checkbox("Save Intensity/Phase/Field .npy for every sweep point", value=False)
    if save_fields:
        total_gb = est["est_bytes_if_saving_all_fields"] / 1e9
        st.warning(f"This would write ~{total_gb:.2f} GB to disk across {n_configs} configurations. "
                   f"Leave unchecked to export the summary CSV only (recommended for large sweeps).")

    if st.button("Run sweep", type="primary"):
        if n_configs > 5000:
            st.error(f"{n_configs} configurations is too large for an interactive run here -- narrow the ranges.")
            return
        progress = st.progress(0.0, text="Starting sweep...")

        def cb(done, total, cfg):
            progress.progress(done / total, text=f"{done}/{total}: "
                               f"a_hole={cfg.a_hole * 1e6:.0f}um z={cfg.z * 1e3:.1f}mm "
                               f"wl={cfg.wavelength * 1e9:.0f}nm")

        fields_dir = os.path.join(OUT_DIR, "sweep_fields") if save_fields else None
        if fields_dir:
            os.makedirs(fields_dir, exist_ok=True)
        df, saved_dirs = sweep.run_sweep(
            diam_values, gap_values, wavelength_values, params["N"], params["L"],
            ee_percent=params["ee_percent"], threshold_percent=params["threshold_percent"],
            band_limit=params["band_limit"], progress_cb=cb,
            save_fields=save_fields, fields_dir=fields_dir)
        progress.progress(1.0, text="Done.")
        st.session_state["sweep_df"] = df
        st.session_state["sweep_fields_dir"] = fields_dir
        st.success(f"Sweep complete: {len(df)} configurations.")

    df = st.session_state.get("sweep_df")
    if df is None:
        return

    st.dataframe(df, use_container_width=True)
    st.download_button("Download sweep summary.csv", df.to_csv(index=False).encode(),
                        file_name="sweep_summary.csv", mime="text/csv")

    fields_dir = st.session_state.get("sweep_fields_dir")
    if fields_dir and os.path.isdir(fields_dir):
        zip_path_base = os.path.join(OUT_DIR, "sweep_fields_export")
        if st.button("Package saved fields as .zip"):
            archive = shutil.make_archive(zip_path_base, "zip", fields_dir)
            with open(archive, "rb") as f:
                st.download_button("Download fields.zip", f.read(), file_name="sweep_fields.zip",
                                    mime="application/zip")

    st.subheader("Sweep visualisation")
    radius_cols = [c for c in df.columns if "radius_um" in c or "r_EE" in c]
    radius_col = st.selectbox("Radius metric", radius_cols, key="sweep_radius_col")
    wl_options = sorted(df["wavelength_nm"].unique())
    wl_pick = st.selectbox("Wavelength (nm)", wl_options, key="sweep_wl_pick")

    v1, v2 = st.columns(2)
    with v1:
        figv1 = plotting.fig_radius_vs_z(df, radius_col, wl_pick)
        st.pyplot(figv1)
        plt.close(figv1)
    with v2:
        figv2 = plotting.fig_radius_vs_diameter(df, radius_col, wl_pick)
        st.pyplot(figv2)
        plt.close(figv2)
    figv3 = plotting.fig_heatmap(df, radius_col, wl_pick)
    st.pyplot(figv3)
    plt.close(figv3)


HELP_TEXT = """
### What Stage 1 is

```
Plane Wave / Object
        |
Circular Pinhole
        |
Exact Angular Spectrum Method
        |
Corneal Plane
```

This tool characterizes the field arriving at the cornea. It does **not** estimate
the "best" pinhole, and it does **not** model the eye lens, vitreous, retina, or image
formation -- that is a separate, later stage that would consume the complex field
`U(x, y, z)` this tool produces.

### Physics

Propagation uses the **exact scalar Angular Spectrum Method** -- no Fraunhofer
approximation, no paraxial Fresnel approximation, no FFT shortcut substituted for the
real kernel. The transfer function's evanescent orders are zeroed exactly; propagating
orders beyond the Matsushima band limit are optionally suppressed to remove a sampling
artifact (toggle in the sidebar), not to change the physical model.

**Fresnel number** `N_F = a^2 / (λ z)`, with `a` the aperture radius:

| N_F | Regime |
|---|---|
| < 0.1 | Fraunhofer |
| 0.1 -- 10 | Transition |
| > 10 | Strong Fresnel |

A typical pinhole-sunglasses geometry sits at N_F ≈ 1-50, i.e. Transition to Strong
Fresnel -- this tool is built to stay in that regime.

### Effective corneal illumination radius -- definitions

- **r_EE(P)**: radius enclosing P% of total power (P is yours to choose -- never
  hardcoded to 50/80/90).
- **Second-moment radius**: `sqrt(sum(I r²) / sum(I))`.
- **FWHM radius**: half-max crossing, walking outward from the radial profile's peak and
  stopping at whichever comes first -- the crossing, or the central lobe turning back up
  into the next Fresnel ring. A value marked "≥ ... lower bound" means the lobe never
  reached half its peak before turning back up; the true FWHM is at least that number.
- **1/e² radius**: same method at 1/e² (≈13.5%) of the peak.
- **Custom threshold radius**: same method at any peak fraction you choose.
- **Equivalent-area radius**: radius of a uniform disk with the same peak intensity
  that would carry the same total power, `sqrt(P_total / (π I_peak))`.

The term "effective aperture" is avoided deliberately -- it already has established
meanings elsewhere in optics. Every number here is labeled with its definition.

**Why "outward from the peak, stop at the first turning point" and not "first sample
below threshold"**: once two Fresnel rings sit close in brightness (routine once N_F is
O(1)-O(10)), a fixed intensity threshold is crossed multiple times as radius increases.
Reporting the *first* crossing lets the reported width hop between rings on a sub-1%
change in aperture diameter or gap -- confirmed to jump >20 µm in this tool's own test
sweeps. Restricting the search to the segment between the peak and its first genuine
local minimum (confirmed by a real, prominent rise afterward, not sampling noise) keeps
the number locked to one physical feature and continuous as parameters sweep smoothly.
The one discontinuity this cannot and should not smooth over is the profile's global
peak itself relocating from the central spot to an outer ring -- a real physical
hot-spot/hot-ring transition, flagged separately by the central-peak validation check
below, not an artifact of this measurement.

The radial profile itself is sampled by interpolation along angular rays at the native
pixel spacing, not by histogram-binning the 2D grid -- a histogram bin average over the
first annulus understates a sharp on-axis peak (confirmed ~2.5x low at one tested
configuration), which would then bias every peak-referenced radius above outward. Only
encircled energy (a cumulative power integral, not a peak-referenced local measurement)
still uses histogram binning, which is the natural and correct tool for a running sum.

### Validation

Every run is checked for energy conservation, window size / wraparound risk, aperture
sampling (Nyquist across the aperture edge), angular-spectrum band-limit violations,
whether the profile's peak sits on-axis (needed for FWHM/1/e²/threshold to mean what
they usually mean), and whether the FWHM crossing was clean or is a lower bound. Grid
convergence is available on demand from the Single Run tab since it costs a second,
finer-grid propagation.
"""


def help_tab():
    st.markdown(HELP_TEXT)


def main():
    params = sidebar_controls()
    st.title("Corneal Fresnel Field Analyzer -- Stage 1")
    st.caption("Plane wave -> circular pinhole -> exact Angular Spectrum Method -> corneal plane. "
               "No lens, retina, or image-quality estimate here by design.")

    tabs = st.tabs(["Single Run", "Compare Runs", "Parameter Sweep", "Diagnostics & Help"])
    with tabs[0]:
        single_run_tab(params)
    with tabs[1]:
        compare_tab(params)
    with tabs[2]:
        sweep_tab(params)
    with tabs[3]:
        help_tab()


if __name__ == "__main__":
    main()
