"""Local search for densest k-induced subgraph.

Simulated-annealing swap: hold a size-k subset S; at each step propose
swapping a vertex v in S for a vertex u outside S, accept based on the
edge-count delta with a temperature schedule.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from eud.core.edges import adjacency
from eud.core.pointset import Candidate


@dataclass
class SAConfig:
    """Hyperparameters for the swap-based simulated-annealing pruner."""

    max_iters: int = 5000
    seed: int = 0
    start_temp: float = 2.0
    end_temp: float = 0.01
    restarts: int = 1
    warm_start_with_greedy: bool = True


def _initial_subset(adj: list[set[int]], k: int, rng: random.Random) -> set[int]:
    """Random initial subset weighted by degree: highest-degree top 2k pool."""
    n = len(adj)
    if k >= n:
        return set(range(n))
    deg_order = sorted(range(n), key=lambda v: (-len(adj[v]), v))
    base = set(deg_order[: k * 2])
    if len(base) < k:
        base.update(range(n))
    chosen = list(base)
    rng.shuffle(chosen)
    return set(chosen[:k])


def _greedy_subset(adj: list[set[int]], k: int) -> set[int]:
    """Greedy peel result as a set, deterministic. Mirrors prune.greedy_peel.

    Repeatedly drop the lowest-degree remaining vertex until k remain.
    """
    n = len(adj)
    if k >= n:
        return set(range(n))
    alive = set(range(n))
    deg = {i: len(adj[i]) for i in alive}
    while len(alive) > k:
        worst = min(alive, key=lambda v: (deg[v], v))
        for u in adj[worst]:
            if u in deg:
                deg[u] -= 1
        alive.discard(worst)
        del deg[worst]
    return alive


def _internal_edges(S: set[int], adj: list[set[int]]) -> int:
    """Number of edges induced by S (each counted once)."""
    e = 0
    for v in S:
        for u in adj[v]:
            if u in S and u > v:
                e += 1
    return e


def _delta_swap(
    S: set[int], adj: list[set[int]], v_out: int, v_in: int
) -> int:
    """Edge change from removing v_out and adding v_in."""
    lost = sum(1 for u in adj[v_out] if u in S and u != v_out)
    gained = sum(1 for u in adj[v_in] if u in S and u != v_out)
    if v_in in adj[v_out] and v_in in S:
        pass
    return gained - lost


def local_swap(
    candidate: Candidate,
    k: int,
    *,
    config: SAConfig | None = None,
) -> Candidate:
    """Find a dense k-vertex induced subgraph via simulated-annealing swaps."""
    config = config or SAConfig()
    n = candidate.n
    if k <= 0:
        return candidate.induced_subgraph([])
    if k >= n:
        return candidate

    adj = adjacency(n, candidate.edges)
    rng = random.Random(config.seed)

    best_S: set[int] = set()
    best_e = -1

    if config.warm_start_with_greedy:
        greedy_S = _greedy_subset(adj, k)
        greedy_e = _internal_edges(greedy_S, adj)
        if greedy_e > best_e:
            best_S = set(greedy_S)
            best_e = greedy_e

    for restart in range(max(1, config.restarts)):
        if config.warm_start_with_greedy and restart == 0:
            S = set(greedy_S)
            cur_e = greedy_e
        else:
            S = _initial_subset(adj, k, rng)
            cur_e = _internal_edges(S, adj)

        for it in range(config.max_iters):
            t = max(
                config.end_temp,
                config.start_temp
                * ((config.end_temp / config.start_temp) ** (it / max(1, config.max_iters))),
            )
            v_out = rng.choice(list(S))
            outside = [u for u in range(n) if u not in S]
            if not outside:
                break
            v_in = rng.choice(outside)
            d = _delta_swap(S, adj, v_out, v_in)
            if d > 0 or rng.random() < math.exp(d / t):
                S.discard(v_out)
                S.add(v_in)
                cur_e += d

        if cur_e > best_e:
            best_e = cur_e
            best_S = set(S)

    return candidate.induced_subgraph(sorted(best_S))
