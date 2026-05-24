"""Engel et al. 18-unit Moser lattice.

This is the rank-4 lattice used by Engel--Hammond-Lee--Su--Varga--
Zsámboki (2025), "Diverse beam search to find densest-known planar unit
distance graphs". It differs from our earlier cyclotomic/Moser lattice:

    M_L = Z<1, omega_1, omega_3, omega_1 * omega_3>

where
    omega_1 = exp(i*pi/3)
    omega_3 = exp(i*arccos(5/6)) = 5/6 + i*sqrt(11)/6

Engel et al. prove this lattice has exactly 18 unit vectors. We enumerate
them using their exact criterion:

    p(a,b,c,d) = 1 and ad = bc

with p the rational quadratic form from Theorem 2.5. This avoids trusting
floating-point distances for the unit-vector list.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from math import sqrt

import sympy as sp

from eud.core.algebra import ExactSquaredDistance
from eud.core.edges import count_edges
from eud.core.lattice import LatticeBasis
from eud.core.pointset import Candidate, LatticePoint


@dataclass(frozen=True)
class EngelMoserParams:
    """Parameters for finite windows in the Engel 18-unit Moser lattice."""

    coeff_bound: int = 3
    window_kind: str = "visible_disk"  # visible_disk | coeff_box
    visible_radius: float = 4.0


def basis() -> LatticeBasis:
    """Visible basis (1, omega_1, omega_3, omega_1 * omega_3)."""
    omega_1 = complex(0.5, sqrt(3) / 2)
    omega_3 = complex(5 / 6, sqrt(11) / 6)
    return LatticeBasis(
        visible=(1 + 0j, omega_1, omega_3, omega_1 * omega_3),
        hidden=(),
        name="engel_moser",
    )


def squared_distance_symbolic() -> ExactSquaredDistance:
    """Exact squared distance for the visible Engel-Moser embedding."""

    def squared_distance(diff: tuple[int, ...]) -> sp.Expr:
        if len(diff) != 4:
            raise ValueError(f"diff dim {len(diff)} != rank 4")
        a, b, c, d = diff
        rational_part = sp.Rational(twelve_p(a, b, c, d), 12)
        irrational_part = sp.sqrt(33) * sp.Rational(b * c - a * d, 6)
        return rational_part + irrational_part

    return squared_distance


def twelve_p(a: int, b: int, c: int, d: int) -> int:
    """Return 12 * p(a,b,c,d) from Engel et al. Theorem 2.5.

    p = a^2 + ab + 5/3 ac + 5/6 ad + b^2 + 5/6 bc + 5/3 bd
        + c^2 + cd + d^2
    """
    return (
        12 * a * a
        + 12 * a * b
        + 20 * a * c
        + 10 * a * d
        + 12 * b * b
        + 10 * b * c
        + 20 * b * d
        + 12 * c * c
        + 12 * c * d
        + 12 * d * d
    )


def is_exact_unit_vector(u: tuple[int, int, int, int]) -> bool:
    """Engel et al.'s exact unit-vector criterion."""
    a, b, c, d = u
    return twelve_p(a, b, c, d) == 12 and a * d == b * c


def enumerate_unit_vectors(search_bound: int = 4) -> list[tuple[int, int, int, int]]:
    """Enumerate the 18 exact unit vectors in the Engel Moser lattice."""
    units: list[tuple[int, int, int, int]] = []
    for u in itertools.product(range(-search_bound, search_bound + 1), repeat=4):
        if u == (0, 0, 0, 0):
            continue
        if is_exact_unit_vector(u):
            units.append(u)
    units.sort()
    return units


def enumerate_points(params: EngelMoserParams) -> list[LatticePoint]:
    """Finite point window in the Engel Moser lattice."""
    lat = basis()
    pts: list[LatticePoint] = []
    r2 = params.visible_radius * params.visible_radius
    for coeffs in itertools.product(
        range(-params.coeff_bound, params.coeff_bound + 1), repeat=4
    ):
        xy = lat.project(coeffs)
        if params.window_kind == "visible_disk" and xy[0] * xy[0] + xy[1] * xy[1] > r2:
            continue
        if params.window_kind not in {"visible_disk", "coeff_box"}:
            raise ValueError(f"unknown window_kind: {params.window_kind}")
        pts.append(LatticePoint(coeffs=coeffs, xy=xy))
    return pts


def build(params: EngelMoserParams) -> Candidate:
    """Build a finite Engel Moser candidate."""
    points = enumerate_points(params)
    units = enumerate_unit_vectors()
    edges = count_edges(points, units)
    return Candidate(
        family="engel_moser",
        params={
            "coeff_bound": params.coeff_bound,
            "window_kind": params.window_kind,
            "visible_radius": params.visible_radius,
        },
        points=points,
        edges=edges,
        unit_vectors=units,
    )
