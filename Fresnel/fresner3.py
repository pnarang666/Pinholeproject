import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons

def generate_aperture(shape, grid_size, pitch_px, radius_px):
    """Creates initial 2D complex electric field U(x,y,0) at the pinhole plane."""
    y, x = np.ogrid[-grid_size//2:grid_size//2, -grid_size//2:grid_size//2]
    U0 = np.zeros((grid_size, grid_size), dtype=complex)
    
    if shape == 'Single Pinhole':
        U0[x**2 + y**2 <= radius_px**2] = 1.0 + 0.0j
        
    elif shape == 'Hexagonal Array':
        # Create a mini hexagonal grid of pinholes
        r2 = x**2 + y**2
        # Center hole
        U0[r2 <= radius_px**2] = 1.0
        # Surrounding 6 holes
        angles = np.linspace(0, 2*np.pi, 6, endpoint=False)
        for ang in angles:
            cx = int(pitch_px * np.cos(ang))
            cy = int(pitch_px * np.sin(ang))
            U0[(x - cx)**2 + (y - cy)**2 <= radius_px**2] = 1.0
            
    elif shape == 'Square Slit':
        U0[(np.abs(x) <= radius_px) & (np.abs(y) <= radius_px)] = 1.0 + 0.0j
        
    return U0

def fresnel_asm_propagate(U0, wavelength_m, z_gap_m, L_physical_m):
    """
    Propagates electric field U0 across distance z_gap using Angular Spectrum Method (ASM).
    """
    if z_gap_m == 0:
        return U0
        
    N = U0.shape[0]
    df = 1.0 / L_physical_m  # Spatial frequency step size
    
    # Frequency grid
    fx = np.fft.fftfreq(N, d=L_physical_m/N)
    fy = np.fft.fftfreq(N, d=L_physical_m/N)
    FX, FY = np.meshgrid(fx, fy)
    
    # Transfer function for free-space Angular Spectrum Method
    k = 2 * np.pi / wavelength_m
    f_sq = FX**2 + FY**2
    
    # Evanescent wave filter condition: (1 - lambda^2 * f_sq) >= 0
    kernel_phase = np.where(1.0 - (wavelength_m**2 * f_sq) >= 0,
                            2 * np.pi * (z_gap_m / wavelength_m) * np.sqrt(np.maximum(0, 1.0 - (wavelength_m**2 * f_sq))),
                            0)
    
    H = np.exp(1j * kernel_phase)
    # Zero out evanescent non-propagating waves
    H[1.0 - (wavelength_m**2 * f_sq) < 0] = 0.0
    
    # Optical field propagation
    U_fft = np.fft.fft2(U0)
    U_z = np.fft.ifft2(U_fft * H)
    
    return U_z

# --- Interactivity Setup ---
GRID_SIZE = 512
L_PHYSICAL = 6e-3  # 6 mm total physical window size

fig, (ax_int, ax_phase, ax_slice) = plt.subplots(1, 3, figsize=(13, 5))
plt.subplots_adjust(bottom=0.3)
fig.canvas.manager.set_window_title("Fresnel Near-Field Propagation Engine")

# Default Parameters
init_wave = 555.0  # nm
init_gap = 12.0    # mm (Standard vertex gap to cornea)
init_dia = 0.8     # mm
init_shape = 'Single Pinhole'

# Generate Initial Field
px_scale = GRID_SIZE / L_PHYSICAL
r_px = int((init_dia * 1e-3 / 2.0) * px_scale)
pitch_px = int(1.5e-3 * px_scale)

U0 = generate_aperture(init_shape, GRID_SIZE, pitch_px, r_px)
Uz = fresnel_asm_propagate(U0, init_wave*1e-9, init_gap*1e-3, L_PHYSICAL)

I_z = np.abs(Uz)**2
Phase_z = np.angle(Uz)

# Render Images
im_int = ax_int.imshow(I_z, cmap='inferno', origin='lower', extent=[-3, 3, -3, 3])
ax_int.set_title("Fresnel Intensity at Cornea Plane")
ax_int.set_xlabel("x (mm)")
ax_int.set_ylabel("y (mm)")

im_phase = ax_phase.imshow(Phase_z, cmap='twilight', origin='lower', extent=[-3, 3, -3, 3])
ax_phase.set_title("Wavefront Phase Profile (Ripples)")
ax_phase.set_xlabel("x (mm)")

mid = GRID_SIZE // 2
x_mm = np.linspace(-L_PHYSICAL*1e3/2, L_PHYSICAL*1e3/2, GRID_SIZE)
line_slice, = ax_slice.plot(x_mm, I_z[mid, :], color='crimson', lw=1.5)
ax_slice.set_title("1D Transverse Cut")
ax_slice.set_xlabel("x (mm)")
ax_slice.set_ylabel("Intensity |U|^2")
ax_slice.set_ylim(-0.1, 1.4)
ax_slice.grid(True, alpha=0.3)

# Sliders
ax_gap  = plt.axes([0.1, 0.15, 0.4, 0.03])
ax_dia  = plt.axes([0.1, 0.08, 0.4, 0.03])
ax_wave = plt.axes([0.1, 0.01, 0.4, 0.03])
ax_radio = plt.axes([0.60, 0.02, 0.25, 0.15])

s_gap  = Slider(ax_gap,  'Gap d_gap (mm)', 0.0, 50.0, valinit=init_gap, valfmt='%1.1f mm')
s_dia  = Slider(ax_dia,  'Hole Dia (mm)',  0.2, 2.0,  valinit=init_dia, valfmt='%1.2f mm')
s_wave = Slider(ax_wave, 'Wavelength (nm)', 400.0, 700.0, valinit=init_wave, valfmt='%1.0f nm')

radio_shape = RadioButtons(ax_radio, ('Single Pinhole', 'Hexagonal Array', 'Square Slit'), active=0)

def update(val):
    gap_m = s_gap.val * 1e-3
    dia_m = s_dia.val * 1e-3
    wave_m = s_wave.val * 1e-9
    shape = radio_shape.value_selected
    
    r_px_val = int((dia_m / 2.0) * px_scale)
    pitch_px_val = int(1.5e-3 * px_scale)
    
    U0_new = generate_aperture(shape, GRID_SIZE, pitch_px_val, r_px_val)
    Uz_new = fresnel_asm_propagate(U0_new, wave_m, gap_m, L_PHYSICAL)
    
    I_new = np.abs(Uz_new)**2
    Phase_new = np.angle(Uz_new)
    
    im_int.set_data(I_new)
    im_phase.set_data(Phase_new)
    line_slice.set_ydata(I_new[mid, :])
    
    fig.canvas.draw_idle()

s_gap.on_changed(update)
s_dia.on_changed(update)
s_wave.on_changed(update)
radio_shape.on_clicked(update)

plt.show()
