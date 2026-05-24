"""Pruning engine: greedy / core / local_swap / cp-sat agreement on small inputs."""

from __future__ import annotations

import random

import pytest

from eud.core.pointset import Candidate, LatticePoint
from eud.search.ilp import CPSATConfig, cp_sat_densest_k
from eud.search.local_search import SAConfig, local_swap
from eud.search.prune import core_peel, greedy_peel, per_k_frontier


def _erdos_renyi(n: int, p: float, seed: int = 0) -> Candidate:
    rng = random.Random(seed)
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p]
    pts = [LatticePoint(coeffs=(i,), xy=(float(i), 0.0)) for i in range(n)]
    return Candidate(family="er", params={"p": p}, points=pts, edges=edges)


def _clique_with_isolates(clique_n: int, isolated_n: int) -> Candidate:
    n = clique_n + isolated_n
    edges = [(i, j) for i in range(clique_n) for j in range(i + 1, clique_n)]
    pts = [LatticePoint(coeffs=(i,), xy=(float(i), 0.0)) for i in range(n)]
    return Candidate(family="clique", params={}, points=pts, edges=edges)


def test_greedy_peel_keeps_clique_intact() -> None:
    c = _clique_with_isolates(5, 5)
    sub = greedy_peel(c, 5)
    assert sub.n == 5
    assert sub.e == 10  # K_5 edges


def test_greedy_peel_target_zero_or_full() -> None:
    c = _clique_with_isolates(3, 2)
    assert greedy_peel(c, 0).n == 0
    full = greedy_peel(c, c.n)
    assert full.n == c.n
    assert full.e == c.e


def test_core_peel_keeps_clique_intact() -> None:
    c = _clique_with_isolates(5, 5)
    sub = core_peel(c, 5)
    assert sub.n == 5
    assert sub.e == 10


def test_per_k_frontier_returns_one_row_per_k() -> None:
    c = _erdos_renyi(20, 0.3, seed=1)
    rows = per_k_frontier(c, [5, 10, 15], method="greedy")
    assert [r["n"] for r in rows] == [5, 10, 15]
    assert all(r["family"] == "er" for r in rows)


def test_local_swap_finds_dense_subgraph() -> None:
    c = _clique_with_isolates(6, 8)
    sub = local_swap(c, 6, config=SAConfig(max_iters=2000, seed=7))
    assert sub.n == 6
    assert sub.e >= 13  # near-clique


def test_local_swap_at_least_as_good_as_greedy() -> None:
    c = _erdos_renyi(30, 0.4, seed=3)
    sg = greedy_peel(c, 10).e
    sl = local_swap(c, 10, config=SAConfig(max_iters=3000, seed=3, restarts=2)).e
    assert sl >= sg


def test_cp_sat_finds_optimal_clique() -> None:
    c = _clique_with_isolates(5, 5)
    sub, info = cp_sat_densest_k(c, 5, config=CPSATConfig(time_limit_s=10, workers=1))
    assert sub.n == 5
    assert sub.e == 10  # K_5
    assert info["status"] in ("OPTIMAL", "FEASIBLE")


@pytest.mark.parametrize("k", [3, 5, 8])
def test_cp_sat_at_least_as_good_as_greedy(k: int) -> None:
    c = _erdos_renyi(20, 0.4, seed=5)
    sg = greedy_peel(c, k).e
    sub, info = cp_sat_densest_k(c, k, config=CPSATConfig(time_limit_s=10, workers=1))
    assert sub.n == k
    assert sub.e >= sg
    assert info["status"] in ("OPTIMAL", "FEASIBLE")
