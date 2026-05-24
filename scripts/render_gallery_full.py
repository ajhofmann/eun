"""Render the full visual story for the strict baseline and v2 wins.

Outputs (all under data/gallery/):
  baseline/triangular_r{r}.png             hex disks for r in 1..6
  baseline/moser_zeta{6|12}_r{r}.png       Moser visible-disk samples
  baseline/erdos_grid_K{K}_m{mx}x{my}.png  rectangular grid examples
  baseline/strict_frontier.png             multi-family frontier plot
  baseline/strict_density.png              density vs n plot
  baseline/source_share.png                stacked-area "who owns each n"

  wins/winv2_compare_n{n}.png              5-way side-by-side per n in {64..196}
  wins/v2_wins.png                         absolute + relative deltas
  wins/winv2_zeta12_n{n}.png               final pruned subgraph (already had)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

matplotlib.use("Agg")

from eud.benchmarks.compare import load_frontier
from eud.core.io import read_candidate
from eud.families.cyclotomic import CyclotomicParams
from eud.families.cyclotomic import build as build_cyc
from eud.families.erdos_grid import ErdosGridParams, build as build_grid, best_grid_for_n_rect
from eud.families.moser import MoserParams, build_in_visible_disk
from eud.families.triangular import TriangularParams, build as build_tri
from eud.search.prune import greedy_peel
from eud.viz.draw import draw_candidate

GALLERY = Path("data/gallery")
BASELINE_DIR = GALLERY / "baseline"
WINS_DIR = GALLERY / "wins"
SHOWCASE_DIR = GALLERY / "showcase"
for d in (BASELINE_DIR, WINS_DIR, SHOWCASE_DIR):
    d.mkdir(parents=True, exist_ok=True)

COLORS = {
    "known_bounds": "#444444",
    "erdos_grid": "#1f77b4",
    "triangular": "#2ca02c",
    "moser_hex": "#d62728",
    "cyclotomic": "#ff8800",
    "winv2": "#ff8800",
}


def render_candidate_to_ax(cand, ax, *, title=None, point_size=6.0, line_width=0.4, line_alpha=0.7, edge_color=None):
    edge_color = edge_color or "#1f77b4"
    xs = [p.xy[0] for p in cand.points]
    ys = [p.xy[1] for p in cand.points]
    for i, j in cand.edges:
        x0, y0 = cand.points[i].xy
        x1, y1 = cand.points[j].xy
        ax.plot([x0, x1], [y0, y1], color=edge_color, linewidth=line_width, alpha=line_alpha)
    ax.scatter(xs, ys, s=point_size, color="#111", zorder=3)
    ax.set_aspect("equal")
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
    axes[0].set_xlabel("n"); axes[0].set_ylabel("u(n) lower bound")
    axes[0].legend(fontsize=9); axes[0].grid(alpha=0.3)

    axes[1].set_title("Density e/n vs n", fontsize=12)
    axes[1].set_xlabel("n"); axes[1].set_ylabel("e / n")
    axes[1].legend(fontsize=9); axes[1].grid(alpha=0.3)

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
    sources.sort(key=lambda s: ["known_bounds", "erdos_grid", "triangular", "moser_hex"].index(s) if s in ("known_bounds", "erdos_grid", "triangular", "moser_hex") else 999)

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
    ax.set_title("Which construction wins the strict baseline at each n", fontsize=12)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=4, fontsize=10)
    fig.tight_layout()
    out = BASELINE_DIR / "source_share.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


# -----------------------------------------------------------------------------
# Per-n win comparisons (5 panels: triangular, moser, grid, ζ12 v1, ζ12 v2)
# -----------------------------------------------------------------------------

def render_per_n_comparisons() -> None:
    fr = load_frontier(Path("data/frontiers/baseline.jsonl"))
    v2_summary = json.loads(Path("data/runs/zeta12_winv2_vs_strict.json").read_text())
    v2_by_k = {r["k"]: r for r in v2_summary}

    for n in [49, 64, 81, 100, 121, 144, 169, 196]:
        fig, axes = plt.subplots(1, 5, figsize=(20, 4.5))

        # Triangular best
        from eud.families.triangular import best_for_n as tri_best
        label, p, e_tri = tri_best(n)
        if p["shape"] == "hex":
            c_tri = greedy_peel(build_tri(TriangularParams(radius=p["radius"], shape="hex")), n)
        elif p["shape"] == "parallelogram":
            c_tri = greedy_peel(build_tri(TriangularParams(shape="parallelogram", sx=p["sx"], sy=p["sy"])), n)
        else:
            c_tri = greedy_peel(build_tri(TriangularParams(shape="strip", sx=p["sx"], sy=p["sy"])), n)
        render_candidate_to_ax(
            c_tri, axes[0],
            title=f"triangular ({label})\nn={c_tri.n} e={c_tri.e} e/n={c_tri.density:.3f}",
            edge_color=COLORS["triangular"], point_size=8,
        )

        # Moser best
        from eud.families.moser import sweep_for_n as moser_best
        mrow = moser_best(n)
        c_moser = greedy_peel(
            build_in_visible_disk(
                MoserParams(zeta_order=mrow["zeta_order"], coeff_bound=4),
                radius=mrow["visible_radius"], coeff_bound=4,
            ), n,
        )
        render_candidate_to_ax(
            c_moser, axes[1],
            title=(
                f"moser_hex \u03b6_{mrow['zeta_order']} r={mrow['visible_radius']}\n"
                f"n={c_moser.n} e={c_moser.e} e/n={c_moser.density:.3f}"
            ),
            edge_color=COLORS["moser_hex"], point_size=8,
        )

        # Erdős grid best
        gp, e_grid = best_grid_for_n_rect(n)
        c_grid = greedy_peel(build_grid(gp), n)
        render_candidate_to_ax(
            c_grid, axes[2],
            title=f"erdos_grid K={gp.K} {gp.width}\u00d7{gp.height}\nn={c_grid.n} e={c_grid.e} e/n={c_grid.density:.3f}",
            edge_color=COLORS["erdos_grid"], point_size=8,
        )

        # ζ_12 v1 (centered ball R=3.0)
        c_v1 = greedy_peel(
            build_cyc(CyclotomicParams(m=12, coeff_bound=4, R=3.0, window_kind="ball")),
            n,
        )
        render_candidate_to_ax(
            c_v1, axes[3],
            title=f"\u03b6_12 v1 (ball R=3, centered)\nn={c_v1.n} e={c_v1.e} e/n={c_v1.density:.3f}",
            edge_color=COLORS["winv2"], point_size=8,
        )

        # ζ_12 v2 (best per n from window-explore)
        v2 = v2_by_k.get(n, {})
        if v2:
            c_v2 = read_candidate(Path(f"data/candidates/winv2_zeta12_n{n}.json"))
            render_candidate_to_ax(
                c_v2, axes[4],
                title=(
                    f"\u03b6_12 v2 ({v2['window_kind']} R={v2['R']}, "
                    f"seed={v2['translation_seed']})\n"
                    f"n={c_v2.n} e={c_v2.e} e/n={c_v2.density:.3f}"
                ),
                edge_color="#000", point_size=8,
            )
        else:
            axes[4].axis("off")

        baseline_e = fr.best_edges_at(n) or 0
        delta = (v2.get("best_e", 0) or 0) - baseline_e if v2 else 0
        title = (
            f"n={n}: strict baseline e={baseline_e}; "
            f"\u03b6_12 v2 e={v2.get('best_e', '?')} (\u0394={delta:+d})"
            if v2 else f"n={n}: strict baseline e={baseline_e}"
        )
        fig.suptitle(title, fontsize=13)
        fig.tight_layout()
        out = WINS_DIR / f"compare_n{n}.png"
        fig.savefig(out, dpi=110)
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
    axes[0].set_xticks(range(len(ns))); axes[0].set_xticklabels(map(str, ns))
    axes[0].set_xlabel("n"); axes[0].set_ylabel("\u0394 over strict baseline")
    axes[0].set_title("Z[\u03b6_12] v2 wins: absolute edge gain")
    for b, d in zip(bars, deltas, strict=True):
        axes[0].text(b.get_x() + b.get_width() / 2, b.get_height(), f"+{d}", ha="center", va="bottom", fontsize=9)
    bars = axes[1].bar(range(len(ns)), pcts, color="#1f77b4")
    axes[1].set_xticks(range(len(ns))); axes[1].set_xticklabels(map(str, ns))
    axes[1].set_xlabel("n"); axes[1].set_ylabel("% over strict baseline")
    axes[1].set_title("Z[\u03b6_12] v2 wins: relative gain")
    for b, p in zip(bars, pcts, strict=True):
        axes[1].text(b.get_x() + b.get_width() / 2, b.get_height(), f"+{p:.1f}%", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    out = WINS_DIR / "v2_wins.png"
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
    render_erdos_grids()
    render_strict_frontier_plots()
    render_source_share()

    print("\n=== per-n win comparisons ===")
    render_per_n_comparisons()
    render_v2_wins_panel()

    print("\n=== showcase: window translation ===")
    for n in [100, 144, 196]:
        render_window_translation_showcase(n)


if __name__ == "__main__":
    main()
