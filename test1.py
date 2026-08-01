"""
Interactive, tweakable version of the pinhole -> cornea Fresnel/ASM propagation stage.

Unlike fresnel_cornea_stage.py (which runs a fixed sweep and dumps PNGs), this script opens
a live matplotlib window with sliders for a_hole, d_gap, and wavelength. Moving a slider
recomputes the ASM propagation and redraws the intensity map, phase map, radial profile,
and encircled-energy curve immediately -- no editing lists and re-running.

REQUIRES A GUI BACKEND. This will NOT work in a headless/Agg environment (e.g. a remote
sandbox with no display). Run it on your own machine:

    pip install numpy scipy matplotlib
    python3 interactive_cornea_sim.py

If it opens a blank window or errors on 'no display', try forcing a backend:
    MPLBACKEND=TkAgg python3 interactive_cornea_sim.py      (Linux/most installs)
    MPLBACKEND=MacOSX python3 interactive_cornea_sim.py     (Mac)
    MPLBACKEND=Qt5Agg python3 interactive_cornea_sim.py     (if you have PyQt5 installed)

Grid resolution note (read before assuming a weird-looking pattern is a bug): this tool
defaults to N=512 for responsiveness while dragging sliders. That is fine for a_hole above
~400um but WILL under-resolve the Fresnel-zone structure for small a_hole / large d_gap
(high Fresnel number) combinations -- exactly the aliasing issue documented and measured in
fresnel_cornea_stage.py's own validation. Use the "grid N" radio buttons to bump to 1024 or
2048 before trusting fine ring structure or reading off r_EE for a final number; only use
512 for fast exploration while you're still choosing which region of parameter space to look at.
"""

import numpy as np
import matplotlib
matplotlib.use(matplotlib.get_backend() if matplotlib.get_backend().lower() != "agg" else "TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons, Button

# ----------------------------------------------------------------------------------
# Core physics (same equations as fresnel_cornea_stage.py, copied here so this file
# runs standalone -- no import dependency on the other script)
# ----------------------------------------------------------------------------------
L_WINDOW = 6e-3   # m, fixed physical window size


def circular_aperture(N, dx, diameter):
    x = (np.arange(N) - N // 2) * dx
    X, Y = np.meshgrid(x, x, indexing="xy")
    R = np.sqrt(X**2 + Y**2)
    U0 = (R <= diameter / 2.0).astype(np.complex128)
    return U0, R


def asm_propagate(U0, dx, wavelength, z):
    N = U0.shape[0]
    k = 2 * np.pi / wavelength
    fx = np.fft.fftfreq(N, d=dx)
    FX, FY = np.meshgrid(fx, fx, indexing="xy")
    freq_sq = FX**2 + FY**2
    prop_mask = freq_sq <= (1.0 / wavelength**2)
    kz_term = np.zeros_like(freq_sq)
    kz_term[prop_mask] = np.sqrt(1.0 - (wavelength**2) * freq_sq[prop_mask])
    H = np.zeros((N, N), dtype=np.complex128)
    H[prop_mask] = np.exp(1j * k * z * kz_term[prop_mask])
    return np.fft.ifft2(np.fft.fft2(U0) * H)


def radial_profile(I, R, n_bins=250):
    r_max = R.max()
    bins = np.linspace(0, r_max, n_bins + 1)
    idx = np.clip(np.digitize(R.ravel(), bins) - 1, 0, n_bins - 1)
    sums = np.bincount(idx, weights=I.ravel(), minlength=n_bins)
    counts = np.bincount(idx, minlength=n_bins)
    counts[counts == 0] = 1
    return 0.5 * (bins[:-1] + bins[1:]), sums / counts


def encircled_energy(I, R, dx, n_bins=250):
    r_max = R.max()
    bins = np.linspace(0, r_max, n_bins + 1)
    idx = np.clip(np.digitize(R.ravel(), bins) - 1, 0, n_bins - 1)
    power_per_bin = np.bincount(idx, weights=I.ravel(), minlength=n_bins) * dx**2
    cum = np.cumsum(power_per_bin)
    total = cum[-1]
    EE = cum / total if total > 0 else cum
    return bins[1:], EE, total


def r_for_EE(r_edges, EE, target_P):
    if target_P >= EE[-1]:
        return r_edges[-1]
    i = np.searchsorted(EE, target_P)
    if i == 0:
        return r_edges[0]
    r0, r1, e0, e1 = r_edges[i - 1], r_edges[i], EE[i - 1], EE[i]
    if e1 == e0:
        return r0
    return r0 + (target_P - e0) / (e1 - e0) * (r1 - r0)


def fresnel_number(a_hole, wavelength, z):
    return (a_hole / 2.0) ** 2 / (wavelength * z)


def deprecated_a_eff(a_hole, wavelength, d_gap):
    return np.sqrt(a_hole**2 + (2.44 * wavelength * d_gap / a_hole) ** 2)


# ----------------------------------------------------------------------------------
# Interactive figure
# ----------------------------------------------------------------------------------
class InteractiveCorneaSim:
    def __init__(self):
        self.N = 512
        self.a_hole = 428e-6     # m
        self.d_gap = 12e-3       # m
        self.wavelength = 550e-9  # m

        self.fig = plt.figure(figsize=(12, 8))
        gs = self.fig.add_gridspec(2, 3, height_ratios=[4, 1], width_ratios=[1, 1, 1])

        self.ax_intensity = self.fig.add_subplot(gs[0, 0])
        self.ax_phase = self.fig.add_subplot(gs[0, 1])
        self.ax_radial = self.fig.add_subplot(gs[0, 2])
        # bottom row reserved for controls; built via subplots_adjust + manual axes below

        self.fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.32, wspace=0.35)

        # Slider axes (manually placed in the bottom margin)
        ax_a = self.fig.add_axes([0.08, 0.20, 0.55, 0.03])
        ax_d = self.fig.add_axes([0.08, 0.15, 0.55, 0.03])
        ax_w = self.fig.add_axes([0.08, 0.10, 0.55, 0.03])
        ax_radio = self.fig.add_axes([0.70, 0.05, 0.10, 0.20])
        ax_reset = self.fig.add_axes([0.85, 0.10, 0.10, 0.05])

        self.s_a = Slider(ax_a, "a_hole (um)", 100, 1500, valinit=self.a_hole * 1e6, valstep=5)
        self.s_d = Slider(ax_d, "d_gap (mm)", 3, 25, valinit=self.d_gap * 1e3, valstep=0.5)
        self.s_w = Slider(ax_w, "wavelength (nm)", 400, 700, valinit=self.wavelength * 1e9, valstep=5)
        self.radio_N = RadioButtons(ax_radio, ("512 (fast)", "1024", "2048 (slow)"), active=0)
        self.b_reset = Button(ax_reset, "Reset")

        self.s_a.on_changed(self.update)
        self.s_d.on_changed(self.update)
        self.s_w.on_changed(self.update)
        self.radio_N.on_clicked(self.change_N)
        self.b_reset.on_clicked(self.reset)

        # EE curve shares ax_radial via a twin y-axis (built once, reused every redraw)
        self.ax_radial2 = self.ax_radial.twinx()

        self.text_box = self.fig.text(0.70, 0.27, "", fontsize=9, family="monospace",
                                       verticalalignment="top")

        self.compute_and_draw(first=True)
        plt.show()

    def change_N(self, label):
        self.N = {"512 (fast)": 512, "1024": 1024, "2048 (slow)": 2048}[label]
        self.update(None)

    def reset(self, event):
        self.s_a.reset()
        self.s_d.reset()
        self.s_w.reset()

    def compute_and_draw(self, first=False):
        a_hole = self.s_a.val * 1e-6
        d_gap = self.s_d.val * 1e-3
        wavelength = self.s_w.val * 1e-9
        N = self.N
        dx = L_WINDOW / N

        U0, R = circular_aperture(N, dx, a_hole)
        input_power = np.sum(np.abs(U0) ** 2) * dx**2

        Uz = asm_propagate(U0, dx, wavelength, d_gap)
        I = np.abs(Uz) ** 2
        phase = np.angle(Uz)

        output_power = np.sum(I) * dx**2
        energy_err = abs(output_power - input_power) / input_power if input_power > 0 else np.nan

        r_edges, EE, _ = encircled_energy(I, R, dx)
        r_centers, I_radial = radial_profile(I, R)
        r50 = r_for_EE(r_edges, EE, 0.5) * 1e6
        r80 = r_for_EE(r_edges, EE, 0.8) * 1e6
        r90 = r_for_EE(r_edges, EE, 0.9) * 1e6
        NF = fresnel_number(a_hole, wavelength, d_gap)
        a_eff = deprecated_a_eff(a_hole, wavelength, d_gap)

        extent_um = R.max() * 1e6 * np.array([-1, 1, -1, 1])
        r_max_plot = R.max() * 1e6 * 0.5

        self.ax_intensity.clear()
        im1 = self.ax_intensity.imshow(I, extent=extent_um, cmap="inferno", origin="lower")
        self.ax_intensity.set_title("Intensity at cornea")
        self.ax_intensity.set_xlabel("x (um)"); self.ax_intensity.set_ylabel("y (um)")

        self.ax_phase.clear()
        self.ax_phase.imshow(phase, extent=extent_um, cmap="twilight", origin="lower")
        self.ax_phase.set_title("Phase arg(U)")
        self.ax_phase.set_xlabel("x (um)"); self.ax_phase.set_ylabel("y (um)")

        self.ax_radial.clear()
        self.ax_radial.plot(r_centers * 1e6, I_radial, color="firebrick")
        self.ax_radial.set_xlim(0, r_max_plot)
        self.ax_radial.set_xlabel("radius (um)")
        self.ax_radial.set_ylabel("intensity", color="firebrick")
        self.ax_radial.set_title("Radial profile + EE(r)")

        self.ax_radial2.clear()
        self.ax_radial2.plot(r_edges * 1e6, EE, color="navy")
        self.ax_radial2.axvline(a_eff / 2 * 1e6, color="gray", linestyle=":", alpha=0.6)
        self.ax_radial2.set_xlim(0, r_max_plot)
        self.ax_radial2.set_ylim(0, 1.05)
        self.ax_radial2.set_ylabel("encircled energy", color="navy")

        self.text_box.set_text(
            f"N_F           = {NF:8.2f}\n"
            f"r_EE(0.5)     = {r50:8.2f} um\n"
            f"r_EE(0.8)     = {r80:8.2f} um\n"
            f"r_EE(0.9)     = {r90:8.2f} um\n"
            f"a_eff/2 (dep.)= {a_eff/2*1e6:8.2f} um  <- diagnostic only\n"
            f"energy cons.  = {energy_err:8.2e}\n"
            f"grid N        = {N}  (dx={dx*1e6:.2f} um)"
        )

        self.fig.canvas.draw_idle()

    def update(self, val):
        self.compute_and_draw()


if __name__ == "__main__":
    InteractiveCorneaSim()