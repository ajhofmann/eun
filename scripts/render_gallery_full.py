"""Render the full visual story for the strict baseline and v2 wins.

Outputs (all under data/gallery/):
  baseline/triangular_r{r}.png             hex disks for r in 1..6
  baseline/moser_zeta{6|12}_r{r}.png       Moser visible-disk samples
  baseline/erdos_grid_K{K}_m{mx}x{my}.png  rectangular grid examples
  baseline/strict_frontier.png             multi-family frontier plot
  baseline/strict_density.png              density vs n plot
  baseline/source_share.png                stacked-area "who owns each n"

  wins/compare_n{n}.png                    5-way side-by-side per n
  wins/v2_wins.png                         absolute + relative deltas
  wins/winv2_zeta12_n{n}.png               final pruned subgraph (already had)
"""

from __future__ import annotations

# ruff: noqa: I001

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

from eud.core.io import read_candidate
from eud.families.cyclotomic import CyclotomicParams
from eud.families.cyclotomic import build as build_cyc
from eud.families.erdos_grid import (
    ErdosGridParams,
    best_grid_for_n,
    build as build_grid,
)
from eud.families.engel_moser import EngelMoserParams, build as build_engel_moser
from eud.families.moser import MoserParams, build_in_visible_disk
from eud.families.moser_ring import MoserRingParams, enumerate_unit_vectors as ring_units
from eud.families.triangular import TriangularParams, build as build_tri
from eud.search.prune import greedy_peel

GALLERY = Path("data/gallery")
BASELINE_DIR = GALLERY / "baseline"
WINS_DIR = GALLERY / "wins"
SHOWCASE_DIR = GALLERY / "showcase"
SOTA_DIR = GALLERY / "sota"
SAWIN_DIR = GALLERY / "sawin"
for d in (BASELINE_DIR, WINS_DIR, SHOWCASE_DIR, SOTA_DIR, SAWIN_DIR):
    d.mkdir(parents=True, exist_ok=True)

COLORS = {
    "known_bounds": "#444444",
    "erdos_grid": "#1f77b4",
    "triangular": "#2ca02c",
    "moser_hex": "#d62728",
    "engel_2025": "#7c3aed",
    "cyclotomic": "#ff8800",
    "winv2": "#ff8800",
}


def render_candidate_to_ax(cand, ax, *, title=None, point_size=6.0, line_width=0.4, line_alpha=0.7, edge_color=None):
    edge_color = edge_color or "#1f77b4"
    xs = [p.xy[0] for p in cand.points]
    ys = [p.xy[1] for p in cand.points]
    segments = [(cand.points[i].xy, cand.points[j].xy) for i, j in cand.edges]
    if segments:
        ax.add_collection(
            LineCollection(
                segments,
                colors=edge_color,
                linewidths=line_width,
                alpha=line_alpha,
            )
        )
    ax.scatter(xs, ys, s=point_size, color="#111", zorder=3)
    ax.set_aspect("equal")
    ax.margins(0.08)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_alpha(0.2)
    if title:
        ax.set_title(title, fontsize=10)


# -----------------------------------------------------------------------------
# Baseline family showcases
# -----------------------------------------------------------------------------

def render_triangular_disks() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    for ax, r in zip(axes.flat, [1, 2, 3, 4, 5, 6], strict=True):
        c = build_tri(TriangularParams(radius=r, shape="hex"))
        render_candidate_to_ax(
            c,
            ax,
            title=f"Z[\u03b6_6] hex disk r={r} | n={c.n} e={c.e} e/n={c.density:.3f}",
            edge_color=COLORS["triangular"],
        )
    fig.suptitle(
        "Triangular / Eisenstein lattice: 6 unit vectors, closed-form n=3r²+3r+1, e=9r²+3r",
        fontsize=12,
    )
    fig.tight_layout()
    out = BASELINE_DIR / "triangular_disks.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")

def render_moser_disks() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    cfgs = [(6, 2.0), (6, 3.0), (6, 4.0), (12, 2.0), (12, 3.0), (12, 4.0)]
    for ax, (zo, r) in zip(axes.flat, cfgs, strict=True):
        c = build_in_visible_disk(
            MoserParams(zeta_order=zo, coeff_bound=4), radius=r, coeff_bound=4
        )
        render_candidate_to_ax(
            c,
            ax,
            title=f"Moser \u03b6_{zo} visible-disk r={r} | n={c.n} e={c.e} e/n={c.density:.3f}",
            edge_color=COLORS["moser_hex"],
        )
    fig.suptitle(
        "Rank-4 Moser lattice Z[i, \u03b6]: 12 unit vectors, points filtered by visible-plane disk",
        fontsize=12,
    )
    fig.tight_layout()
    out = BASELINE_DIR / "moser_disks.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


def render_engel_moser_disks() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    cfgs = [(2, 2.0), (2, 3.0), (3, 3.0), (3, 4.0), (4, 4.0), (4, 5.0)]
    for ax, (cb, r) in zip(axes.flat, cfgs, strict=True):
        c = build_engel_moser(
            EngelMoserParams(coeff_bound=cb, visible_radius=r, window_kind="visible_disk")
        )
        render_candidate_to_ax(
            c,
            ax,
            title=f"Engel Moser cb={cb} r={r} | n={c.n} e={c.e} |U|={len(c.unit_vectors)}",
            edge_color=COLORS["engel_2025"],
        )
    fig.suptitle(
        "Engel et al. rank-4 Moser lattice: 18 exact unit vectors (right SOTA target)",
        fontsize=12,
    )
    fig.tight_layout()
    out = BASELINE_DIR / "engel_moser_disks.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


def render_erdos_grids() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    cfgs = [
        (1, 5, 5),  # K=1 baseline 5x5 grid (just unit lattice spacing)
        (5, 5, 5),  # K=5 (8 directions)
        (5, 5, 10),  # K=5 rectangular
        (25, 7, 7),  # K=25 multi-direction
        (65, 10, 10),  # K=65 (16 directions, dominates large n)
        (65, 13, 13),
    ]
    for ax, (K, mx, my) in zip(axes.flat, cfgs, strict=True):
        c = build_grid(ErdosGridParams(K=K, m=max(mx, my), mx=mx, my=my))
        title = (
            f"K={K} grid {mx}\u00d7{my} | n={c.n} e={c.e} e/n={c.density:.3f}"
        )
        render_candidate_to_ax(c, ax, title=title, edge_color=COLORS["erdos_grid"])
    fig.suptitle(
        "Erd\u0151s grid: integer points in m\u00d7m' box, unit distance \u221aK; K = product of primes \u22611 mod 4",
        fontsize=12,
    )
    fig.tight_layout()
    out = BASELINE_DIR / "erdos_grids.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


def render_strict_frontier_plots(frontier_path: Path = Path("data/frontiers/baseline.jsonl")) -> None:
    rows = [json.loads(line) for line in frontier_path.read_text().splitlines() if line.strip()]
    by_source: dict[str, list[tuple[int, int]]] = {}
    for r in rows:
        n, e = int(r["n"]), int(r["e"])
        by_source.setdefault(r.get("source", "?"), []).append((n, e))

    v2 = []
    v2_path = Path("data/runs/zeta12_winv2_vs_strict.json")
    if v2_path.exists():
        v2 = json.loads(v2_path.read_text())

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for src, pts in by_source.items():
        pts.sort()
        ns, es = zip(*pts, strict=True)
        axes[0].plot(ns, es, ".", label=src, color=COLORS.get(src, "#999999"), markersize=3)
        axes[1].plot(ns, [e / n for n, e in pts], ".", label=src, color=COLORS.get(src, "#999999"), markersize=3)

    if v2:
        wins = [r for r in v2 if r["wins"]]
        v2_ns = [r["k"] for r in wins]
        v2_es = [r["best_e"] for r in wins]
        axes[0].plot(v2_ns, v2_es, "*", color=COLORS["winv2"], markersize=14, label="\u03b6_12 v2 wins", markeredgecolor="black", markeredgewidth=0.5)
        axes[1].plot(
            v2_ns,
            [e / n for n, e in zip(v2_ns, v2_es, strict=True)],
            "*",
            color=COLORS["winv2"],
            markersize=14,
            label="\u03b6_12 v2 wins",
            markeredgecolor="black",
            markeredgewidth=0.5,
        )

    axes[0].set_title("Strict best-of-finite-construction frontier", fontsize=12)
    axes[0].set_xlabel("n")
    axes[0].set_ylabel("u(n) lower bound")
    axes[0].legend(fontsize=9)
    axes[0].grid(alpha=0.3)

    axes[1].set_title("Density e/n vs n", fontsize=12)
    axes[1].set_xlabel("n")
    axes[1].set_ylabel("e / n")
    axes[1].legend(fontsize=9)
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    out = BASELINE_DIR / "strict_frontier.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


def render_source_share(frontier_path: Path = Path("data/frontiers/baseline.jsonl")) -> None:
    """Stacked area: which family contributes the strict baseline at each n."""
    rows = [json.loads(line) for line in frontier_path.read_text().splitlines() if line.strip()]
    rows.sort(key=lambda r: r["n"])
    sources = list({r["source"] for r in rows})
    order = ["known_bounds", "engel_2025", "erdos_grid", "triangular", "moser_hex"]
    sources.sort(key=lambda s: order.index(s) if s in order else 999)

    ns = [r["n"] for r in rows]
    fig, ax = plt.subplots(figsize=(12, 4.5))
    seg_start = 0
    src_at_n = [r["source"] for r in rows]
    spans: list[tuple[int, int, str]] = []
    for i in range(1, len(ns) + 1):
        if i == len(ns) or src_at_n[i] != src_at_n[seg_start]:
            spans.append((ns[seg_start], ns[i - 1], src_at_n[seg_start]))
            seg_start = i

    seen = set()
    for n0, n1, src in spans:
        ax.barh(
            0,
            n1 - n0 + 1,
            left=n0,
            color=COLORS.get(src, "#999"),
            edgecolor="white",
            linewidth=0.0,
            label=src if src not in seen else None,
        )
        seen.add(src)

    ax.set_yticks([])
    ax.set_xlim(0, max(ns))
    ax.set_xlabel("n")
    ax.set_title("Which construction/source wins the published baseline at each n", fontsize=12)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=4, fontsize=10)
    fig.tight_layout()
    out = BASELINE_DIR / "source_share.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


# -----------------------------------------------------------------------------
# Per-n comparisons (triangular, Engel Moser, grid, uploaded Moser, ζ12 window)
# -----------------------------------------------------------------------------

def render_per_n_comparisons() -> None:
    comparison_scales = [
        {
            "slug": 545,
            "label": "original scale",
            "tri_radius": 13,
            "grid_m": 24,
            "engel": EngelMoserParams(coeff_bound=2, visible_radius=4.0),
            "uploaded": {"coeff_bound": 2, "radius": 4.0},
            "zeta12": CyclotomicParams(m=12, coeff_bound=4, R=2.0, window_kind="ball"),
            "figsize": (24, 5.2),
            "dpi": 130,
            "point_size": 2.0,
            "line_width": 0.2,
            "line_alpha": 0.65,
        },
        {
            "slug": 6061,
            "label": "medium scale",
            "tri_radius": 45,
            "grid_m": 78,
            "engel": EngelMoserParams(coeff_bound=5, visible_radius=5.0),
            "uploaded": {"coeff_bound": 4, "radius": 8.0},
            "zeta12": CyclotomicParams(m=12, coeff_bound=5, R=3.5, window_kind="box"),
            "figsize": (34, 7.0),
            "dpi": 160,
            "point_size": 0.8,
            "line_width": 0.16,
            "line_alpha": 0.55,
        },
        {
            "slug": 13669,
            "label": "large scale",
            "tri_radius": 67,
            "grid_m": 117,
            "engel": EngelMoserParams(coeff_bound=5, visible_radius=10.0),
            "uploaded": {"coeff_bound": 5, "radius": 10.0},
            "zeta12": CyclotomicParams(m=12, coeff_bound=8, R=4.0, window_kind="box"),
            "figsize": (42, 8.5),
            "dpi": 180,
            "point_size": 0.45,
            "line_width": 0.12,
            "line_alpha": 0.45,
        },
    ]

    for scale in comparison_scales:
        fig, axes = plt.subplots(1, 5, figsize=scale["figsize"])
        point_size = scale["point_size"]
        line_width = scale["line_width"]
        line_alpha = scale["line_alpha"]

        # Natural hex disk: no peeling, so the plotted shape keeps its symmetry.
        c_tri = build_tri(TriangularParams(radius=scale["tri_radius"], shape="hex"))
        render_candidate_to_ax(
            c_tri, axes[0],
            title=f"triangular hex r={scale['tri_radius']}\nn={c_tri.n} e={c_tri.e} e/n={c_tri.density:.3f}",
            edge_color=COLORS["triangular"], point_size=point_size, line_width=line_width, line_alpha=line_alpha,
        )

        # Natural Engel visible disk: no greedy peel.
        engel_params = scale["engel"]
        c_engel = build_engel_moser(engel_params)
        render_candidate_to_ax(
            c_engel, axes[1],
            title=(
                f"Engel Moser 18-unit r={engel_params.visible_radius:g}\n"
                f"n={c_engel.n} e={c_engel.e} e/n={c_engel.density:.3f}"
            ),
            edge_color=COLORS["engel_2025"], point_size=point_size, line_width=line_width, line_alpha=line_alpha,
        )

        # Natural square Erdős grid.
        grid_m = scale["grid_m"]
        gp, _ = best_grid_for_n(grid_m * grid_m)
        c_grid = build_grid(gp)
        render_candidate_to_ax(
            c_grid, axes[2],
            title=f"erdos_grid K={gp.K} {gp.width}\u00d7{gp.height}\nn={c_grid.n} e={c_grid.e} e/n={c_grid.density:.3f}",
            edge_color=COLORS["erdos_grid"], point_size=point_size, line_width=line_width, line_alpha=line_alpha,
        )

        # Uploaded construction: natural Z[i, rho] disk, no greedy peel.
        uploaded_params = scale["uploaded"]
        c_uploaded = build_in_visible_disk(
            MoserParams(zeta_order=6, coeff_bound=uploaded_params["coeff_bound"]),
            radius=uploaded_params["radius"],
            coeff_bound=uploaded_params["coeff_bound"],
        )
        render_candidate_to_ax(
            c_uploaded, axes[3],
            title=(
                f"uploaded Z[i,\u03c1] B={uploaded_params['coeff_bound']} R={uploaded_params['radius']:g}\n"
                f"n={c_uploaded.n} e={c_uploaded.e} e/n={c_uploaded.density:.3f}"
            ),
            edge_color="#111111", point_size=point_size, line_width=line_width, line_alpha=line_alpha,
        )

        # Natural centered Z[ζ_12] window, no translation / peel.
        zeta12_params = scale["zeta12"]
        c_zeta12 = build_cyc(zeta12_params)
        zeta12_window = (
            f"{zeta12_params.window_kind} R={zeta12_params.R:g}"
            if zeta12_params.translation_seed is None
            else f"{zeta12_params.window_kind} R={zeta12_params.R:g} seed={zeta12_params.translation_seed}"
        )
        render_candidate_to_ax(
            c_zeta12, axes[4],
            title=(
                f"\u03b6_12 {zeta12_window}\n"
                f"n={c_zeta12.n} e={c_zeta12.e} e/n={c_zeta12.density:.3f}"
            ),
            edge_color=COLORS["winv2"], point_size=point_size, line_width=line_width, line_alpha=line_alpha,
        )
        delta = c_uploaded.e - c_grid.e
        title = (
            f"{scale['label']}: natural symmetric windows/shapes; "
            f"uploaded e={c_uploaded.e}, Erdős grid e={c_grid.e} (\u0394={delta:+d})"
        )
        fig.suptitle(title, fontsize=13)
        fig.tight_layout(w_pad=2.0, rect=(0, 0, 1, 0.94))
        out = WINS_DIR / f"compare_n{scale['slug']}.png"
        fig.savefig(out, dpi=scale["dpi"])
        plt.close(fig)
        print(f"wrote {out}")


# -----------------------------------------------------------------------------
# Standalone v2 wins panel
# -----------------------------------------------------------------------------

def render_v2_wins_panel() -> None:
    summary = json.loads(Path("data/runs/zeta12_winv2_vs_strict.json").read_text())
    wins = [r for r in summary if r["wins"]]
    if not wins:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
    ns = [r["k"] for r in wins]
    deltas = [r["delta"] for r in wins]
    pcts = [100.0 * r["delta"] / r["strict_baseline_e"] for r in wins]
    bars = axes[0].bar(range(len(ns)), deltas, color=COLORS["winv2"])
    axes[0].set_xticks(range(len(ns)))
    axes[0].set_xticklabels(map(str, ns))
    axes[0].set_xlabel("n")
    axes[0].set_ylabel("\u0394 over strict baseline")
    axes[0].set_title("Z[\u03b6_12] v2 wins: absolute edge gain")
    for b, d in zip(bars, deltas, strict=True):
        axes[0].text(b.get_x() + b.get_width() / 2, b.get_height(), f"+{d}", ha="center", va="bottom", fontsize=9)
    bars = axes[1].bar(range(len(ns)), pcts, color="#1f77b4")
    axes[1].set_xticks(range(len(ns)))
    axes[1].set_xticklabels(map(str, ns))
    axes[1].set_xlabel("n")
    axes[1].set_ylabel("% over strict baseline")
    axes[1].set_title("Z[\u03b6_12] v2 wins: relative gain")
    for b, p in zip(bars, pcts, strict=True):
        axes[1].text(b.get_x() + b.get_width() / 2, b.get_height(), f"+{p:.1f}%", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    out = WINS_DIR / "v2_wins.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


def render_sota_correction_panels() -> None:
    """Plot the honest result: ζ_12 beats our reproducible baseline but trails Engel."""
    rows = json.loads(Path("data/runs/zeta12_vs_published_sota.json").read_text())
    ns = [r["n"] for r in rows]
    zeta = [r["e_zeta12_best"] for r in rows]
    repro = [r["reproducible_baseline_e"] for r in rows]
    engel = [r["published_sota_e"] for r in rows]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(ns, repro, "o-", color=COLORS["moser_hex"], label="reproducible baseline")
    ax.plot(ns, zeta, "*-", color=COLORS["winv2"], markersize=11, label="Z[ζ_12] best")
    engel_ns = [n for n, e in zip(ns, engel, strict=True) if e is not None]
    engel_es = [e for e in engel if e is not None]
    ax.plot(
        engel_ns,
        engel_es,
        "s-",
        color=COLORS["engel_2025"],
        label="Engel et al. 2025 published SOTA",
    )
    ax.set_xlabel("n")
    ax.set_ylabel("edges")
    ax.set_title("Z[ζ_12] beats our reproducible baseline but trails published SOTA through n=100")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = SOTA_DIR / "published_vs_ours.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")

    sota_rows = [r for r in rows if r["published_sota_e"] is not None]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = list(range(len(sota_rows)))
    gaps = [r["delta_vs_published_sota"] for r in sota_rows]
    bars = ax.bar(x, gaps, color=COLORS["engel_2025"])
    ax.axhline(0, color="#222", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([str(r["n"]) for r in sota_rows])
    ax.set_xlabel("n")
    ax.set_ylabel("Z[ζ_12] best - Engel et al. 2025")
    ax.set_title("Gap to published SOTA (negative means we trail)")
    for bar, gap in zip(bars, gaps, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(gap),
            ha="center",
            va="top" if gap < 0 else "bottom",
            fontsize=9,
        )
    fig.tight_layout()
    out = SOTA_DIR / "gap_to_engel.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


def render_engel_reproduction_panel() -> None:
    """Show how close our Engel-Moser visible-disk reproduction gets to Table 2."""
    path = Path("data/runs/engel_moser_reproduce.json")
    if not path.exists():
        return
    rows = json.loads(path.read_text())

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, row in zip(axes.flat, rows, strict=False):
        cand = read_candidate(row["candidate_file"])
        delta = row["delta_vs_engel_2025"]
        title = (
            f"n={row['k']} ours={row['e']} Engel={row['engel_2025_e']} "
            f"Δ={delta:+d}\ncb={row['params']['coeff_bound']} r={row['params']['visible_radius']}"
        )
        render_candidate_to_ax(
            cand,
            ax,
            title=title,
            edge_color=COLORS["engel_2025"],
            point_size=8,
            line_width=0.45,
        )
    fig.suptitle(
        "Reproducing Engel et al. 2025 with the 18-unit Moser lattice: 5 exact matches, n=64 off by one",
        fontsize=12,
    )
    fig.tight_layout()
    out = SOTA_DIR / "engel_reproduction.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


def render_engel_beyond_panel() -> None:
    """Plot Engel-Moser candidates beyond the published n<=100 table."""

    path = Path("data/runs/engel_moser_beyond_100.json")
    if not path.exists():
        return
    rows = json.loads(path.read_text())
    ns = [r["k"] for r in rows]
    es = [r["e"] for r in rows]
    deltas = [r["delta_vs_reproducible_baseline"] for r in rows]

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
    axes[0].plot(ns, es, "o-", color=COLORS["engel_2025"], label="Engel-Moser beam")
    axes[0].plot(
        ns,
        [r["reproducible_baseline_e"] for r in rows],
        "s--",
        color="#666",
        label="repo fallback frontier",
    )
    axes[0].set_xlabel("n")
    axes[0].set_ylabel("edges")
    axes[0].set_title("Engel-Moser beyond the published n≤100 table")
    axes[0].legend(fontsize=9)
    axes[0].grid(alpha=0.3)

    bars = axes[1].bar(range(len(ns)), deltas, color=COLORS["engel_2025"])
    axes[1].set_xticks(range(len(ns)))
    axes[1].set_xticklabels([str(n) for n in ns])
    axes[1].set_xlabel("n")
    axes[1].set_ylabel("edge gain over repo fallback")
    axes[1].set_title("Why Engel-Moser should replace the fallback baseline")
    for bar, delta in zip(bars, deltas, strict=True):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"+{delta}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    fig.tight_layout()
    out = SOTA_DIR / "engel_beyond_100.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


def render_moser_ring_probe_panel() -> None:
    """Summarize the first bounded common-denominator Moser ring probe."""

    path = Path("data/runs/moser_ring_probe.jsonl")
    if not path.exists():
        return
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    best_by_k: dict[int, int] = {}
    for row in rows:
        for pruned in row.get("pruned", []):
            k = int(pruned["n"])
            best_by_k[k] = max(best_by_k.get(k, 0), int(pruned["e"]))

    denom_powers = [0, 1, 2]
    unit_counts = [
        len(ring_units(MoserRingParams(denom_power=k, unit_search_bound=4 * (3**k))))
        for k in denom_powers
    ]
    ks = sorted(best_by_k)
    engel_targets = {25: 72, 36: 119, 49: 180, 64: 252, 81: 338, 100: 439}

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
    axes[0].bar([str(k) for k in denom_powers], unit_counts, color="#8b5cf6")
    axes[0].set_xlabel("common denominator exponent k")
    axes[0].set_ylabel("exact unit directions found")
    axes[0].set_title("Moser ring exposes more exact unit directions")
    for i, count in enumerate(unit_counts):
        axes[0].text(i, count, str(count), ha="center", va="bottom", fontsize=9)

    axes[1].plot(ks, [best_by_k[k] for k in ks], "o-", color="#8b5cf6", label="Moser ring greedy")
    axes[1].plot(ks, [engel_targets[k] for k in ks], "s--", color=COLORS["engel_2025"], label="Engel 2025")
    axes[1].set_xlabel("n")
    axes[1].set_ylabel("edges")
    axes[1].set_title("First ring probe: more units, weaker search/window")
    axes[1].legend(fontsize=9)
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    out = SOTA_DIR / "moser_ring_probe.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


def render_found_graph_panels() -> None:
    """Render the actual saved graph candidates found by the current searches."""

    beyond_path = Path("data/runs/engel_moser_beyond_100.json")
    if beyond_path.exists():
        rows = json.loads(beyond_path.read_text())
        fig, axes = plt.subplots(2, 3, figsize=(15, 9))
        for ax, row in zip(axes.flat, rows, strict=False):
            cand = read_candidate(row["candidate_file"])
            title = (
                f"Engel-Moser n={row['k']} e={cand.e} e/n={cand.density:.3f}\n"
                f"Δ fallback={row['delta_vs_reproducible_baseline']:+d}"
            )
            render_candidate_to_ax(
                cand,
                ax,
                title=title,
                edge_color=COLORS["engel_2025"],
                point_size=4.0,
                line_width=0.25,
            )
        fig.suptitle(
            "Current Engel-Moser found graphs beyond Engel et al.'s published n≤100 table",
            fontsize=12,
        )
        fig.tight_layout()
        out = SOTA_DIR / "engel_beyond_graphs.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"wrote {out}")

    ring_path = Path("data/runs/moser_ring_probe_best.json")
    if ring_path.exists():
        rows = json.loads(ring_path.read_text())
        fig, axes = plt.subplots(2, 3, figsize=(15, 9))
        for ax, row in zip(axes.flat, rows, strict=False):
            cand = read_candidate(row["candidate_file"])
            params = row["params"]
            title = (
                f"Moser ring n={row['k']} e={cand.e} e/n={cand.density:.3f}\n"
                f"|U|={row['n_units']} 3^{params['denom_power']} cb={params['coeff_bound']} r={params['visible_radius']}"
            )
            render_candidate_to_ax(
                cand,
                ax,
                title=title,
                edge_color="#8b5cf6",
                point_size=4.0,
                line_width=0.25,
            )
        fig.suptitle("Current Moser ring greedy-pruned probe graphs", fontsize=12)
        fig.tight_layout()
        out = SOTA_DIR / "moser_ring_graphs.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"wrote {out}")


def render_sawin_openai_concept_panels() -> None:
    """Conceptual images explaining why Sawin/OpenAI is asymptotic, not finite."""
    ns = [10**k for k in range(1, 13)]
    erdos_like = [n * (1 + 0.35 * (1 / max(1, math.log(math.log(max(n, 3)))))) for n in ns]
    # The actual Sawin witness starts astronomically later; this curve is illustrative.
    sawin_shape = [n ** 1.014 for n in ns]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].loglog(ns, erdos_like, "o-", label="classical finite-shape baseline")
    axes[0].loglog(ns, sawin_shape, "s-", label="n^1.014 asymptotic slope")
    axes[0].axvline(10**12, color="#999", linestyle="--", label="far below known Sawin witness scale")
    axes[0].set_xlabel("n (log scale)")
    axes[0].set_ylabel("edge lower bound scale (illustrative)")
    axes[0].set_title("Sawin/OpenAI is an asymptotic direction, not a small-n recipe")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3, which="both")

    labels = ["triangular", "Z[ζ_12]", "Engel Moser", "Moser ring / future"]
    units = [6, 12, 18, 24]
    caps = [u / 2 for u in units]
    bars = axes[1].bar(labels, caps, color=["#2ca02c", "#ff8800", "#7c3aed", "#888888"])
    axes[1].set_ylabel("interior density cap |U|/2")
    axes[1].set_title("Finite wins need more local unit directions and better pruning")
    axes[1].tick_params(axis="x", rotation=18)
    for bar, cap, u in zip(bars, caps, units, strict=True):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"|U|={u}\ncap={cap:g}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    fig.tight_layout()
    out = SAWIN_DIR / "finite_vs_asymptotic.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.axis("off")
    text = (
        "What we take from Sawin/OpenAI:\n\n"
        "1. Algebraic number fields are the right search space.\n"
        "2. Asymptotic towers are not directly visible at n≤1000.\n"
        "3. For finite n, the local recipe matters: unit-vector count, boundary loss,\n"
        "   window shape, and graph search/canonization dominate.\n"
        "4. Engel's 18-unit Moser lattice is the right finite bridge: it is algebraic,\n"
        "   exact, and already matches the published beam-search table when paired\n"
        "   with better local search.\n\n"
        "Next credible attempt: implement Engel-style children/parents/canonization,\n"
        "then probe the Moser ring for degree >18."
    )
    ax.text(0.02, 0.95, text, va="top", ha="left", fontsize=13, family="monospace")
    out = SAWIN_DIR / "lessons_panel.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")

# -----------------------------------------------------------------------------
# Showcase: window-translation effect
# -----------------------------------------------------------------------------

def render_window_translation_showcase(n: int = 100) -> None:
    """Show how window choice (ball, box, ellipsoid, zonotope) and translation seed
    change the dense-k subgraph extracted from the same lattice.
    """
    cfgs = [
        ("ball", None, 3.0),
        ("ball", 7, 3.0),
        ("box", None, 3.0),
        ("box", 1, 3.0),
        ("ellipsoid", None, 3.0),
        ("zonotope", None, 3.0),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    for ax, (window_kind, seed, R) in zip(axes.flat, cfgs, strict=True):
        c = build_cyc(
            CyclotomicParams(
                m=12, coeff_bound=4, R=R, window_kind=window_kind, translation_seed=seed
            )
        )
        sub = greedy_peel(c, n)
        title = (
            f"window={window_kind} R={R} seed={seed}\n"
            f"seed_n={c.n} -> peeled n={sub.n} e={sub.e} e/n={sub.density:.3f}"
        )
        render_candidate_to_ax(sub, ax, title=title, edge_color="#ff8800", point_size=8)
    fig.suptitle(
        f"Z[\u03b6_12] window-shape sensitivity at n={n}: same lattice, 6 windows, greedy-peeled",
        fontsize=12,
    )
    fig.tight_layout()
    out = SHOWCASE_DIR / f"window_translation_n{n}.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    print("=== baseline family showcases ===")
    render_triangular_disks()
    render_moser_disks()
    render_engel_moser_disks()
    render_erdos_grids()
    render_strict_frontier_plots()
    render_source_share()

    print("\n=== per-n win comparisons ===")
    render_per_n_comparisons()
    render_v2_wins_panel()
    render_sota_correction_panels()
    render_engel_reproduction_panel()
    render_engel_beyond_panel()
    render_moser_ring_probe_panel()
    render_found_graph_panels()

    print("\n=== showcase: window translation ===")
    for n in [100, 144, 196]:
        render_window_translation_showcase(n)

    print("\n=== Sawin/OpenAI concept panels ===")
    render_sawin_openai_concept_panels()


if __name__ == "__main__":
    main()
