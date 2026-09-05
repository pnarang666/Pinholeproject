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
from scipy.ndimage import map_coordinates

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

def choose_radial_bins(r_max, dx, target_bin_over_dx=2.5, min_bins=200, max_bins=2000):
    """
    Pick a radial-bin count for encircled_energy's histogram whose bin width is a safe
    multiple of the native pixel spacing dx. Too coarse (a fixed low bin count) loses
    resolution on r_EE(P); too fine (bin width < dx) makes some thin near-axis annuli
    contain zero actual samples, and the bincount fallback (count==0 -> 1) then silently
    reports those bins as intensity 0 -- a fabricated value, not a resolved one.
    target_bin_over_dx=2.5 keeps bins several pixels wide (safe from empty bins) while
    still much finer than a fixed low bin count. Encircled energy is a cumulative power
    integral, so a histogram sum-per-annulus is the natural (and correct) tool for it;
    see radial_profile() for why the *point-sampled* profile uses a different method.
    """
    target_bin_width = target_bin_over_dx * dx
    n_bins = int(r_max / target_bin_width)
    return int(np.clip(n_bins, min_bins, max_bins))


def radial_profile(I, R, dx, n_r=None, n_theta=360):
    """
    Azimuthally-averaged radial intensity profile, sampled by bilinear interpolation
    along n_theta angular rays at each of n_r radii spaced at the native pixel spacing
    dx -- not a histogram bin average.

    A histogram bin average over the annulus nearest r=0 (necessarily a few pixels wide)
    understates a sharp on-axis diffraction spike -- confirmed ~2.5x low here versus the
    true center-pixel value -- which then biases every peak-referenced radius (FWHM,
    1/e^2, custom threshold, equivalent-area) outward, since "100%" itself was measured
    too low. Interpolating along an actual radial ray instead gives r=0 exactly the true
    center-pixel intensity (every angle maps to the same point there), and every other
    radius a value at least as fine as the grid itself -- finer than any bin width that
    stays safely clear of the empty-bin problem in encircled_energy's histogram.

    Restricted to the circle inscribed in the simulation window (not out to the corner)
    so every angular ray at every sampled radius stays in-bounds; this is the region
    these diagnostics (and their plots) ever actually look at.

    PHYSICS_AUDIT.md item E3: this inscribed-circle domain (radius = dx*min(center,
    N-1-center), i.e. up to the nearest edge) is SMALLER than encircled_energy()'s own
    domain, which bins all the way out to R.max() -- the corner distance, ~1.41x
    further for a square grid. Threshold radii derived from this function (FWHM, 1/e^2,
    custom threshold) and r_EE(P) from encircled_energy() are therefore measured over
    different domains: r_EE(P) can (and for high P, does) draw on energy in the
    corner-only region this function never samples, while a threshold-crossing search
    here can never report a radius beyond the inscribed circle even if the true
    threshold crossing lies further out. This affects high percentiles most (they need
    more of the field's extent to reach the target fraction) and is also the least
    validated region of the grid (furthest from the well-sampled, well-checked center).
    """
    N = I.shape[0]
    center = N // 2
    r_max = dx * min(center, N - 1 - center)
    if n_r is None:
        n_r = int(r_max / dx) + 1
    r_centers = np.linspace(0, r_max, n_r)
    theta = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    R_grid, Theta_grid = np.meshgrid(r_centers, theta, indexing="ij")
    col = (R_grid * np.cos(Theta_grid)) / dx + center
    row = (R_grid * np.sin(Theta_grid)) / dx + center
    samples = map_coordinates(I, [row.ravel(), col.ravel()], order=1, mode="nearest")
    I_radial = samples.reshape(n_r, n_theta).mean(axis=1)
    return r_centers, I_radial


def encircled_energy(I, R, dx, n_bins=None):
    """
    Cumulative radial power profile: r_edges[i] is the outer radius of bin i, EE[i] is
    the fraction of GRID-CAPTURED power enclosed within r_edges[i], total_power is the
    grid-captured power itself.

    PHYSICS_AUDIT.md item E2: `total_power = cum_power[-1]` normalizes to whatever power
    is captured within the simulation grid at the time I is measured -- NOT to the power
    originally emitted at the aperture. If some fraction of energy has left the window
    (legitimately diffracted beyond a finite window, or suppressed by the ASM's own
    band-limiting -- see asm_propagate's band_info), EE(r) reports "P% of the power that
    remains," not "P% of the power that was emitted." The existing wraparound check
    (see run_validation's "Window size / wraparound" check, and
    pipeline_junction.validate_junction's divergence estimate) is PEAK-relative (it
    checks whether edge intensity is small compared to the peak), not an integrated
    energy accounting -- it can catch gross wraparound contamination but does not by
    itself bound how much real energy may have left the window. Callers wanting an
    integrated escape estimate should compare this function's own `total_power` against
    the field's known input power at an earlier, unclipped stage (e.g. the analytic
    aperture area at the pinhole plane) -- see phase2_retina.run_pipeline_point's
    `energy_escape_estimate` for a concrete instance of this comparison.

    PHYSICS_AUDIT.md item E3: bins all the way out to R.max() (the corner of a square
    grid, ~1.41x the inscribed-circle radius) -- a LARGER domain than radial_profile()'s
    inscribed-circle restriction. See radial_profile()'s docstring for the consequence:
    r_EE(P) and threshold-crossing radii (FWHM, 1/e^2, ...) are measured over different
    domains, which matters most at high P.
    """
    if n_bins is None:
        n_bins = choose_radial_bins(R.max(), dx)
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


def _parabolic_refine(r_centers, I_radial, i):
    """
    Sub-bin location of the true minimum near index i, via a quadratic fit through
    (i-1, i, i+1). A discrete "which raw bin is smallest" test flips between two
    near-tied adjacent bins on a sub-percent change in a swept parameter whenever the
    true continuous minimum is broad/shallow (confirmed: a bare bin-index minimum jumps
    ~7 um on a 1 um change in aperture diameter here). Fitting through the three raw
    samples gives a location that moves continuously with those samples instead of
    snapping to whichever bin happens to be marginally lower. Falls back to the raw bin
    center if the fit is degenerate or extrapolates outside the bracketing interval.
    """
    if i <= 0 or i >= len(I_radial) - 1:
        return r_centers[i]
    x0, x1, x2 = r_centers[i - 1], r_centers[i], r_centers[i + 1]
    y0, y1, y2 = I_radial[i - 1], I_radial[i], I_radial[i + 1]
    denom = y2 - 2 * y1 + y0
    if abs(denom) < 1e-12:
        return x1
    dx_local = x1 - x0
    x_vertex = x1 - 0.5 * dx_local * (y2 - y0) / denom
    if x_vertex < x0 or x_vertex > x2:
        return x1
    return x_vertex


def locate_threshold_crossing(r_centers, I_radial, frac_of_peak, confirm_samples=3,
                               prominence_frac=0.02, I_peak=None):
    """
    Walk outward from the radial profile's global maximum and stop at whichever comes
    first:

      (a) intensity drops below frac_of_peak * I_peak -- a genuine crossing, interpolated
          to sub-bin precision from the two bracketing (raw, unsmoothed) samples; or
      (b) a genuine local minimum -- confirmed by a rise of at least prominence_frac *
          I_peak over the next `confirm_samples` samples, so a sub-percent noise wiggle
          isn't mistaken for the start of the next ring -- reached before the profile
          ever crosses the threshold. This means the central lobe turns back up into the
          next Fresnel ring before reaching that threshold; the result is reported as a
          LOWER BOUND, not a crossing, and its radius is sub-bin refined (see
          _parabolic_refine) since the minimum itself is often broad and shallow.

    Why this and not "first sample below threshold": once two Fresnel rings sit close in
    brightness (common whenever N_F is O(1)-O(10)), a fixed intensity threshold is crossed
    multiple times as r increases, and different rings drift above/below that threshold on
    sub-percent changes in peak intensity as a parameter sweeps smoothly. Reporting the
    first crossing lets the algorithm hop between rings -- confirmed to jump >20 um from a
    <2% smooth change in aperture diameter. Restricting the outward search to stop at the
    first genuine local minimum keeps the reported radius locked to one physical feature
    (the central lobe), so it varies continuously with the sweep parameter instead of
    hopping between whichever ring happens to be nearest the threshold at that instant.

    This does NOT and cannot smooth over the profile's global maximum itself relocating
    (a real hot-spot <-> hot-ring transition as N_F crosses certain values) -- that is a
    genuine physical regime change, already surfaced separately by the "central-peak
    assumption" validation check, not an artifact this function is responsible for.

    Returns a dict: radius (m), mode ("crossed" | "local_min_above_threshold" |
    "never_crossed"), stop_index, and crossing_count (number of threshold crossings across
    the FULL outward profile -- a direct measure of how much ring-competition risk exists
    even after restricting the search, useful for a validation warning).
    """
    idx_peak = int(np.argmax(I_radial))
    if I_peak is None:
        # Fallback only: the azimuthally-binned profile's own max, coarser than the raw
        # grid. Callers with access to the raw 2D intensity should pass its true max here
        # -- binning smooths a sharp on-axis peak down, which would understate 100% and
        # bias every threshold-based radius outward.
        I_peak = I_radial[idx_peak]
    n = len(I_radial)

    if I_peak <= 0:
        return {"radius": r_centers[idx_peak], "mode": "never_crossed",
                "stop_index": idx_peak, "crossing_count": 0}

    threshold = I_peak * frac_of_peak
    prominence = prominence_frac * I_peak
    tail = I_radial[idx_peak:]
    crossing_count = int(np.sum(np.diff((tail < threshold).astype(int)) != 0))

    i = idx_peak
    while i < n - 1:
        if I_radial[i + 1] < threshold:
            r0, r1 = r_centers[i], r_centers[i + 1]
            I0, I1 = I_radial[i], I_radial[i + 1]
            frac = (I0 - threshold) / (I0 - I1)
            radius = r0 + frac * (r1 - r0)
            return {"radius": radius, "mode": "crossed", "stop_index": i + 1,
                    "crossing_count": crossing_count}

        if I_radial[i + 1] > I_radial[i]:
            look_ahead = I_radial[i + 1: i + 1 + confirm_samples]
            if len(look_ahead) > 0 and (look_ahead.max() - I_radial[i]) >= prominence:
                radius = _parabolic_refine(r_centers, I_radial, i)
                return {"radius": radius, "mode": "local_min_above_threshold",
                        "stop_index": i, "crossing_count": crossing_count}
        i += 1

    return {"radius": r_centers[-1], "mode": "never_crossed", "stop_index": n - 1,
            "crossing_count": crossing_count}


def fwhm_radius(r_centers, I_radial, I_peak=None):
    return locate_threshold_crossing(r_centers, I_radial, 0.5, I_peak=I_peak)["radius"]


def one_over_e2_radius(r_centers, I_radial, I_peak=None):
    return locate_threshold_crossing(r_centers, I_radial, TWO_OVER_E_SQUARED, I_peak=I_peak)["radius"]


def custom_threshold_radius(r_centers, I_radial, frac_of_peak, I_peak=None):
    return locate_threshold_crossing(r_centers, I_radial, frac_of_peak, I_peak=I_peak)["radius"]


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
        return fwhm_radius(run["r_centers"], run["I_radial"], I_peak=run["I_peak"])
    if definition == "1/e2":
        return one_over_e2_radius(run["r_centers"], run["I_radial"], I_peak=run["I_peak"])
    if definition == "threshold":
        return custom_threshold_radius(run["r_centers"], run["I_radial"], threshold_percent / 100.0,
                                        I_peak=run["I_peak"])
    if definition == "equivalent_area":
        return equivalent_area_radius(run["total_power"], run["I_peak"])
    raise ValueError(f"unknown effective radius definition: {definition!r}")


def effective_radius_detail(run, definition, ee_percent=80.0, threshold_percent=10.0):
    """
    Like effective_radius(), but for the threshold-crossing definitions (fwhm, 1/e2,
    threshold) also returns the crossing mode and crossing count, so a lower-bound or
    ring-ambiguous reading is never exported or displayed as an unqualified number.
    """
    r_centers, I_radial = run["r_centers"], run["I_radial"]
    I_peak = run["I_peak"]
    if definition == "fwhm":
        return locate_threshold_crossing(r_centers, I_radial, 0.5, I_peak=I_peak)
    if definition == "1/e2":
        return locate_threshold_crossing(r_centers, I_radial, TWO_OVER_E_SQUARED, I_peak=I_peak)
    if definition == "threshold":
        return locate_threshold_crossing(r_centers, I_radial, threshold_percent / 100.0, I_peak=I_peak)
    return {"radius": effective_radius(run, definition, ee_percent, threshold_percent),
            "mode": "n/a", "crossing_count": 0}


# ---------------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------------

def run_validation(cfg, I, R, dx, band_info, energy_error, r_centers, I_radial, I_peak):
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

    fwhm_info = locate_threshold_crossing(r_centers, I_radial, 0.5, I_peak=I_peak)
    if fwhm_info["mode"] == "crossed":
        extra = (f" {fwhm_info['crossing_count']} half-max crossings total in this profile -- "
                 f"a further ring also nears the half-max level; the search below stopped at "
                 f"the first local minimum so FWHM stays well-defined, but treat close calls "
                 f"with care." if fwhm_info["crossing_count"] > 1 else "")
        checks.append({
            "name": "Central-lobe half-max crossing (FWHM well-posedness)",
            "ok": True,
            "detail": f"FWHM crosses half-max cleanly at r={fwhm_info['radius'] * 1e6:.2f} um." + extra,
        })
    else:
        checks.append({
            "name": "Central-lobe half-max crossing (FWHM well-posedness)",
            "ok": False,
            "detail": (f"the central lobe reaches a local minimum at r={fwhm_info['radius'] * 1e6:.2f} um "
                       f"without ever dropping to half its peak value -- it turns back up into the "
                       f"next Fresnel ring first. Reported FWHM is a LOWER BOUND "
                       f"(>= {fwhm_info['radius'] * 1e6:.2f} um), not a clean crossing; "
                       f"prefer r_EE(P) or the second-moment radius here."),
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
    r_centers, I_radial = radial_profile(I, R, dx=dx)

    center = cfg.N // 2
    I_onaxis = float(I[center, center])
    # radial_profile() samples by interpolation, not histogram binning, so its r=0 value
    # already equals I_onaxis exactly when the peak is on-axis (every angle maps to the
    # same point there) -- no separate raw-grid peak needed to avoid understating "100%".
    I_peak = float(I_radial.max())

    N_F = fresnel_number(cfg.a_hole, cfg.wavelength, cfg.z)
    regime = fresnel_regime(N_F)

    validation = run_validation(cfg, I, R, dx, band_info, energy_error, r_centers, I_radial, I_peak)

    return {
        "cfg": cfg,
        "U0": U0, "Uz": Uz, "I": I, "phase": phase, "R": R, "dx": dx,
        "r_edges": r_edges, "EE": EE, "total_power": total_power,
        "r_centers": r_centers, "I_radial": I_radial, "radial_bins_used": len(r_centers),
        "I_peak": I_peak, "I_onaxis": I_onaxis,
        "N_F": N_F, "regime": regime,
        "energy_conservation_error": energy_error,
        "band_info": band_info,
        "validation": validation,
    }
