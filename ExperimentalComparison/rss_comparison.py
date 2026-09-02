"""
ExperimentalComparison/rss_comparison.py

Adds an RSS (root-sum-square geometric+diffraction) theoretical blur model
alongside the existing ASM (blur_sweep.csv, full angular-spectrum propagation)
comparison already in measurements/all_measurements.csv. Does not modify or
overwrite any existing file -- reads all_measurements.csv read-only, writes
three NEW files only.

EYE CONSTANTS -- traced to source, not assumed:
  /Users/parikshitnarang/Pinholeproject/new_sweeps/run_blur_sweep.py (the
  actual script that generated blur_sweep.csv) calls
  phase2_retina.run_pipeline_point(..., P0=60.0, n_prime=1.336,
  wavelength=550e-9, refractive_index_correction=True) -- literal values at
  lines 29/56 of that file:
      P0       = 60.0          (D, reduced-eye optical power)
      n_prime  = 1.336         (vitreous refractive index)
      lambda0  = 550.0 nm      (vacuum wavelength)

  f_prime: stage2_fixed/myopia_axial.py and phase2_retina.py both define the
  reduced eye's image-side focal length as f_prime = n_prime / P0 (NOT the
  naive 1/P0 -- that's the refractive_index_correction=False, air-equivalent
  case, which run_blur_sweep.py does not use). So:
      f_prime_um = (n_prime / P0) * 1e6 = (1.336 / 60.0) * 1e6 = 22266.667 um

  lambda for c_diff: phase2_retina.py's own docstring (lines ~55-62) warns
  explicitly that f_prime = n_prime/P0 is a media-reduced (vitreous-space)
  distance, and pairing it with the raw vacuum wavelength "under-applies the
  lens's converging phase by a factor of n_prime" -- the same physical
  inconsistency this script must avoid to stay faithful to how blur_sweep.csv
  was actually computed. So the wavelength used in c_diff here is the
  effective (media-reduced) wavelength, exactly as phase2_retina.py uses
  internally:
      lambda_um = 0.550 / 1.336 = 0.411677 um   (NOT the raw 0.550 um)

  This is a judgment call, logged here and in the output report: it is the
  internally-consistent pairing given f_prime's definition, not an
  independently invented constant.

RSS MODEL (as specified):
  c_geom_um(a_hole_um, M) = a_hole_um * M / P0
  c_diff_um(a_hole_um)    = 1.22 * lambda_um * f_prime_um / a_hole_um
  c_tot_RSS(a_hole_um, M) = sqrt(c_geom^2 + c_diff^2)
  predicted_ratio_RSS(folder, M) = c_tot_RSS(a_hole_um, M) / c_tot_RSS(a_hole_um, 0)
  -- the M=0 reference is evaluated analytically (c_geom=0 at M=0, so
  c_tot_RSS(M=0) = c_diff alone) -- it needs no measured or ASM-table M=0
  row, so predicted_ratio_RSS is computable for every (aperture, M) pair
  including 1000b (whose measured M=0 photo is unparseable) and 1200b (whose
  aperture has no blur_sweep.csv row at all, since RSS is a closed-form
  formula, not a table lookup).

Run: python3 rss_comparison.py
"""
import os
import csv
import math

ROOT = "/Users/parikshitnarang/Pinholeproject"
EXP_DIR = os.path.join(ROOT, "ExperimentalComparison")
ALL_MEAS_CSV = os.path.join(EXP_DIR, "measurements", "all_measurements.csv")
OUT_CSV = os.path.join(EXP_DIR, "measurements", "rss_vs_asm_comparison.csv")
OUT_SUMMARY = os.path.join(EXP_DIR, "report", "rss_comparison_summary.txt")
OUT_PDF = os.path.join(EXP_DIR, "report", "RSS_vs_ASM_Comparison_Report.pdf")

# --- eye constants, traced to new_sweeps/run_blur_sweep.py (see docstring) ---
P0 = 60.0                       # D
N_PRIME = 1.336
LAMBDA_VACUUM_UM = 550.0 / 1000.0
LAMBDA_UM = LAMBDA_VACUUM_UM / N_PRIME   # effective (media-reduced), see docstring
F_PRIME_UM = (N_PRIME / P0) * 1e6

APERTURE_UM = {"400b": 400.0, "600b": 600.0, "700b": 700.0, "1000b": 1000.0, "1200b": 1200.0}
FOLDER_ORDER = ["400b", "600b", "700b", "1000b", "1200b"]
M_ORDER = [0, 1, 2, 3, 4, 6, 8]

DEV_GOOD_THRESHOLD = 20.0


def c_geom_um(a_hole_um, M):
    return a_hole_um * M / P0


def c_diff_um(a_hole_um):
    return 1.22 * LAMBDA_UM * F_PRIME_UM / a_hole_um


def c_tot_rss_um(a_hole_um, M):
    return math.sqrt(c_geom_um(a_hole_um, M) ** 2 + c_diff_um(a_hole_um) ** 2)


def predicted_ratio_rss(a_hole_um, M):
    ref = c_tot_rss_um(a_hole_um, 0.0)
    return c_tot_rss_um(a_hole_um, M) / ref


def load_all_measurements():
    with open(ALL_MEAS_CSV) as f:
        return list(csv.DictReader(f))


def main():
    rows = load_all_measurements()
    out_rows = []
    for r in rows:
        folder = r["folder"]
        M = float(r["parsed_M"])
        a_hole_um = APERTURE_UM[folder]
        pred_rss = predicted_ratio_rss(a_hole_um, M)

        measured_ratio = r["normalized_ratio_measured"]
        pred_asm = r["predicted_ratio_theory"]
        pct_dev_asm = r["pct_deviation"]

        pct_dev_rss = ""
        closer_model = ""
        if measured_ratio != "":
            mr = float(measured_ratio)
            pct_dev_rss_val = (mr - pred_rss) / pred_rss * 100.0
            pct_dev_rss = round(pct_dev_rss_val, 2)
            if pct_dev_asm != "" and M != 0.0:
                # M=0 is a tautological tie (every model and the measured ratio
                # are exactly 1.0 by construction at the normalization point) --
                # not a real predictive comparison, so no verdict is assigned
                # there rather than letting a 0.0%-vs-0.0% tie inflate either
                # model's count.
                closer_model = "ASM" if abs(float(pct_dev_asm)) < abs(pct_dev_rss_val) else "RSS"

        out_rows.append({
            "aperture_um": a_hole_um, "folder": folder, "M": r["parsed_M"],
            "measured_ratio": measured_ratio,
            "predicted_ratio_ASM": pred_asm,
            "pct_deviation_ASM": pct_dev_asm,
            "predicted_ratio_RSS": round(pred_rss, 5),
            "pct_deviation_RSS": pct_dev_rss,
            "closer_model": closer_model,
        })

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["aperture_um", "folder", "M", "measured_ratio",
                                          "predicted_ratio_ASM", "pct_deviation_ASM",
                                          "predicted_ratio_RSS", "pct_deviation_RSS",
                                          "closer_model"])
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"wrote {OUT_CSV} ({len(out_rows)} rows)")

    write_summary(out_rows)
    build_pdf(out_rows)
    return out_rows


def write_summary(out_rows):
    lines = []
    lines.append("RSS vs ASM THEORETICAL MODEL COMPARISON -- PLAIN-LANGUAGE SUMMARY")
    lines.append("=" * 74)
    lines.append("")
    lines.append("EYE CONSTANTS (traced to new_sweeps/run_blur_sweep.py, the actual script")
    lines.append("that generated blur_sweep.csv -- not assumed separately, see")
    lines.append("rss_comparison.py docstring for the full derivation):")
    lines.append(f"  P0 = {P0} D, n_prime = {N_PRIME}, vacuum wavelength = {LAMBDA_VACUUM_UM*1000:.0f} nm")
    lines.append(f"  f_prime_um = n_prime/P0 * 1e6 = {F_PRIME_UM:.3f} um  (NOT naive 1/P0 --")
    lines.append("    run_blur_sweep.py used refractive_index_correction=True)")
    lines.append(f"  lambda_um used in c_diff = vacuum/n_prime = {LAMBDA_UM:.6f} um (media-reduced,")
    lines.append("    matching phase2_retina.py's own documented f_prime/wavelength pairing --")
    lines.append("    pairing a media-reduced f_prime with the raw vacuum wavelength would be")
    lines.append("    the exact inconsistency that module's own docstring warns against)")
    lines.append("")
    lines.append("This reuses the measured data and ASM comparison from all_measurements.csv")
    lines.append("as-is (including its existing exposure/saturation notes) -- nothing was")
    lines.append("re-measured or re-flagged here.")
    lines.append("")

    by_folder = {}
    for r in out_rows:
        by_folder.setdefault(r["folder"], []).append(r)

    lines.append("PER-APERTURE RESULT")
    lines.append("-" * 74)
    for folder in FOLDER_ORDER:
        rows = by_folder.get(folder, [])
        a_hole = APERTURE_UM[folder]
        lines.append(f"\n{folder} (a_hole_um={a_hole:.0f}):")
        has_asm = any(r["predicted_ratio_ASM"] != "" for r in rows)
        has_measured = any(r["measured_ratio"] != "" for r in rows)
        if not has_measured:
            lines.append("  No measured normalized ratio available for this folder (no valid M=0")
            lines.append("  reference photo) -- RSS's predicted ratio is still reported below")
            lines.append("  (it's a closed-form formula, needs no measured reference), but no")
            lines.append("  measured-vs-model comparison or 'closer model' verdict is possible.")
        elif not has_asm:
            lines.append("  No ASM theory match for this aperture in blur_sweep.csv -- RSS-ONLY")
            lines.append("  comparison (RSS is closed-form, works for any aperture size).")
        for r in rows:
            bits = [f"M={r['M']}", f"predicted_RSS={r['predicted_ratio_RSS']}"]
            if r["measured_ratio"] != "":
                bits.append(f"measured={r['measured_ratio']}")
                bits.append(f"%dev_RSS={r['pct_deviation_RSS']:+.1f}%" if r['pct_deviation_RSS'] != "" else "")
                if r["pct_deviation_ASM"] != "":
                    bits.append(f"%dev_ASM={float(r['pct_deviation_ASM']):+.1f}%")
                    bits.append(f"closer={r['closer_model']}" if r["closer_model"] != "" else "closer=n/a (M=0 tie)")
            lines.append("    " + ", ".join(b for b in bits if b))

    lines.append("")
    lines.append("-" * 74)
    lines.append("\nTALLY (rows where BOTH ASM and RSS predictions and a measured ratio exist,")
    lines.append("excluding M=0 -- every model equals the measured ratio there by construction")
    lines.append("(it's the normalization point itself), so it is not a real predictive test.")
    lines.append("i.e. 400b/600b/700b at M=1..8; 1200b has no ASM match, 1000b has no measured")
    lines.append("ratio, so neither can contribute a 'closer model' verdict):")
    comparable = [r for r in out_rows if r["closer_model"] != ""]
    n_asm = sum(1 for r in comparable if r["closer_model"] == "ASM")
    n_rss = sum(1 for r in comparable if r["closer_model"] == "RSS")
    lines.append(f"  {len(comparable)} comparable rows: ASM closer in {n_asm}, RSS closer in {n_rss}.")
    if comparable:
        mean_abs_asm = sum(abs(float(r["pct_deviation_ASM"])) for r in comparable) / len(comparable)
        mean_abs_rss = sum(abs(float(r["pct_deviation_RSS"])) for r in comparable) / len(comparable)
        lines.append(f"  Mean |%deviation|: ASM = {mean_abs_asm:.1f}%, RSS = {mean_abs_rss:.1f}%.")
        lines.append("")
        lines.append("HONEST VERDICT")
        if abs(mean_abs_asm - mean_abs_rss) < 3.0:
            lines.append(f"  The two models are close on average (within 3 points of each other's mean")
            lines.append(f"  |%deviation|) -- INCONCLUSIVE overall which model the real data favors,")
            lines.append(f"  especially given the near-universal core-saturation and the unexplained")
            lines.append(f"  high-M plateau already documented in comparison_summary.txt. Not")
            lines.append(f"  overclaiming a winner where the margin doesn't support one.")
        elif n_rss > n_asm or mean_abs_rss < mean_abs_asm:
            lines.append(f"  RSS fits the measured data better on average ({mean_abs_rss:.1f}% vs")
            lines.append(f"  {mean_abs_asm:.1f}% mean |deviation|, {n_rss}/{len(comparable)} rows closer to RSS).")
            lines.append(f"  This is plausible and worth stating plainly, not as an embarrassment for")
            lines.append(f"  ASM: RSS is known to UNDERPREDICT blur growth relative to full")
            lines.append(f"  wave-optics diffraction, and the measured data itself plateaus at high M")
            lines.append(f"  well below ASM's prediction (see comparison_summary.txt) -- a simpler")
            lines.append(f"  model that also underpredicts high-M growth can end up numerically closer")
            lines.append(f"  to a measurement that plateaus, without that meaning RSS's physics is")
            lines.append(f"  more correct. Whether that's really what's happening here, or whether the")
            lines.append(f"  measured plateau has a different, still-undetermined cause (see prior")
            lines.append(f"  report), is NOT resolved by this comparison alone.")
        else:
            lines.append(f"  ASM fits the measured data better on average ({mean_abs_asm:.1f}% vs")
            lines.append(f"  {mean_abs_rss:.1f}% mean |deviation|, {n_asm}/{len(comparable)} rows closer to ASM).")
    else:
        lines.append("  No rows have both ASM and RSS predictions plus a measured ratio -- no tally possible.")

    lines.append("")
    lines.append("-" * 74)
    lines.append("\n1200b (RSS-only, no ASM match in blur_sweep.csv):")
    r1200 = by_folder.get("1200b", [])
    for r in r1200:
        line = f"  M={r['M']}: predicted_RSS={r['predicted_ratio_RSS']}"
        if r["measured_ratio"] != "":
            line += f", measured={r['measured_ratio']}, %dev_RSS={r['pct_deviation_RSS']:+.1f}%"
        lines.append(line)

    lines.append("")
    lines.append("-" * 74)
    lines.append("\n1000b (measured M=0 unparseable -- RSS predicted ratio only, no comparison):")
    r1000 = by_folder.get("1000b", [])
    for r in r1000:
        lines.append(f"  M={r['M']}: predicted_RSS={r['predicted_ratio_RSS']}, "
                      f"predicted_ASM={r['predicted_ratio_ASM']} (measured ratio: n/a)")

    with open(OUT_SUMMARY, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT_SUMMARY}")


COLOR_MEASURED = "#2C6E9E"
COLOR_ASM = "#E07B39"
COLOR_RSS = "#4E9F3D"  # third series, distinguishable from the blue/amber pair


def build_pdf(out_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    by_folder = {}
    for r in out_rows:
        by_folder.setdefault(r["folder"], {})[float(r["M"])] = r

    with PdfPages(OUT_PDF) as pdf:
        for folder in FOLDER_ORDER:
            _render_page(pdf, plt, folder, by_folder.get(folder, {}))
        _render_tally_page(pdf, plt, out_rows)
    print(f"wrote {OUT_PDF}")


def _render_page(pdf, plt, folder, rows_by_M):
    fig = plt.figure(figsize=(8.5, 8))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.3, 1.2], hspace=0.3,
                           top=0.90, bottom=0.06, left=0.1, right=0.95)
    a_hole = APERTURE_UM[folder]
    has_asm = any(r["predicted_ratio_ASM"] != "" for r in rows_by_M.values())
    subtitle = "" if has_asm else "  (RSS-only -- no ASM match in blur_sweep.csv)"
    fig.suptitle(f"{folder}  (aperture = {a_hole:.0f} µm){subtitle}", fontsize=13, fontweight="bold")

    ax = fig.add_subplot(gs[0])
    Ms = sorted(rows_by_M.keys())
    meas = [(M, float(rows_by_M[M]["measured_ratio"])) for M in Ms if rows_by_M[M]["measured_ratio"] != ""]
    asm = [(M, float(rows_by_M[M]["predicted_ratio_ASM"])) for M in Ms if rows_by_M[M]["predicted_ratio_ASM"] != ""]
    rss = [(M, float(rows_by_M[M]["predicted_ratio_RSS"])) for M in Ms]
    if meas:
        xs, ys = zip(*meas)
        ax.plot(xs, ys, "o-", color=COLOR_MEASURED, label="Measured", linewidth=2, markersize=6)
    if asm:
        xs, ys = zip(*asm)
        ax.plot(xs, ys, "s--", color=COLOR_ASM, label="Predicted (ASM)", linewidth=2, markersize=6)
    xs, ys = zip(*rss)
    ax.plot(xs, ys, "^:", color=COLOR_RSS, label="Predicted (RSS)", linewidth=2, markersize=6)
    ax.set_xlabel("M (diopters)")
    ax.set_ylabel("r_EE_50(M) / r_EE_50(M=0)")
    ax.set_xticks(M_ORDER)
    ax.grid(axis="y", color="#e0e0e0", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, loc="best")

    ax_table = fig.add_subplot(gs[1])
    ax_table.axis("off")
    col_labels = ["M", "Measured", "ASM", "%dev ASM", "RSS", "%dev RSS", "Closer"]
    cell_text = []
    for M in Ms:
        r = rows_by_M[M]
        cell_text.append([
            f"{M:g}",
            r["measured_ratio"] if r["measured_ratio"] != "" else "n/a",
            r["predicted_ratio_ASM"] if r["predicted_ratio_ASM"] != "" else "n/a",
            f"{float(r['pct_deviation_ASM']):+.1f}%" if r["pct_deviation_ASM"] != "" else "n/a",
            f"{r['predicted_ratio_RSS']}",
            f"{r['pct_deviation_RSS']:+.1f}%" if r["pct_deviation_RSS"] != "" else "n/a",
            r["closer_model"] if r["closer_model"] != "" else "n/a",
        ])
    tbl = ax_table.table(cellText=cell_text, colLabels=col_labels, loc="upper center",
                          cellLoc="center", colLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.5)
    pdf.savefig(fig)
    plt.close(fig)


def _render_tally_page(pdf, plt, out_rows):
    fig = plt.figure(figsize=(8.5, 6))
    ax = fig.add_subplot(111)
    comparable = [r for r in out_rows if r["closer_model"] != ""]
    n_asm = sum(1 for r in comparable if r["closer_model"] == "ASM")
    n_rss = sum(1 for r in comparable if r["closer_model"] == "RSS")
    mean_asm = (sum(abs(float(r["pct_deviation_ASM"])) for r in comparable) / len(comparable)) if comparable else 0
    mean_rss = (sum(abs(float(r["pct_deviation_RSS"])) for r in comparable) / len(comparable)) if comparable else 0

    bars = ax.bar(["ASM", "RSS"], [n_asm, n_rss], color=[COLOR_ASM, COLOR_RSS], width=0.5)
    for b, n in zip(bars, [n_asm, n_rss]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05, str(n), ha="center", fontsize=11)
    ax.set_ylabel(f"# of {len(comparable)} comparable rows closer to this model")
    ax.set_title("Final tally: which model is closer to measured data\n"
                  "(400b/600b/700b only -- 1200b has no ASM match, 1000b has no measured ratio)",
                  fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(0.5, -0.18, f"Mean |%deviation|:  ASM = {mean_asm:.1f}%   RSS = {mean_rss:.1f}%",
             ha="center", transform=ax.transAxes, fontsize=10)
    pdf.savefig(fig)
    plt.close(fig)


if __name__ == "__main__":
    main()
