"""
Stage 1 core physics: Plane wave -> Circular Pinhole -> Exact Scalar Angular Spectrum
Method -> Corneal Plane.

Scope boundary (by design, not oversight): this module stops at the cornea. It never
touches the eye lens, vitreous, retina, or image formation -- those belong to a later
stage that would consume the complex field U(x,y,z) this module returns. It also never
estimates a single "best pinhole" -- it only characterizes the field at a chosen plane.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

TWO_OVER_E_SQUARED = np.exp(-2.0)


# ---------------------------------------------------------------------------------
# Grid / aperture
# ---------------------------------------------------------------------------------

def make_grid(N, L):
    dx = L / N
    x = (np.arange(N) - N // 2) * dx
    X, Y = np.meshgrid(x, x, indexing="xy")
    R = np.sqrt(X ** 2 + Y ** 2)
    return X, Y, R, dx


def circular_aperture(N, L, diameter):
    X, Y, R, dx = make_grid(N, L)
    U0 = (R <= diameter / 2.0).astype(np.complex128)
    return U0, R, dx


# ---------------------------------------------------------------------------------
# Exact scalar Angular Spectrum Method, with optional Matsushima band-limiting
# ---------------------------------------------------------------------------------

def _frequency_grid(N, dx):
    fx = np.fft.fftfreq(N, d=dx)
    FX, FY = np.meshgrid(fx, fx, indexing="xy")
    return FX, FY


def asm_transfer_function(N, dx, wavelength, z, L, band_limit=True):
    """
    H(fx,fy) = exp(i k z sqrt(1 - (lambda fx)^2 - (lambda fy)^2)) on propagating orders,
    zero elsewhere (evanescent cutoff) -- the exact scalar ASM kernel, no paraxial term.

    When band_limit is True, also zeros propagating orders beyond the Matsushima &
    Shimobaba (2009) elliptical band limit f_limit = 1 / (lambda*sqrt((2*z/L)^2+1)).
    Those orders are the ones whose fringe spacing aliases against the frequency-grid
    spacing 1/L; suppressing them removes a sampling artifact, not real physics -- it is
    still the exact ASM kernel, just numerically stabilized. Returns the propagating mask
    and the (propagating & suppressed-by-band-limit) mask separately so callers can report
    what fraction of the *physical* spectrum, not the evanescent tail, was affected.
    """
    FX, FY = _frequency_grid(N, dx)
    freq_sq = FX ** 2 + FY ** 2
    propagating = freq_sq <= (1.0 / wavelength ** 2)

    kz = np.zeros_like(freq_sq)
    kz[propagating] = np.sqrt(1.0 - (wavelength ** 2) * freq_sq[propagating])
    k = 2 * np.pi / wavelength

    kept = propagating
    band_suppressed = np.zeros_like(propagating)
    fx_limit = None
    if band_limit:
        du = 1.0 / L
        fx_limit = 1.0 / (wavelength * np.sqrt((2 * du * z) ** 2 + 1.0))
        within_band = (FX / fx_limit) ** 2 + (FY / fx_limit) ** 2 <= 1.0
        kept = propagating & within_band
        band_suppressed = propagating & ~within_band

    H = np.zeros((N, N), dtype=np.complex128)
    H[kept] = np.exp(1j * k * z * kz[kept])
    return H, propagating, band_suppressed, fx_limit


def asm_propagate(U0, dx, wavelength, z, L=None, band_limit=True, precomputed=None):
    """Returns (U(x,y,z), band_info). band_info reports energy-weighted band-limit impact."""
    N = U0.shape[0]
    if L is None:
        L = N * dx
    if precomputed is None:
        H, propagating, band_suppressed, fx_limit = asm_transfer_function(N, dx, wavelength, z, L, band_limit)
    else:
        H, propagating, band_suppressed, fx_limit = precomputed

    U0_hat = np.fft.fft2(U0)
    propagating_power = np.sum(np.abs(U0_hat[propagating]) ** 2)
    suppressed_power = np.sum(np.abs(U0_hat[band_suppressed]) ** 2) if band_limit else 0.0
    band_info = {
        "band_limit_applied": band_limit,
        "fx_limit": fx_limit,
        "fraction_energy_suppressed": (suppressed_power / propagating_power) if propagating_power > 0 else 0.0,
    }
    Uz = np.fft.ifft2(U0_hat * H)
    return Uz, band_info


def precompute_transfer_function(N, dx, wavelength, z, L, band_limit=True):
    """Same (N, dx, wavelength, z, L, band_limit) -> reusable across an aperture-diameter sweep."""
    return asm_transfer_function(N, dx, wavelength, z, L, band_limit)


# ---------------------------------------------------------------------------------
# Fresnel number / regime
# ---------------------------------------------------------------------------------

def fresnel_number(a_hole, wavelength, z):
    radius = a_hole / 2.0
    return radius ** 2 / (wavelength * z)


def fresnel_regime(N_F):
    if N_F < 0.1:
        return "Fraunhofer"
    if N_F <= 10:
        return "Transition"
    return "Strong Fresnel"


# ---------------------------------------------------------------------------------
# Radial profile / encircled energy
# ---------------------------------------------------------------------------------

def radial_profile(I, R, n_bins=300):
    r_max = R.max()
    bins = np.linspace(0, r_max, n_bins + 1)
    idx = np.clip(np.digitize(R.ravel(), bins) - 1, 0, n_bins - 1)
    sums = np.bincount(idx, weights=I.ravel(), minlength=n_bins)
    counts = np.bincount(idx, minlength=n_bins)
    counts[counts == 0] = 1
    r_centers = 0.5 * (bins[:-1] + bins[1:])
    return r_centers, sums / counts


def encircled_energy(I, R, dx, n_bins=300):
    r_max = R.max()
    bins = np.linspace(0, r_max, n_bins + 1)
    idx = np.clip(np.digitize(R.ravel(), bins) - 1, 0, n_bins - 1)
    power_per_bin = np.bincount(idx, weights=I.ravel(), minlength=n_bins) * dx ** 2
    cum_power = np.cumsum(power_per_bin)
    total_power = cum_power[-1]
    EE = cum_power / total_power if total_power > 0 else cum_power
    r_edges = bins[1:]
    return r_edges, EE, total_power


def r_for_EE(r_edges, EE, target_P):
    """Invert EE(r) for the radius enclosing fraction target_P in [0, 1]. Never hardcoded."""
    if target_P >= EE[-1]:
        return r_edges[-1]
    idx = np.searchsorted(EE, target_P)
    if idx == 0:
        return r_edges[0]
    r0, r1 = r_edges[idx - 1], r_edges[idx]
    e0, e1 = EE[idx - 1], EE[idx]
    if e1 == e0:
        return r0
    frac = (target_P - e0) / (e1 - e0)
    return r0 + frac * (r1 - r0)


# ---------------------------------------------------------------------------------
# Effective corneal illumination radius -- multiple selectable definitions.
# "Effective aperture" is deliberately avoided as a label (see module docstring context);
# callers should always show the definition name alongside the number.
# ---------------------------------------------------------------------------------

def second_moment_radius(I, R, dx):
    total = np.sum(I) * dx ** 2
    if total <= 0:
        return 0.0
    return float(np.sqrt(np.sum(I * R ** 2) * dx ** 2 / total))


def _outward_threshold_radius(r_centers, I_radial, frac_of_peak):
    """
    Locate the radial-profile's global maximum (not necessarily at r=0 -- Fresnel ringing
    can put the brightest ring near the geometric shadow edge, not the axis) and walk
    OUTWARD from there for the first radius where intensity drops below frac_of_peak of
    that maximum. Returns (radius, r_peak, I_peak) so callers can flag an off-axis peak.
    """
    idx_peak = int(np.argmax(I_radial))
    I_peak = I_radial[idx_peak]
    r_peak = r_centers[idx_peak]
    if I_peak <= 0:
        return 0.0, r_peak, I_peak
    threshold = I_peak * frac_of_peak
    tail = I_radial[idx_peak:]
    below = tail < threshold
    if not below.any():
        return r_centers[-1], r_peak, I_peak
    rel_idx = int(np.argmax(below))
    return r_centers[idx_peak + rel_idx], r_peak, I_peak


def fwhm_radius(r_centers, I_radial):
    r, _, _ = _outward_threshold_radius(r_centers, I_radial, 0.5)
    return r


def one_over_e2_radius(r_centers, I_radial):
    r, _, _ = _outward_threshold_radius(r_centers, I_radial, TWO_OVER_E_SQUARED)
    return r


def custom_threshold_radius(r_centers, I_radial, frac_of_peak):
    r, _, _ = _outward_threshold_radius(r_centers, I_radial, frac_of_peak)
    return r


def equivalent_area_radius(total_power, I_peak):
    """Radius of a uniform circular aperture with peak intensity I_peak carrying the same power."""
    if I_peak <= 0:
        return 0.0
    return float(np.sqrt(total_power / (np.pi * I_peak)))


EFFECTIVE_RADIUS_LABELS = {
    "EE": "Encircled-energy radius r_EE(P)",
    "second_moment": "Second-moment radius",
    "fwhm": "FWHM radius (outward from brightest ring)",
    "1/e2": "1/e² radius",
    "threshold": "Custom intensity-threshold radius",
    "equivalent_area": "Equivalent-area radius",
}


def effective_radius(run, definition, ee_percent=80.0, threshold_percent=10.0):
    if definition == "EE":
        return r_for_EE(run["r_edges"], run["EE"], ee_percent / 100.0)
    if definition == "second_moment":
        return second_moment_radius(run["I"], run["R"], run["dx"])
    if definition == "fwhm":
        return fwhm_radius(run["r_centers"], run["I_radial"])
    if definition == "1/e2":
        return one_over_e2_radius(run["r_centers"], run["I_radial"])
    if definition == "threshold":
        return custom_threshold_radius(run["r_centers"], run["I_radial"], threshold_percent / 100.0)
    if definition == "equivalent_area":
        return equivalent_area_radius(run["total_power"], run["I_peak"])
    raise ValueError(f"unknown effective radius definition: {definition!r}")


# ---------------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------------

def run_validation(cfg, I, R, dx, band_info, energy_error, r_centers, I_radial):
    checks = []

    checks.append({
        "name": "Energy conservation",
        "ok": energy_error < 1e-3,
        "detail": f"|P_out - P_in| / P_in = {energy_error:.2e} (want < 1e-3)",
    })

    edge_band = np.concatenate([I[0, :], I[-1, :], I[:, 0], I[:, -1]])
    peak = I.max() if I.max() > 0 else 1.0
    edge_fraction = float(edge_band.max() / peak)
    window_ratio = cfg.L / cfg.a_hole
    checks.append({
        "name": "Window size / wraparound",
        "ok": edge_fraction < 1e-3 and window_ratio > 3,
        "detail": (f"L / a_hole = {window_ratio:.1f} (want > ~3-4); "
                   f"max edge intensity / peak = {edge_fraction:.2e} (want << 1)"),
    })

    pixels_across = cfg.a_hole / dx
    checks.append({
        "name": "Aperture sampling (Nyquist on the aperture edge)",
        "ok": pixels_across >= 20,
        "detail": f"{pixels_across:.0f} grid points across the aperture diameter (want >= 20)",
    })

    if band_info["fx_limit"] is not None:
        frac = band_info["fraction_energy_suppressed"]
        checks.append({
            "name": "Angular-spectrum band limit (Matsushima anti-aliasing)",
            "ok": frac < 0.05,
            "detail": (f"{frac * 100:.2f}% of the propagating spectrum's energy lay beyond "
                       f"the anti-aliasing band limit (f_limit={band_info['fx_limit']:.3e} 1/m) "
                       f"and was suppressed; a large fraction means this grid/window "
                       f"under-resolves this propagation distance -- increase N or the window."),
        })

    idx_peak = int(np.argmax(I_radial))
    r_peak = r_centers[idx_peak]
    on_axis = r_peak < 3 * dx
    checks.append({
        "name": "Central-peak assumption (for FWHM / 1/e² / threshold radii)",
        "ok": on_axis,
        "detail": (f"radial-profile maximum sits at r={r_peak * 1e6:.2f} um -- " +
                   ("near the optical axis, as those definitions assume."
                    if on_axis else
                    "OFF the optical axis (Fresnel ringing puts the brightest ring away "
                    "from the center). FWHM/1/e²/threshold radii are measured outward "
                    "from that ring, not from center, and may not read as a simple beam "
                    "radius here -- prefer r_EE(P) or the second-moment radius as the "
                    "primary metric in this regime.")),
    })

    return checks


# ---------------------------------------------------------------------------------
# Single-configuration run
# ---------------------------------------------------------------------------------

@dataclass
class RunConfig:
    a_hole: float          # aperture diameter, m
    wavelength: float      # m
    z: float               # propagation distance, pinhole -> cornea, m
    N: int = 2048
    L: float = 6e-3
    band_limit: bool = True


def run_configuration(cfg: RunConfig, precomputed: Optional[tuple] = None):
    U0, R, dx = circular_aperture(cfg.N, cfg.L, cfg.a_hole)
    input_power = np.sum(np.abs(U0) ** 2) * dx ** 2

    Uz, band_info = asm_propagate(U0, dx, cfg.wavelength, cfg.z, L=cfg.L,
                                   band_limit=cfg.band_limit, precomputed=precomputed)
    I = np.abs(Uz) ** 2
    phase = np.angle(Uz)

    output_power = np.sum(I) * dx ** 2
    energy_error = abs(output_power - input_power) / input_power if input_power > 0 else np.nan

    r_edges, EE, total_power = encircled_energy(I, R, dx)
    r_centers, I_radial = radial_profile(I, R)

    center = cfg.N // 2
    I_onaxis = float(I[center, center])
    I_peak = float(I_radial.max())

    N_F = fresnel_number(cfg.a_hole, cfg.wavelength, cfg.z)
    regime = fresnel_regime(N_F)

    validation = run_validation(cfg, I, R, dx, band_info, energy_error, r_centers, I_radial)

    return {
        "cfg": cfg,
        "U0": U0, "Uz": Uz, "I": I, "phase": phase, "R": R, "dx": dx,
        "r_edges": r_edges, "EE": EE, "total_power": total_power,
        "r_centers": r_centers, "I_radial": I_radial,
        "I_peak": I_peak, "I_onaxis": I_onaxis,
        "N_F": N_F, "regime": regime,
        "energy_conservation_error": energy_error,
        "band_info": band_info,
        "validation": validation,
    }
