"""Reproduce the uploaded Z[i, rho] unit-distance graph.

The plotted point set is

    z = a + b i + c rho + d i rho

with rho = exp(i*pi/3), a,b,c,d in {-2,-1,0,1,2}, and |z| < 4.
Edges join pairs whose exact algebraic distance is 1.
"""

from __future__ import annotations

# ruff: noqa: I001

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from eud.core.io import write_candidate  # noqa: E402
from eud.families.moser import MoserParams, build_in_visible_disk  # noqa: E402


OUT = Path("data/candidates")


def radius_label(radius: float) -> str:
    return str(int(radius)) if radius.is_integer() else str(radius).replace(".", "p")


def render_uploaded_style(
    *,
    coeff_bound: int,
    radius: float,
    stem: str,
    write_svg: bool,
    write_png: bool,
) -> None:
    params = MoserParams(zeta_order=6, coeff_bound=coeff_bound)
    candidate = build_in_visible_disk(params, radius=radius, coeff_bound=coeff_bound)
    json_path = OUT / f"{stem}.json"
    write_candidate(candidate, json_path)

    xs = [point.xy[0] for point in candidate.points]
    ys = [point.xy[1] for point in candidate.points]

    fig, ax = plt.subplots(figsize=(10, 10), dpi=120)
    for i, j in candidate.edges:
        x0, y0 = candidate.points[i].xy
        x1, y1 = candidate.points[j].xy
        ax.plot([x0, x1], [y0, y1], color="blue", linewidth=0.28, alpha=0.55)

    ax.scatter(xs, ys, s=5, color="orange", edgecolors="none", zorder=3)
    ax.set_aspect("equal")
    ax.set_xlabel("Re(z)")
    ax.set_ylabel("Im(z)")
    ax.set_title(
        r"$a + bi + c\rho + di\rho$, "
        rf"$a,b,c,d \in \{{-{coeff_bound},\ldots,{coeff_bound}\}}$, "
        rf"$|z| < {radius:g}$"
    )
    ax.grid(True, alpha=0.2)
    fig.tight_layout()

    written = [json_path]
    if write_svg:
        svg_path = OUT / f"{stem}.svg"
        fig.savefig(svg_path)
        written.append(svg_path)
    if write_png:
        png_path = OUT / f"{stem}.png"
        fig.savefig(png_path)
        written.append(png_path)
    plt.close(fig)

    print(
        f"wrote {', '.join(str(path) for path in written)} "
        f"(n={candidate.n}, e={candidate.e}, |U|={len(candidate.unit_vectors)})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coeff-bound", type=int, default=2)
    parser.add_argument("--radius", type=float, default=4.0)
    parser.add_argument("--stem", default=None)
    parser.add_argument("--no-svg", action="store_true")
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args()

    stem = args.stem or (
        f"uploaded_moser_disk_B{args.coeff_bound}_R{radius_label(args.radius)}"
    )
    render_uploaded_style(
        coeff_bound=args.coeff_bound,
        radius=args.radius,
        stem=stem,
        write_svg=not args.no_svg,
        write_png=not args.no_png,
    )


if __name__ == "__main__":
    main()
