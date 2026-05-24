"""Matplotlib renderers for unit-distance graphs."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from eud.core.pointset import Candidate  # noqa: E402


def draw_candidate(
    candidate: Candidate,
    out_path: str | Path,
    *,
    title: str | None = None,
    point_size: float = 12.0,
    line_width: float = 0.6,
    line_alpha: float = 0.7,
    figsize: tuple[float, float] = (8.0, 8.0),
    dpi: int = 200,
) -> Path:
    """Render `candidate` to a PNG/SVG/PDF (inferred from extension)."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    xs = [pt.xy[0] for pt in candidate.points]
    ys = [pt.xy[1] for pt in candidate.points]

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    for i, j in candidate.edges:
        x0, y0 = candidate.points[i].xy
        x1, y1 = candidate.points[j].xy
        ax.plot([x0, x1], [y0, y1], color="#1f77b4", linewidth=line_width, alpha=line_alpha)

    ax.scatter(xs, ys, s=point_size, color="#111", zorder=3)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.2)

    default_title = (
        f"{candidate.family} | n={candidate.n} e={candidate.e} "
        f"e/n={candidate.density:.3f}"
    )
    ax.set_title(title or default_title, fontsize=10)
    fig.tight_layout()
    fig.savefig(p)
    plt.close(fig)
    return p


def draw_frontier(
    rows: list[dict],
    out_path: str | Path,
    *,
    x_key: str = "n",
    y_key: str = "e",
    label_key: str | None = "family",
    figsize: tuple[float, float] = (8.0, 5.0),
    dpi: int = 150,
    log_x: bool = False,
    log_y: bool = False,
    title: str | None = None,
) -> Path:
    """Plot a frontier table grouped by `label_key` (e.g. 'family')."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    if label_key is None:
        xs = [r[x_key] for r in rows]
        ys = [r[y_key] for r in rows]
        ax.plot(xs, ys, marker="o", linewidth=0.8)
    else:
        groups: dict[str, list[dict]] = {}
        for r in rows:
            groups.setdefault(str(r.get(label_key, "?")), []).append(r)
        for label, gr in sorted(groups.items()):
            gr_sorted = sorted(gr, key=lambda r: r[x_key])
            xs = [r[x_key] for r in gr_sorted]
            ys = [r[y_key] for r in gr_sorted]
            ax.plot(xs, ys, marker="o", linewidth=0.8, label=label)
        ax.legend(fontsize=8)

    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")
    ax.set_xlabel(x_key)
    ax.set_ylabel(y_key)
    ax.grid(True, alpha=0.3)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    fig.savefig(p)
    plt.close(fig)
    return p
