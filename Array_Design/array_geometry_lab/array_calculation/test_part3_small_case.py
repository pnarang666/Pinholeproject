"""Required check before Part 4: Parts 1-3 confirmed working on one small test case
(one family, one N, one M) before running the full sweep."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "generators"))
sys.path.insert(0, os.path.join(HERE, "margins"))  # renamed from "evaluation" --
                          # see array_calculation/README.md

import square  # noqa: E402
import active_pairs as ap  # noqa: E402
import ghost_margin as gm  # noqa: E402
import vignetting_robustness as vr  # noqa: E402

D_PUPIL_UM = 4000.0
M = 4.0

a_hole_um = gm.load_acuity_optimal_aperture(M)
print(f"a_hole({M}D) = {a_hole_um}um (read live from per_M_optimum_map.csv)")

coords, meta = square.generate(N=30, a_hole_um=a_hole_um, pitch_um=1200.0)
print(f"generated {meta['N_actual']}/{meta['N_requested']} holes, family={meta['family']}")

pairs, active_idx = ap.active_pairs(coords, D_PUPIL_UM, a_hole_um)
print(f"active holes under pupil at phi=0: {len(active_idx)}, active pairs: {len(pairs)}")

per_M = gm.evaluate_per_M(coords, D_PUPIL_UM, M)
print(f"per_M ghost margin: {per_M}")

glob = gm.evaluate_global(coords, D_PUPIL_UM)
print(f"\nglobal worst-case margin: {glob['worst_case_margin']:.4f} at M={glob['worst_case_M']}")
print(f"ambiguity note: {glob['a_hole_um_AMBIGUOUS']}")

vig = vr.worst_case_across_phi(coords, D_PUPIL_UM, M, a_hole_um)
print(f"\nvignetting worst-case margin across phi: {vig['worst_case_vignetting_margin']:.4f} "
      f"at phi={vig['worst_case_phi_deg']}deg")

print("\n=== Part 3 small-case test: OK (no exceptions, all three modules produced results) ===")
