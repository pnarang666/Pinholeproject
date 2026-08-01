# Changes from stage2/

1. **sweep_myopia.py, `finalize_row()`** — energy-conservation bug fix.
   Was comparing discrete output power against a continuous reference area
   (`pi*(a_hole/2)^2`), which silently mixed a ~0.05-0.35% pixelation artifact
   into a column that's supposed to measure ASM propagation fidelity. Now
   compares against the actual discrete input power of the rasterized
   aperture (`sum|U0|^2*dx^2`, matching how stage1_v2/physics.py does it).
   This was the fix you asked for.

2. **pipeline_junction.py, `validate_junction()`** — wraparound check
   correction, done at the same time since it was in the same review.
   The pre-lens divergence estimate used the Gaussian-beam (M^2=1) minimum
   divergence formula, mislabeled as "conservative". It's actually a lower
   bound, not an upper one -- real hard-aperture fields diverge at least as
   fast. Added a margin_factor=3.0 as a documented, visible first-pass
   safety inflation (not a validated bound -- said so in the docstring).
   If this check becomes load-bearing, replace margin_factor with the
   field's own measured divergence instead of trusting a fixed multiplier.

Everything else is byte-identical to stage2/. Not run/tested here (no
execution access to your machine from this session) -- run
`python3 validation_gate.py` first thing, same as before.
