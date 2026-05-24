"""Hash-indexed counter must agree with brute force on small random subsets."""

from __future__ import annotations

import random

import pytest

from eud.core.edges import count_edges, count_edges_brute
from eud.core.pointset import LatticePoint


def _square_lattice_points(n: int = 50, side: int = 12, seed: int = 0) -> list[LatticePoint]:
    """Random subset of Z[i] for testing - rank 2, unit vectors are (+/-1, 0), (0, +/-1)."""
    rng = random.Random(seed)
    coords = set()
    while len(coords) < n:
        coords.add((rng.randint(-side, side), rng.randint(-side, side)))
    return [LatticePoint(coeffs=c, xy=(float(c[0]), float(c[1]))) for c in coords]


SQUARE_UNITS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def test_hash_matches_brute_on_square_lattice() -> None:
    pts = _square_lattice_points(n=50, seed=42)
    hash_edges = count_edges(pts, SQUARE_UNITS)
    brute_edges = count_edges_brute(pts)
    assert sorted(hash_edges) == sorted(brute_edges)


@pytest.mark.parametrize("seed", list(range(10)))
def test_hash_matches_brute_random_seeds(seed: int) -> None:
    pts = _square_lattice_points(n=40, seed=seed)
    assert sorted(count_edges(pts, SQUARE_UNITS)) == sorted(count_edges_brute(pts))


def test_count_edges_no_self_loops() -> None:
    pts = _square_lattice_points(n=20, seed=1)
    edges = count_edges(pts, SQUARE_UNITS + [(0, 0)])
    for i, j in edges:
        assert i != j


def test_count_edges_pairs_are_ordered() -> None:
    pts = _square_lattice_points(n=20, seed=2)
    for i, j in count_edges(pts, SQUARE_UNITS):
        assert i < j


def test_count_edges_dim_mismatch_raises() -> None:
    pts = _square_lattice_points(n=5, seed=3)
    with pytest.raises(ValueError):
        count_edges(pts, [(1, 0, 0)])
