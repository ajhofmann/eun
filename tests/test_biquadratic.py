"""Biquadratic / multiquadratic family Q(i, sqrt(p_1), ..., sqrt(p_k))."""

from __future__ import annotations

import pytest

from eud.core.algebra import is_exact_unit
from eud.families.biquadratic import (
    BiquadraticParams,
    _basis_index,
    basis,
    build,
    enumerate_unit_vectors,
    squared_distance_symbolic,
)


@pytest.mark.parametrize("k", [1, 2, 3])
def test_basis_size_matches_2_to_kp1(k: int) -> None:
    elems = _basis_index(k)
    assert len(elems) == 2 ** (k + 1)


def test_basis_dim_q_i_sqrt3() -> None:
    p = BiquadraticParams(primes=(3,))
    lat = basis(p)
    assert lat.rank == 4
    # 2^k - 1 hidden complex pairs = 2^1 - 1 = 1
    assert len(lat.hidden) == 1


def test_basis_dim_q_i_sqrt3_sqrt5() -> None:
    p = BiquadraticParams(primes=(3, 5))
    lat = basis(p)
    assert lat.rank == 8
    assert len(lat.hidden) == 3  # 2^2 - 1


def test_unit_vectors_q_i_sqrt3_includes_basic() -> None:
    """In Z[i, sqrt(3)] the only sub-ring units are +/-1 and +/-i.

    Basis order (per `_basis_index(1)`): (1, sqrt(3), i, i*sqrt(3)).
    """
    p = BiquadraticParams(primes=(3,))
    units = set(enumerate_unit_vectors(p, search_bound=3))
    expected = {
        (1, 0, 0, 0),
        (-1, 0, 0, 0),
        (0, 0, 1, 0),
        (0, 0, -1, 0),
    }
    assert units == expected


def test_unit_vectors_exact() -> None:
    p = BiquadraticParams(primes=(3, 5), coeff_bound=1)
    units = enumerate_unit_vectors(p, search_bound=2)
    sd = squared_distance_symbolic(p)
    for u in units:
        assert is_exact_unit(u, sd), u


def test_build_q_i_sqrt3_smoke() -> None:
    p = BiquadraticParams(primes=(3,), coeff_bound=2, R=1.5)
    c = build(p)
    assert c.family == "biquadratic"
    assert c.n > 0
    assert all(0 <= i < c.n and 0 <= j < c.n and i < j for i, j in c.edges)


def test_build_with_window() -> None:
    p = BiquadraticParams(primes=(3,), coeff_bound=2, R=0.5, window_kind="ball")
    c_small = build(p)
    p2 = BiquadraticParams(primes=(3,), coeff_bound=2, R=2.0, window_kind="ball")
    c_big = build(p2)
    assert c_small.n <= c_big.n
