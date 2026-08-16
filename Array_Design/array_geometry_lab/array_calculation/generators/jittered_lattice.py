"""Jittered hexagonal lattice: hexagonal.py's own lattice (IMPORTED, not copied --
permitted for new files within this folder per Prompt A's own rule; the "copy, don't
import" rule applies only at the array_optimization/ boundary), with each hole's
position perturbed by a random offset before this folder's standard overlap-rejection
is re-applied. STOCHASTIC -- `seed: int` is REQUIRED (no default) for reproducibility.

DISTRIBUTION CHOICE, STATED: UNIFORM (not Gaussian) offset, sampled uniformly BY AREA
within a disk of radius jitter_fraction*pitch_um (i.e. offset magnitude =
jitter_fraction*pitch_um*sqrt(u), u~Uniform(0,1), angle~Uniform(0,2*pi) -- the
sqrt(u) is not optional: sampling magnitude directly as
jitter_fraction*pitch_um*u would over-concentrate points near zero offset, since
area scales with r^2, not r. This exact sqrt(u) construction already appears
elsewhere in this project for the same reason -- array_optimization/vignetting.py's
own Monte Carlo validation samples a disk via `r = R_h*sqrt(rng.random(n))` -- reused
here as the same, already-established pattern, not invented fresh.
Uniform (not Gaussian) was chosen specifically because jitter_fraction's own contract
is "offset UP TO jitter_fraction*pitch_um" -- a hard, stated bound; a Gaussian offset
has unbounded support (a rare draw could in principle move a hole arbitrarily far),
which would make that "up to X" contract false in the tail, however unlikely.

At jitter_fraction=0.0 this reduces EXACTLY to hexagonal.generate()'s own output (zero
offset magnitude regardless of the random draws) -- spot-checked explicitly in
spot_check_generators.py, the same pattern as rectangular.py's square-equivalence
check.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_generator as bg  # noqa: E402
import hexagonal  # noqa: E402


def generate(N, a_hole_um, pitch_um, jitter_fraction, seed):
    base_coords, base_meta = hexagonal.generate(N, a_hole_um, pitch_um)

    rng = np.random.default_rng(seed)
    n = len(base_coords)
    max_offset_um = jitter_fraction * pitch_um
    u = rng.uniform(0.0, 1.0, size=n)
    magnitudes = max_offset_um * np.sqrt(u)  # uniform-in-AREA within the jitter disk
    angles = rng.uniform(0.0, 2.0 * np.pi, size=n)
    offsets = np.column_stack([magnitudes * np.cos(angles), magnitudes * np.sin(angles)])
    jittered = base_coords + offsets

    # Re-applying base_generator.finalize() (overlap-rejection + recentering) on the
    # jittered set, not just adding the offsets, matters: jitter can push two holes
    # that were exactly at the lattice's own valid spacing closer than a_hole_um --
    # those must be rejected here exactly as any other overlapping candidate would be,
    # not silently kept because they "started" from a valid lattice. At
    # jitter_fraction=0.0, offsets are identically zero, so this re-finalize is a
    # provable no-op on an already-valid, already-centered set -- the exact-reduction
    # property follows from that, not from special-casing jitter_fraction==0.
    coords, meta = bg.finalize(jittered, a_hole_um, family="jittered_lattice", N_requested=N,
                               nominal_spacing_desc={"pitch_um": float(pitch_um),
                                                      "jitter_fraction": float(jitter_fraction)})
    meta["seed"] = int(seed)
    meta["N_actual_before_jitter"] = base_meta["N_actual"]  # transparency: how many
                                        # holes the underlying hex lattice itself had,
                                        # before any jitter-induced rejections further
                                        # reduced the count
    return coords, meta
