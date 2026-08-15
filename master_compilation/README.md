# Master Compilation

Two files, one job: give you a single place to see everything collected across every
stage, and a dashboard to actually look at it.

## Setup (one-time)

```
pip install pandas openpyxl streamlit plotly
```

## Step 1: Compile the master workbook

```
cd Pinholeproject
python3 master_compilation/compile_master_results.py
```

Produces `master_compilation/master_results.xlsx` with 6 sheets:

1. **INDEX_Provenance** -- what every other sheet is, its source file, and what it contains. Read this first.
2. **Master_Grid_Blur_Illum** -- the primary aperture x myopia grid (550nm/12mm), Stage 2/3 physics merged with Stage 3a illumination.
3. **Model_Comparison_RSS_vs_Exact** -- exact numerics vs. the deprecated closed-form RSS formula (Chapter 7's finding).
4. **Stage4_Wang2009_Validation** -- Stage 4's acuity predictor tested against real clinical data, at both the project's default luminance and the paper's actual stated testing luminance. Fails both (R²<0).
5. **Ghosting_Regime_Aperture_x_Pitch** -- the three-regime (A/B/C) ghosting classification, real Barten CSF, full harmonic series.
6. **Brightness_Reconciliation** -- absolute (troland) brightness floors vs. scene luminance, and where they land relative to the reverse-engineered percentage floor.

**Why 6 sheets and not one flat table**: the underlying data has genuinely different
shapes -- aperture x myopia (sheets 2-4), aperture x pitch (sheet 5), and luminance-only
(sheet 6). Forcing these into one table would silently produce NaN-filled rows or
misaligned joins on columns that don't mean the same thing across sources. Every sheet
here is read directly from its real source file via pandas -- nothing is retyped by
hand, so there is no transcription-error risk. If a source file's shape changes, the
script fails loudly rather than silently compiling a stale or wrong file.

Re-run this script any time an underlying sweep changes -- it always reads the current
files on disk, never a cached copy.

## Step 2: Run the dashboard

```
streamlit run master_compilation/dashboard.py
```

8 tabs: an overview/provenance tab, one tab per data sheet (with interactive filtering
and plots, not just a static table dump), a raw sheet browser with CSV export, and a
"Live Point Check" tab that runs one real Stage 2 propagation on demand (~2-5s) to
sanity-check the precomputed sweeps -- if a live point disagrees with the precomputed
grid at the same parameters, that's a real discrepancy worth investigating, not
expected noise.

The dashboard auto-detects when `master_results.xlsx` changes on disk (via file
modification time) and reloads automatically -- no need to restart Streamlit after
re-running the compile script.

## What this does NOT do

Does not recompute any sweep. Every sheet here is a VIEW over work already done in
`stage2_fixed/`, `stage3a/`, `stage3_integrated/`, `stage4_human_vision/`,
`Array_Design/ghosting/`, `model_comparison/`, and `brightness_reconciliation/`. If a
number here looks wrong, the fix belongs in the stage that produced it, not in this
compilation layer -- re-run that stage's own sweep, then re-run
`compile_master_results.py` to pick up the change.
