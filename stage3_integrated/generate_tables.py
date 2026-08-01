"""
All Phase A tables. Renders literature.py's CITATIONS dict directly (never hand-copied
so it cannot drift out of sync), extends stage3_human_vision/comparison.py's error
budget schema (does not invent a new one), and propagates literature.py's stated
uncertainty ranges into the primary optimum-aperture number.
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
_STAGE3HV_DIR = os.path.abspath(os.path.join(HERE, "..", "stage3_human_vision"))
_STAGE2_FIXED_DIR = os.path.abspath(os.path.join(HERE, "..", "stage2_fixed"))
for _d in (_STAGE3HV_DIR, _STAGE2_FIXED_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import literature  # noqa: E402
import validation_gate  # noqa: E402 (stage2_fixed -- the bug-fixed validation gate)
import comparison as hv_comparison  # noqa: E402
import photometry  # noqa: E402
import contrast  # noqa: E402

OUT_DIR = os.path.join(HERE, "outputs")


def table_literature_citations():
    """Renders literature.py's CITATIONS dict directly -- never hand-copied."""
    rows = []
    for key, entry in literature.CITATIONS.items():
        rows.append({"key": key, "type": entry["type"], "statement": entry["statement"],
                     "source": entry["source"], "fidelity": entry["fidelity"]})
    return pd.DataFrame(rows)


def table_validation_statistics():
    """rel_error vs closed-form for every metric the Airy validation gate checks."""
    gate = validation_gate.run_validation_gate()
    rows = []
    for r in gate["rows"]:
        rows.append({"metric": r["label"], "numeric_um": r["numeric_um"], "closed_form_um": r["closed_form_um"],
                     "rel_error_pct": r["rel_error"] * 100, "tolerance_pct": r["tolerance"] * 100,
                     "passed": r["passed"]})
    return pd.DataFrame(rows)


def table_uncertainty_propagation(combined_grid_path):
    """
    Propagates literature.py's stated uncertainty ranges into the primary optimum-
    aperture number (r_EE_50 optimum, per M) -- turning the "heuristic"/"approximate"
    fidelity notes into a quantified sensitivity rather than a docstring caveat alone.

    Two parameters carry an explicit stated range in literature.py/photometry.py:
      - HEURISTIC_OCULAR_TRANSMISSION: 0.85-0.95 (this project's own round stand-in,
        literature.py has no cited precise value -- see photometry.py)
      - CSF peak location: photopic ~4cpd vs Mannos-Sakrison ~8cpd (a genuine
        published-model disagreement, not an uncertainty band on one model)

    Ocular transmission does not enter r_EE(50%) at all (a pure geometric/energy
    metric) -- it only affects photometry-derived quantities (Trolands, photon flux,
    SNR-bound acuity). This table makes that explicit rather than silently reporting
    "no sensitivity" without saying why.
    """
    df = pd.read_csv(combined_grid_path)
    rows = []
    for M in sorted(df["M_diopters"].unique()):
        g = df[np.isclose(df["M_diopters"], M)].sort_values("a_hole_um")
        r_ee_50_opt = g.loc[g["r_EE_50_um"].idxmin(), "a_hole_um"]

        # Ocular transmission sensitivity -- propagated into photon flux / SNR bound,
        # NOT into r_EE_50 (see docstring: geometric metric, transmission-independent).
        ref_flux_mid = g.loc[np.isclose(g["a_hole_um"], 400.0), "photon_flux_density_per_s_per_m2"].iloc[0]
        flux_low = ref_flux_mid * (0.85 / 0.90)  # HEURISTIC_OCULAR_TRANSMISSION default is 0.90
        flux_high = ref_flux_mid * (0.95 / 0.90)

        rows.append({
            "M_diopters": M,
            "r_EE_50_optimum_um": r_ee_50_opt,
            "r_EE_50_sensitivity_to_ocular_transmission": "none (geometric metric, transmission-independent)",
            "photon_flux_at_400um_mid_(tau=0.90)": ref_flux_mid,
            "photon_flux_at_400um_low_(tau=0.85)": flux_low,
            "photon_flux_at_400um_high_(tau=0.95)": flux_high,
            "photon_flux_range_pct": (flux_high - flux_low) / ref_flux_mid * 100,
            "csf_peak_photopic_cpd": 4.0,
            "csf_peak_mannos_sakrison_cpd": 8.0,
            "csf_peak_disagreement_note": "genuine published-model disagreement, not an uncertainty band",
        })
    return pd.DataFrame(rows)


def table_validation_regression_stats():
    """
    Re-exports stage3_human_vision/validate_against_literature.py's own output
    (RMSE/MAE/R^2/Pearson r, predicted LogMAR vs literature.get('ideal_pinhole_
    wang_2009'), swept across M and predictor) -- not recomputed here, matching this
    module's own rule (renders/re-exports, does not invent new numbers). This is the
    project's first (and only) direct regression-agreement statistic against a
    multi-point published dataset -- see stage3_human_vision/README.md's "Validation
    against literature" section for the sensitivity-across-M finding.
    """
    path = os.path.join(_STAGE3HV_DIR, "outputs", "validation_regression_stats.csv")
    return pd.read_csv(path)


def table_error_budget_extended():
    """Extends stage3_human_vision/comparison.py's error_budget() schema -- same
    columns, does not invent a new one -- adding the two findings unique to this
    integration (retina-plane FWHM ring-hopping, Strehl genuine oscillation)."""
    base = hv_comparison.error_budget(
        polychromatic_shift_um=85.7,
        ocular_aberration_note="~0.33-0.38 micron RMS over a 6mm pupil in normal eyes; "
                                "expected much smaller at pinhole-scale apertures.",
    )
    base.extend([
        {"contributor": "Retina-plane FWHM ring-hopping",
         "quantified": True,
         "magnitude": "confirmed present (not just at the cornea plane) -- FWHM jumps "
                       "from 4.7um to 154.7um between adjacent 250um-spaced test "
                       "apertures at M=4D; NOT a reliable single-value metric at the "
                       "retina plane for this system",
         "source": "stage3_integrated/run_full_theory_sweep.py sweep_1_retina_fwhm(), this project"},
        {"contributor": "Strehl ratio non-monotonicity",
         "quantified": True,
         "magnitude": "confirmed GENUINE (not a sampling artifact) -- a 10x finer "
                       "aperture grid revealed MORE local maxima (6-7) and larger "
                       "peak-to-peak swings (up to 8.4x), not fewer/smaller; Strehl is "
                       "not a reliable single-peak optimizer for this system",
         "source": "stage3_integrated/run_full_theory_sweep.py sweep_2_fine_strehl(), this project"},
    ])
    return pd.DataFrame(base)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    combined_path = os.path.join(OUT_DIR, "combined_grid_550nm_12mm.csv")

    table_literature_citations().to_csv(os.path.join(OUT_DIR, "table_literature_citations.csv"), index=False)
    table_validation_statistics().to_csv(os.path.join(OUT_DIR, "table_validation_statistics.csv"), index=False)
    table_uncertainty_propagation(combined_path).to_csv(os.path.join(OUT_DIR, "table_uncertainty_propagation.csv"), index=False)
    table_validation_regression_stats().to_csv(os.path.join(OUT_DIR, "table_validation_regression_stats.csv"), index=False)
    table_error_budget_extended().to_csv(os.path.join(OUT_DIR, "table_error_budget_extended.csv"), index=False)

    print("Wrote table_literature_citations.csv, table_validation_statistics.csv, "
          "table_uncertainty_propagation.csv, table_validation_regression_stats.csv, "
          "table_error_budget_extended.csv")


if __name__ == "__main__":
    main()
