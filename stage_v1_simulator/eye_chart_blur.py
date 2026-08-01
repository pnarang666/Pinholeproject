"""
Synthetic eye chart (tumbling-E rows at decreasing size) convolved with the normalized
retinal PSF. NOT a clinically calibrated optotype -- a qualitative demonstration only,
labeled as such everywhere it appears.
"""

import numpy as np
from scipy.signal import fftconvolve


def make_tumbling_e_chart(size_px=512, n_rows=8, um_per_px=None):
    """
    Draws n_rows of a tumbling 'E' shape at geometrically decreasing size (mimicking a
    Snellen-chart row progression, NOT a calibrated optotype -- stroke widths and row
    spacing are chosen for visual clarity in this demo, not clinical accuracy).
    Returns (chart, um_per_px) -- chart is a 2D float array in [0, 1].
    """
    chart = np.zeros((size_px, size_px), dtype=float)
    row_height = size_px // n_rows
    for row in range(n_rows):
        scale = 0.9 ** row
        e_height = int(row_height * 0.7 * scale) + 4
        stroke = max(2, e_height // 5)
        y0 = row * row_height + (row_height - e_height) // 2
        x0 = size_px // 6
        # vertical spine
        chart[y0:y0 + e_height, x0:x0 + stroke] = 1.0
        # three horizontal arms
        arm_len = int(e_height * 0.8)
        for frac in (0.0, 0.45, 0.9):
            y_arm = y0 + int(frac * (e_height - stroke))
            chart[y_arm:y_arm + stroke, x0:x0 + arm_len] = 1.0

    if um_per_px is None:
        um_per_px = 1.0
    return chart, um_per_px


def normalize_psf(I_retina):
    """Unit-VOLUME normalization (sum=1), the correct convolution kernel convention --
    NOT peak-normalized, which would silently change the chart's overall brightness."""
    total = np.sum(I_retina)
    return I_retina / total if total > 0 else I_retina


def convolve_chart_with_psf(chart, I_retina, chart_um_per_px, retina_dx_m):
    """
    Resamples the retinal PSF onto the chart's own pixel grid (via the stated
    um-per-px conversion factor) and convolves. Returns (blurred_chart, conversion_info).
    """
    retina_um_per_px = retina_dx_m * 1e6
    zoom_factor = retina_um_per_px / chart_um_per_px

    from scipy.ndimage import zoom
    psf_norm = normalize_psf(I_retina)
    # crop the PSF to a reasonable kernel size before resampling (the full grid is
    # mostly near-zero far from center; cropping keeps the convolution fast)
    N = psf_norm.shape[0]
    center = N // 2
    crop = min(N, 256)
    half = crop // 2
    psf_crop = psf_norm[center - half:center + half, center - half:center + half]

    if zoom_factor > 0 and np.isfinite(zoom_factor):
        psf_resampled = zoom(psf_crop, zoom_factor, order=1)
        psf_resampled = np.clip(psf_resampled, 0, None)
        s = psf_resampled.sum()
        if s > 0:
            psf_resampled /= s
    else:
        psf_resampled = psf_crop

    blurred = fftconvolve(chart, psf_resampled, mode="same")
    blurred = np.clip(blurred, 0, blurred.max() if blurred.max() > 0 else 1)

    return blurred, {
        "chart_um_per_px": chart_um_per_px,
        "retina_um_per_px": retina_um_per_px,
        "zoom_factor": zoom_factor,
        "psf_kernel_px": psf_resampled.shape[0],
    }
