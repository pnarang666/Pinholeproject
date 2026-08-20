# Centered Concentric Comparison

## Correction to this experiment's own motivation (found before building anything)

`ring_offset_concentric.py` does **not** skip a center hole "because rings start at
k=1" — both it and `concentric.py` already start their own point list with a literal
`pts = [np.array([0.0, 0.0])]`. Confirmed directly: a naive "prepend (0,0), reuse the
ring loop unchanged" implementation produces **bit-identical** coordinates to
`ring_offset_concentric.generate()` for the same inputs (checked, max diff = 0.0) —
because that is already exactly what it does.

The real reason no hole sits at the origin in the final output is
`base_generator.py`'s own shared `recenter_on_centroid()` step (applied identically
to all 10 families): it shifts the whole pattern by `-mean(all kept points)`. A
**complete** ring always sums to exactly (0,0) by rotational symmetry, so it never
disturbs this; a **truncated** final ring (whenever N doesn't exactly fill an integer
number of complete rings — the common case) does not sum to zero, and the shared
recenter step shifts the nominal center hole away by exactly that imbalance.
Reproduced exactly: `ring_offset_concentric`'s own N=20, ring_spacing_um=4000,
holes_per_ring0=8 candidate (its M=2–3 winner) has its center hole recentred to
**1704.8µm** from the origin — matching the motivating finding precisely.

## The actual fix

`concentric_centered.py` recenters the **ring points on their own centroid first**,
then prepends the (0,0) center hole, then finalizes the combined set. Since the ring
points are already exactly zero-mean before the center hole is added, the combined
mean is exactly (0,0) by construction, and the final `recenter_on_centroid()` call is
provably a no-op — the center hole survives at **exactly** (0,0) regardless of
partial-ring truncation. Verified: **1.6×10⁻¹³µm** displacement for the same N=20
case that displaced `ring_offset_concentric`'s own center hole by 1704.8µm.

**Sanity check** (`concentric_centered.py`, run standalone): overlap_fraction = 1.000000
via `active_pairs.hole_illumination_fractions`/`overlap_area_um2` for both a
complete-ring case (N=9) and the genuinely partial-ring case (N=20) — PASSED.

## A necessary side effect, discovered and verified precisely

Choosing a different recentering reference point doesn't only move the center hole —
it shifts **every other hole** in the pattern by a uniform vector. Derived and
confirmed exactly for the N=20 test case: every one of the 19 ring points shifts by
**(34.34, −82.90)µm, magnitude 89.73µm**, in the same direction, while the center hole
itself moves by 1704.79µm. This is small relative to the 4000µm ring spacing, but the
tested candidates sit at knife-edge margins (`worst_case_ghost_margin = +∞` means
*zero* active pairs — a discrete, combinatorial count that a small shift can flip from
0 to ≥1). This shift is the actual mechanism behind every result below, not a defect
in the new generator.

## Pipeline run (additive, verified)

324 new `concentric_centered` rows appended to `sweep_results.csv` (same N∈{20,50,100},
ring_spacing_um∈{700,1000,1500,2000,3000,4000}, holes_per_ring0∈{6,8} grid
`ring_offset_concentric` uses, imported not duplicated) — **existing 9046 rows
verified byte-identical via checksum** before/after. `compute_density.py` and
`compute_coverage_metrics.py` (both `c_min_um=0` and `c_min_um=55`) re-run — **existing
8501 rows in each output verified value-identical via key-merge** (0 mismatches) before
adding 317–324 new rows (a few candidates were excluded as degenerate, same as every
other family). `degeneracy_filter.py`'s `GEN_FUNCS` and
`compute_coverage_metrics.py`'s `SIMPLE_SPACING_KEY` needed one additive registration
line each (new family, zero changes to existing entries) — neither is on the
do-not-modify list. All prior outputs legacy-preserved.

## Comparison table (c_min_um=0 gate criteria — margin > real threshold, then max effective density)

| M | Candidate | N, spacing | nearest-hole dist | overlap % | blind_rate | ghost margin | vign. margin | eff. density |
|---|---|---|---|---|---|---|---|---|
| 0.0 | ring_offset_concentric (**winner**) | 20, pitch=2000,30° | 0 µm | 100.0% | 0.173 | +∞ | +∞ | 1.815e-08 |
| 0.0 | concentric_centered (best passing gates) | 50, rs=1500,hpr=6 | 85.8 µm | 100.0% | **0.097** | +∞ | +∞ | 9.532e-09 |
| 1.0 | ring_offset_concentric (**winner**) | 20, rs=4000,hpr=8 | 1704.8 µm | 76.3% | 0.113 | +∞ | +∞ | 5.492e-09 |
| 1.0 | concentric_centered | — | — | — | — | — | — | **none pass gates** |
| 2.0 | ring_offset_concentric (**winner**) | 20, rs=4000,hpr=8 | 1704.8 µm | 93.8% | 0.107 | +∞ | +∞ | 5.891e-09 |
| 2.0 | concentric_centered | — | — | — | — | — | — | **none pass gates** |
| 3.0 | ring_offset_concentric (**winner**) | 20, rs=4000,hpr=8 | 1704.8 µm | 93.8% | 0.107 | +∞ | +∞ | 5.891e-09 |
| 3.0 | concentric_centered | — | — | — | — | — | — | **none pass gates** |
| 4.0 | ring_offset_concentric (**winner**) | 20, rs=4000,hpr=8 | 1704.8 µm | 99.9% | 0.105 | +∞ | +∞ | 6.019e-09 |
| 4.0 | concentric_centered | — | — | — | — | — | — | **none pass gates** |
| 5.0 | ring_offset_concentric (**winner**) | 20, rs=4000,hpr=8 | 1704.8 µm | 99.9% | 0.105 | +∞ | +∞ | 6.019e-09 |
| 5.0 | concentric_centered | — | — | — | — | — | — | **none pass gates** |
| 6.0 | ring_offset_concentric (**winner**) | 20, rs=4000,hpr=8 | 1704.8 µm | 100.0% | 0.103 | +∞ | +∞ | 6.107e-09 |
| 6.0 | concentric_centered | — | — | — | — | — | — | **none pass gates** |
| 8.0 | ring_offset_concentric (**winner**) | 20, rs=4000,hpr=8 | 1704.8 µm | 100.0% | 0.101 | +∞ | +∞ | 6.197e-09 |
| 8.0 | concentric_centered | — | — | — | — | — | — | **none pass gates** |

*(M=1–8's ring_offset_concentric row is 93.8–100% overlap, not the flat "93.8%
everywhere" the motivating example implied — computed per M since `resolvable_blur_um`
and the tested phi range interact with which phi is "worst," but the geometry and
nearest-hole distance are M-independent, since ring_offset_concentric's own geometry
doesn't change with M.)*

**Reference — square's M=1 winner** (the `c_min_um=55` table's own winner, N=20,
`pitch_um=2000, rotation_deg=0`, literal center hole): nearest-hole distance = 0µm,
overlap = 100.0%, **blind_rate = 8.2%**, optical ghost/vignetting margin = **−6.59**
(fails outright), floored (`c_min=55`) margin = **+0.128** (passes only under Shen's
perceptual floor), effective_density = 4.162e-08. Included as the task's own reference
point — not re-run, read directly from the already-computed `c_min_um=55` table.

**Under `c_min_um=55` gates**, the picture is the same: `concentric_centered` gains a
few more gate-passing candidates (M=0: 24, M=1: 3, M=2–8: 0) but its best
effective_density is lower than `ring_offset_concentric`'s at every single M where
both have any (M=0: 1.624e-08 vs 3.599e-08; M=1: 3.298e-09 vs 5.492e-09) — checked, not
assumed.

## Verdict: concentric_centered does not win anywhere

**`ring_offset_concentric` remains the winner at every M, under both `c_min_um=0` and
`c_min_um=55`, using the exact same criteria as the existing winner tables.** The
hypothesis (a guaranteed center hole improves overlap and blind_rate, therefore wins)
is **half-confirmed, half-refuted**:

- **Confirmed**: `concentric_centered` genuinely achieves better overlap (100% vs.
  76–99%) and, at M=0, better blind_rate (9.7% vs. 17.3%) than `ring_offset_concentric`'s
  own winning candidate.
- **Refuted as a path to winning**: at every M, `concentric_centered`'s own best
  candidate has lower effective_density than `ring_offset_concentric`'s winner — either
  because the shift needed to realize the exact center hole (see above) pushes
  otherwise-comparable candidates below the margin threshold entirely (M=1–8, `c_min=0`:
  zero `concentric_centered` candidates pass gates at all), or because the candidate that
  *does* pass gates does so at a less N-dense configuration (M=0: N=50 vs. N=20, but a
  much larger ring spacing, netting a lower density despite more holes).

This is a genuine negative result, not a null one: the underlying idea (a
literal, guaranteed center hole) works exactly as intended geometrically, and the
mechanism for why it still doesn't win is fully traced (the recentering-shift side
effect on every other hole) rather than left as "it just didn't." `ring_offset_concentric`
is not being beaten because its "accidental" 1704.8µm-off-center hole happens to be
positioned advantageously relative to the tested phi sweep in a way a perfectly-centered
alternative is not, for the specific candidates in this grid.
