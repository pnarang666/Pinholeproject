# Gaze-usage distribution sensitivity: uniform placeholder vs cited gaussian_centered

Compares the two `w(phi)` options `vignetting.py` now implements, run against the same 20
Stage-3 Pareto candidates, same phi sweep (-25 to 25deg, 5deg step), same
`alignment_n_offsets=15`:

- **`uniform`** (unchanged placeholder, +/-15deg): `array_candidates_field_averaged_uniform_placeholder_legacy.csv`
- **`gaussian_centered`** (new, sigma=6.0deg, cited): `array_candidates_field_averaged.csv`
  (current file — the `uniform` run was preserved under the `_legacy` name above *before*
  this overwrote it, per this project's audit-trail convention)

Sourcing for `gaussian_centered` (full detail in `vignetting.py`'s module docstring):
mean saccade amplitude ~4.4+/-1.3deg during free-viewing of natural scenes (Boston
Univ/Cornell group), a measured center-bias in fixation density during natural
scene/movie viewing (Dorr et al. 2010, *J. Vision*), and this project's own Handbook 2
Sec 13.1 validity range (|phi|<~20-30deg) as consistency support. **This is a proxy for
gaze usage, not a direct measurement of dwell time while wearing pinhole sunglasses** —
stated here again because that distinction must not get lost in this comparison.

## Result: the robustness finding holds under BOTH distributions

| check | uniform | gaussian_centered |
|---|---|---|
| Any candidate's `ranking_changed` (Pareto-front membership, static vs field-averaged T) | **False** (0/20) | **False** (0/20) |
| All 20 on the Pareto front, static (phi=0) | True (20/20) | True (20/20) — same input |
| All 20 on the Pareto front, field-averaged T | True (20/20) | True (20/20) |
| `T_field_over_T_static_pct` range across the 20 | 99.918% – 100.184% | 99.924% – 100.163% |
| Max \|difference in `T_field_over_T_static_pct`\| between the two distributions | — | **0.0205 percentage points** (500um/4700um/square) |
| Mean \|difference\| across the 20 | — | **0.0051 percentage points** |

**No candidate changes Pareto-front membership under either distribution, and the two
distributions' own field-averaged transmission numbers agree with each other to within
~0.02 percentage points.** This is a materially stronger claim than the uniform-only
result reported previously: it is not merely that one particular (unsourced) weighting
choice happens to leave the ranking unchanged, but that two distributions with a very
different shape (flat over +/-15deg vs peaked at 0 with sigma=6deg) — including the one
grounded in external literature — agree with each other almost exactly, on top of both
individually agreeing with the static baseline. Reported plainly because it came out
this way, not because it was expected; see below for why it is expected on separate
mathematical grounds, which the agreement itself now confirms empirically rather than
just algebraically.

## Why the population-mean T is essentially insensitive to w(phi) shape here

`T_field_averaged` is a *ratio of population means* (mean over ~225 alignment offsets,
each phi-integrated), and the alignment sweep already covers one full lattice period.
Averaging a spatially-periodic quantity over a full period is close to translation-
invariant under *any* bounded, reasonably-smooth weighting `w(phi)` — uniform, gaussian,
or otherwise — for exactly the reason documented in `vignetting.py`'s own
`apply_to_candidates()` comment. The near-identical results under two very different
`w(phi)` shapes is the expected consequence of that property, not a coincidence specific
to these two choices; it does **not** mean gaze angle has no physical effect on any
individual wearer (see below).

## Secondary finding: still present, and comparable in size across both distributions

The individual-wearer effect reported previously — several candidates whose worst-case
pupil alignment sees zero light at primary gaze (`N_eff_worst_static_phi0=0`) show
non-zero `N_eff_worst_field_averaged` once that wearer's own gaze range is integrated —
holds under `gaussian_centered` too, at a comparable (slightly smaller, as expected from
a narrower, more origin-peaked weighting) magnitude:

| candidate (N/s/pattern) | N_eff_worst static (phi=0) | N_eff_worst field-avg, uniform | N_eff_worst field-avg, gaussian_centered |
|---|---|---|---|
| 400/4200/hex | 0.000 | 0.649 | 0.579 |
| 500/4200/hex | 0.000 | 0.643 | 0.589 |
| 600/4200/hex | 0.000 | 0.647 | 0.606 |
| 700/4200/hex | 0.000 | 0.662 | 0.629 |
| 750/4200/hex | 0.000 | 0.670 | 0.640 |
| 1000/4200/hex | 0.125 | 0.674 | 0.656 |
| 2000/4200/hex | 0.612 | 0.719 | 0.718 |

(Full 20-candidate comparison in the two source CSVs; the pattern above — gaussian
values consistently a bit below uniform's, since a sigma=6deg peak concentrates weight
closer to phi=0 than a flat +/-15deg window does — holds across all rows.)

## Conclusion

Both the "no ranking change" headline finding and the "gaze movement can partially light
up an otherwise-dark alignment" secondary finding are now confirmed under two
distributions with different shapes, one of them grounded in external literature rather
than an arbitrary placeholder. Reported as a materially stronger robustness claim than
before, not because a stronger claim was the goal, but because that is what running the
comparison actually showed.
