"""
Array_Design Step 3: the (aperture diameter x pitch) design space with all three
constraints on one plot, at M = 1, 4 and 8 D.

Constraints drawn, and where each comes from -- no constraint is re-derived here:

  1. DIAMETER (blur). Array_Design/single_hole_reference/r1_multi_EE_sweep_postfix.csv,
     i.e. stage2_fixed's own R1 sweep run AFTER the lens-wavelength fix. The per-M
     minimiser of r_EE_50 and the band within +10% of it are read straight off that
     file (400-750um across M=1-8D, decreasing with M -- NOT the superseded 300-400um,
     which came from the pre-fix optics).
  2. BRIGHTNESS. Array_Design/photometry/array_photometry.py's own discrete lattice
     enumeration, via corrected_regime.n_eff_cached(). Shaded where the worst-case
     alignment gives N_eff < 1, i.e. pitches at which some pupil positions see NO hole
     at all.
  3. GHOSTING. Array_Design/ghosting, through corrected_regime.classify(), using the
     ghost separation resolved in Step 2 (delta_r = s*|v_r-v_f|/v_f, see
     ghosting/ghost_separation.py and ghosting/delta_r_derivation_check.py), the same
     Barten-1999 CSF (contrast_barten.py), the same radial MTF (metrics_mtf.py), and
     the same harmonic rule as harmonic_analysis.py. cross_check_against_harmonic_module()
     asserts this reproduces harmonic_analysis.harmonic_margin_profile() itself, run
     unmodified, rather than assuming it does.

Also drawn, because leaving them off would make the region look larger than it is:
  4. s <= a_hole is not an array (the holes would overlap) -- greyed out.
  5. The single-hole diameter optimum in (1) only describes the retinal blur while at
     most ONE hole is active. Where N_eff > 1 the blur is set by the illuminated hole
     CLUSTER, not the hole (measured in Array_Design/array_psf_envelope.py: 7-17x the
     single-hole r_EE_50 at M=4-8D, approaching the full-pupil blur). The diameter band
     is therefore drawn solid only where it is actually load-bearing (N_eff_worst<=1)
     and dashed elsewhere.

Outputs: joint_design_space_M{1,4,8}.png, joint_design_space.png (3-panel),
joint_design_space_grid.csv, pupil_sensitivity.csv.

Run:  python3 joint_design_space.py       (~3 min; dominated by 3x16 PSF propagations)
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ghosting"))
sys.path.insert(0, os.path.join(HERE, "photometry"))

import corrected_regime as cr  # noqa: E402
import ghost_separation as gs  # noqa: E402
import harmonic_analysis  # noqa: E402  (used by cross_check_against_harmonic_module)
import array_photometry as ap  # noqa: E402  (used by alignment_fractions)

M_PANELS = [1.0, 4.0, 8.0]
APERTURES_UM = [150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 700, 750, 850, 1000, 1150, 1300]
PITCHES_UM = list(range(300, 5301, 100))
D_PUPIL_UM = 4000.0
D_GAP_MM = 12.0
WAVELENGTH_NM = 550.0
PACKING = "square"
BLUR_BAND_TOLERANCE = 0.10  # "optimum band" = apertures within +10% of the minimum r_EE_50
# Alignment-sweep resolution. NOT the defaults elsewhere in the project (25 in
# array_photometry.n_holes_exact_sweep_alignment, 15 in ghosting_regime), because those
# are too coarse exactly where this plot's boundaries sit: at D_pupil=4000um square,
# n_offsets=15/25 report N_eff_worst=1 at s=2900um (41+ report 0) and N_eff_best=1 at
# s=3900um (41+ report 2) -- i.e. they miss both critical alignments and report the
# design as safer than it is. 61 and 121 agree at every pitch tested, so 61 is converged.
N_OFFSETS = 61

# Okabe-Ito bluish-green / blue / vermillion. Validated (dataviz validator, light mode):
# all three inside the lightness band, chroma floor and 3:1 contrast pass, worst
# adjacent CVD separation dE 18.0 (protan) / 8.6 (tritan). Region fills use light tints
# of these with the saturated hue on the edge; every region is ALSO directly labelled,
# so identity never rests on colour alone.
COL = {"A": "#009E73", "B": "#0072B2", "C": "#D55E00"}
FILL = {"A": "#cdeade", "B": "#cfe0f0", "C": "#f6ddcc"}
INK, MUTED, GRID = "#1a1a1a", "#5c5c5c", "#d8d8d8"
REGIME_CODE = {"A": 0, "B": 1, "C": 2}


# ---------------------------------------------------------------------------------
# Constraint 1: the corrected single-hole diameter optimum, read from stage2_fixed
# ---------------------------------------------------------------------------------

def r1_optimum_band():
    """Per-M (argmin aperture, band_lo, band_hi, r_EE_50_min) from the post-fix R1 sweep."""
    path = os.path.join(HERE, "single_hole_reference", "r1_multi_EE_sweep_postfix.csv")
    df = pd.read_csv(path)
    assert df.junction_ok.all(), "R1 reference sweep contains junction failures"
    out = {}
    for M, d in df.groupby("M_diopters"):
        d = d.sort_values("a_hole_um")
        best = d.loc[d.r_EE_50_um.idxmin()]
        band = d[d.r_EE_50_um <= best.r_EE_50_um * (1.0 + BLUR_BAND_TOLERANCE)]
        out[float(M)] = {"opt_um": float(best.a_hole_um), "lo_um": float(band.a_hole_um.min()),
                          "hi_um": float(band.a_hole_um.max()), "r_EE_50_um": float(best.r_EE_50_um)}
    return out, path


# ---------------------------------------------------------------------------------
# Constraints 2 + 3 on the grid
# ---------------------------------------------------------------------------------

def build_grid(M, packing=PACKING):
    rows = []
    for a_um in APERTURES_UM:
        for s_um in PITCHES_UM:
            if s_um <= a_um:
                rows.append({"a_hole_um": a_um, "pitch_um": s_um, "M_diopters": M,
                             "regime_harmonic": None, "manufacturable": False})
                continue
            r = cr.classify(a_um, s_um, M, separation_model="corrected",
                            wavelength_nm=WAVELENGTH_NM, d_gap_mm=D_GAP_MM,
                            D_pupil_um=D_PUPIL_UM, packing=packing, n_offsets=N_OFFSETS)
            r["manufacturable"] = True
            rows.append(r)
    return pd.DataFrame(rows)


def pitch_thresholds(D_pupil_um=D_PUPIL_UM, packing=PACKING, n_offsets=N_OFFSETS):
    """The two purely geometric pitch limits, measured off array_photometry's own
    enumeration rather than assumed from the closed forms:
      s_dark  -- smallest pitch at which some pupil alignment sees NO hole (N_eff_worst=0)
      s_solo  -- smallest pitch at which NO pupil alignment ever sees 2+ holes (N_eff_best=1)
    Closed forms for a lattice of nearest-neighbour spacing s inside a circle of
    diameter D: covering requires the Voronoi circumradius <= D/2 (s <= D/sqrt(2)
    square, s <= D*sqrt(3)/2 hex), and 2 points cannot both fit once s > D."""
    def bisect(predicate, lo=200.0, hi=8000.0, tol=5.0):
        # Both predicates are monotone in s over this range (more pitch = fewer holes),
        # spot-checked against the closed forms printed by main(); bisection replaces a
        # 10um linear scan that dominated runtime.
        assert not predicate(lo) and predicate(hi), "predicate not bracketed"
        while hi - lo > tol:
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if predicate(mid) else (mid, hi)
        return hi

    s_dark = bisect(lambda s: n_eff_triple(s, D_pupil_um, packing, n_offsets)[0] < 1)
    s_solo = bisect(lambda s: n_eff_triple(s, D_pupil_um, packing, n_offsets)[2] <= 1)
    return s_dark, s_solo


_COUNT_CACHE = {}


def alignment_counts(pitch_um, D_pupil_um=D_PUPIL_UM, packing=PACKING, n_offsets=N_OFFSETS):
    """
    The full distribution of "how many holes are inside the pupil" over one lattice
    alignment cell, as an array of n_offsets^2 counts.

    array_photometry.n_holes_exact_sweep_alignment() computes the same thing but
    returns only (min, mean, max) and rebuilds the whole lattice once per alignment,
    which is ~3700 lattice constructions per pitch -- too slow for the pitch scans
    below. This builds the lattice ONCE via that module's own hole_lattice() and
    applies its own "hole centre inside the pupil circle" rule vectorised over
    alignments. verify_alignment_counts() asserts the two agree exactly rather than
    assuming the restatement is faithful.
    """
    key = (pitch_um, D_pupil_um, packing, n_offsets)
    if key in _COUNT_CACHE:
        return _COUNT_CACHE[key]
    hx, hy = ap.hole_lattice(pitch_um, D_pupil_um * 0.75, packing=packing)
    offs = np.linspace(0.0, pitch_um, n_offsets, endpoint=False)
    OX, OY = np.meshgrid(offs, offs, indexing="ij")
    ox, oy = OX.ravel()[:, None], OY.ravel()[:, None]
    inside = ((hx[None, :] - ox) ** 2 + (hy[None, :] - oy) ** 2) <= (D_pupil_um / 2.0) ** 2
    counts = inside.sum(axis=1)
    _COUNT_CACHE[key] = counts
    return counts


def verify_alignment_counts(pitches=(700.0, 2100.0, 2900.0, 3900.0, 4800.0), n_offsets=15):
    """Asserts alignment_counts() reproduces array_photometry's own sweep exactly."""
    for s in pitches:
        c = alignment_counts(s, n_offsets=n_offsets)
        ref = ap.n_holes_exact_sweep_alignment(s, D_PUPIL_UM, packing=PACKING, n_offsets=n_offsets)
        got = (int(c.min()), float(c.mean()), int(c.max()))
        assert got[0] == ref[0] and got[2] == ref[2] and abs(got[1] - ref[1]) < 1e-9, \
            f"alignment_counts disagrees with array_photometry at s={s}: {got} vs {ref}"
    print(f"  alignment_counts() == array_photometry.n_holes_exact_sweep_alignment() "
          f"at {len(pitches)} pitches -- MATCH")
    return True


def n_eff_triple(pitch_um, D_pupil_um=D_PUPIL_UM, packing=PACKING, n_offsets=N_OFFSETS):
    c = alignment_counts(pitch_um, D_pupil_um, packing, n_offsets)
    return int(c.min()), float(c.mean()), int(c.max())


def prefill_neff_cache(pitches, D_pupil_um=D_PUPIL_UM, packing=PACKING, n_offsets=N_OFFSETS):
    """Fills corrected_regime's N_eff memo with the identical values computed the fast
    way, so classify() never pays for the slow per-alignment lattice rebuild. Values
    are the same numbers array_photometry would return (verify_alignment_counts)."""
    for s in pitches:
        cr._NEFF_CACHE[(float(s), D_pupil_um, packing, n_offsets)] = \
            n_eff_triple(float(s), D_pupil_um, packing, n_offsets)


def alignment_fractions(pitch_um, D_pupil_um=D_PUPIL_UM, packing=PACKING, n_offsets=N_OFFSETS):
    """
    Fraction of pupil alignments that see 0 holes (momentarily dark), exactly 1 (the
    wanted single-pinhole state), and >=2 (ghost-capable).

    Why this is needed on top of the (min, mean, max) that
    array_photometry.n_holes_exact_sweep_alignment already returns: the A/B/C
    classifier reads Regime A off the MINIMUM N_eff, which is the right worst case for
    BRIGHTNESS (fewest holes = darkest) but the wrong one for GHOSTING (most holes =
    worst ghosting). A pitch with min=1, max=4 is classified "A -- no second hole to
    ghost against" while in fact having a second hole over most of the alignment cell.
    """
    c = alignment_counts(pitch_um, D_pupil_um, packing, n_offsets)
    return float((c == 0).mean()), float((c == 1).mean()), float((c >= 2).mean())


def plot_alignment_fractions(path):
    pitches = np.arange(400.0, 5401.0, 50.0)
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.6), sharey=True)
    rows = []
    for ax, packing in zip(axes, ["square", "hex"]):
        fr = np.array([alignment_fractions(float(s), packing=packing) for s in pitches])
        for i, (lbl, col) in enumerate([("sees 0 holes — momentarily dark", COL["B"]),
                                         ("sees exactly 1 hole — wanted state", COL["A"]),
                                         ("sees ≥2 holes — ghost-capable", COL["C"])]):
            ax.plot(pitches, fr[:, i], lw=2.0, color=col, label=lbl)
        best = pitches[int(np.argmax(fr[:, 1]))]
        ax.axvline(best, color=INK, lw=1.2, ls=(0, (1, 1.6)))
        ax.annotate(f"max single-hole time\n{best:.0f} µm ({fr[:,1].max()*100:.0f}%)",
                    xy=(best, fr[:, 1].max()), xytext=(best + 180, 0.90), fontsize=8,
                    color=INK, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
        ax.set_title(f"{packing} packing", fontsize=10, color=INK)
        ax.set_xlabel("array pitch  s  (µm)", fontsize=9, color=INK)
        ax.grid(True, color=GRID, lw=0.5, alpha=0.6)
        ax.tick_params(labelsize=8, colors=MUTED)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for s, f in zip(pitches, fr):
            rows.append({"pitch_um": s, "packing": packing, "frac_dark": f[0],
                          "frac_single": f[1], "frac_ghost_capable": f[2]})
    axes[0].set_ylabel("fraction of pupil alignments", fontsize=9, color=INK)
    axes[0].legend(fontsize=8, frameon=False, loc="center left")
    fig.suptitle(f"What the pupil actually sees as it moves over the hole lattice "
                 f"(D$_{{pupil}}$={D_PUPIL_UM/1000:.0f} mm, {N_OFFSETS}×{N_OFFSETS} alignments per pitch)",
                 fontsize=11, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)
    return pd.DataFrame(rows)


def cross_check_against_harmonic_module(tol=1e-9):
    """Asserts corrected_regime's harmonic margins ARE harmonic_analysis.py's, by running
    that module unmodified at the frequency-equivalent pitch (see
    ghost_separation.legacy_equivalent_pitch_um for why that is exact)."""
    checked = []
    for a_um, s_um, M in [(400.0, 900.0, 4.0), (700.0, 1500.0, 8.0)]:
        mine = cr.classify(a_um, s_um, M, separation_model="corrected",
                           D_pupil_um=D_PUPIL_UM, d_gap_mm=D_GAP_MM, wavelength_nm=WAVELENGTH_NM)
        psf = cr.psf_for(a_um, M, WAVELENGTH_NM, D_GAP_MM, D_PUPIL_UM)
        s_equiv = gs.legacy_equivalent_pitch_um(s_um, psf["v_r_um"], psf["v_f_um"], D_GAP_MM * 1e3)
        ref = harmonic_analysis.harmonic_margin_profile(
            a_hole_um=a_um, pitch_um=s_equiv, D_pupil_um=D_PUPIL_UM,
            wavelength_nm=WAVELENGTH_NM, d_gap_mm=D_GAP_MM, M_diopters=M)
        assert abs(ref["worst_margin"] - mine["worst_margin"]) < tol * max(1.0, ref["worst_margin"]), \
            f"harmonic mismatch at a={a_um} s={s_um} M={M}: {ref['worst_margin']} vs {mine['worst_margin']}"
        assert ref["worst_n"] == mine["worst_n"]
        checked.append((a_um, s_um, M, ref["worst_margin"]))
        print(f"  harmonic_analysis.py cross-check a={a_um:.0f}um s={s_um:.0f}um M={M:.0f}D: "
              f"worst_margin {ref['worst_margin']:.4f} (n={ref['worst_n']}) -- MATCH")
    return checked


# ---------------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------------

def draw_panel(ax, grid, M, band, s_dark, s_solo, show_ylabel=True):
    piv = grid.pivot(index="pitch_um", columns="a_hole_um", values="regime_harmonic")
    Z = np.array([[REGIME_CODE.get(v, np.nan) for v in row] for row in piv.values],
                 dtype=float)
    A = np.array(piv.columns, dtype=float)
    S = np.array(piv.index, dtype=float)

    def edges(v):
        mid = (v[:-1] + v[1:]) / 2.0
        return np.concatenate([[v[0] - (mid[0] - v[0])], mid, [v[-1] + (v[-1] - mid[-1])]])

    cmap = matplotlib.colors.ListedColormap([FILL["A"], FILL["B"], FILL["C"]])
    cmap.set_bad("#eeeeee")
    ax.pcolormesh(edges(A), edges(S), np.ma.masked_invalid(Z), cmap=cmap,
                  vmin=-0.5, vmax=2.5, shading="flat", zorder=1)

    # Constraint 2: brightness -- worst-case alignment sees no hole at all.
    ax.axhspan(s_dark, edges(S)[-1], facecolor="none", edgecolor=MUTED, hatch="///",
               linewidth=0.0, alpha=0.55, zorder=2)
    ax.axhline(s_dark, color=MUTED, lw=1.4, ls="-", zorder=4)
    ax.axhline(s_solo, color=MUTED, lw=1.2, ls=":", zorder=4)

    # Constraint 1: the corrected R1 diameter band. It is a SINGLE-hole blur optimum, so
    # it describes the array's actual blur only where at most one hole is ever in the
    # pupil, i.e. above s_solo. Solid there, dashed below -- see module docstring item 5.
    ax.axvspan(band["lo_um"], band["hi_um"], ymin=0, ymax=1, facecolor="#8c8c8c",
               alpha=0.16, zorder=3)
    for x in (band["lo_um"], band["hi_um"]):
        ax.plot([x, x], [s_solo, edges(S)[-1]], color=INK, lw=1.3, ls="-", zorder=5)
        ax.plot([x, x], [edges(S)[0], s_solo], color=INK, lw=1.1, ls=(0, (4, 3)), zorder=5)
    ax.plot([band["opt_um"], band["opt_um"]], [edges(S)[0], edges(S)[-1]], color=INK,
            lw=1.8, ls=(0, (1, 1.6)), zorder=5)

    # Constraint 4: pitch must exceed the hole diameter.
    ax.plot([edges(A)[0], edges(A)[-1]], [edges(A)[0], edges(A)[-1]], color="#8c8c8c",
            lw=1.0, zorder=4)

    # The strip that satisfies brightness AND ghosting at once, if it exists.
    feasible = grid[(grid.regime_harmonic == "A") & (grid.N_eff_worst >= 1)]
    if len(feasible):
        lo, hi = feasible.pitch_um.min(), feasible.pitch_um.max()
        ax.axhspan(lo - 50, hi + 50, facecolor="none", edgecolor=COL["A"], lw=2.2, zorder=6)
        d_lo, _, g_lo = alignment_fractions(float(lo))
        d_hi, _, g_hi = alignment_fractions(float(hi))
        ax.annotate(f"never-dark ∩ Regime A: {lo:.0f}–{hi:.0f} µm\n"
                    f"but ≥2 holes at {g_hi*100:.0f}–{g_lo*100:.0f}% of alignments\n"
                    f"(Regime A reads N$_{{eff}}$(min); see alignment_fractions.png)",
                    xy=(edges(A)[-1] * 0.985, (lo + hi) / 2), ha="right", va="center",
                    fontsize=7.5, color=COL["A"], fontweight="bold", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=COL["A"], lw=0.8, alpha=0.9))

    for regime, y_frac in (("C", 0.10), ("B", 0.02), ("A", 0.80)):
        sub = grid[grid.regime_harmonic == regime]
        if len(sub) < 3:
            continue
        ax.annotate(f"Regime {regime}", xy=(sub.a_hole_um.median(), sub.pitch_um.quantile(0.5)),
                    ha="center", va="center", fontsize=9, fontweight="bold",
                    color=COL[regime], zorder=7,
                    bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="none", alpha=0.72))

    ax.set_xlim(edges(A)[0], edges(A)[-1])
    ax.set_ylim(edges(S)[0], edges(S)[-1])
    ax.set_xlabel("hole diameter  a  (µm)", fontsize=9, color=INK)
    if show_ylabel:
        ax.set_ylabel("array pitch  s  (µm)", fontsize=9, color=INK)
    ax.set_title(f"M = {M:.0f} D   ·   blur optimum {band['opt_um']:.0f} µm "
                 f"(band {band['lo_um']:.0f}–{band['hi_um']:.0f} µm)",
                 fontsize=10, color=INK, pad=8)
    ax.tick_params(labelsize=8, colors=MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(True, color=GRID, lw=0.5, alpha=0.5, zorder=0)


def legend_handles(s_dark, s_solo):
    return [
        Patch(facecolor=FILL["A"], edgecolor=COL["A"], label="Regime A — N$_{eff}$(worst) ≤ 1: no 2nd hole to ghost against"),
        Patch(facecolor=FILL["B"], edgecolor=COL["B"], label="Regime B — ghost comb above the eye's cutoff / below CSF threshold"),
        Patch(facecolor=FILL["C"], edgecolor=COL["C"], label="Regime C — ghost comb predicted perceptible (danger zone)"),
        Patch(facecolor="white", edgecolor=MUTED, hatch="///", label=f"brightness fail — worst-case N$_{{eff}}$ < 1 (s > {s_dark:.0f} µm)"),
        Patch(facecolor="#eeeeee", edgecolor="#8c8c8c", label="s ≤ a — holes overlap, not an array"),
        Line2D([], [], color=INK, lw=1.8, ls=(0, (1, 1.6)), label="corrected R1 blur optimum (stage2_fixed post-fix)"),
        Line2D([], [], color=INK, lw=1.3, ls="-", label="±10% blur band — solid where one hole at most applies, dashed where the cluster sets the blur"),
        Line2D([], [], color=MUTED, lw=1.2, ls=":", label=f"s > {s_solo:.0f} µm — 2 holes can never both be in the pupil"),
    ]


def main():
    print(f"phase2_retina in use: {cr.assert_corrected_optics()}")
    print("verifying the classifier against the folder's own modules:")
    cr.self_check()
    verify_alignment_counts()
    cross_check_against_harmonic_module()
    prefill_neff_cache(PITCHES_UM)

    bands, r1_path = r1_optimum_band()
    print(f"\ncorrected R1 optimum band, read from {os.path.relpath(r1_path, HERE)}:")
    for M in M_PANELS:
        b = bands[M]
        print(f"  M={M:.0f}D: optimum {b['opt_um']:.0f}um (within +10%: "
              f"{b['lo_um']:.0f}-{b['hi_um']:.0f}um), r_EE_50={b['r_EE_50_um']:.2f}um")

    s_dark, s_solo = pitch_thresholds()
    print(f"\ngeometric pitch limits at D_pupil={D_PUPIL_UM:.0f}um, {PACKING} packing:")
    print(f"  s_dark = {s_dark:.0f}um  (>= this, some pupil alignments see zero holes; "
          f"closed form D/sqrt(2) = {D_PUPIL_UM/np.sqrt(2):.0f}um)")
    print(f"  s_solo = {s_solo:.0f}um  (>= this, two holes can never both be in the pupil; "
          f"closed form D = {D_PUPIL_UM:.0f}um)")
    print(f"  => 'never dark' and 'never ghosting' are mutually exclusive by "
          f"{s_solo - s_dark:.0f}um of pitch.")

    grid_csv = os.path.join(HERE, "joint_design_space_grid.csv")
    replot = "--replot" in sys.argv and os.path.exists(grid_csv)
    cached = pd.read_csv(grid_csv) if replot else None
    if replot:
        print(f"\n--replot: reusing {os.path.basename(grid_csv)} "
              f"(figures only; no optics re-run)")

    grids, all_rows = {}, []
    for M in M_PANELS:
        if replot:
            g = cached[cached.M_diopters == M].copy()
        else:
            print(f"\nbuilding grid at M={M:.0f}D "
                  f"({len(APERTURES_UM)}x{len(PITCHES_UM)} points, "
                  f"{len(APERTURES_UM)} propagations)...")
            g = build_grid(M)
        grids[M] = g
        all_rows.append(g)
        tally = g[g.manufacturable].regime_harmonic.value_counts()
        print(f"  regimes: " + ", ".join(f"{k}={int(v)}" for k, v in sorted(tally.items())))
        feas = g[(g.regime_harmonic == "A") & (g.N_eff_worst >= 1)]
        if len(feas):
            print(f"  brightness-AND-ghosting-feasible pitches: "
                  f"{feas.pitch_um.min():.0f}-{feas.pitch_um.max():.0f}um "
                  f"(at every aperture on the grid -- N_eff depends on pitch alone)")
        else:
            print("  brightness-AND-ghosting-feasible pitches: NONE")

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 6.0), sharey=True)
    for ax, M in zip(axes, M_PANELS):
        draw_panel(ax, grids[M], M, bands[M], s_dark, s_solo, show_ylabel=(M == M_PANELS[0]))
    fig.suptitle("Pinhole-array design space: hole diameter × pitch, all three constraints\n"
                 f"corrected optics (stage2_fixed, post lens-wavelength-fix) · corrected ghost "
                 f"separation Δr = s·|v$_r$−v$_f$|/v$_f$ · D$_{{pupil}}$={D_PUPIL_UM/1000:.0f} mm · "
                 f"{PACKING} packing · d$_{{gap}}$={D_GAP_MM:.0f} mm · λ={WAVELENGTH_NM:.0f} nm",
                 fontsize=11.5, color=INK, y=0.995)
    fig.legend(handles=legend_handles(s_dark, s_solo), loc="lower center", ncol=2,
               fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=[0, 0.16, 1, 0.90])
    out = os.path.join(HERE, "joint_design_space.png")
    fig.savefig(out, dpi=170, facecolor="white")
    print(f"\nwrote {out}")

    for M in M_PANELS:
        f1, a1 = plt.subplots(figsize=(7.2, 6.2))
        draw_panel(a1, grids[M], M, bands[M], s_dark, s_solo)
        f1.legend(handles=legend_handles(s_dark, s_solo), loc="lower center", ncol=1,
                  fontsize=7.5, frameon=False)
        f1.tight_layout(rect=[0, 0.30, 1, 1])
        p = os.path.join(HERE, f"joint_design_space_M{M:.0f}.png")
        f1.savefig(p, dpi=170, facecolor="white")
        plt.close(f1)
        print(f"wrote {p}")

    if not replot:
        pd.concat(all_rows, ignore_index=True).to_csv(grid_csv, index=False)
        print(f"wrote {grid_csv}")

    af_png = os.path.join(HERE, "alignment_fractions.png")
    af = plot_alignment_fractions(af_png)
    af.to_csv(os.path.join(HERE, "alignment_fractions.csv"), index=False)
    print(f"wrote {af_png}")
    print(f"wrote {os.path.join(HERE, 'alignment_fractions.csv')}")
    print("\nalignment breakdown at the pitches that bound the strip "
          "(what 'Regime A' actually means there):")
    print(f"{'pitch(um)':>10} {'packing':>8} {'P(dark)':>9} {'P(1 hole)':>10} {'P(>=2 holes)':>13}")
    for s in [2100.0, 2500.0, 2800.0, 2900.0, 3200.0, 4000.0, 4800.0]:
        for packing in ["square", "hex"]:
            d, one, multi = alignment_fractions(s, packing=packing)
            print(f"{s:10.0f} {packing:>8} {d:9.2f} {one:10.2f} {multi:13.2f}")

    # --- pupil sensitivity: the strip's position depends on a parameter the wearer,
    # not the designer, controls. Reported because the recommendation cannot be read
    # off the M=1/4/8 panels without it. ---
    print(f"\npupil sensitivity of the two geometric pitch limits:")
    print(f"{'D_pupil(um)':>12} {'packing':>8} {'s_dark(um)':>11} {'s_solo(um)':>11}")
    rows = []
    for D in [2000.0, 3000.0, 4000.0, 5000.0, 6000.0]:
        for packing in ["square", "hex"]:
            sd, ss = pitch_thresholds(D, packing)
            rows.append({"D_pupil_um": D, "packing": packing, "s_dark_um": sd, "s_solo_um": ss})
            print(f"{D:12.0f} {packing:>8} {sd:11.0f} {ss:11.0f}")
    ps = pd.DataFrame(rows)
    ps.to_csv(os.path.join(HERE, "pupil_sensitivity.csv"), index=False)
    for packing in ["square", "hex"]:
        p = ps[ps.packing == packing]
        lo, hi = p.s_dark_um.min(), p.s_solo_um.max()
        print(f"  {packing}: across D_pupil 2-6mm, no single pitch is below every s_dark "
              f"({p.s_dark_um.min():.0f}um) and above every s_solo ({p.s_solo_um.max():.0f}um) "
              f"-- {'no' if lo < hi else 'a'} pitch works for every pupil size.")
    print(f"wrote {os.path.join(HERE, 'pupil_sensitivity.csv')}")


if __name__ == "__main__":
    main()
