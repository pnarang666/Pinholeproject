"""
Master interactive dashboard -- runs live sweeps across every registered stage of the
pinhole-sunglasses project (see registry.py for the stage list and README.md for how
to add a 12th). Run with:

    python3 -m streamlit run master_dashboard/app.py

(the `streamlit` console script is not on PATH in every environment this project has
been run in -- confirmed in this one: `which streamlit` finds nothing even though
`python3 -c "import streamlit"` works fine, because the script that provides the bare
`streamlit` command lives in a directory PATH doesn't include. `python3 -m streamlit`
sidesteps that entirely. If `which streamlit` finds something in yours, the plain
`streamlit run master_dashboard/app.py` works too -- see README.md.)

Every stage is registered in registry.REGISTRY; this file contains NO stage-specific
physics, sweep loops, or plotting math -- only generic UI plumbing (widgets, caching,
progress, plot-type dispatch) that reads its behavior from that registry.
"""
import os
import sys
import time

import pandas as pd
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry  # noqa: E402
import wrappers as w  # noqa: E402

ROOT = w.ROOT
RUNTIME_CONFIRM_THRESHOLD_S = 30.0

st.set_page_config(page_title="Master Dashboard -- Pinhole Sunglasses Project",
                    page_icon="\U0001F52C", layout="wide")

# --- palette (dataviz skill references/palette.md, documented values only) ---
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID_COLOR = "#e1e0d9"
BASELINE = "#c3c2b7"
CATEGORICAL_1 = "#2a78d6"
CATEGORICAL_2 = "#eb6834"
REGIME_COLORS = {"A": "#008300", "B": "#eda100", "C": "#e34948", None: "#898781"}
SEQ_BLUE_STOPS = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#184f95", "#0d366b"]
SEQ_CMAP = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE_STOPS, N=256)

plt.rcParams.update({
    "font.family": "sans-serif", "axes.edgecolor": BASELINE, "axes.labelcolor": INK_PRIMARY,
    "text.color": INK_PRIMARY, "xtick.color": INK_SECONDARY, "ytick.color": INK_SECONDARY,
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "grid.color": GRID_COLOR, "grid.linewidth": 0.8, "axes.grid": True, "axes.axisbelow": True,
})


# =============================================================================
# Project Physics Status -- always visible, computed live, never a hardcoded string
# =============================================================================

def render_physics_status():
    st.markdown("### \U0001F9EA Project Physics Status")
    cols = st.columns([2, 3])

    with cols[0]:
        # Force an import right now so the check is never "nothing loaded yet".
        try:
            _ensure_phase2_retina_loaded()
            path, is_correct = w.verify_phase2_retina_source()
        except Exception as e:  # noqa: BLE001 -- surface any import failure plainly
            path, is_correct = f"IMPORT FAILED: {e}", False

        if is_correct:
            st.success(f"`phase2_retina` loaded from **stage2_fixed/** ✓")
        else:
            st.error(f"`phase2_retina` NOT resolving to stage2_fixed/ -- regression!")
        st.caption(f"Live path: `{path}`")

    with cols[1]:
        corrected, superseded = _read_optimum_ranges()
        if corrected and superseded:
            st.info(
                f"**Blur-only optimum (r_EE 50%), computed live from output files:** "
                f"corrected = **{corrected[0]:.0f}–{corrected[1]:.0f}µm** "
                f"(`new_sweeps/blur_sweep.csv`) vs. superseded pre-fix = "
                f"**{superseded[0]:.0f}–{superseded[1]:.0f}µm** "
                f"(`stage2_fixed/outputs/prefix_baseline_audit/`)."
            )
        else:
            st.warning("Could not read one or both baseline CSVs for the optimum-range "
                       "comparison (see caption below) -- not silently hidden.")
            if not corrected:
                st.caption("Missing: new_sweeps/blur_sweep.csv")
            if not superseded:
                st.caption("Missing: stage2_fixed/outputs/prefix_baseline_audit/multi_EE_sweep.csv")
    st.markdown("---")


def _ensure_phase2_retina_loaded():
    p = os.path.join(ROOT, "stage2_fixed")
    if p not in sys.path:
        sys.path.insert(0, p)
    import phase2_retina  # noqa: F401


@st.cache_data(show_spinner=False)
def _read_optimum_ranges():
    """Reads the FRESH (post-fix) and PRE-FIX baseline blur sweeps directly from disk
    and computes each one's own per-M optimum-aperture range -- live, not hardcoded,
    so it can never silently go stale the way PROJECT_STATUS.md's own prose can."""
    def optimum_range(path, m_col="M_diopters", a_col="a_hole_um", y_col="r_EE_50_um"):
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        opts = []
        for M in sorted(df[m_col].unique()):
            g = df[df[m_col] == M]
            if g[y_col].isna().all():
                continue
            opts.append(g.loc[g[y_col].idxmin(), a_col])
        return (min(opts), max(opts)) if opts else None

    corrected = optimum_range(os.path.join(ROOT, "new_sweeps", "blur_sweep.csv"))
    superseded = optimum_range(os.path.join(
        ROOT, "stage2_fixed", "outputs", "prefix_baseline_audit", "multi_EE_sweep.csv"))
    return corrected, superseded


# =============================================================================
# Parameter widgets, generated from registry.py -- no per-stage UI code
# =============================================================================

def render_param_widgets(stage_key, entry):
    params = {}
    for key, spec in entry["params"].items():
        label = spec.get("label", key)
        widget_key = f"{stage_key}__{key}"
        if spec["kind"] == "multiselect":
            params[key] = st.sidebar.multiselect(
                label, options=spec["options"], default=spec["default"], key=widget_key)
            if not params[key]:
                params[key] = spec["default"]
        elif spec["kind"] == "slider":
            params[key] = st.sidebar.slider(
                label, min_value=spec["min"], max_value=spec["max"], step=spec["step"],
                value=spec["default"], key=widget_key)
        elif spec["kind"] == "select":
            params[key] = st.sidebar.selectbox(
                label, options=spec["options"],
                index=spec["options"].index(spec["default"]), key=widget_key)
    return params


def _cache_key(stage_key, params):
    parts = [stage_key]
    for k in sorted(params):
        v = params[k]
        v = tuple(v) if isinstance(v, list) else v
        parts.append((k, v))
    return tuple(parts)


# =============================================================================
# Plot dispatch -- reuses the same sequential-M-colormap convention as
# new_sweeps/generate_plots.py (dataviz skill: M is a continuous ordered magnitude,
# encoded sequentially with a colorbar, not as discrete categorical swatches)
# =============================================================================

def _style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.grid(True, which="major", linewidth=0.8, color=GRID_COLOR)


def plot_line_vs_aperture(df, y_col, color_by, x_col="a_hole_um"):
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
    if x_col not in df.columns or y_col not in df.columns:
        st.warning(f"Column `{y_col}` or `{x_col}` not in results.")
        return fig
    if color_by and color_by in df.columns and df[color_by].nunique() > 1:
        vals = sorted(df[color_by].unique())
        vmin, vmax = min(vals), max(vals)
        sm = ScalarMappable(cmap=SEQ_CMAP, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        for v in vals:
            g = df[df[color_by] == v].sort_values(x_col)
            t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
            ax.plot(g[x_col], g[y_col], color=SEQ_CMAP(0.15 + 0.85 * t),
                    linewidth=1.8, marker="o", markersize=3.5)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.06)
        cbar.set_label(color_by, color=INK_SECONDARY, fontsize=9)
        cbar.outline.set_visible(False)
    else:
        g = df.sort_values(x_col)
        ax.plot(g[x_col], g[y_col], color=CATEGORICAL_1, linewidth=2.0, marker="o", markersize=5)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    _style_axes(ax)
    fig.tight_layout()
    return fig


def plot_heatmap(df, y_col, x_col="a_hole_um", row_col="M_diopters"):
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
    if y_col not in df.columns:
        st.warning(f"Column `{y_col}` not in results.")
        return fig
    pivot = df.pivot_table(index=row_col, columns=x_col, values=y_col, aggfunc="mean")
    im = ax.imshow(pivot.values, aspect="auto", cmap=SEQ_CMAP, origin="lower")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{c:g}" for c in pivot.columns], rotation=45, fontsize=8)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{r:g}" for r in pivot.index], fontsize=8)
    ax.set_xlabel(x_col)
    ax.set_ylabel(row_col)
    cbar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.06)
    cbar.set_label(y_col, color=INK_SECONDARY, fontsize=9)
    fig.tight_layout()
    return fig


def plot_regime_map(df, x_col="a_hole_um", y_col="pitch_um", regime_col="regime"):
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
    if regime_col not in df.columns:
        st.warning(f"Column `{regime_col}` not in results.")
        return fig
    for regime, color in REGIME_COLORS.items():
        g = df[df[regime_col] == regime]
        if len(g) == 0:
            continue
        label = f"Regime {regime}" if regime else "n/a"
        ax.scatter(g[x_col], g[y_col], color=color, s=90, label=label,
                   edgecolor=SURFACE, linewidth=1.2)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    leg = ax.legend(frameon=False, fontsize=9, loc="upper left")
    for t in leg.get_texts():
        t.set_color(INK_SECONDARY)
    _style_axes(ax)
    fig.tight_layout()
    return fig


PLOT_DISPATCH = {
    "line_vs_aperture": lambda df, entry, y_col: plot_line_vs_aperture(
        df, y_col, entry.get("color_by"),
        x_col="a_hole_um" if "a_hole_um" in df.columns else "scene_luminance_cdm2"),
    "heatmap": lambda df, entry, y_col: plot_heatmap(df, y_col),
    "regime_map": lambda df, entry, y_col: plot_regime_map(df),
    "table_only": lambda df, entry, y_col: None,
}


# =============================================================================
# Main
# =============================================================================

def main():
    st.title("\U0001F52C Master Dashboard")
    st.caption("Live sweeps across every registered stage of the pinhole-sunglasses "
               "project. Every optics call goes through stage2_fixed/ -- verified "
               "below, not assumed.")

    render_physics_status()

    if "sweep_cache" not in st.session_state:
        st.session_state.sweep_cache = {}

    stage_keys = list(registry.REGISTRY.keys())
    stage_labels = [registry.REGISTRY[k]["label"] for k in stage_keys]
    st.sidebar.header("Stage")
    label_to_key = dict(zip(stage_labels, stage_keys))
    chosen_label = st.sidebar.selectbox("Select a stage", stage_labels)
    stage_key = label_to_key[chosen_label]
    entry = registry.REGISTRY[stage_key]

    st.sidebar.markdown(f"**Modules:** `{'`, `'.join(entry['modules'])}`")
    st.sidebar.markdown("---")
    st.sidebar.header("Parameters")
    params = render_param_widgets(stage_key, entry)

    st.header(entry["label"])
    if entry["uses_optics"]:
        path, is_correct = w.verify_phase2_retina_source()
        badge = "✅ stage2_fixed/" if is_correct else "⚠️ NOT stage2_fixed/"
        st.caption(f"Optics source for this tab: {badge} -- `{path}`")

    with st.expander("Notes / caveats for this stage", expanded=False):
        st.write(entry["notes"])

    n_points = registry.estimate_points(stage_key, params)
    est_s = registry.estimate_runtime_s(stage_key, params)
    key = _cache_key(stage_key, params)
    already_cached = key in st.session_state.sweep_cache

    col_a, col_b, col_c = st.columns([2, 2, 3])
    col_a.metric("Points in this sweep", n_points)
    col_b.metric("Estimated runtime", f"{est_s:.0f}s" if est_s < 120 else f"{est_s/60:.1f}min")
    with col_c:
        if already_cached:
            st.success("Already computed for this exact parameter set -- cached in this session.")

    run_clicked = False
    if already_cached:
        run_clicked = st.button("Re-run anyway (ignore cache)")
        show_results = True
    else:
        show_results = False
        if est_s > RUNTIME_CONFIRM_THRESHOLD_S:
            st.warning(f"Estimated runtime ~{est_s:.0f}s exceeds the {RUNTIME_CONFIRM_THRESHOLD_S:g}s "
                      f"auto-run threshold ({n_points} points × "
                      f"~{entry['cost_per_point_s']:g}s/point). Confirm before running:")
            confirmed = st.checkbox("Yes, run this sweep (I understand it will take a while)")
            if confirmed:
                run_clicked = st.button("Run Sweep", type="primary")
        else:
            run_clicked = st.button("Run Sweep", type="primary")

    if run_clicked:
        progress_bar = st.progress(0.0, text="Starting...")
        t0 = time.time()

        def _cb(done, total):
            frac = done / total if total else 1.0
            elapsed = time.time() - t0
            progress_bar.progress(min(frac, 1.0),
                                  text=f"{done}/{total} points ({elapsed:.0f}s elapsed)")

        try:
            df = entry["sweep_fn"](params, progress_cb=_cb)
            st.session_state.sweep_cache[key] = df
            show_results = True
            progress_bar.progress(1.0, text=f"Done -- {len(df)} rows in {time.time()-t0:.0f}s")
        except Exception as e:  # noqa: BLE001 -- surface, never swallow
            st.exception(e)
            show_results = False

    if show_results and key in st.session_state.sweep_cache:
        df = st.session_state.sweep_cache[key]
        st.subheader("Results")

        # Special-case surfaces for stages whose "notes" promise them:
        if stage_key == "r7acuity":
            cal = w.r7acuity_attempt_calibration(n_trials=100)
            if cal["ok"]:
                st.success(f"Ideal-observer calibration succeeded: sigma={cal['sigma']:.6f}")
            else:
                st.error("R7acuity's ideal-observer Monte Carlo calibration CRASHES against "
                        "the corrected optics (reproduced fresh, just now):")
                st.code(cal["message"])
                st.caption("Not worked around by widening the search bracket -- see "
                          "R7acuity/RESULTS.md's corrected-optics section. The plot/table "
                          "below is the closed-form Strehl/VSOTF cross-check ONLY.")
        if stage_key == "stage4_acuity":
            vs = w.read_stage4_validation_summary()
            if vs is not None:
                st.caption("Wang-2009 validation against these SAME corrected optics "
                          "(read from stage4_human_vision/outputs/, not recomputed live):")
                st.dataframe(vs, use_container_width=True)

        if entry["plot_type"] == "regime_map":
            # Fixed shape (aperture vs. pitch, colored by regime) -- the metric
            # selector below doesn't apply here; N_eff/margin values are in the
            # table beneath instead.
            fig = PLOT_DISPATCH[entry["plot_type"]](df, entry, "pitch_um")
            if fig is not None:
                st.pyplot(fig, use_container_width=True)
        elif entry["plot_type"] != "table_only":
            y_options = [c for c in entry["y_metrics"] if c in df.columns]
            if y_options:
                y_col = st.selectbox("Plot metric", y_options, key=f"{stage_key}__yplot")
                fig = PLOT_DISPATCH[entry["plot_type"]](df, entry, y_col)
                if fig is not None:
                    st.pyplot(fig, use_container_width=True)

        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, file_name=f"{stage_key}_sweep.csv",
                           mime="text/csv")


if __name__ == "__main__":
    main()
