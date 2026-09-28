import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons

def create_mask(shape_type, grid_size, mask_radius_px):
    """Generates a 2D binary grid mask (1 = transparent, 0 = opaque)."""
    y, x = np.ogrid[-grid_size//2:grid_size//2, -grid_size//2:grid_size//2]
    mask = np.zeros((grid_size, grid_size), dtype=float)
    
    if shape_type == 'Single Circle':
        mask[x**2 + y**2 <= mask_radius_px**2] = 1.0
        
    elif shape_type == 'Square':
        w = mask_radius_px
        mask[np.abs(x) <= w] = 1.0
        mask[np.abs(y) <= w] = 1.0
        
    elif shape_type == 'Annulus (Ring)':
        r_out = mask_radius_px
        r_in = mask_radius_px * 0.5
        r2 = x**2 + y**2
        mask[(r2 <= r_out**2) & (r2 >= r_in**2)] = 1.0
        
    elif shape_type == '3-Hole Triplet':
        r_hole = mask_radius_px * 0.35
        d = mask_radius_px * 0.8
        centers = [(0, d), (-d * np.sin(np.pi/3), -d * np.cos(np.pi/3)), (d * np.sin(np.pi/3), -d * np.cos(np.pi/3))]
        for cx, cy in centers:
            mask[(x - cx)**2 + (y - cy)**2 <= r_hole**2] = 1.0
            
    return mask

def compute_diffraction(mask, wavelength_nm, distance_cm, aperture_diameter_mm, grid_size=512):
    """Computes the 2D diffraction pattern using FFT."""
    wavelength = wavelength_nm * 1e-9
    distance = distance_cm * 1e-2
    
    # 2D Fast Fourier Transform
    fft_field = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(mask)))
    intensity = np.abs(fft_field)**2
    
    # Normalize intensity
    if np.max(intensity) > 0:
        intensity /= np.max(intensity)
        
    return intensity

# --- Setup Interactive Figure ---
fig = plt.figure(figsize=(12, 6))
fig.canvas.manager.set_window_title('Arbitrary Mask Diffraction Simulator')

# Subplot axes for layout
ax_mask = plt.axes([0.05, 0.35, 0.28, 0.55])
ax_diff = plt.axes([0.38, 0.35, 0.28, 0.55])
ax_slice = plt.axes([0.71, 0.35, 0.26, 0.55])

# Initial values
init_wavelength = 555.0  # nm
init_distance = 15.0     # cm
init_diameter = 0.8      # mm
init_shape = 'Single Circle'
GRID_SIZE = 512

# Generate initial data
mask_init = create_mask(init_shape, GRID_SIZE, mask_radius_px=30)
I_init = compute_diffraction(mask_init, init_wavelength, init_distance, init_diameter, GRID_SIZE)

# Render initial images
im_mask = ax_mask.imshow(mask_init, cmap='gray', origin='lower')
ax_mask.set_title("Aperture Mask (Arbitrary Shape)")
ax_mask.axis('off')

im_diff = ax_diff.imshow(I_init**0.3, cmap='inferno', origin='lower')  # gamma = 0.3 for visibility
ax_diff.set_title("Diffraction Pattern (I^0.3)")
ax_diff.axis('off')

mid = GRID_SIZE // 2
line_slice, = ax_slice.plot(I_init[mid, :], color='crimson', lw=1.5)
ax_slice.set_title("Horizontal Intensity Profile")
ax_slice.set_ylim(-0.05, 1.05)
ax_slice.grid(True, alpha=0.3)

# --- UI Controls (Sliders & Radio Buttons) ---
ax_slider_wave = plt.axes([0.1, 0.20, 0.4, 0.03])
ax_slider_dist = plt.axes([0.1, 0.13, 0.4, 0.03])
ax_slider_dia  = plt.axes([0.1, 0.06, 0.4, 0.03])
ax_radio       = plt.axes([0.60, 0.05, 0.22, 0.20])

slider_wave = Slider(ax_slider_wave, 'Wavelength (nm)', 400.0, 700.0, valinit=init_wavelength, valfmt='%1.0f nm')
slider_dist = Slider(ax_slider_dist, 'Distance (cm)', 5.0, 50.0, valinit=init_distance, valfmt='%1.1f cm')
slider_dia  = Slider(ax_slider_dia, 'Scale / Dia (mm)', 0.1, 2.0, valinit=init_diameter, valfmt='%1.2f mm')

radio_shape = RadioButtons(ax_radio, ('Single Circle', 'Square', 'Annulus (Ring)', '3-Hole Triplet'), active=0)

# --- Update Callback ---
def update(val):
    wave = slider_wave.val
    dist = slider_dist.val
    dia = slider_dia.val
    shape = radio_shape.value_selected
    
    # Scale mask radius dynamically based on aperture diameter slider
    mask_radius = int(dia * 35) 
    
    new_mask = create_mask(shape, GRID_SIZE, mask_radius)
    new_I = compute_diffraction(new_mask, wave, dist, dia, GRID_SIZE)
    
    im_mask.set_data(new_mask)
    im_diff.set_data(new_I**0.3)
    line_slice.set_ydata(new_I[mid, :])
    
    fig.canvas.draw_idle()

slider_wave.on_changed(update)
slider_dist.on_changed(update)
slider_dia.on_changed(update)
radio_shape.on_clicked(update)

plt.show()
