"""
Re-runs the EXACT 36-point sweep of RESULTS.md Passes 1-3 (apertures
[300,400,700,1000]um x pitches [700,900,1200,1500,2000,2500,3200,4000,4800]um, M=4D,
d_gap=12mm, 550nm, D_pupil=4000um, square packing) under both ghost-separation models,
on stage2_fixed's post-lens-wavelength-fix optics, and writes the side-by-side
comparison RESULTS.md's "Pass 4" section reports.

Three columns of history are being separated here, deliberately:
  (a) ghosting_sweep_harmonic_legacy.csv  -- legacy formula, PRE-fix optics, n_offsets
      unknown (script lost; likely 15 or 25 given contemporaneous defaults) (29 Jul
      2026; the lens-wavelength fix landed 6 Aug 2026). Read from disk, not re-run.
      (Originally at ghosting_sweep_harmonic.csv; copied to the _legacy name during the
      Array_Design N_OFFSETS fix below, RESULTS.md's Pass 1-3 citations of the original
      filename are unaffected since that file is untouched.)
  (b) this run, separation_model="legacy"    -- legacy formula, POST-fix optics.
  (c) this run, separation_model="corrected" -- corrected formula, POST-fix optics.
(a)->(b) isolates the optics fix; (b)->(c) isolates the formula correction.

N_OFFSETS FIX (Array_Design ANALYSIS.md F3, applied here): earlier runs of this script
used classify()'s n_offsets=15 default. F3 found 15/25 miss the worst pupil alignment
at the pitches that matter most (2900um: reports N_eff_worst=1 at n_offsets<=25, the
correct 0 only at 41+; 3900um similarly for N_eff_best). N_OFFSETS below matches
joint_design_space.py's own resolved value (61, where 61 and 121 agree). The pre-fix
(n_offsets=15) sweep is preserved at ghosting_sweep_corrected_formula_legacy_n15.csv /
ghosting_myopia_robustness_corrected_legacy_n15.csv before this script overwrites the
canonical filenames -- diffed in main() below rather than assumed unchanged.

Run:  python3 rerun_corrected_sweep.py     (~2 min: 4 PSF propagations, then cached)
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import corrected_regime as cr  # noqa: E402

APERTURES_UM = [300, 400, 700, 1000]
PITCHES_UM = [700, 900, 1200, 1500, 2000, 2500, 3200, 4000, 4800]
M_MAIN = 4.0
M_ROBUSTNESS = [1.0, 2.0, 4.0, 6.0, 8.0]
N_OFFSETS = 61  # see module docstring's N_OFFSETS FIX note (ANALYSIS.md F3)


def run_sweep(model, M=M_MAIN):
    rows = []
    for a_um in APERTURES_UM:
        for s_um in PITCHES_UM:
            rows.append(cr.classify(a_um, s_um, M, separation_model=model, n_offsets=N_OFFSETS))
    return pd.DataFrame(rows)


def main():
    print(f"phase2_retina in use: {cr.assert_corrected_optics()}")
    print("verifying the classifier reproduces ghosting_regime.py on the legacy path:")
    cr.self_check()

    legacy = run_sweep("legacy")
    corrected = run_sweep("corrected")

    merge_keys = ["a_hole_um", "pitch_um", "M_diopters"]
    cols = ["delta_r_um", "f0_cpd", "mtf_f0", "fundamental_margin", "worst_n",
            "worst_margin", "worst_f_cpd", "regime_fundamental", "regime_harmonic",
            "N_eff_worst"]
    both = legacy[merge_keys + cols].merge(
        corrected[merge_keys + cols], on=merge_keys, suffixes=("_legacy", "_corrected"))

    prior_path = os.path.join(HERE, "ghosting_sweep_harmonic.csv")
    prior = pd.read_csv(prior_path).rename(columns={
        "regime": "regime_prefix_prerun", "worst_n_harmonic": "worst_n_prefix_prerun",
        "worst_margin": "worst_margin_prefix_prerun",
        "fundamental_margin": "fundamental_margin_prefix_prerun"})
    both = both.merge(prior[["a_hole_um", "pitch_um", "regime_prefix_prerun",
                             "worst_n_prefix_prerun", "worst_margin_prefix_prerun",
                             "fundamental_margin_prefix_prerun"]],
                      on=["a_hole_um", "pitch_um"], how="left")

    out = os.path.join(HERE, "ghosting_sweep_corrected_formula.csv")
    both.to_csv(out, index=False)

    n15_path = os.path.join(HERE, "ghosting_sweep_corrected_formula_legacy_n15.csv")
    if os.path.exists(n15_path):
        n15 = pd.read_csv(n15_path)
        merged = both.merge(n15[["a_hole_um", "pitch_um", "regime_harmonic_corrected",
                                 "N_eff_worst_legacy"]],
                            on=["a_hole_um", "pitch_um"], suffixes=("", "_n15"))
        n_changed = int((merged.regime_harmonic_corrected != merged.regime_harmonic_corrected_n15).sum())
        n_neff_changed = int((merged.N_eff_worst_legacy != merged.N_eff_worst_legacy_n15).sum())
        print(f"\nn_offsets=15 -> {N_OFFSETS} (ANALYSIS.md F3 fix) on this 36-point grid: "
              f"N_eff_worst changed at {n_neff_changed}/{len(merged)} points, "
              f"regime_harmonic (corrected formula) changed at {n_changed}/{len(merged)} points")
        if n_changed:
            print(merged[merged.regime_harmonic_corrected != merged.regime_harmonic_corrected_n15]
                  [["a_hole_um", "pitch_um", "regime_harmonic_corrected_n15", "regime_harmonic_corrected"]]
                  .to_string(index=False))

    def tally(series):
        return {r: int((series == r).sum()) for r in ["A", "B", "C"]}

    print("\n=== 36-point sweep, M=4D: regime tallies ===")
    print(f"{'run':<58} {'A':>4} {'B':>4} {'C':>4}")
    print(f"{'(a) legacy formula, PRE-fix optics (recorded CSV, harmonic rule)':<58} "
          f"{tally(both.regime_prefix_prerun)['A']:>4} {tally(both.regime_prefix_prerun)['B']:>4} "
          f"{tally(both.regime_prefix_prerun)['C']:>4}")
    for label, col in [("(b) legacy formula, post-fix optics, fundamental rule", "regime_fundamental_legacy"),
                       ("(b) legacy formula, post-fix optics, harmonic rule", "regime_harmonic_legacy"),
                       ("(c) CORRECTED formula, post-fix optics, fundamental rule", "regime_fundamental_corrected"),
                       ("(c) CORRECTED formula, post-fix optics, harmonic rule", "regime_harmonic_corrected")]:
        t = tally(both[col])
        print(f"{label:<58} {t['A']:>4} {t['B']:>4} {t['C']:>4}")

    print("\n=== per-point detail (dense pitches only; sparse pitches are Regime A in every run) ===")
    dense = both[both.N_eff_worst_legacy > 1].copy()
    print(f"{'a(um)':>6} {'s(um)':>6} {'N_eff':>5} | "
          f"{'dr_leg(um)':>10} {'f0_leg':>7} {'wn_leg':>6} {'wmarg_leg':>9} {'reg_leg':>7} | "
          f"{'dr_cor(um)':>10} {'f0_cor':>7} {'wn_cor':>6} {'wmarg_cor':>9} {'reg_cor':>7}")
    for _, r in dense.iterrows():
        print(f"{r.a_hole_um:6.0f} {r.pitch_um:6.0f} {r.N_eff_worst_legacy:5.0f} | "
              f"{r.delta_r_um_legacy:10.1f} {r.f0_cpd_legacy:7.3f} {r.worst_n_legacy:6.0f} "
              f"{r.worst_margin_legacy:9.1f} {r.regime_harmonic_legacy:>7} | "
              f"{r.delta_r_um_corrected:10.1f} {r.f0_cpd_corrected:7.3f} {r.worst_n_corrected:6.0f} "
              f"{r.worst_margin_corrected:9.3f} {r.regime_harmonic_corrected:>7}")

    n_worst_is_fundamental = int((dense.worst_n_corrected == 1).sum())
    print(f"\nharmonic check (corrected formula): worst harmonic is the FUNDAMENTAL (n=1) "
          f"at {n_worst_is_fundamental}/{len(dense)} dense points "
          f"(legacy: {int((dense.worst_n_legacy == 1).sum())}/{len(dense)})")
    ratio = (dense.worst_margin_corrected / dense.fundamental_margin_corrected)
    print(f"worst-harmonic margin / fundamental-only margin, corrected: "
          f"min {ratio.min():.3f}, max {ratio.max():.3f} "
          f"(legacy: min {(dense.worst_margin_legacy/dense.fundamental_margin_legacy).min():.2f}, "
          f"max {(dense.worst_margin_legacy/dense.fundamental_margin_legacy).max():.2f})")

    # --- myopia robustness, corrected model (Pass 3 claimed robustness across M) ---
    print("\n=== myopia dependence at a_hole=400um, pitch=900um (corrected formula) ===")
    print(f"{'M(D)':>5} {'delta_r(um)':>12} {'f0(cpd)':>8} {'MTF(f0)':>8} {'fund margin':>12} "
          f"{'worst n':>8} {'worst cpd':>10} {'worst margin':>13} {'regime':>7}")
    rob_rows = []
    for M in M_ROBUSTNESS:
        r = cr.classify(400, 900, M, separation_model="corrected", n_offsets=N_OFFSETS)
        rob_rows.append(r)
        print(f"{M:5.1f} {r['delta_r_um']:12.1f} {r['f0_cpd']:8.2f} {r['mtf_f0']:8.4f} "
              f"{r['fundamental_margin']:12.2f} {r['worst_n']:8.0f} {r['worst_f_cpd']:10.2f} "
              f"{r['worst_margin']:13.2f} {r['regime_harmonic']:>7}")
    pd.DataFrame(rob_rows).to_csv(os.path.join(HERE, "ghosting_myopia_robustness_corrected.csv"), index=False)

    print(f"\nwrote {out}")
    print(f"wrote {os.path.join(HERE, 'ghosting_myopia_robustness_corrected.csv')}")


if __name__ == "__main__":
    main()
