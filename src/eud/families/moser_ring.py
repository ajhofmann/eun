"""Bounded common-denominator windows in the Moser ring.

Engel et al. define the Moser ring as Z[omega_1, omega_3], where every element
can be uniquely represented after simplification as

    (a + b omega_1 + c omega_3 + d omega_1 omega_3) / 3^k.

For finite experiments we fix a common denominator exponent `denom_power` and
enumerate bounded numerator coefficient tuples.  At denom_power=0 this reduces
to the 18-unit Engel-Moser lattice; larger denominator powers expose more exact
unit directions in the bounded numerator model.
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
from eud.families.engel_moser import twelve_p


@dataclass(frozen=True)
class MoserRingParams:
    """Parameters for finite common-denominator Moser ring windows."""

    denom_power: int = 1
    coeff_bound: int = 6
    visible_radius: float = 3.0
    window_kind: str = "visible_disk"  # visible_disk | coeff_box
    unit_search_bound: int | None = None


def denominator(denom_power: int) -> int:
    if denom_power < 0:
        raise ValueError("denom_power must be nonnegative")
    return 3**denom_power


def basis(params: MoserRingParams) -> LatticeBasis:
    """Visible basis scaled by the common denominator."""

    denom = denominator(params.denom_power)
    omega_1 = complex(0.5, sqrt(3) / 2)
    omega_3 = complex(5 / 6, sqrt(11) / 6)
    scale = 1 / denom
    return LatticeBasis(
        visible=(
            scale * (1 + 0j),
            scale * omega_1,
            scale * omega_3,
            scale * omega_1 * omega_3,
        ),
        hidden=(),
        name=f"moser_ring_3^-{params.denom_power}",
    )


def squared_distance_symbolic(params: MoserRingParams) -> ExactSquaredDistance:
    """Exact squared distance for numerator differences at denominator 3^k."""

    denom_sq = denominator(params.denom_power) ** 2

    def squared_distance(diff: tuple[int, ...]) -> sp.Expr:
        if len(diff) != 4:
            raise ValueError(f"diff dim {len(diff)} != rank 4")
        a, b, c, d = diff
        rational_part = sp.Rational(twelve_p(a, b, c, d), 12 * denom_sq)
        irrational_part = sp.sqrt(33) * sp.Rational(b * c - a * d, 6 * denom_sq)
        return rational_part + irrational_part

    return squared_distance


def is_exact_unit_vector(u: tuple[int, int, int, int], denom_power: int) -> bool:
    """Return true iff numerator difference `u / 3^k` has Euclidean length 1."""

    a, b, c, d = u
    return a * d == b * c and twelve_p(a, b, c, d) == 12 * (9**denom_power)


def enumerate_unit_vectors(params: MoserRingParams) -> list[tuple[int, int, int, int]]:
    """Enumerate exact unit numerator differences for the common denominator."""

    bound = params.unit_search_bound
    if bound is None:
        bound = 4 * denominator(params.denom_power)
    units: list[tuple[int, int, int, int]] = []
    for u in itertools.product(range(-bound, bound + 1), repeat=4):
        if u == (0, 0, 0, 0):
            continue
        if is_exact_unit_vector(u, params.denom_power):
            units.append(u)
    units.sort()
    return units


def enumerate_points(params: MoserRingParams) -> list[LatticePoint]:
    """Finite point window in the common-denominator Moser ring model."""

    lat = basis(params)
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


def build(params: MoserRingParams) -> Candidate:
    """Build a bounded Moser ring candidate."""

    points = enumerate_points(params)
    units = enumerate_unit_vectors(params)
    edges = count_edges(points, units)
    return Candidate(
        family="moser_ring",
        params={
            "denom_power": params.denom_power,
            "coeff_bound": params.coeff_bound,
            "window_kind": params.window_kind,
            "visible_radius": params.visible_radius,
            "unit_search_bound": params.unit_search_bound,
        },
        points=points,
        edges=edges,
        unit_vectors=units,
    )


def candidate_from_coeffs(
    coeffs: list[tuple[int, int, int, int]] | tuple[tuple[int, int, int, int], ...],
    params: MoserRingParams,
    *,
    unit_vectors: list[tuple[int, int, int, int]] | None = None,
    notes: dict | None = None,
) -> Candidate:
    """Build a Moser-ring candidate from numerator coefficients."""

    lat = basis(params)
    units = unit_vectors or enumerate_unit_vectors(params)
    points = [LatticePoint(coeffs=c, xy=lat.project(c)) for c in coeffs]
    return Candidate(
        family="moser_ring",
        params={
            "denom_power": params.denom_power,
            "coeff_bound": params.coeff_bound,
            "window_kind": params.window_kind,
            "visible_radius": params.visible_radius,
            "unit_search_bound": params.unit_search_bound,
        },
        points=points,
        edges=count_edges(points, units),
        unit_vectors=units,
        notes=notes or {},
    )
