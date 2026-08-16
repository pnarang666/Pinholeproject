"""Poisson-disk (blue-noise) sampling: random hole placement with enforced minimum
pairwise distance = a_hole_um * spacing_factor (same spacing_factor convention as
archimedean_spiral.py). STOCHASTIC -- unlike every other generator in this folder, the
same (N, spacing) produces a DIFFERENT layout each call, so `seed: int` is a REQUIRED
(not optional, no default) parameter for every call to be reproducible.

ALGORITHM CHOICE, STATED: Bridson's algorithm (Robert Bridson, "Fast Poisson Disk
Sampling in Arbitrary Dimensions", SIGGRAPH 2007 sketches), not naive dart-throwing-
with-rejection. Dart-throwing's rejection rate grows without bound as the domain fills
up (each new dart is increasingly likely to land too close to an existing point,
degrading to O(N^2) or worse and potentially never terminating cleanly near the
packing limit); Bridson's algorithm instead grows the point set from an active
frontier (only ever proposing candidates in the annulus [r, 2r] around an existing
point, checked against nearby points via a background grid, O(1) amortized per
accepted or exhausted-and-retired point) and terminates deterministically when no
active point can produce a valid candidate after k tries -- the standard,
well-behaved choice for this problem, implemented directly here (not copied from any
external package).

DOMAIN SIZING: Bridson's algorithm fills a bounded region to near-maximal packing
density, it does not target an exact point count directly. This generator picks a
square domain (centered at the origin, so recentering is a near-no-op) generously
sized for N points at the requested minimum distance, runs the algorithm to
exhaustion (active list empty = maximal packing for that domain), and takes the N
points closest to the origin -- same "closest-to-origin" selection convention as
square.py/hexagonal.py, both for consistency and because it gives a compact,
roughly-circular candidate array rather than an oddly-shaped domain-filling one. If
the maximal fill still has fewer than N points (only possible if the initial domain
was undersized), the domain is doubled and retried, up to a small retry cap -- if
still short after that, N_actual < N_requested is reported honestly (base_generator's
own established convention), not padded or errored.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402

BRIDSON_K = 30  # candidate attempts per active point before retiring it -- Bridson's
                # own recommended default, large enough that a retired point is a
                # genuine local packing limit, not an unlucky run of bad candidates
DOMAIN_MULTIPLIER = 1.8  # initial domain side, in units of r_um*sqrt(N) -- see module
                         # docstring; generous enough in practice that the retry path
                         # below is rarely exercised, checked against this pipeline's
                         # own N<=100, spacing-factor~1.5 range
MAX_DOMAIN_RETRIES = 4


def _bridson_fill(half_width_um, r_um, rng, k=BRIDSON_K):
    """Fills the square [-half_width_um, half_width_um]^2 to near-maximal Poisson-disk
    packing at minimum distance r_um. Returns an (n, 2) array."""
    cell_size = r_um / np.sqrt(2.0)  # Bridson's own recommended cell size: small enough
                                      # that each grid cell holds at most one sample
    samples = [np.array([0.0, 0.0])]
    grid = {}

    def cell_of(p):
        return (int((p[0] + half_width_um) // cell_size), int((p[1] + half_width_um) // cell_size))

    def in_domain(p):
        return -half_width_um <= p[0] <= half_width_um and -half_width_um <= p[1] <= half_width_um

    def far_enough(p):
        gi, gj = cell_of(p)
        for di in (-2, -1, 0, 1, 2):
            for dj in (-2, -1, 0, 1, 2):
                j = grid.get((gi + di, gj + dj))
                if j is not None:
                    q = samples[j]
                    if (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < r_um ** 2:
                        return False
        return True

    grid[cell_of(samples[0])] = 0
    active = [0]
    while active:
        pick = rng.integers(len(active))
        p = samples[active[pick]]
        placed = False
        for _ in range(k):
            radius = rng.uniform(r_um, 2.0 * r_um)
            angle = rng.uniform(0.0, 2.0 * np.pi)
            cand = p + radius * np.array([np.cos(angle), np.sin(angle)])
            if in_domain(cand) and far_enough(cand):
                samples.append(cand)
                grid[cell_of(cand)] = len(samples) - 1
                active.append(len(samples) - 1)
                placed = True
                break
        if not placed:
            active.pop(pick)

    return np.array(samples)


def generate(N, a_hole_um, spacing_factor, seed):
    r_um = a_hole_um * spacing_factor
    rng = np.random.default_rng(seed)

    half_width_um = 0.5 * DOMAIN_MULTIPLIER * r_um * np.sqrt(max(N, 1))
    filled = _bridson_fill(half_width_um, r_um, rng)
    retries = 0
    while len(filled) < N and retries < MAX_DOMAIN_RETRIES:
        half_width_um *= 2.0
        filled = _bridson_fill(half_width_um, r_um, rng)
        retries += 1

    r2 = np.sum(filled ** 2, axis=1)
    order = np.argsort(r2)
    pts = filled[order][:N]

    coords, meta = bg.finalize(pts, a_hole_um, family="poisson_disk", N_requested=N,
                               nominal_spacing_desc={"spacing_factor": float(spacing_factor),
                                                      "min_distance_um": float(r_um)})
    meta["seed"] = int(seed)
    meta["domain_retries"] = retries
    return coords, meta
