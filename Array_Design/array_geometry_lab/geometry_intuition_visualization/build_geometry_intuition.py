"""
Array_Design/array_geometry_lab/geometry_intuition_visualization/build_geometry_intuition.py

Visualizes the fundamental geometric intuition behind hexagonal packing winning
this project's primary ranking: hexagonal is the unique 2D lattice that is BOTH
the densest possible packing AND has the highest rotational symmetry (6-fold --
the max any periodic lattice can have, crystallographic restriction theorem),
so its gap structure is nearly the same in every azimuth. Square only has
4-fold symmetry (its diagonal nearest-neighbor distance is sqrt(2) times the
axis-aligned one -- a real, quantifiable weak direction). Ring_offset_concentric
has a LITERAL discrete angular structure (holes_per_ring0 positions per ring),
creating real periodic gaps between ring holes.

Two figures, using REAL geometry and REAL already-computed project numbers,
nothing invented:

  Figure 1 (geometry_intuition_structure.png): local hole-neighborhood panels
  for 4 real designs at the SAME pitch/ring-spacing (4000um, M=2D, a_hole=750um
  -- an apples-to-apples comparison, only the lattice TYPE differs), nearest-
  neighbor connections annotated with real distances.

  Figure 2 (geometry_intuition_real_consequence.png): grouped bar chart of the
  REAL time_weighted_blind_pct / time_weighted_ghost_pct for those same 4
  designs, read directly from array_data/theoretical_data/gaze_weighted_metrics.csv
  (Layer 1's own already-computed, already-validated output) -- not recomputed
  or approximated here.

Run: python3 build_geometry_intuition.py
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LAB, "array_calculation"))
import degeneracy_filter as dgf  # noqa: E402

DATA_DIR = os.path.join(LAB, "array_data", "theoretical_data")
GAZE_METRICS_CSV = os.path.join(DATA_DIR, "gaze_weighted_metrics.csv")

M = 2.0
A_HOLE_UM = 750.0
N_REQUESTED = 20
PITCH_UM = 4000.0

DESIGNS = [
    {"label": "square\n(4-fold symmetry)", "family": "square",
     "spacing_params": "pitch_um=4000.0;rotation_deg=0.0", "color": "#2C6E9E"},
    {"label": "hexagonal\n(6-fold symmetry)", "family": "hexagonal",
     "spacing_params": "pitch_um=4000.0;rotation_deg=0.0", "color": "#4E9F3D"},
    {"label": "ring_offset_concentric\n(6 holes/ring)", "family": "ring_offset_concentric",
     "spacing_params": "ring_spacing_um=4000.0;holes_per_ring0=6", "color": "#E07B39"},
    {"label": "ring_offset_concentric\n(8 holes/ring)", "family": "ring_offset_concentric",
     "spacing_params": "ring_spacing_um=4000.0;holes_per_ring0=8", "color": "#B23A48"},
]


def regenerate(family, spacing_params):
    kwargs = dgf.parse_spacing_params(spacing_params)
    coords, _meta = dgf.GEN_FUNCS[family](N=N_REQUESTED, a_hole_um=A_HOLE_UM, **kwargs)
    return np.asarray(coords, dtype=float)


def nearest_neighbor_lines(coords, center_idx=None):
    """From the hole closest to the array centroid, distance+direction to its
    few nearest neighbors -- real nearest-neighbor structure, not idealized."""
    dists_from_center = np.hypot(coords[:, 0], coords[:, 1])
    if center_idx is None:
        center_idx = np.argmin(dists_from_center)
    c = coords[center_idx]
    d = np.hypot(coords[:, 0] - c[0], coords[:, 1] - c[1])
    order = np.argsort(d)
    order = order[order != center_idx]
    return c, coords[order[:6]], d[order[:6]]


def fig1_structure():
    fig, axes = plt.subplots(1, 4, figsize=(17, 5.2))

    # Panels 0-1: square, hexagonal -- clean regular lattices, the nearest-neighbor-
    # distance argument applies cleanly and exactly.
    for ax, d in zip(axes[:2], DESIGNS[:2]):
        coords = regenerate(d["family"], d["spacing_params"])
        c, neighbors, dists = nearest_neighbor_lines(coords)
        extent = 2600
        ax.set_xlim(-extent, extent); ax.set_ylim(-extent, extent)
        ax.set_aspect("equal")
        ax.scatter(coords[:, 0], coords[:, 1], s=28, color="#cccccc", edgecolor="#666", zorder=2)
        ax.scatter([c[0]], [c[1]], s=60, color=d["color"], zorder=4, edgecolor="black")
        for (nx, ny), dist in zip(neighbors, dists):
            ax.plot([c[0], nx], [c[1], ny], color=d["color"], linewidth=1.4, zorder=3, alpha=0.85)
            mx, my = (c[0] + nx) / 2, (c[1] + ny) / 2
            ax.text(mx, my, f"{dist:.0f}", fontsize=7.5, color=d["color"], fontweight="bold",
                    ha="center", va="center", bbox=dict(facecolor="white", edgecolor="none", pad=0.5, alpha=0.85))
        ax.set_title(d["label"], fontsize=10.5, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#ddd")
        n_unique = len(set(np.round(dists, 0)))
        ax.set_xlabel(f"{n_unique} distinct nearest-neighbor distance(s)", fontsize=8.5, color="#555")

    # Panels 2-3: the two ring designs -- REAL structure is offset, non-uniform rings
    # (checked: radii are NOT clean multiples of ring_spacing), not a simple lattice --
    # shown as real coordinate scatter, not forced into the same distance-count framing.
    for ax, d in zip(axes[2:], DESIGNS[2:]):
        coords = regenerate(d["family"], d["spacing_params"])
        extent = np.abs(coords).max() * 1.15
        ax.set_xlim(-extent, extent); ax.set_ylim(-extent, extent)
        ax.set_aspect("equal")
        radii = np.hypot(coords[:, 0], coords[:, 1])
        ax.scatter(coords[:, 0], coords[:, 1], s=32, c=radii, cmap="Oranges" if "6" in d["label"] else "Reds",
                  edgecolor="#666", zorder=3)
        ax.add_patch(plt.Circle((0, 0), radii.min(), fill=False, edgecolor=d["color"], linewidth=1.0,
                                linestyle=":", alpha=0.6))
        ax.set_title(d["label"], fontsize=10.5, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#ddd")
        ax.set_xlabel(f"real radii range {radii.min():.0f}-{radii.max():.0f}um\n(offset rings, not uniform)",
                     fontsize=8.5, color="#555")

    fig.suptitle("Why lattice TYPE matters: real geometry at identical spacing\n"
                "(M=2D, a_hole=750um, pitch/ring-spacing=4000um for all four)",
                fontsize=13, fontweight="bold", y=0.985)
    plt.tight_layout(rect=[0, 0.13, 1, 0.84])
    fig.text(0.5, 0.06,
             "Square: neighbors split into a short axis-aligned set and a longer sqrt(2) diagonal set -- one real "
             "weak direction. Hexagonal: all 6 nearest neighbors equidistant -- no weak direction.",
             ha="center", fontsize=9, color="#333", linespacing=1.6)
    fig.text(0.5, 0.015,
             "Ring designs deliberately offset each ring's radius (breaking simple periodicity) -- real behavior "
             "(right figure) is governed by discrete holes-per-ring count, not a clean lattice symmetry.",
             ha="center", fontsize=9, color="#333", linespacing=1.6)
    out = os.path.join(HERE, "geometry_intuition_structure.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}")


def fig2_real_consequence():
    df = pd.read_csv(GAZE_METRICS_CSV, dtype={"M": str})
    df = df[df.M == "2.0"]
    rows = []
    for d in DESIGNS:
        r = df[(df.family == d["family"]) & (df.spacing_params == d["spacing_params"]) &
              (df.a_hole_um == A_HOLE_UM) & (df.N_requested == N_REQUESTED)]
        assert len(r) == 1, f"expected exactly 1 real row for {d['label']}, got {len(r)}"
        rows.append(r.iloc[0])

    labels = [d["label"].replace("\n", " ") for d in DESIGNS]
    blind = [float(r.time_weighted_blind_pct) for r in rows]
    ghost = [float(r.time_weighted_ghost_pct) for r in rows]
    colors = [d["color"] for d in DESIGNS]

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.5))
    x = np.arange(len(DESIGNS))
    axes[0].bar(x, blind, color=colors)
    axes[0].set_xticks(x); axes[0].set_xticklabels(labels, fontsize=8.3, rotation=12)
    axes[0].set_ylabel("time-weighted blind %")
    axes[0].set_title("Real blind %, same pitch (4000um), M=2D", fontsize=11, fontweight="bold")
    for xi, v in zip(x, blind):
        axes[0].annotate(f"{v:.2f}%", (xi, v), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9)
    axes[0].spines[["top", "right"]].set_visible(False)

    axes[1].bar(x, ghost, color=colors)
    axes[1].set_xticks(x); axes[1].set_xticklabels(labels, fontsize=8.3, rotation=12)
    axes[1].set_ylabel("time-weighted ghost %")
    axes[1].set_title("Real ghost %, same pitch (4000um), M=2D", fontsize=11, fontweight="bold")
    for xi, v in zip(x, ghost):
        axes[1].annotate(f"{v:.2f}%", (xi, v), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9)
    axes[1].spines[["top", "right"]].set_visible(False)

    fig.suptitle("Real consequence: same spacing, only lattice type differs\n"
                "(array_data/theoretical_data/gaze_weighted_metrics.csv, not recomputed here)",
                fontsize=12.5, fontweight="bold")
    fig.text(0.5, -0.02,
             "Hexagonal: 0% blind AND 0% ghost -- no tradeoff. Ring-of-8 trades blind% for a real 7.58% ghost "
             "(more holes/ring = closer together = more simultaneous illumination) -- the discrete-angular-gap "
             "tension hexagonal's continuous-feeling packing avoids.",
             ha="center", fontsize=9, color="#333", linespacing=1.5)
    plt.tight_layout(rect=[0, 0.04, 1, 0.92])
    out = os.path.join(HERE, "geometry_intuition_real_consequence.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    fig1_structure()
    fig2_real_consequence()
