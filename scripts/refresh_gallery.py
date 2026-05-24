"""Generate gallery PNGs for the strict baseline and v2 wins."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from eud.core.io import read_candidate
from eud.viz.draw import draw_candidate

GALLERY = Path("data/gallery")
CANDIDATES = Path("data/candidates")


def plot_strict_frontier(
    frontier_path: Path = Path("data/frontiers/baseline.jsonl"),
    out_path: Path = GALLERY / "strict_frontier.png",
    n_max: int = 1000,
) -> None:
    rows = [json.loads(line) for line in frontier_path.read_text().splitlines() if line.strip()]
    by_source: dict[str, list[tuple[int, int]]] = {}
    for r in rows:
        n = int(r["n"])
        if n > n_max:
            continue
        by_source.setdefault(r.get("source", "?"), []).append((n, int(r["e"])))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    colors = {
        "known_bounds": "#444444",
        "erdos_grid": "#1f77b4",
        "triangular": "#2ca02c",
        "moser_hex": "#d62728",
    }

    for src, pts in by_source.items():
        pts.sort()
        ns, es = zip(*pts, strict=True)
        axes[0].plot(ns, es, ".", label=src, color=colors.get(src, "#999999"), markersize=3)
        axes[1].plot(ns, [e / n for n, e in pts], ".", label=src, color=colors.get(src, "#999999"), markersize=3)

    # Overlay v2 wins
    v2_path = Path("data/runs/zeta12_winv2_vs_strict.json")
    if v2_path.exists():
        v2 = json.loads(v2_path.read_text())
        v2_ns = [r["k"] for r in v2 if r["wins"]]
        v2_es = [r["best_e"] for r in v2 if r["wins"]]
        axes[0].plot(v2_ns, v2_es, "*", color="#ff8800", markersize=12, label="ζ_12 v2 wins")
        axes[1].plot(
            v2_ns,
            [e / n for n, e in zip(v2_ns, v2_es, strict=True)],
            "*",
            color="#ff8800",
            markersize=12,
            label="ζ_12 v2 wins",
        )

    axes[0].set_title("Strict best-of-finite-construction frontier")
    axes[0].set_xlabel("n")
    axes[0].set_ylabel("u(n) lower bound")
    axes[0].legend(fontsize=9)
    axes[0].grid(alpha=0.3)

    axes[1].set_title("Density e/n vs n")
    axes[1].set_xlabel("n")
    axes[1].set_ylabel("e / n")
    axes[1].legend(fontsize=9)
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"wrote {out_path}")


def plot_v2_wins_table(
    summary_path: Path = Path("data/runs/zeta12_winv2_vs_strict.json"),
    out_path: Path = GALLERY / "v2_wins.png",
) -> None:
    data = json.loads(summary_path.read_text())
    wins = [r for r in data if r["wins"]]

    if not wins:
        print(f"no wins to plot at {summary_path}; skipping")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ns = [r["k"] for r in wins]
    deltas = [r["delta"] for r in wins]
    pcts = [100.0 * r["delta"] / r["strict_baseline_e"] for r in wins]

    bars = axes[0].bar(range(len(ns)), deltas, color="#ff8800")
    axes[0].set_xticks(range(len(ns)))
    axes[0].set_xticklabels([str(n) for n in ns])
    axes[0].set_xlabel("n")
    axes[0].set_ylabel("Δ (edges over strict baseline)")
    axes[0].set_title("Z[ζ_12] v2 wins (absolute)")
    for bar, delta in zip(bars, deltas, strict=True):
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"+{delta}",
            ha="center", va="bottom", fontsize=9,
        )

    bars = axes[1].bar(range(len(ns)), pcts, color="#1f77b4")
    axes[1].set_xticks(range(len(ns)))
    axes[1].set_xticklabels([str(n) for n in ns])
    axes[1].set_xlabel("n")
    axes[1].set_ylabel("% improvement over strict baseline")
    axes[1].set_title("Z[ζ_12] v2 wins (relative)")
    for bar, pct in zip(bars, pcts, strict=True):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"+{pct:.1f}%",
            ha="center", va="bottom", fontsize=9,
        )

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"wrote {out_path}")


def render_all_v2_candidates() -> None:
    for p in sorted(CANDIDATES.glob("winv2_zeta12_n*.json")):
        out = p.with_suffix(".png")
        c = read_candidate(p)
        draw_candidate(c, out)
        print(f"wrote {out}  n={c.n} e={c.e}")


def main() -> None:
    plot_strict_frontier()
    plot_v2_wins_table()
    render_all_v2_candidates()


if __name__ == "__main__":
    main()
