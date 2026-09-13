"""
Array_Design/array_geometry_lab/fabrication_package/build_fabrication_spec.py

Renders the fabrication specification PDF for etching this project's
gaze-weighted per-M winner designs into a 0.05mm brass shim via UV
photoresist + a printed transparency photomask. Reads generate_masks.py's
own outputs (fabrication_summary.csv, hole_coordinates/*.csv) read-only.

Run: python3 build_fabrication_spec.py   (run generate_masks.py first)
"""
import os
import csv
import textwrap

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
SUMMARY_CSV = os.path.join(HERE, "fabrication_summary.csv")
COORD_DIR = os.path.join(HERE, "hole_coordinates")
OUT_PDF = os.path.join(HERE, "Fabrication_Specification.pdf")

SHIM_THICKNESS_UM = 50.0
UNDERCUT_LOW_UM, UNDERCUT_NOMINAL_UM, UNDERCUT_HIGH_UM = 25.0, 50.0, 75.0
CAL_SQUARE_SIDE_MM = 10.0

COLOR_ACCENT = "#6B4C9A"
INK = "#222222"
MUTED = "#666666"
PAGE_SIZE = (8.5, 11)


def load_summary():
    with open(SUMMARY_CSV) as f:
        return list(csv.DictReader(f))


def load_coords(m_label):
    path = os.path.join(COORD_DIR, f"hole_coordinates_M{m_label}.csv")
    xs, ys = [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            xs.append(float(row["x_mm"]))
            ys.append(float(row["y_mm"]))
    return np.array(xs), np.array(ys)


def render_text_page(pdf, title, subtitle, blocks):
    fig = plt.figure(figsize=PAGE_SIZE)
    ax = fig.add_axes([0.085, 0.045, 0.83, 0.90])
    ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    y = 1.0
    ax.plot([0, 1], [y, y], color=COLOR_ACCENT, linewidth=2.4, transform=ax.transAxes, clip_on=False)
    y -= 0.008
    ax.text(0, y, title, fontsize=16, fontweight="bold", va="top", color=INK, transform=ax.transAxes)
    y -= 0.045
    if subtitle:
        ax.text(0, y, subtitle, fontsize=10, va="top", color=MUTED, style="italic", transform=ax.transAxes)
        y -= 0.035
    y -= 0.012

    line_h = 0.0205
    for kind, payload in blocks:
        if kind == "space":
            y -= payload
            continue
        if kind == "para":
            for ln in (textwrap.wrap(payload, width=104) or [""]):
                ax.text(0, y, ln, fontsize=9.4, va="top", color=INK, transform=ax.transAxes)
                y -= line_h
            y -= 0.008
        elif kind == "bullets":
            for item in payload:
                wrapped = textwrap.wrap(item, width=99) or [""]
                for j, ln in enumerate(wrapped):
                    prefix = "•  " if j == 0 else "   "
                    ax.text(0.012, y, prefix + ln, fontsize=9.2, va="top", color=INK, transform=ax.transAxes)
                    y -= line_h
            y -= 0.008
        elif kind == "heading2":
            y -= 0.006
            for j, ln in enumerate(textwrap.wrap(payload, width=86) or [""]):
                ax.text(0, y, ln, fontsize=11.5, fontweight="bold", va="top", color=COLOR_ACCENT,
                         transform=ax.transAxes)
                y -= line_h * 1.25
            y -= 0.006
        elif kind == "eq":
            ax.text(0.5, y, payload, fontsize=12.5, va="top", ha="center", color=COLOR_ACCENT,
                     transform=ax.transAxes)
            y -= line_h * 1.9
        elif kind == "code":
            code_title, code_text = payload
            n_lines = code_text.count("\n") + 1
            box_h = 0.020 * n_lines + 0.018
            if code_title:
                ax.text(0, y, code_title, fontsize=9.0, fontweight="bold", va="top", color=MUTED,
                         transform=ax.transAxes)
                y -= 0.023
            ax.add_patch(plt.Rectangle((0.0, y - box_h), 1.0, box_h, transform=ax.transAxes,
                                        facecolor="#f4f4f4", edgecolor="#cfcfcf", linewidth=0.8,
                                        clip_on=False))
            ax.text(0.012, y - 0.007, code_text, fontsize=7.4, va="top", family="monospace",
                     color="#1a1a1a", transform=ax.transAxes)
            y -= box_h + 0.013

    pdf.savefig(fig)
    plt.close(fig)


def render_title(pdf):
    fig = plt.figure(figsize=PAGE_SIZE)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(Rectangle((0, 0.78), 1, 0.015, facecolor=COLOR_ACCENT))
    ax.add_patch(Rectangle((0, 0.20), 1, 0.015, facecolor=COLOR_ACCENT))
    ax.text(0.5, 0.70, "Gaze-Weighted Array Designs:", fontsize=15, ha="center", color=MUTED)
    ax.text(0.5, 0.655, "Photochemical-Etching Fabrication Specification", fontsize=20,
            ha="center", fontweight="bold", color=INK)
    ax.text(0.5, 0.61, "0.05mm brass shim  •  UV photoresist  •  printed transparency photomask",
            fontsize=12, ha="center", color=INK)
    ax.text(0.5, 0.53, "One physical mask design per myopia power M, per this project's own",
            fontsize=10.5, ha="center", color=COLOR_ACCENT)
    ax.text(0.5, 0.505, "gaze-weighted winner-per-M ranking",
            fontsize=10.5, ha="center", color=COLOR_ACCENT, fontweight="bold")
    ax.text(0.5, 0.40,
            "Hole geometry generated by directly importing and executing this project's own\n"
            "validated lattice generators (square.py / hexagonal.py) -- not re-derived by hand.\n"
            "Undercut compensation, print/DPI settings, resist-polarity inversion rules, and\n"
            "double-side registration are derived below, with every assumption sourced or flagged.",
            fontsize=9.5, ha="center", va="top", color=INK, linespacing=1.9)
    ax.text(0.5, 0.06, "2026", fontsize=10, ha="center", color=MUTED)
    pdf.savefig(fig); plt.close(fig)


def section_executive_summary(pdf, rows):
    blocks = [
        ("heading2", "Source of the design geometry"),
        ("para", "Every hole position in this package comes from "
                  "array_data/evaluation_results/gaze_weighted_winner_per_M.csv -- this "
                  "project's own per-M winner under the gaze-weighted ranking rule (rank by "
                  "time_weighted_ghost_pct ascending, tie-break time_weighted_blind_pct "
                  "ascending; see GAZE_WEIGHTED_APPROACH.md). The (x,y) hole-center coordinates "
                  "themselves were computed by importing and running this project's own real "
                  "generator functions directly (array_calculation/generators/square.py and "
                  "hexagonal.py) -- not reimplemented or hand-derived -- so they are guaranteed "
                  "identical to the exact design the gaze-weighted evaluation actually scored."),
        ("heading2", "One design per M, all sharing the same 4mm pitch"),
        ("para", "A notable, checked-not-assumed observation: every row of the gaze-weighted "
                  "winner table uses pitch_um=4000.0 -- the winning family (square at M=0/global, "
                  "hexagonal at every other M) and the aperture diameter change with M, but the "
                  "lattice pitch does not. This means every mask in this package shares the same "
                  "underlying grid spacing; only the hole family/count/diameter differs."),
        ("bullets", [f"M={r['M']}: {r['family']} lattice, N={r['N_actual']} holes, "
                     f"aperture={float(r['target_etched_diameter_um']):.0f}µm, "
                     f"blank size {r['blank_side_mm']}mm x {r['blank_side_mm']}mm"
                     for r in rows]),
        ("heading2", "What this document does NOT claim"),
        ("bullets", [
            "The undercut-compensation numbers below (Section 2) are a standard photochemical "
            "machining (PCM) design-rule starting point, NOT an empirical calibration of this "
            "specific brass alloy/thickness/etchant/equipment -- this project has run no test "
            "etch. A test coupon is explicitly recommended before committing the real shim.",
            "This document assumes the reader is etching in-house or via a shop that accepts a "
            "printed-transparency photomask (a standard, low-cost PCM/PCB-style workflow), not "
            "a professional photoplotter/imagesetter file handoff -- if using a PCM vendor "
            "directly, hand them the hole_coordinates_M*.csv files and this document's Section 2 "
            "undercut numbers; they will generate their own tooling to their own process's known "
            "bite ratio, which will be more accurate than the generic figure used here.",
        ]),
    ]
    render_text_page(pdf, "1. Executive Summary and Design Source", "", blocks)


def section_undercut(pdf, rows):
    blocks = [
        ("para", "Wet (chemical) etching is isotropic -- it removes material sideways under the "
                  "resist edge at roughly the same rate it removes material through the "
                  "thickness. For a hole (an opening cut through the metal), this means the "
                  "FINAL etched hole is LARGER than the resist opening that defined it -- so the "
                  "resist/mask opening must be made SMALLER than the target hole diameter by the "
                  "expected undercut, or the etched holes will come out oversized."),
        ("heading2", "2.1  Recommended process: simultaneous double-sided etching"),
        ("para", "For a 0.05mm (50µm) shim, standard PCM practice is to laminate photoresist on "
                  "BOTH faces and expose/develop/etch from both sides simultaneously, so each "
                  "face only needs to etch through half the thickness (25µm) before the two "
                  "fronts meet in the middle. This roughly halves the undercut compared to "
                  "etching the full thickness from one side only, and is the standard reason PCM "
                  "shops etch thin sheet from both sides -- this document assumes that process, "
                  "and Section 5 covers the two-mask registration this requires."),
        ("heading2", "2.2  Undercut compensation -- a standard rule of thumb, not this project's own measurement"),
        ("eq", r"$\mathrm{mask\ aperture\ diameter} \;=\; \mathrm{target\ etched\ diameter} - \mathrm{undercut\ allowance}$"),
        ("para", f"A commonly cited PCM starting design rule for a controlled double-sided "
                  f"chemical etch of thin sheet metal is a TOTAL diameter undercut allowance in "
                  f"the range of 0.5x to 1.5x material thickness, with 1.0x thickness "
                  f"(={SHIM_THICKNESS_UM:.0f}µm here) the most commonly cited nominal starting "
                  f"point. This range (not a single confirmed number) is used below because this "
                  f"project has no etch-rate/undercut calibration specific to this exact brass "
                  f"alloy, thickness, etchant chemistry (e.g. ferric chloride), temperature, or "
                  f"agitation setup."),
        ("bullets", [
            f"LOW bracket (0.5x thickness = {UNDERCUT_LOW_UM:.0f}µm total): use if your process "
            f"is known to be well-controlled (fresh, correctly-dosed etchant; good spray "
            f"agitation) or if a prior test coupon on this exact setup measured less undercut.",
            f"NOMINAL (1.0x thickness = {UNDERCUT_NOMINAL_UM:.0f}µm total): the recommended "
            f"DEFAULT starting point absent any test-coupon data -- used to size the primary "
            f"masks in this package.",
            f"HIGH bracket (1.5x thickness = {UNDERCUT_HIGH_UM:.0f}µm total): use if etching by "
            f"immersion (not spray) or with an aged/depleted etchant, both of which typically "
            f"increase undercut.",
        ]),
        ("heading2", "2.3  Strongly recommended: etch a test coupon first"),
        ("para", "Before committing the real array shim, etch a small test strip with a row of "
                  "isolated circles at several nominal diameters (e.g. 300, 500, 800, 1200µm) "
                  "using the SAME resist, etchant, temperature, and agitation you intend to use "
                  "for the real part. Measure the actual etched diameters against the known mask "
                  "diameters under a loupe or microscope with a calibrated scale; the difference "
                  "gives your process's REAL undercut, which will be more accurate than any of "
                  "the three brackets above. hole_coordinates_M*.csv already includes all three "
                  "bracket columns so you can re-print with whichever one matches your measured "
                  "result."),
        ("heading2", "2.4  Minimum feature-size sanity check (passed for every M)"),
        ("para", "A standard PCM guideline is that a hole's diameter should be at least "
                  "comparable to (ideally 1.5-2x or more) the material thickness, or the two "
                  "etch fronts (from opposite faces) can meet at a sharp, hard-to-control point "
                  "rather than a clean cylindrical wall. Checked directly against every row in "
                  "this package's design table:"),
        ("bullets", [f"M={r['M']}: target diameter {float(r['target_etched_diameter_um']):.0f}µm "
                     f"= {float(r['target_etched_diameter_um'])/SHIM_THICKNESS_UM:.1f}x the "
                     f"{SHIM_THICKNESS_UM:.0f}µm shim thickness -- comfortably clear of the "
                     f"minimum-feature guideline" for r in rows]),
    ]
    render_text_page(pdf, "2. Wet-Etch Undercut Compensation",
                      "How much smaller than the target hole to draw the mask opening, and why", blocks)


def section_geometry_table(pdf, rows):
    fig = plt.figure(figsize=PAGE_SIZE)
    ax = fig.add_axes([0.06, 0.06, 0.9, 0.88]); ax.axis("off")
    ax.plot([0, 1], [1.0, 1.0], color=COLOR_ACCENT, linewidth=2.4, transform=ax.transAxes)
    ax.text(0, 0.975, "3. Per-M Design Geometry and Mask-Aperture Table", fontsize=16,
            fontweight="bold", va="top", transform=ax.transAxes)
    ax.text(0, 0.94, "Every column below is read directly from fabrication_summary.csv / "
                     "hole_coordinates_M*.csv -- not retyped.", fontsize=9.5, style="italic",
            color=MUTED, va="top", transform=ax.transAxes)

    col_labels = ["M", "family", "N", "pitch\n(µm)", "target\nhole (µm)", "mask aperture (µm)\nlow / nom / high",
                  "blank\n(mm)"]
    cell_text = []
    for r in rows:
        cell_text.append([
            r["M"], r["family"], r["N_actual"], f"{float(r['pitch_um']):.0f}",
            f"{float(r['target_etched_diameter_um']):.0f}",
            f"{float(r['mask_aperture_diameter_um_low']):.0f} / "
            f"{float(r['mask_aperture_diameter_um_nominal']):.0f} / "
            f"{float(r['mask_aperture_diameter_um_high']):.0f}",
            r["blank_side_mm"],
        ])
    tbl = ax.table(cellText=cell_text, colLabels=col_labels, loc="upper center",
                    cellLoc="center", colLoc="center", bbox=[0.0, 0.55, 0.96, 0.36],
                    colWidths=[0.08, 0.13, 0.06, 0.10, 0.13, 0.32, 0.10])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.3)

    note = ("Nominal = 1.0x thickness undercut allowance (recommended default). Blank = the "
            "square brass sheet size this package's SVG masks are drawn at (array bounding "
            "circle + 8mm margin on each side, rounded up to a clean 5mm size).")
    ax.text(0, 0.50, "\n".join(textwrap.wrap(note, width=100)), fontsize=8.8, va="top",
            color=MUTED, transform=ax.transAxes, linespacing=1.5)

    ax2 = fig.add_axes([0.08, 0.06, 0.38, 0.35])
    xs, ys = load_coords("6.0")
    ax2.scatter(xs, ys, s=10, color=COLOR_ACCENT)
    ax2.set_aspect("equal")
    ax2.set_title("M=6 layout preview (largest, N=100)", fontsize=8.5)
    ax2.tick_params(labelsize=7)

    ax3 = fig.add_axes([0.56, 0.06, 0.38, 0.35])
    xs, ys = load_coords("0.0")
    ax3.scatter(xs, ys, s=18, color=COLOR_ACCENT)
    ax3.set_aspect("equal")
    ax3.set_title("M=0 layout preview (square, N=20)", fontsize=8.5)
    ax3.tick_params(labelsize=7)

    pdf.savefig(fig); plt.close(fig)


def section_file_format(pdf):
    blocks = [
        ("heading2", "4.1  File type: vector SVG, print at true physical scale"),
        ("para", "This package's masks/ folder contains one SVG per (M, resist polarity, shim "
                  "side) combination. SVG is used because it is a VECTOR format -- the file "
                  "declares physical width/height in millimeters directly (width=\"60.0mm\" "
                  "height=\"60.0mm\"), so a correctly-configured print pipeline reproduces exact "
                  "hole diameters and positions at whatever the printer's native resolution is, "
                  "with no raster resampling/aliasing at the hole edges."),
        ("para", "Recommended handoff, in order of preference:"),
        ("bullets", [
            "Best: open the SVG in Inkscape (free) or Illustrator, verify the document size "
            "matches the intended blank size (e.g. 60.0mm x 60.0mm for M=6) EXACTLY, then export "
            "or print directly -- do not let the application \"fit to page\" or rescale on import.",
            "If your printer/RIP only accepts PDF: export the verified SVG to PDF from Inkscape/"
            "Illustrator at the SAME physical page size (not a fixed paper size like A4/Letter "
            "with content scaled to fit) -- set the PDF page size to the exact blank dimensions.",
            "If your only tool is a raster editor: rasterize the SVG at a fixed PHYSICAL size "
            "(exact mm) and the DPI given in Section 4.2 below, never at a fixed pixel count "
            "with the physical size left to \"whatever fits.\"",
        ]),
        ("heading2", "4.2  Resolution (DPI)"),
        ("para", "The smallest feature in this package is a 350µm-diameter mask aperture (M=8, "
                  "nominal compensation). A commonly used rule of thumb for reproducing a clean, "
                  "round photomask edge on a printed transparency is roughly 15-20 print dots "
                  "across the smallest feature's diameter."),
        ("bullets", [
            "1200 DPI (21.2µm/dot): ~16 dots across the 350µm feature -- workable minimum.",
            "2400 DPI (10.6µm/dot): ~33 dots across the 350µm feature -- comfortably smooth; "
            "RECOMMENDED if your printer supports it natively.",
            "Set the printer to its TRUE native/optical maximum resolution, not an interpolated "
            "\"enhanced\" mode -- many office laser printers advertise a high number but only "
            "address a lower true resolution; interpolated upscaling does not improve real edge "
            "sharpness and can introduce its own artifacts at small feature sizes.",
            "If edge quality at the printed DPI is not adequate on inspection (see Section 6), "
            "the next step up in quality is a professional imagesetter/photoplotter run at a "
            "print/prepress bureau -- the same SVG/PDF file works for that handoff unchanged.",
        ]),
        ("heading2", "4.3  Disable ALL print-time scaling -- the single most common way to ruin a 1:1 mask"),
        ("para", "In the print dialog (whichever OS/application), explicitly set scale to "
                  "\"100% / Actual Size / Custom Scale = 100%\" and DISABLE any \"Fit to Page,\" "
                  "\"Shrink to Printable Area,\" or \"Fit to Paper Size\" option. These options "
                  "are commonly ON by default and will silently rescale the artwork to fit "
                  "whatever paper size is loaded, destroying the 1:1 physical scale this entire "
                  "package depends on. See Section 6 for how to CATCH this after printing, before "
                  "it reaches the etch tank."),
    ]
    render_text_page(pdf, "4. File Format, Resolution, and Scale Settings", "", blocks)


def section_polarity(pdf):
    blocks = [
        ("heading2", "5.1  The rule, derived from first principles"),
        ("para", "Positive and negative photoresist respond to UV exposure in OPPOSITE ways, so "
                  "the mask artwork must be inverted between them to get the same physical result "
                  "(bare metal exactly at the hole locations, resist intact everywhere else):"),
        ("bullets", [
            "NEGATIVE resist (exposure HARDENS/cross-links the resist -- unexposed resist washes "
            "away in developer): to make a HOLE, that spot must be UNEXPOSED, so the mask must be "
            "OPAQUE there. To PROTECT metal, that spot must be EXPOSED, so the mask must be CLEAR "
            "there. Net artwork: a CLEAR field with OPAQUE (dark) dots at each hole location -- "
            "this is the direct, intuitive image of the hole pattern.",
            "POSITIVE resist (exposure DISSOLVES the resist -- exposed resist washes away in "
            "developer): to make a HOLE, that spot must be EXPOSED, so the mask must be CLEAR "
            "there. To PROTECT metal, that spot must be UNEXPOSED, so the mask must be OPAQUE "
            "there. Net artwork: an OPAQUE field with CLEAR (white/see-through) circles at each "
            "hole location -- the INVERSE of the negative-resist artwork.",
        ]),
        ("para", "Most dry-film photoresist laminates commonly used for PCM/PCB-style etching "
                  "(the process this document assumes) are NEGATIVE-acting -- if you don't "
                  "already know which resist you have, this is the more likely default, but "
                  "CONFIRM against your specific product's datasheet before printing; using the "
                  "wrong polarity produces the exact inverse of the intended array (metal where "
                  "holes should be, and vice versa) and is not something you can correct after "
                  "etching."),
        ("heading2", "5.2  Files provided for both polarities"),
        ("para", "This package pre-generates BOTH polarity conventions for every M so you do not "
                  "need to invert anything by hand -- pick the folder matching your actual resist:"),
        ("bullets", [
            "masks/M{M}_negative_top.svg, masks/M{M}_negative_bottom_mirrored.svg -- for "
            "negative-acting resist (clear field, opaque hole dots).",
            "masks/M{M}_positive_top.svg, masks/M{M}_positive_bottom_mirrored.svg -- for "
            "positive-acting resist (opaque field, clear hole circles).",
        ]),
        ("para", "If you ever need to invert a file yourself instead (e.g. a design change after "
                  "this package was generated): a full black/white color inversion of the mask "
                  "image is the correct and complete operation -- there is no partial/approximate "
                  "inversion; every pixel's polarity must flip."),
    ]
    render_text_page(pdf, "5. Photoresist Polarity and Mask Inversion", "", blocks)


def section_registration(pdf):
    blocks = [
        ("heading2", "6.1  Why the two sides need mirrored (not identical) artwork"),
        ("para", "Section 2.1 assumes simultaneous double-sided etching: one photomask film "
                  "contacts the TOP face of the shim, a second contacts the BOTTOM face, and "
                  "both must be exposed so their hole openings line up through the sheet. Because "
                  "the two films are viewed from OPPOSITE sides of the same physical sheet, a "
                  "hole pattern that is not perfectly left-right symmetric will appear mirrored "
                  "between the two views -- printing the identical file on both sides would "
                  "misalign every hole that isn't on the pattern's own mirror axis."),
        ("para", "This was checked directly against the actual generated coordinates, not "
                  "assumed: the gaze-weighted winner designs are truncated to their requested "
                  "hole count by a closest-N-to-origin radial sort (see square.py/hexagonal.py), "
                  "which does not generally preserve exact left-right mirror symmetry once the "
                  "point set is recentered on its own centroid. The bottom-side files in this "
                  "package (masks/M{M}_*_bottom_mirrored.svg) are therefore genuinely computed "
                  "mirror images (x -> -x) of the top-side files, not the same file reused."),
        ("heading2", "6.2  Emulsion/print-side orientation"),
        ("para", "The printed side of the transparency (the side carrying the actual ink/toner) "
                  "should make DIRECT CONTACT with the photoresist surface during exposure, on "
                  "BOTH the top and bottom film. This minimizes the gap between the opaque "
                  "artwork and the resist, which reduces UV light scatter/spread under the mask "
                  "edges (a second, separate source of feature-size error on top of the wet-etch "
                  "undercut in Section 2) -- print with \"mirror image\"/\"flip horizontal\" OFF "
                  "for the film that will be placed print-side-down against the resist as drawn, "
                  "and this package's own _bottom_mirrored.svg file already encodes the correct "
                  "opposite-side view, so print it AS-IS (do not apply an additional flip in your "
                  "printer driver -- that would un-mirror it back to the wrong orientation)."),
        ("heading2", "6.3  Physical alignment between the two films"),
        ("bullets", [
            "Both films in this package carry the same 4 corner fiducial dots (0.75mm radius) at "
            "identical positions relative to the array -- align the two printed transparencies "
            "against each other (e.g. on a light table) using these fiducials before taping them "
            "to opposite faces of the shim blank, ensuring the shim itself is positioned "
            "identically relative to both.",
            "A simple mechanical jig (two registration pins through pre-punched holes at two of "
            "the four fiducial positions, matched by corresponding holes punched through both "
            "transparencies and the shim blank) is the standard, low-cost way to guarantee this "
            "alignment holds during the exposure step, when the two-sided sandwich is clamped "
            "together.",
        ]),
    ]
    render_text_page(pdf, "6. Double-Side Registration", "", blocks)


def section_verification(pdf):
    blocks = [
        ("heading2", "7.1  The 1:1 physical-scale self-check (do this before EVERY exposure)"),
        ("para", "Every mask in this package includes a printed 10.000mm x 10.000mm reference "
                  "square (labeled \"10.0 mm ref\") near one corner, outside the working array. "
                  "After printing (and before loading the transparency into any exposure rig), "
                  "measure this square directly with calipers or a certified steel ruler:"),
        ("bullets", [
            "If it measures 10.00mm (within your measuring tool's own precision, typically "
            "±0.05mm for calipers): the print is at true 1:1 scale -- proceed.",
            "If it measures anything else (e.g. 9.7mm or 10.3mm): STOP. The print pipeline "
            "applied an unwanted scale factor somewhere (see Section 4.3) -- every hole position "
            "and diameter on that print is wrong by the same factor, and it is not safe to use "
            "\"as is\" or to try to compensate for afterward. Find and fix the scaling setting, "
            "then reprint and re-measure.",
        ]),
        ("heading2", "7.2  Visual QA before etching"),
        ("bullets", [
            "Confirm hole COUNT visually against the design table in Section 3 (e.g. M=6 should "
            "show 100 holes) -- an interrupted print or a corrupted export can silently drop "
            "rows.",
            "Confirm hole polarity matches your resist (Section 5) -- for negative resist you "
            "should see dark dots on a clear/see-through background; for positive resist, light/"
            "clear circles on an opaque dark background.",
            "Hold the top and bottom transparencies together up to a light source, aligned on "
            "their fiducials -- every hole should appear as a single sharp circle, not a doubled "
            "or offset pair, confirming the mirroring in Section 6 produced correct registration.",
        ]),
        ("heading2", "7.3  Full process order (summary)"),
        ("bullets", [
            "1. Print both top and bottom transparency films (Section 4); verify 1:1 scale "
            "(Section 7.1) and visual QA (Section 7.2) on both before proceeding.",
            "2. Laminate/apply photoresist to both faces of the 0.05mm brass blank.",
            "3. Register and clamp both films to opposite faces of the shim (Section 6.3).",
            "4. Expose both sides to UV through their respective films.",
            "5. Develop (removes the resist that did not harden -- see Section 5.1 for which "
            "areas that is, per your resist type).",
            "6. Etch (chemical bath, e.g. ferric chloride for brass) from both sides "
            "simultaneously until break-through; inspect periodically rather than fixing a blind "
            "etch time, since actual etch rate depends on your specific bath's condition.",
            "7. Strip remaining resist, rinse, inspect hole diameters/positions against Section 3 "
            "before considering the shim finished.",
        ]),
    ]
    render_text_page(pdf, "7. Print Verification and Process Summary", "", blocks)


def section_manifest(pdf, rows):
    blocks = [
        ("heading2", "Files in this package (Array_Design/array_geometry_lab/fabrication_package/)"),
        ("bullets", [
            "generate_masks.py -- generates every file below from the project's own gaze-weighted "
            "winner table and real generator code; re-run after changing any UNDERCUT_* constant "
            "or after a test-coupon result (Section 2.3) changes which bracket you want to use.",
            "build_fabrication_spec.py -- generates this PDF.",
            "fabrication_summary.csv -- the master per-M table (Section 3).",
            "hole_coordinates/hole_coordinates_M{M}.csv -- one row per physical hole "
            "(x_mm, y_mm) plus target and all three bracket mask-aperture diameters, per M.",
            "masks/M{M}_{polarity}_{side}.svg -- print-ready, true-physical-scale vector "
            "artwork, one per (M, negative/positive, top/bottom_mirrored) combination "
            "(36 files: 9 designs x 2 polarities x 2 sides).",
        ]),
        ("heading2", "Upstream source files this package reads (read-only, never modified)"),
        ("bullets", [
            "array_data/evaluation_results/gaze_weighted_winner_per_M.csv -- the design source "
            "(Section 1).",
            "array_calculation/generators/square.py, hexagonal.py, base_generator.py -- the real "
            "lattice-generation code, imported directly.",
            "GAZE_WEIGHTED_APPROACH.md -- the gaze-weighted ranking methodology this table's "
            "winners were selected by.",
        ]),
        ("space", 0.02),
        ("para", "Design geometry in this package is exact (directly computed from this "
                  "project's own generator code). Undercut compensation, DPI, and process "
                  "guidance are standard PCM engineering practice applied explicitly and "
                  "traceably to this design -- NOT this project's own empirical measurement. "
                  "Confirm the undercut bracket with a test coupon (Section 2.3) before "
                  "committing the real shim."),
    ]
    render_text_page(pdf, "8. File Manifest", "", blocks)


def main():
    rows = load_summary()
    with PdfPages(OUT_PDF) as pdf:
        render_title(pdf)
        section_executive_summary(pdf, rows)
        section_undercut(pdf, rows)
        section_geometry_table(pdf, rows)
        section_file_format(pdf)
        section_polarity(pdf)
        section_registration(pdf)
        section_verification(pdf)
        section_manifest(pdf, rows)
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
