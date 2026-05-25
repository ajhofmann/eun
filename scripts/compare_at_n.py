"""Render a side-by-side comparison of Erdős grid, our best (Engel-Moser),
and the uploaded Sawin/OpenAI-style Z[i, ρ] disk at a target n.

The script searches each family for the parameter setting whose natural
(unpruned) vertex count is closest to the target, then renders them
in one panel with matched cosmetics for honest visual comparison.
"""

from __future__ import annotations

# ruff: noqa: I001

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

from eud.families.engel_moser import EngelMoserParams, build as build_engel_moser  # noqa: E402
from eud.families.erdos_grid import (  # noqa: E402
    ErdosGridParams,
    best_grid_for_n_rect,
    build as build_grid,
    edges_analytic,
    primes_one_mod_four,
    squarefree_products_of_pmod1,
)
from eud.families.moser import MoserParams, build_in_visible_disk  # noqa: E402
from eud.search.prune import greedy_peel  # noqa: E402


WINS_DIR = Path("data/gallery/wins")
WINS_DIR.mkdir(parents=True, exist_ok=True)


def find_best_grid_near(n_target: int, window: int = 60) -> ErdosGridParams:
    """Best Erdős grid for any n in [n_target - window, n_target + window]."""
    primes = primes_one_mod_four(200)
    K_candidates = [1, *squarefree_products_of_pmod1(primes, 10_000_000)]
    best: tuple[int, int, ErdosGridParams] | None = None
    for n in range(max(4, n_target - window), n_target + window + 1):
        for mx in range(2, n + 1):
            if n % mx:
                continue
            my = n // mx
            if my < mx:
                break
            for K in K_candidates:
                e = edges_analytic(ErdosGridParams(K=K, mx=mx, my=my))
                key = (-e, abs(n - n_target))
                if best is None or key < (-best[1], abs(best[0] - n_target)):
                    best = (n, e, ErdosGridParams(K=K, mx=mx, my=my, m=max(mx, my)))
    assert best is not None
    return best[2]


def find_engel_for_peel(n_target: int):
    """Pick the Engel-Moser configuration whose greedy-peel to n_target
    yields the most edges. We try every (cb, r) whose seed size is in
    [n_target, 2.5 * n_target] and peel each, keeping the densest."""
    grid = [
        (cb, r)
        for cb in range(2, 8)
        for r in [2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 4.0, 4.5, 5.0, 6.0]
    ]
    best = None
    for cb, r in grid:
        params = EngelMoserParams(coeff_bound=cb, visible_radius=r)
        c = build_engel_moser(params)
        if c.n < n_target or c.n > int(2.5 * n_target):
            continue
        peeled = greedy_peel(c, n_target)
        if best is None or peeled.e > best[2]:
            best = (params, c, peeled.e, peeled)
    assert best is not None, "no Engel-Moser seed at or above n_target"
    return best  # (params, seed, peeled_e, peeled)


def find_uploaded_for_peel(n_target: int):
    grid = [
        (cb, r)
        for cb in range(2, 8)
        for r in [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0]
    ]
    best = None
    for cb, r in grid:
        c = build_in_visible_disk(
            MoserParams(zeta_order=6, coeff_bound=cb), radius=r, coeff_bound=cb
        )
        if c.n < n_target or c.n > int(2.5 * n_target):
            continue
        peeled = greedy_peel(c, n_target)
        if best is None or peeled.e > best[2]:
            best = ((cb, r), c, peeled.e, peeled)
    assert best is not None, "no uploaded seed at or above n_target"
    return best


def find_grid_for_peel(n_target: int):
    """Two-pass grid search. Pass 1 uses the analytic edge formula to rank
    (mx, my, K) seeds with size in [n_target, 1.8*n_target]. Pass 2 builds
    and peels only the top-ranked seeds (since peeling away ~30 % of the
    densest seeds can lose a lot of edges; we keep several candidates)."""
    primes = primes_one_mod_four(60)  # 5,13,17,29,37,41,53
    K_candidates = [1, *squarefree_products_of_pmod1(primes, 200_000)]

    seeds: list[tuple[int, ErdosGridParams]] = []
    for size in range(n_target, int(1.8 * n_target) + 1):
        for mx in range(2, size + 1):
            if size % mx:
                continue
            my = size // mx
            if my < mx:
                break
            if my > 3 * mx:
                continue
            for K in K_candidates:
                p = ErdosGridParams(K=K, mx=mx, my=my, m=max(mx, my))
                e_seed = edges_analytic(p)
                if e_seed <= 0:
                    continue
                seeds.append((e_seed, p))

    seeds.sort(key=lambda t: -t[0])
    best = None
    for _, p in seeds[:80]:
        cand = build_grid(p)
        peeled = greedy_peel(cand, n_target)
        if best is None or peeled.e > best[2]:
            best = (p, cand, peeled.e, peeled)
    assert best is not None
    return best


def render_to_ax(cand, ax, *, title, color, point_size=2.2, line_width=0.22, line_alpha=0.65):
    xs = [p.xy[0] for p in cand.points]
    ys = [p.xy[1] for p in cand.points]
    segs = [(cand.points[i].xy, cand.points[j].xy) for i, j in cand.edges]
    if segs:
        ax.add_collection(
            LineCollection(segs, colors=color, linewidths=line_width, alpha=line_alpha)
        )
    ax.scatter(xs, ys, s=point_size, color="#111", zorder=3)
    ax.set_aspect("equal")
    ax.margins(0.08)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_alpha(0.25)
    ax.set_title(title, fontsize=11)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=865)
    parser.add_argument("--window", type=int, default=60)
    parser.add_argument(
        "--out", type=Path, default=WINS_DIR / "compare_grid_best_uploaded_n865.png"
    )
    parser.add_argument(
        "--peel-out",
        type=Path,
        default=WINS_DIR / "compare_grid_best_uploaded_n865_peeled.png",
    )
    args = parser.parse_args()

    n_target = args.n
    print(f"finding best peel-source for n={n_target}")

    grid_params, c_grid, _, _ = find_grid_for_peel(n_target)
    print(
        f"  erdos_grid seed: K={grid_params.K} {grid_params.width}x{grid_params.height} "
        f"n={c_grid.n} e={c_grid.e} e/n={c_grid.density:.3f}"
    )

    engel_params, c_engel, _, _ = find_engel_for_peel(n_target)
    print(
        f"  engel_moser seed: cb={engel_params.coeff_bound} r={engel_params.visible_radius} "
        f"n={c_engel.n} e={c_engel.e} e/n={c_engel.density:.3f} |U|={len(c_engel.unit_vectors)}"
    )

    upl_cb_r, c_upl, _, _ = find_uploaded_for_peel(n_target)
    upl_cb, upl_r = upl_cb_r
    print(
        f"  uploaded Z[i,rho] seed: B={upl_cb} R={upl_r} "
        f"n={c_upl.n} e={c_upl.e} e/n={c_upl.density:.3f}"
    )

    fig, axes = plt.subplots(1, 3, figsize=(18, 6.4))
    render_to_ax(
        c_grid, axes[0],
        title=(
            f"Erdős grid K={grid_params.K} {grid_params.width}×{grid_params.height}\n"
            f"n={c_grid.n}  e={c_grid.e}  e/n={c_grid.density:.3f}  |U|={len(c_grid.unit_vectors)}"
        ),
        color="#1f77b4",
    )
    render_to_ax(
        c_engel, axes[1],
        title=(
            f"our best: Engel–Moser 18-unit (cb={engel_params.coeff_bound}, r={engel_params.visible_radius:g})\n"
            f"n={c_engel.n}  e={c_engel.e}  e/n={c_engel.density:.3f}  |U|={len(c_engel.unit_vectors)}"
        ),
        color="#7c3aed",
    )
    render_to_ax(
        c_upl, axes[2],
        title=(
            f"uploaded Sawin/OpenAI Z[i,ρ] (B={upl_cb}, R={upl_r:g})\n"
            f"n={c_upl.n}  e={c_upl.e}  e/n={c_upl.density:.3f}  |U|={len(c_upl.unit_vectors)}"
        ),
        color="#222222",
    )

    fig.suptitle(
        f"Near n={n_target}: same scale, natural windows. "
        f"Engel–Moser e={c_engel.e} vs grid e={c_grid.e} (Δ={c_engel.e - c_grid.e:+d}) "
        f"vs uploaded e={c_upl.e} (Δ={c_engel.e - c_upl.e:+d})",
        fontsize=13,
    )
    fig.tight_layout(w_pad=2.0, rect=(0, 0, 1, 0.94))
    fig.savefig(args.out, dpi=140)
    plt.close(fig)
    print(f"\nwrote {args.out}")

    p_grid = greedy_peel(c_grid, n_target)
    p_engel = greedy_peel(c_engel, n_target)
    p_upl = greedy_peel(c_upl, n_target)
    print(
        f"\npeeled to n={n_target}:\n"
        f"  erdos_grid: e={p_grid.e} e/n={p_grid.density:.3f}\n"
        f"  engel_moser: e={p_engel.e} e/n={p_engel.density:.3f}\n"
        f"  uploaded Z[i,rho]: e={p_upl.e} e/n={p_upl.density:.3f}"
    )

    fig, axes = plt.subplots(1, 3, figsize=(18, 6.4))
    render_to_ax(
        p_grid, axes[0],
        title=(
            f"Erdős grid K={grid_params.K} {grid_params.width}×{grid_params.height} → peeled to n={n_target}\n"
            f"e={p_grid.e}  e/n={p_grid.density:.3f}"
        ),
        color="#1f77b4",
    )
    render_to_ax(
        p_engel, axes[1],
        title=(
            f"our best: Engel–Moser (cb={engel_params.coeff_bound}, r={engel_params.visible_radius:g}) → peeled to n={n_target}\n"
            f"e={p_engel.e}  e/n={p_engel.density:.3f}"
        ),
        color="#7c3aed",
    )
    render_to_ax(
        p_upl, axes[2],
        title=(
            f"uploaded Z[i,ρ] (B={upl_cb}, R={upl_r:g}) → peeled to n={n_target}\n"
            f"e={p_upl.e}  e/n={p_upl.density:.3f}"
        ),
        color="#222222",
    )
    fig.suptitle(
        f"Same n={n_target} via greedy peel: "
        f"Engel–Moser e={p_engel.e} vs grid e={p_grid.e} (Δ={p_engel.e - p_grid.e:+d}) "
        f"vs uploaded e={p_upl.e} (Δ={p_engel.e - p_upl.e:+d})",
        fontsize=13,
    )
    fig.tight_layout(w_pad=2.0, rect=(0, 0, 1, 0.94))
    fig.savefig(args.peel_out, dpi=140)
    plt.close(fig)
    print(f"wrote {args.peel_out}")


if __name__ == "__main__":
    main()
