"""
Verification script (not part of the app itself): exercises entry["sweep_fn"] and the
matching PLOT_DISPATCH renderer for every registered stage with a MINIMAL parameter
set, exactly the code path app.py's "Run Sweep" button triggers. Used to confirm a
clean boot across every stage without needing the browser extension.
"""
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")

import registry
import app as dash_app
import wrappers as w

MINIMAL_OVERRIDES = {
    "stage1": {"a_hole_um": [300, 750], "d_gap_mm": [12.0], "wavelength_nm": [550.0]},
    "stage2_blur": {"a_hole_um": [300, 750], "M_diopters": [2.0]},
    "stage3a_brightness": {"a_hole_um": [300, 750, 1000], "M_diopters": [2.0], "T_min": 0.0625},
    "stage3_human_vision": {"a_hole_um": [300, 750], "M_diopters": [2.0], "grid_N": 512},
    "stage3_integrated": {"a_hole_um": [300, 750, 1000], "M_diopters": [2.0], "grid_N": 512, "T_min": 0.0625},
    "stage4_acuity": {"a_hole_um": [300, 750], "M_diopters": [2.0]},
    "r7acuity": {"a_hole_um": [300, 750], "M_diopters": [2.0]},
    "model_comparison": {"a_hole_um": [300, 750], "M_diopters": [2.0]},
    "array_ghosting": {"a_hole_um": [500], "pitch_um": [600, 2000], "M_diopters": [2.0]},
    "brightness_reconciliation": {"scene_luminance_cdm2": [300, 10000]},
    "singleilluminate": {"a_hole_um": [300, 750], "D_pupil_um": [4000.0]},
}

results = {}
for stage_key, entry in registry.REGISTRY.items():
    params = {}
    for k, spec in entry["params"].items():
        params[k] = MINIMAL_OVERRIDES[stage_key].get(k, spec["default"])
    print(f"=== {stage_key} ({entry['label']}) ===")
    t0 = time.time()
    try:
        df = entry["sweep_fn"](params, progress_cb=None)
        n = len(df)
        cols = list(df.columns)
        plot_ok, plot_err = True, None
        if entry["plot_type"] != "table_only":
            y_options = [c for c in entry["y_metrics"] if c in df.columns]
            if y_options:
                try:
                    fig = dash_app.PLOT_DISPATCH[entry["plot_type"]](df, entry, y_options[0])
                    if fig is not None:
                        import matplotlib.pyplot as plt
                        plt.close(fig)
                except Exception as pe:  # noqa: BLE001
                    plot_ok, plot_err = False, str(pe)
        optics_ok = None
        if entry["uses_optics"]:
            _, optics_ok = w.verify_phase2_retina_source()
        results[stage_key] = {
            "sweep_ok": True, "rows": n, "cols": cols, "plot_ok": plot_ok,
            "plot_err": plot_err, "optics_ok": optics_ok, "elapsed_s": time.time() - t0,
        }
        status = "OK" if plot_ok else f"SWEEP OK, PLOT FAILED: {plot_err}"
        print(f"  {status} -- {n} rows, {time.time()-t0:.1f}s, optics_ok={optics_ok}")
    except Exception as e:  # noqa: BLE001
        results[stage_key] = {"sweep_ok": False, "error": str(e), "traceback": traceback.format_exc()}
        print(f"  SWEEP FAILED: {e}")
        traceback.print_exc()
    print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)
n_ok = 0
for k, r in results.items():
    if r.get("sweep_ok") and r.get("plot_ok", True):
        n_ok += 1
        print(f"  [PASS] {k}")
    else:
        print(f"  [FAIL] {k}: {r.get('error') or r.get('plot_err')}")
print(f"\n{n_ok}/{len(results)} stages passed cleanly.")
