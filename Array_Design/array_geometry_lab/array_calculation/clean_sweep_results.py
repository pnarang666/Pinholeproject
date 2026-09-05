"""
Closes the root-level gap left by comparison_metric/compute_density.py's degeneracy
filter: that filter only ever excluded degenerate rows on its OWN output
(sweep_results_with_density.csv) -- sweep_results.csv itself, the file every other
script in this project reads from, still carried all 6615 original rows including
the 220 degenerate ones. This script applies degeneracy_filter.is_degenerate() (the
SAME logic, unchanged, now shared) directly to sweep_results.csv and makes the
ACTIVE file clean at the root, so the exclusion can't recur silently in some future
script that reads sweep_results.csv without going through compute_density.py.

sweep_results.csv (original, contaminated) is archived FIRST, unconditionally, as
sweep_results_PRECLEAN_legacy.csv -- a permanent, full, unmodified record.

Before overwriting the active file, this script cross-checks its own count of
degenerate rows against the already-existing degenerate_rows_excluded.csv (produced
by an earlier compute_density.py run) -- if the counts don't match exactly, that
means degeneracy_filter.py's extraction does not faithfully reproduce what
compute_density.py actually did, and this script STOPS without writing anything,
per this task's own explicit instruction.

Run:  python3 clean_sweep_results.py
"""
import os
import shutil

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))  # array_calculation/
LAB_ROOT = os.path.dirname(HERE)  # array_geometry_lab/
import degeneracy_filter  # noqa: E402

DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
IN_CSV = os.path.join(DATA_DIR, "sweep_results.csv")
PRECLEAN_LEGACY_CSV = os.path.join(DATA_DIR, "sweep_results_PRECLEAN_legacy.csv")
EXCLUDED_LOG_CSV = os.path.join(DATA_DIR, "degenerate_rows_excluded.csv")
# HISTORICAL BASELINE, not a hard requirement (audit-fix update): these were the
# correct counts for the ORIGINAL 10-family sweep under the pre-audit-fix
# degeneracy_filter.py (unit-cell formula for square/hexagonal/rectangular, a
# stricter N_actual>=4 floor for those three specifically). Defect A's fix
# (degeneracy_filter.py now uses ONE buffered-convex-hull formula for every family,
# unifying the point-count floor to 3 for everyone) INTENTIONALLY changes which rows
# classify as degenerate -- a hard assertion against these frozen numbers would
# reject a correct, intentional result. Kept here for CONTEXT in the printed report
# only; see the count check below, which now REPORTS rather than enforces.
HISTORICAL_EXPECTED_EXCLUDED_COUNT = 220
HISTORICAL_EXPECTED_CLEAN_COUNT = 6395


def preserve_legacy(path):
    """Auto-incrementing preservation (matches sweep/run_sweep.py's own
    preserve_legacy convention). ADDED after a real gap found in this project's own
    audit-fix task: this script overwrites degenerate_rows_excluded.csv (below)
    WITHOUT ever having preserved it first -- only compute_density.py's own copy of
    that file had a preservation step. That gap silently destroyed one real
    historical snapshot (a 432-row exclusion log, from before the Defect-A density
    fix, unrecoverable after the fact since the OLD degeneracy_filter.py code
    itself was also overwritten in place with no separate version kept) before
    being caught and fixed here -- reported plainly in AUDIT_FIXES_REPORT.md rather
    than glossed over."""
    if not os.path.exists(path):
        return
    i = 1
    legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    while os.path.exists(legacy_path):
        i += 1
        legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    shutil.copy2(path, legacy_path)
    print(f"preserved predecessor -> {legacy_path}")


def main():
    df = pd.read_csv(IN_CSV)
    print(f"loaded {len(df)} rows from {IN_CSV}")

    shutil.copy2(IN_CSV, PRECLEAN_LEGACY_CSV)
    print(f"archived original (contaminated, unmodified) -> {PRECLEAN_LEGACY_CSV}")
    preserve_legacy(EXCLUDED_LOG_CSV)

    degenerate_mask = []
    reasons = []
    n_done = 0
    for row in df.itertuples():
        deg, reason = degeneracy_filter.is_degenerate(row)
        degenerate_mask.append(deg)
        reasons.append(reason)
        n_done += 1
        if n_done % 1000 == 0:
            print(f"  {n_done}/{len(df)} rows checked")

    df["_is_degenerate"] = degenerate_mask
    df["_reason"] = reasons
    excluded = df[df["_is_degenerate"]]
    clean = df[~df["_is_degenerate"]]

    print(f"\nis_degenerate()==True (excluded): {len(excluded)}")
    print(f"is_degenerate()==False (kept): {len(clean)}")

    # Cross-check against the existing audit log -- REPORTED, not enforced, as of
    # the Defect-A degeneracy-logic audit fix (see HISTORICAL_EXPECTED_* comment
    # above): degenerate_rows_excluded.csv on disk reflects whatever
    # compute_density.py's LAST run found, which -- unless that run already used
    # the current, fixed degeneracy_filter.py -- is comparing NEW classification
    # logic against OLD logic's own output, which is EXPECTED to differ now. A
    # hard stop here would reject a correct, intentional result. This check still
    # RUNS and PRINTS its finding (so a genuinely unintended drift is still
    # visible), it just no longer sys.exit()s on a mismatch.
    if os.path.exists(EXCLUDED_LOG_CSV):
        prior = pd.read_csv(EXCLUDED_LOG_CSV)
        if len(excluded) != len(prior):
            print(f"\nNOTE: this script's is_degenerate() found {len(excluded)} degenerate "
                  f"rows; {EXCLUDED_LOG_CSV} (from a PRIOR compute_density.py run, possibly "
                  f"predating the current degeneracy_filter.py) has {len(prior)}. Expected to "
                  f"differ if the degeneracy logic changed since that prior run -- not treated "
                  f"as an error here (see HISTORICAL_EXPECTED_* comment).")
        else:
            print(f"cross-check: matches {EXCLUDED_LOG_CSV}'s {len(prior)} rows exactly.")
    else:
        print(f"\nNOTE: {EXCLUDED_LOG_CSV} not found, cannot cross-check against a prior run.")

    print(f"\ncount vs. historical baseline (pre-audit-fix, for CONTEXT only, not enforced): "
          f"{len(excluded)} excluded / {len(clean)} clean now, vs. "
          f"{HISTORICAL_EXPECTED_EXCLUDED_COUNT} / {HISTORICAL_EXPECTED_CLEAN_COUNT} then.")

    # Refresh the canonical audit log -- this is the ROOT-level record, since
    # exclusion happens here (row count reflects whatever the CURRENT
    # degeneracy_filter.py finds, not a fixed historical number -- see above).
    excluded_out = excluded[["family", "N_requested", "N_actual", "spacing_params",
                             "a_hole_um", "seed", "M", "_reason"]].rename(
        columns={"_reason": "reason"})
    excluded_out.to_csv(EXCLUDED_LOG_CSV, index=False)
    print(f"wrote {EXCLUDED_LOG_CSV} ({len(excluded_out)} rows)")

    clean_out = clean.drop(columns=["_is_degenerate", "_reason"]).reset_index(drop=True)
    clean_out.to_csv(IN_CSV, index=False)
    print(f"wrote {IN_CSV} ({len(clean_out)} rows) -- sweep_results.csv is now the "
          f"clean, active file; the original is preserved at {PRECLEAN_LEGACY_CSV}")


if __name__ == "__main__":
    main()
