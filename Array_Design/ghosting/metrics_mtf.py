"""Mirrors stage3_human_vision/metrics.py's mtf_radial + frequency-conversion
functions exactly (same FFT/normalization/binning), needed for the ghosting-regime
classifier. Not reimplemented differently -- copied verbatim from the real project
file to avoid any numerical divergence."""
import numpy as np

def mtf_radial(I, dx):
    N = I.shape[0]
    otf = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(I)))
    mtf2d = np.abs(otf)
    center = N // 2
    mtf2d = mtf2d / mtf2d[center, center]
    freqs = np.fft.fftshift(np.fft.fftfreq(N, d=dx)) * 1e-6
    FX, FY = np.meshgrid(freqs, freqs, indexing="xy")
    Frad = np.sqrt(FX ** 2 + FY ** 2)
    n_bins = N // 2
    f_max = freqs.max()
    bins = np.linspace(0, f_max, n_bins + 1)
    idx = np.clip(np.digitize(Frad.ravel(), bins) - 1, 0, n_bins - 1)
    sums = np.bincount(idx, weights=mtf2d.ravel(), minlength=n_bins)
    counts = np.bincount(idx, minlength=n_bins)
    counts[counts == 0] = 1
    mtf_1d = sums / counts
    f_centers = 0.5 * (bins[:-1] + bins[1:])
    return f_centers, mtf_1d

def cycles_per_um_to_cycles_per_degree(f_cpum, v_r):
    um_per_degree = v_r * (np.pi / 180.0) * 1e6
    return f_cpum * um_per_degree

def interp_mtf_at_freq(f_centers_cpum, mtf_1d, f_query_cpum):
    """MTF value at an arbitrary query frequency, linearly interpolated (0 beyond
    the computed grid's Nyquist limit, since MTF is by definition ~0 or undefined
    past the sampling limit anyway)."""
    if f_query_cpum > f_centers_cpum.max():
        return 0.0
    return float(np.interp(f_query_cpum, f_centers_cpum, mtf_1d))
