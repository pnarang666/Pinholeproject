"""
Recompute r_EE at 50/70/80/90% directly from the raw retinal intensity field, for a
representative myopia level M, across the full aperture range. Reads the raw I_retina
that phase2_retina.run_pipeline_point() ALREADY returns (never saved to any CSV before
now) -- does not modify phase2_retina.py or any Stage 2 file. r_EE_70 didn't exist
anywhere before this (retinal_encircled_energy() only ever computed 50/80/90); this adds
it without touching Stage 2, by reusing junction.encircled_energy/r_for_EE on the raw
field Stage 2 was already computing and discarding.

Usage: python3 recompute_multi_EE.py <M_diopters>
Appends to multi_EE_sweep.csv. Run once per M value (kept single-M per invocation
deliberately -- ~15 points/~80s per call, safe against tool timeouts; a single 105-point
run is not).
"""
import sys, os
import numpy as np
import pandas as pd
import phase2_retina as p2
import pipeline_junction as junction

M = float(sys.argv[1])
A_HOLE_UM = [75, 100, 150, 200, 300, 400, 500, 600, 700, 750, 1000, 1250, 1500, 1750, 2000]
PERCENTILES = [0.50, 0.70, 0.80, 0.90]

rows = []
for a_um in A_HOLE_UM:
    result = p2.run_pipeline_point(
        a_hole=a_um * 1e-6, wavelength=550e-9, d_gap=12e-3,
        grid_N=2048, window_L_mm=6.0, M_diopters=M, P0=60.0, n_prime=1.336,
        D_pupil_um=4000.0, refractive_index_correction=True,
    )
    row = {"a_hole_um": a_um, "M_diopters": M, "junction_ok": result["junction_check_passed"]}
    if result["junction_check_passed"]:
        I_retina = result["I_retina"]
        dx = result["cornea_result"]["dx"]
        N = I_retina.shape[0]
        L = N * dx
        _, _, R, _ = junction.make_grid(N, L)
        r_edges, EE, total_power = junction.encircled_energy(I_retina, R, dx)
        for p in PERCENTILES:
            row[f"r_EE_{int(p*100)}_um"] = junction.r_for_EE(r_edges, EE, p) * 1e6
    rows.append(row)
    print(a_um, {k: round(v,2) if isinstance(v,float) else v for k,v in row.items() if 'r_EE' in k})

df = pd.DataFrame(rows)
out = "multi_EE_sweep.csv"
df.to_csv(out, mode="a", header=not os.path.exists(out), index=False)
print("appended", len(df), "rows for M=", M)
