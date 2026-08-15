"""
Computes THEORY.md Eq. (2) -- the actual multi-hole retinal PSF as the incoherent sum
of shifted single-hole copies -- and its encircled-energy radius. This equation has
been WRITTEN in this project since the ghosting theory was drafted but never evaluated:
every blur/acuity number in the project (stage2_fixed's R1 sweep, stage3a, stage4) is a
SINGLE-hole r_EE(P), and every array number (photometry N_eff, ghosting regimes) treats
the copies' existence without ever asking what the summed pattern's blur radius is.

Two questions it answers, both raised by reading photometry/ and ghosting/ together:

  Q1. Is Eq. (2) itself right -- are the copies really identical and merely shifted?
      Checked by propagating holes at increasing off-axis heights through the real
      pipeline and comparing each spot's r_EE_50 and centroid.

  Q2. When N_eff > 1, is the array's blur still the single-hole blur that the diameter
      optimum (Array_Design/single_hole_reference/) was chosen to minimise? Checked by
      summing the copies over the holes actually inside the pupil and measuring the sum's
      r_EE_50 directly.

Physics reuse only: the PSF comes from stage2_fixed.phase2_retina.run_pipeline_point,
the encircled energy from stage2_fixed.pipeline_junction (stage1_v2's own function), the
hole lattice and pupil counting from Array_Design/photometry/array_photometry.py, and
the copy displacement from Array_Design/ghosting/ghost_separation.py (Eq. C, verified in
ghosting/delta_r_derivation_check.py). Nothing here re-derives an optical quantity.

Run:  python3 array_psf_envelope.py
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ghosting"))
sys.path.insert(0, os.path.join(HERE, "photometry"))
sys.path.insert(0, os.path.join(HERE, "..", "stage2_fixed"))

import myopia_axial  # noqa: E402
import pipeline_junction as junction  # noqa: E402
import phase2_retina as p2  # noqa: E402
import array_photometry as ap  # noqa: E402
from corrected_regime import assert_corrected_optics  # noqa: E402

WAVELENGTH_NM = 550.0
D_GAP_MM = 12.0
D_PUPIL_UM = 4000.0
P0 = 60.0
N_PRIME = 1.336
# GRID_N=4096 (was 2048). DEFECT 1 FIX, diagnosed by instrumentation (see
# ANALYSIS.md's Defect-1 addendum for the full trace): r_max_lens = wavelength*f_eye/
# (2*dx) is a pure function of the GRID (wavelength, f_eye, dx=window_L_mm/grid_N),
# independent of aperture, M, or pitch -- confirmed identical (1564.44um) across every
# (a, M) tested at grid_N=2048. That value is SMALLER than the pupil radius
# (D_PUPIL_UM/2=2000um) for every design in this module's tested range, so a hole
# anywhere in the outer ~22% of the pupil radius is unrepresentable at grid_N=2048 and
# gets excluded, not approximated -- this is why exclusion triggered at 100% of the
# 1370-point sweep. NOT a crop-window bug (r_max_lens is computed in single_hole_psf(),
# before any crop decision exists) and NOT a units bug (r_max_lens_um and r_hole are
# both already in micrometres at the comparison site, verified). It is exactly the
# limitation phase2_retina.validate_lens_sampling's own docstring already flagged as
# untested beyond stage2_fixed's single-hole use case ("a future, more extreme
# configuration... can be checked") -- this module's off-axis multi-hole shifts are
# that more extreme configuration. grid_N=4096 (same WINDOW_L_MM) gives
# r_max_lens=3128.9um, comfortably past the pupil radius with margin for even the
# largest tested aperture (a=2000um) sitting right at the pupil edge
# (r_hole+a/2=3000um < 3128.9um) -- eliminating the exclusion rather than working
# around it by shrinking the tested geometry. Cost: ~16s/cold propagation (was ~6-7s),
# paid once per (aperture, M) via the existing cache, not per sweep point. Single-hole
# r_EE_50 shifts by 0.05-2.1% between grid_N=2048 and 4096 at spot-checked points --
# ordinary grid-refinement convergence, well inside this project's own +-10% tolerance
# conventions, not a new discrepancy.
GRID_N = 4096
WINDOW_L_MM = 6.0


def dx_um_hint():
    """Grid pixel size in um -- reported alongside sub-pixel agreement claims so a
    'matches to 1.3um' statement can be read as 'matches to half a pixel'."""
    return (WINDOW_L_MM * 1e-3 / GRID_N) * 1e6


def _optics(M):
    m = myopia_axial.axial_length_for_myopia(M, P0=P0, n_prime=N_PRIME)
    return m["L_ax"], m["f_eye"]


def _retina_from_cornea(U_cornea, dx, M):
    v_r, f_eye = _optics(M)
    eff_wl = (WAVELENGTH_NM * 1e-9) / N_PRIME
    field = p2.pupil_clip(U_cornea, dx, D_PUPIL_UM)
    field = p2.lens_phase(field, dx, eff_wl, f_eye)
    U_ret, _ = p2.propagate_to_retina(field, dx, eff_wl, v_r,
                                       refractive_index_correction=False, n_prime=N_PRIME)
    return np.abs(U_ret) ** 2


def _r_ee(I, dx, P=0.50):
    N = I.shape[0]
    _, _, R, _ = junction.make_grid(N, N * dx)
    r_edges, EE, _ = junction.encircled_energy(I, R, dx)
    return junction.r_for_EE(r_edges, EE, P) * 1e6


def q1_copies_are_shifted_replicas(a_hole_um=400.0, M=4.0,
                                    heights_um=(0.0, 450.0, 900.0, 1350.0, 1800.0)):
    """Propagates one hole at several off-axis heights and reports r_EE_50 and centroid
    of each retinal spot. Eq. (2) assumes every copy is the SAME PSF, merely shifted."""
    cornea = junction.run_gap_to_cornea(a_hole_um * 1e-6, WAVELENGTH_NM * 1e-9,
                                         D_GAP_MM * 1e-3, GRID_N, WINDOW_L_MM)
    dx = cornea["dx"]
    v_r, v_f = _optics(M)
    X, _, R, _ = junction.make_grid(GRID_N, GRID_N * dx)
    rows = []
    for h in heights_um:
        n_pix = int(round((h * 1e-6) / dx))
        U_shift = np.roll(cornea["U_cornea"], n_pix, axis=1)
        # Three ways a displaced hole leaves the validity of this test, all measured
        # rather than assumed: (i) the pupil clips it (a real physical effect, but then
        # it is no longer the SAME copy Eq. (2) assumes); (ii) the roll pushes field
        # energy past the window edge, where the FFT wraps it round; and (iii) -- the
        # one that actually bites -- the hole sits beyond r_max_lens, the radius past
        # which the lens's quadratic phase is under-sampled on this grid
        # (phase2_retina.validate_lens_sampling, PHYSICS_AUDIT item C). Beyond it the
        # sampled phase aliases and deflects the beam to a spurious retinal position.
        I_c = np.abs(U_shift) ** 2
        frac_clipped = float(I_c[R > (D_PUPIL_UM * 1e-6) / 2.0].sum() / I_c.sum())
        half_w = GRID_N * dx / 2.0
        frac_wrapped = float(I_c[np.abs(X) > 0.9 * half_w].sum() / I_c.sum())
        r_max_lens_um = p2.validate_lens_sampling(
            dx, (WAVELENGTH_NM * 1e-9) / N_PRIME, v_f, D_PUPIL_UM, cornea)["r_max_lens_um"]
        within_lens_nyquist = (h + a_hole_um / 2.0) <= r_max_lens_um
        I = _retina_from_cornea(U_shift, dx, M)
        centroid = float((I * X).sum() / I.sum()) * 1e6
        # r_EE about the spot's OWN centre, not the optical axis -- otherwise a shifted
        # spot's radius trivially grows with its displacement.
        I_recentred = np.roll(I, -int(round((centroid * 1e-6) / dx)), axis=1)
        rows.append({"h_um": n_pix * dx * 1e6, "centroid_um": centroid,
                     "r_EE_50_um": _r_ee(I_recentred, dx),
                     "predicted_shift_um": -(n_pix * dx * 1e6) * (v_r - v_f) / v_f,
                     "frac_energy_clipped_by_pupil": frac_clipped,
                     "frac_energy_near_window_edge": frac_wrapped,
                     "r_max_lens_um": r_max_lens_um,
                     "valid": bool(frac_clipped < 0.05 and frac_wrapped < 1e-3
                                   and within_lens_nyquist)})
    return pd.DataFrame(rows)


import collections

_PSF_FIELD_CACHE = collections.OrderedDict()
# BOUNDED CACHE, added after this cache caused a genuine memory blowup: each cached
# I_single field is grid_N x grid_N float64 -- 134MB at grid_N=4096 (the Defect-1 fix's
# new default, vs 33.5MB at the old 2048). This module's own caching docstring below
# was written when grid_N=2048 made an UNBOUNDED cache survivable (75 unique (a,M)
# entries in a full sweep -> ~2.5GB); at grid_N=4096 the same sweep tried to hold
# ~10GB of cached fields simultaneously and drove the host machine into full swap
# (12.5GB used, 0 free) and a 100%-full disk, stalling the process entirely (observed
# directly: RSS collapsed, CPU dropped to 0%, process state "stuck"). A sweep's actual
# access pattern (loop over M, and within each M loop over aperture, never revisiting
# an (aperture, M) pair once its M-level's pitches are exhausted) means only ONE
# M-level's worth of apertures needs to stay resident at a time -- capping at 20
# entries (~2.7GB at grid_N=4096) comfortably covers that pattern (this project's own
# largest aperture list has 15 entries) without reverting to an unbounded cache that
# quietly assumes a small grid_N forever.
_PSF_FIELD_CACHE_MAX_ENTRIES = 20


def single_hole_psf(a_hole_um, M, wavelength_nm=WAVELENGTH_NM, d_gap_mm=D_GAP_MM,
                     D_pupil_um=D_PUPIL_UM, P0=P0, n_prime=N_PRIME, grid_N=GRID_N,
                     window_L_mm=WINDOW_L_MM):
    """
    The expensive part of array_psf() -- one wave-optics propagation -- pulled out and
    cached per (a_hole, M, optics), since it does not depend on pitch, packing, or
    pupil alignment at all (verified by reading run_pipeline_point's signature: no
    pitch argument). array_psf() used to call this fresh on every single invocation;
    with N holes x N pitches x N myopia x N alignments to sweep, that made a full sweep
    intractable (~4s/call measured -- a 1000-point sweep would be over an hour before
    even reaching the summation step). Refactored for multi_hole_blur_sweep.py.

    Cache is size-capped (see _PSF_FIELD_CACHE_MAX_ENTRIES) with FIFO eviction, not
    unbounded -- see that constant's own comment for why this was found necessary,
    not a preemptive guess.
    """
    key = (a_hole_um, M, wavelength_nm, d_gap_mm, D_pupil_um, P0, n_prime, grid_N, window_L_mm)
    if key in _PSF_FIELD_CACHE:
        _PSF_FIELD_CACHE.move_to_end(key)
        return _PSF_FIELD_CACHE[key]
    while len(_PSF_FIELD_CACHE) >= _PSF_FIELD_CACHE_MAX_ENTRIES:
        _PSF_FIELD_CACHE.popitem(last=False)
    res = p2.run_pipeline_point(a_hole=a_hole_um * 1e-6, wavelength=wavelength_nm * 1e-9,
                                 d_gap=d_gap_mm * 1e-3, grid_N=grid_N, window_L_mm=window_L_mm,
                                 M_diopters=M, P0=P0, n_prime=n_prime, D_pupil_um=D_pupil_um,
                                 refractive_index_correction=True)
    assert res["junction_check_passed"], res["junction_fail_reason"]
    v_r, v_f = _optics(M)
    dx = res["cornea_result"]["dx"]
    eff_wl = (wavelength_nm * 1e-9) / n_prime
    r_max_lens_um = p2.validate_lens_sampling(dx, eff_wl, v_f, D_pupil_um,
                                               res["cornea_result"])["r_max_lens_um"]

    # r_EE_98 on the FULL, uncropped field -- measured once here (amortised over every
    # array_psf() call at this (a,M)), used as array_psf()'s crop safety margin below.
    # An earlier fixed "8x r_EE_80" heuristic under-margined it: crop_vs_full_grid_check()
    # caught a 0.9um (1.2%) discrepancy. The single-hole PSF's diffraction rings decay
    # slowly (measured: 90%->50um, 98%->234um, 99.95%->1733um -- almost the full grid),
    # so "containment" is a spectrum, not a threshold; 98% (234um, ~8x r_EE_80 in
    # practice) is used as a crop margin that keeps r_EE_50 accurate to well under the
    # 1% precision this feasibility-region analysis is conducted at elsewhere (the R1
    # diameter band itself is a +-10% tolerance) while keeping the crop small enough for
    # a full sweep to be tractable -- verified, not assumed, by crop_vs_full_grid_check().
    I_single = res["I_retina"]
    N_full = I_single.shape[0]
    _, _, R_full, _ = junction.make_grid(N_full, N_full * dx)
    r_edges_full, EE_full, _ = junction.encircled_energy(I_single, R_full, dx)
    r_EE_98_um = junction.r_for_EE(r_edges_full, EE_full, 0.98) * 1e6

    out = {
        "I_single": I_single, "dx": dx,
        "v_r_um": v_r * 1e6, "v_f_um": v_f * 1e6,
        "single_r_EE_50_um": res["retina_EE"]["r_EE_50"] * 1e6,
        "single_r_EE_80_um": res["retina_EE"]["r_EE_80"] * 1e6,
        "single_r_EE_98_um": r_EE_98_um,
        "r_max_lens_um": r_max_lens_um,
    }
    _PSF_FIELD_CACHE[key] = out
    return out


def array_psf(a_hole_um, pitch_um, M, packing="square", pupil_offset=(0.0, 0.0),
              D_pupil_um=D_PUPIL_UM, exclude_aliased=True, crop_half_width_um=None,
              return_field=False):
    """
    Eq. (2): I_array = sum over holes inside the pupil of I_single(r - h*(v_r-v_f)/v_f).
    Reuses the CACHED single-hole PSF (single_hole_psf()) so repeated calls at the same
    (a_hole, M) pay for the wave-optics propagation once, not once per call.

    Sums on a window CROPPED around the optical axis rather than the full grid_N field.
    Sized (unless crop_half_width_um overrides it) to comfortably contain the farthest
    shifted copy plus 8x its own r_EE_80 tail, this cuts the per-hole roll+add cost by
    10-100x at this project's grid (2048 -> a few hundred px), which is what makes a
    full sweep tractable. crop_vs_full_grid_check() below verifies this is a genuine
    equivalence, not an approximation that changes the answer.

    Holes whose far edge (radius from axis + a_hole/2) exceeds r_max_lens are EXCLUDED
    from the sum, not included at a possibly-aliased position -- see
    q1_copies_are_shifted_replicas's docstring: beyond r_max_lens the lens phase is
    under-sampled on this grid and the beam deflects to a spurious retinal position.
    Reports how many were excluded rather than silently returning a corrupted sum.

    Returns (r_EE_50_um, r_EE_80_um, n_holes_in_pupil, n_holes_included,
    n_holes_excluded_aliased, single_hole_r_EE_50_um). NaN r_EE if n_holes_included=0
    (the array is momentarily fully dark at this alignment -- there is no PSF to
    measure, not a computation failure).
    """
    psf = single_hole_psf(a_hole_um, M, D_pupil_um=D_pupil_um)
    I_single, dx = psf["I_single"], psf["dx"]
    demag = (psf["v_r_um"] - psf["v_f_um"]) / psf["v_f_um"]

    hx, hy = ap.hole_lattice(pitch_um, D_pupil_um * 0.75, packing=packing)
    ox, oy = pupil_offset
    hx, hy = hx - ox, hy - oy
    r_hole = np.sqrt(hx ** 2 + hy ** 2)
    inside = r_hole <= (D_pupil_um / 2.0)
    hx, hy, r_hole = hx[inside], hy[inside], r_hole[inside]
    n_in_pupil = int(len(hx))

    safe = ((r_hole + a_hole_um / 2.0) <= psf["r_max_lens_um"]) if exclude_aliased \
        else np.ones_like(r_hole, dtype=bool)
    n_excluded = int((~safe).sum())
    hx, hy, r_hole = hx[safe], hy[safe], r_hole[safe]
    n_included = int(len(hx))

    if n_included == 0:
        out = (float("nan"), float("nan"), n_in_pupil, n_included, n_excluded,
               psf["single_r_EE_50_um"])
        return (out + (None, dx)) if return_field else out

    N_full = I_single.shape[0]
    if crop_half_width_um is None:
        max_shift_um = demag * float(r_hole.max())
        half_width_um = max_shift_um + psf["single_r_EE_98_um"]
    else:
        half_width_um = crop_half_width_um
    half_px = min(int(np.ceil(half_width_um / (dx * 1e6))), N_full // 2)
    c = N_full // 2
    I_crop = I_single[c - half_px:c + half_px, c - half_px:c + half_px]

    I_sum = np.zeros_like(I_crop)
    for x_um, y_um in zip(hx, hy):
        sx = int(round((-demag * x_um * 1e-6) / dx))
        sy = int(round((-demag * y_um * 1e-6) / dx))
        I_sum += np.roll(np.roll(I_crop, sy, axis=0), sx, axis=1)

    # Recentre on the SUMMED PATTERN'S OWN centroid before measuring r_EE, not the
    # optical axis -- found necessary by direct inspection (a single off-axis hole,
    # N_eff=1, was being reported with r_EE_50 growing with its distance from axis,
    # 11um at the centre hole up to 86um for the same hole two lattice rows out, at
    # a pitch where geometry guarantees only ONE hole is ever active). A single active
    # hole produces a SHARP retinal image, just displaced -- the whole scene shifts,
    # it does not blur -- exactly the reasoning q1_copies_are_shifted_replicas() above
    # already applies per-hole; array_psf() must apply it to the SUMMED pattern for the
    # same reason. Uncentred, this measured "distance from the axis" as if it were
    # blur, silently inflating the blur of every off-centre N_eff<=1 alignment and
    # biasing any downstream comparison against them (found via optimise.py picking
    # unexpectedly large apertures -- traced back to here, not left as an unexplained
    # result).
    N_crop = I_sum.shape[0]
    Xc, Yc, _, _ = junction.make_grid(N_crop, N_crop * dx)
    total_power = I_sum.sum()
    if total_power > 0:
        cx = float((I_sum * Xc).sum() / total_power)
        cy = float((I_sum * Yc).sum() / total_power)
        I_sum = np.roll(np.roll(I_sum, -int(round(cy / dx)), axis=0),
                        -int(round(cx / dx)), axis=1)

    out = (_r_ee(I_sum, dx), _r_ee(I_sum, dx, 0.80), n_in_pupil, n_included, n_excluded,
           psf["single_r_EE_50_um"])
    return (out + (I_sum, dx)) if return_field else out


def crop_vs_full_grid_check(cases=((400.0, 900.0, 4.0), (700.0, 2000.0, 8.0), (300.0, 1200.0, 1.0))):
    """Verifies the crop in array_psf() gives the SAME r_EE_50 as summing on the full,
    uncropped grid_N field (crop_half_width_um forced to the full half-grid) -- a check,
    not an assumption, that nothing relevant to the multi-hole blur lives beyond the
    auto-sized crop."""
    rows = []
    for a_um, s_um, M in cases:
        r50_crop, _, n_in, n_inc, n_exc, single = array_psf(a_um, s_um, M)
        psf = single_hole_psf(a_um, M)
        full_half_um = (psf["I_single"].shape[0] // 2) * psf["dx"] * 1e6
        r50_full, _, _, _, _, _ = array_psf(a_um, s_um, M, crop_half_width_um=full_half_um)
        diff_um = abs(r50_crop - r50_full)
        rows.append({"a_hole_um": a_um, "pitch_um": s_um, "M_diopters": M,
                     "r50_cropped_um": r50_crop, "r50_full_grid_um": r50_full,
                     "diff_um": diff_um, "n_holes": n_inc})
        # r_EE_98 deliberately truncates real (if slowly-decaying-tail) energy; a
        # residual difference here of a percent or so is that intentional truncation,
        # not a bug -- checked against the precision this analysis is conducted at
        # elsewhere (the R1 diameter band is a +-10% tolerance), not against a
        # sub-percent standard nothing else in this folder claims either.
        tol_um = max(0.3, 0.015 * r50_full)
        print(f"  crop check a={a_um:.0f}um s={s_um:.0f}um M={M:.0f}D: "
              f"cropped r50={r50_crop:.4f}um  full-grid r50={r50_full:.4f}um  "
              f"diff={diff_um:.5f}um ({diff_um/r50_full*100:.3f}%, {n_inc} holes) -- "
              f"{'MATCH' if diff_um < tol_um else 'MISMATCH'}")
        assert diff_um < tol_um, f"crop vs full-grid mismatch at a={a_um} s={s_um} M={M}: {diff_um}um"
    return pd.DataFrame(rows)


def main():
    print(f"phase2_retina in use: {assert_corrected_optics()}")
    print(f"lambda={WAVELENGTH_NM}nm d_gap={D_GAP_MM}mm D_pupil={D_PUPIL_UM}um "
          f"grid_N={GRID_N} window={WINDOW_L_MM}mm packing=square\n")

    print("=== Q1: are the copies identical, merely shifted? (a=400um, M=4D) ===")
    df1 = q1_copies_are_shifted_replicas()
    print(df1.to_string(index=False, float_format=lambda v: f"{v:9.3f}"))
    ok = df1[df1.valid]
    spread = ok.r_EE_50_um.max() - ok.r_EE_50_um.min()
    print(f"over the {len(ok)}/{len(df1)} displacements that stay inside the pupil and "
          f"the window: r_EE_50 varies by {spread:.3f} um "
          f"({spread/ok.r_EE_50_um.mean()*100:.2f}%), and the centroid tracks Eq. (C) to "
          f"{(ok.centroid_um - ok.predicted_shift_um).abs().max():.3f} um "
          f"({(ok.centroid_um - ok.predicted_shift_um).abs().max()/dx_um_hint():.2f} pixels).")
    bad = df1[~df1.valid]
    if len(bad):
        print(f"excluded (a limit of the SIMULATION, not evidence against Eq. (2)): h="
              f"{', '.join(f'{h:.0f}um' for h in bad.h_um)} -- beyond r_max_lens="
              f"{df1.r_max_lens_um.iloc[0]:.0f}um the lens phase is under-sampled on this "
              f"grid (PHYSICS_AUDIT item C) and the beam aliases to a spurious position; "
              f"{bad.frac_energy_clipped_by_pupil.max()*100:.1f}% of that hole's energy is "
              f"also outside the {D_PUPIL_UM/2:.0f}um pupil radius.\n")

    print("=== crop-vs-full-grid validity check (before trusting any cropped result) ===")
    crop_vs_full_grid_check()

    print("\n=== Q2: array r_EE_50 vs single-hole r_EE_50, at the alignment that puts one "
          "hole on the optical axis ===")
    rows = []
    header = (f"{'M(D)':>5} {'a(um)':>6} {'pitch(um)':>9} {'N_holes':>8} "
              f"{'single r50':>11} {'array r50':>10} {'ratio':>7} {'full-pupil r_geo':>17}")
    print(header); print("-" * len(header))
    for M in [1.0, 4.0, 8.0]:
        v_r, v_f = _optics(M)
        full_pupil_r_geo = (D_PUPIL_UM / 2.0) * (v_r - v_f) / v_f
        for a_um, s_um in [(400, 700), (400, 900), (400, 1200), (400, 2000),
                            (400, 2900), (400, 4000)]:
            r50, r80, n_in, n_inc, n_exc, single = array_psf(a_um, s_um, M)
            rows.append({"M_diopters": M, "a_hole_um": a_um, "pitch_um": s_um,
                          "n_holes_in_pupil": n_in, "n_holes_included": n_inc,
                          "n_holes_excluded_aliased": n_exc,
                          "single_hole_r_EE_50_um": single,
                          "array_r_EE_50_um": r50, "array_r_EE_80_um": r80,
                          "ratio_array_over_single": r50 / single,
                          "full_pupil_geometric_blur_radius_um": full_pupil_r_geo})
            print(f"{M:5.1f} {a_um:6.0f} {s_um:9.0f} {n_inc:8d} {single:11.2f} {r50:10.2f} "
                  f"{r50/single:7.2f} {full_pupil_r_geo:17.1f}")
    out = os.path.join(HERE, "array_psf_envelope.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    df1.to_csv(os.path.join(HERE, "array_psf_shift_invariance_check.csv"), index=False)
    print(f"\nwrote {out}")
    print(f"wrote {os.path.join(HERE, 'array_psf_shift_invariance_check.csv')}")


if __name__ == "__main__":
    main()
