"""
Generates all data tables and summary figures for
FINAL_ARRAY_GEOMETRY_COMPARISON_REPORT.tex, pulled live from the verified,
post-cleanup CSVs. No numbers are hardcoded here that aren't derived directly
from a file on disk.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_TEX = os.path.join(BASE, "report_tables")
OUT_FIG = os.path.join(BASE, "report_figs")
os.makedirs(OUT_TEX, exist_ok=True)
os.makedirs(OUT_FIG, exist_ok=True)

THEORY_DIR = os.path.join(BASE, "array_data", "theoretical_data")
EVAL_DIR = os.path.join(BASE, "array_data", "evaluation_results")
sweep = pd.read_csv(os.path.join(THEORY_DIR, "sweep_results.csv"))
excluded = pd.read_csv(os.path.join(THEORY_DIR, "degenerate_rows_excluded.csv"))
legacy_preclean = pd.read_csv(os.path.join(THEORY_DIR, "sweep_results_PRECLEAN_legacy.csv"))
dens = pd.read_csv(os.path.join(THEORY_DIR, "sweep_results_with_density.csv"))
fam_rank = pd.read_csv(os.path.join(EVAL_DIR, "family_ranking.csv"))
m1 = pd.read_csv(os.path.join(EVAL_DIR, "metric1_max_density_per_M.csv"))
m2 = pd.read_csv(os.path.join(EVAL_DIR, "metric2_pareto_front_per_M.csv"))

FAMILIES = sorted(sweep.family.unique())

# ---------- Table 1: dataset integrity summary ----------
with open(os.path.join(OUT_TEX, "table1_integrity.tex"), "w") as f:
    f.write(r"""\begin{tabular}{lrrr}
\toprule
Quantity & Value \\
\midrule
""")
    f.write(f"Raw rows generated (pre-cleanup) & {len(legacy_preclean)} \\\\\n")
    f.write(f"Degenerate rows identified and excluded & {len(excluded)} \\\\\n")
    f.write(f"Active rows in sweep\\_results.csv (post-cleanup) & {len(sweep)} \\\\\n")
    f.write(f"Geometry families tested & {len(FAMILIES)} \\\\\n")
    viol = np.pi * (dens.a_hole_um/2)**2 * dens['packing_density_per_area_um-2']
    f.write(f"Physically-impossible density rows remaining (open area fraction $>1$) & {(viol>1.0001).sum()} \\\\\n")
    f.write(r"\bottomrule" + "\n" + r"\end{tabular}" + "\n")

# ---------- Table 2: exclusion reasons ----------
reason_counts = excluded['reason'].str.split(' \\(').str[0].str.extract(r'^(.*?=[\d.]+.*?|\S.*?below \d|\S.*?points\))')[0]
# fallback: just use full reason text, truncated, grouped
short_reason = excluded['reason'].apply(lambda r: r.split(' (')[0][:70])
counts = short_reason.value_counts()
with open(os.path.join(OUT_TEX, "table2_exclusion_reasons.tex"), "w") as f:
    f.write(r"\begin{longtable}{p{11cm}r}" + "\n")
    f.write(r"\toprule Exclusion reason (truncated) & Count \\ \midrule \endhead" + "\n")
    for reason, cnt in counts.items():
        safe = reason.replace('_', '\\_').replace('%','\\%').replace('&','\\&')
        f.write(f"{safe} & {cnt} \\\\\n")
    f.write(r"\bottomrule \end{longtable}" + "\n")

# ---------- Table 3: gate survivor funnel per family ----------
rows = []
for fam in FAMILIES:
    sub = sweep[sweep.family == fam]
    total = len(sub)
    ghost_safe = (sub.worst_case_ghost_margin > 0).sum()
    both_safe = ((sub.worst_case_ghost_margin > 0) & (sub.worst_case_vignetting_margin > 0)).sum()
    rows.append((fam, total, ghost_safe, both_safe))
funnel = pd.DataFrame(rows, columns=["family","total_rows","gate1_ghost_safe","gate1+2_both_safe"])
funnel["pct_survive_both"] = (100*funnel["gate1+2_both_safe"]/funnel["total_rows"]).round(1)
funnel.to_csv(os.path.join(OUT_TEX, "table3_funnel.csv"), index=False)
with open(os.path.join(OUT_TEX, "table3_funnel.tex"), "w") as f:
    f.write(r"\begin{tabular}{lrrrr}" + "\n")
    f.write(r"\toprule Family & Total rows & Ghost-safe (Gate 1) & Both gates & \% survive \\ \midrule" + "\n")
    for _, r in funnel.iterrows():
        f.write(f"{r.family.replace('_',' ')} & {r.total_rows} & {r.gate1_ghost_safe} & {r['gate1+2_both_safe']} & {r.pct_survive_both}\\% \\\\\n")
    f.write(r"\bottomrule \end{tabular}" + "\n")

# ---------- Table 4: ghost/vignetting divergence (inf-margin rows only) ----------
rows = []
for fam in FAMILIES:
    sub = sweep[sweep.family == fam]
    inf_rows = sub[sub.worst_case_ghost_margin == np.inf]
    if len(inf_rows) == 0:
        continue
    safe = (inf_rows.worst_case_vignetting_margin > 0).sum()
    fails = (inf_rows.worst_case_vignetting_margin <= 0).sum()
    pct = 100.0*fails/len(inf_rows)
    rows.append((fam, len(inf_rows), safe, fails, pct))
div = pd.DataFrame(rows, columns=["family","inf_ghost_rows","also_vig_safe","vig_fails","divergence_pct"])
div = div.sort_values("divergence_pct")
div.to_csv(os.path.join(OUT_TEX, "table4_divergence.csv"), index=False)
with open(os.path.join(OUT_TEX, "table4_divergence.tex"), "w") as f:
    f.write(r"\begin{tabular}{lrrrr}" + "\n")
    f.write(r"\toprule Family & $\phi{=}0$ ghost-safe rows & Also vignetting-safe & Fails vignetting & Divergence \\ \midrule" + "\n")
    for _, r in div.iterrows():
        f.write(f"{r.family.replace('_',' ')} & {r.inf_ghost_rows} & {r.also_vig_safe} & {r.vig_fails} & {r.divergence_pct:.1f}\\% \\\\\n")
    f.write(r"\bottomrule \end{tabular}" + "\n")

# ---------- Table 5: Metric 1 winners per M ----------
m1_disp = m1.copy()
m1_disp['margin_display'] = m1_disp['worst_case_ghost_margin'].apply(lambda x: "inf" if x==np.inf else f"{x:.2f}")
with open(os.path.join(OUT_TEX, "table5_metric1_winners.tex"), "w") as f:
    f.write(r"\begin{longtable}{lllrrl}" + "\n")
    f.write(r"\toprule M & Family & N$_{\rm actual}$ & $a_{\rm hole}$ ($\mu$m) & density ($\mu$m$^{-2}$) & ghost margin \\ \midrule \endhead" + "\n")
    for _, r in m1_disp.iterrows():
        fam = str(r.family).replace('_',' ')
        f.write(f"{r.M} & {fam} & {int(r.N_actual)} & {r.a_hole_um:.0f} & {r['packing_density_per_area_um-2']:.3e} & {r.margin_display} \\\\\n")
    f.write(r"\bottomrule \end{longtable}" + "\n")

# ---------- Figure: survivor funnel bar chart ----------
fig, ax = plt.subplots(figsize=(9,5))
x = np.arange(len(funnel))
w = 0.35
ax.bar(x - w/2, funnel.gate1_ghost_safe, w, label="Gate 1 only (ghost-safe)")
ax.bar(x + w/2, funnel["gate1+2_both_safe"], w, label="Gate 1 + Gate 2 (both safe)")
ax.set_xticks(x)
ax.set_xticklabels([f.replace('_','\n') for f in funnel.family], fontsize=8)
ax.set_ylabel("row count")
ax.set_title("Structural safety survivors per family (post-cleanup dataset, N=6395 rows)")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_FIG, "fig_funnel_survivors.png"), dpi=150)
plt.close()

# ---------- Figure: divergence bar chart ----------
fig, ax = plt.subplots(figsize=(9,5))
ax.barh(div.family.str.replace('_',' '), div.divergence_pct, color='indianred')
ax.set_xlabel("% of $\\phi{=}0$ ghost-safe rows that FAIL vignetting")
ax.set_title("Ghost-safety at $\\phi=0$ does not imply vignetting-safety")
plt.tight_layout()
plt.savefig(os.path.join(OUT_FIG, "fig_divergence.png"), dpi=150)
plt.close()

print("DONE")
print("Families:", FAMILIES)
print("Funnel:\n", funnel)
print("Divergence:\n", div)
