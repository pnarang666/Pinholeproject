"""
Generates every raw sweep CSV the aperture-optimization report needs, for stages that
do not already have a current (post-physics-fix) full-grid CSV sitting in new_sweeps/.

Reuses master_dashboard/wrappers.py's thin wrapper functions directly -- the same,
already-audited/isolated code paths the dashboard itself uses (including
_isolated_stage2_deprecated_import() for the deprecated-pipeline comparison) -- no
physics is reimplemented here, only orchestration + CSV writing.

Run from anywhere:
    python3 Aperture_Optimization_Report/generate_report_data.py
"""
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "master_dashboard"))
import wrappers as w  # noqa: E402
import pandas as pd  # noqa: E402

OUT = os.path.join(ROOT, "Aperture_Optimization_Report", "data")
os.makedirs(OUT, exist_ok=True)

APERTURES = w.STANDARD_APERTURES_UM          # 15 values, 75-2000um
M_VALUES = w.STANDARD_M_VALUES               # 8 values, 0-8D


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_and_save(name, fn, params, csv_name):
    path = os.path.join(OUT, csv_name)
    if os.path.exists(path):
        log(f"SKIP {name} -- {csv_name} already exists ({sum(1 for _ in open(path))-1} rows)")
        return
    log(f"START {name} ({csv_name})")
    t0 = time.time()

    def cb(done, total):
        if done % 10 == 0 or done == total:
            log(f"  {name}: {done}/{total} ({time.time()-t0:.0f}s elapsed)")

    df = fn(params, progress_cb=cb)
    df.to_csv(path, index=False)
    log(f"DONE {name} -- {len(df)} rows in {time.time()-t0:.0f}s -> {csv_name}")


def main():
    log(f"Standard grid: {len(APERTURES)} apertures x {len(M_VALUES)} M values "
        f"= {len(APERTURES)*len(M_VALUES)} points per full sweep")

    # 1. Stage 1 -- cornea-plane diffraction only (no M dependence, but sweep M-free
    #    columns anyway isn't meaningful; sweep aperture x wavelength x gap instead,
    #    matching the dashboard's own Stage 1 params).
    run_and_save(
        "stage1_cornea", w.sweep_stage1,
        {"a_hole_um": APERTURES, "d_gap_mm": [12.0], "wavelength_nm": [550.0]},
        "stage1_cornea_sweep.csv")

    # 2. Stage 2 deprecated (pre-fix) -- full grid, for the corrected-vs-deprecated
    #    comparison chapter. Isolated automatically by wrappers.py.
    run_and_save(
        "stage2_deprecated", w.sweep_stage2_deprecated,
        {"a_hole_um": APERTURES, "M_diopters": M_VALUES},
        "stage2_deprecated_sweep.csv")

    # 3. Stage 3a -- brightness-constrained optimum (recomputes fresh blur internally
    #    via stage2_fixed/, T_min at its own documented default 6.25%).
    run_and_save(
        "stage3a_brightness", w.sweep_stage3a_brightness,
        {"a_hole_um": APERTURES, "M_diopters": M_VALUES, "D_pupil_um": 4000.0, "T_min": 0.0625},
        "stage3a_brightness_sweep.csv")

    # 4. Stage 3 Human Vision -- MTF/CSF/Strehl/photometry, full grid.
    run_and_save(
        "stage3_human_vision", w.sweep_stage3_human_vision,
        {"a_hole_um": APERTURES, "M_diopters": M_VALUES},
        "stage3_human_vision_sweep.csv")

    # 5. Model Comparison -- RSS (deprecated closed-form) vs exact numerical divergence.
    run_and_save(
        "model_comparison", w.sweep_model_comparison,
        {"a_hole_um": APERTURES, "M_diopters": M_VALUES},
        "model_comparison_sweep.csv")

    # 6. R7acuity -- closed-form Strehl/VSOTF cross-check (the only R7 path that
    #    doesn't require noise-sigma calibration, which crashes against corrected
    #    optics -- see R7acuity/RESULTS.md). Smaller aperture subset (dashboard's own
    #    registry default) since this is the most expensive per-point stage (~8.5s).
    run_and_save(
        "r7acuity_closed_form", w.r7acuity_closed_form_sweep,
        {"a_hole_um": [300, 500, 750, 1000, 1250, 1500, 1750, 2000], "M_diopters": M_VALUES},
        "r7acuity_closed_form_sweep.csv")

    # 7. Brightness reconciliation -- absolute (troland) vs percentage threshold,
    #    across a luminance range (no aperture/M dependence, fast).
    run_and_save(
        "brightness_reconciliation", w.sweep_brightness_reconciliation,
        {"scene_luminance_cdm2": [10, 30, 100, 200, 300, 1000, 3000, 10000, 25000]},
        "brightness_reconciliation_sweep.csv")

    # 8. Single illuminate -- single-hole illumination vs pupil diameter.
    run_and_save(
        "singleilluminate", w.sweep_singleilluminate,
        {"a_hole_um": APERTURES, "D_pupil_um": [3000.0, 4000.0, 5000.0]},
        "singleilluminate_sweep.csv")

    log("ALL DATA GENERATION COMPLETE")


if __name__ == "__main__":
    main()
