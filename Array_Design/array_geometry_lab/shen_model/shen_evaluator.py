"""
shen_model/shen_evaluator.py -- a standalone, INDEPENDENT reimplementation of
Shen (Hangzhou Normal University, Aug. 2026)'s own pinhole-array evaluator,
built from that paper's own formulas (cited by section in each function's
docstring below) -- NOT a reuse of this project's own judgment layer
(array_evaluation/) or margin physics (array_calculation/margins/,
array_calculation/degeneracy_filter.py). This is a genuinely different model
sitting alongside this project's own pipeline for comparison, not a variant of
it (see comparison_metric/paper_score.py's own docstring for the earlier,
acknowledged-as-partial attempt this supersedes: it reused THIS project's
columns with Shen's closed-form score, which is useful but is not Shen's own
evaluator).

ALLOWED IMPORTS FROM THIS PROJECT, per this task's own explicit scope:
  - array_calculation/generators/*.py -- coordinates only.
  - array_calculation/engine/vignetting_overlap.py's overlap_area_um2 -- pure
    circle-circle overlap geometry (Handbook 2 Sec 13.2, already independently
    validated against Monte Carlo -- see that module's own docstring), not
    judgment.
NOT imported, by design: degeneracy_filter.py, margins/ghost_margin.py,
margins/vignetting_robustness.py, margins/active_pairs.py,
array_evaluation/comparison_metric/gates.py, metrics.py, paper_score.py,
paper_soft_gates.py. Every formula and threshold below is Shen's own,
reimplemented from scratch -- including the buffered-convex-hull "pattern
area" (Sec 2.2's eta denominator), which reuses the SAME well-validated
Minkowski-buffer construction array_calculation/degeneracy_filter.py's own
convex_hull_area() uses (hull_area + hull_perimeter*r + pi*r^2 -- standard
closed-form area of a convex polygon offset outward by radius r), written
fresh here rather than imported, since it is a standard computational-geometry
construction, not this project's own judgment.

===========================================================================
SHEN'S FORMULAS, Sec 2.1 -- Blur and Acuity
===========================================================================
  c_geom = d * M / P              [P = 60 D, Shen's own optical-power constant
                                    -- NOT this project's own P0]
  c_diff = 1.22 * lambda * f' / d [lambda=550nm, f'=22.2mm -- diffraction at
                                    the HOLE's own diameter d, not the pupil]
  c_tot  = sqrt(c_geom^2 + c_diff^2)     [RSS combination, Shen's own choice --
                                           see Shen's Discussion, cited in this
                                           project's own model-comparison doc,
                                           acknowledging RSS as an
                                           approximation vs. this project's own
                                           full wave-optics propagation]
  c_ref  = 1.22 * lambda * f' / p        [p = pupil diameter -- DIFFERENT
                                           denominator from c_diff above: pupil,
                                           not hole]
  a      = c_ref / c_tot
  a_norm = clip(a, 0, 3) / 3

===========================================================================
SHEN'S FORMULAS, Sec 2.2 -- Fill Factor
===========================================================================
  eta = (open hole area) / (pattern area)
  open hole area = N_actual * pi*(d/2)^2 (holes never overlap, by this
  project's own generator construction -- reject_overlapping() -- so a plain
  sum is exact, not an overcount)
  pattern area = buffered convex hull area of the ACTUAL generated coordinates
  (see module docstring above) -- general, family-agnostic, NOT the
  lattice-specific closed-form eta_sq=pi*d^2/(4*s^2) /
  eta_hex=pi*d^2/(2*sqrt(3)*s^2) this project's own paper_score.py used, per
  this task's own explicit instruction.
  mu_eta = exp(-(eta-0.15)^2 / (2*0.08^2))

===========================================================================
SHEN'S FORMULAS, Sec 2.2 Eq 8 -- Scheiner Ghost Metric (closed form)
===========================================================================
  Delta_x = s * M / P    [P ALONE, not P-M -- Shen's own convention, KEPT
                          DISTINCT from this project's own
                          delta_r_corrected_from_M_um formula, never
                          substituted for it]
  w       = clip((p + d - s) / d, 0, 1)
  c_min   = 55 (default, CLI --c_min, admissible range [50,200] per Shen's own
            Miller & Johnson clinical-diplopia-onset calibration -- the SAME
            c_min concept this project's own compute_coverage_metrics.py
            already cited when testing Shen's floor against OUR OWN margins;
            here it is Shen's own formula using it, not a borrowed floor on
            our own quantities)
  g_Sch   = w * Delta_x / max(c_tot, c_min)
  Reported as its OWN column (g_Sch), a per-candidate CLOSED-FORM diagnostic
  using this candidate's own representative lattice spacing s -- NOT fed into
  the score (see Sec 2.4 below: the score uses the Monte-Carlo-sampled
  ghost_rate instead). Kept alongside ghost_rate specifically so the two can
  be compared honestly, per this task's own instruction.

===========================================================================
SHEN'S FORMULAS, Sec 2.4 -- Monte Carlo Array Evaluator (the actual evaluator)
===========================================================================
Per candidate (one row of this project's own theoretical_data, at ONE M --
Shen's formulas are all M-specific; M='global' rows are OUT OF SCOPE here,
since Shen's paper describes no cross-M aggregate and none is assumed),
n_trials=1000 (Shen's own count) independent trials:
  1. Sample an object direction uniformly in SOLID ANGLE within a +-10deg
     half-angle cone (theta = arccos(1 - u*(1-cos(10deg))), u~Uniform(0,1);
     azimuth ~ Uniform(0, 2*pi) -- standard uniform-solid-angle-in-a-cone
     sampling, not a uniform angle sweep, which would over-sample near the
     cone's edge). Converted to a pupil shift via the same R_rot_mm=13.5mm
     eye-rotation radius this project's own vignetting_overlap.py already
     cites (Handbook 2 Sec 13.1's physiological range) -- but applied in BOTH
     x and y here (Shen's own 2D object-direction field), unlike this
     project's own single-axis gaze simplification.
  2. Sample a pupil WANDER position uniformly within a disc of radius
     half_width_um = (this candidate's own representative lattice spacing) *
     --wander_half_width_factor (default 0.5, i.e. half the spacing -- the
     SAME half-width array_calculation/compute_coverage_metrics.py's own
     cell_half_width_um() uses, reused for consistency per this task's own
     instruction, though this module's own sampling and ghost/blind
     computation are otherwise fully independent of that file).
  3. Determine ADMITTED holes at this trial's pupil position: overlap_area_um2
     (reused, pure geometry) > 0 -- ANY nonzero pupil-hole overlap admits a
     beam. No 0.5-fraction threshold here (that is this project's OWN
     active_pairs.py modeling choice, explicitly not imported).
  4. For every pair of simultaneously admitted beams, test resolvability:
     Delta_x_ij = s_ij * M / P, s_ij = the ACTUAL pairwise Euclidean distance
     between the two admitted holes (generalizing Shen's own "s" the same
     well-justified way this project's own ghost_margin.py generalizes its
     own "s" for arbitrary coordinates -- see that module's own comment).
     Resolvable iff Delta_x_ij > max(mean(c_tot_i, c_tot_j), c_min); since
     every hole in one candidate shares the same a_hole_um here,
     mean(c_tot_i,c_tot_j) reduces to this candidate's single c_tot, but the
     formula is implemented exactly as given, not simplified away.
Per-candidate outputs:
  ghost_rate            = fraction of trials with >=1 resolvable pair
  blind_rate             = fraction of trials with zero admitted beams
  pair_resolved_fraction = (resolvable pairs summed across ALL trials) /
                           (admitted pairs summed across ALL trials) --
                           severity, not just occurrence (Shen's own
                           distinguishing metric, per this task's brief)

===========================================================================
SHEN'S FORMULAS, Sec 2.4 -- Score (MC-normalized form)
===========================================================================
  mu_g(ghost_rate) = sigmoid(2*(1 - ghost_rate/1.0))   [applied to the MC RATE,
                      NOT to g_Sch -- the two are kept structurally separate,
                      per this task's own instruction]
  S = (1.0*a_norm + 0.8*mu_eta + 1.0*mu_g(ghost_rate) + 0.6*(1-blind_rate)) / 3.4
      [3.4 = 1.0+0.8+1.0+0.6, Shen's own MC-normalized form]

Run:  python3 shen_evaluator.py                      # c_min=55, 1000 trials
      python3 shen_evaluator.py --c_min 55 --n_trials 1000 --limit 200
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__))  # shen_model/
LAB_ROOT = os.path.dirname(HERE)  # array_geometry_lab/
CALC_ROOT = os.path.join(LAB_ROOT, "array_calculation")

sys.path.insert(0, os.path.join(CALC_ROOT, "generators"))
sys.path.insert(0, os.path.join(CALC_ROOT, "engine"))
import square  # noqa: E402
import hexagonal  # noqa: E402
import concentric  # noqa: E402
import fibonacci_spiral  # noqa: E402
import golden_angle  # noqa: E402
import rectangular  # noqa: E402
import archimedean_spiral  # noqa: E402
import ring_offset_concentric  # noqa: E402
import poisson_disk  # noqa: E402
import jittered_lattice  # noqa: E402
import vignetting_overlap as vo  # noqa: E402 -- pure geometry (overlap_area_um2),
                                  # explicitly allowed by this task's own scope.

DATA_DIR = os.path.join(LAB_ROOT, "array_data", "theoretical_data")
IN_CSV = os.path.join(DATA_DIR, "sweep_results_with_density.csv")  # READ-ONLY;
                                                                    # array_data/
                                                                    # itself is
                                                                    # never
                                                                    # written to
                                                                    # by this
                                                                    # module.
OUT_DIR = HERE  # shen_model/ -- all outputs of this module live here, not in
                # array_data/, per this task's own instruction.

GEN_FUNCS = {
    "square": square.generate,
    "hexagonal": hexagonal.generate,
    "concentric": concentric.generate,
    "fibonacci_spiral": fibonacci_spiral.generate,
    "golden_angle": golden_angle.generate,
    "rectangular": rectangular.generate,
    "archimedean_spiral": archimedean_spiral.generate,
    "ring_offset_concentric": ring_offset_concentric.generate,
    "poisson_disk": poisson_disk.generate,
    "jittered_lattice": jittered_lattice.generate,
}

SIMPLE_SPACING_KEY = {
    "square": "pitch_um",
    "hexagonal": "pitch_um",
    "jittered_lattice": "pitch_um",
    "concentric": "ring_spacing_um",
    "ring_offset_concentric": "ring_spacing_um",
    "fibonacci_spiral": "c_um",
    "golden_angle": "c_um",
    "archimedean_spiral": "c_um",
}

# --- constants, Shen's own, as given ---
LAMBDA_UM = 550.0 / 1000.0       # 550nm
F_PRIME_UM = 22.2 * 1000.0       # 22.2mm
SHEN_P = 60.0                    # Shen's own optical-power constant, Sec 2.1/2.2
D_PUPIL_UM = 4000.0              # this project's own established pupil diameter
                                  # constant (array_calculation/sweep/run_sweep.py's
                                  # DEFAULT_D_PUPIL_UM) -- Shen's own paper does not
                                  # redefine this project's physical pupil size, only
                                  # its own formulas' TREATMENT of it.
R_ROT_MM = 13.5                  # physiological eye-rotation radius, Handbook 2
                                  # Sec 13.1's own stated range (13-14mm) -- the same
                                  # constant this project's own vignetting_overlap.py
                                  # already cites; a physical/anatomical value, not
                                  # this project's judgment.
OBJECT_HALF_ANGLE_DEG = 10.0      # Sec 2.4's own stated field, +-10deg


def parse_spacing_params(s):
    d = {}
    if pd.isna(s) or s == "":
        return d
    for part in str(s).split(";"):
        k, v = part.split("=")
        try:
            v = float(v)
        except ValueError:
            pass
        d[k] = v
    return d


def spacing_um(family, spacing_params, a_hole_um):
    """s, per family -- same mapping this project's own comparison_metric/
    paper_score.py uses for an analogous purpose, re-derived locally here
    (this module does not import array_evaluation/)."""
    params = parse_spacing_params(spacing_params)
    if family == "poisson_disk":
        return params["spacing_factor"] * a_hole_um
    if family == "rectangular":
        return float(np.sqrt(params["pitch_x_um"] * params["pitch_y_um"]))
    key = SIMPLE_SPACING_KEY.get(family)
    if key is None:
        raise ValueError(f"no spacing mapping defined for family {family!r}")
    return params[key]


def generate_coords(family, N, a_hole_um, spacing_params, seed):
    kwargs = parse_spacing_params(spacing_params)
    gen_kwargs = dict(kwargs)
    if pd.notna(seed):
        gen_kwargs["seed"] = int(seed)
    coords, meta = GEN_FUNCS[family](N=int(N), a_hole_um=a_hole_um, **gen_kwargs)
    return coords


def buffered_hull_area_um2(coords, a_hole_um):
    """Pattern area, Sec 2.2's eta denominator -- buffered convex hull (same
    well-validated Minkowski-buffer construction as this project's own
    degeneracy_filter.convex_hull_area(), reimplemented fresh here, see module
    docstring). NaN for fewer than 3 points."""
    if len(coords) < 3:
        return np.nan
    try:
        hull = ConvexHull(coords)
    except Exception:
        return np.nan
    r = a_hole_um / 2.0
    return hull.volume + hull.area * r + np.pi * r ** 2  # scipy 2D: volume=area, area=perimeter


# --- Sec 2.1: blur and acuity ---

def c_geom_um(d_um, M):
    return d_um * M / SHEN_P


def c_diff_um(d_um):
    return 1.22 * LAMBDA_UM * F_PRIME_UM / d_um


def c_tot_um(d_um, M):
    return float(np.sqrt(c_geom_um(d_um, M) ** 2 + c_diff_um(d_um) ** 2))


def c_ref_um(p_um=D_PUPIL_UM):
    return 1.22 * LAMBDA_UM * F_PRIME_UM / p_um


def acuity_a_norm(c_tot):
    a = c_ref_um() / c_tot
    return min(max(a, 0.0), 3.0) / 3.0


# --- Sec 2.2: fill factor ---

def eta_and_mu_eta(coords, a_hole_um):
    N_actual = len(coords)
    open_area = N_actual * np.pi * (a_hole_um / 2.0) ** 2
    pattern_area = buffered_hull_area_um2(coords, a_hole_um)
    if not np.isfinite(pattern_area) or pattern_area <= 0:
        return np.nan, np.nan
    eta = open_area / pattern_area
    mu_eta = float(np.exp(-((eta - 0.15) ** 2) / (2.0 * 0.08 ** 2)))
    return float(eta), mu_eta


# --- Sec 2.2 Eq 8: closed-form Scheiner ghost metric ---

def g_sch(s_um, M, d_um, c_tot, c_min):
    w = min(max((D_PUPIL_UM + d_um - s_um) / d_um, 0.0), 1.0)
    delta_x = s_um * M / SHEN_P
    return w * delta_x / max(c_tot, c_min)


# --- Sec 2.4: Monte Carlo array evaluator ---

def sample_object_direction_shifts_um(n_trials, rng, half_angle_deg=OBJECT_HALF_ANGLE_DEG,
                                      R_rot_mm=R_ROT_MM):
    """Uniform-in-solid-angle sampling within a half_angle_deg cone (Sec 2.4
    step 1) -- theta = arccos(1 - u*(1-cos(half_angle))), NOT a uniform angle
    sweep (which would over-sample the cone's edge). Returns (n_trials, 2) x/y
    pupil shifts in um -- Shen's own 2D object-direction field, unlike this
    project's own single-axis gaze simplification."""
    half_angle_rad = np.radians(half_angle_deg)
    u = rng.uniform(0.0, 1.0, n_trials)
    theta = np.arccos(1.0 - u * (1.0 - np.cos(half_angle_rad)))
    azimuth = rng.uniform(0.0, 2.0 * np.pi, n_trials)
    R_rot_um = R_rot_mm * 1000.0
    shift_x = R_rot_um * np.sin(theta) * np.cos(azimuth)
    shift_y = R_rot_um * np.sin(theta) * np.sin(azimuth)
    return np.column_stack([shift_x, shift_y])


def sample_wander_offsets_um(n_trials, half_width_um, rng):
    """Uniform sampling within a DISC of radius half_width_um (Sec 2.4 step 2
    -- 'wander disc'), r=R*sqrt(u) for area-uniform disc sampling."""
    r = half_width_um * np.sqrt(rng.uniform(0.0, 1.0, n_trials))
    theta = rng.uniform(0.0, 2.0 * np.pi, n_trials)
    return np.column_stack([r * np.cos(theta), r * np.sin(theta)])


def run_mc_trials(coords, a_hole_um, M, c_tot, c_min, half_width_um, n_trials, rng):
    """Returns (ghost_rate, blind_rate, pair_resolved_fraction) -- Sec 2.4."""
    coords = np.asarray(coords, dtype=float)
    N = len(coords)
    if N == 0:
        return 0.0, 1.0, np.nan

    obj_shifts = sample_object_direction_shifts_um(n_trials, rng)
    wander = sample_wander_offsets_um(n_trials, half_width_um, rng)
    pupil_centers = obj_shifts + wander  # (n_trials, 2)

    R_h = a_hole_um / 2.0
    R_p = D_PUPIL_UM / 2.0
    dx = pupil_centers[:, 0][:, None] - coords[:, 0][None, :]
    dy = pupil_centers[:, 1][:, None] - coords[:, 1][None, :]
    delta = np.sqrt(dx ** 2 + dy ** 2)
    areas = vo.overlap_area_um2(delta, R_p, R_h)  # (n_trials, N)
    admitted = areas > 0.0

    n_admitted = admitted.sum(axis=1)
    blind_trials = int((n_admitted == 0).sum())

    ghost_trials = 0
    total_admitted_pairs = 0
    total_resolvable_pairs = 0
    threshold = max(c_tot, c_min)
    for t in np.where(n_admitted >= 2)[0]:
        idx = np.where(admitted[t])[0]
        pts = coords[idx]
        n_pts = len(pts)
        pair_i, pair_j = np.triu_indices(n_pts, k=1)
        s_ij = np.sqrt(((pts[pair_i] - pts[pair_j]) ** 2).sum(axis=1))
        delta_x_ij = s_ij * M / SHEN_P
        resolvable = delta_x_ij > threshold
        n_pairs = len(resolvable)
        n_resolvable = int(resolvable.sum())
        total_admitted_pairs += n_pairs
        total_resolvable_pairs += n_resolvable
        if n_resolvable > 0:
            ghost_trials += 1

    ghost_rate = ghost_trials / n_trials
    blind_rate = blind_trials / n_trials
    pair_resolved_fraction = (total_resolvable_pairs / total_admitted_pairs
                              if total_admitted_pairs > 0 else np.nan)
    return ghost_rate, blind_rate, pair_resolved_fraction


def sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0 + np.exp(-x))
    ex = np.exp(x)
    return ex / (1.0 + ex)


def shen_score(a_norm, mu_eta, ghost_rate, blind_rate):
    mu_g = sigmoid(2.0 * (1.0 - ghost_rate / 1.0))
    return (1.0 * a_norm + 0.8 * mu_eta + 1.0 * mu_g + 0.6 * (1.0 - blind_rate)) / 3.4


def process_row(row, c_min, n_trials, wander_half_width_factor, rng):
    d_um = float(row.a_hole_um)
    M = float(row.M)
    s_um = spacing_um(row.family, row.spacing_params, d_um)

    coords = generate_coords(row.family, row.N_requested, d_um, row.spacing_params, row.seed)

    c_tot = c_tot_um(d_um, M)
    a_norm = acuity_a_norm(c_tot)
    eta, mu_eta = eta_and_mu_eta(coords, d_um)
    gsch = g_sch(s_um, M, d_um, c_tot, c_min)

    half_width_um = (s_um / 2.0) * wander_half_width_factor
    ghost_rate, blind_rate, pair_resolved_fraction = run_mc_trials(
        coords, d_um, M, c_tot, c_min, half_width_um, n_trials, rng)

    if np.isnan(mu_eta):
        S = np.nan
    else:
        S = shen_score(a_norm, mu_eta, ghost_rate, blind_rate)

    return {
        "c_tot_um": c_tot, "a_norm": a_norm, "eta": eta, "mu_eta": mu_eta,
        "g_Sch": gsch, "ghost_rate": ghost_rate, "blind_rate": blind_rate,
        "pair_resolved_fraction": pair_resolved_fraction, "S": S,
    }


def preserve_legacy(path):
    if not os.path.exists(path):
        return
    import shutil
    i = 1
    legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    while os.path.exists(legacy_path):
        i += 1
        legacy_path = path.replace(".csv", f"_legacy{i}.csv")
    shutil.copy2(path, legacy_path)
    print(f"preserved predecessor -> {legacy_path}")


def m_sort_key(m):
    return (m == "global", m)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--c_min", type=float, default=55.0,
                   help="Shen's own perceptual fusion floor, admissible range "
                        "[50,200] per Shen's Miller & Johnson calibration (default 55)")
    p.add_argument("--n_trials", type=int, default=1000, help="Monte Carlo trials per candidate")
    p.add_argument("--wander_half_width_factor", type=float, default=1.0,
                   help="wander-disc radius = (candidate's own spacing / 2) * this factor")
    p.add_argument("--seed", type=int, default=0, help="RNG seed, for reproducibility")
    p.add_argument("--limit", type=int, default=None, help="process only first N rows (testing)")
    return p.parse_args()


def main():
    args = parse_args()
    if not (50.0 <= args.c_min <= 200.0):
        print(f"WARNING: --c_min={args.c_min} is outside Shen's own stated admissible "
              f"range [50,200] -- proceeding anyway since this is CLI-configurable, but "
              f"flagging it.")
    rng = np.random.default_rng(args.seed)

    df = pd.read_csv(IN_CSV, dtype={"M": str})
    df = df[df.M != "global"].copy()  # Shen's formulas are all per-M; no cross-M
                                       # aggregate is described in the paper, so
                                       # 'global' rows are out of scope here, not
                                       # silently approximated.
    if args.limit:
        df = df.head(args.limit).copy()
    print(f"loaded {len(df)} per-M rows from {IN_CSV} (M='global' rows excluded -- "
          f"see module docstring)")
    print(f"c_min={args.c_min}  n_trials={args.n_trials}  "
          f"wander_half_width_factor={args.wander_half_width_factor}  seed={args.seed}")

    results = []
    n_done = 0
    for row in df.itertuples():
        results.append(process_row(row, args.c_min, args.n_trials,
                                   args.wander_half_width_factor, rng))
        n_done += 1
        if n_done % 500 == 0:
            print(f"  {n_done}/{len(df)} rows done")

    results_df = pd.DataFrame(results)
    out_df = pd.concat([df.reset_index(drop=True), results_df], axis=1)

    out_csv = os.path.join(OUT_DIR, "shen_model_results.csv")
    preserve_legacy(out_csv)
    out_df.to_csv(out_csv, index=False)
    print(f"\nwrote {out_csv} ({len(out_df)} rows)")

    print("\n--- ghost_rate vs closed-form g_Sch, whole dataset ---")
    print(f"  ghost_rate:  mean={out_df.ghost_rate.mean():.4f}  "
          f"median={out_df.ghost_rate.median():.4f}  "
          f"frac==0: {(out_df.ghost_rate == 0).mean():.4f}  "
          f"frac==1: {(out_df.ghost_rate == 1).mean():.4f}")
    print(f"  g_Sch:       mean={out_df.g_Sch.mean():.4f}  median={out_df.g_Sch.median():.4f}  "
          f"frac>1 (saturation-like): {(out_df.g_Sch > 1).mean():.4f}")
    corr = out_df[["ghost_rate", "g_Sch"]].dropna().corr().iloc[0, 1]
    print(f"  correlation(ghost_rate, g_Sch) = {corr:.4f} "
          f"(1.0 would mean they agree; this is an honest empirical check, not assumed)")

    survivors = out_df.dropna(subset=["S"])
    winners = []
    for M, group in survivors.groupby("M"):
        winners.append(group.loc[group["S"].idxmax()])
    winners_df = pd.DataFrame(winners).sort_values(by="M", key=lambda c: c.map(m_sort_key)).reset_index(drop=True)

    out_winner_csv = os.path.join(OUT_DIR, "shen_model_winner_per_M.csv")
    preserve_legacy(out_winner_csv)
    winners_df.to_csv(out_winner_csv, index=False)
    print(f"\nwrote {out_winner_csv} ({len(winners_df)} rows)")

    print("\n--- Shen-model winner per M ---")
    cols = ["M", "family", "N_requested", "N_actual", "spacing_params", "c_tot_um",
           "a_norm", "eta", "mu_eta", "g_Sch", "ghost_rate", "blind_rate",
           "pair_resolved_fraction", "S"]
    print(winners_df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
