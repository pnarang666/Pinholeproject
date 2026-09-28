"""
build_deviation_report.py -- IYPT presentation PDF: predicted LogMAR per array
model, deviation from real clinical data, R^2 status, and a search for
additional external validation datasets.

Sources: predicted_logmar_per_array_model.csv (this folder, already built),
wang2009_validation_postfix_predicted.csv/_stats.csv (stage4_human_vision/outputs/,
the CORRECTED post-optics-fix Wang 2009 re-run), wang2009_calibration_pooled_stats_postfix.csv
(this folder, calibration re-fit against the corrected predictions -- the project's
own RESULTS.md explicitly left this step undone), stage4_human_vision/literature.py's
'single_pinhole_kim_2017' entry (a real, already-vetted-but-previously-unused
anchor, evaluated here for the first time), and a live web search for additional
external datasets (see Section 5 -- found nothing new and independently
verifiable; the search reproduced a claim this project had already investigated
and rejected as fabricated).

Run: python3 build_deviation_report.py
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
STAGE4_OUT = os.path.join(REPO, "stage4_human_vision", "outputs")

OUT_PDF = os.path.join(HERE, "Model_vs_Reality_Deviation_Report.pdf")

INK = "#1a1a1a"
MUTED = "#666666"
ACCENT = "#2C6E9E"
BAD = "#B23A48"
GOOD = "#4E9F3D"
WARN = "#E07B39"

KIM2017 = {"a_hole_um": 900, "M_diopters": 2.7, "observed_logmar": 0.20, "observed_sd": 0.21,
          "predicted_logmar": 0.2769636678060971, "n": 36}

ARRAY_MATCHES = [
    {"M": 2.0, "a_hole_um": 750, "predicted": 0.0756, "observed": 0.31},
    {"M": 3.0, "a_hole_um": 750, "predicted": 0.1117, "observed": 0.31},
    {"M": 6.0, "a_hole_um": 500, "predicted": 0.2585, "observed": 0.28},
]


def title_page(pdf):
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.5, 0.70, "Predicted LogMAR vs. Reality", fontsize=26, fontweight="bold", ha="center")
    fig.text(0.5, 0.63, "Deviation Analysis for the Pinhole-Array Myopia Correction Project",
             fontsize=14, ha="center", color=ACCENT)
    fig.text(0.5, 0.50,
             "How well does this project's acuity model predict REAL, clinically-observed\n"
             "vision through a pinhole -- for the array project's own chosen apertures, and\n"
             "for the model in general? Includes a stale-data correction found and fixed\n"
             "during this analysis, and an additional real data anchor never previously used.",
             fontsize=11.5, ha="center", va="top", color=MUTED, linespacing=1.8)
    fig.text(0.5, 0.10, "IYPT presentation material -- prepared from this project's own data and "
                        "code, plus one live literature check.", fontsize=9, ha="center", color="#999")
    pdf.savefig(fig)
    plt.close(fig)


def text_page(pdf, title, body_lines, fontsize=11.5):
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.06, 0.93, title, fontsize=16, fontweight="bold")
    y = 0.85
    for line in body_lines:
        if line == "":
            y -= 0.02
            continue
        bold = line.startswith("**")
        color = INK
        if line.startswith("[GOOD]"):
            line = line[6:]; color = GOOD
        elif line.startswith("[BAD]"):
            line = line[5:]; color = BAD
        elif line.startswith("[WARN]"):
            line = line[6:]; color = WARN
        text = line.replace("**", "")
        wrapped = textwrap.wrap(text, width=100)
        for wline in (wrapped or [""]):
            fig.text(0.07, y, wline, fontsize=fontsize, fontweight=("bold" if bold else "normal"),
                     color=color, va="top")
            y -= 0.032
        y -= 0.008
    pdf.savefig(fig)
    plt.close(fig)


def methodology_page(pdf):
    body = [
        "**How predicted LogMAR is calculated (stage4_human_vision/acuity.py)**",
        "1. MTF10 cutoff frequency (cycles/degree, from the wave-optics PSF through the pinhole) "
        "-> Minimum Angle of Resolution (MAR, arcmin) -> log10(MAR) = raw LogMAR.",
        "2. Adjusted by VSOTF (Visual Strehl ratio of the OTF) ^0.1 -- accounts for how much the "
        "eye's own optical quality (not just the pinhole) limits resolution.",
        "3. Additive brightness correction in log space: 0 above 300 Td (Weber-Fechner regime, "
        "Van Nes & Bouman 1967); below 300 Td, += 0.060 x log10(300/Td) (de Vries-Rose slope, "
        "Tidbury/Czanner/Newsham 2016). Default scene luminance: 10,000 cd/m^2 (bright daylight).",
        "4. This combination is the 'recommended' model (mtf10_vsotf_brightness_adjusted). A "
        "legacy alternative (an uncited SNR^0.05 term) is kept for comparison, never deleted.",
        "5. Wave-optics propagation grid: N=4096 (fixed 2026-09-12/13 -- the one stale call site, "
        "new_sweeps/run_acuity_sweep.py, now explicit).",
        "",
        "**Why the array project can reuse this single-pinhole model directly**",
        "Every hole in an array design has IDENTICAL per-hole optics to a standalone pinhole of "
        "the same diameter at the same myopia power M -- the array geometry only changes whether "
        "multiple holes' images overlap (ghosting) or none do (blindness), not the blur of a single "
        "hole's own image. So each array model's predicted LogMAR is looked up directly from the "
        "single-pinhole sweep at that model's chosen aperture -- not re-derived per family.",
    ]
    text_page(pdf, "1. The Acuity Prediction System", body)


def array_model_page(pdf, detail_df, opt_map):
    fig, ax = plt.subplots(figsize=(11, 6.5))
    Ms = sorted(detail_df.M_diopters.unique())
    per_m = detail_df.drop_duplicates("M_diopters").set_index("M_diopters")
    predicted = [per_m.loc[m, "predicted_logmar"] for m in Ms]
    ax.plot(Ms, predicted, "o-", color=ACCENT, linewidth=2.5, markersize=9,
            label="Predicted LogMAR (ALL 6 array models -- identical)")
    ax.axhline(0, color="#cccccc", linewidth=1, linestyle=":")
    for m, p in zip(Ms, predicted):
        ax.annotate(f"{p:.3f}", (m, p), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9)
    ax.set_xlabel("Myopic power M (D)")
    ax.set_ylabel("Predicted LogMAR (lower = better vision)")
    ax.set_title("Predicted LogMAR per myopia power -- all 6 array evaluation models agree exactly",
                 fontsize=13, fontweight="bold")
    ax.grid(axis="y", color="#eee")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    fig.text(0.5, 0.015,
             "Every ranking model (worst-case gate, gaze-weighted, primary, metric1, effective-density x2) "
             "independently picked the SAME optical aperture per M -- because that aperture is chosen from the "
             "single-pinhole acuity-optimum map FIRST; the array layer only decides safe GEOMETRY for it. "
             "Deviation from the theoretical single-pinhole optimum is ~0.000 logMAR everywhere, by construction.",
             ha="center", fontsize=8.5, color=MUTED, wrap=True)
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    pdf.savefig(fig)
    plt.close(fig)


def stale_data_page(pdf):
    body = [
        "**Found while preparing this report: the project's own prior Wang-2009 validation "
        "output was stale**",
        "stage4_human_vision/outputs/validation_predicted_vs_observed.csv (and its regression/"
        "calibration stats) were dated 2026-07-29 -- 8 days BEFORE the 2026-08-06 fix to "
        "stage4_human_vision/pipeline.py (a stage2/ -> stage2_fixed/ import-shadowing bug, already "
        "documented in this project's own RESULTS.md). Confirmed by direct re-run: same inputs, "
        "current code, gave a materially different result (e.g. aperture=750um, M=2D: 0.076 now vs. "
        "1.010 in the stale file).",
        "",
        "[GOOD]The project HAD already re-run the core validation post-fix (files suffixed "
        "'_postfix', dated exactly 2026-08-06) -- this report uses those, not the stale ones.",
        "[WARN]The affine-calibration step was explicitly left un-re-run by the project's own "
        "RESULTS.md ('Section 4c's calibration fit ... also not re-touched here'). This report "
        "closes that specific gap, using the project's own unmodified calibration.py fitting code "
        "against the corrected predictions -- no new physics, no new assumptions.",
        "",
        "This matters for the numbers on the following pages: R^2 and deviation figures shown here "
        "are the CORRECTED, current values -- not what a naive read of the existing output files "
        "would have given.",
    ]
    text_page(pdf, "2. A Correction Made During This Analysis", body)


def array_relevant_deviation_page(pdf):
    fig, ax = plt.subplots(figsize=(11, 6.0))
    labels = [f"M={d['M']:.0f}D\na={d['a_hole_um']}um" for d in ARRAY_MATCHES]
    pred = [d["predicted"] for d in ARRAY_MATCHES]
    obs = [d["observed"] for d in ARRAY_MATCHES]
    x = np.arange(len(ARRAY_MATCHES))
    w = 0.32
    ax.bar(x - w/2, pred, w, label="Model predicted", color=ACCENT)
    ax.bar(x + w/2, obs, w, label="Real observed (Wang 2009)", color=WARN)
    for xi, p, o in zip(x, pred, obs):
        ax.annotate(f"{p:.3f}", (xi - w/2, p), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9)
        ax.annotate(f"{o:.3f}", (xi + w/2, o), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9)
        dev = p - o
        ax.annotate(f"deviation {dev:+.3f}\n({'optimistic' if dev<0 else 'pessimistic'})",
                    (xi, max(p, o) + 0.06), ha="center", fontsize=8.5, color=BAD if dev < 0 else WARN,
                    fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("LogMAR (lower = better vision)")
    ax.set_title("At the apertures/M our array models actually use: model vs. real clinical data",
                 fontsize=12.5, fontweight="bold")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, 0.55)
    fig.text(0.5, 0.01,
             "Real observed values are Wang (2009)'s own aperture-indexed clinical data, reused across M per "
             "this project's already-documented convention (the source paper reports no per-M breakdown).",
             ha="center", fontsize=8, color=MUTED)
    plt.tight_layout(rect=[0, 0.035, 1, 1])
    pdf.savefig(fig)
    plt.close(fig)


def full_grid_page(pdf, postfix_df):
    df = postfix_df.copy()
    df["deviation"] = df.predicted_logmar - df.observed_logmar
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    colors = {0.0: "#4E9F3D", 2.0: "#2C6E9E", 5.0: "#B23A48"}
    for m, c in colors.items():
        sub = df[df.M_diopters == m]
        axes[0].plot(sub.a_hole_um, sub.deviation, "o-", color=c, label=f"M={m:.0f}D")
    axes[0].axhline(0, color="#999", linewidth=1)
    axes[0].set_xlabel("Aperture (um)"); axes[0].set_ylabel("Deviation (predicted - observed) LogMAR")
    axes[0].set_title("Deviation vs. aperture", fontsize=11.5, fontweight="bold")
    axes[0].legend(frameon=False, fontsize=9)
    axes[0].spines[["top", "right"]].set_visible(False)
    axes[0].text(0.02, 0.02, "below 0 = model too OPTIMISTIC\nabove 0 = model too PESSIMISTIC",
                fontsize=7.5, color=MUTED, transform=axes[0].transAxes, va="bottom")

    aps = sorted(df.a_hole_um.unique())
    ap_colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(aps)))
    for a, c in zip(aps, ap_colors):
        sub = df[df.a_hole_um == a].sort_values("M_diopters")
        axes[1].plot(sub.M_diopters, sub.deviation, "o-", color=c, label=f"{a}um")
    kim_dev = KIM2017["predicted_logmar"] - KIM2017["observed_logmar"]
    axes[1].scatter([KIM2017["M_diopters"]], [kim_dev], marker="*", s=300, color="black", zorder=5,
                    label="Kim 2017 (900um, new anchor)")
    axes[1].axhline(0, color="#999", linewidth=1)
    axes[1].set_xlabel("Myopic power M (D)"); axes[1].set_ylabel("Deviation (predicted - observed) LogMAR")
    axes[1].set_title("Deviation vs. myopic power", fontsize=11.5, fontweight="bold")
    axes[1].legend(frameon=False, fontsize=8, ncol=2)
    axes[1].spines[["top", "right"]].set_visible(False)

    fig.suptitle("How the deviation progresses -- full Wang(2009) grid (15 pts) + Kim(2017) anchor (16 total)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    pdf.savefig(fig)
    plt.close(fig)


def r2_summary_page(pdf, postfix_stats, calib_postfix):
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.axis("off")
    ax.text(0.5, 0.97, "R^2 status -- current (post-fix), all real-data comparisons", fontsize=15,
            fontweight="bold", ha="center", transform=ax.transAxes)

    KIND_LABEL = {
        "raw_pooled_uncalibrated": "raw model (uncalibrated)",
        "affine_calibrated_in_sample": "calibrated, in-sample",
        "affine_calibrated_leave_one_out": "calibrated, leave-one-out",
    }
    rows = []
    for _, r in postfix_stats.iterrows():
        rows.append([f"M={r.M_diopters:.0f}D, raw model", f"{int(r.n)}", f"{r.r2:.2f}", f"{r.pearson_r:+.3f}",
                    f"{r.pearson_p_value:.3f}", "FAIL"])
    for _, r in calib_postfix.iterrows():
        rows.append([f"pooled, {KIND_LABEL[r.kind]}", "15", f"{r.r2:.4f}", f"{r.pearson_r:+.3f}",
                    f"{r.pearson_p_value:.4f}", "PASS" if r.r2 > 0 and r.pearson_p_value < 0.05 else "FAIL"])

    col_labels = ["comparison", "n", "R^2", "pearson r", "p-value", "R^2>0 & p<0.05?"]
    tbl = ax.table(cellText=rows, colLabels=col_labels, cellLoc="center", bbox=[0.03, 0.45, 0.94, 0.42])
    tbl.auto_set_font_size(False); tbl.set_fontsize(9.5)
    tbl.auto_set_column_width(list(range(len(col_labels))))
    for j in range(len(col_labels)):
        tbl[(0, j)].set_facecolor("#e8e8e8"); tbl[(0, j)].set_text_props(fontweight="bold")
    for i, r in enumerate(rows, start=1):
        color = BAD if r[-1] == "FAIL" else GOOD
        tbl[(i, len(col_labels) - 1)].set_text_props(color=color, fontweight="bold")

    verdict = ("Verdict: fails the stated bar (R^2>0 AND p<0.05) at every single comparison, before and "
              "after the optics fix, before and after calibration. The fix narrowed the gap substantially "
              "(pooled raw R^2: -4.98 -> -2.30) but did not close it. In-sample affine calibration gives "
              "R^2~=0 post-fix (down from +0.13 pre-fix) -- meaning the earlier apparent calibration "
              "benefit was itself partly an artifact of the since-fixed optics bug, not a real effect.")
    for i, wline in enumerate(textwrap.wrap(verdict, width=78)):
        ax.text(0.5, 0.30 - i * 0.045, wline, ha="center", fontsize=10, transform=ax.transAxes, color=INK)
    pdf.savefig(fig)
    plt.close(fig)


def kim_anchor_page(pdf):
    body = [
        "**A second real anchor point, found already inside this project's own vetted literature, "
        "used here for the first time**",
        f"Kim WS, Park IK, Park YK, Chun YS (2017). J Korean Med Sci 32(5):850-857. Single-pinhole "
        "spectacles, 0.9mm (900um) aperture, N=36 subjects, mean spherical equivalent -2.7+/-2.3D "
        "(range -6.0 to +0.75D), mean uncorrected LogMAR with pinhole = 0.20 +/- 0.21.",
        "Already in stage4_human_vision/literature.py, flagged 'USABLE as one additional real "
        "anchor' -- but never actually run through the model until this analysis.",
        "",
        f"Model prediction at a=900um, M=2.7D (this study's own mean): LogMAR = "
        f"{KIM2017['predicted_logmar']:.3f}",
        f"Real observed: {KIM2017['observed_logmar']:.2f} +/- {KIM2017['observed_sd']:.2f} (n={KIM2017['n']})",
        f"Deviation: {KIM2017['predicted_logmar']-KIM2017['observed_logmar']:+.3f} logMAR -- model "
        "PESSIMISTIC here (opposite direction from the 750/500um array-relevant points), and WITHIN "
        "1 standard deviation of the real data's own spread.",
        "",
        "[WARN]Key honest takeaway: the model's error is NOT a single, universal 'always optimistic "
        "by X' bias. Direction and magnitude both depend on aperture/M region -- optimistic and small "
        "at 500-750um (where the array project actually operates), roughly neutral (within real noise) "
        "at 900um, and large/mixed-sign across the fuller 1000-1500um range (Section 4's chart).",
    ]
    text_page(pdf, "4. A Second Real Anchor: Kim et al. (2017)", body)


def search_honesty_page(pdf):
    body = [
        "**What a live web search for additional datasets found**",
        "Searched for published pinhole-aperture-size vs. visual-acuity studies with quantitative "
        "aperture/refractive-error/LogMAR data, to extend the real-data comparison beyond Wang (2009) "
        "and Kim (2017).",
        "",
        "[BAD]Result: the AI-generated search summary reproduced the EXACT claim this project had "
        "already investigated and marked REJECTED in its own literature.py ('0.17 LogMAR at up to "
        "5.5D, 1.16 LogMAR at 7-11D') -- a number this project already confirmed, by reading the "
        "actual paper's full text directly, DOES NOT APPEAR ANYWHERE in that source. This is strong, "
        "concrete evidence that AI web-search summaries on this specific topic are not reliable enough "
        "to use without independently reading the primary source -- consistent with this project's own "
        "prior finding, not a new problem.",
        "",
        "Also found: Kim WS et al. (2014), IOVS 55:6679-6685 (verified via PubMed abstract) -- N=48 "
        "eyes, mean spherical equivalent -2.4+/-3.3D, pinhole glasses improved UDVA LogMAR from "
        "0.44+/-0.46 to 0.19+/-0.25. A real, citable result -- but the exact pinhole aperture diameter "
        "used could not be verified from the accessible abstract (full text paywalled), so it is "
        "EXCLUDED from the aperture-indexed deviation chart, not guessed at.",
        "",
        "Also found (already in-repo, not new): Abdul et al. (2009) -- real, verified, but explicitly "
        "not usable for this comparison (near-vision task in children, M-notation acuity not LogMAR, "
        "only 1.5-2mm apertures tested where the paper's own conclusion is that aperture size did not "
        "matter).",
        "",
        "**Bottom line: two independently-verified, quantitatively-usable real datasets exist and are "
        "used in this report (Wang 2009, Kim 2017) -- no further independently-verifiable dataset was "
        "found. This is reported as a real limitation, not glossed over with an unverified number.**",
    ]
    text_page(pdf, "5. Searching for More Real-World Data", body, fontsize=10.8)


def conclusions_page(pdf):
    body = [
        "**Summary for the presentation**",
        "1. All 6 array evaluation models predict IDENTICAL LogMAR per M -- the array geometry work "
        "trades off ghost/blindness safety, not optical acuity, which is fixed by aperture choice alone.",
        "2. Deviation from the single-pinhole theoretical optimum is ~0 by construction.",
        "3. Against the only two independently-verified real clinical datasets available (Wang 2009, "
        "Kim 2017): at the SPECIFIC apertures/M this project's array models actually use (500-750um), "
        "the model is modestly-to-moderately OPTIMISTIC (0.02-0.23 logMAR, ~0.2-2.3 eye-chart lines).",
        "4. Across the FULLER tested range (up to 1500um), the error is larger and its SIGN is not "
        "constant -- it is not a simple universal offset.",
        "5. R^2 fails the significance bar (R^2>0 AND p<0.05) at every comparison, before and after a "
        "real optics fix that substantially narrowed (did not close) the gap.",
        "6. This is n=16 real data points total, worldwide, found across this project's own vetted "
        "literature plus a live search -- a genuinely thin evidence base, honestly stated as such.",
        "",
        "[GOOD]For IYPT: this is a legitimate, defensible story -- a physically-grounded model that "
        "tracks real pinhole vision in the right ballpark and improved measurably after a real bug fix, "
        "openly reporting where it still falls short of formal statistical validation, rather than "
        "overstating agreement with reality.",
    ]
    text_page(pdf, "6. Conclusions", body)


def main():
    detail = pd.read_csv(os.path.join(HERE, "predicted_logmar_per_array_model.csv"))
    opt_map = pd.read_csv(os.path.join(REPO, "new_sweeps", "per_M_optimum_map.csv"))
    postfix_pred = pd.read_csv(os.path.join(STAGE4_OUT, "wang2009_validation_postfix_predicted.csv"))
    postfix_stats = pd.read_csv(os.path.join(STAGE4_OUT, "wang2009_validation_postfix_stats.csv"))
    calib_postfix = pd.read_csv(os.path.join(HERE, "wang2009_calibration_pooled_stats_postfix.csv"))

    with PdfPages(OUT_PDF) as pdf:
        title_page(pdf)
        methodology_page(pdf)
        array_model_page(pdf, detail, opt_map)
        stale_data_page(pdf)
        array_relevant_deviation_page(pdf)
        full_grid_page(pdf, postfix_pred)
        r2_summary_page(pdf, postfix_stats, calib_postfix)
        kim_anchor_page(pdf)
        search_honesty_page(pdf)
        conclusions_page(pdf)
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
