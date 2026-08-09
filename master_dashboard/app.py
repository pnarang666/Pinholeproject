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
from matplotlib.lines import Line2D
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


def plot_line_vs_aperture(df, y_col, color_by, x_col="a_hole_um",
                           overlay_df=None, overlay_label=None, primary_label=None):
    """
    overlay_df (optional): a second, already-cached sweep result (any stage, any
    params -- caller in main() only offers ones sharing x_col/y_col) plotted on the
    SAME axes for direct comparison -- e.g. the deprecated stage2/ tab overlaid
    against the corrected Stage 2 tab. Encodes the two dimensions separately, never
    conflated: color still encodes color_by's magnitude (identical hue = identical
    color_by value in either series), linestyle (solid vs dashed) encodes which
    series is which -- so a two-entry style legend is added alongside the existing
    color_by colorbar rather than instead of it.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
    if x_col not in df.columns or y_col not in df.columns:
        st.warning(f"Column `{y_col}` or `{x_col}` not in results.")
        return fig

    has_overlay = (overlay_df is not None and x_col in overlay_df.columns
                   and y_col in overlay_df.columns)
    use_color = color_by and color_by in df.columns and df[color_by].nunique() > 1

    if use_color:
        vals = set(df[color_by].unique())
        if has_overlay and color_by in overlay_df.columns:
            vals |= set(overlay_df[color_by].unique())
        vals = sorted(vals)
        vmin, vmax = min(vals), max(vals)
        sm = ScalarMappable(cmap=SEQ_CMAP, norm=plt.Normalize(vmin=vmin, vmax=vmax))

        def _plot_series(source_df, linestyle):
            if color_by not in source_df.columns:
                return
            for v in sorted(source_df[color_by].unique()):
                g = source_df[source_df[color_by] == v].sort_values(x_col)
                t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
                ax.plot(g[x_col], g[y_col], color=SEQ_CMAP(0.15 + 0.85 * t),
                        linewidth=1.8, marker="o", markersize=3.5, linestyle=linestyle)

        _plot_series(df, "-")
        if has_overlay:
            _plot_series(overlay_df, "--")
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.06)
        cbar.set_label(color_by, color=INK_SECONDARY, fontsize=9)
        cbar.outline.set_visible(False)
        if has_overlay:
            style_handles = [
                Line2D([0], [0], color=INK_SECONDARY, linestyle="-",
                       label=primary_label or "this sweep"),
                Line2D([0], [0], color=INK_SECONDARY, linestyle="--",
                       label=overlay_label or "overlay"),
            ]
            leg = ax.legend(handles=style_handles, frameon=False, fontsize=8, loc="best")
            for t in leg.get_texts():
                t.set_color(INK_SECONDARY)
    else:
        g = df.sort_values(x_col)
        ax.plot(g[x_col], g[y_col], color=CATEGORICAL_1, linewidth=2.0, marker="o",
                markersize=5, linestyle="-", label=primary_label or "this sweep")
        if has_overlay:
            go = overlay_df.sort_values(x_col)
            ax.plot(go[x_col], go[y_col], color=CATEGORICAL_2, linewidth=2.0, marker="o",
                    markersize=5, linestyle="--", label=overlay_label or "overlay")
            leg = ax.legend(frameon=False, fontsize=9, loc="best")
            for t in leg.get_texts():
                t.set_color(INK_SECONDARY)
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
    # line_vs_aperture and heatmap are called directly in main() with user-picked
    # X/Y/color axes (the free axis picker) -- only regime_map (fixed shape: aperture
    # vs. pitch, colored by regime -- a domain-specific plot, not a generic metric
    # picker) and table_only (no plot at all) still go through this dispatch table.
    "regime_map": lambda df, entry, y_col: plot_regime_map(df),
    "table_only": lambda df, entry, y_col: None,
}


def _numeric_cols(df):
    return [c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]


def _param_summary(params):
    """Compact, stable-order text summary of a param dict for the sweep-cache label
    (e.g. overlay picker) -- never truncates silently to something misleading; long
    lists are shown as first..last plus a count rather than dropped."""
    parts = []
    for k in sorted(params):
        v = params[k]
        if isinstance(v, list) and len(v) > 3:
            parts.append(f"{k}=[{v[0]}..{v[-1]}, n={len(v)}]")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)


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
    if entry.get("deprecated_optics"):
        # This tab loads stage2/ (the pre-fix, known-broken copy) ON PURPOSE -- see
        # wrappers.py's _isolated_stage2_deprecated_import(). verify_phase2_retina_source()
        # would correctly report "NOT stage2_fixed" for the instant this tab's sweep is
        # actually running, which is expected here, not a regression -- so this tab gets
        # its own distinct badge instead of the normal green/red one, which is reserved
        # for reporting whether the CORRECTED pipeline (every other tab) is intact.
        st.warning("Optics source for this tab: ⚠️ **stage2/ -- DEPRECATED, known-broken "
                  "pre-fix optics, used here ON PURPOSE** for reference/comparison only. "
                  "Isolated to this one tab -- every other tab still verifies "
                  "stage2_fixed/ live and is unaffected (see Project Physics Status "
                  "above, and this tab's own Notes below for what's actually wrong "
                  "with this pipeline).")
    elif entry["uses_optics"]:
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
            label = f"{entry['label']} ({_param_summary(params)})"
            st.session_state.sweep_cache[key] = {"df": df, "label": label, "stage_key": stage_key}
            show_results = True
            progress_bar.progress(1.0, text=f"Done -- {len(df)} rows in {time.time()-t0:.0f}s")
        except Exception as e:  # noqa: BLE001 -- surface, never swallow
            st.exception(e)
            show_results = False

    if show_results and key in st.session_state.sweep_cache:
        cached = st.session_state.sweep_cache[key]
        df = cached["df"]
        st.subheader("Results")

        # Special-case surfaces for stages whose "notes" promise them:
        if stage_key == "r7acuity":
            # This itself takes real time (a bisection over noise-calibration trials,
            # same underlying MC cost class as the sweep above) -- found via a live
            # browser test that the page otherwise sits on "Done" with nothing below
            # it for 20-30s with no explanation. The spinner is the fix, not making
            # this call faster (it needs to actually run, fresh, every time -- see
            # its own docstring on why this is never skipped or cached).
            with st.spinner("Attempting fresh ideal-observer calibration (not cached -- "
                            "re-run every time, per this project's own no-post-hoc-"
                            "tuning discipline)..."):
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
            # Fixed shape (aperture vs. pitch, colored by regime) -- a domain-specific
            # plot, not a generic metric picker; N_eff/margin values are in the table
            # beneath instead.
            fig = PLOT_DISPATCH[entry["plot_type"]](df, entry, "pitch_um")
            if fig is not None:
                st.pyplot(fig, use_container_width=True)

        elif entry["plot_type"] == "line_vs_aperture":
            numeric_cols = _numeric_cols(df)
            if numeric_cols:
                default_x = next((c for c in ("a_hole_um", "scene_luminance_cdm2")
                                  if c in numeric_cols), numeric_cols[0])
                y_defaults = [m for m in entry["y_metrics"] if m in numeric_cols and m != default_x]
                default_y = y_defaults[0] if y_defaults else next(
                    (c for c in numeric_cols if c != default_x), numeric_cols[0])

                pcols = st.columns(3)
                x_col = pcols[0].selectbox("X-axis", numeric_cols,
                                           index=numeric_cols.index(default_x),
                                           key=f"{stage_key}__xplot")
                y_options = [c for c in numeric_cols if c != x_col] or numeric_cols
                y_col = pcols[1].selectbox("Y-axis", y_options,
                                           index=y_options.index(default_y) if default_y in y_options else 0,
                                           key=f"{stage_key}__yplot")
                color_options = ["None"] + [c for c in numeric_cols
                                            if c != x_col and df[c].nunique() > 1]
                default_color = entry.get("color_by") if entry.get("color_by") in color_options else "None"
                color_choice = pcols[2].selectbox("Color by", color_options,
                                                   index=color_options.index(default_color),
                                                   key=f"{stage_key}__colorby")
                color_by = None if color_choice == "None" else color_choice

                # Overlay another cached sweep from THIS session (any stage, any
                # params) on the same axes for direct comparison -- e.g. the
                # deprecated stage2/ tab against the corrected Stage 2 tab, or two
                # different parameter sets of the same stage. Only offered when a
                # compatible cached sweep (same X and Y columns) actually exists.
                compatible = {k2: v2 for k2, v2 in st.session_state.sweep_cache.items()
                             if k2 != key and x_col in v2["df"].columns and y_col in v2["df"].columns}
                overlay_df = overlay_label = None
                if compatible:
                    overlay_choice = st.selectbox(
                        "Overlay another cached sweep for comparison (optional)",
                        ["None"] + [v2["label"] for v2 in compatible.values()],
                        key=f"{stage_key}__overlay")
                    if overlay_choice != "None":
                        overlay_key = next(k2 for k2, v2 in compatible.items()
                                           if v2["label"] == overlay_choice)
                        overlay_df = compatible[overlay_key]["df"]
                        overlay_label = overlay_choice
                else:
                    st.caption("Run another sweep sharing this X/Y axis (any stage, any "
                              "parameters -- e.g. the deprecated Stage 2 tab vs. this "
                              "one) to unlock overlay comparison here.")

                fig = plot_line_vs_aperture(df, y_col, color_by, x_col=x_col,
                                            overlay_df=overlay_df, overlay_label=overlay_label,
                                            primary_label=cached["label"])
                st.pyplot(fig, use_container_width=True)

        elif entry["plot_type"] == "heatmap":
            numeric_cols = _numeric_cols(df)
            if numeric_cols:
                default_x = "a_hole_um" if "a_hole_um" in numeric_cols else numeric_cols[0]
                row_options = [c for c in numeric_cols if c != default_x] or numeric_cols
                default_row = "M_diopters" if "M_diopters" in row_options else row_options[0]

                pcols = st.columns(3)
                x_col = pcols[0].selectbox("X-axis (columns)", numeric_cols,
                                           index=numeric_cols.index(default_x),
                                           key=f"{stage_key}__hx")
                row_options = [c for c in numeric_cols if c != x_col] or numeric_cols
                row_col = pcols[1].selectbox("Row axis", row_options,
                                             index=row_options.index(default_row) if default_row in row_options else 0,
                                             key=f"{stage_key}__hrow")
                val_options = [c for c in numeric_cols if c not in (x_col, row_col)] or numeric_cols
                val_defaults = [m for m in entry["y_metrics"] if m in val_options]
                default_val = val_defaults[0] if val_defaults else val_options[0]
                y_col = pcols[2].selectbox("Value (color)", val_options,
                                           index=val_options.index(default_val),
                                           key=f"{stage_key}__hval")
                fig = plot_heatmap(df, y_col, x_col=x_col, row_col=row_col)
                st.pyplot(fig, use_container_width=True)

        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, file_name=f"{stage_key}_sweep.csv",
                           mime="text/csv")


if __name__ == "__main__":
    main()
