"""Hash-indexed unit-edge enumeration on lattice points.

Once a family precomputes the integer-coefficient unit vectors `U`,
counting unit edges across `n` points is `O(n * |U|)` via a hash on
coefficient tuples. The brute-force version is kept for testing.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from math import isclose

from eud.core.pointset import LatticePoint


def count_edges(
    points: Sequence[LatticePoint],
    unit_vectors: Iterable[tuple[int, ...]],
) -> list[tuple[int, int]]:
    """Return all unit-distance edges as ordered index pairs (i < j).

    A pair (p, q) is an edge iff `q.coeffs - p.coeffs` is in `unit_vectors`.
    We enumerate edges by adding each unit vector to each point and looking
    up the result in a hash map.
    """
    index: dict[tuple[int, ...], int] = {p.coeffs: i for i, p in enumerate(points)}
    edges: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    for i, p in enumerate(points):
        for u in unit_vectors:
            if len(u) != len(p.coeffs):
                raise ValueError(
                    f"unit vector dim {len(u)} != point dim {len(p.coeffs)}"
                )
            q = tuple(a + b for a, b in zip(p.coeffs, u, strict=True))
            j = index.get(q)
            if j is None or j == i:
                continue
            a, b = (i, j) if i < j else (j, i)
            if (a, b) in seen:
                continue
            seen.add((a, b))
            edges.append((a, b))

    edges.sort()
    return edges


def count_edges_brute(
    points: Sequence[LatticePoint],
    *,
    target_squared: float = 1.0,
    rel_tol: float = 1e-9,
    abs_tol: float = 1e-9,
) -> list[tuple[int, int]]:
    """Brute O(n^2) edge enumeration on the float `xy` projection.

    Used only as a sanity check against the hash-indexed counter on small
    inputs. NOT for record claims - floats lie on close-but-not-equal pairs.
    """
    edges: list[tuple[int, int]] = []
    n = len(points)
    for i in range(n):
        xi, yi = points[i].xy
        for j in range(i + 1, n):
            xj, yj = points[j].xy
            dx = xi - xj
            dy = yi - yj
            d2 = dx * dx + dy * dy
            if isclose(d2, target_squared, rel_tol=rel_tol, abs_tol=abs_tol):
                edges.append((i, j))
    return edges


def adjacency(n: int, edges: Iterable[tuple[int, int]]) -> list[set[int]]:
    """Return a per-vertex neighbor set."""
    adj: list[set[int]] = [set() for _ in range(n)]
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    return adj
