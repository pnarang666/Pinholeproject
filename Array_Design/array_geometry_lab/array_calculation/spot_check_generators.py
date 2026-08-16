"""Part 2 spot-check, required before Part 3 per this folder's own task order: for each
generator, print a few coordinates, confirm no two holes are closer than a_hole_um
(overlap rejection actually worked), and confirm the minimum nearest-neighbor spacing
found is >= the requested spacing parameter (sanity: the pattern isn't secretly denser
than asked)."""
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "generators"))

import square, hexagonal, concentric, fibonacci_spiral, golden_angle  # noqa: E402
import rectangular, archimedean_spiral, ring_offset_concentric  # noqa: E402
import poisson_disk, jittered_lattice  # noqa: E402


def min_nn_distance(coords):
    if len(coords) < 2:
        return float("inf")
    tree = cKDTree(coords)
    d, _ = tree.query(coords, k=2)
    return float(d[:, 1].min())


def check(name, coords, meta, a_hole_um, expected_spacing_um=None):
    n = len(coords)
    min_d = min_nn_distance(coords)
    no_overlap = min_d > a_hole_um or n < 2
    print(f"\n--- {name} ---")
    print(f"  requested N={meta['N_requested']}, actual N={meta['N_actual']}, "
          f"a_hole_um={a_hole_um}, spacing_params={meta['nominal_spacing_desc']}")
    print(f"  first 5 coords (um): {coords[:5].tolist()}")
    print(f"  min nearest-neighbor distance: {min_d:.2f}um "
          f"(must be > a_hole_um={a_hole_um}): {'OK' if no_overlap else 'FAIL -- OVERLAP'}")
    if expected_spacing_um is not None:
        ratio = min_d / expected_spacing_um
        print(f"  min NN distance / requested spacing = {ratio:.3f} "
              f"(expect ~1.0 for a lattice; {'OK' if 0.9 <= ratio <= 1.11 else 'CHECK'})")
    return no_overlap


all_ok = True

c, m = square.generate(N=50, a_hole_um=400.0, pitch_um=900.0)
all_ok &= check("square", c, m, 400.0, expected_spacing_um=900.0)

c, m = hexagonal.generate(N=50, a_hole_um=400.0, pitch_um=900.0)
all_ok &= check("hexagonal", c, m, 400.0, expected_spacing_um=900.0)

c, m = concentric.generate(N=50, a_hole_um=400.0, ring_spacing_um=900.0, holes_per_ring0=6)
all_ok &= check("concentric", c, m, 400.0, expected_spacing_um=None)

c, m = fibonacci_spiral.generate(N=50, a_hole_um=400.0, c_um=900.0)
all_ok &= check("fibonacci_spiral", c, m, 400.0, expected_spacing_um=None)

c, m = golden_angle.generate(N=50, a_hole_um=400.0, c_um=900.0)
all_ok &= check("golden_angle", c, m, 400.0, expected_spacing_um=None)

# Confirm golden_angle and fibonacci_spiral produce identical coordinates (same formula)
c1, m1 = fibonacci_spiral.generate(N=50, a_hole_um=400.0, c_um=900.0)
c2, m2 = golden_angle.generate(N=50, a_hole_um=400.0, c_um=900.0)
identical = np.allclose(c1, c2)
print(f"\n--- fibonacci_spiral vs golden_angle identity check ---")
print(f"  coordinates identical: {identical} (expected True -- documented as the same pattern)")
print(f"  family labels differ: {m1['family']} vs {m2['family']} (expected True -- distinguishable in metadata)")
all_ok &= identical

c, m = rectangular.generate(N=50, a_hole_um=400.0, pitch_x_um=900.0, pitch_y_um=1400.0)
all_ok &= check("rectangular (anisotropic)", c, m, 400.0, expected_spacing_um=900.0)
# expected_spacing_um=900.0 (the SMALLER of pitch_x/pitch_y) since min NN distance on
# an anisotropic lattice is set by the tighter of the two axes near the origin

c, m = archimedean_spiral.generate(N=50, a_hole_um=400.0, c_um=300.0)
all_ok &= check("archimedean_spiral", c, m, 400.0, expected_spacing_um=None)

c, m = ring_offset_concentric.generate(N=50, a_hole_um=400.0, ring_spacing_um=900.0, holes_per_ring0=6)
all_ok &= check("ring_offset_concentric", c, m, 400.0, expected_spacing_um=None)

# Confirm rectangular reduces EXACTLY to square when pitch_x_um == pitch_y_um
c1, m1 = square.generate(N=50, a_hole_um=400.0, pitch_um=900.0)
c2, m2 = rectangular.generate(N=50, a_hole_um=400.0, pitch_x_um=900.0, pitch_y_um=900.0)
identical_rect_square = np.allclose(c1, c2)
print(f"\n--- rectangular(pitch_x==pitch_y) vs square identity check ---")
print(f"  coordinates identical: {identical_rect_square} (expected True -- rectangular "
      f"must reduce exactly to square's own lattice at pitch_x_um==pitch_y_um)")
all_ok &= identical_rect_square

# Confirm rotation_deg=0.0 (default) reproduces the EXISTING pre-rotation-support
# output EXACTLY, for all three lattice families that just gained the parameter --
# required before the rotation sweep runs (a bug here would corrupt every
# downstream number in that task).
print(f"\n--- rotation_deg=0.0 exact-reproduction check (square, hexagonal, rectangular) ---")
c_sq_norot, _ = square.generate(N=50, a_hole_um=400.0, pitch_um=900.0)
c_sq_rot0, _ = square.generate(N=50, a_hole_um=400.0, pitch_um=900.0, rotation_deg=0.0)
sq_rot0_identical = np.array_equal(c_sq_norot, c_sq_rot0)
print(f"  square: no-rotation-arg vs rotation_deg=0.0 bit-identical: {sq_rot0_identical} (expected True)")
all_ok &= sq_rot0_identical

c_hex_norot, _ = hexagonal.generate(N=50, a_hole_um=400.0, pitch_um=900.0)
c_hex_rot0, _ = hexagonal.generate(N=50, a_hole_um=400.0, pitch_um=900.0, rotation_deg=0.0)
hex_rot0_identical = np.array_equal(c_hex_norot, c_hex_rot0)
print(f"  hexagonal: no-rotation-arg vs rotation_deg=0.0 bit-identical: {hex_rot0_identical} (expected True)")
all_ok &= hex_rot0_identical

c_rect_norot, _ = rectangular.generate(N=50, a_hole_um=400.0, pitch_x_um=900.0, pitch_y_um=1400.0)
c_rect_rot0, _ = rectangular.generate(N=50, a_hole_um=400.0, pitch_x_um=900.0, pitch_y_um=1400.0, rotation_deg=0.0)
rect_rot0_identical = np.array_equal(c_rect_norot, c_rect_rot0)
print(f"  rectangular: no-rotation-arg vs rotation_deg=0.0 bit-identical: {rect_rot0_identical} (expected True)")
all_ok &= rect_rot0_identical

# Confirm rotation actually rotates (coordinates change at rotation_deg!=0) while
# N_actual stays exactly invariant (rotation preserves every pairwise distance and
# every distance-from-origin, so overlap rejection's kept-point SET cannot change --
# see base_generator.rotate_points's own docstring for why this isn't assumed, just
# a direct consequence of rotation being an origin-fixing isometry).
print(f"\n--- rotation_deg=30.0 sanity check (square, hexagonal, rectangular) ---")
for gen, kwargs, label in [
    (square.generate, {"pitch_um": 900.0}, "square"),
    (hexagonal.generate, {"pitch_um": 900.0}, "hexagonal"),
    (rectangular.generate, {"pitch_x_um": 900.0, "pitch_y_um": 1400.0}, "rectangular"),
]:
    c0, m0_ = gen(N=50, a_hole_um=400.0, rotation_deg=0.0, **kwargs)
    c30, m30 = gen(N=50, a_hole_um=400.0, rotation_deg=30.0, **kwargs)
    coords_differ = not np.allclose(c0, c30)
    n_actual_same = (m0_["N_actual"] == m30["N_actual"])
    # pairwise-distance invariance: sorted pairwise distances must match exactly
    # (confirms rotation is a true rigid rotation, not an accidental distortion)
    d0 = np.sort(np.linalg.norm(c0[:, None, :] - c0[None, :, :], axis=-1), axis=None)
    d30 = np.sort(np.linalg.norm(c30[:, None, :] - c30[None, :, :], axis=-1), axis=None)
    distances_preserved = np.allclose(d0, d30)
    print(f"  {label}: coords differ at 30deg: {coords_differ} (expected True), "
          f"N_actual invariant: {n_actual_same} (expected True, {m0_['N_actual']}=={m30['N_actual']}), "
          f"pairwise distances preserved: {distances_preserved} (expected True)")
    all_ok &= coords_differ and n_actual_same and distances_preserved

# Confirm archimedean_spiral is NOT the same pattern as fibonacci_spiral (opposite
# assertion from the golden_angle identity check above)
c1, m1 = fibonacci_spiral.generate(N=50, a_hole_um=400.0, c_um=300.0)
c2, m2 = archimedean_spiral.generate(N=50, a_hole_um=400.0, c_um=300.0)
different_spirals = not np.allclose(c1, c2)
print(f"\n--- archimedean_spiral vs fibonacci_spiral DIFFERENCE check ---")
print(f"  coordinates identical: {not different_spirals} (expected False -- these are "
      f"DIFFERENT patterns: r=c*theta linear-in-angle growth vs r=c*sqrt(n) growth "
      f"with golden-angle stepping)")
all_ok &= different_spirals

c, m = poisson_disk.generate(N=50, a_hole_um=400.0, spacing_factor=1.5, seed=0)
all_ok &= check("poisson_disk (seed=0)", c, m, 400.0, expected_spacing_um=None)
print(f"  seed used (from metadata): {m['seed']}, domain_retries: {m['domain_retries']}")

c, m = jittered_lattice.generate(N=50, a_hole_um=400.0, pitch_um=900.0, jitter_fraction=0.3, seed=0)
all_ok &= check("jittered_lattice (jitter=0.3, seed=0)", c, m, 400.0, expected_spacing_um=None)

# STOCHASTIC-GENERATOR-SPECIFIC CHECKS: same seed -> identical output (reproducibility);
# different seed -> different output (confirms randomness is actually exercised, not a
# no-op RNG call)
c_s0a, _ = poisson_disk.generate(N=50, a_hole_um=400.0, spacing_factor=1.5, seed=0)
c_s0b, _ = poisson_disk.generate(N=50, a_hole_um=400.0, spacing_factor=1.5, seed=0)
c_s1, _ = poisson_disk.generate(N=50, a_hole_um=400.0, spacing_factor=1.5, seed=1)
same_seed_reproducible = np.allclose(c_s0a, c_s0b)
diff_seed_different = (c_s0a.shape != c_s1.shape) or not np.allclose(c_s0a, c_s1)
print(f"\n--- poisson_disk reproducibility check ---")
print(f"  seed=0 called twice, identical output: {same_seed_reproducible} (expected True)")
print(f"  seed=0 vs seed=1, different output: {diff_seed_different} (expected True)")
all_ok &= same_seed_reproducible and diff_seed_different

j_s0a, _ = jittered_lattice.generate(N=50, a_hole_um=400.0, pitch_um=900.0, jitter_fraction=0.3, seed=0)
j_s0b, _ = jittered_lattice.generate(N=50, a_hole_um=400.0, pitch_um=900.0, jitter_fraction=0.3, seed=0)
j_s1, _ = jittered_lattice.generate(N=50, a_hole_um=400.0, pitch_um=900.0, jitter_fraction=0.3, seed=1)
same_seed_reproducible_j = np.allclose(j_s0a, j_s0b)
diff_seed_different_j = (j_s0a.shape != j_s1.shape) or not np.allclose(j_s0a, j_s1)
print(f"\n--- jittered_lattice reproducibility check ---")
print(f"  seed=0 called twice, identical output: {same_seed_reproducible_j} (expected True)")
print(f"  seed=0 vs seed=1, different output: {diff_seed_different_j} (expected True)")
all_ok &= same_seed_reproducible_j and diff_seed_different_j

# Confirm jittered_lattice reduces EXACTLY to hexagonal when jitter_fraction=0.0
c1, m1 = hexagonal.generate(N=50, a_hole_um=400.0, pitch_um=900.0)
c2, m2 = jittered_lattice.generate(N=50, a_hole_um=400.0, pitch_um=900.0, jitter_fraction=0.0, seed=0)
identical_jitter0 = np.allclose(c1, c2)
print(f"\n--- jittered_lattice(jitter_fraction=0.0) vs hexagonal identity check ---")
print(f"  coordinates identical: {identical_jitter0} (expected True -- zero jitter must "
      f"reduce exactly to hexagonal.py's own output, regardless of seed)")
all_ok &= identical_jitter0
# also confirm this holds regardless of WHICH seed is used, since jitter magnitude is
# zero and no random draw should be able to move a point at jitter_fraction=0.0
c3, m3 = jittered_lattice.generate(N=50, a_hole_um=400.0, pitch_um=900.0, jitter_fraction=0.0, seed=42)
all_ok &= np.allclose(c1, c3)
print(f"  also holds at a different seed (seed=42): {np.allclose(c1, c3)} (expected True)")

# Poisson-disk minimum-distance contract: min_distance_um = a_hole_um*spacing_factor,
# check the ACTUAL min NN distance across several seeds is never below that contract
# (not just "greater than a_hole_um" as the generic check above already verifies)
min_distances = []
for sd in range(5):
    cc, _ = poisson_disk.generate(N=60, a_hole_um=400.0, spacing_factor=1.5, seed=sd)
    min_distances.append(min_nn_distance(cc))
contract_um = 400.0 * 1.5
print(f"\n--- poisson_disk minimum-distance contract check (5 seeds) ---")
print(f"  min NN distances: {[f'{d:.1f}' for d in min_distances]}um "
      f"(all must be >= contract={contract_um}um)")
contract_ok = all(d >= contract_um - 1e-6 for d in min_distances)
print(f"  {'OK' if contract_ok else 'FAIL'}")
all_ok &= contract_ok

# Overlap-rejection stress test: request a spacing SMALLER than a_hole_um, confirm
# N_actual << N_requested (honest rejection, not silent overlap)
c_dense, m_dense = square.generate(N=50, a_hole_um=900.0, pitch_um=400.0)
print(f"\n--- overlap-rejection stress test (pitch < a_hole_um) ---")
print(f"  square, a_hole_um=900 > pitch_um=400: requested N=50, actual N={m_dense['N_actual']} "
      f"(expect << 50, since most candidates collide)")
min_d_dense = min_nn_distance(c_dense)
print(f"  min NN distance = {min_d_dense:.2f}um (must be > 900um): "
      f"{'OK' if min_d_dense > 900.0 or m_dense['N_actual'] < 2 else 'FAIL'}")

print(f"\n=== SPOT-CHECK OVERALL: {'PASS' if all_ok else 'FAIL'} ===")
if not all_ok:
    sys.exit(1)
