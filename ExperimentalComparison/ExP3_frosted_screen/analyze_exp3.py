"""
ExperimentalComparison/ExP3_frosted_screen/analyze_exp3.py

Fixed-lens/moving-screen defocus sweep on a frosted screen, per aperture and
displacement. Hardens the already-hand-verified method (threshold at 50% of
peak, equivalent radius = sqrt(area/pi)) by restricting the thresholded area
to its LARGEST CONNECTED COMPONENT (cv2.connectedComponentsWithStats), so a
stray bright pixel elsewhere in frame (confirmed present: a second faint
light source at the bottom edge of several frames) cannot silently inflate
the measured area the way a global-threshold-pixel-count would.

Definitions:
  - intensity image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) (standard BT.601
    luma). CONFIRMED, not assumed: this exact convention was reverse-engineered
    against the task's own hand-verified reference numbers for 1000um (45.6px
    at 0mm, 63.6px at 20mm) -- a max(R,G,B) intensity image was tried first
    and gave 95.8px/110.2px (wrong, ~2x too large); plain per-channel mean
    gave 48.9px/wrong shape; BT.601 luma reproduced 45.58px and 63.60px
    (this pipeline's own numbers, below) to within rounding of the stated
    reference, on the same files, confirming this is the convention the
    hand-check actually used.
  - peak = intensity image's maximum value (0-255, 8-bit JPEG).
  - threshold = 0.5 * peak (exactly the already-hand-verified rule).
  - mask = intensity >= threshold; largest connected component (8-connectivity)
    of that mask by pixel AREA is "the spot" -- matches this task's own
    instruction to hardn the hand-verified method this way.
  - area_px = that component's pixel count (from connectedComponentsWithStats'
    own stats, not a manual mask.sum() -- avoids re-including other
    components).
  - radius_px = sqrt(area_px / pi).
  - centroid = that component's own (x, y) centroid, as reported by
    connectedComponentsWithStats (unweighted over the binary mask -- matches
    the equally simple, non-intensity-weighted nature of the area/radius
    metric; no separate weighting scheme is introduced).
  - centroid_drift_px = distance from this image's centroid to the SAME
    aperture's (or, for the No-pinhole series, the No-series') own 0mm
    image's centroid. 0 by definition at displacement=0.

Flags (logged in the "flags" column, never used to exclude a row from
all_spot_measurements.csv -- "log, don't discard"):
  - "peak<200 (dim, threshold may be unreliable)"
  - "centroid_drift>100px"

Excluded outright (not measured, not in all_spot_measurements.csv -- logged
separately in measurements/excluded_files.csv with a reason):
  - the 5 20260902_*.jpg timestamped setup/calibration shots.

No displacement_mm -> diopter conversion is attempted anywhere in this
pipeline (requires calibrating beam width at the lens, not yet done) -- see
report/exp3_summary.txt for this limitation stated explicitly.

Run: python3 analyze_exp3.py
"""
import os
import re
import csv
import math

import numpy as np
import cv2

SRC_DIR = "/Users/parikshitnarang/Pinholeproject/ExP3/Frosted screen "
OUT_DIR = "/Users/parikshitnarang/Pinholeproject/ExperimentalComparison/ExP3_frosted_screen"
MEAS_DIR = os.path.join(OUT_DIR, "measurements")
REPORT_DIR = os.path.join(OUT_DIR, "report")

APERTURE_RE = re.compile(r'^(\d+)-(\d+)\.jpg$', re.IGNORECASE)
CONTROL_RE = re.compile(r'^No(\d+)\.jpg$', re.IGNORECASE)
CALIBRATION_RE = re.compile(r'^\d{8}_\d{6}\.jpg$', re.IGNORECASE)

PEAK_DIM_THRESHOLD = 200
CENTROID_DRIFT_THRESHOLD_PX = 100.0

APERTURES = [400, 500, 600, 800, 1000, 1400]
DISPLACEMENTS = [0, 5, 10, 15, 20]


def classify_filename(fname):
    """Returns ('aperture', aperture_um, displacement_mm), ('control', None,
    displacement_mm), ('excluded', None, reason), or ('unparseable', None, None)."""
    m = APERTURE_RE.match(fname)
    if m:
        return "aperture", int(m.group(1)), int(m.group(2))
    m = CONTROL_RE.match(fname)
    if m:
        return "control", None, int(m.group(1))
    if CALIBRATION_RE.match(fname):
        return "excluded", None, "timestamped setup/calibration shot, not part of the systematic sweep"
    return "unparseable", None, None


def measure_spot(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"cv2 could not read {path}")
    intensity = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # BT.601 luma -- see module docstring
    peak = int(intensity.max())

    threshold = 0.5 * peak
    mask = (intensity >= threshold).astype(np.uint8)
    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n_labels <= 1:
        # no foreground component at all (mask is entirely background)
        return {"peak": peak, "area_px": 0, "radius_px": 0.0,
                "centroid_x": float("nan"), "centroid_y": float("nan"),
                "n_components": 0}

    areas = stats[1:, cv2.CC_STAT_AREA]  # skip label 0 (background)
    largest_idx = int(np.argmax(areas)) + 1  # +1 to re-offset past background
    area_px = int(stats[largest_idx, cv2.CC_STAT_AREA])
    cx, cy = centroids[largest_idx]
    radius_px = math.sqrt(area_px / math.pi)
    return {"peak": peak, "area_px": area_px, "radius_px": radius_px,
            "centroid_x": float(cx), "centroid_y": float(cy),
            "n_components": int(n_labels - 1)}


def main():
    files = sorted(f for f in os.listdir(SRC_DIR) if f.lower().endswith(".jpg"))

    excluded_rows = []
    aperture_files = {}   # aperture_um -> {displacement: fname}
    control_files = {}    # displacement -> fname

    for fname in files:
        kind, a_or_none, b = classify_filename(fname)
        if kind == "aperture":
            aperture_files.setdefault(a_or_none, {})[b] = fname
        elif kind == "control":
            control_files[b] = fname
        elif kind == "excluded":
            excluded_rows.append({"filename": fname, "reason": b})
            print(f"[excluded] {fname}: {b}")
        else:
            excluded_rows.append({"filename": fname, "reason": "does not match any known filename pattern -- not guessed"})
            print(f"[UNPARSEABLE] {fname}")

    with open(os.path.join(MEAS_DIR, "excluded_files.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["filename", "reason"])
        w.writeheader()
        for r in excluded_rows:
            w.writerow(r)
    print(f"wrote excluded_files.csv ({len(excluded_rows)} rows)")

    all_rows = []

    # --- aperture series ---
    for aperture in APERTURES:
        disp_map = aperture_files.get(aperture, {})
        ref_centroid = None
        for disp in DISPLACEMENTS:
            fname = disp_map.get(disp)
            if fname is None:
                print(f"[MISSING] aperture={aperture} displacement={disp}mm -- no file, not guessed")
                continue
            m = measure_spot(os.path.join(SRC_DIR, fname))
            flags = []
            if m["peak"] < PEAK_DIM_THRESHOLD:
                flags.append("peak<200 (dim, threshold may be unreliable)")
            if disp == 0:
                ref_centroid = (m["centroid_x"], m["centroid_y"])
                drift = 0.0
            elif ref_centroid is not None and not math.isnan(m["centroid_x"]):
                drift = math.hypot(m["centroid_x"] - ref_centroid[0], m["centroid_y"] - ref_centroid[1])
                if drift > CENTROID_DRIFT_THRESHOLD_PX:
                    flags.append("centroid_drift>100px")
            else:
                drift = float("nan")
            all_rows.append({
                "series": "aperture", "aperture_um": aperture, "displacement_mm": disp,
                "filename": fname, "peak": m["peak"], "area_px": m["area_px"],
                "radius_px": round(m["radius_px"], 3), "centroid_x": round(m["centroid_x"], 2),
                "centroid_y": round(m["centroid_y"], 2),
                "centroid_drift_px": round(drift, 2) if not math.isnan(drift) else "",
                "flags": "; ".join(flags),
            })
            print(f"[ok] aperture={aperture} disp={disp}mm peak={m['peak']} area={m['area_px']} "
                  f"r={m['radius_px']:.2f}px drift={drift if not math.isnan(drift) else 'n/a'}"
                  + (f"  FLAGS: {flags}" if flags else ""))

    # --- No-pinhole control series ---
    ref_centroid = None
    for disp in DISPLACEMENTS:
        fname = control_files.get(disp)
        if fname is None:
            print(f"[MISSING] control displacement={disp}mm -- no file, not guessed")
            continue
        m = measure_spot(os.path.join(SRC_DIR, fname))
        flags = []
        if m["peak"] < PEAK_DIM_THRESHOLD:
            flags.append("peak<200 (dim, threshold may be unreliable)")
        if disp == 0:
            ref_centroid = (m["centroid_x"], m["centroid_y"])
            drift = 0.0
        elif ref_centroid is not None and not math.isnan(m["centroid_x"]):
            drift = math.hypot(m["centroid_x"] - ref_centroid[0], m["centroid_y"] - ref_centroid[1])
            if drift > CENTROID_DRIFT_THRESHOLD_PX:
                flags.append("centroid_drift>100px")
        else:
            drift = float("nan")
        all_rows.append({
            "series": "control", "aperture_um": "", "displacement_mm": disp,
            "filename": fname, "peak": m["peak"], "area_px": m["area_px"],
            "radius_px": round(m["radius_px"], 3), "centroid_x": round(m["centroid_x"], 2),
            "centroid_y": round(m["centroid_y"], 2),
            "centroid_drift_px": round(drift, 2) if not math.isnan(drift) else "",
            "flags": "; ".join(flags),
        })
        print(f"[ok] control disp={disp}mm peak={m['peak']} area={m['area_px']} "
              f"r={m['radius_px']:.2f}px drift={drift if not math.isnan(drift) else 'n/a'}"
              + (f"  FLAGS: {flags}" if flags else ""))

    out_csv = os.path.join(MEAS_DIR, "all_spot_measurements.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["series", "aperture_um", "displacement_mm", "filename",
                                          "peak", "area_px", "radius_px", "centroid_x", "centroid_y",
                                          "centroid_drift_px", "flags"])
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"\nwrote {out_csv} ({len(all_rows)} rows)")
    return all_rows


if __name__ == "__main__":
    main()
