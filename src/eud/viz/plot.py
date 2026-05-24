"""Convenience plot functions on top of viz/draw."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def plot_frontier_n_e(
    rows: list[dict],
    out_path: str | Path,
    *,
    title: str = "Frontier: e vs n",
    figsize: tuple[float, float] = (8, 5),
    dpi: int = 150,
) -> Path:
    """Plot e vs n grouped by family/source."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(str(r.get("source", r.get("family", "?"))), []).append(r)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    for label, gr in sorted(groups.items()):
        gr_sorted = sorted(gr, key=lambda r: r["n"])
        xs = [r["n"] for r in gr_sorted]
        ys = [r["e"] for r in gr_sorted]
        ax.plot(xs, ys, marker="o", linewidth=0.8, label=label)
    ax.set_xlabel("n")
    ax.set_ylabel("e")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(p)
    plt.close(fig)
    return p


def plot_frontier_density(
    rows: list[dict],
    out_path: str | Path,
    *,
    title: str = "Frontier: e/n vs n",
    figsize: tuple[float, float] = (8, 5),
    dpi: int = 150,
    log_x: bool = True,
) -> Path:
    """Plot density e/n vs n (often log-x)."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(str(r.get("source", r.get("family", "?"))), []).append(r)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    for label, gr in sorted(groups.items()):
        gr_sorted = sorted(gr, key=lambda r: r["n"])
        xs = [r["n"] for r in gr_sorted]
        ys = [r["e"] / r["n"] for r in gr_sorted]
        ax.plot(xs, ys, marker="o", linewidth=0.8, label=label)
    if log_x:
        ax.set_xscale("log")
    ax.set_xlabel("n")
    ax.set_ylabel("e / n")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(p)
    plt.close(fig)
    return p
