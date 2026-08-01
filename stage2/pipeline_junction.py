"""
The ONLY bridge between stage1_v2's gap-stage code and stage2's retina-stage code.

phase2_retina.py and the main sweep must import from THIS module, never from
stage1_v2/physics.py directly -- this module re-exports exactly the v2 primitives
stage2 needs (asm_propagate, make_grid, encircled_energy, r_for_EE, ...) so the import
boundary is enforced by construction, not by convention.
"""

import os
import sys

import numpy as np

_STAGE1_V2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stage1_v2"))
if _STAGE1_V2_DIR not in sys.path:
    sys.path.insert(0, _STAGE1_V2_DIR)

import physics as _v2_physics  # noqa: E402  (path must be set up first)

# Re-exported v2 primitives -- stage2 code calls these via `junction.<name>`, never via
# a direct `import physics`.
asm_propagate = _v2_physics.asm_propagate
asm_transfer_function = _v2_physics.asm_transfer_function
circular_aperture = _v2_physics.circular_aperture
make_grid = _v2_physics.make_grid
encircled_energy = _v2_physics.encircled_energy
r_for_EE = _v2_physics.r_for_EE
fresnel_number = _v2_physics.fresnel_number
fresnel_regime = _v2_physics.fresnel_regime
second_moment_radius = _v2_physics.second_moment_radius
RunConfig = _v2_physics.RunConfig


def run_gap_to_cornea(a_hole, wavelength, d_gap, grid_N, window_L_mm):
    """Thin wrapper around v2's existing ASM call -- no propagation logic of its own."""
    N = grid_N
    L = window_L_mm * 1e-3
    U0, R, dx = circular_aperture(N, L, a_hole)
    U_cornea, band_info = asm_propagate(U0, dx, wavelength, d_gap, L=L, band_limit=True)
    return {
        "U_cornea": U_cornea, "dx": dx, "N": N, "wavelength": wavelength,
        "a_hole": a_hole, "d_gap": d_gap, "grid_N": grid_N, "window_L_mm": window_L_mm,
        "band_info": band_info,
    }


def _fail(reason, suggested_grid_N):
    return {"ok": False, "reason": reason, "suggested_grid_N": suggested_grid_N}


def _suggest_scaled_grid(N, L, v_r_target, target_z_over_L=2.0):
    """
    The Matsushima band limit fx_limit = 1/(lambda*sqrt((2z/L)^2+1)) widens with a
    LARGER window L, not a finer grid_N at fixed L -- N alone doesn't move it. So the
    honest fix when the band-limit or wraparound check fails is usually "grow the
    window", and suggested_grid_N here is "what N would keep today's pixel resolution
    (dx) if the window also grows enough to bring z/L back down near the ratio
    (d_gap=12mm)/(L=6mm)=2 that stage1_v2's own validated gap-stage configuration uses."
    Returns (L_required, N_required); callers fold L_required into the reason text since
    the return schema only carries suggested_grid_N.
    """
    L_required = max(L, v_r_target / target_z_over_L)
    N_required = int(np.ceil(N * (L_required / L)))
    return L_required, N_required


def validate_junction(cornea_result, v_r_target, wavelength):
    """
    Gate before phase 2 ever touches the cornea field. Checks, in order:
      1. finite / non-NaN / non-zero energy on the cornea field itself (cheapest).
      2. Nyquist / Matsushima band-limit AT v_r_target -- typically LONGER than
         v2's validated 12-15mm gap range, so this must not assume that grid/window
         choice is still adequate; it re-propagates a diagnostic copy at v_r_target to
         measure it directly, using v2's own asm_propagate.
      3. window-size / wraparound risk at v_r_target, via a conservative (deliberately
         pessimistic) free-space divergence estimate from the cornea field's own
         second-moment radius -- the lens hasn't been applied yet at this point in the
         pipeline, and a converging lens can only narrow the beam relative to this
         estimate, so ignoring the lens here is the safe direction for a pre-check, not
         a claim that this is what the focused beam will actually look like.

    Returns {'ok': True, 'reason': None, 'suggested_grid_N': None} on success, or
    {'ok': False, 'reason': str, 'suggested_grid_N': int} on the first failing check.
    """
    U_cornea = cornea_result["U_cornea"]
    dx = cornea_result["dx"]
    N = cornea_result["N"]
    a_hole = cornea_result["a_hole"]
    L = N * dx

    if not np.all(np.isfinite(U_cornea)):
        return _fail("cornea field contains non-finite values (NaN/Inf)", None)

    energy = float(np.sum(np.abs(U_cornea) ** 2) * dx ** 2)
    if not (energy > 0):
        return _fail("cornea field carries zero energy", None)

    _, band_info = asm_propagate(U_cornea, dx, wavelength, v_r_target, L=L, band_limit=True)
    frac_suppressed = band_info["fraction_energy_suppressed"]
    if frac_suppressed > 0.05:
        L_required, N_required = _suggest_scaled_grid(N, L, v_r_target)
        return _fail(
            f"{frac_suppressed * 100:.2f}% of the propagating spectrum's energy lies "
            f"beyond the Matsushima band limit at v_r={v_r_target * 1e3:.2f} mm "
            f"(fx_limit={band_info['fx_limit']:.3e} 1/m) -- this window/grid "
            f"under-resolves propagation this far. Widening window_L_mm to "
            f"~{L_required * 1e3:.1f} mm (at proportionally finer grid_N) is likely "
            f"needed at least as much as raising grid_N alone.",
            N_required,
        )

    _, _, R, _ = make_grid(N, L)
    I_cornea = np.abs(U_cornea) ** 2
    w_cornea = second_moment_radius(I_cornea, R, dx)
    # FIXED: wavelength/(pi*w) is the Gaussian-beam (M^2=1) MINIMUM-divergence formula --
    # a LOWER bound on real divergence, not conservative on its own as originally labeled.
    # A hard-edged circular aperture's Airy-like field has M^2>1, so it diverges at least
    # this fast, typically faster. margin_factor is a documented, visible first-pass
    # inflation to compensate -- not a validated bound. If this check becomes
    # load-bearing, replace it with the field's own measured divergence (propagate a
    # diagnostic step and remeasure second_moment_radius) instead of a fixed multiplier.
    margin_factor = 3.0
    divergence_half_angle = (margin_factor * wavelength / (np.pi * w_cornea)) if w_cornea > 0 else 0.0
    predicted_radius = w_cornea + v_r_target * divergence_half_angle
    safety_margin = 0.4
    if predicted_radius > safety_margin * (L / 2.0):
        L_required, N_required = _suggest_scaled_grid(N, L, v_r_target)
        return _fail(
            f"predicted beam radius at v_r={v_r_target * 1e3:.2f} mm "
            f"(~{predicted_radius * 1e6:.1f} um, conservative unfocused estimate, "
            f"lens not yet applied) exceeds {safety_margin:.0%} of the half-window "
            f"({0.5 * L * 1e6:.1f} um) -- risk of wraparound. Increase window_L_mm "
            f"to ~{L_required * 1e3:.1f} mm.",
            N_required,
        )

    return {"ok": True, "reason": None, "suggested_grid_N": None}
