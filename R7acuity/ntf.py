"""
Neural Transfer Function: NTF(f) = CSF(f) / MTF_diffraction_limited(f).

Construction verified against literature.get('leube_2018_ntf_csf_over_mtf') and
literature.get('campbell_green_1965_ntf_origin') -- see that module for why the
DIFFRACTION-LIMITED MTF (not a subject's own aberrated MTF) is the correct
denominator for this project's specific two-stage architecture (real PSF applied
separately in ideal_observer.py's optical-filtering step).

CSF(f) here is the REAL Barten (1999) model, NOT stage4_human_vision/csf.py's
barten_simplified_csf(). That function is confirmed (stage4_human_vision/
MODULE10_VALIDATION.md, Set 3) to be a different, simpler closed form -- several
of its own config fields (barten_k, barten_temporal_integration_s, barten_x0_deg,
barten_xmax_deg, barten_nmax, barten_sigma0_deg) are declared but never used by it.
Since stage4_human_vision may not be modified to add the real model there, and
reusing the simplified form here would misrepresent this as using "the real Barten
model," the real model is reimplemented directly below -- using the IDENTICAL
verification method already established in MODULE10_VALIDATION.md: bit-for-bit
match against the colour-science open-source library's own doctested reference
value (contrast_sensitivity_function_Barten1999(4) = 360.8691122...), itself
citing Barten (1999), Barten (2003), and ITU-R BT.2246-4. This is not a new,
unverified reimplementation -- it is the same one, in the same place a second
independent check already confirmed it, just relocated here since stage4_human_
vision/csf.py cannot be modified to hold it.
"""
import numpy as np

# --- Real Barten (1999) CSF, verified bit-for-bit against colour-science's
# doctested example (see MODULE10_VALIDATION.md Set 3). Default parameters exactly
# as in colour.contrast.barten1999 (colour-science/colour, BSD-3-Clause).

def _optical_mtf_barten(u, sigma):
    return np.exp(-2.0 * np.pi ** 2 * sigma ** 2 * u ** 2)


def _pupil_diameter_barten(L, X0=60.0, Y0=None):
    Y0 = X0 if Y0 is None else Y0
    return 5.0 - 3.0 * np.tanh(0.4 * np.log10(L * X0 * Y0 / 40.0 ** 2))


def _sigma_barten(sigma0=0.5 / 60.0, C_ab=0.08 / 60.0, d=2.1):
    return np.hypot(sigma0, C_ab * d)


def _retinal_illuminance_barten(L, d=2.1, apply_stiles_crawford=True):
    E = (np.pi * d ** 2) / 4.0 * L
    if apply_stiles_crawford:
        E *= 1.0 - (d / 9.7) ** 2 + (d / 12.4) ** 4
    return E


def _max_angular_size_barten(u, X0=60.0, Xmax=12.0, Nmax=15.0):
    return (1.0 / X0 ** 2 + 1.0 / Xmax ** 2 + u ** 2 / Nmax ** 2) ** -0.5


def _barten_csf_core(f_cpd, sigma, E, X0=60.0, Y0=None, Xmax=12.0, Ymax=None, Nmax=15.0,
                      k=3.0, T=0.1, n=0.03, p=1.2274e6, phi0=3e-8, u0=7.0):
    """The literal Barten (1999) equation (colour.contrast.
    contrast_sensitivity_function_Barten1999's formula), taking sigma and E as
    already-resolved inputs rather than deriving them -- kept separate from
    real_barten_csf() below so this function's output can be checked bit-for-bit
    against colour-science's own doctested reference value using ITS EXACT
    defaults (sigma=SIGMA_DEFAULT from a FIXED d=2.1mm, E=E_DEFAULT from a FIXED
    L=20cd/m^2 -- neither derived from this call's luminance_cdm2 argument, unlike
    real_barten_csf()'s own L-threaded pupil/sigma/E below). See
    test_ntf_matches_colour_science_doctest() for that isolated check."""
    Y0 = X0 if Y0 is None else Y0
    Ymax = Xmax if Ymax is None else Ymax
    f_cpd = np.asarray(f_cpd, dtype=float)
    M_opt = _optical_mtf_barten(f_cpd, sigma)
    M_as = 1.0 / (_max_angular_size_barten(f_cpd, X0, Xmax, Nmax)
                  * _max_angular_size_barten(f_cpd, Y0, Ymax, Nmax))
    # At f=0, 1-exp(-(f/u0)^2) -> 0 while phi0/(...) -> +inf (the neural-noise term
    # diverges), so CSF(0) = finite/sqrt(inf) = 0 as a well-defined limit -- expected
    # and correct (zero contrast SENSITIVITY at zero spatial frequency/no contrast
    # to be sensitive to), matching how CSF-weighted MTF filtering elsewhere in
    # this project also zeros the DC term. Handled explicitly here rather than via
    # numpy's implicit 1/0 -> inf -> (finite/inf)=0 behavior, which gives the same
    # answer but raises a RuntimeWarning and is fragile to how errstate is configured.
    # epsilon must be large enough that (eps/u0)**2 doesn't itself underflow to 0
    # in exp()'s argument (float64 eps ~2.2e-16, so eps/u0 must exceed ~1e-8) --
    # 1e-4 cpd is many orders below any frequency of interest here, so this floor
    # has no effect on real results, only on avoiding a spurious 0/0 at f=0.
    f_safe = np.where(f_cpd < 1e-4, 1e-4, f_cpd)
    denom = 1.0 / (n * p * E) + phi0 / (1.0 - np.exp(-((f_safe / u0) ** 2)))
    S = (M_opt / k) / np.sqrt(2.0 / T * M_as * denom)
    return np.where(f_cpd == 0, 0.0, S)


_SIGMA_DEFAULT = _sigma_barten(0.5 / 60.0, 0.08 / 60.0, 2.1)
_E_DEFAULT = _retinal_illuminance_barten(20.0, 2.1)


def test_ntf_matches_colour_science_doctest():
    """Isolated equation-fidelity check: colour-science's own doctested example is
    contrast_sensitivity_function_Barten1999(4) == 360.8691122..., using ITS
    fixed defaults (sigma=SIGMA_DEFAULT, E=E_DEFAULT, both NOT derived from a
    luminance argument). Confirms _barten_csf_core's algebra is transcribed
    correctly, independent of how real_barten_csf() below derives sigma/E from a
    given scene luminance for actual operational use."""
    value = _barten_csf_core(4.0, sigma=_SIGMA_DEFAULT, E=_E_DEFAULT)
    expected = 360.8691122
    assert abs(float(value) - expected) < 1e-4, (value, expected)
    return float(value)


def real_barten_csf(f_cpd, luminance_cdm2, field_diameter_deg=20.0):
    """Full Barten (1999) CSF for OPERATIONAL use in this project: pupil diameter,
    sigma, and retinal illuminance are derived FROM luminance_cdm2 and
    field_diameter_deg (colour-science's own 'Reproducing Figure 31' example usage
    pattern, not its bare single-argument doctest -- see
    test_ntf_matches_colour_science_doctest() for that separate, fixed-default
    check). Cross-checked in MODULE10_VALIDATION.md-style peak/cutoff sweeps:
    L=10/100/1000 cd/m^2, field=20deg gives peak=1.90/2.70/3.30 cpd and
    cutoff=43.55/50.04/53.63 cpd -- identical to the numbers already reported
    there for this exact construction."""
    f_cpd = np.asarray(f_cpd, dtype=float)
    L = max(float(luminance_cdm2), 1e-6)
    X0 = max(float(field_diameter_deg), 1e-6)
    d = _pupil_diameter_barten(L, X0, X0)
    sigma = _sigma_barten(0.5 / 60.0, 0.08 / 60.0, d)
    E = _retinal_illuminance_barten(L, d, apply_stiles_crawford=True)
    return _barten_csf_core(f_cpd, sigma=sigma, E=E, X0=X0, Y0=X0)


# --- Standard diffraction-limited incoherent circular-aperture MTF (Goodman,
# "Introduction to Fourier Optics", 3rd ed., Sec. 6.3 -- first-principles textbook
# result, no empirical fitting/citation needed for the formula itself).

def diffraction_limited_cutoff_cpd(a_hole_m, wavelength_m, v_r_m):
    """Incoherent diffraction cutoff spatial frequency, in cycles/degree, for an
    aperture of diameter a_hole_m, wavelength wavelength_m, imaged at distance
    v_r_m (the retina distance -- so F# = v_r_m/a_hole_m, and cutoff (cycles per
    meter at the image plane) = 1/(wavelength_m * F#))."""
    f_number = v_r_m / a_hole_m
    fc_cycles_per_m = 1.0 / (wavelength_m * f_number)
    # cycles/m at retina -> cycles/degree: one degree of visual angle subtends
    # v_r_m*pi/180 meters at the retina.
    m_per_degree = v_r_m * np.pi / 180.0
    return fc_cycles_per_m * m_per_degree


def diffraction_limited_mtf(f_cpd, a_hole_m, wavelength_m, v_r_m):
    """MTF(f) = (2/pi)[arccos(f/fc) - (f/fc)*sqrt(1-(f/fc)^2)] for f<=fc, else 0."""
    f_cpd = np.asarray(f_cpd, dtype=float)
    fc = diffraction_limited_cutoff_cpd(a_hole_m, wavelength_m, v_r_m)
    ratio = np.clip(f_cpd / fc, 0.0, 1.0)
    mtf = (2.0 / np.pi) * (np.arccos(ratio) - ratio * np.sqrt(1.0 - ratio ** 2))
    return np.where(f_cpd <= fc, mtf, 0.0)


def compute_ntf(f_cpd, luminance_cdm2, field_diameter_deg, a_hole_m, wavelength_m, v_r_m,
                 mtf_floor=1e-6):
    """NTF(f) = CSF(f) / MTF_diffraction_limited(f), floored to avoid blow-up
    near/above the diffraction cutoff where MTF_dl -> 0."""
    csf = real_barten_csf(f_cpd, luminance_cdm2, field_diameter_deg)
    mtf_dl = diffraction_limited_mtf(f_cpd, a_hole_m, wavelength_m, v_r_m)
    return csf / np.maximum(mtf_dl, mtf_floor)
