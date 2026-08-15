"""
The retinal ghost separation delta_r: legacy formula, corrected formula, and the
first-principles derivation of both. Added during the Array_Design consolidation
(Step 2) -- it does NOT modify ghosting_regime.py's own ghost_ripple_frequency(),
which still implements the legacy formula exactly as Passes 1-3 used it, so every
number in RESULTS.md Passes 1-3 remains reproducible.

====================================================================================
THE QUESTION
====================================================================================
THEORY.md Eq. (1), used by every pass of the ghosting analysis so far and by
photometry/array_photometry.py::no_ghost_max_pitch(), states that two holes at pitch
s produce retinal copies of a DISTANT scene point separated by

    delta_r_legacy = s * v_r / d_gap                                            (L)

with v_r the retina distance and d_gap the array-to-cornea distance. The competing
candidate, matching this project's own Formula #5 defocus factor (r_geo =
(a_stop/2)*|v_r - v_f|/v_f, stage2/classical_formulas.py), is

    delta_r_corrected = s * |v_r - v_f| / v_f  =  s * M / (P0 - M)               (C)

====================================================================================
DERIVATION FROM FIRST PRINCIPLES (paraxial ray optics, on-axis distant object)
====================================================================================
Object at infinity, on axis => every ray reaching the eyewear is parallel to the
optical axis. A hole at transverse height h in the array plane passes the narrow
ray bundle whose height is h. Because those rays are parallel to the axis, they are
STILL at height h when they arrive at the eye's refracting plane a distance d_gap
later (this is why d_gap cannot appear in the answer for an on-axis object -- a
parallel ray does not change height in a drift).

Defining property of the rear focal point: a lens of focal length v_f sends EVERY
incident ray that is parallel to the axis through the rear focal point F' on the
axis, at distance v_f behind the lens. So the ray entering at height h leaves the
lens, crosses the axis at z = v_f, and continues straight. A straight line through
(z=0, y=h) and (z=v_f, y=0) is

    y(z) = h * (1 - z / v_f)                                                     (1)

The retina sits at z = v_r (axial myopia model: the eye's power, hence v_f = f_eye =
n'/P0, is FIXED; only v_r = n'/(P0 - M) grows -- myopia_axial.py). Substituting:

    y(v_r) = h * (1 - v_r / v_f) = -h * (v_r - v_f) / v_f                        (2)

Two adjacent holes at heights h and h+s therefore land at retinal positions
separated by

    delta_r = |y(v_r; h+s) - y(v_r; h)| = s * |v_r - v_f| / v_f                  (C)

and with v_r = n'/(P0-M), v_f = n'/P0:

    (v_r - v_f)/v_f = [n'/(P0-M) - n'/P0] * P0/n' = M / (P0 - M)                 (3)

    ==> delta_r_corrected = s * M / (P0 - M)                                     (C')

M = 0 SUBSTITUTION (the physically required check):
    (C)  at M=0: v_r = v_f exactly  =>  delta_r = s * 0 / v_f = 0.        VANISHES.
    (L)  at M=0: v_r = v_f = n'/P0 = 22.27mm, d_gap = 12mm
                 =>  delta_r = s * 1.856  !=  0.                      DOES NOT VANISH.
An emmetropic eye images a distant point to a single point no matter how many holes
admit light -- all the bundles converge on the same rear focal point, Eq. (1) with
z = v_f. (L) predicts ghost copies 1.86 pitches apart for an eye with no defocus at
all, which is false. (L) is therefore not the separation of ghost images of a
distant scene point.

WHAT (L) ACTUALLY IS: v_r/d_gap is the transverse magnification of an object AT the
array plane imaged onto the retina, i.e. the retinal size of a projected image of
the hole pattern itself. That is a different physical quantity (and it is not
realizable here either: an object 12mm in front of a 60D eye has vergence
-83.3D + 60D = -23.3D, a virtual image, so the array plane is nowhere near
conjugate to the retina). Nothing in Eq. (2)'s geometry produces it.

CONSISTENCY CHECK AGAINST THE REST OF THE PROJECT: dividing (C) by the geometric
blur diameter of one hole, a_stop * |v_r - v_f| / v_f (Formula #5 x2),

    delta_r / blur_diameter = s / a_stop                                         (4)

i.e. the defocused retinal image of a distant point is just a scaled image of the
aperture-plane transmission function -- the standard result that a defocus blur
circle is a demagnified image of the aperture. (L) is inconsistent with Formula #5
(it would make that ratio (s/a_stop) * (v_r/d_gap) * (v_f/(v_r-v_f)), i.e. myopia-
dependent, for a purely geometric shadow relation that cannot be).

VERIFIED NUMERICALLY, not just algebraically: delta_r_derivation_check.py propagates
a laterally displaced hole through this project's own unmodified wave-optics chain
(stage2_fixed/pipeline_junction.py + phase2_retina.py) and measures where the retinal
spot actually lands. See that script's output table.

====================================================================================
SCOPE / LIMITS OF (C)
====================================================================================
- On-axis object point. For an off-axis field angle theta the ray at the array plane
  arrives at the eye plane at height h + d_gap*tan(theta) -- this shifts WHICH holes
  are inside the pupil (the unimplemented R4/R5 vignetting/gaze problem) but shifts
  every hole by the same amount, so delta_r itself is unchanged to first order.
- Paraxial, reduced-eye (single refracting plane), same assumptions as the rest of
  Phase 2 (see phase2_retina.py's PHYSICS_AUDIT E1 note).
- Sign: Eq. (2) is negative -- the retinal pattern is inverted relative to the hole
  lattice. Only |delta_r| matters for a periodicity, so the sign is dropped below.
"""
import numpy as np


def delta_r_legacy_um(pitch_um, v_r_um, d_gap_um):
    """THEORY.md Eq. (1) as used by Passes 1-3: delta_r = s * v_r / d_gap.
    Kept so the legacy numbers stay reproducible -- see this module's docstring for
    why it is not the separation of ghost images of a distant point."""
    return pitch_um * (v_r_um / d_gap_um)


def delta_r_corrected_um(pitch_um, v_r_um, v_f_um):
    """Eq. (C): delta_r = s * |v_r - v_f| / v_f. Vanishes at v_r = v_f (M=0)."""
    return pitch_um * abs(v_r_um - v_f_um) / v_f_um


def delta_r_corrected_from_M_um(pitch_um, M_diopters, P0=60.0):
    """Eq. (C'): the same quantity written in terms of myopia only, s * M/(P0-M).
    Identical to delta_r_corrected_um() under the axial model (myopia_axial.py);
    both are provided so the identity can be checked, not assumed."""
    return pitch_um * M_diopters / (P0 - M_diopters)


def um_per_degree(v_r_um):
    """Retinal micrometres subtended by one degree of visual angle (small-angle),
    identical to the conversion already used in metrics_mtf.py."""
    return v_r_um * (np.pi / 180.0)


def f0_from_delta_r(delta_r_um, v_r_um):
    """Ghost-comb fundamental frequency as (cycles/um at the retina, cycles/degree).
    Same convention as ghosting_regime.ghost_ripple_frequency(), so the two are
    directly comparable; only the delta_r fed in differs."""
    if delta_r_um <= 0:
        return float("inf"), float("inf")
    f0_cpum = 1.0 / delta_r_um
    return f0_cpum, f0_cpum * um_per_degree(v_r_um)


def legacy_equivalent_pitch_um(pitch_um, v_r_um, v_f_um, d_gap_um):
    """
    The pitch that, fed to the LEGACY formula, reproduces the CORRECTED delta_r:

        s_equiv * v_r/d_gap  ==  s * |v_r-v_f|/v_f
        s_equiv = s * (|v_r-v_f|/v_f) * (d_gap/v_r)

    Purpose: harmonic_analysis.harmonic_margin_profile() uses `pitch_um` for exactly
    one thing -- computing f0 through the legacy formula (verified by reading it: no
    other use). Passing s_equiv therefore runs that function, byte-for-byte unchanged,
    at the corrected ghost frequency. The corrected harmonic sweep reuses the existing
    validated harmonic code this way instead of duplicating it, so any difference
    between the legacy and corrected harmonic results is provably the delta_r formula
    and nothing else. NEVER pass s_equiv to anything that uses pitch geometrically
    (N_eff / packing / photometry) -- it is a frequency-equivalent pitch, not a real one.
    """
    return pitch_um * (abs(v_r_um - v_f_um) / v_f_um) * (d_gap_um / v_r_um)
