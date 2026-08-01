"""Parameter sweep engine: Cartesian product over aperture diameter x propagation
distance x wavelength, with CSV summary export and optional per-config field export."""

import os

import numpy as np
import pandas as pd

from physics import RunConfig, effective_radius, precompute_transfer_function, run_configuration


def parse_wavelength_list(text, unit_scale=1e-9):
    return [float(v.strip()) * unit_scale for v in text.split(",") if v.strip()]


def range_values(start, stop, step):
    if step <= 0:
        return [start]
    n = int(round((stop - start) / step)) + 1
    return [start + i * step for i in range(n)]


def sweep_configs(diam_values, gap_values, wavelength_values):
    for wl in wavelength_values:
        for z in gap_values:
            for d in diam_values:
                yield wl, z, d


def estimate_sweep(n_configs, N, time_per_config_s=None):
    """Rough, informational-only cost estimate for the sweep UI (not a hard limit)."""
    if time_per_config_s is None:
        time_per_config_s = 3e-8 * (N ** 2) * np.log2(max(N, 2))  # ~ FFT cost scaling
    est_seconds = n_configs * time_per_config_s
    bytes_per_field_set = (N * N * 16) + 2 * (N * N * 8)  # Field.npy + Intensity.npy + Phase.npy
    return {
        "n_configs": n_configs,
        "est_seconds": est_seconds,
        "bytes_per_field_set": bytes_per_field_set,
        "est_bytes_if_saving_all_fields": n_configs * bytes_per_field_set,
    }


def build_csv_row(result, ee_percent, threshold_percent):
    cfg = result["cfg"]
    ee_label = f"r_EE_{ee_percent:g}pct_um"
    thr_label = f"threshold_{threshold_percent:g}pct_radius_um"
    return {
        "a_hole_um": cfg.a_hole * 1e6,
        "wavelength_nm": cfg.wavelength * 1e9,
        "z_gap_mm": cfg.z * 1e3,
        "N_F": result["N_F"],
        "regime": result["regime"],
        ee_label: effective_radius(result, "EE", ee_percent=ee_percent) * 1e6,
        "fwhm_radius_um": effective_radius(result, "fwhm") * 1e6,
        "second_moment_radius_um": effective_radius(result, "second_moment") * 1e6,
        "equivalent_area_radius_um": effective_radius(result, "equivalent_area") * 1e6,
        "one_over_e2_radius_um": effective_radius(result, "1/e2") * 1e6,
        thr_label: effective_radius(result, "threshold", threshold_percent=threshold_percent) * 1e6,
        "peak_intensity": result["I_peak"],
        "on_axis_intensity": result["I_onaxis"],
        "total_energy": result["total_power"],
        "energy_conservation_rel_error": result["energy_conservation_error"],
        "band_limit_energy_suppressed_frac": result["band_info"]["fraction_energy_suppressed"],
        "grid_N": cfg.N,
        "window_L_mm": cfg.L * 1e3,
        "all_checks_ok": all(c["ok"] for c in result["validation"]),
    }


def save_run_fields(result, out_dir):
    cfg = result["cfg"]
    tag = f"a{cfg.a_hole * 1e6:.0f}um_z{cfg.z * 1e3:.2f}mm_wl{cfg.wavelength * 1e9:.0f}nm_N{cfg.N}"
    sub = os.path.join(out_dir, tag)
    os.makedirs(sub, exist_ok=True)
    np.save(os.path.join(sub, "Intensity.npy"), result["I"])
    np.save(os.path.join(sub, "Phase.npy"), result["phase"])
    np.save(os.path.join(sub, "Field.npy"), result["Uz"])
    return sub


def run_sweep(diam_values, gap_values, wavelength_values, N, L, ee_percent=80.0,
              threshold_percent=10.0, band_limit=True, progress_cb=None,
              save_fields=False, fields_dir=None):
    total = len(diam_values) * len(gap_values) * len(wavelength_values)
    rows = []
    saved_dirs = []

    # H depends only on (N, dx, wavelength, z, L, band_limit) -- precomputed once per
    # (wavelength, z) pair and reused across the inner diameter loop below.
    dx = L / N
    for wl in wavelength_values:
        for z in gap_values:
            precomputed = precompute_transfer_function(N, dx, wl, z, L, band_limit)
            for d in diam_values:
                cfg = RunConfig(a_hole=d, wavelength=wl, z=z, N=N, L=L, band_limit=band_limit)
                result = run_configuration(cfg, precomputed=precomputed)
                rows.append(build_csv_row(result, ee_percent, threshold_percent))
                if save_fields and fields_dir:
                    saved_dirs.append(save_run_fields(result, fields_dir))
                if progress_cb:
                    progress_cb(len(rows), total, cfg)

    df = pd.DataFrame(rows)
    return df, saved_dirs
