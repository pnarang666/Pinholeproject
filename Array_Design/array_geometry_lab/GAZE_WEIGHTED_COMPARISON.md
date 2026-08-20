# Gaze-Weighted Comparison

A **parallel** metric, additive only — the existing worst-case-across-phi gates
(`array_evaluation/comparison_metric/gates.py`, `effective_density_ranking.py`) are
untouched and still the project's primary ranking. This asks a different question:
not "is there any tested gaze angle where this design fails" (worst-case, unweighted —
treats φ=25°, ~0.6% of viewing time, as heavily as φ=0°), but "what fraction of actual
viewing time is this design blind or ghosting," using the given empirical eccentricity
distribution (not fitted, not assumed).

**Weight verification** (`compute_gaze_weighted_metrics.py`, run before any sweep):
sum = 100.0000 (expect 100.0), cumulative by 6° = 51.6100 (expect 51.61), cumulative by
17° = 95.2700 (expect 95.27) — all three PASSED exactly.

**Azimuthal sampling** (36 azimuths/eccentricity bin, 26 bins = 936 samples/candidate,
run over the full 8818-row candidate set including `concentric_centered`): essential,
not decorative — confirmed directly (see below) that a candidate can be fully dark at
one azimuth of a given eccentricity and fully lit at another azimuth of the *same*
eccentricity, which this project's existing single-axis (+x only) sweep cannot see by
construction.

## Does the winner change?

**Yes, at every M** (0–8 and global) — but the mechanism needs stating precisely, not
just the yes/no: **both the worst-case winner and the gaze-weighted winner have
`worst_case_ghost_margin = worst_case_vignetting_margin = +∞`** at every M. The
worst-case pipeline was never wrong about either design's safety — the two rankings
optimize genuinely different objectives (max effective_density among margin-safe
survivors vs. min time-weighted ghost%, blind% tiebreak), so a different winner is the
expected outcome of asking a different question, not evidence the old winner was
secretly unsafe.

**Important caveat on "winner," found while building the table**: at low-to-mid M, a
*large* tied plateau of candidates reach exactly 0.0% / 0.0% (ghost/blind) — e.g. at
M=2.0, `hexagonal` (N=20/50/100), `jittered_lattice` (3 seeds), and others all tie at
0.0/0.0. The single "winner" row is one representative of that tie, picked by
insertion order, not a uniquely-best design — reported honestly rather than implying a
sharper distinction than the data supports.

## Per-M comparison

| M | Worst-case winner | ghost%/blind% | Gaze-weighted winner | ghost%/blind% | Both worst-case margins |
|---|---|---|---|---|---|
| 0.0 | hexagonal, N=20, pitch=2000,30° | 9.16% / 0.31% | **square, N=20, pitch=4000** | **0.00% / 0.00%** | both +∞/+∞ |
| 1.0 | ring_offset_concentric, N=20, rs=4000,hpr=8 | 7.37% / 0.00% | **hexagonal, N=20, pitch=4000** | **0.00% / 0.00%** | both +∞/+∞ |
| 2.0 | ring_offset_concentric, N=20, rs=4000,hpr=8 | 7.58% / 0.03% | **hexagonal, N=20, pitch=4000** | **0.00% / 0.00%** | both +∞/+∞ |
| 3.0 | ring_offset_concentric, N=20, rs=4000,hpr=8 | 7.58% / 0.03% | **hexagonal, N=20, pitch=4000** | **0.00% / 0.00%** | both +∞/+∞ |
| 4.0 | ring_offset_concentric, N=20, rs=4000,hpr=8 | 7.74% / 0.04% | **hexagonal, N=20, pitch=4000** | **0.00% / 0.00%** | both +∞/+∞ |
| 5.0 | ring_offset_concentric, N=20, rs=4000,hpr=8 | 7.74% / 0.04% | **hexagonal, N=20, pitch=4000** | **0.00% / 0.00%** | both +∞/+∞ |
| 6.0 | ring_offset_concentric, N=20, rs=4000,hpr=8 | 7.74% / 0.11% | **hexagonal, N=100, pitch=4000** | **0.00% / 0.12%** | both +∞/+∞ |
| 8.0 | ring_offset_concentric, N=20, rs=4000,hpr=8 | 7.87% / 0.27% | **hexagonal, N=50, pitch=4000** | **0.00% / 0.33%** | both +∞/+∞ |
| global | hexagonal, N=20, pitch=2000,30° | 9.16% / 0.31% | **square, N=20, pitch=4000** | **0.00% / 0.00%** | both +∞/+∞ |

No degenerate "wins by being permanently dark" case was found (checked directly, not
assumed — `gaze_weighted_ranking.py` flags this automatically): every gaze-weighted
winner above has `time_weighted_blind_pct` at or near 0%, so its 0% ghost_pct reflects
genuine safety, not an opaque design gaming the ascending-ghost-then-blind sort.

**A pattern worth naming**: every gaze-weighted winner uses `pitch_um=4000` — the
*sparsest* tested spacing for its family. This is not a coincidence: sparse lattices
place holes far enough apart that no azimuth at any tested eccentricity brings two
holes simultaneously active, and the pupil (4mm) is still large enough relative to the
gaps that blackouts stay rare too. The worst-case pipeline's own winners favor denser
packings (optimizing density among survivors) that happen to tolerate the single
worst-case direction it tests; time-weighting doesn't reward density at all, so it
settles on the geometrically safest, not the densest, layout.

## Does `concentric_centered` become competitive?

**Confirmed and refined, not just confirmed.** Directly regenerated its N=20,
ring_spacing_um=4000, holes_per_ring0=6 candidate (its own best under gaze-weighting)
and swept the existing single-axis φ grid:

| φ | −25° | −20° | −15° | −10° | −5° | 0° | +5° | +10° | +15° | **+20°** | +25° |
|---|---|---|---|---|---|---|---|---|---|---|---|
| illuminated area (µm²) | **0 (BLIND)** | 327937 | 305178 | 5663 | 441786 | 441786 | 441786 | 345198 | 280945 | **0 (BLIND)** | 427374 |

The worst-case gate fails this candidate via `min_illuminated_area_um2_across_phi = 0`
— a real blackout, exactly as claimed — but it occurs at **φ=−25° and φ=+20°
specifically, not at +25° or −20°**: direction-dependent, exactly the "blackout in the
gap between ring holes, not along the radial direction" phenomenon this task's own
azimuthal sampling was built to catch. The existing single-axis sweep happens to graze
a gap at two of its eleven tested points and a hole at the other nine — a fragile,
alignment-dependent result the azimuthal average smooths out.

Under gaze-weighting: this same candidate scores `time_weighted_ghost_pct` = 2.17–4.75%
and `time_weighted_blind_pct` = 0.01–3.47% across M=1–8 — **a real, low, rankable
number**, a sharp change from the worst-case pipeline's *zero* viable
`concentric_centered` candidates at every M≥1 (confirmed in the prior task). It is
**competitive in the sense that it is no longer categorically excluded** — but it does
**not win anywhere**: at every M, several other candidates (mostly `hexagonal` and
`jittered_lattice` at `pitch_um=4000`) reach exactly 0.00% ghost, beating
`concentric_centered`'s 2–5% outright. Reported honestly: the hypothesis that gaze
weighting would make `concentric_centered` *win* is not supported by the data — it
substantially rehabilitates the family without making it the best available choice.

## Summary

The gaze-weighted winner differs from the worst-case winner at every M, but not
because gaze-weighting exposed a hidden flaw in the worst-case winners — both winners
are equally `+∞`-margin-safe under the existing gates either way. The two metrics
simply optimize different things (density-among-survivors vs. time-weighted
ghost/blind), and a large tied plateau of designs (mostly sparse, `pitch_um=4000`
layouts) achieve a genuine 0%/0% under time-weighting regardless of family.
`concentric_centered` is real, meaningful evidence that a candidate this project's hard
gate rejects outright can be substantially safer than that rejection implies once gaze
is weighted by actual viewing time — but it still loses to designs that reach true
0% under either metric.
