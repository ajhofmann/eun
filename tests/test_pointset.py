"""Smoke tests for LatticePoint and Candidate."""

from __future__ import annotations

from eud.core.pointset import Candidate, LatticePoint


def test_candidate_basic_props() -> None:
    pts = [
        LatticePoint(coeffs=(0, 0), xy=(0.0, 0.0)),
        LatticePoint(coeffs=(1, 0), xy=(1.0, 0.0)),
        LatticePoint(coeffs=(0, 1), xy=(0.0, 1.0)),
    ]
    c = Candidate(family="square", params={}, points=pts, edges=[(0, 1), (0, 2)])
    assert c.n == 3
    assert c.e == 2
    assert c.density == 2 / 3


def test_induced_subgraph_reindexes() -> None:
    pts = [
        LatticePoint(coeffs=(i, 0), xy=(float(i), 0.0)) for i in range(5)
    ]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
    c = Candidate(family="path5", params={}, points=pts, edges=edges)
    sub = c.induced_subgraph([1, 2, 3])
    assert sub.n == 3
    assert sorted(sub.edges) == [(0, 1), (1, 2)]
    assert sub.notes["induced"] is True
