# Presentation Decisions Log

Authoritative record of structural decisions for the IYPT deck. Supersedes
`SLIDE_DECK_SPEC.pdf` wherever they conflict. Last updated: 2026-09-09.

---

## D1. The objective is ACUITY, not blur radius

**Decision:** The project's optimisation objective is maximised visual acuity
(minimised logMAR), computed by `mtf10_vsotf_brightness_adjusted`. Blur radius
`r_EE(50%)` is a superseded proxy.

**Why it matters:** Brightness is *not* an external constraint bolted onto a blur
optimisation. It is endogenous to the acuity objective — the brightness correction is
applied inside the model at `stage4_human_vision/acuity.py:69`, via
`logmar_per_log10_illuminance` against retinal trolands. The objective already contains
contrast sensitivity, the MTF10 cutoff, and illuminance in one number.

**CORRECTION (2026-09-11): the brightness term is inert at every actual operating point.**
The Weber knee is 300 Td. At the model's 10,000 cd/m² default, every aperture ≥200 µm
clears it — and all eight gaze-weighted winners are 400–2000 µm. The brightness penalty
is exactly 0.0000 logMAR for every fabricated design. MTF10 alone accounts for ~96% of
the final logMAR; VSOTF adds ~0.01; brightness adds nothing. Full derivation in
`stage4_human_vision/300TD_KNEE_NOTES.txt` and `ACUITY_INPUTS_AND_WEIGHTS.pdf`.
**Do not say "brightness is part of the objective" without immediately stating it
contributes zero at our apertures** — say this yourself, it is stronger stated than found.

**This dissolves the "three competing optima" problem.** Restated correctly:

| Approach | Result | Status |
|---|---|---|
| Minimise `r_EE(50%)` | 300–400 µm, flat across M | Proxy. **Superseded → reserve.** |
| Minimise blur s.t. explicit `T_min` floor | 900–1250 µm | Intermediate step. **Reserve.** |
| **Maximise acuity (logMAR)** | **400–2000 µm, M-dependent** | **THE ANSWER** |

Do not present these as three competing answers. Present one answer and a discarded proxy.

---

## D2. The cross-validation result

Acuity optima (from `new_sweeps/acuity_sweep_stage4.csv`) vs. gaze-weighted geometric
winners (from `gaze_weighted_winner_per_M.csv`):

| M (D) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 8 |
|---|---|---|---|---|---|---|---|---|
| Acuity-optimal (µm) | 2000 | 1250 | 750 | 750 | 600 | 600 | 500 | 400 |
| Gaze-weighted winner (µm) | 2000 | 1250 | 750 | 750 | 600 | 600 | 500 | 400 |

**Identical at all eight myopia levels.** The gaze-weighted evaluator scores viability,
ghost margin, and blind fraction — it contains no acuity term. Two objectives with no
shared component agree on every design. This was not enforced. It is the strongest
internal validation in the project and belongs in the main deck, not reserve.

---

## D3. MANDATORY caveat on the M=0 row

**M=0's optimum of 2000 µm is the largest aperture in the sweep** (`A_HOLE_UM` ends at
2000). Acuity is still improving monotonically at that edge, so it is *not* a converged
interior optimum — it is where the grid ran out.

Physically expected: with no defocus there is nothing to trade diffraction against, so
larger is always better until aberrations the model excludes take over. Every myopic
case (M ≥ 1) is a genuine interior optimum.

**Script line:** "At zero myopia the optimum is unbounded within our range — with no
defocus there's nothing to trade diffraction against. Every myopic case is an interior
optimum."

Showing the table without this caveat invites the observation that 2000 is the sweep
maximum, which reads as not having checked.

---

## D4. Basics first — judges lack background

Three foundational slides added at the front. Time is taken from merging and demoting,
never from slides 4, 6, 8, 9.

**Revised running order — 14 main slides, ~685 s of 720 s:**

| # | Slide | Time | Origin |
|---|---|---|---|
| 1 | What goes wrong in a short-sighted eye | 40 s | NEW |
| 2 | Why a pinhole helps | 40 s | NEW |
| 3 | Why smaller isn't better | 45 s | NEW (was old S1) |
| 4 | Computing it properly — the ASM correction | 85 s | old S2 |
| 5 | Does the code work? | 40 s | old S3, compressed |
| 6 | The answer: optimising acuity | 85 s | old S5+S6 MERGED, rewritten per D1 |
| 7 | One hole → an array | 55 s | old S7 |
| 8 | A published criterion that doesn't discriminate | 55 s | old S8 |
| 9 | Our design, and the parameter that doesn't bind | 80 s | old S9 |
| 10 | Fabrication | 40 s | old S10 |
| 11 | Measurement | 70 s | old S11 |
| 12 | Limits | 50 s | old S12 |

**Demoted:** old Slide 4 (RSS refutation, 64.8 % mean / 192.8 % max divergence) → **R28**.
Keep one baiting sentence inside Slide 4's script: "the shortcut everyone uses diverges
from the exact answer by 65 % on average, and we have the slide if you want it."

**Never cut:** 4, 6, 8, 9. If overrunning, fold 5 into 6, then shorten 3.

---

## D5. Slide 6 script (rewritten per D1)

> "Blur radius is a proxy, and it's a bad one — it says where half the light is, not what
> the eye can resolve. So we optimised acuity directly: contrast sensitivity, the MTF
> cutoff, and retinal illuminance, in one objective. The answer isn't a single aperture —
> it scales with myopia. Two millimetres for an unaffected eye, four hundred microns at
> eight dioptres. As the eye gets worse the optimal hole gets smaller, because defocus is
> growing and diffraction is the price you pay to suppress it.
>
> [D3 caveat here.]
>
> Then the check we didn't design for. The array geometry was selected by a completely
> separate evaluator — pure geometry, viability and ghost margin, no acuity term anywhere
> in it. It picked the same aperture at all eight myopia levels."

**Slide 6 addition, immediately after the paragraph above, per D1's correction:**
> "One honest note on that objective: it includes a brightness term, cited from Van Nes
> and Bouman, but at our apertures it contributes nothing — we're above the illuminance
> knee at every design we picked. The answer is set by the MTF cutoff alone."

**Slide 11 addition, per D9 — say before presenting any predicted number:**
> "One caveat before these numbers: this model hasn't been validated against real
> clinical data before today. We checked it once, against a published dataset, and it
> failed — no significant relationship. We tested whether our brightness assumption was
> the cause and ruled that out. The leading suspects are an uncalibrated formula and a
> very small clinical dataset, not necessarily the optics. This measurement is the
> calibration data the model has never had."

---

## D9. The acuity model failed its own external validation — say this before Slide 11

**Finding (2026-09-11), from `stage4_human_vision/RESULTS.md` and
`LUMINANCE_RECONCILIATION.md`, already run before this conversation:**

The full `mtf10_vsotf_brightness_adjusted` model was tested against Wang et al. (2009)'s
real clinical pinhole-acuity data:

| M (D) | R² | Pearson r | p-value |
|---|---|---|---|
| 0 | −6.39 | 0.395 | 0.510 |
| 2 | −4.98 | 0.393 | 0.513 |
| 5 | −2.84 | 0.405 | 0.499 |

Negative R² = worse than predicting the mean. p≈0.50 = no significant relationship
detected. Not weak correlation — all 15 tested points show the same-direction bias
(model over-predicts blur at every point).

**Scene luminance was tested and ruled out as the cause.** Correcting to Wang 2009's own
stated illumination (43.7 cd/m² vs. the 10,000 cd/m² default) made R² *worse*
(−7.88 vs. −6.68 at M=0), because it pushed apertures further below the 300 Td knee and
added more predicted blur on top of a model already over-predicting it.

**Project's own leading diagnosis, in order:** (1) no fitted calibration against real
data anywhere in the formula — `DESIGN.md` flags this as a known gap; (2) Wang 2009 is
non-monotonic at n=5 (logMAR spikes to 1.00 at 1000µm, drops to 0.40 at 1200µm — one
outlier sinks any smooth model at this sample size); (3) no per-subject refractive error
in the dataset; (4) n=5 is too small for significance regardless. `RESULTS.md`'s own
verdict: cannot be properly validated with currently available public data.

**Consequence for every predicted-logMAR number in this project (both PDFs, all sweep
CSVs):** these are self-consistent model outputs, traceable term by term, **not
validated clinical predictions**. Do not present them as validated. Say the status
yourself — see Slide 11 script addition above.

**This is not a reason to hide the numbers or abandon the acuity framing in D1.** It is
the reason the logMAR measurement protocol (`LOGMAR_ACUITY_PROTOCOL.pdf`) is calibration
data, not a confirmatory afterthought — say that framing explicitly, it is a stronger
position than either overclaiming or omitting.

Full detail: `stage4_human_vision/300TD_KNEE_NOTES.txt`, Section 6.

---

## D6. Scripts for the three new basics slides

**Slide 1 — What goes wrong in a short-sighted eye (40 s).**
*Figure:* two-panel ray diagram, build in slide tool. Normal eye converging on retina;
myopic eye converging in front of it.
*On slide:* "Normal eye: 22.3 mm" / "−4 D eye: 23.9 mm" / "The lens is fine. The eyeball
is 1.6 mm too long."
> "Short-sightedness is usually not a problem with the lens. The eye's focusing power is
> normal — the eyeball has simply grown too long. Light comes to a focus in the right
> place, but the retina sits behind it. At four dioptres that's about 1.6 millimetres too
> far back. So every point in the world lands on the retina as a small disc instead of a
> point, and the world looks blurred."

Deliver "a point becomes a disc" slowly. It is the mental model everything else uses.

**Slide 2 — Why a pinhole helps (40 s).**
*Figure:* same myopic eye with pinhole; wide cone shaded out, narrow cone through hole,
smaller disc on retina.
*On slide:* "Narrow the cone → shrink the disc."
> "Now block most of the light and let through only a narrow pencil of rays. The eye is
> still focusing in the wrong place, but the cone reaching the retina is much narrower, so
> the disc it makes is much smaller. This is why squinting helps, and why you may have
> looked through a small hole in your hand to read something far away. No correction has
> been applied — the blur has just been geometrically starved."

**Slide 3 — Why smaller isn't better (45 s).**
*Figure:* `all_outputs/stage1_radius_vs_diameter.png`, branches labelled.
*On slide:* "Defocus blur ∝ aperture" / "Diffraction blur ∝ 1/aperture" / "There is a
minimum."
> "So make the hole as small as possible? No. Light is a wave, and forcing it through a
> small opening makes it spread — diffraction. Below some size that spreading grows faster
> than the defocus blur shrinks, and the image gets worse again. Two effects pulling in
> opposite directions, with a minimum between them. Finding that minimum — correctly — is
> the problem."

---

## D7. Reserve deck rules and additions

Push detail into reserve, but it fails if a slide can't be found in four seconds under
questioning.

- Group with section dividers, never a flat run. Existing groups A–D (metric reliability /
  optics detail / brightness / array). **Add Group E — Basics.**
- One idea per reserve slide.
- Number visibly on the slide face so you can jump by number.
- **Printed one-page index at the lectern: number → title.** Ten minutes of work, highest
  value single action for Q&A.

**Additions beyond the 27 in `SLIDE_DECK_SPEC.pdf`:**

| # | Slide |
|---|---|
| R28 | RSS refutation (demoted from main) |
| R29 | Axial myopia derivation, worked arithmetic |
| R30 | Fresnel number worked example |
| R31 | Circle-overlap area formula |
| R32 | Band-limiting and the energy-check redundancy proof |
| R33 | Undercut compensation bracket |
| R34 | Why FWHM and r_EE(50 %) disagree, in full |
| R35 | Blur-only optimum (300–400 µm) — the superseded proxy, per D1 |

---

## D8. Open items

- **FIG-A** — one-hole-per-pupil overlap diagram. Blocks Slide 9. Not yet created.
- **FIG-B** — µ_g saturation histogram across 8501 candidates. Blocks Slide 8. Not yet created.
- **Scene luminance 10 000 cd/m²** (`stage4_human_vision/constants.json:96`) is the
  assumption behind every acuity number; `run_acuity_sweep.py` never overrides it. Must
  appear on the constants reserve slide (R27). If measured logMAR data is taken indoors,
  re-run the sweep at the measured luminance rather than comparing across regimes.
  NOTE: re-running at Wang 2009's real luminance made *validation* worse, not better
  (D9) — this is a separate question from whether YOUR OWN measurement should be taken
  at high luminance, which it still should, per `LOGMAR_ACUITY_PROTOCOL.pdf` Ch.5.
- **RESOLVED, folded into D9:** acuity model validation status. Was an open item;
  now documented with full reasoning and script language.
- Confirm actual time slot for national selection — 14 main slides assumes the 12-minute
  IYPT standard.
