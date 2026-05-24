"""Erdős square-grid baseline: number-theoretic checks + edge-count agreement."""

from __future__ import annotations

from eud.families.erdos_grid import (
    ErdosGridParams,
    all_unit_vectors_for_K,
    best_grid_for_n,
    build,
    edges_analytic,
    positive_unit_vectors_for_K,
    primes_one_mod_four,
    squarefree_products_of_pmod1,
    sum_of_two_squares,
)


def test_primes_one_mod_four() -> None:
    assert primes_one_mod_four(50) == [5, 13, 17, 29, 37, 41]


def test_sum_of_two_squares_basic() -> None:
    s5 = set(sum_of_two_squares(5))
    assert s5 == {(1, 2), (1, -2), (-1, 2), (-1, -2), (2, 1), (2, -1), (-2, 1), (-2, -1)}
    s25 = set(sum_of_two_squares(25))
    assert (0, 5) in s25 and (5, 0) in s25
    assert (3, 4) in s25 and (4, 3) in s25


def test_positive_unit_vectors_count() -> None:
    """Each positive direction corresponds to exactly one undirected edge direction."""
    for K in [1, 5, 25, 65, 325]:
        full = all_unit_vectors_for_K(K)
        pos = positive_unit_vectors_for_K(K)
        assert len(full) == 2 * len(pos), f"K={K}"


def test_squarefree_products() -> None:
    primes = [5, 13, 17]
    out = squarefree_products_of_pmod1(primes, 2000)
    assert 5 in out and 13 in out and 17 in out
    assert 65 in out and 85 in out and 221 in out and 1105 in out
    assert 25 not in out  # 5^2 not squarefree
    out_small = squarefree_products_of_pmod1(primes, 100)
    assert 1105 not in out_small


def test_edges_analytic_matches_built_candidate() -> None:
    """Closed-form analytic count must match `count_edges` on the explicit grid."""
    for K in [1, 5, 25, 65]:
        for m in [3, 5, 8, 10]:
            params = ErdosGridParams(K=K, m=m)
            c = build(params)
            assert c.n == m * m
            assert c.e == edges_analytic(params), (K, m)


def test_best_grid_picks_richer_K_for_large_m() -> None:
    """At m=10, K=5 (8 unit vectors) should beat K=1 (4 unit vectors)."""
    params, e = best_grid_for_n(100)
    assert params.K != 1
    assert e > edges_analytic(ErdosGridParams(K=1, m=10))


def test_best_grid_density_grows_with_m() -> None:
    """e/n grows (slowly) with m on the optimized erdos_grid."""
    p1, e1 = best_grid_for_n(25)
    p2, e2 = best_grid_for_n(400)
    p3, e3 = best_grid_for_n(2500)
    assert e1 / 25 < e2 / 400 < e3 / 2500


def test_known_bounds_table_n_le_14_exact() -> None:
    from eud.benchmarks.known_bounds import KNOWN_BOUNDS, is_exact

    for n, _, exact in KNOWN_BOUNDS[:21]:
        assert exact, f"n={n} should be exact"
    for n in range(22, 31):
        assert not is_exact(n)


def test_frontier_picks_max_per_n() -> None:
    from eud.benchmarks.score import Frontier

    rows = [
        {"family": "a", "n": 4, "e": 5},
        {"family": "b", "n": 4, "e": 7},
        {"family": "c", "n": 9, "e": 18},
    ]
    fr = Frontier.from_jsonl_rows(rows)
    assert fr.best_edges_at(4) == 7
    assert fr.best_edges_at(9) == 18
    assert fr.best_at_or_below(9) == 18
    assert fr.best_at_or_below(4) == 7
