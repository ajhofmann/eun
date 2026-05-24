"""Cyclotomic cut-and-project: Z[zeta_m] viewed via its Minkowski embedding.

For m with phi(m) = rank, the ring of integers of Q(zeta_m) is Z[zeta_m]
with Z-basis (1, zeta, zeta^2, ..., zeta^{rank-1}). The Galois group of
Q(zeta_m)/Q is (Z/m)*; complex conjugation pairs each embedding sigma_j
(zeta -> zeta^j) with sigma_{-j}. We choose

    visible:   sigma_1 (zeta -> e^{2 pi i / m})
    hidden_k:  sigma_{j_k} for one representative per non-identity
               conjugate pair {j, -j mod m}

and collect points whose hidden-space image lies in a `Window`.

Examples:
    m = 5  -> rank 4, 1 hidden complex pair  (Z[zeta_5])
    m = 7  -> rank 6, 2 hidden complex pairs (Z[zeta_7])
    m = 8  -> rank 4, 1 hidden complex pair  (Z[zeta_8] = Z[i, sqrt(2)])
    m = 12 -> rank 4, 1 hidden complex pair  (Z[zeta_12] = Z[i, sqrt(3)])
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from math import cos, pi, sin

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
class CyclotomicParams:
    """Parameters for a Z[zeta_m] cut-and-project construction.

    Attributes:
        m: order of the primitive root zeta = e^{2 pi i / m}.
        coeff_bound: half-width of the integer coefficient box.
        R: window radius / scale parameter.
        window_kind: one of "ball", "box", "ellipsoid", "zonotope", "all".
            "all" disables the window (full coefficient box; hidden image
            is dense in C^k, giving very large candidates).
        window_params: extra kwargs for non-ball windows (e.g. axes for
            ellipsoid, half_widths for box, generators for zonotope).
        translation_seed: seed for a random center in hidden space.
        translation_scale: max magnitude of the random center per coord.
    """

    m: int = 5
    coeff_bound: int = 6
    R: float = 2.5
    window_kind: str = "ball"
    window_params: dict = field(default_factory=dict)
    translation_seed: int | None = None
    translation_scale: float = 0.5
    unit_search_bound: int | None = None


def _phi(m: int) -> int:
    """Euler totient of m."""
    return int(sp.totient(m))


def _hidden_orbit_reps(m: int) -> list[int]:
    """Pick one representative per non-trivial conjugate pair in (Z/m)*.

    Galois orbits in Q(zeta_m)/Q are the residues coprime to m.
    Complex conjugation maps j -> -j mod m. We skip j=1 (visible) and
    j with j == -j mod m (real embedding, not present for m > 2).
    """
    out: list[int] = []
    seen: set[int] = {1, m - 1}
    for j in range(2, m):
        from math import gcd

        if gcd(j, m) != 1:
            continue
        if j in seen:
            continue
        out.append(j)
        seen.add(j)
        seen.add((-j) % m)
    return out


def basis(params: CyclotomicParams) -> LatticeBasis:
    """Visible + hidden bases for Z[zeta_m]."""
    rank = _phi(params.m)
    theta = 2 * pi / params.m
    visible = tuple(complex(cos(theta * k), sin(theta * k)) for k in range(rank))

    hidden_pairs: list[tuple[complex, ...]] = []
    for j in _hidden_orbit_reps(params.m):
        theta_j = 2 * pi * j / params.m
        hidden_pairs.append(
            tuple(complex(cos(theta_j * k), sin(theta_j * k)) for k in range(rank))
        )
    return LatticeBasis(
        visible=visible,
        hidden=tuple(hidden_pairs),
        name=f"cyclotomic_m{params.m}",
    )


def squared_distance_symbolic(params: CyclotomicParams):
    """Exact symbolic squared-norm of integer 4..k tuple (visible embedding)."""
    rank = _phi(params.m)
    zeta = sp.exp(sp.I * 2 * sp.pi / params.m)
    sym_basis = tuple(zeta**k for k in range(rank))
    return make_squared_distance(sym_basis)


def make_window(params: CyclotomicParams, lat: LatticeBasis) -> Window:
    """Build the hidden-space window for these params."""
    hidden_dim = len(lat.hidden) * 2
    kind = params.window_kind
    extra = params.window_params or {}

    center: tuple[float, ...] = (0.0,) * hidden_dim
    if params.translation_seed is not None:
        from eud.families.cut_project import random_translation

        center = random_translation(
            hidden_dim, seed=params.translation_seed, scale=params.translation_scale
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
    params: CyclotomicParams,
    *,
    search_bound: int = 4,
    float_tol: float = 1e-7,
) -> list[tuple[int, ...]]:
    """Integer rank-tuples whose visible squared-norm is exactly 1."""
    rank = _phi(params.m)
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


def enumerate_points(params: CyclotomicParams) -> list[LatticePoint]:
    """Cut-and-project lattice points: coefficient box ∩ hidden window."""
    lat = basis(params)
    window = make_window(params, lat)
    return cut_project_points(lat, coeff_bound=params.coeff_bound, window=window)


def _default_unit_search_bound(m: int) -> int:
    """In Q(zeta_m) the only norm-1 algebraic integers are roots of unity.

    For m < 105 the m-th cyclotomic polynomial Phi_m has coefficients in
    {-1, 0, 1}, so every root of unity has power-basis coefficients in
    {-1, 0, 1}. search_bound=1 then enumerates all of them. For m >= 105
    (the first m with |coefficient(Phi_m)| = 2) we fall back to 4 to be
    safe.
    """
    return 1 if m < 105 else 4


def build(params: CyclotomicParams) -> Candidate:
    points = enumerate_points(params)
    sb = (
        params.unit_search_bound
        if params.unit_search_bound is not None
        else _default_unit_search_bound(params.m)
    )
    units = enumerate_unit_vectors(params, search_bound=sb)
    edges = count_edges(points, units)
    return Candidate(
        family="cyclotomic",
        params={
            "m": params.m,
            "coeff_bound": params.coeff_bound,
            "R": params.R,
            "window_kind": params.window_kind,
            "window_params": dict(params.window_params),
            "translation_seed": params.translation_seed,
            "translation_scale": params.translation_scale,
            "unit_search_bound": sb,
        },
        points=points,
        edges=edges,
        unit_vectors=units,
    )


def sweep(
    *,
    m: int = 5,
    coeff_bounds: list[int] | None = None,
    Rs: list[float] | None = None,
    window_kinds: list[str] | None = None,
    translation_seeds: list[int | None] | None = None,
) -> list[Candidate]:
    """Cartesian-product sweep over CyclotomicParams configurations."""
    coeff_bounds = coeff_bounds or [4, 5, 6]
    Rs = Rs or [1.5, 2.0, 2.5, 3.0]
    window_kinds = window_kinds or ["ball"]
    translation_seeds = translation_seeds or [None]

    results: list[Candidate] = []
    for cb, R, wk, ts in itertools.product(coeff_bounds, Rs, window_kinds, translation_seeds):
        p = CyclotomicParams(
            m=m,
            coeff_bound=cb,
            R=R,
            window_kind=wk,
            translation_seed=ts,
        )
        results.append(build(p))
    return results
