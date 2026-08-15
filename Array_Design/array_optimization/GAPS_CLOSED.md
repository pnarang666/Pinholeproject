# Part A — Five verification gaps, closed

Written before any vignetting code was touched, per this task's own ordering requirement.
None of the five gaps below turned up a problem serious enough to invalidate the prior
defect report; two (Gap 3, Gap 4) turned up things that **were not previously checked**
and are now checked and reported honestly, including where the answer is "no, it
doesn't do that." No stop condition was triggered.

---

## Gap 1 — Physical size of "1 grid pixel" in the M=0 ghost-gate, and whether it's clean

`validate_ghost_formula.py`'s defaults are `grid_N=4096`, `window_L_mm=6.0`. Grid pixel:

```
dx = window_L_mm / grid_N = 6.0 mm / 4096 = 1.46484375 um
```

**Not sub-micron.** It's ~1.46 um — closer to "a few microns" than to "clean, negligible."
The M=0 gate's tolerance is `2*dx = 2.93 um`, and the measured (incoherent, physically-
relevant) residual at M=0 is **exactly `1.46484375` um at all four tested pitches**
(700/1200/2000/3200 um) — bit-identical, not merely close, per
`ghost_formula_validation.csv` rows 1-4.

**Which is it — measurement floor or real propagation asymmetry? Measurement floor.**
Evidence: `two_peak_positions_um()` splits the field at the array's midline and takes
`argmax` of each half independently. At M=0 both holes converge to a single, symmetric,
on-axis peak — there is no real second peak. The two argmax hits therefore always land on
the two grid cells immediately straddling the split boundary, giving a **constant**
1-pixel separation by construction of the method, regardless of pitch or hole geometry.
A genuine numerical propagation asymmetry (e.g. FFT-grid anisotropy, band-limiting edge
effects) would be expected to scale with the physical configuration — and the script's own
**coherent**-propagation column (which legitimately contains interference structure) does
exactly that: `1.46, 7.32, 4.39, 2.93` um across the same four pitches, not constant. The
incoherent column's exact invariance is the tell that it's the split-at-midline detector's
floor, not physics. This was previously asserted but not cross-checked against the
coherent column's own pitch-dependence — doing so now closes the gap: **PASS, and the
2 um-scale residual has an identified, non-physical cause**, not swept under "PASS" alone.

No action required. If a future finer-grained ghost-separation measurement is ever needed
below the ~1.5 um floor, the fix is a sub-pixel peak-detection method (e.g. centroid or
parabolic interpolation around the argmax), not a grid refinement — noted for the record,
not acted on here (out of scope, nothing downstream currently needs sub-pixel precision).

## Gap 2 — Which formula actually won

Recomputed directly from `ghost_formula_validation.csv` (32 points), not quoted from memory:

| formula | form | R² |
|---|---|---|
| (a) legacy | `delta_r = s*v_r/d_gap` | **-1701.711721** |
| (b) corrected | `delta_r = s*M/(P0-M)` | **0.995135** |
| (c) free fit | `delta_r = A*[s*M/(P0-M)] + B` | 0.996787, A=1.041429, B=-2.746592 |

**Winner: candidate (b), `delta_r = s*M/(P0-M)`** (equivalently `s*|v_r-v_f|/v_f` under
the axial eye model — `ghost_separation.delta_r_corrected_um`/`delta_r_corrected_from_M_um`,
confirmed identical). The free fit is *not* a materially different functional form: its
slope A=1.0414 and intercept B=-2.75 both fall inside the script's own pre-registered 5%
consistency band against (b)'s implied A=1, B=0 (`|A-1|=0.041<0.05`; `|B|=2.75 <
max(1.0, 0.05*mean(delta_r))=4.32`) — i.e. the "free" fit independently rediscovers (b),
it does not propose a new formula. **(b) is what is wired into `ghosting_risk.py` and
what every downstream risk/ghosting number in this pipeline uses** — this is now logged
explicitly, not left implicit in a code comment.

## Gap 3 — Was the M=4-8D weight-sensitivity check re-run against the 20 Pareto candidates?

**No, not previously** — `optimise.py`'s `sensitivity()` searches the *entire* 1370-row
grid for the argmin under perturbed weights; it was never restricted to Stage 3's 20
recommended `(a, s, packing)` designs specifically, and Stage 3's Pareto front (built on
`r_EE_50` vs `T` only, gated by a hard risk threshold) doesn't use those weights at all —
so Pareto-membership alone said nothing about weight-robustness. **Run now**
(`gap3_weight_sensitivity_check.csv`, reusing `optimise.py`'s own `cost()` and default
weights `W_BLUR=1, W_DARK=5, W_GHOST=1, W_BRIGHT=1`, `GHOST_CAP=50`, `BRIGHT_REF_PCT=1`):

At M=4D/6D/8D, under default weights, weighted-objective 2x brightness, weighted-objective
0.5x ghost, and the combined ("flip") scenario, the **global** argmin over the full grid
moves exactly as the original sensitivity sweep found: from `a=2000, s=4200, hex`
(N_eff_worst=0, risk=0.0 — one of the 20) under default weights, to `a=2000, s=2200, hex`
(N_eff_worst=1, risk≈98-137 — a real, non-negligible ghosting risk) under every perturbed
scenario tested. **This confirms the original finding is real and reproduces cleanly**, not
a one-off artifact.

The two things that matter for trusting the 20, both now checked directly rather than
inferred:

1. **The fragile design (`a=2000, s=2200`) is not, and under none of these perturbations
   becomes, one of the 20.** `s=2200` never appears among the 20 recommended pitches (all
   20 have `s>=4200`) — because Stage 3's admission gates (`risk < 1.0`,
   `margin_fraction_of_ceiling >= 1.0`) are hard thresholds on measured quantities, not on
   any weighted combination — no value of `w_ghost`/`w_bright` moves a design across either
   gate. This is a structural, not merely empirical, reason the instability can't leak in.
2. **The ranking *within* the 20 is itself stable.** Restricted to just the 20's own rows
   at M=4/6/8D, the same design (`a=2000, s=4200, hex`) is the lowest-cost pick under
   *every one* of the four weight scenarios tested — the internal preference order among
   the 20 doesn't move, only its margin over the (excluded) fragile alternative does.

**Conclusion: checked, not just assumed. Result is a clean pass** — the 20 are robust to
the specific weight perturbation that previously caused a problem, for a structural reason
(hard gates, not weighted scoring) that will hold under other weight values too, not just
the ones tested.

## Gap 4 — Does the safety/margin funnel enforce a transmission target, and is the margin flag baked in?

**Margin flag: yes, baked into the 274→90 cut, not just the 90→20 Pareto step.**
`decide.py`'s own `n_safe` count is `(is_ghosting_safe & ~margin_flag_insufficient).sum()`
— both the hard ghosting-risk gate *and* the pitch-margin-to-ceiling gate are ANDed
together before the Pareto front is ever computed (`decide.py:187`,
`rank_candidates()`). The 90 in "274→90→20" already reflects both conditions.

**OD 0.6-0.8 / T 15-25% transmission target: NOT enforced anywhere in this pipeline, and
not a target this project's own documents specify a number for.** Searched
`IYPT_Pinhole_Master_Formulas_and_Pipeline.md` (R2: "achieve a target light-attenuation
spec" — stated qualitatively, no number given), `THEORY.md`, `ANALYSIS.md`,
`RECOMMENDATION.md`, and `photometry/*.py`: no OD or %T numeric target exists in this
project's own record. `decide.py` computes `T` and uses it only as one *unconstrained*
Pareto-maximization axis — never filtered against any target window. Checked the 20
against the OD 0.6-0.8/T 15-25% band directly since it wasn't gated:

```
T range across the 20 recommended designs: 0.57% - 20.56%
Inside T 15-25%:        3 / 20   (a=1750/s=4200/hex, a=2000/s=4700/hex, a=2000/s=4200/hex)
Inside OD 0.6-0.8 exactly (T 15.8-25.1%): 2 / 20
```

**Most of the 20 (17/20) sit well below a 15-25% transmission band** — some as low as
0.57%, i.e. far darker than a typical sunglass spec. This is stated plainly per this
project's own honesty requirement: **if this transmission target matters for
prototyping, the current `recommended_for_prototyping=True` flag does not check it, and
most of the 20 would fail it.** This is not a new bug — Stage 3 was never built against
this specific numeric target (no prior document in this project stated one for it to be
built against) — but it is a real, previously-undocumented scope gap in what
`recommended_for_prototyping` means, and `array_optimization/README.md` is updated below
to state it in the "does NOT guarantee" list.

## Gap 5 — Is the single-aperture pipeline at the same grid_N as the array pipeline?

**No.** `new_sweeps/run_blur_sweep.py:32` hardcodes `GRID_N = 2048`, and
`new_sweeps/blur_sweep.csv`, `per_M_optimum_map.csv`, `table1_optimum_summary.csv` are all
dated **2026-08-08/09** — before this task's Defect-1 fix (`array_psf_envelope.py`'s
`GRID_N` 2048→4096, applied only to the array-pipeline files, dated **2026-08-15**). The
single-aperture pipeline was never touched by that fix and still carries whatever residual
r_max_lens-type exclusion existed at grid_N=2048 (this project's earlier defect report
already established that grid_N=2048 was measurably too coarse for the pupil-edge case).

**Flagged, not fixed** — out of scope per this task's own instruction and the prior
session's stated decision that a full grid_N audit is too compute-heavy to run
opportunistically.

**Does this corrupt anything vignetting.py will consume? No.** `vignetting.py` (Part B)
consumes the **array** pipeline's outputs (`optimise_grid.csv`, `array_candidates.csv` —
both already regenerated at `grid_N=4096`), not `new_sweeps/*`. The single-aperture files'
stale resolution is a real, open item for anyone using `new_sweeps/table1_optimum_summary.csv`
or `per_M_optimum_map.csv` directly, but it does not sit anywhere in vignetting's input
chain. Noted here so it isn't silently forgotten, not because it blocks Part B.

---

## Verdict

No stop condition triggered. Gaps 1-2 confirm the prior defect report's headline numbers
on re-derivation from raw data (not memory). Gaps 3-4 found real, previously-unchecked
scope limits (the weight-sensitivity check had never been run against the actual 20;
the transmission target was never enforced or even checked against) — both are now
checked, both are reported honestly (one clean pass, one real gap), and neither changes
which 20 designs are on the Pareto front. Gap 5 confirms a known, already-flagged
resolution mismatch in a *different* pipeline that does not feed vignetting. Proceeding
to Part B.
