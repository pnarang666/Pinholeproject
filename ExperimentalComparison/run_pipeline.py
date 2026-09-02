"""
ExperimentalComparison/run_pipeline.py

Driver: DNG -> TIFF -> exposure gate -> blob r_EE_50_px -> M=0-normalized
ratio -> compare to new_sweeps/blur_sweep.csv theory. See analyze.py for the
measurement definitions/rationale. Writes all outputs under
ExperimentalComparison/{measurements,report}/. Does not touch ExP2/ (originals).

Run: python3 run_pipeline.py
"""
import os
import csv
import time

import numpy as np

import analyze as A

THEORY_CSV = A.BLUR_SWEEP_CSV
SCRATCH_DIR = "/tmp/exp_comparison_scratch"


def load_theory():
    theory = {}  # a_hole_um(float) -> {M(float): r_EE_50_um}
    with open(THEORY_CSV) as f:
        for row in csv.DictReader(f):
            ah = float(row["a_hole_um"])
            m = float(row["M_diopters"])
            theory.setdefault(ah, {})[m] = float(row["r_EE_50_um"])
    return theory


def discover(folder):
    d = os.path.join(A.EXP2, folder)
    return sorted(os.listdir(d))


def process_folder(folder, unparseable_rows, flagged_rows):
    """Returns dict M(int) -> measurement dict (only for valid, unflagged
    images), plus records retake notes."""
    src_dir = os.path.join(A.EXP2, folder)
    dst_dir = os.path.join(A.TIFF_DIR, folder)
    os.makedirs(dst_dir, exist_ok=True)
    scratch_dir = os.path.join(SCRATCH_DIR, folder)
    os.makedirs(scratch_dir, exist_ok=True)

    results = {}
    for fname in discover(folder):
        if not fname.lower().endswith(".dng"):
            continue
        M, note, is_retake = A.parse_filename(folder, fname)
        if M is None:
            unparseable_rows.append({"folder": folder, "filename": fname, "reason": note})
            print(f"  [unparseable] {folder}/{fname}: {note}")
            continue

        stem = os.path.splitext(fname)[0]
        scratch_tiff = os.path.join(scratch_dir, stem + ".tiff")  # full-res, temporary
        deliverable_tiff = os.path.join(dst_dir, stem + ".tiff")  # downsized, kept
        ok, err = A.convert_to_tiff(os.path.join(src_dir, fname), scratch_tiff)
        if not ok:
            unparseable_rows.append({"folder": folder, "filename": fname,
                                      "reason": f"sips conversion failed: {err}"})
            print(f"  [conversion failed] {folder}/{fname}: {err}")
            continue

        try:
            arr = A.read_tiff_rgb_u16(scratch_tiff)
        except ValueError as e:
            unparseable_rows.append({"folder": folder, "filename": fname,
                                      "reason": f"TIFF read failed: {e}"})
            print(f"  [read failed] {folder}/{fname}: {e}")
            os.remove(scratch_tiff)
            continue

        A.save_downsized_copy(arr, deliverable_tiff)
        os.remove(scratch_tiff)  # full-res scratch never persists -- disk space

        stats = A.channel_stats(arr)
        names = ["R", "G", "B"][:arr.shape[2]]
        flag_reason = A.exposure_flag_reason(stats, names)
        if flag_reason:
            flagged_rows.append({
                "folder": folder, "filename": fname, "parsed_M": M,
                "R_mean": round(stats[0][2], 2),
                "G_mean": round(stats[1][2], 2) if len(stats) > 1 else "",
                "B_mean": round(stats[2][2], 2) if len(stats) > 2 else "",
                "reason": flag_reason,
            })
            print(f"  [FLAGGED exposure] {folder}/{fname} (M={M}): {flag_reason}")
            continue

        t0 = time.time()
        try:
            blob = A.measure_blob(arr)
        except ValueError as e:
            unparseable_rows.append({"folder": folder, "filename": fname,
                                      "reason": f"blob measurement failed: {e}"})
            print(f"  [blob measurement failed] {folder}/{fname}: {e}")
            continue
        elapsed = time.time() - t0

        core_saturated = any(mx >= A.NATIVE_RANGE for (mn, mx, mean) in stats)
        results[M] = {
            "folder": folder, "filename": fname, "M": M, "is_retake": is_retake,
            "note": note, "r_EE_50_px": blob["r_EE_50_px"],
            "centroid_x_px": blob["centroid_x_px"], "centroid_y_px": blob["centroid_y_px"],
            "total_intensity": blob["total_intensity"],
            "threshold_frac_used": blob["threshold_frac_used"],
            "core_saturated": core_saturated,
            "deliverable_tiff": deliverable_tiff,
            "thumbnail": A.make_thumbnail(arr),
            "channel_means": tuple(round(s[2], 2) for s in stats),
        }
        print(f"  [ok] {folder}/{fname} M={M} r_EE_50_px={blob['r_EE_50_px']:.2f} "
              f"(thr_frac={blob['threshold_frac_used']:.2f}, {elapsed:.1f}s)"
              + (" [CORE SATURATED]" if core_saturated else ""))
    return results


def main():
    os.makedirs(A.MEAS_DIR, exist_ok=True)
    os.makedirs(A.REPORT_DIR, exist_ok=True)

    theory = load_theory()

    unparseable_rows = []
    flagged_rows = []
    all_results = {}  # folder -> {M: measurement}

    for folder in A.ALL_FOLDERS:
        print(f"\n=== {folder} ===")
        all_results[folder] = process_folder(folder, unparseable_rows, flagged_rows)

    # ---- normalization + theory comparison ----
    all_measurements_rows = []
    control_rows = []
    folder_notes = {}  # folder -> list of str, for the summary

    for folder in APERTURE_FOLDERS_ORDER:
        res = all_results[folder]
        notes = folder_notes.setdefault(folder, [])
        m0 = res.get(0)
        if m0 is None:
            notes.append(f"No valid M=0 (reference) image for {folder} -- normalized "
                          f"ratios cannot be computed for this folder; raw r_EE_50_px "
                          f"only is reported.")
        a_hole = A.APERTURE_FOLDERS[folder]
        theory_for_ah = theory.get(a_hole)
        if theory_for_ah is None:
            notes.append(f"No exact a_hole_um={a_hole:.0f} row exists in blur_sweep.csv "
                         f"(nearest available: {sorted(k for k in theory if abs(k-a_hole)<400)}) "
                         f"-- theory comparison skipped for {folder}, not guessed/interpolated.")
        theory_r0 = theory_for_ah.get(0.0) if theory_for_ah else None

        for M in sorted(res.keys()):
            m = res[M]
            norm_ratio = (m["r_EE_50_px"] / m0["r_EE_50_px"]) if m0 else None
            pred_ratio = None
            pct_dev = None
            if theory_for_ah is not None and theory_r0 is not None and M in theory_for_ah:
                pred_ratio = theory_for_ah[M] / theory_r0
                if norm_ratio is not None and pred_ratio != 0:
                    pct_dev = (norm_ratio - pred_ratio) / pred_ratio * 100.0

            note_bits = []
            if m["is_retake"]:
                note_bits.append("possible retake (extra digit in filename)")
            if m["core_saturated"]:
                note_bits.append("core pixel-saturated (>=65535 in a channel) -- r_EE_50 may be biased low")

            all_measurements_rows.append({
                "folder": folder, "filename": m["filename"], "parsed_M": M,
                "aperture_um": a_hole,
                "measured_r_EE_50_px": round(m["r_EE_50_px"], 3),
                "normalized_ratio_measured": round(norm_ratio, 5) if norm_ratio is not None else "",
                "predicted_ratio_theory": round(pred_ratio, 5) if pred_ratio is not None else "",
                "pct_deviation": round(pct_dev, 2) if pct_dev is not None else "",
                "notes": "; ".join(note_bits),
            })

    # Nopinholeb control (separate, no theory)
    res = all_results[A.CONTROL_FOLDER]
    m0 = res.get(0)
    if m0 is None:
        folder_notes[A.CONTROL_FOLDER] = [f"No valid M=0 reference for {A.CONTROL_FOLDER} -- "
                                           f"cannot normalize control dataset."]
    else:
        folder_notes[A.CONTROL_FOLDER] = []
    for M in sorted(res.keys()):
        m = res[M]
        norm_ratio = (m["r_EE_50_px"] / m0["r_EE_50_px"]) if m0 else None
        note_bits = []
        if m["core_saturated"]:
            note_bits.append("core pixel-saturated (>=65535 in a channel)")
        control_rows.append({
            "folder": A.CONTROL_FOLDER, "filename": m["filename"], "parsed_M": M,
            "measured_r_EE_50_px": round(m["r_EE_50_px"], 3),
            "normalized_ratio_measured": round(norm_ratio, 5) if norm_ratio is not None else "",
            "notes": "; ".join(note_bits),
        })

    # ---- write CSVs ----
    def write_csv(path, rows, fieldnames):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"wrote {path} ({len(rows)} rows)")

    write_csv(os.path.join(A.MEAS_DIR, "all_measurements.csv"), all_measurements_rows,
              ["folder", "filename", "parsed_M", "aperture_um", "measured_r_EE_50_px",
               "normalized_ratio_measured", "predicted_ratio_theory", "pct_deviation", "notes"])
    write_csv(os.path.join(A.MEAS_DIR, "flagged_exposure_issues.csv"), flagged_rows,
              ["folder", "filename", "parsed_M", "R_mean", "G_mean", "B_mean", "reason"])
    write_csv(os.path.join(A.MEAS_DIR, "unparseable_files.csv"), unparseable_rows,
              ["folder", "filename", "reason"])
    write_csv(os.path.join(A.MEAS_DIR, "nopinhole_control.csv"), control_rows,
              ["folder", "filename", "parsed_M", "measured_r_EE_50_px",
               "normalized_ratio_measured", "notes"])

    write_summary(all_measurements_rows, control_rows, unparseable_rows, flagged_rows, folder_notes)
    build_pdf_report(all_results, all_measurements_rows, control_rows, folder_notes)

    return all_results, all_measurements_rows, folder_notes, theory


M_ORDER = [0, 1, 2, 3, 4, 6, 8]
COLOR_MEASURED = "#2C6E9E"   # dark blue
COLOR_PREDICTED = "#E07B39"  # amber -- CVD-safe pair, consistent across all pages


def build_pdf_report(all_results, all_measurements_rows, control_rows, folder_notes):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    by_folder_rows = {}
    for r in all_measurements_rows:
        by_folder_rows.setdefault(r["folder"], {})[r["parsed_M"]] = r

    pdf_path = os.path.join(A.REPORT_DIR, "Experimental_Comparison_Report.pdf")
    with PdfPages(pdf_path) as pdf:
        for folder in APERTURE_FOLDERS_ORDER:
            _render_aperture_page(pdf, plt, folder, all_results.get(folder, {}),
                                   by_folder_rows.get(folder, {}), folder_notes.get(folder, []))
        _render_control_page(pdf, plt, all_results.get(A.CONTROL_FOLDER, {}),
                              control_rows, folder_notes.get(A.CONTROL_FOLDER, []))
    print(f"wrote {pdf_path}")


def _thumb_row(fig, gs_row, res, title_prefix=""):
    n = len(M_ORDER)
    sub = gs_row.subgridspec(1, n, wspace=0.08)
    for i, M in enumerate(M_ORDER):
        ax = fig.add_subplot(sub[0, i])
        ax.set_xticks([]); ax.set_yticks([])
        m = res.get(M)
        if m is not None:
            ax.imshow(m["thumbnail"])
            ax.set_title(f"M={M}", fontsize=9)
        else:
            ax.set_facecolor("#f0f0f0")
            ax.text(0.5, 0.5, f"M={M}\nn/a", ha="center", va="center", fontsize=8, color="#888")
        for spine in ax.spines.values():
            spine.set_edgecolor("#cccccc")


def _render_aperture_page(pdf, plt, folder, res, rows_by_M, notes):
    fig = plt.figure(figsize=(8.5, 11))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.1, 1.3, 1.4], hspace=0.35,
                           top=0.93, bottom=0.05, left=0.08, right=0.95)
    a_hole = A.APERTURE_FOLDERS[folder]
    fig.suptitle(f"{folder}  (aperture = {a_hole:.0f} µm)  --  M-sweep comparison", fontsize=13, fontweight="bold")

    _thumb_row(fig, gs[0], res)

    ax_plot = fig.add_subplot(gs[1])
    Ms_present = sorted(rows_by_M.keys())
    meas = [rows_by_M[M]["normalized_ratio_measured"] for M in Ms_present]
    pred = [rows_by_M[M]["predicted_ratio_theory"] for M in Ms_present]
    have_meas = [(M, v) for M, v in zip(Ms_present, meas) if v != ""]
    have_pred = [(M, v) for M, v in zip(Ms_present, pred) if v != ""]
    if have_meas:
        xs, ys = zip(*have_meas)
        ax_plot.plot(xs, ys, "o-", color=COLOR_MEASURED, label="Measured (normalized)", linewidth=2, markersize=6)
    if have_pred:
        xs, ys = zip(*have_pred)
        ax_plot.plot(xs, ys, "s--", color=COLOR_PREDICTED, label="Predicted (theory)", linewidth=2, markersize=6)
    if not have_meas and not have_pred:
        ax_plot.text(0.5, 0.5, "No normalized-ratio data available for this folder\n(see notes)",
                     ha="center", va="center", transform=ax_plot.transAxes, color="#888")
    ax_plot.set_xlabel("M (diopters)")
    ax_plot.set_ylabel("r_EE_50(M) / r_EE_50(M=0)")
    ax_plot.set_xticks(M_ORDER)
    ax_plot.grid(axis="y", color="#e0e0e0", linewidth=0.8)
    ax_plot.spines["top"].set_visible(False)
    ax_plot.spines["right"].set_visible(False)
    if have_meas or have_pred:
        ax_plot.legend(frameon=False, loc="best")

    ax_table = fig.add_subplot(gs[2])
    ax_table.axis("off")
    col_labels = ["M", "r_EE_50 (px)", "Measured ratio", "Predicted ratio", "% dev", "Notes"]
    cell_text = []
    for M in Ms_present:
        r = rows_by_M[M]
        cell_text.append([
            f"{M}", f"{r['measured_r_EE_50_px']:.1f}",
            f"{r['normalized_ratio_measured']}" if r["normalized_ratio_measured"] != "" else "n/a",
            f"{r['predicted_ratio_theory']}" if r["predicted_ratio_theory"] != "" else "n/a",
            f"{r['pct_deviation']:+.1f}%" if r["pct_deviation"] != "" else "n/a",
            r["notes"][:28],
        ])
    if cell_text:
        tbl = ax_table.table(cellText=cell_text, colLabels=col_labels, loc="upper center",
                              cellLoc="center", colLoc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(7.5)
        tbl.scale(1, 1.4)
        tbl.auto_set_column_width(col=list(range(len(col_labels))))
    note_text = "\n".join(f"- {n}" for n in notes) if notes else ""
    if note_text:
        ax_table.text(0, -0.05 - 0.06 * len(cell_text), note_text, fontsize=7.5, color="#555",
                       va="top", transform=ax_table.transAxes, wrap=True)

    pdf.savefig(fig)
    plt.close(fig)


def _render_control_page(pdf, plt, res, control_rows, notes):
    fig = plt.figure(figsize=(8.5, 11))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.1, 1.3, 1.2], hspace=0.35,
                           top=0.93, bottom=0.05, left=0.08, right=0.95)
    fig.suptitle(f"{A.CONTROL_FOLDER}  (control -- no aperture; NOT compared to blur_sweep.csv theory)",
                 fontsize=13, fontweight="bold")

    _thumb_row(fig, gs[0], res)

    ax_plot = fig.add_subplot(gs[1])
    have = [(r["parsed_M"], r["normalized_ratio_measured"]) for r in control_rows
            if r["normalized_ratio_measured"] != ""]
    if have:
        xs, ys = zip(*sorted(have))
        ax_plot.plot(xs, ys, "o-", color=COLOR_MEASURED, label="Measured (normalized, control)",
                     linewidth=2, markersize=6)
        ax_plot.legend(frameon=False, loc="best")
    else:
        ax_plot.text(0.5, 0.5, "No normalized-ratio data available (see notes)",
                     ha="center", va="center", transform=ax_plot.transAxes, color="#888")
    ax_plot.set_xlabel("M (diopters)")
    ax_plot.set_ylabel("r_EE_50(M) / r_EE_50(M=0)  [pixels, control]")
    ax_plot.set_xticks(M_ORDER)
    ax_plot.grid(axis="y", color="#e0e0e0", linewidth=0.8)
    ax_plot.spines["top"].set_visible(False)
    ax_plot.spines["right"].set_visible(False)

    ax_table = fig.add_subplot(gs[2])
    ax_table.axis("off")
    col_labels = ["M", "r_EE_50 (px)", "Normalized ratio", "Notes"]
    cell_text = [[f"{r['parsed_M']}", f"{r['measured_r_EE_50_px']:.1f}",
                  f"{r['normalized_ratio_measured']}" if r["normalized_ratio_measured"] != "" else "n/a",
                  r["notes"][:40]] for r in sorted(control_rows, key=lambda r: r["parsed_M"])]
    if cell_text:
        tbl = ax_table.table(cellText=cell_text, colLabels=col_labels, loc="upper center",
                              cellLoc="center", colLoc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1, 1.4)
    note_text = "\n".join(f"- {n}" for n in notes) if notes else ""
    if note_text:
        ax_table.text(0, -0.05 - 0.06 * len(cell_text), note_text, fontsize=7.5, color="#555",
                       va="top", transform=ax_table.transAxes, wrap=True)

    pdf.savefig(fig)
    plt.close(fig)


DEV_GOOD_THRESHOLD = 20.0  # |%deviation| at/below this counts as "matched theory well"


def write_summary(all_measurements_rows, control_rows, unparseable_rows, flagged_rows, folder_notes):
    lines = []
    lines.append("EXPERIMENTAL vs THEORETICAL r_EE_50 COMPARISON -- PLAIN-LANGUAGE SUMMARY")
    lines.append("=" * 74)
    lines.append("")
    lines.append("CALIBRATION STATUS: pixel-to-micrometer conversion is NOT calibrated.")
    lines.append("All comparisons below are between two calibration-independent ratios --")
    lines.append("measured r_EE_50(M)/r_EE_50(M=0) in pixels vs. the same ratio computed")
    lines.append("from blur_sweep.csv's theoretical r_EE_50_um. No absolute-size claim is")
    lines.append("made or possible from this data yet.")
    lines.append("")
    lines.append("METHODOLOGY NOTES (found during this run, not assumed going in):")
    lines.append("- sips writes a REAL 16-bit-per-channel TIFF (confirmed via TIFF tag")
    lines.append("  inspection). The installed Pillow silently downcast this to 8-bit on")
    lines.append("  array read -- caught before any measurement was finalized; all reading")
    lines.append("  in this pipeline uses OpenCV instead, verified to preserve true uint16")
    lines.append("  values losslessly. Exposure-flag thresholds are therefore 5%/95% of")
    lines.append("  the native 0-65535 range, not literal 0/255.")
    lines.append("- This machine had only ~1-3GB free disk system-wide during this run")
    lines.append("  (pre-existing, unrelated to this task -- /Users volume was ~99% full).")
    lines.append("  Full-resolution 16-bit TIFFs run ~290MB raw / ~176MB lossless-compressed")
    lines.append("  each; 41 of them would not fit. Per your choice, tiff_converted/ holds a")
    lines.append("  50%-linear-downsized, lossless-deflate-compressed copy of each image.")
    lines.append("  ALL measurements (blob detection, centroid, r_EE_50) were computed on")
    lines.append("  the FULL-RESOLUTION pixel data in memory before downsizing -- the kept")
    lines.append("  TIFF files are a smaller copy for reference/viewing, not what was")
    lines.append("  measured.")
    lines.append("- Real phone-camera point-source photos in this set show a compact bright")
    lines.append("  core plus a wide veiling-glare halo and thin near-peak diffraction")
    lines.append("  spikes that connect to the frame edge or a secondary ghost blob at a")
    lines.append("  naive low threshold. The blob-isolation threshold is auto-raised per")
    lines.append("  image until the core bounding box is compact; see analyze.py docstring.")
    lines.append("")

    lines.append("PER-APERTURE RESULT")
    lines.append("-" * 74)
    by_folder = {}
    for r in all_measurements_rows:
        by_folder.setdefault(r["folder"], []).append(r)
    for folder in APERTURE_FOLDERS_ORDER:
        rows = by_folder.get(folder, [])
        lines.append(f"\n{folder} (a_hole_um={A.APERTURE_FOLDERS[folder]:.0f}):")
        for note in folder_notes.get(folder, []):
            lines.append(f"  NOTE: {note}")
        devs = [(r["parsed_M"], r["pct_deviation"]) for r in rows if r["pct_deviation"] != ""]
        if not devs:
            lines.append("  No measured-vs-predicted comparison available for this folder"
                          " (see NOTE above).")
        else:
            good = [(m, d) for m, d in devs if abs(d) <= DEV_GOOD_THRESHOLD]
            poor = [(m, d) for m, d in devs if abs(d) > DEV_GOOD_THRESHOLD]
            if good:
                lines.append(f"  Matched theory well (|%dev|<={DEV_GOOD_THRESHOLD:.0f}%): "
                              + ", ".join(f"M={m:g} ({d:+.1f}%)" for m, d in sorted(good)))
            if poor:
                lines.append(f"  Diverged from theory (|%dev|>{DEV_GOOD_THRESHOLD:.0f}%): "
                              + ", ".join(f"M={m:g} ({d:+.1f}%)" for m, d in sorted(poor)))
        for r in rows:
            if r["notes"]:
                lines.append(f"    [{r['filename']}, M={r['parsed_M']}] {r['notes']}")

    lines.append("")
    lines.append("-" * 74)
    lines.append(f"\n{A.CONTROL_FOLDER} (control -- no aperture, NOT compared to blur_sweep.csv theory):")
    for note in folder_notes.get(A.CONTROL_FOLDER, []):
        lines.append(f"  NOTE: {note}")
    for r in control_rows:
        nr = r["normalized_ratio_measured"]
        lines.append(f"  M={r['parsed_M']}: r_EE_50_px={r['measured_r_EE_50_px']}, "
                      f"normalized_ratio={nr if nr != '' else 'n/a (no M=0 reference)'}"
                      + (f"  [{r['notes']}]" if r["notes"] else ""))

    lines.append("")
    lines.append("-" * 74)
    lines.append(f"\nEXCLUDED / UNRESOLVED FILES")
    lines.append(f"  Flagged for exposure (excluded from comparison): {len(flagged_rows)} file(s)"
                  + (" -- see flagged_exposure_issues.csv" if flagged_rows else ""))
    for r in flagged_rows:
        lines.append(f"    {r['folder']}/{r['filename']} (M={r['parsed_M']}): {r['reason']}")
    lines.append(f"  Unparseable / excluded filenames: {len(unparseable_rows)} file(s)"
                  + (" -- see unparseable_files.csv" if unparseable_rows else ""))
    for r in unparseable_rows:
        lines.append(f"    {r['folder']}/{r['filename']}: {r['reason']}")

    lines.append("")
    lines.append("-" * 74)
    lines.append("\nHONEST BOTTOM LINE")
    all_devs = [r["pct_deviation"] for r in all_measurements_rows if r["pct_deviation"] != ""]
    if all_devs:
        import statistics
        lines.append(f"  {len(all_devs)} measured/predicted ratio pairs available across all apertures.")
        lines.append(f"  Mean |%deviation| = {statistics.mean(abs(d) for d in all_devs):.1f}%, "
                      f"median = {statistics.median(abs(d) for d in all_devs):.1f}%, "
                      f"max = {max(abs(d) for d in all_devs):.1f}%.")
        n_poor = sum(1 for d in all_devs if abs(d) > DEV_GOOD_THRESHOLD)
        if n_poor:
            lines.append(f"  {n_poor}/{len(all_devs)} pairs diverge by more than "
                          f"{DEV_GOOD_THRESHOLD:.0f}% -- reported plainly above, not smoothed over.")
        else:
            lines.append(f"  All pairs are within {DEV_GOOD_THRESHOLD:.0f}% of theory.")
    else:
        lines.append("  No measured-vs-predicted pairs were available at all (see per-aperture"
                      " notes above) -- this run could not validate theory against measurement.")
    lines.append("  1200b has no exact match in blur_sweep.csv (nearest: 1000um, 1250um) --")
    lines.append("  not interpolated or guessed; theory comparison is skipped for that folder.")
    lines.append("  1000b's own M=0 file (010006.dng) does not match the folder's established")
    lines.append("  filename pattern -- logged as unparseable, not guessed; 1000b's normalized")
    lines.append("  ratios (both measured and predicted) are therefore unavailable.")

    path = os.path.join(A.REPORT_DIR, "comparison_summary.txt")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {path}")


APERTURE_FOLDERS_ORDER = ["400b", "600b", "700b", "1000b", "1200b"]

if __name__ == "__main__":
    main()
