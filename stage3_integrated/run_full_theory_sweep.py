"""
Supplementary sweeps beyond the existing 105-point (550nm/12mm) grid already combined
by combine_metrics.py. Three targeted additions, each reusing stage3_human_vision's own
functions (metrics.py, phase2_retina.py via metrics.py) -- no new physics, no
modification to any prior stage:

  1. Retina-plane FWHM, on the full 105-point grid (never computed before -- Stage 2's
     phase2_retina.retinal_encircled_energy only ever returns r_EE, not FWHM). Checks
     whether stage1_v2's documented cornea-plane FWHM ring-hopping ambiguity also
     appears at the retina plane.
  2. A finer aperture sweep at M=4D and M=8D (where optimum_by_metric_and_M.csv shows
     Strehl's most dramatic jumps) to determine whether the non-monotonicity is genuine
     multiple local maxima or a 15-point sampling artifact.
  3. A representative subset (8 apertures) at 450nm/650nm and at 15mm gap, extending
     the full metric set beyond the 550nm/12mm grid it was previously limited to --
     scoped down from the full 15-aperture x 3-wavelength x 2-gap grid (which would
     re-run the entire sweep 6x over) to keep this tractable; documented, not hidden.
"""

import os
import sys
import time

import numpy as np
import pandas as pd

_STAGE1_V2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage1_v2"))
_STAGE3HV_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage3_human_vision"))
for _d in (_STAGE1_V2_DIR, _STAGE3HV_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import metrics  # noqa: E402 (stage3_human_vision -- includes fwhm_radius, promoted from this file's own former inline FWHM code)
import phase2_retina as p2  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
FULL_APERTURE_LIST_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
M_VALUES = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
REPRESENTATIVE_APERTURES_UM = [100, 300, 400, 500, 750, 1000, 1500, 2000]


def retina_plane_fwhm(a_hole_um, wavelength_nm, d_gap_mm, M, D_pupil_um=4000.0,
                       grid_N=2048, window_L_mm=6.0):
    """FWHM at the retina, via metrics.fwhm_radius() (stage3_human_vision) -- which
    itself reuses the SAME outward-from-peak, local-minimum-stopping algorithm
    stage1_v2/physics.py::locate_threshold_crossing already validated at the cornea
    plane. Previously this function inlined that same radial_profile +
    locate_threshold_crossing pair directly; now that metrics.fwhm_radius() exists
    as a first-class metric (promoted for the same reason this sweep needed it),
    calling it here instead removes the duplication -- behavior-preserving, not a
    numeric change."""
    result = p2.run_pipeline_point(
        a_hole=a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9, d_gap=d_gap_mm * 1e-3,
        grid_N=grid_N, window_L_mm=window_L_mm, M_diopters=M, P0=60.0, n_prime=1.336,
        D_pupil_um=D_pupil_um, refractive_index_correction=True,
    )
    if not result["junction_check_passed"]:
        return None
    I = result["I_retina"]
    dx = result["cornea_result"]["dx"]
    detail = metrics.fwhm_radius(I, dx)
    return {"fwhm_radius_um": detail["radius"] * 1e6, "fwhm_mode": detail["mode"],
            "crossing_count": detail["crossing_count"]}


def sweep_1_retina_fwhm():
    print("[1/3] Retina-plane FWHM across the full 105-point grid...")
    rows = []
    t0 = time.time()
    for a_um in FULL_APERTURE_LIST_UM:
        for M in M_VALUES:
            fwhm = retina_plane_fwhm(a_um, 550.0, 12.0, M)
            row = {"a_hole_um": a_um, "M_diopters": M}
            row.update(fwhm or {"fwhm_radius_um": np.nan, "fwhm_mode": "junction_failed", "crossing_count": np.nan})
            rows.append(row)
    df = pd.DataFrame(rows)
    print(f"  done in {time.time()-t0:.0f}s")
    return df


def sweep_2_fine_strehl(M_values=(4.0, 8.0), step_um=100):
    print(f"[2/3] Fine aperture sweep for Strehl non-monotonicity check (M={M_values})...")
    fine_apertures = list(range(100, 2001, step_um))
    rows = []
    t0 = time.time()
    for M in M_values:
        for a_um in fine_apertures:
            a_hole = a_um * 1e-6
            I_dl = metrics.get_diffraction_limited_reference(a_hole, 550e-9, 12e-3, 4000.0)
            m = metrics.compute_all_metrics(a_hole, 550e-9, 12e-3, M, 4000.0, precomputed_I_dl=I_dl)
            m["a_hole_um_target"] = a_um
            rows.append(m)
        print(f"  M={M}D done ({time.time()-t0:.0f}s elapsed)")
    return pd.DataFrame(rows)


def sweep_3_wavelength_gap(apertures_um=REPRESENTATIVE_APERTURES_UM):
    print("[3/3] Representative wavelength (450/650nm) and gap (15mm) coverage...")
    rows = []
    t0 = time.time()
    configs = [(wl, 12.0) for wl in (450.0, 650.0)] + [(550.0, 15.0)]
    for wl, gap in configs:
        for a_um in apertures_um:
            a_hole = a_um * 1e-6
            I_dl = metrics.get_diffraction_limited_reference(a_hole, wl * 1e-9, gap * 1e-3, 4000.0)
            for M in M_VALUES:
                m = metrics.compute_all_metrics(a_hole, wl * 1e-9, gap * 1e-3, M, 4000.0, precomputed_I_dl=I_dl)
                rows.append(m)
        print(f"  wavelength={wl}nm gap={gap}mm done ({time.time()-t0:.0f}s elapsed)")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which in ("1", "all"):
        sweep_1_retina_fwhm().to_csv(os.path.join(OUT_DIR, "retina_fwhm_sweep.csv"), index=False)
    if which in ("2", "all"):
        sweep_2_fine_strehl().to_csv(os.path.join(OUT_DIR, "fine_strehl_sweep.csv"), index=False)
    if which in ("3", "all"):
        sweep_3_wavelength_gap().to_csv(os.path.join(OUT_DIR, "wavelength_gap_sweep.csv"), index=False)
    print("Done.")
