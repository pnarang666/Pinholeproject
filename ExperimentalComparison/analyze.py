"""
ExperimentalComparison/analyze.py

Pipeline: DNG -> TIFF (sips) -> exposure check -> brightest-blob r_EE_50 (px)
-> M=0-normalized ratio -> compare to blur_sweep.csv theory ratio.

Definitions (documented here since they are judgment calls not fully pinned
down by the task spec):

  - sips writes a REAL 16-bit-per-channel TIFF (BitsPerSample=16, confirmed via
    tag inspection) -- this is the actual dynamic range the task's own
    CRITICAL note wanted preserved. The installed Pillow (9.5.0, old Python
    3.7 env) silently downcasts this to 8-bit on `np.array(Image.open(...))`,
    which would have quietly thrown away exactly the dynamic range this
    pipeline exists to preserve -- caught by direct inspection before any
    measurement was finalized, not assumed. All reading/writing here uses
    OpenCV (`cv2.imread(..., cv2.IMREAD_UNCHANGED)`), verified to round-trip
    the true uint16 values losslessly.
  - Grayscale intensity = unweighted mean of R,G,B, computed on the native
    uint16 data (0..65535), not 8-bit.
  - Exposure-flag thresholds (near-0 / near-255 in the task's own wording,
    written assuming an 8-bit output) are applied as the equivalent 5%/95%
    of the true native range (0..65535), since these files are genuinely
    16-bit -- literal 0..255 thresholds against 16-bit data would almost
    never fire and silently defeat the flag's purpose. Documented here and in
    comparison_summary.txt, not silently substituted.
  - The full-resolution image is used for EVERY measurement (blob search,
    centroid, r_EE_50, exposure stats). Only the on-disk TIFF kept in
    tiff_converted/ is downsized (50% linear, i.e. 1/4 the pixels) and
    deflate-compressed, per explicit instruction, to fit the machine's real
    available disk space (~1-3GB free system-wide on this run, unrelated to
    this task) -- this affects nothing about the reported numbers.
  - Background level = median of the full-frame grayscale image (the blob
    covers a small minority of the frame in every shot inspected).
  - flux = max(gray - background, 0)  (background-subtracted, clipped >=0)
  - "Brightest connected blob" = the connected component (8-connectivity,
    threshold = 5% of peak flux) with the HIGHEST TOTAL FLUX (sum, not peak
    pixel value). Chosen over "highest peak" because a lens-flare streak or a
    small hot pixel can have peak==255 without being the actual point-source
    image; total flux is robust to that and matches "the blob" as the object
    of interest for a photometric radius. Confirmed by eye on 600b/M0: the
    correct central blob is both visually the biggest and brightest of the
    (blob + secondary ghost blob + flare streak) present in the frame.
  - ROI for centroid/EE50 = blob's bounding box padded by 2x its own size on
    each side (capped so the padded box never exceeds the frame), with any
    pixels belonging to a DIFFERENT connected component zeroed out first, so
    a nearby secondary blob/ghost does not contaminate this blob's energy or
    centroid.
  - centroid = flux-weighted centroid over that (cleaned) ROI.
  - total_intensity = sum(flux) over that ROI.
  - r_EE_50_px = radius (linear interpolation between the two bracketing
    pixel distances) at which cumulative flux, pixels sorted by distance from
    centroid ascending, first reaches 50% of total_intensity.

Known caveat (reported, not silently ignored): several frames show the
blob CORE pixel-saturated (gray==255) even though the frame's per-channel
MEAN is nowhere near the 5%-of-0/255 flag threshold. Saturation clips the
true peak and can bias r_EE_50 slightly low. This is out of scope for the
task's explicit flagging rule (which is a whole-frame mean criterion) but is
called out plainly in comparison_summary.txt.
"""
import os
import re
import csv
import subprocess
import sys

import numpy as np
import cv2
from scipy import ndimage

ROOT = "/Users/parikshitnarang/Pinholeproject"
EXP2 = os.path.join(ROOT, "ExP2")
OUT = os.path.join(ROOT, "ExperimentalComparison")
TIFF_DIR = os.path.join(OUT, "tiff_converted")
MEAS_DIR = os.path.join(OUT, "measurements")
REPORT_DIR = os.path.join(OUT, "report")
BLUR_SWEEP_CSV = os.path.join(ROOT, "new_sweeps", "blur_sweep.csv")

APERTURE_FOLDERS = {"400b": 400.0, "600b": 600.0, "700b": 700.0,
                     "1000b": 1000.0, "1200b": 1200.0}
CONTROL_FOLDER = "Nopinholeb"
ALL_FOLDERS = list(APERTURE_FOLDERS.keys()) + [CONTROL_FOLDER]

VALID_M = {0, 1, 2, 3, 4, 6, 8}  # 5, 7 legitimately absent by design

NATIVE_RANGE = 65535.0  # true sensor bit depth sips preserves (16-bit/channel)
FLAG_LOW = NATIVE_RANGE * 0.05
FLAG_HIGH = NATIVE_RANGE * 0.95

DOWNSIZE_LINEAR_FACTOR = 0.5  # kept tiff_converted/ deliverable only -- all
                               # measurements use the full-resolution array


# ---------- filename parsing (per-folder rules, no guessing) ----------

_PATTERNS = {
    "600b": re.compile(r'^M(\d)600b\.dng$', re.IGNORECASE),
    "700b": re.compile(r'^(\d)700b(\d)?\.dng$', re.IGNORECASE),
    "400b": re.compile(r'^(\d)400\.dng$', re.IGNORECASE),
    "1000b": re.compile(r'^(\d)1000\.dng$', re.IGNORECASE),
    "1200b": re.compile(r'^(\d)1200\.dng$', re.IGNORECASE),
    "Nopinholeb": re.compile(r'^(\d)\.dng$', re.IGNORECASE),
}


def parse_filename(folder, fname):
    """Returns (M:int|None, note:str|None, is_retake:bool).
    M is None when the file must be excluded/logged as unparseable/anomalous.
    """
    pat = _PATTERNS[folder]
    m = pat.match(fname)
    if not m:
        if folder == "400b" and fname.lower() == "20260826_225126.dng":
            return None, "anomalous filename (timestamp-style), not M-mapped, excluded per task spec", False
        return None, "does not match this folder's established filename pattern -- not guessed", False
    M = int(m.group(1))
    is_retake = False
    if folder == "700b" and m.group(2) is not None:
        is_retake = True
    if M not in VALID_M:
        return None, f"parsed M={M} is not in the valid set {sorted(VALID_M)}", False
    return M, ("possible retake (extra trailing digit in filename)" if is_retake else None), is_retake


# ---------- conversion + exposure ----------

def convert_to_tiff(src_path, dst_path):
    """sips writes a full-resolution, real-16-bit TIFF to dst_path (a
    scratch/temp path -- NOT the final tiff_converted/ deliverable, which is
    a downsized+compressed copy written separately by save_downsized_copy())."""
    if os.path.exists(dst_path):
        return True, ""
    proc = subprocess.run(["sips", "-s", "format", "tiff", src_path, "--out", dst_path],
                           capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(dst_path):
        return False, proc.stderr.strip()
    return True, ""


def read_tiff_rgb_u16(tiff_path):
    """Reads via OpenCV (preserves true 16-bit data; PIL on this old Pillow
    silently downcasts to 8-bit, verified). Returns HxWx3 uint16, RGB order."""
    bgr = cv2.imread(tiff_path, cv2.IMREAD_UNCHANGED)
    if bgr is None:
        raise ValueError(f"cv2 could not read {tiff_path} (possibly truncated/corrupt)")
    if bgr.ndim == 2:
        bgr = np.stack([bgr, bgr, bgr], axis=-1)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def save_downsized_copy(arr_rgb_u16, dst_path):
    """Writes the tiff_converted/ deliverable: 50%-linear downsized, lossless
    deflate-compressed 16-bit TIFF. Measurements never read this file back --
    it exists only as the on-disk artifact, sized to fit real available disk
    space (see module docstring)."""
    h, w = arr_rgb_u16.shape[:2]
    small = cv2.resize(arr_rgb_u16, (max(1, int(w * DOWNSIZE_LINEAR_FACTOR)),
                                      max(1, int(h * DOWNSIZE_LINEAR_FACTOR))),
                        interpolation=cv2.INTER_AREA)
    bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(dst_path, bgr, [cv2.IMWRITE_TIFF_COMPRESSION, 8])  # 8 = Adobe Deflate, lossless
    if not ok:
        raise ValueError(f"failed to write downsized deliverable {dst_path}")


def make_thumbnail(arr_rgb_u16, target_w=320):
    """Small 8-bit RGB thumbnail for the PDF report only (display, not
    measurement). Percentile-stretched (1st-99.5th) per image so the faint
    16-bit background and the bright core are both visible -- a plain /257
    linear downcast leaves most of these frames looking almost black."""
    h, w = arr_rgb_u16.shape[:2]
    target_h = max(1, int(h * target_w / w))
    small = cv2.resize(arr_rgb_u16, (target_w, target_h), interpolation=cv2.INTER_AREA).astype(np.float64)
    lo, hi = np.percentile(small, [1.0, 99.5])
    if hi <= lo:
        hi = lo + 1.0
    stretched = np.clip((small - lo) / (hi - lo), 0, 1) * 255.0
    return stretched.astype(np.uint8)


def channel_stats(arr):
    """arr: HxWxC uint16/float. Returns list of (min,max,mean) per channel."""
    stats = []
    nch = arr.shape[2] if arr.ndim == 3 else 1
    if arr.ndim == 2:
        arr = arr[:, :, None]
    for c in range(nch):
        ch = arr[:, :, c].astype(np.float64)
        stats.append((float(ch.min()), float(ch.max()), float(ch.mean())))
    return stats


def exposure_flag_reason(stats, channel_names):
    reasons = []
    for name, (mn, mx, mean) in zip(channel_names, stats):
        if mean <= FLAG_LOW:
            reasons.append(f"{name} channel mean={mean:.1f} within 5% of 0 "
                            f"(of native 16-bit range 0-65535) -- near-black/underexposed")
        elif mean >= FLAG_HIGH:
            reasons.append(f"{name} channel mean={mean:.1f} within 5% of 65535 "
                            f"(native 16-bit range) -- near-white/clipped")
    return "; ".join(reasons) if reasons else None


# ---------- blob / r_EE_50 ----------

MAX_BLOB_FRACTION = 0.35   # a real blob's core must fit within this fraction of
                           # the smaller image dimension; used to auto-raise the
                           # threshold past thin diffraction-spike artifacts that
                           # would otherwise connect the blob to the frame edge
                           # or to a distant secondary ghost/flare blob
WING_PAD_MULT = 1.5        # ROI padding beyond the core bbox, as a multiple of
                           # the core bbox's larger dimension
WING_PAD_CAP_PX = 800      # ...capped at this many pixels, so padding can't
                           # balloon back out toward full-frame size


def _label_at(flux_full, frac):
    peak = flux_full.max()
    mask = flux_full > (frac * peak)
    labeled, n = ndimage.label(mask, structure=np.ones((3, 3), dtype=int))
    return labeled, n, peak


SEARCH_DOWNSAMPLE = 8  # coarse blob-location search runs on a strided
                       # 1/8-scale copy for speed; the actual energy/centroid
                       # integral is always computed on full-resolution pixels


def measure_blob(arr_rgb):
    """arr_rgb: HxWx3 uint8/float array. Returns dict with centroid, r_EE_50_px,
    total_intensity, blob_bbox, n_components, or raises ValueError if no blob found.

    Real phone-camera point-source photos in this dataset show a compact bright
    core plus (a) a wide, gradually-decaying veiling-glare halo and (b) thin,
    near-peak-brightness diffraction spikes that, at a naive low threshold,
    connect the main blob to the image edge and/or to an unrelated secondary
    ghost blob elsewhere in the frame (confirmed by inspection on 600b/M0).
    To isolate the true point-source core robustly, the threshold fraction is
    raised from 5% of peak in 5%-of-peak steps until the resulting main
    component's bounding box fits within MAX_BLOB_FRACTION of the frame --
    i.e. until the spike/edge/ghost connection breaks. This search runs on a
    downsampled copy for speed; the energy/centroid integral is then taken at
    full resolution over that core bbox (scaled back up) padded by a capped
    wing margin (WING_PAD_MULT / WING_PAD_CAP_PX), not the whole frame, with
    any pixel belonging to a different component (relabeled at full res
    within the ROI, same final threshold) zeroed out first.
    """
    H, W = arr_rgb.shape[:2]

    small_rgb = arr_rgb[::SEARCH_DOWNSAMPLE, ::SEARCH_DOWNSAMPLE]
    gray_small = small_rgb.astype(np.float64).mean(axis=2)
    background = float(np.percentile(gray_small, 5))
    flux_small = np.clip(gray_small - background, 0, None)
    peak_small = flux_small.max()
    if peak_small <= 0:
        raise ValueError("no signal above background (5th percentile) -- flat/blank frame")
    Hs, Ws = gray_small.shape
    max_dim_small = MAX_BLOB_FRACTION * min(Hs, Ws)

    chosen_frac = None
    by0 = by1 = bx0 = bx1 = None
    for frac in np.arange(0.05, 1.0, 0.05):
        lab, n, _ = _label_at(flux_small, frac)
        if n == 0:
            continue
        sums = ndimage.sum(flux_small, lab, index=np.arange(1, n + 1))
        main = int(np.argmax(sums)) + 1
        ys, xs = np.where(lab == main)
        y0s, y1s, x0s, x1s = ys.min(), ys.max(), xs.min(), xs.max()
        if max(y1s - y0s, x1s - x0s) <= max_dim_small:
            chosen_frac = frac
            by0, by1, bx0, bx1 = y0s, y1s, x0s, x1s
            break
    if chosen_frac is None:
        chosen_frac = 0.95
        lab, n, _ = _label_at(flux_small, chosen_frac)
        sums = ndimage.sum(flux_small, lab, index=np.arange(1, n + 1))
        main = int(np.argmax(sums)) + 1
        ys, xs = np.where(lab == main)
        by0, by1, bx0, bx1 = ys.min(), ys.max(), xs.min(), xs.max()

    # scale the downsampled-coords core bbox back to full resolution
    y0 = max(0, by0 * SEARCH_DOWNSAMPLE)
    y1 = min(H - 1, (by1 + 1) * SEARCH_DOWNSAMPLE - 1)
    x0 = max(0, bx0 * SEARCH_DOWNSAMPLE)
    x1 = min(W - 1, (bx1 + 1) * SEARCH_DOWNSAMPLE - 1)

    bh, bw = (y1 - y0 + 1), (x1 - x0 + 1)
    pad = min(WING_PAD_MULT * max(bh, bw), WING_PAD_CAP_PX)
    ry0, ry1 = max(0, int(y0 - pad)), min(H, int(y1 + pad + 1))
    rx0, rx1 = max(0, int(x0 - pad)), min(W, int(x1 + pad + 1))

    # full-resolution analysis, confined to this ROI only
    roi_gray = arr_rgb[ry0:ry1, rx0:rx1].astype(np.float64).mean(axis=2)
    roi_flux = np.clip(roi_gray - background, 0, None)
    peak = roi_flux.max()
    roi_labeled, n_components, _ = _label_at(roi_flux, chosen_frac)
    sums = ndimage.sum(roi_flux, roi_labeled, index=np.arange(1, n_components + 1))
    main_label = int(np.argmax(sums)) + 1
    # zero out any OTHER component's pixels (same final threshold) so a
    # nearby secondary blob/ghost does not contaminate this blob's
    # centroid/energy
    other_mask = (roi_labeled != 0) & (roi_labeled != main_label)
    roi_flux[other_mask] = 0.0

    total_intensity = float(roi_flux.sum())
    if total_intensity <= 0:
        raise ValueError("zero total intensity in ROI after masking other components")

    yy, xx = np.mgrid[ry0:ry1, rx0:rx1]
    cy = float((yy * roi_flux).sum() / total_intensity)
    cx = float((xx * roi_flux).sum() / total_intensity)

    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2).ravel()
    flat_flux = roi_flux.ravel()
    order = np.argsort(dist)
    dist_sorted = dist[order]
    flux_sorted = flat_flux[order]
    cumsum = np.cumsum(flux_sorted)
    target = 0.5 * total_intensity
    idx = np.searchsorted(cumsum, target)
    if idx <= 0:
        r_ee50 = float(dist_sorted[0])
    elif idx >= len(dist_sorted):
        r_ee50 = float(dist_sorted[-1])
    else:
        d0, d1 = dist_sorted[idx - 1], dist_sorted[idx]
        c0, c1 = cumsum[idx - 1], cumsum[idx]
        if c1 > c0:
            r_ee50 = float(d0 + (target - c0) * (d1 - d0) / (c1 - c0))
        else:
            r_ee50 = float(d1)

    return {
        "centroid_x_px": cx + 0,  # already in full-image coords (mgrid used rx0/ry0 offsets)
        "centroid_y_px": cy + 0,
        "r_EE_50_px": r_ee50,
        "total_intensity": total_intensity,
        "bbox": (int(y0), int(y1), int(x0), int(x1)),
        "n_components": int(n_components),
        "peak_flux": float(peak),
        "background": background,
        "threshold_frac_used": float(chosen_frac),
        "core_bbox": (int(y0), int(y1), int(x0), int(x1)),
    }


if __name__ == "__main__":
    import time
    tmp = "/tmp/_smoke_probe.tiff"
    ok, err = convert_to_tiff(os.path.join(EXP2, "600b", "M0600b.dng"), tmp)
    assert ok, err
    arr = read_tiff_rgb_u16(tmp)
    print("shape/dtype:", arr.shape, arr.dtype, "max:", arr.max())
    print("channel stats:", channel_stats(arr))
    t0 = time.time()
    result = measure_blob(arr)
    print("blob result:", result, "elapsed", time.time() - t0)
    os.remove(tmp)
