"""Session logging: every live-computed point (Tab 1 or 2) appended to a session CSV."""

import os
from datetime import datetime, timezone

import pandas as pd

LOG_COLUMNS = [
    "timestamp", "source_tab", "a_hole_um", "wavelength_nm", "M_diopters", "d_gap_mm",
    "D_pupil_um", "grid_N", "compute_time_s", "junction_check_passed",
    "r_EE_50_um", "r_EE_80_um", "r_EE_90_um", "rms_spot_radius_um", "strehl_ratio",
    "mtf50_cpd", "mtf10_cpd", "relative_retinal_illuminance", "snellen_denom_mtf50",
]


def log_point(session_state, result, source_tab):
    """Appends one computed point to session_state['log_rows'] (a list of dicts)."""
    if "log_rows" not in session_state:
        session_state["log_rows"] = []
    row = {"timestamp": datetime.now(timezone.utc).isoformat(), "source_tab": source_tab}
    for col in LOG_COLUMNS:
        if col in ("timestamp", "source_tab"):
            continue
        row[col] = result.get(col)
    session_state["log_rows"].append(row)


def get_log_df(session_state):
    rows = session_state.get("log_rows", [])
    if not rows:
        return pd.DataFrame(columns=LOG_COLUMNS)
    return pd.DataFrame(rows)


def export_csv_bytes(session_state):
    return get_log_df(session_state).to_csv(index=False).encode()
