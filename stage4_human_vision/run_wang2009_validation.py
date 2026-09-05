"""
Re-runs Stage 4's Wang (2009) "Ideal Pinhole" validation against the corrected optics
(stage2_fixed/, post the import-shadowing fix -- see RESULTS.md's "Re-run against
corrected optics" section and PHYSICS_AUDIT.md). No dedicated runner for this existed
before this fix (RESULTS.md's original numbers were produced by an uncommitted,
one-off script); this one is written to reproduce that exact procedure so the
before/after comparison is apples to apples.

Dataset: literature.get('ideal_pinhole_wang_2009') via stage3_human_vision/literature.py
-- 5 apertures (500/750/1000/1200/1500um), observed LogMAR (0.28/0.31/1.00/0.40/0.50),
evaluated as a sensitivity sweep across M=[0,2,5]D (the paper's own summary table has
no per-point M -- same limitation this project's other Wang-2009 comparisons already
documented; the same 5 observed values are reused at each M).

Predictor: run_stage4_point(...).acuity['logmar'] -- Stage 4's own "recommended" model
(config-selected, not chosen post-hoc here), matching RESULTS.md Section 2's "Stage 4
recommended" row exactly. No parameter (adaptation, config defaults, or anything in
acuity.py's own model selection) is changed from its existing, already-locked value.

Run: python3 -m stage4_human_vision.run_wang2009_validation
"""
import os

import pandas as pd

from .pipeline import run_stage4_point
from .validation import regression_stats

APERTURES_UM = [500, 750, 1000, 1200, 1500]
OBSERVED_LOGMAR = [0.28, 0.31, 1.00, 0.40, 0.50]
M_VALUES = [0.0, 2.0, 5.0]
WAVELENGTH_NM = 550.0
D_GAP_MM = 12.0

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    for M in M_VALUES:
        for a_um, obs in zip(APERTURES_UM, OBSERVED_LOGMAR):
            r = run_stage4_point(a_hole_um=a_um, wavelength_nm=WAVELENGTH_NM,
                                  d_gap_mm=D_GAP_MM, M_diopters=M)
            if not r.junction_check_passed:
                rows.append({"M_diopters": M, "a_hole_um": a_um, "observed_logmar": obs,
                             "predicted_logmar": None, "recommended_model": None,
                             "junction_check_passed": False})
                continue
            rows.append({
                "M_diopters": M, "a_hole_um": a_um, "observed_logmar": obs,
                "predicted_logmar": r.acuity["logmar"],
                "recommended_model": r.acuity["recommended_model"],
                "junction_check_passed": True,
            })
            print(f"  a={a_um}um M={M}D ... predicted={r.acuity['logmar']:.4f} "
                  f"(observed={obs:.3f}) [{r.acuity['recommended_model']}]")

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT_DIR, "wang2009_validation_postfix_predicted.csv"), index=False)

    stats_rows = []
    for M in M_VALUES:
        g = df[df.M_diopters == M]
        stats = regression_stats(g["observed_logmar"].tolist(), g["predicted_logmar"].tolist())
        stats_rows.append({"M_diopters": M, "predictor": "stage4_recommended", **stats})
    stats_df = pd.DataFrame(stats_rows)
    stats_df.to_csv(os.path.join(OUT_DIR, "wang2009_validation_postfix_stats.csv"), index=False)

    print("\n=== Regression stats (post import-shadowing fix, against stage2_fixed/) ===")
    print(stats_df.to_string(index=False))
    return df, stats_df


if __name__ == "__main__":
    main()
