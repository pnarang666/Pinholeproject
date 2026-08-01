"""
Single-hole illumination explorer -- lightweight companion to stage_v1_simulator.

Illumination is a closed-form (a_hole/D_pupil)^2 area ratio, not a wave-optics
quantity -- no ASM propagation anywhere in this app, so there is no fast/accurate-
mode toggle and no reason for this to be slow. Precomputed sweep data
(outputs/illumination_results.csv, from run_illumination_sweep.py) is loaded for
every curve; only the current single point is computed live.

SCOPE: single-hole illumination only. The array tab (multi-hole illumination,
no-ghost pitch cross-check) described in the original brief for this app requires
stage_array/, which does not exist anywhere in this project (see
illumination_model.py's module docstring for the exhaustive search that confirmed
this). That tab is shown below as an explicit "blocked" placeholder, not silently
dropped and not filled with invented numbers -- a user opening only this app still
sees that gap, per this project's standing rule against silently hiding known
limitations.
"""

import os
import sys

import numpy as np
import pandas as pd
import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import illumination_model

OUT_DIR = os.path.join(_HERE, "outputs")
RESULTS_CSV = os.path.join(OUT_DIR, "illumination_results.csv")

st.set_page_config(page_title="Single-hole Illumination Explorer", layout="wide")
st.title("Single-hole Illumination Explorer")
st.caption(
    "Closed-form (a_hole/D_pupil)^2 illumination only -- no wave-optics computation, "
    "so every number on this page updates instantly. For blur/MTF/Strehl/acuity, see "
    "the full stage_v1_simulator app instead."
)


@st.cache_data
def load_results():
    if not os.path.exists(RESULTS_CSV):
        return None
    return pd.read_csv(RESULTS_CSV)


results_df = load_results()

tab1, tab2, tab3 = st.tabs(["Single-hole", "Array (blocked)", "No-ghost cross-check (blocked)"])

# ---------------------------------------------------------------------------------
# Tab 1: Single-hole
# ---------------------------------------------------------------------------------
with tab1:
    st.subheader("Single circular pinhole")
    col_controls, col_plot = st.columns([1, 2])

    with col_controls:
        a_hole_um = st.slider("Pinhole diameter a_hole (µm)", min_value=50, max_value=4000,
                               value=400, step=10)
        D_pupil_um = st.slider("Natural pupil diameter D_pupil (µm)", min_value=2000, max_value=8000,
                                value=4000, step=100)

        live = illumination_model.percent_illumination(a_hole_um, D_pupil_um)
        st.metric("percent_illumination", f"{live['percent_illumination'] * 100:.2f}%")
        st.caption(f"model={live['model']}, N_eff={live['N_eff']}")

        floor_lo, floor_hi = illumination_model.BRIGHTNESS_FLOOR_LOW, illumination_model.BRIGHTNESS_FLOOR_HIGH
        if live["percent_illumination"] >= floor_hi:
            st.success(f"Above the 9% brightness floor (stage3a's upper reference).")
        elif live["percent_illumination"] >= floor_lo:
            st.info(f"Between the 6.25% and 9% brightness floors (stage3a's reference range).")
        else:
            st.warning(f"Below the 6.25% brightness floor (stage3a's lower reference).")

    with col_plot:
        if results_df is None:
            st.warning(f"No precomputed data found at {RESULTS_CSV} -- run "
                       f"`python3 run_illumination_sweep.py` first for the curve below. "
                       f"The live readout on the left still works without it.")
        else:
            single_df = results_df[results_df["row_type"] == "single_hole"]
            nearest_D = single_df["D_pupil_um"].iloc[
                (single_df["D_pupil_um"] - D_pupil_um).abs().argsort().iloc[0]
            ]
            curve = single_df[np.isclose(single_df["D_pupil_um"], nearest_D)].sort_values("a_hole_um")

            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(7, 5))
            ax.plot(curve["a_hole_um"], curve["percent_illumination"] * 100, "o-",
                    color="#2a78d6", label=f"D_pupil={nearest_D:.0f}um (nearest precomputed)")
            ax.axhline(floor_lo * 100, color="gray", linestyle=":", label="6.25% floor")
            ax.axhline(floor_hi * 100, color="gray", linestyle="--", label="9% floor")
            ax.plot([a_hole_um], [live["percent_illumination"] * 100], "*", color="red",
                    markersize=18, label="current point", zorder=5)
            ax.set_xlabel("aperture (µm)")
            ax.set_ylabel("percent_illumination (%)")
            ax.set_title("percent_illumination vs aperture")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
            st.pyplot(fig)
            plt.close(fig)
            if not np.isclose(nearest_D, D_pupil_um):
                st.caption(f"Note: curve shown at the nearest precomputed D_pupil "
                           f"({nearest_D:.0f}um) -- your slider is at {D_pupil_um}um; "
                           f"the live star marker above is still exact.")

# ---------------------------------------------------------------------------------
# Tab 2: Array -- explicitly blocked, not faked
# ---------------------------------------------------------------------------------
with tab2:
    st.error(
        "**Blocked: stage_array/ does not exist in this project.**\n\n"
        "This tab was specified to show multi-hole array illumination (N_holes, "
        "pitch, square/hex packing, worst/mean/best-case discrete lattice alignment) "
        "via a `stage_array/array_photometry.py` module. That module was searched "
        "for exhaustively across this entire codebase (function names, README "
        "mentions, everything) and does not exist -- there is no prior array-"
        "photometry implementation to reuse, and this project's own rule is to never "
        "invent new physics to fill a gap like this. Calling "
        "`illumination_model.percent_illumination(..., N_holes>1, pitch_um=...)` "
        "raises `NotImplementedError` for exactly this reason -- try it below."
    )
    with st.expander("Try it (will raise NotImplementedError)"):
        try:
            illumination_model.percent_illumination(400.0, 4000.0, N_holes=7, pitch_um=1200.0)
        except NotImplementedError as e:
            st.code(str(e), language=None)

# ---------------------------------------------------------------------------------
# Tab 3: No-ghost cross-check -- explicitly blocked, not faked
# ---------------------------------------------------------------------------------
with tab3:
    st.error(
        "**Blocked: stage_array/no_ghost_max_pitch() does not exist in this "
        "project.**\n\n"
        "This tab was specified to compare a chosen (a_hole, pitch) against the "
        "no-ghost maximum pitch derived from REAL r_EE(P) data (per the Master "
        "Formulas doc's constraint `s < r_EE(P)*d_gap/v_r`), and to surface two "
        "already-claimed findings: a 'zero-holes-under-pupil' worst case and a "
        "discrepancy between the no-ghost bound and real patent pitch values. None "
        "of that has actually been built or verified anywhere in this project -- "
        "showing those findings here without the underlying computation would mean "
        "fabricating results, which this app deliberately does not do. This gap is "
        "shown here on purpose, not silently omitted, so a user of this "
        "illumination-only app still sees it."
    )

st.divider()
st.caption(
    "Scope: single-hole illumination only (see illumination_model.py, "
    "run_illumination_sweep.py, README.md). No 'recommended aperture' is computed "
    "or implied anywhere in this app -- this is an exploration tool for one factor "
    "(brightness), meant to sit alongside blur/acuity/Strehl comparisons in the rest "
    "of this project, not to rank against or replace them."
)
