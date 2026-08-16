# Part 1 validation gate: copied physics reproduces the original, checked not assumed

Both `engine/ghost_formula.py` and `engine/vignetting_overlap.py` were copied (not
imported) from the validated originals in `array_optimization/`. Copying by hand risks
transcription errors (a dropped minus sign, a swapped variable, a missing clamp) that
would silently corrupt every downstream number in this pipeline. This file is the record
of checking that did not happen, run via `validate_copies.py`.

## Method

Re-run each copied function against the **original validation dataset's own input
columns**, and compare against that dataset's **own recorded output column** (computed by
the original, un-copied module). This is not a self-consistency check — it's a check
against an independent, previously-generated artifact, so it catches a bad copy even if
the bad copy is internally consistent with itself.

## Ghost formula (`ghost_formula.py` vs. `stage0_ghost_validation/ghost_formula_validation.csv`)

32 points. Two forms checked against the CSV's own `pred_corrected_um` column (the
original `ghost_separation.delta_r_corrected_um` output):

| check | max absolute difference | tolerance | result |
|---|---|---|---|
| `delta_r_corrected_um(pitch_um, v_r_um, f_eye_um)` vs. `pred_corrected_um` | **5.684e-13 µm** | 1e-9 µm | **PASS** |
| `delta_r_corrected_from_M_um(pitch_um, M_diopters, P0=60)` vs. `pred_corrected_um` | **3.411e-13 µm** | 1e-9 µm | **PASS** |

Both differences are at the level of floating-point round-off (~1e-13), not a real
numerical discrepancy — the copy is exact.

## Vignetting overlap (`vignetting_overlap.py` vs. `vignetting_validation.csv`)

72 points. `overlap_area_um2(delta_um, R_p_um, R_h_um)` checked against the CSV's own
`A_overlap_closed_form_um2` column (the original `vignetting.overlap_area_um2` output,
already including the boundary-clamp fix):

| check | value |
|---|---|
| max absolute difference | **4.657e-10 µm²** |
| tolerance | 1e-6 µm² |
| negative values produced by the copy | **0** (confirms the boundary-clamp fix was copied, not just the pre-fix formula) |
| result | **PASS** |

## Overall gate: PASS

Both copies reproduce their originals to floating-point precision, not merely "close."
Part 2 (generators) may proceed. Re-run `python3 validate_copies.py` any time either
`engine/` file or its corresponding `array_optimization/` original changes, to confirm the
copies haven't drifted out of sync — this pipeline has no import-time dependency that
would otherwise catch that automatically.
