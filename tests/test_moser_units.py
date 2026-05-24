"""Moser rank-4 family: exact unit-vector enumeration and stable edge counts."""

from __future__ import annotations

from pathlib import Path

import pytest

from eud.core.algebra import is_exact_unit
from eud.core.edges import count_edges, count_edges_brute
from eud.families.moser import (
    MoserParams,
    build,
    enumerate_points,
    enumerate_unit_vectors,
    squared_distance_symbolic,
)


def test_unit_vectors_zeta6_exact() -> None:
    """All enumerated unit vectors must be exactly unit-norm."""
    p = MoserParams(zeta_order=6, coeff_bound=2)
    units = enumerate_unit_vectors(p)
    sd = squared_distance_symbolic(p)
    assert len(units) > 0
    for u in units:
        assert is_exact_unit(u, sd), f"{u} not unit"


def test_unit_vectors_zeta6_count_stable() -> None:
    """The count is reproducible run-to-run."""
    p = MoserParams(zeta_order=6, coeff_bound=2)
    a = enumerate_unit_vectors(p)
    b = enumerate_unit_vectors(p)
    assert sorted(a) == sorted(b)


def test_unit_vectors_have_expected_symmetries() -> None:
    """Unit vectors come in negation pairs (closed under -id)."""
    p = MoserParams(zeta_order=6)
    units = set(enumerate_unit_vectors(p))
    for u in units:
        assert tuple(-x for x in u) in units


def test_unit_vectors_includes_basis_directions() -> None:
    """(1,0,0,0), (0,1,0,0), (0,0,1,0), (0,0,0,1) all have unit norm."""
    p = MoserParams(zeta_order=6)
    units = set(enumerate_unit_vectors(p))
    for d in [(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]:
        assert d in units, f"missing basis direction {d}"


def test_build_moser_smoke() -> None:
    p = MoserParams(zeta_order=6, coeff_bound=2)
    c = build(p)
    assert c.family == "moser"
    assert c.n == 5**4
    assert c.e > 0
    assert all(0 <= i < c.n and 0 <= j < c.n and i < j for i, j in c.edges)


def test_build_moser_reproducible() -> None:
    p = MoserParams(zeta_order=6, coeff_bound=2)
    c1 = build(p)
    c2 = build(p)
    assert c1.n == c2.n
    assert sorted(c1.edges) == sorted(c2.edges)


def test_hash_count_matches_brute_on_small_subset() -> None:
    p = MoserParams(zeta_order=6, coeff_bound=1)
    pts = enumerate_points(p)
    units = enumerate_unit_vectors(p)
    hash_edges = count_edges(pts, units)
    brute_edges = count_edges_brute(pts, target_squared=1.0, abs_tol=1e-7)
    assert sorted(hash_edges) == sorted(brute_edges)


@pytest.mark.parametrize("m", [3, 6, 12])
def test_alternative_zetas_produce_unit_vectors(m: int) -> None:
    p = MoserParams(zeta_order=m, coeff_bound=2)
    units = enumerate_unit_vectors(p)
    assert len(units) > 0


@pytest.mark.parametrize("m", [1, 2, 4])
def test_degenerate_zeta_orders_rejected(m: int) -> None:
    with pytest.raises(ValueError, match="Z-linearly dependent"):
        MoserParams(zeta_order=m)


def test_draw_candidate_writes_png(tmp_path: Path) -> None:
    from eud.viz.draw import draw_candidate

    c = build(MoserParams(zeta_order=6, coeff_bound=2))
    out = draw_candidate(c, tmp_path / "moser.png")
    assert out.exists()
    assert out.stat().st_size > 0
