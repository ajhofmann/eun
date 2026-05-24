"""Cyclotomic family + cut-and-project sanity tests."""

from __future__ import annotations

import pytest

from eud.core.algebra import is_exact_unit
from eud.families.cut_project import (
    BallWindow,
    BoxWindow,
    EllipsoidWindow,
    ZonotopeWindow,
)
from eud.families.cyclotomic import (
    CyclotomicParams,
    _hidden_orbit_reps,
    _phi,
    basis,
    build,
    enumerate_unit_vectors,
    squared_distance_symbolic,
    sweep,
)


@pytest.mark.parametrize("m,phi_m", [(5, 4), (7, 6), (8, 4), (12, 4)])
def test_phi_values(m: int, phi_m: int) -> None:
    assert _phi(m) == phi_m


@pytest.mark.parametrize(
    "m,expected_hidden_count",
    [(5, 1), (7, 2), (8, 1), (12, 1)],
)
def test_hidden_orbit_count(m: int, expected_hidden_count: int) -> None:
    assert len(_hidden_orbit_reps(m)) == expected_hidden_count


def test_zeta5_basis_dimensions() -> None:
    p = CyclotomicParams(m=5)
    lat = basis(p)
    assert lat.rank == 4
    assert len(lat.hidden) == 1


def test_zeta5_unit_vectors_exact() -> None:
    """Every enumerated unit vector survives exact algebra."""
    p = CyclotomicParams(m=5, coeff_bound=4)
    units = enumerate_unit_vectors(p)
    sd = squared_distance_symbolic(p)
    assert len(units) > 0
    for u in units:
        assert is_exact_unit(u, sd), u


def test_zeta5_unit_vectors_include_basis_directions() -> None:
    p = CyclotomicParams(m=5)
    units = set(enumerate_unit_vectors(p))
    for k in range(4):
        e = tuple(1 if i == k else 0 for i in range(4))
        assert e in units, e


def test_zeta5_unit_vectors_negation_closed() -> None:
    p = CyclotomicParams(m=5)
    units = set(enumerate_unit_vectors(p))
    for u in units:
        assert tuple(-x for x in u) in units


def test_zeta5_build_smoke() -> None:
    p = CyclotomicParams(m=5, coeff_bound=4, R=2.0, window_kind="ball")
    c = build(p)
    assert c.family == "cyclotomic"
    assert c.n > 0
    assert c.e > 0
    assert all(0 <= i < c.n and 0 <= j < c.n and i < j for i, j in c.edges)


def test_zeta5_R_zero_keeps_only_origin() -> None:
    """A degenerate ball of radius 0 keeps only points whose hidden coord is exactly 0.
    For Z[zeta_5] those are scalar multiples of (1,1,1,1)? Actually the only
    integer combo with hidden coord = 0 is the zero vector. So |P| = 1."""
    p = CyclotomicParams(m=5, coeff_bound=2, R=0.0)
    c = build(p)
    assert c.n == 1


def test_zeta5_growing_R_grows_n() -> None:
    """Wider window strictly increases (or keeps equal) the kept point count."""
    ns = []
    for R in [0.5, 1.0, 1.5, 2.0, 2.5]:
        p = CyclotomicParams(m=5, coeff_bound=5, R=R)
        ns.append(build(p).n)
    assert ns == sorted(ns)
    assert ns[0] < ns[-1]


def test_box_window_basic() -> None:
    w = BoxWindow(half_widths=(1.0, 1.0))
    assert w.contains((0.5, 0.5))
    assert not w.contains((1.5, 0.0))


def test_ball_window_basic() -> None:
    w = BallWindow(radius=1.0)
    assert w.contains((0.5, 0.5))
    assert not w.contains((1.0, 1.0))


def test_ellipsoid_window_basic() -> None:
    w = EllipsoidWindow(axes=(2.0, 1.0))
    assert w.contains((1.5, 0.5))
    assert not w.contains((1.5, 0.9))  # (1.5/2)^2 + (0.9/1)^2 = 0.5625 + 0.81 > 1


def test_zonotope_window_basic() -> None:
    w = ZonotopeWindow(generators=((1.0, 0.0), (0.0, 1.0)))
    assert w.contains((0.5, 0.5))
    assert not w.contains((1.5, 0.0))


def test_cyclotomic_sweep_returns_multiple_candidates() -> None:
    candidates = sweep(m=5, coeff_bounds=[3], Rs=[1.5, 2.0], window_kinds=["ball"])
    assert len(candidates) == 2
    assert all(c.family == "cyclotomic" for c in candidates)


def test_random_translation_changes_candidate() -> None:
    p_no = CyclotomicParams(m=5, coeff_bound=4, R=2.0, translation_seed=None)
    p_yes = CyclotomicParams(m=5, coeff_bound=4, R=2.0, translation_seed=42)
    c1 = build(p_no)
    c2 = build(p_yes)
    assert c1.n != c2.n or sorted(c1.edges) != sorted(c2.edges)
