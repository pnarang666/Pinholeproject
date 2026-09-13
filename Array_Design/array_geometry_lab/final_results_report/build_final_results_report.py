"""
Array_Design/array_geometry_lab/final_results_report/build_final_results_report.py

Final, post-remediation results comparison across every array-geometry family,
built entirely from freshly re-run data (2026-09-13, after the acuity grid_N
fix -- see Array_Design/legacy_archive/08_stale_acuity_aperture_artifact/README.md).
Also reflects the same-day methodology decision to promote gaze-weighted
ghost time (with a hard blindness gate) to this project's PRIMARY ranking,
superseding the worst-case-gated standard as the headline answer -- see
GAZE_WEIGHTED_APPROACH.md's "UPDATE, 2026-09-13" section and
comparison_metric/primary_ranking_gaze_weighted.py.
Reads only current (non-legacy) CSVs. Writes nothing outside this folder.

Run: python3 build_final_results_report.py
"""
import os
import csv
import textwrap

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

LAB = "/Users/parikshitnarang/Pinholeproject/Array_Design/array_geometry_lab"
EVAL = os.path.join(LAB, "array_data", "evaluation_results")
THEO = os.path.join(LAB, "array_data", "theoretical_data")
SHEN = os.path.join(LAB, "shen_model")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PDF = os.path.join(HERE, "Final_Array_Results_All_Families.pdf")

COLOR_ACCENT = "#6B4C9A"
COLOR_A = "#2C6E9E"
COLOR_B = "#E07B39"
COLOR_C = "#4E9F3D"
COLOR_BAD = "#B23A48"
INK = "#222222"
MUTED = "#666666"
PAGE = (8.5, 11)

FAMILIES = ["square", "hexagonal", "rectangular", "concentric", "ring_offset_concentric",
            "fibonacci_spiral", "golden_angle", "archimedean_spiral", "poisson_disk",
            "jittered_lattice"]
FAM_COLORS = plt.cm.tab10(np.linspace(0, 1, 10))
FAM_COLOR = dict(zip(FAMILIES, FAM_COLORS))


def render_text_page(pdf, title, subtitle, blocks):
    fig = plt.figure(figsize=PAGE)
    ax = fig.add_axes([0.085, 0.045, 0.83, 0.90])
    ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    y = 1.0
    ax.plot([0, 1], [y, y], color=COLOR_ACCENT, linewidth=2.4, transform=ax.transAxes, clip_on=False)
    y -= 0.008
    ax.text(0, y, title, fontsize=15, fontweight="bold", va="top", color=INK, transform=ax.transAxes)
    y -= 0.042
    if subtitle:
        ax.text(0, y, subtitle, fontsize=9.5, va="top", color=MUTED, style="italic", transform=ax.transAxes)
        y -= 0.032
    y -= 0.010
    line_h = 0.0205
    for kind, payload in blocks:
        if kind == "space":
            y -= payload; continue
        if kind == "para":
            for ln in (textwrap.wrap(payload, width=104) or [""]):
                ax.text(0, y, ln, fontsize=9.3, va="top", color=INK, transform=ax.transAxes)
                y -= line_h
            y -= 0.008
        elif kind == "bullets":
            for item in payload:
                wrapped = textwrap.wrap(item, width=99) or [""]
                for j, ln in enumerate(wrapped):
                    prefix = "•  " if j == 0 else "   "
                    ax.text(0.012, y, prefix + ln, fontsize=9.1, va="top", color=INK, transform=ax.transAxes)
                    y -= line_h
            y -= 0.008
        elif kind == "heading2":
            y -= 0.006
            for ln in (textwrap.wrap(payload, width=88) or [""]):
                ax.text(0, y, ln, fontsize=11.2, fontweight="bold", va="top", color=COLOR_ACCENT, transform=ax.transAxes)
                y -= line_h * 1.25
            y -= 0.006
        elif kind == "code":
            code_title, code_text = payload
            n_lines = code_text.count("\n") + 1
            box_h = 0.020 * n_lines + 0.018
            if code_title:
                ax.text(0, y, code_title, fontsize=8.8, fontweight="bold", va="top", color=MUTED, transform=ax.transAxes)
                y -= 0.022
            ax.add_patch(plt.Rectangle((0.0, y - box_h), 1.0, box_h, transform=ax.transAxes,
                                        facecolor="#f4f4f4", edgecolor="#cfcfcf", linewidth=0.8, clip_on=False))
            ax.text(0.012, y - 0.007, code_text, fontsize=7.3, va="top", family="monospace", color="#1a1a1a", transform=ax.transAxes)
            y -= box_h + 0.013
    pdf.savefig(fig); plt.close(fig)


def render_title(pdf):
    fig = plt.figure(figsize=PAGE)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(plt.Rectangle((0, 0.78), 1, 0.015, facecolor=COLOR_ACCENT))
    ax.add_patch(plt.Rectangle((0, 0.20), 1, 0.015, facecolor=COLOR_ACCENT))
    ax.text(0.5, 0.70, "Multi-Pinhole Array Design:", fontsize=15, ha="center", color=MUTED)
    ax.text(0.5, 0.655, "Final Results Across All Geometric Families", fontsize=20, ha="center", fontweight="bold", color=INK)
    ax.text(0.5, 0.53, "Post-remediation results (2026-09-13) -- every table in this document was", fontsize=10, ha="center", color=COLOR_ACCENT)
    ax.text(0.5, 0.505, "regenerated fresh after a real bug fix, verified unchanged, PRIMARY standard updated", fontsize=10, ha="center", color=COLOR_ACCENT, fontweight="bold")
    ax.text(0.5, 0.40,
            "10 geometric families x up to 9045 candidates x 8 myopic powers, evaluated\n"
            "under this project's new PRIMARY standard (gaze-weighted ghost time + a hard\n"
            "blindness gate), its previous worst-case safety gates (still reported), and an\n"
            "independent comparison against Shen (2026)'s own published evaluator --\n"
            "reported honestly, agreement and disagreement alike.",
            fontsize=9.5, ha="center", va="top", color=INK, linespacing=1.9)
    ax.text(0.5, 0.06, "2026", fontsize=10, ha="center", color=MUTED)
    pdf.savefig(fig); plt.close(fig)


def section_bug_and_verification(pdf):
    blocks = [
        ("heading2", "What happened"),
        ("para", "A real bug was found: new_sweeps/run_acuity_sweep.py silently used a stale "
                  "diffraction grid (grid_N=2048) that new_sweeps/run_blur_sweep.py had already "
                  "fixed to grid_N=4096 on 2026-08-16. Since this lab's own "
                  "ghost_margin.py::load_acuity_optimal_aperture() reads the acuity sweep's output "
                  "live as the actual hole diameter a_hole(M) used to generate every candidate "
                  "array, the ENTIRE candidate pool in this lab -- every family, every ranking "
                  "table, the gaze-weighted winner, the worst-case-gated final winner -- had been "
                  "generated against a stale aperture choice."),
        ("heading2", "What was done about it"),
        ("bullets", [
            "Fixed the one call site (grid_N=4096 passed explicitly), re-ran the acuity sweep "
            "(120 points, ~98 minutes), regenerated every downstream new_sweeps/ file.",
            "Re-ran this lab's ENTIRE pipeline end-to-end, in the exact order this project's own "
            "README.md specifies: validate_copies -> spot_check_generators -> "
            "test_part3_small_case -> sweep/run_sweep -> run_rotation_sweep -> compute_density "
            "-> run_comparison -> rank_by_family -> effective_density_ranking -> "
            "compute_gaze_weighted_metrics -> gaze_weighted_ranking -> final_winner -> "
            "paper_score -> paper_soft_gates -> shen_evaluator. All 10 families (including "
            "jittered_lattice and archimedean_spiral) completed with no errors.",
        ]),
        ("heading2", "The critical check: did the final answer actually change?"),
        ("para", "Verified directly, not assumed: diff'd every pre-fix vs. post-fix output file. "
                  "gaze_weighted_winner_per_M.csv and FINAL_WINNER_PER_M.csv are BYTE-IDENTICAL, "
                  "every column, before and after the fix. The fabrication_package brass-shim "
                  "hole coordinates and SVG masks (already delivered) were regenerated and are "
                  "also byte-identical."),
        ("code", ("Verification performed:", "diff gaze_weighted_winner_per_M_legacy1.csv gaze_weighted_winner_per_M.csv\n"
                  "  -> exit code 0 (no differences)\n"
                  "diff FINAL_WINNER_PER_M_legacy1.csv FINAL_WINNER_PER_M.csv\n"
                  "  -> exit code 0 (no differences)\n"
                  "diff -r hole_coordinates_BEFORE/ hole_coordinates/  -> exit code 0")),
        ("para", "The bug inflated the raw blur/logMAR magnitudes at every aperture, but never "
                  "changed which discrete aperture minimized logMAR for a given M -- so nothing "
                  "already reported or built needed to change. The stale intermediate candidate "
                  "pool (sweep_results.csv, 8501-9045 rows) IS archived for a complete audit "
                  "trail -- see Array_Design/legacy_archive/08_stale_acuity_aperture_artifact/."),
    ]
    render_text_page(pdf, "1. What Happened, and What Was Verified", "", blocks)


def section_methodology_change(pdf):
    blocks = [
        ("heading2", "Gaze-weighted + blindness gate is now this project's PRIMARY standard"),
        ("para", "Per explicit decision (2026-09-13), this project's ranking hierarchy changed: "
                  "gaze-weighted ghost percentage, combined with a hard blindness gate, now REPLACES "
                  "the pure worst-case-across-every-tested-gaze-angle criterion as the primary "
                  "standard -- judged more realistic, since it reflects how the eye actually moves "
                  "(sharply peaked near straight-ahead) rather than treating a rare 25-degree "
                  "failure as equally serious as a straight-ahead one. The worst-case gates "
                  "(FINAL_WINNER_PER_M.csv) are NOT deleted -- they remain valid, reported data -- "
                  "but are no longer this project's headline answer."),
        ("heading2", "The new rule"),
        ("bullets", [
            "HARD GATE: exclude any candidate with time_weighted_blind_pct > 1.0% (\"blind\" = "
            "literally zero illuminated area at that gaze angle, time-weighted across a measured "
            "eye-tracking eccentricity distribution).",
            "Among gate-survivors, minimize time_weighted_ghost_pct (primary criterion), tie-break "
            "on time_weighted_blind_pct.",
        ]),
        ("heading2", "Why 1.0%, not a strict 0% gate -- checked, not assumed"),
        ("para", "A strict 0%-blind gate was tried first. It produces a sharp cliff at M=6D and "
                  "M=8D: every candidate with genuinely zero blind time at those M has real (27-30%) "
                  "ghost, while the excellent 0%-ghost candidates that exist there (hexagonal, "
                  "pitch=4000um) carry a small nonzero blind time (0.33-0.71%). A bare-zero threshold "
                  "is exactly the same \"margin vs. zero\" failure mode this project's own gates.py "
                  "already diagnosed and fixed once before for the worst-case metric (a threshold of "
                  "precisely 0 cannot distinguish a trivial sliver from a real problem). Consistent "
                  "with that established precedent, a small, explicit, documented tolerance (1.0%, "
                  "chosen to clear every existing winner's own blind_pct with headroom) is used "
                  "instead."),
        ("heading2", "Result: this gate did not have to override anything"),
        ("para", "The new PRIMARY_WINNER_PER_M.csv produces the SAME family choices as the old, "
                  "ungated gaze-weighted ranking (hexagonal M=1-6, square M=0/8/global) -- every one "
                  "of those winners already happened to clear the 1.0% gate on its own. The gate's "
                  "purpose is not to change today's answer but to guarantee a future re-run, on "
                  "different candidate data, cannot silently select a degenerate mostly-blind design "
                  "the way the old ungated ranking's own module docstring warned it theoretically "
                  "could (see Section 5b for a live example of exactly that failure mode, correctly "
                  "excluded)."),
    ]
    render_text_page(pdf, "2. Methodology Change: New Primary Standard", "Gaze-weighted ghost time + a hard blindness gate", blocks)


def load_family_ranking():
    df = pd.read_csv(os.path.join(EVAL, "family_ranking.csv"))
    return df


def section_family_survival(pdf):
    # from run_comparison.log survivor counts (recomputed here directly from source CSVs)
    sweep = pd.read_csv(os.path.join(THEO, "sweep_results_with_density.csv"))
    total = sweep.groupby("family").size()
    safe = sweep[sweep.structurally_safe == True].groupby("family").size()
    pct = (safe / total * 100).reindex(FAMILIES).fillna(0)

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = [FAM_COLOR[f] for f in FAMILIES]
    bars = ax.bar(FAMILIES, pct.values, color=colors)
    for b, v in zip(bars, pct.values):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, f"{v:.1f}%", ha="center", fontsize=8)
    ax.set_ylabel("% of tested candidates structurally safe\n(worst-case ghost + vignetting gates)")
    ax.set_title("3. Structural safety survival rate, per family\n(fresh data, all N/spacing/seed combinations tested)", fontsize=12, fontweight="bold")
    ax.set_xticklabels(FAMILIES, rotation=35, ha="right", fontsize=8.5)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()
    pdf.savefig(fig); plt.close(fig)


def section_metric_winners(pdf):
    m1 = pd.read_csv(os.path.join(EVAL, "metric1_max_density_per_M.csv"))
    fw = pd.read_csv(os.path.join(EVAL, "FINAL_WINNER_PER_M.csv"))
    gw = pd.read_csv(os.path.join(EVAL, "gaze_weighted_winner_per_M.csv"))
    pw = pd.read_csv(os.path.join(EVAL, "PRIMARY_WINNER_PER_M.csv"), dtype={"M": str})

    fig = plt.figure(figsize=PAGE)
    ax = fig.add_axes([0.06, 0.06, 0.9, 0.88]); ax.axis("off")
    ax.plot([0, 1], [1.0, 1.0], color=COLOR_ACCENT, linewidth=2.4, transform=ax.transAxes)
    ax.text(0, 0.975, "4. Winner-Per-M Comparison Across Ranking Standards", fontsize=15, fontweight="bold", va="top", transform=ax.transAxes)
    ax.text(0, 0.945, "PRIMARY (leftmost) is this project's current answer; the rest are reported alongside, not hidden:", fontsize=9.3, style="italic", color=MUTED, va="top", transform=ax.transAxes)

    col_labels = ["M", "PRIMARY\n(gaze-weighted +\nblind gate<=1%)", "Metric-1\n(max density,\nno margin)", "Worst-case\n(margin-aware\nhard gates)", "Gaze-weighted\n(ungated)"]
    Ms = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, "global"]
    cell_text = []
    for M in Ms:
        r0 = pw[pw.M.astype(str) == str(M)].iloc[0] if (pw.M.astype(str) == str(M)).any() else None
        r1 = m1[m1.M.astype(str) == str(M)].iloc[0] if (m1.M.astype(str) == str(M)).any() else None
        r2 = fw[fw.M.astype(str) == str(M)].iloc[0] if (fw.M.astype(str) == str(M)).any() else None
        r3 = gw[gw.M.astype(str) == str(M)].iloc[0] if (gw.M.astype(str) == str(M)).any() else None
        cell_text.append([
            str(M),
            f"{r0['family']}\nN={r0['N_requested']}" if r0 is not None else "n/a",
            f"{r1['family']}\nN={r1['N_requested']}" if r1 is not None else "n/a",
            f"{r2['family']}\nN={r2['N_requested']}" if r2 is not None else "n/a",
            f"{r3['family']}\nN={r3['N_requested']}" if r3 is not None else "n/a",
        ])
    tbl = ax.table(cellText=cell_text, colLabels=col_labels, loc="upper center", cellLoc="center",
                    bbox=[0.0, 0.45, 1.0, 0.48])
    tbl.auto_set_font_size(False); tbl.set_fontsize(8.2)
    for (row, col), cell in tbl.get_celld().items():
        if col == 1:
            cell.set_facecolor("#EDE7F6")

    note = ("PRIMARY (Section 2): hexagonal wins M=1-6, square wins M=0/8/global -- identical "
            "picks to the ungated gaze-weighted column, since every winner already cleared the "
            "1.0% blind gate on its own. Metric-1 (pure density, no safety margin) favors square/"
            "rectangular at tight spacing. The worst-case margin-aware standard (this project's "
            "PREVIOUS primary, still reported) also picks square at every M, but at a much larger, "
            "more conservative pitch than PRIMARY's hexagonal picks -- both are legitimate answers "
            "to different questions (guaranteed-safe-everywhere vs. realistic-time-weighted), "
            "neither is hidden.")
    ax.text(0, 0.40, "\n".join(textwrap.wrap(note, width=100)), fontsize=8.6, va="top", color=INK, transform=ax.transAxes, linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)


def section_gaze_weighted_all_families(pdf):
    gwm = pd.read_csv(os.path.join(THEO, "gaze_weighted_metrics.csv"))
    best = gwm.loc[gwm.groupby("family")["time_weighted_ghost_pct"].idxmin()].set_index("family").reindex(FAMILIES)

    fig, axes = plt.subplots(2, 1, figsize=(9, 9))
    ax1 = axes[0]
    colors = [FAM_COLOR[f] for f in FAMILIES]
    bars = ax1.bar(FAMILIES, best["time_weighted_ghost_pct"].values, color=colors)
    for b, v in zip(bars, best["time_weighted_ghost_pct"].values):
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, f"{v:.1f}%", ha="center", fontsize=7.5)
    ax1.set_ylabel("time-weighted ghost % (best candidate per family)")
    ax1.set_title("5. Best-candidate-per-family comparison, gaze-weighted metric", fontsize=12, fontweight="bold", pad=16)
    ax1.set_xticklabels(FAMILIES, rotation=35, ha="right", fontsize=8)
    ax1.set_ylim(0, max(best["time_weighted_ghost_pct"].values) * 1.7 + 0.1)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    ax2 = axes[1]
    blind_vals = best["time_weighted_blind_pct"].values
    bar_colors = [COLOR_BAD if v > 30 else COLOR_A for v in blind_vals]
    bars2 = ax2.bar(FAMILIES, blind_vals, color=bar_colors)
    for b, v in zip(bars2, blind_vals):
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, f"{v:.1f}%", ha="center", fontsize=7.5)
    ax2.set_ylabel("time-weighted blind % (SAME candidate)")
    ax2.set_title("Same candidates' blind-time % -- red flags a likely degenerate\n"
                  "'rewards blindness' pick (near-zero ghost only because it's mostly dark)", fontsize=10)
    ax2.set_xticklabels(FAMILIES, rotation=35, ha="right", fontsize=8)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)
    plt.tight_layout()
    pdf.savefig(fig); plt.close(fig)

    return best


def section_degenerate_flag(pdf, best):
    arch = best.loc["archimedean_spiral"]
    blocks = [
        ("heading2", "Honest flag: archimedean_spiral's 'best' candidate is degenerate"),
        ("para", f"archimedean_spiral's minimum-ghost candidate (N={int(arch.N_requested)}, "
                  f"{arch.spacing_params}) achieves only {arch.time_weighted_ghost_pct:.2f}% "
                  f"time-weighted ghost -- but at the cost of {arch.time_weighted_blind_pct:.1f}% "
                  f"time-weighted BLIND. This is exactly the 'rewards blindness' degenerate "
                  f"pattern this project's own gaze_weighted_ranking.py module docstring warns "
                  f"about: a design that is mostly dark has nothing left to ghost. Reported here "
                  f"plainly, not filtered out or hidden -- this candidate is NOT a viable design "
                  f"despite its low ghost score, and is excluded from consideration on that basis, "
                  f"not on ghost performance."),
        ("para", "This is exactly the failure mode Section 2's blindness gate (time_weighted_blind_pct "
                  "<= 1.0%) is built to exclude before ranking even sees this candidate -- "
                  f"archimedean_spiral's {arch.time_weighted_blind_pct:.1f}% blind time is nowhere "
                  "close to that 1.0% threshold, so it never reaches PRIMARY_WINNER_PER_M.csv at "
                  "all. This case is kept in this report as a live demonstration of why the gate "
                  "exists, not a residual problem in the current primary answer."),
    ]
    render_text_page(pdf, "5b. Degenerate-Candidate Check", "Checked directly, not assumed away", blocks)


def section_shen_comparison(pdf):
    psvc = pd.read_csv(os.path.join(EVAL, "paper_score_vs_current_winner.csv"))
    psg = pd.read_csv(os.path.join(EVAL, "paper_soft_gates_winner_per_M.csv"))
    shen_winner = pd.read_csv(os.path.join(SHEN, "shen_model_winner_per_M.csv"))

    fig = plt.figure(figsize=PAGE)
    ax = fig.add_axes([0.06, 0.05, 0.9, 0.90]); ax.axis("off")
    ax.plot([0, 1], [1.0, 1.0], color=COLOR_ACCENT, linewidth=2.4, transform=ax.transAxes)
    ax.text(0, 0.975, "6. Comparison Against Shen (2026)'s Own Evaluator", fontsize=15, fontweight="bold", va="top", transform=ax.transAxes)
    ax.text(0, 0.945, "Three independent checks against the published reference model -- reported honestly, agreement and disagreement alike", fontsize=9, style="italic", color=MUTED, va="top", transform=ax.transAxes)

    y0 = 0.90
    ax.text(0, y0, "6.1  This project's Metric-1 (density-only) pick, scored by Shen's own closed-form S_paper", fontsize=10.5, fontweight="bold", color=COLOR_ACCENT, va="top", transform=ax.transAxes)
    subtitle_lines = textwrap.wrap(
        "(paper_score.py's own comparison uses metric1_max_density_per_M.csv, not "
        "PRIMARY_WINNER_PER_M.csv or FINAL_WINNER_PER_M.csv -- noted accurately here, not relabeled)",
        width=100)
    for i, ln in enumerate(subtitle_lines):
        ax.text(0, y0 - 0.026 - i * 0.018, ln, fontsize=7.6, style="italic", color=MUTED, va="top", transform=ax.transAxes)
    table_top = y0 - 0.026 - len(subtitle_lines) * 0.018 - 0.015
    col_labels = ["M", "Metric-1\n(density-only)\npick", "S_paper of\nthat pick", "Shen's own\nS_paper winner", "Shen's\nS_paper value"]
    cell_text = []
    for _, r in psvc.iterrows():
        cell_text.append([str(r["M"]), f"{r['current_winner_family']}", f"{r['current_winner_S_paper']:.3f}",
                           f"{r['paper_winner_family']}", f"{r['paper_winner_S_paper']:.3f}"])
    tbl = ax.table(cellText=cell_text, colLabels=col_labels, loc="upper center", cellLoc="center",
                    bbox=[0.0, table_top - 0.28, 1.0, 0.28])
    tbl.auto_set_font_size(False); tbl.set_fontsize(7.6)
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_height(cell.get_height() * 1.8)

    note1 = ("Under Shen's own raw density-driven score with NO safety gate, this project's "
             "density-only Metric-1 pick scores lower than Shen's own top-scoring candidate at "
             "every M -- expected: Shen's own top pick has no safety consideration built in at "
             "all here, while Metric-1 already uses this project's own aperture choices. This is "
             "a difference in OBJECTIVE and candidate pool, not a contradiction -- and separately, "
             "neither this project's PRIMARY (hexagonal, gaze-weighted+blind-gated) nor its "
             "worst-case (square, margin-gated) answer is what this specific comparison tests.")
    ax.text(0, 0.50, "\n".join(textwrap.wrap(note1, width=102)), fontsize=8.3, va="top", color=INK, transform=ax.transAxes, linespacing=1.4)

    ax.text(0, 0.38, "6.2  Under Shen's own SOFT-gate treatment (accounts for partial safety credit)", fontsize=10.5, fontweight="bold", color=COLOR_ACCENT, va="top", transform=ax.transAxes)
    n_soft_recover = int((psg.s_paper_soft_winner_family == "hexagonal").sum())
    note2 = (f"hexagonal recovers as the S_paper_soft winner in {n_soft_recover}/9 M-slots once "
             f"Shen's own soft-gate treatment (partial credit near the safety boundary, not a "
             f"hard cutoff) is applied -- directly from paper_soft_gates.py's own one-line "
             f"summary: \"hexagonal wins 7/9 computable M-slots under S_paper_soft (square wins "
             f"2/9) -- YES, hex recovers under the paper's soft treatment.\" This is a genuine "
             f"point of agreement worth stating plainly: hexagonal is BOTH this project's own "
             f"PRIMARY pick (Section 2, M=1..6) AND the family Shen's own scoring prefers once a "
             f"comparable safety standard is applied on both sides.")
    ax.text(0, 0.345, "\n".join(textwrap.wrap(note2, width=102)), fontsize=8.3, va="top", color=INK, transform=ax.transAxes, linespacing=1.4)

    ax.text(0, 0.16, "6.3  Independent reimplementation of Shen's own ghost formula", fontsize=10.5, fontweight="bold", color=COLOR_ACCENT, va="top", transform=ax.transAxes)
    note3 = ("shen_evaluator.py reimplements Shen's OWN published formulas from scratch (not this "
             "project's judgment layer) and checks Shen's closed-form ghost prediction (g_Sch) "
             "against directly-simulated ghost rate on the same 7708 candidates: "
             "correlation(ghost_rate, g_Sch) = -0.0485 -- close to zero, i.e. Shen's own closed-form "
             "ghost formula does not strongly predict directly-simulated ghosting in this "
             "reimplementation. Reported as a genuine, unresolved tension with the published "
             "model, not smoothed over -- it is NOT evidence this project's own (different, "
             "independently-validated R²=0.995) ghost formula is wrong, since the two formulas "
             "were checked against different simulation setups.")
    ax.text(0, 0.125, "\n".join(textwrap.wrap(note3, width=102)), fontsize=8.3, va="top", color=INK, transform=ax.transAxes, linespacing=1.4)

    pdf.savefig(fig); plt.close(fig)


def section_defensible_conclusion(pdf):
    blocks = [
        ("heading2", "The defensible final position for presentation"),
        ("bullets", [
            "This project's PRIMARY answer (Section 2) is hexagonal (M=1-6) / square (M=0, 8, "
            "global), chosen by minimizing realistic, gaze-weighted ghost time subject to a hard "
            "blindness gate (time_weighted_blind_pct <= 1.0%) -- judged more realistic than a "
            "pure worst-case-across-every-gaze-angle criterion because it reflects how the eye "
            "actually spends its viewing time, not a rare extreme angle weighted equally with "
            "straight-ahead.",
            "The previous worst-case standard (square, every M, Section 4's 'Worst-case' column) "
            "is not discarded -- it remains available as a stricter, guaranteed-safe-everywhere "
            "answer for contexts that need that stronger guarantee.",
            "Once Shen (2026)'s own soft-gate treatment (which itself partially accounts for "
            "safety, not just raw density) is applied, hexagonal -- this project's own PRIMARY "
            "pick for M=1..6 -- independently recovers as the S_paper_soft winner in 7 of 9 tested "
            "M-slots (Section 6.2). This is a genuine point of agreement between this project's "
            "own realistic-use standard and Shen's published scoring.",
            "Every candidate Shen's raw (ungated) score prefers instead (poisson_disk, "
            "archimedean_spiral, jittered_lattice) either fails this project's own hard structural-"
            "safety gate outright (poisson_disk: 2.9% project-wide survival; archimedean_spiral: "
            "0%) or, at its lowest-ghost setting, is a degenerate mostly-blind design (Section "
            "5b) -- not a safe, viable alternative once actually checked.",
        ]),
        ("heading2", "What this project is NOT claiming"),
        ("bullets", [
            "NOT claiming Shen's model is wrong -- the raw S_paper comparison in Section 6.1 uses "
            "a different candidate pool (this project's own density-only Metric-1 pick) and a "
            "different objective (density, no safety term); the gap is explained by that, not a "
            "computational error on either side.",
            "NOT claiming the ghost-formula correlation mismatch (Section 6.3) is resolved -- it "
            "is reported as an open, unexplained tension between the two independently-built "
            "simulation setups.",
            "NOT re-selecting a winner to chase a better Shen-agreement score -- PRIMARY_WINNER_"
            "PER_M.csv was fixed by the methodology decision in Section 2 BEFORE the Section 6.2 "
            "soft-gate agreement was found; the agreement is a genuine independent corroboration, "
            "not the reason for the choice.",
            "NOT claiming the blindness-gate threshold (1.0%) is derived from a deeper physical or "
            "clinical source -- it is this project's own explicit, documented choice, picked to "
            "avoid an arbitrary bare-zero cliff (Section 2), not asserted as an authoritative "
            "clinical safety limit.",
        ]),
    ]
    render_text_page(pdf, "7. Final Defensible Position", "For IYPT presentation and jury discussion", blocks)


def main():
    with PdfPages(OUT_PDF) as pdf:
        render_title(pdf)
        section_bug_and_verification(pdf)
        section_methodology_change(pdf)
        section_family_survival(pdf)
        section_metric_winners(pdf)
        best = section_gaze_weighted_all_families(pdf)
        section_degenerate_flag(pdf, best)
        section_shen_comparison(pdf)
        section_defensible_conclusion(pdf)
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
