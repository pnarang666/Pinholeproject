"""
Matplotlib figure builders for the Stage 1 Corneal Fresnel Field Analyzer.

Every function returns a Figure so callers can st.pyplot() it and also fig.savefig()
the same object at publication dpi -- there is no separate "screen" vs "export" figure.
"""

import matplotlib.pyplot as plt
import numpy as np

import physics

CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#008300",
               "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]


def _series_color(i):
    return CATEGORICAL[i % len(CATEGORICAL)]


def plot_intensity(result, ax=None):
    fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=(5.5, 5))
    extent_um = result["R"].max() * 1e6 * np.array([-1, 1, -1, 1])
    im = ax.imshow(result["I"], extent=extent_um, cmap="inferno", origin="lower")
    ax.set_title("Intensity at cornea")
    ax.set_xlabel("x (µm)"); ax.set_ylabel("y (µm)")
    fig.colorbar(im, ax=ax, fraction=0.046, label="intensity (a.u.)")
    return fig


def plot_phase(result, ax=None):
    fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=(5.5, 5))
    extent_um = result["R"].max() * 1e6 * np.array([-1, 1, -1, 1])
    im = ax.imshow(result["phase"], extent=extent_um, cmap="twilight", origin="lower",
                    vmin=-np.pi, vmax=np.pi)
    ax.set_title("Phase arg(U) at cornea (wrapped)")
    ax.set_xlabel("x (µm)"); ax.set_ylabel("y (µm)")
    fig.colorbar(im, ax=ax, fraction=0.046, label="phase (rad)")
    return fig


def plot_radial_profile(result, effective_radii=None, ax=None, r_max_um=None):
    fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=(6, 4.5))
    r_um = result["r_centers"] * 1e6
    ax.plot(r_um, result["I_radial"], color=CATEGORICAL[0], lw=2)
    xmax = r_max_um if r_max_um else result["R"].max() * 1e6 * 0.5
    ax.set_xlim(0, xmax)
    ax.set_xlabel("radius (µm)"); ax.set_ylabel("azimuthally-averaged intensity")
    ax.set_title("Radial intensity (Fresnel ringing)")
    ax.grid(alpha=0.3)
    if effective_radii:
        for i, (label, r_m) in enumerate(effective_radii.items()):
            r_um_val = r_m * 1e6
            if r_um_val <= xmax:
                ax.axvline(r_um_val, color=_series_color(i + 1), linestyle="--", alpha=0.8,
                           label=f"{label} = {r_um_val:.1f} µm")
        ax.legend(fontsize=8, loc="upper right")
    return fig


def plot_encircled_energy(result, target_P=None, effective_radii=None, ax=None, r_max_um=None):
    fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=(6, 4.5))
    r_um = result["r_edges"] * 1e6
    ax.plot(r_um, result["EE"], color=CATEGORICAL[0], lw=2)
    xmax = r_max_um if r_max_um else result["R"].max() * 1e6 * 0.5
    ax.set_xlim(0, xmax); ax.set_ylim(0, 1.05)
    ax.set_xlabel("radius (µm)"); ax.set_ylabel("encircled energy fraction")
    ax.set_title("Encircled energy at cornea")
    ax.grid(alpha=0.3)
    if target_P is not None:
        r_p = physics.r_for_EE(result["r_edges"], result["EE"], target_P / 100.0) * 1e6
        ax.axhline(target_P / 100.0, color="gray", linestyle=":", alpha=0.6)
        ax.axvline(r_p, color="gray", linestyle=":", alpha=0.6)
        ax.annotate(f"EE({target_P:g}%) = {r_p:.1f} µm", xy=(r_p, target_P / 100.0),
                    fontsize=8, xytext=(5, -12), textcoords="offset points")
    if effective_radii:
        for i, (label, r_m) in enumerate(effective_radii.items()):
            r_um_val = r_m * 1e6
            if r_um_val <= xmax:
                ax.axvline(r_um_val, color=_series_color(i + 1), linestyle="--", alpha=0.6)
    return fig


def fig_single_run(result, effective_radii=None, target_P=None):
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    plot_intensity(result, ax=axes[0, 0])
    plot_phase(result, ax=axes[0, 1])
    plot_radial_profile(result, effective_radii=effective_radii, ax=axes[1, 0])
    plot_encircled_energy(result, target_P=target_P, effective_radii=effective_radii, ax=axes[1, 1])
    cfg = result["cfg"]
    fig.suptitle(f"a_hole={cfg.a_hole * 1e6:.0f} µm | z={cfg.z * 1e3:.1f} mm | "
                 f"λ={cfg.wavelength * 1e9:.0f} nm | N_F={result['N_F']:.2f} ({result['regime']})")
    fig.tight_layout()
    return fig


def fig_compare_radial(results, labels, r_max_um=None):
    fig, ax = plt.subplots(figsize=(7, 5))
    xmax = 0
    for i, (r, label) in enumerate(zip(results, labels)):
        r_um = r["r_centers"] * 1e6
        ax.plot(r_um, r["I_radial"], color=_series_color(i), lw=2, label=label)
        xmax = max(xmax, r["R"].max() * 1e6 * 0.5)
    ax.set_xlim(0, r_max_um or xmax)
    ax.set_xlabel("radius (µm)"); ax.set_ylabel("azimuthally-averaged intensity")
    ax.set_title("Radial intensity -- comparison")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    return fig


def fig_compare_ee(results, labels, r_max_um=None):
    fig, ax = plt.subplots(figsize=(7, 5))
    xmax = 0
    for i, (r, label) in enumerate(zip(results, labels)):
        r_um = r["r_edges"] * 1e6
        ax.plot(r_um, r["EE"], color=_series_color(i), lw=2, label=label)
        xmax = max(xmax, r["R"].max() * 1e6 * 0.5)
    ax.set_xlim(0, r_max_um or xmax); ax.set_ylim(0, 1.05)
    ax.set_xlabel("radius (µm)"); ax.set_ylabel("encircled energy fraction")
    ax.set_title("Encircled energy -- comparison")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    return fig


def fig_compare_bar(labels, values, ylabel):
    fig, ax = plt.subplots(figsize=(max(5, 0.8 * len(labels)), 4.5))
    colors = [_series_color(i) for i in range(len(labels))]
    ax.bar(labels, values, color=colors)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=30)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    return fig


def fig_radius_vs_z(df, radius_col, wavelength_nm, ax=None):
    fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=(7, 5))
    sub = df[np.isclose(df["wavelength_nm"], wavelength_nm)]
    diam_values = sorted(sub["a_hole_um"].unique())
    for i, d in enumerate(diam_values):
        g = sub[np.isclose(sub["a_hole_um"], d)].sort_values("z_gap_mm")
        ax.plot(g["z_gap_mm"], g[radius_col], "o-", color=_series_color(i),
                 markersize=4, label=f"{d:.0f} µm")
    ax.set_xlabel("propagation distance z (mm)")
    ax.set_ylabel(radius_col)
    ax.set_title(f"{radius_col} vs propagation distance (λ={wavelength_nm:.0f} nm)")
    ax.legend(title="aperture diameter", fontsize=8)
    ax.grid(alpha=0.3)
    return fig


def fig_radius_vs_diameter(df, radius_col, wavelength_nm, ax=None):
    fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=(7, 5))
    sub = df[np.isclose(df["wavelength_nm"], wavelength_nm)]
    gap_values = sorted(sub["z_gap_mm"].unique())
    for i, z in enumerate(gap_values):
        g = sub[np.isclose(sub["z_gap_mm"], z)].sort_values("a_hole_um")
        ax.plot(g["a_hole_um"], g[radius_col], "o-", color=_series_color(i),
                 markersize=4, label=f"{z:.1f} mm")
    ax.set_xlabel("aperture diameter (µm)")
    ax.set_ylabel(radius_col)
    ax.set_title(f"{radius_col} vs aperture diameter (λ={wavelength_nm:.0f} nm)")
    ax.legend(title="propagation distance", fontsize=8)
    ax.grid(alpha=0.3)
    return fig


def fig_heatmap(df, radius_col, wavelength_nm, ax=None):
    fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=(7, 5.5))
    sub = df[np.isclose(df["wavelength_nm"], wavelength_nm)]
    pivot = sub.pivot_table(index="z_gap_mm", columns="a_hole_um", values=radius_col)
    im = ax.imshow(pivot.values, aspect="auto", origin="lower", cmap="viridis",
                   extent=[pivot.columns.min(), pivot.columns.max(),
                           pivot.index.min(), pivot.index.max()])
    ax.set_xlabel("aperture diameter (µm)"); ax.set_ylabel("propagation distance z (mm)")
    ax.set_title(f"{radius_col} heatmap (λ={wavelength_nm:.0f} nm)")
    fig.colorbar(im, ax=ax, label=radius_col)
    return fig
