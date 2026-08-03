"""
Tumbling-E optotype generation.

Watson & Ahumada (2008) (literature.get('watson_ahumada_2008_wfa_metric')) defines
each optotype on a standard 5x5-unit grid: 5 MAR tall, 5 MAR wide, where MAR (the
model's size parameter) is the optotype's STROKE WIDTH in arcmin. Snellen E's
(tumbling E, 4 orientations) are one of the patent's own explicitly-supported
optotype sets (claim 6) -- this project's choice, not a deviation, made because a
4-alternative task is simpler to template-match unambiguously than 10 Sloan
letters, per the task brief.
"""
import numpy as np
from scipy import ndimage

# Classic block "E", 5x5 units, opening to the right (three horizontal bars
# extending right from a vertical spine on the left). The other 3 orientations are
# 90-degree rotations of this -- a block E has no rotational symmetry, so all 4
# are mutually distinguishable, which is all that matters for template matching
# (the specific right/down/left/up labeling below is a naming convention only).
_E_PATTERN = np.array([
    [1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0],
    [1, 1, 1, 1, 0],
    [1, 0, 0, 0, 0],
    [1, 1, 1, 1, 1],
], dtype=float)

ORIENTATIONS = ("right", "up", "left", "down")  # np.rot90 k=0,1,2,3


def pattern_for_orientation(orientation):
    k = ORIENTATIONS.index(orientation)
    return np.rot90(_E_PATTERN, k=k)


def render_tumbling_e(orientation, mar_arcmin, arcmin_per_pixel, canvas_size_px):
    """
    Renders one tumbling-E orientation as a clean (unblurred, noiseless) bitmap,
    anti-aliased via area-preserving zoom, centered on a canvas_size_px x
    canvas_size_px canvas (zero-padded or center-cropped as needed to fit).

    mar_arcmin: the optotype's stroke width (MAR) in arcmin. Overall letter size
      is 5*mar_arcmin arcmin (Watson & Ahumada's 5x5-unit convention).
    arcmin_per_pixel: the simulation grid's angular pixel scale (derived from the
      real retinal PSF's dx and the eye's v_r -- see ideal_observer.py).
    """
    pattern = pattern_for_orientation(orientation)
    overall_size_arcmin = 5.0 * mar_arcmin
    size_px = max(int(round(overall_size_arcmin / arcmin_per_pixel)), 5)
    zoom_factor = size_px / pattern.shape[0]
    letter = ndimage.zoom(pattern, zoom_factor, order=1, mode="nearest")
    letter = np.clip(letter, 0.0, 1.0)

    canvas = np.zeros((canvas_size_px, canvas_size_px), dtype=float)
    lh, lw = letter.shape
    # Center the letter on the canvas; crop the letter if it doesn't fit (large
    # letter sizes / small canvases), crop the canvas placement otherwise.
    if lh > canvas_size_px or lw > canvas_size_px:
        top = max((lh - canvas_size_px) // 2, 0)
        left = max((lw - canvas_size_px) // 2, 0)
        letter = letter[top:top + canvas_size_px, left:left + canvas_size_px]
        lh, lw = letter.shape
    r0 = (canvas_size_px - lh) // 2
    c0 = (canvas_size_px - lw) // 2
    canvas[r0:r0 + lh, c0:c0 + lw] = letter
    return canvas


def render_all_orientations(mar_arcmin, arcmin_per_pixel, canvas_size_px):
    """Returns dict {orientation: bitmap} for all 4 orientations, same size/scale."""
    return {
        o: render_tumbling_e(o, mar_arcmin, arcmin_per_pixel, canvas_size_px)
        for o in ORIENTATIONS
    }
