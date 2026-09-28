"""
combine_masks_for_printing.py

Composites multiple existing, already-mm-scaled mask SVGs (from ./masks/)
onto ONE print sheet, side by side, via pure translation only -- never
rescales a source file's internal coordinates.

Why this exists instead of drag-and-drop in Inkscape/Illustrator:
GUI paste/import can silently rescale (wrong DPI assumption, accidental
corner-handle drag). These source files are built at exact physical mm
scale with an embedded 10mm calibration square specifically so you can
catch that failure -- don't reintroduce it while combining them.

Also fixes a real gap in the source files: their embedded label text does
NOT distinguish top vs. bottom_mirrored vs. polarity. Two masks for the
same M can look nearly identical once printed. This script burns an
explicit, large, unambiguous tag (from the filename) onto each tile, plus
corner cut-marks, so physically cut pieces stay identifiable.

Usage:
    python3 combine_masks_for_printing.py \\
        masks/M8.0_negative_top.svg \\
        masks/M8.0_negative_bottom_mirrored.svg \\
        --gap_mm 8 --out combined_sheet.svg

Then open combined_sheet.svg in a browser, print at 100% / "actual size" --
no "fit to page" -- same as any single mask file. Verify EVERY embedded
10mm calibration square with calipers after printing, not just one.
"""
import argparse
import os
import re
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def parse_length_mm(s):
    """'50mm' -> 50.0 ; '50' -> 50.0 (assume mm, these files are always mm)."""
    m = re.match(r"([0-9.]+)", s.strip())
    if not m:
        raise ValueError(f"cannot parse length from {s!r}")
    return float(m.group(1))


def load_tile(path):
    tree = ET.parse(path)
    root = tree.getroot()
    w_mm = parse_length_mm(root.get("width"))
    h_mm = parse_length_mm(root.get("height"))
    vb = [float(x) for x in root.get("viewBox").split()]
    vb_x, vb_y, vb_w, vb_h = vb
    # children of the root <svg>, in document order -- copied as-is
    children = list(root)
    return {
        "path": path,
        "w_mm": w_mm, "h_mm": h_mm,
        "vb_x": vb_x, "vb_y": vb_y,
        "children": children,
    }


def tile_tag_from_filename(path):
    """Turn 'M8.0_negative_bottom_mirrored.svg' into a short, loud tag."""
    stem = os.path.splitext(os.path.basename(path))[0]
    parts = stem.split("_", 1)
    m_label = parts[0]
    rest = parts[1].replace("_", " ").upper() if len(parts) > 1 else ""
    return f"{m_label}  {rest}"


def build_combined(tile_paths, gap_mm, out_path):
    tiles = [load_tile(p) for p in tile_paths]

    total_w = sum(t["w_mm"] for t in tiles) + gap_mm * (len(tiles) - 1)
    total_h = max(t["h_mm"] for t in tiles)

    svg = ET.Element(f"{{{SVG_NS}}}svg", {
        "width": f"{total_w}mm",
        "height": f"{total_h}mm",
        "viewBox": f"0 0 {total_w} {total_h}",
    })

    x_cursor = 0.0
    for t in tiles:
        # translate so this tile's own viewBox origin lands at (x_cursor, 0)
        dx = x_cursor - t["vb_x"]
        dy = 0.0 - t["vb_y"]
        g = ET.SubElement(svg, f"{{{SVG_NS}}}g", {
            "transform": f"translate({dx:.5f},{dy:.5f})"
        })
        for child in t["children"]:
            g.append(child)

        # loud, unambiguous tag burned into this tile -- survives cutting
        tag = tile_tag_from_filename(t["path"])
        tag_x = x_cursor + t["w_mm"] / 2.0
        ET.SubElement(svg, f"{{{SVG_NS}}}rect", {
            "x": f"{x_cursor + 1.0:.3f}", "y": f"{total_h - 9.0:.3f}",
            "width": f"{t['w_mm'] - 2.0:.3f}", "height": "7.0",
            "fill": "white", "stroke": "black", "stroke-width": "0.3",
        })
        ET.SubElement(svg, f"{{{SVG_NS}}}text", {
            "x": f"{tag_x:.3f}", "y": f"{total_h - 3.5:.3f}",
            "font-size": "4.5", "font-weight": "bold",
            "text-anchor": "middle", "fill": "black",
        }).text = tag

        # corner cut-marks (small crosses just outside this tile's own edges)
        for cx, cy in [(x_cursor, 0), (x_cursor + t["w_mm"], 0),
                       (x_cursor, total_h), (x_cursor + t["w_mm"], total_h)]:
            ET.SubElement(svg, f"{{{SVG_NS}}}line", {
                "x1": f"{cx-2:.2f}", "y1": f"{cy:.2f}",
                "x2": f"{cx+2:.2f}", "y2": f"{cy:.2f}",
                "stroke": "black", "stroke-width": "0.2",
            })
            ET.SubElement(svg, f"{{{SVG_NS}}}line", {
                "x1": f"{cx:.2f}", "y1": f"{cy-2:.2f}",
                "x2": f"{cx:.2f}", "y2": f"{cy+2:.2f}",
                "stroke": "black", "stroke-width": "0.2",
            })

        x_cursor += t["w_mm"] + gap_mm

    # cut lines between tiles (dashed, so you cut on a straight, marked line)
    x_cursor = 0.0
    for i, t in enumerate(tiles[:-1]):
        cut_x = x_cursor + t["w_mm"] + gap_mm / 2.0
        ET.SubElement(svg, f"{{{SVG_NS}}}line", {
            "x1": f"{cut_x:.3f}", "y1": "0", "x2": f"{cut_x:.3f}", "y2": f"{total_h:.3f}",
            "stroke": "gray", "stroke-width": "0.15", "stroke-dasharray": "1.5,1.5",
        })
        x_cursor += t["w_mm"] + gap_mm

    ET.ElementTree(svg).write(out_path, xml_declaration=True, encoding="UTF-8")
    print(f"wrote {out_path}  ({len(tiles)} tiles, sheet {total_w:.1f}mm x {total_h:.1f}mm)")
    if total_w > 200 or total_h > 280:
        print(f"WARNING: combined sheet {total_w:.1f}x{total_h:.1f}mm may not fit "
              f"A4 (210x297) or Letter (216x279) printable area with margins -- "
              f"reduce tile count/gap or split across two prints.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tiles", nargs="+", help="paths to source mask SVGs, in left-to-right order")
    ap.add_argument("--gap_mm", type=float, default=8.0,
                    help="spacing between tiles, must be enough for scissors/blade + margin")
    ap.add_argument("--out", default="combined_sheet.svg")
    args = ap.parse_args()
    build_combined(args.tiles, args.gap_mm, args.out)
