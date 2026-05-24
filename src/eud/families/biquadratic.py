"""Multiquadratic fields Q(i, sqrt(p_1), ..., sqrt(p_k)).

Z-basis: products i^a * prod_j sqrt(p_j)^{b_j} with a, b_j in {0, 1}.
Total rank = 2^{k+1} where k = len(primes).

Embeddings: each pattern of signs (s_0, s_1, ..., s_k) in {+/-1}^{k+1}.
- Visible:  all +1 (i -> i, sqrt(p_j) -> +sqrt(p_j)).
- Each pair {(s_0, s_1, ...), (-s_0, s_1, ...)} are complex conjugates;
  we pick one representative per pair (s_0 = +1) and skip the visible.
- Hidden complex pairs: 2^k - 1.

Examples:
    primes=(3,)        -> Q(i, sqrt(3)) = Q(zeta_12), rank 4, 1 hidden pair.
    primes=(3, 5)      -> Q(i, sqrt(3), sqrt(5)),     rank 8, 3 hidden pairs.
    primes=(3, 5, 11)  -> rank 16, 7 hidden pairs.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from math import sqrt

import sympy as sp

from eud.core.algebra import is_exact_unit, make_squared_distance
from eud.core.edges import count_edges
from eud.core.lattice import LatticeBasis
from eud.core.pointset import Candidate, LatticePoint
from eud.families.cut_project import (
    BallWindow,
    BoxWindow,
    EllipsoidWindow,
    Window,
    ZonotopeWindow,
    cut_project_points,
)


@dataclass(frozen=True)
class BiquadraticParams:
    """Q(i, sqrt(p_1), ..., sqrt(p_k)) cut-and-project."""

    primes: tuple[int, ...] = (3, 5)
    coeff_bound: int = 2
    R: float = 1.5
    window_kind: str = "ball"
    window_params: dict = field(default_factory=dict)
    translation_seed: int | None = None
    translation_scale: float = 0.5


def _basis_index(k: int) -> list[tuple[int, tuple[int, ...]]]:
    """Enumerate (a, (b_1, ..., b_k)) in deterministic order. Length 2^{k+1}."""
    out: list[tuple[int, tuple[int, ...]]] = []
    for a in (0, 1):
        for b in itertools.product((0, 1), repeat=k):
            out.append((a, b))
    return out


def basis(params: BiquadraticParams) -> LatticeBasis:
    """Visible + hidden Minkowski-embedding bases."""
    k = len(params.primes)
    sqrts = [sqrt(p) for p in params.primes]
    elems = _basis_index(k)

    def value(a: int, b: tuple[int, ...], s: tuple[int, ...]) -> complex:
        sign = 1
        for j, bj in enumerate(b):
            if bj == 1:
                sign *= s[j]
        v: complex = (1j if a == 1 else 1.0) * sign
        for j, bj in enumerate(b):
            if bj == 1:
                v *= sqrts[j]
        return v

    visible_signs: tuple[int, ...] = (1,) * k
    visible = tuple(value(a, b, visible_signs) for (a, b) in elems)

    hidden: list[tuple[complex, ...]] = []
    for s in itertools.product((-1, 1), repeat=k):
        if all(si == 1 for si in s):
            continue
        hidden.append(tuple(value(a, b, s) for (a, b) in elems))

    name = "Q(i," + ",".join(f"sqrt({p})" for p in params.primes) + ")"
    return LatticeBasis(visible=visible, hidden=tuple(hidden), name=name)


def squared_distance_symbolic(params: BiquadraticParams):
    """Exact symbolic |sum c_alpha b_alpha|^2 in Q[sqrt(p_1), ..., sqrt(p_k)]."""
    k = len(params.primes)
    sqrts_sym = [sp.sqrt(p) for p in params.primes]
    elems = _basis_index(k)
    sym_basis: list[sp.Expr] = []
    for a, b in elems:
        v: sp.Expr = sp.I**a if a == 1 else sp.S(1)
        for j, bj in enumerate(b):
            if bj == 1:
                v = v * sqrts_sym[j]
        sym_basis.append(v)
    return make_squared_distance(tuple(sym_basis))


def make_window(params: BiquadraticParams, lat: LatticeBasis) -> Window:
    """Build the hidden-space window."""
    hidden_dim = len(lat.hidden) * 2
    kind = params.window_kind
    extra = params.window_params or {}

    center: tuple[float, ...] = (0.0,) * hidden_dim
    if params.translation_seed is not None:
        from eud.families.cut_project import random_translation

        center = random_translation(
            hidden_dim,
            seed=params.translation_seed,
            scale=params.translation_scale,
        )

    if kind == "ball":
        return BallWindow(radius=params.R, center=center)
    if kind == "box":
        hw = extra.get("half_widths") or (params.R,) * hidden_dim
        return BoxWindow(half_widths=tuple(hw), center=center)
    if kind == "ellipsoid":
        axes = extra.get("axes") or (params.R,) * hidden_dim
        return EllipsoidWindow(axes=tuple(axes), center=center)
    if kind == "zonotope":
        gens = extra.get("generators") or [
            tuple(params.R if i == j else 0.0 for j in range(hidden_dim))
            for i in range(hidden_dim)
        ]
        return ZonotopeWindow(generators=tuple(map(tuple, gens)), center=center)
    if kind == "all":

        @dataclass
        class _All:
            def contains(self, coords) -> bool:
                return True

        return _All()
    raise ValueError(f"unknown window_kind: {kind}")


def enumerate_unit_vectors(
    params: BiquadraticParams,
    *,
    search_bound: int = 2,
    float_tol: float = 1e-7,
) -> list[tuple[int, ...]]:
    """Integer rank-tuples whose visible squared norm is exactly 1.

    Uses float pre-filter + exact sympy verification on survivors.
    """
    k = len(params.primes)
    rank = 2 ** (k + 1)
    lat = basis(params)
    candidates: list[tuple[int, ...]] = []
    for c in itertools.product(range(-search_bound, search_bound + 1), repeat=rank):
        if all(x == 0 for x in c):
            continue
        x, y = lat.project(c)
        d2 = x * x + y * y
        if abs(d2 - 1.0) < float_tol:
            candidates.append(c)

    sd = squared_distance_symbolic(params)
    units: list[tuple[int, ...]] = []
    for u in candidates:
        if is_exact_unit(u, sd):
            units.append(u)
    units.sort()
    return units


def enumerate_points(params: BiquadraticParams) -> list[LatticePoint]:
    lat = basis(params)
    window = make_window(params, lat)
    return cut_project_points(lat, coeff_bound=params.coeff_bound, window=window)


def build(params: BiquadraticParams) -> Candidate:
    points = enumerate_points(params)
    units = enumerate_unit_vectors(params)
    edges = count_edges(points, units)
    return Candidate(
        family="biquadratic",
        params={
            "primes": list(params.primes),
            "coeff_bound": params.coeff_bound,
            "R": params.R,
            "window_kind": params.window_kind,
            "window_params": dict(params.window_params),
            "translation_seed": params.translation_seed,
            "translation_scale": params.translation_scale,
        },
        points=points,
        edges=edges,
        unit_vectors=units,
    )
