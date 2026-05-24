"""Rank-4 Moser-style lattice Z[i, zeta_m].

Points: a + b*i + c*zeta + d*i*zeta with a, b, c, d in a coefficient box.
Visible embedding to C: zeta -> exp(i*pi*k/n) where (k, n) parametrizes
the chosen primitive root of unity. Default zeta = exp(i*pi/3) (a 6th
root) reproduces the "Moser-ish" lattice in the user's writeup.

Unit vectors are integer 4-tuples (a,b,c,d) whose visible-embedding
squared norm equals 1 *exactly* (via sympy). The visible embedding is
in general dense in C as a Z-module - we restrict to a finite coefficient
box for cut-and-project.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import sympy as sp

from eud.core.algebra import is_exact_unit, make_squared_distance
from eud.core.edges import count_edges
from eud.core.lattice import LatticeBasis
from eud.core.pointset import Candidate, LatticePoint


@dataclass(frozen=True)
class MoserParams:
    """Parameters for the rank-4 Moser construction Z + Zi + Z*zeta + Zi*zeta.

    Attributes:
        zeta_order: the order m of the primitive root of unity
            zeta = exp(2*pi*i / m). Default m=6 (so zeta = exp(i*pi/3)).
            Must NOT be in {1, 2, 4} - those make the Z-basis degenerate
            (e.g. for m=4, zeta = i, so (1, i, i, -1) is Z-rank 2 not 4
            and distinct integer coefficients can project to the same
            complex number, producing nonsensical "edges").
        coeff_bound: half-width B of the coefficient box {-B,...,B}^4.
    """

    zeta_order: int = 6
    coeff_bound: int = 2

    def __post_init__(self) -> None:
        if self.zeta_order in {1, 2, 4}:
            raise ValueError(
                f"zeta_order={self.zeta_order} makes the Moser basis "
                "(1, i, zeta, i*zeta) Z-linearly dependent. Use m in "
                "{3, 5, 6, 7, 8, 9, 10, 11, 12, ...}."
            )


def _zeta_symbolic(m: int) -> sp.Expr:
    return sp.exp(sp.I * 2 * sp.pi / m)


def _zeta_numeric(m: int) -> complex:
    return complex(sp.N(_zeta_symbolic(m)))


def basis(params: MoserParams) -> LatticeBasis:
    """Visible-embedding basis (1, i, zeta, i*zeta) as complex floats."""
    zeta_c = _zeta_numeric(params.zeta_order)
    visible = (1 + 0j, 0 + 1j, zeta_c, 1j * zeta_c)
    return LatticeBasis(visible=visible, hidden=(), name=f"moser_zeta{params.zeta_order}")


def squared_distance_symbolic(params: MoserParams):
    """Exact symbolic |a + bi + c*zeta + d*i*zeta|^2 of an integer diff."""
    zeta = _zeta_symbolic(params.zeta_order)
    return make_squared_distance((sp.S(1), sp.I, zeta, sp.I * zeta))


def enumerate_unit_vectors(
    params: MoserParams,
    *,
    search_bound: int = 3,
    float_tol: float = 1e-7,
) -> list[tuple[int, int, int, int]]:
    """Enumerate all integer 4-tuples in [-search_bound, search_bound]^4
    with visible squared norm *exactly* 1.

    Strategy: cheap float pre-filter, then sympy exact verification on
    survivors. Sympy `simplify` is far too slow in the inner loop.
    """
    zeta_c = _zeta_numeric(params.zeta_order)

    candidates: list[tuple[int, int, int, int]] = []
    for a, b, c, d in itertools.product(range(-search_bound, search_bound + 1), repeat=4):
        if (a, b, c, d) == (0, 0, 0, 0):
            continue
        z = a + b * 1j + c * zeta_c + d * 1j * zeta_c
        d2 = z.real * z.real + z.imag * z.imag
        if abs(d2 - 1.0) < float_tol:
            candidates.append((a, b, c, d))

    sd = squared_distance_symbolic(params)
    units: list[tuple[int, int, int, int]] = []
    for u in candidates:
        if is_exact_unit(u, sd):
            units.append(u)
    units.sort()
    return units


def enumerate_points(params: MoserParams) -> list[LatticePoint]:
    """All lattice points with coefficients in {-B,...,B}^4."""
    B = params.coeff_bound
    lat = basis(params)
    pts: list[LatticePoint] = []
    for a, b, c, d in itertools.product(range(-B, B + 1), repeat=4):
        coeffs = (a, b, c, d)
        xy = lat.project(coeffs)
        pts.append(LatticePoint(coeffs=coeffs, xy=xy))
    return pts


def build(params: MoserParams) -> Candidate:
    """Build a Moser candidate: enumerate points + units + edges."""
    points = enumerate_points(params)
    units = enumerate_unit_vectors(params)
    edges = count_edges(points, units)
    return Candidate(
        family="moser",
        params={
            "zeta_order": params.zeta_order,
            "coeff_bound": params.coeff_bound,
        },
        points=points,
        edges=edges,
        unit_vectors=units,
    )


def build_in_visible_disk(
    params: MoserParams,
    *,
    radius: float,
    coeff_bound: int | None = None,
) -> Candidate:
    """Moser lattice points with visible-plane image inside a disk.

    The (1, i, zeta, i*zeta) Z-module is dense in C when zeta is irrational,
    so we filter the integer-coefficient box by the visible-plane radius
    threshold. This produces a finite, roughly disk-shaped point set; the
    distinct integer coefficients all project to distinct visible points
    when zeta_order is in {3, 5, 6, 7, 8, ...} (excluded 1, 2, 4 by params).
    """
    cb = coeff_bound if coeff_bound is not None else params.coeff_bound
    lat = basis(params)
    pts: list[LatticePoint] = []
    seen_xy: dict[tuple[int, int], int] = {}
    r2 = radius * radius
    grid_scale = 1e9
    for a, b, c, d in itertools.product(range(-cb, cb + 1), repeat=4):
        coeffs = (a, b, c, d)
        x, y = lat.project(coeffs)
        if x * x + y * y > r2:
            continue
        # de-duplicate against accidental hits on identical visible points
        # (shouldn't happen for valid zeta_order but cheap to guard).
        key = (round(x * grid_scale), round(y * grid_scale))
        if key in seen_xy:
            continue
        seen_xy[key] = 1
        pts.append(LatticePoint(coeffs=coeffs, xy=(x, y)))
    units = enumerate_unit_vectors(params)
    edges = count_edges(pts, units)
    return Candidate(
        family="moser_hex",
        params={
            "zeta_order": params.zeta_order,
            "coeff_bound": cb,
            "visible_radius": radius,
        },
        points=pts,
        edges=edges,
        unit_vectors=units,
    )


def sweep_for_n(
    n_target: int,
    *,
    zeta_orders: tuple[int, ...] = (6, 12),
    coeff_bound: int = 4,
    radius_grid: tuple[float, ...] = (
        2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
    ),
) -> dict | None:
    """Best Moser-style construction for a target n, by visible-disk + greedy peel.

    For each zeta_order and each radius, build the visible-disk Moser
    candidate, then greedy-peel down to n_target if it has at least n_target
    points. Returns a JSONL-ready dict for the densest result, or None if
    no radius yielded enough points.
    """
    from eud.search.prune import greedy_peel

    best: dict | None = None
    for zo in zeta_orders:
        for r in radius_grid:
            cand = build_in_visible_disk(
                MoserParams(zeta_order=zo, coeff_bound=coeff_bound),
                radius=r,
                coeff_bound=coeff_bound,
            )
            if cand.n < n_target:
                continue
            sub = greedy_peel(cand, n_target)
            row = {
                "family": "moser_hex",
                "n": sub.n,
                "e": sub.e,
                "density": sub.density,
                "zeta_order": zo,
                "coeff_bound": coeff_bound,
                "visible_radius": r,
                "induced_from_n": cand.n,
            }
            if best is None or row["e"] > best["e"]:
                best = row
            break  # smaller radius is faster and usually denser after greedy
    return best


def sweep_frontier(
    *,
    n_values: list[int],
    zeta_orders: tuple[int, ...] = (6, 12),
    coeff_bound: int = 4,
    radius_grid: tuple[float, ...] = (
        2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0,
    ),
) -> list[dict]:
    """Best Moser candidate per n in `n_values`. JSONL-ready.

    Caches one candidate per (zeta_order, radius) so a single sweep over
    [25..1000] is O(|zeta_orders| * |radius_grid|) builds rather than
    O(|n_values| * |zeta_orders| * |radius_grid|).
    """
    from eud.search.prune import greedy_peel

    cache: dict[tuple[int, float], "Candidate"] = {}
    for zo in zeta_orders:
        for r in radius_grid:
            cand = build_in_visible_disk(
                MoserParams(zeta_order=zo, coeff_bound=coeff_bound),
                radius=r,
                coeff_bound=coeff_bound,
            )
            cache[(zo, r)] = cand

    rows: list[dict] = []
    for n in n_values:
        best_row: dict | None = None
        for zo in zeta_orders:
            # smallest radius >= n is usually densest; check the next 1-2 too.
            sorted_radii = sorted(radius_grid)
            for r in sorted_radii:
                cand = cache[(zo, r)]
                if cand.n < n:
                    continue
                sub = greedy_peel(cand, n)
                row = {
                    "family": "moser_hex",
                    "n": sub.n,
                    "e": sub.e,
                    "density": sub.density,
                    "zeta_order": zo,
                    "coeff_bound": coeff_bound,
                    "visible_radius": r,
                    "induced_from_n": cand.n,
                }
                if best_row is None or row["e"] > best_row["e"]:
                    best_row = row
                break
        if best_row is not None:
            rows.append(best_row)
    return rows
