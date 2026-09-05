"""Golden-angle phyllotaxis generator.

NOT A SEPARATE PATTERN FROM fibonacci_spiral.py -- STATED EXPLICITLY RATHER THAN
SHIPPING TWO GENERATORS THAT ARE SECRETLY THE SAME PATTERN.

"Golden-angle phyllotaxis" (r=c*sqrt(n), theta=n*golden_angle) and the "Fibonacci/Vogel
spiral" this folder's task brief separately named are, mathematically, the identical
formula (Vogel 1979's model IS the golden-angle phyllotaxis construction -- there is no
different standard "Fibonacci spiral" point-packing formula in the literature distinct
from this one; the visually-different "nested-squares Fibonacci spiral" curve is an
unrelated aesthetic construction, not a hole-packing pattern, and is not what either
generator name refers to here).

Rather than duplicate the implementation (and risk the two copies silently drifting
apart under future edits), this file re-exports fibonacci_spiral.generate() under this
module's own name, with family="golden_angle" in the output metadata so downstream
sweep/comparison code can still distinguish rows by requested generator name if it
chooses to -- while the underlying coordinates for the same (N, a_hole_um, c_um) are,
by construction, identical to fibonacci_spiral's own output."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fibonacci_spiral as _fib  # noqa: E402


def generate(N, a_hole_um, c_um):
    return _fib.generate(N, a_hole_um, c_um, family_name="golden_angle")
