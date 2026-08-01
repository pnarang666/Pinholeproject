import numpy as np
import matplotlib.pyplot as plt
from scipy.special import jv  # Bessel function of order 1

def generate_diffraction_pattern(wavelength=555e-9, aperture_diameter=1e-3, 
                                 distance=0.1, grid_size=500, screen_width=3e-3):
    """
    Computes 2D Airy disk diffraction pattern for a circular aperture.
    
    Parameters:
    - wavelength: Light wavelength in meters (555 nm green by default)
    - aperture_diameter: Hole diameter D in meters (1 mm by default)
    - distance: Propagation distance z to screen in meters (10 cm by default)
    - grid_size: Resolution of spatial grid (N x N)
    - screen_width: Total physical width of screen array in meters
    """
    # 1. Generate spatial meshgrid on screen (in meters)
    coord = np.linspace(-screen_width / 2, screen_width / 2, grid_size)
    X, Y = np.meshgrid(coord, coord)
    R = np.sqrt(X**2 + Y**2)
    
    # 2. Dimensionless radial coordinate u
    u = (np.pi * aperture_diameter * R) / (wavelength * distance)
    u = np.where(u == 0, 1e-12, u)  # Prevent division by zero at center
    
    # 3. Calculate normalized intensity I / I_0
    intensity = (2.0 * jv(1, u) / u)**2
    
    return X * 1e3, Y * 1e3, intensity  # Convert spatial coordinates to mm

# --- Execute Simulation ---
x_mm, y_mm, I = generate_diffraction_pattern(
    wavelength=555e-9,        # 555 nm photopic green
    aperture_diameter=0.8e-3,  # 0.8 mm pinhole
    distance=0.15,            # 15 cm screen distance
    screen_width=4e-3         # 4 mm viewing region
)

# --- Plot Results ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

# Plot 1: 2D Intensity (Gamma corrected I^0.3 so outer rings are visible)
im = ax1.imshow(I**0.3, extent=[x_mm.min(), x_mm.max(), y_mm.min(), y_mm.max()],
                cmap='inferno', origin='lower')
ax1.set_title("2D Airy Pattern (Gamma-Enhanced)")
ax1.set_xlabel("x position (mm)")
ax1.set_ylabel("y position (mm)")

# Plot 2: 1D Center Slice Profile
mid = I.shape[0] // 2
ax2.plot(x_mm[mid, :], I[mid, :], color='crimson', lw=2)
ax2.axhline(0.0175, color='gray', linestyle='--', alpha=0.6, label='1st Ring Peak (~1.75%)')
ax2.set_title("1D Intensity Profile Across Center")
ax2.set_xlabel("x position (mm)")
ax2.set_ylabel("Normalized Intensity I/I_0")
ax2.set_ylim(-0.02, 1.05)
ax2.grid(True, alpha=0.3)
ax2.legend()

plt.tight_layout()
plt.show()
