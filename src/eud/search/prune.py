"""Greedy / core peeling shrinkers.

Given a Candidate (n, e), pick the densest k-vertex induced subgraph
without exact optimization. These are fast, deterministic, and produce
sensible per-k frontiers.
"""

from __future__ import annotations

from collections.abc import Iterable

from eud.core.edges import adjacency
from eud.core.pointset import Candidate


def greedy_peel(candidate: Candidate, target_k: int) -> Candidate:
    """Repeatedly drop the lowest-degree remaining vertex.

    Tie-broken deterministically by index. Returns the size-`target_k`
    induced subgraph.
    """
    if target_k <= 0:
        return candidate.induced_subgraph([])
    if target_k >= candidate.n:
        return candidate

    adj = adjacency(candidate.n, candidate.edges)
    alive = list(range(candidate.n))
    deg = {i: len(adj[i]) for i in alive}

    while len(alive) > target_k:
        worst = min(alive, key=lambda v: (deg[v], v))
        for u in adj[worst]:
            if u in deg:
                deg[u] -= 1
        alive.remove(worst)
        del deg[worst]

    return candidate.induced_subgraph(alive)


def core_peel(candidate: Candidate, target_k: int) -> Candidate:
    """Iterative k-core-style peeling.

    Repeatedly drops every vertex with current degree below the median.
    Stops when |alive| <= target_k, then completes with greedy_peel.
    """
    if target_k <= 0:
        return candidate.induced_subgraph([])
    if target_k >= candidate.n:
        return candidate

    adj = adjacency(candidate.n, candidate.edges)
    alive = set(range(candidate.n))
    deg = {i: len(adj[i]) for i in alive}

    while len(alive) > target_k:
        if not alive:
            break
        sorted_d = sorted(deg.values())
        median = sorted_d[len(sorted_d) // 2]
        to_drop = [v for v in alive if deg[v] < median]
        if not to_drop:
            break
        for v in to_drop:
            alive.discard(v)
            del deg[v]
            for u in adj[v]:
                if u in deg:
                    deg[u] -= 1

    if len(alive) > target_k:
        sub = candidate.induced_subgraph(sorted(alive))
        return greedy_peel(sub, target_k)
    return candidate.induced_subgraph(sorted(alive))


def per_k_frontier(
    candidate: Candidate,
    ks: Iterable[int],
    *,
    method: str = "greedy",
) -> list[dict]:
    """Apply a peeler at each k. Returns JSONL-ready rows."""
    fn = {"greedy": greedy_peel, "core": core_peel}[method]
    rows: list[dict] = []
    for k in sorted(set(ks)):
        sub = fn(candidate, k)
        rows.append(
            {
                "family": candidate.family,
                "params": candidate.params,
                "method": method,
                "n": sub.n,
                "e": sub.e,
                "density": sub.density,
                "induced_from_n": candidate.n,
            }
        )
    return rows
