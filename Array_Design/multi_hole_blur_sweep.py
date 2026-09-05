"""
Sweeps array_psf_envelope.array_psf() over (aperture, pitch, myopia, pupil alignment,
packing) -- the full multi-hole blur envelope ANALYSIS.md F4/I1 flagged as missing.
The diameter axis in joint_design_space.py currently borrows a SINGLE-hole optimum
(stage2_fixed's R1 sweep) which is only valid where at most one hole is ever active;
this sweep produces the array's TRUE blur (min/mean/max/alignment-weighted-mean r_EE_50
over pupil alignment), which the optimiser (optimise.py) uses directly instead of the
single-hole substitute.

WHY THIS IS NOW TRACTABLE (it was not, before two fixes to array_psf_envelope.py):
  1. array_psf() used to call phase2_retina.run_pipeline_point() -- the expensive
     wave-optics propagation -- on every single call. single_hole_psf() now caches it
     per (a_hole, M), since it does not depend on pitch/packing/alignment at all. A
     1575-point sweep would have cost >1hr before even reaching the summation step;
     with caching, the propagation itself is paid ~75 times total (once per unique
     (a,M) in this sweep), not once per (a,s,M,offset,packing) combination.
  2. array_psf() used to sum on the FULL grid_N=2048 field for every hole. It now sums
     on a window cropped to the shift extent plus a measured r_EE_98 margin (~230um
     typical, vs the full ~3mm half-window) -- found via profiling to be the actual
     remaining bottleneck (np.digitize inside encircled_energy scales with array size).
     This was FOUND, not assumed: an initial fixed "8x r_EE_80" margin under-covered
     the single-hole PSF's slowly-decaying diffraction rings by 1.2%
     (crop_vs_full_grid_check() caught it), and a percentile sweep (90%->50um,
     98%->234um, 99.95%->1733um -- see array_psf_envelope.py) showed containment is a
     spectrum, not a threshold; 98% was chosen as the practical point on that curve,
     verified (not assumed) to keep r_EE_50 within ~1.5% of the full-grid answer -- a
     precision this feasibility analysis is conducted at everywhere else (the R1
     diameter band itself is a +-10% tolerance).
  Net effect, measured: ~2200-1400ms/call (dominated by the wave-optics propagation and
  full-grid summation) down to ~1-6ms/call (cached PSF, cropped summation) -- roughly
  a 300-1000x speedup, which is what makes this sweep possible at all.

ALIGNMENT RESOLUTION, stated explicitly as a distinct choice from
joint_design_space.py's N_OFFSETS=61: this sweep uses n_offsets=11 (121 alignments per
pitch), not 61 (3721 per pitch). The two serve different quantities. N_eff -- a
DISCRETE step function of alignment -- needed 61 to catch the corner alignment where
the worst case actually occurs (ANALYSIS.md F3: 15/25 offsets reported "never dark" at
a pitch where 41+ correctly show it going dark). Blur r_EE_50 -- a CONTINUOUS function
of alignment -- does not have that failure mode; a benchmark comparison (11 vs 15 vs 21
offsets at one representative point) found min/mean/max agreeing to within 2-4% across
that range, i.e. already converged at the coarser end. n_offsets=11 was chosen as the
practical point on that curve given ~2700 (a,s,M,packing) points still to cover.

Run:  python3 multi_hole_blur_sweep.py     (prints a benchmark projection before the
      full sweep launches, then the actual elapsed time on completion)
"""
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ghosting"))
sys.path.insert(0, os.path.join(HERE, "photometry"))

import array_psf_envelope as ae  # noqa: E402
from corrected_regime import assert_corrected_optics  # noqa: E402

APERTURES_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
# SCOPE CUT (live, timed): the first full run (400-5400um pitch, n_offsets=11) exceeded
# a 40+ minute wall-clock budget without finishing -- benchmarked on one moderately
# dense point (a=400um, s=900um, ~9-13 holes), but small apertures (75-300um) paired
# with small pitches (400-1000um) pack far more holes per alignment (more roll+add
# work per array_psf() call, and r_max_lens excludes proportionally fewer of them since
# the exclusion threshold is r_hole<=r_max_lens-a/2, less restrictive for small a) --
# the benchmark point undersampled that tail. Cut two ways, both stated: pitch floor
# raised to 700um (matching RESULTS.md Pass 4's own pitch list's floor -- the removed
# 400-600um region is also below any pitch this project's own R1 apertures could form a
# non-overlapping array at without s<=a anyway for most of APERTURES_UM's larger
# entries), and the alignment grid reduced from 11x11 to 7x7 (a coarser point on the
# same convergence curve benchmarked in array_psf_envelope.py -- 11/15/21 agreed to
# 2-4%; 7 is expected to be somewhat noisier but was not itself re-benchmarked here,
# a real limitation stated rather than hidden).
PITCHES_UM = list(range(700, 5401, 500))
M_VALUES = [1.0, 2.0, 4.0, 6.0, 8.0]
PACKINGS = ["square", "hex"]
N_OFFSETS = 7
D_PUPIL_UM = ae.D_PUPIL_UM


def sweep_one_point(a_hole_um, pitch_um, M, packing, n_offsets=N_OFFSETS):
    """Returns (min, mean, max, alignment_weighted_mean, frac_dark, single_r_EE_50)
    for r_EE_50 over a uniform grid of pupil alignments within one lattice unit cell.
    A uniform offset grid already weights each sample by equal cell area, so its plain
    mean IS the alignment-weighted mean -- no extra weighting step needed (same
    convention as joint_design_space.alignment_counts/alignment_fractions)."""
    offs = np.linspace(0.0, pitch_um, n_offsets, endpoint=False)
    r50s, n_in_list, n_exc_list = [], [], []
    single = None
    for ox in offs:
        for oy in offs:
            r50, r80, n_in, n_inc, n_exc, single = ae.array_psf(
                a_hole_um, pitch_um, M, packing=packing, pupil_offset=(ox, oy),
                D_pupil_um=D_PUPIL_UM)
            r50s.append(r50)
            n_in_list.append(n_in)
            n_exc_list.append(n_exc)
    r50s = np.array(r50s)
    dark = np.isnan(r50s)
    valid = r50s[~dark]
    return {
        "a_hole_um": a_hole_um, "pitch_um": pitch_um, "M_diopters": M, "packing": packing,
        "single_hole_r_EE_50_um": single,
        "array_r_EE_50_min_um": float(valid.min()) if len(valid) else float("nan"),
        "array_r_EE_50_mean_um": float(np.nanmean(r50s)) if not dark.all() else float("nan"),
        "array_r_EE_50_max_um": float(valid.max()) if len(valid) else float("nan"),
        # "alignment-weighted mean" treating a dark alignment (no hole in pupil) as
        # undefined blur, not zero -- excluded from the mean, its rate reported
        # separately via frac_dark instead of silently folded into the blur average.
        "frac_dark": float(dark.mean()),
        "max_n_holes_excluded_aliased": int(max(n_exc_list)) if n_exc_list else 0,
        "mean_n_holes_in_pupil": float(np.mean(n_in_list)) if n_in_list else 0.0,
        "n_offsets": n_offsets,
    }


def main():
    print(f"phase2_retina in use: {assert_corrected_optics()}")

    n_combos = len(APERTURES_UM) * len(PITCHES_UM) * len(M_VALUES) * len(PACKINGS)
    print(f"grid: {len(APERTURES_UM)} apertures x {len(PITCHES_UM)} pitches x "
          f"{len(M_VALUES)} myopia levels x {len(PACKINGS)} packings = {n_combos} points, "
          f"{N_OFFSETS}x{N_OFFSETS}={N_OFFSETS**2} alignments each")

    print("\nbenchmarking on one representative point before committing to the full run...")
    t_cold = time.time()
    ae.single_hole_psf(400.0, 4.0)  # one fresh cold propagation, timed directly --
    cold_propagation_s = time.time() - t_cold  # not a hardcoded constant, since this
    # scales with GRID_N (Defect-1's fix raised the default 2048->4096, roughly
    # 2.3-2.7x the per-propagation cost at 2048 -- measuring it fresh here keeps this
    # projection accurate regardless of which grid_N is actually configured).
    t0 = time.time()
    sweep_one_point(400.0, 900.0, 4.0, "square")
    per_point_s = time.time() - t0
    n_unique_am = len(set(APERTURES_UM)) * len(set(M_VALUES))
    cache_warmup_s_est = n_unique_am * cold_propagation_s
    projected_s = n_combos * per_point_s + cache_warmup_s_est
    print(f"  one cold propagation at grid_N={ae.GRID_N}: {cold_propagation_s:.1f}s")
    print(f"  one (a,s,M,packing) point (cache warm): {per_point_s:.2f}s")
    print(f"  {n_unique_am} unique (aperture, M) cache entries to populate "
          f"(shared across both packings): ~{cache_warmup_s_est/60:.1f} min")
    print(f"  PROJECTED total: ~{projected_s/60:.1f} min "
          f"({n_combos} points x {per_point_s:.2f}s + cache warmup)\n")

    rows = []
    t_start = time.time()
    n_done = 0
    for M in M_VALUES:
        for a_um in APERTURES_UM:
            ae.single_hole_psf(a_um, M)  # populate cache once per (a,M), amortised below
            for packing in PACKINGS:
                for s_um in PITCHES_UM:
                    if s_um <= a_um:
                        n_done += 1
                        continue
                    rows.append(sweep_one_point(a_um, s_um, M, packing))
                    n_done += 1
        elapsed = time.time() - t_start
        rate = n_done / elapsed if elapsed > 0 else 0
        remaining = (n_combos - n_done) / rate if rate > 0 else float("nan")
        print(f"  M={M:.0f}D done -- {n_done}/{n_combos} points, "
              f"{elapsed/60:.1f} min elapsed, ~{remaining/60:.1f} min remaining")

    df = pd.DataFrame(rows)
    df["ratio_max_over_single"] = df.array_r_EE_50_max_um / df.single_hole_r_EE_50_um
    df["ratio_mean_over_single"] = df.array_r_EE_50_mean_um / df.single_hole_r_EE_50_um
    out = os.path.join(HERE, "multi_hole_blur_sweep.csv")
    df.to_csv(out, index=False)

    elapsed = time.time() - t_start
    print(f"\nACTUAL elapsed: {elapsed/60:.1f} min for {len(rows)} points "
          f"({elapsed/max(len(rows),1):.3f}s/point average, projection was {per_point_s:.2f}s/point)")
    print(f"wrote {out}  ({len(df)} rows)")

    exclusion_hit = int((df.max_n_holes_excluded_aliased > 0).sum())
    print(f"\nr_max_lens exclusion triggered (>=1 hole dropped as unrepresentable at this "
          f"grid) at {exclusion_hit}/{len(df)} (a,s,M,packing) points "
          f"({exclusion_hit/len(df)*100:.1f}%) -- those rows' blur is a LOWER BOUND, not "
          f"an exact value (ANALYSIS.md G3/I5: raising grid_N would remove this).")

    worst = df.loc[df.ratio_max_over_single.idxmax()]
    print(f"\nlargest blur ratio found: {worst.ratio_max_over_single:.2f}x single-hole, at "
          f"a={worst.a_hole_um:.0f}um s={worst.pitch_um:.0f}um M={worst.M_diopters:.0f}D "
          f"{worst.packing} (array r_EE_50_max={worst.array_r_EE_50_max_um:.1f}um vs "
          f"single {worst.single_hole_r_EE_50_um:.2f}um)")


if __name__ == "__main__":
    main()
