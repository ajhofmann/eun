"""Triangular / Eisenstein lattice Z[zeta_6], zeta_6 = exp(i pi / 3).

This is the ring of integers of Q(zeta_3) = Q(sqrt -3), but written in
the "hexagonal coordinate" basis (1, zeta_6) instead of the standard
(1, omega) basis (omega = exp(2 pi i / 3)). Translating: zeta_6 = 1 + omega,
so the two bases are related by a unimodular change of coordinates.

The advantage of (1, zeta_6) is that the 6 sixth roots of unity become
the standard short vectors:

    {(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)}

(corresponding to 1, zeta_6, zeta_6^2, -1, -zeta_6, -zeta_6^2).
Squared norm in this basis: |a + b * zeta_6|^2 = a^2 + a b + b^2.

A *filled hex disk* of radius r is the set of (a, b) in Z^2 with
|a|, |b|, |a + b| <= r - i.e. the convex hull of the 6 unit vectors
scaled by r in the L_inf-on-hex-coords norm. It has:
    n_hex(r) = 1 + 6 * (1 + 2 + ... + r) = 3 r^2 + 3 r + 1
    e_hex(r) = 9 r^2 + 3 r                                (closed form)

This is the densest "natural" subgraph; for n that isn't of this form we
greedy-peel from a slightly oversized hex disk.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from math import cos, pi, sin

import sympy as sp

from eud.core.algebra import is_exact_unit, make_squared_distance
from eud.core.edges import count_edges
from eud.core.lattice import LatticeBasis
from eud.core.pointset import Candidate, LatticePoint
from eud.search.prune import greedy_peel

UNIT_VECTORS_TRIANGULAR: list[tuple[int, int]] = [
    (1, 0),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (0, -1),
    (1, -1),
]


@dataclass(frozen=True)
class TriangularParams:
    """Parameters for a Z[omega] hex region.

    Attributes:
        radius: hex-disk radius r (the filled hex disk has 3r^2+3r+1 points).
        shape: "hex" | "parallelogram" | "strip".
        sx, sy: extents for parallelogram / strip windows.
    """

    radius: int = 4
    shape: str = "hex"
    sx: int = 0
    sy: int = 0


def basis() -> LatticeBasis:
    """Visible basis (1, zeta_6), zeta_6 = exp(i pi / 3)."""
    zeta_6 = complex(cos(pi / 3), sin(pi / 3))
    return LatticeBasis(visible=(1 + 0j, zeta_6), hidden=(), name="Z[zeta_6]")


def squared_distance_symbolic():
    """Exact symbolic |a + b * zeta_6|^2 of an integer pair (1, zeta_6 basis)."""
    zeta_6 = sp.exp(sp.I * sp.pi / 3)
    return make_squared_distance((sp.S(1), zeta_6))


def hex_disk(r: int) -> list[tuple[int, int]]:
    """Filled hex disk of radius r in (1, zeta_6) basis.

    Constraint: max(|a|, |b|, |a + b|) <= r. The graph distance in the
    triangular lattice with neighbor set {(1,0),(0,1),(-1,1),(-1,0),(0,-1),(1,-1)}
    coincides with this norm; (1, 1) and (-1, -1) need 2 hops.
    """
    pts: list[tuple[int, int]] = []
    for a in range(-r, r + 1):
        for b in range(-r, r + 1):
            if abs(a) <= r and abs(b) <= r and abs(a + b) <= r:
                pts.append((a, b))
    return pts


def parallelogram(sx: int, sy: int) -> list[tuple[int, int]]:
    """The {0,..,sx-1} x {0,..,sy-1} parallelogram in Z[omega]."""
    return [(a, b) for a in range(sx) for b in range(sy)]


def strip(sx: int, sy: int) -> list[tuple[int, int]]:
    """{-sx,..,sx} x {0,..,sy-1} strip (long in x, narrow in y)."""
    return [(a, b) for a in range(-sx, sx + 1) for b in range(sy)]


def _coords_for_shape(p: TriangularParams) -> list[tuple[int, int]]:
    if p.shape == "hex":
        return hex_disk(p.radius)
    if p.shape == "parallelogram":
        return parallelogram(p.sx, p.sy)
    if p.shape == "strip":
        return strip(p.sx, p.sy)
    raise ValueError(f"unknown shape: {p.shape}")


def hex_disk_n_e(r: int) -> tuple[int, int]:
    """Closed-form (n, e) for the filled hex disk of radius r.

    n = 3 r^2 + 3 r + 1
    e = 9 r^2 + 3 r       (each interior edge is counted once)
    """
    return (3 * r * r + 3 * r + 1, 9 * r * r + 3 * r)


def build(params: TriangularParams) -> Candidate:
    """Build the triangular candidate for a given region shape."""
    lat = basis()
    coords = _coords_for_shape(params)
    points: list[LatticePoint] = []
    for a, b in coords:
        xy = lat.project((a, b))
        points.append(LatticePoint(coeffs=(a, b), xy=xy))
    edges = count_edges(points, UNIT_VECTORS_TRIANGULAR)
    return Candidate(
        family="triangular",
        params={
            "radius": params.radius,
            "shape": params.shape,
            "sx": params.sx,
            "sy": params.sy,
        },
        points=points,
        edges=edges,
        unit_vectors=list(UNIT_VECTORS_TRIANGULAR),
    )


def verify_unit_vectors() -> bool:
    """Sanity-check at import time that all 6 directions are exactly unit."""
    sd = squared_distance_symbolic()
    return all(is_exact_unit(u, sd) for u in UNIT_VECTORS_TRIANGULAR)


def best_for_n(
    n_target: int,
    *,
    radius_max: int = 30,
    parallelogram_max: int = 30,
    strip_y_max: int = 6,
) -> tuple[str, dict, int]:
    """Best triangular construction for a given n, by greedy peel.

    Returns (region_label, params_dict, e). We try:
      - the smallest hex disk with >= n points, greedy-peel to n
      - parallelograms with sx * sy >= n
      - long strips with (2 sx + 1) * sy >= n
    and keep the densest result.
    """
    best_e = -1
    best_label = "?"
    best_params: dict = {}

    for r in range(1, radius_max + 1):
        n_hex, _ = hex_disk_n_e(r)
        if n_hex < n_target:
            continue
        c = build(TriangularParams(radius=r, shape="hex"))
        sub = greedy_peel(c, n_target)
        if sub.e > best_e:
            best_e = sub.e
            best_label = "hex"
            best_params = {"shape": "hex", "radius": r}
        break

    for sx in range(1, parallelogram_max + 1):
        for sy in range(1, parallelogram_max + 1):
            if sx * sy < n_target or sx * sy > n_target + 4 * max(sx, sy):
                continue
            c = build(TriangularParams(shape="parallelogram", sx=sx, sy=sy))
            sub = greedy_peel(c, n_target)
            if sub.e > best_e:
                best_e = sub.e
                best_label = "parallelogram"
                best_params = {"shape": "parallelogram", "sx": sx, "sy": sy}

    for sy in range(1, strip_y_max + 1):
        sx = max(1, (n_target // sy + 1) // 2)
        if (2 * sx + 1) * sy < n_target:
            continue
        c = build(TriangularParams(shape="strip", sx=sx, sy=sy))
        sub = greedy_peel(c, n_target)
        if sub.e > best_e:
            best_e = sub.e
            best_label = "strip"
            best_params = {"shape": "strip", "sx": sx, "sy": sy}

    return best_label, best_params, best_e


def sweep_frontier(*, n_values: list[int]) -> list[dict]:
    """Best-of triangular construction at every n in n_values. JSONL-ready."""
    rows: list[dict] = []
    for n in n_values:
        label, p, e = best_for_n(n)
        rows.append(
            {
                "family": "triangular",
                "n": n,
                "e": e,
                "density": e / n if n else 0.0,
                "shape": label,
                "shape_params": p,
            }
        )
    return rows


def hex_disk_closed_form_rows(*, r_max: int = 30) -> list[dict]:
    """Just the filled hex disks. Useful as a clean record of the
    classical lower bound u(3r^2 + 3r + 1) >= 9r^2 + 3r.
    """
    rows: list[dict] = []
    for r in range(1, r_max + 1):
        n, e = hex_disk_n_e(r)
        rows.append(
            {
                "family": "triangular",
                "n": n,
                "e": e,
                "density": e / n,
                "shape": "hex",
                "shape_params": {"radius": r},
            }
        )
    return rows


def enumerate_unit_vectors() -> list[tuple[int, int]]:
    """Re-derive the 6 unit directions and check them with sympy.

    Mirrors the cyclotomic / biquadratic enumerate_unit_vectors APIs so the
    family integrates with `eud verify`.
    """
    lat = basis()
    sd = squared_distance_symbolic()
    candidates: list[tuple[int, int]] = []
    for a, b in itertools.product(range(-1, 2), repeat=2):
        if (a, b) == (0, 0):
            continue
        x, y = lat.project((a, b))
        if abs(x * x + y * y - 1.0) < 1e-7:
            candidates.append((a, b))
    return [u for u in candidates if is_exact_unit(u, sd)]
