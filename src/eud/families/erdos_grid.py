"""Classical Erdős square-grid construction.

Take points in the Gaussian integers Z[i] inside a side-m square, and
declare unit distance to be sqrt(K) for an integer K with many
representations as a sum of two squares. The resulting unit-distance
graph has n = m^2 points and

    e(m, K) = sum_{(a,b) : a^2 + b^2 = K, (a,b) > (0,0)} (m - |a|)(m - |b|)

(where (a,b) > (0,0) means a > 0 or (a = 0 and b > 0)).

Erdős showed that choosing K = product of the first k primes ≡ 1 (mod 4)
and m balanced against the spread of S_2(K) gives the lower bound
u(n) >= n^{1 + c / log log n}. We sweep over K-sets and m to assemble a
strong baseline frontier.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from math import isqrt

from eud.core.edges import count_edges
from eud.core.pointset import Candidate, LatticePoint


@dataclass(frozen=True)
class ErdosGridParams:
    """Parameters for the (rectangular) Erdős grid.

    Attributes:
        K: integer such that unit distance := sqrt(K). Decompositions
            (a,b) with a^2 + b^2 = K give the unit-vector directions.
        m: side length when the grid is square. If `mx` and `my` are
            both omitted, the grid is `m x m`.
        mx: width of the rectangular grid `{0,..,mx-1} x {0,..,my-1}`.
            Defaults to `m` if not set.
        my: height of the rectangular grid. Defaults to `m` if not set.
    """

    K: int = 1
    m: int = 10
    mx: int | None = None
    my: int | None = None

    @property
    def width(self) -> int:
        return self.mx if self.mx is not None else self.m

    @property
    def height(self) -> int:
        return self.my if self.my is not None else self.m


def primes_one_mod_four(limit: int) -> list[int]:
    """Primes p <= limit with p ≡ 1 (mod 4). 5, 13, 17, 29, 37, 41, ..."""
    if limit < 5:
        return []
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for p in range(2, isqrt(limit) + 1):
        if sieve[p]:
            for k in range(p * p, limit + 1, p):
                sieve[k] = False
    return [p for p in range(5, limit + 1) if sieve[p] and p % 4 == 1]


def squarefree_products_of_pmod1(primes: list[int], max_K: int) -> list[int]:
    """All squarefree products of `primes` that are <= max_K, sorted."""
    out = {1}
    for p in primes:
        out.update({k * p for k in list(out) if k * p <= max_K})
    out.discard(1)
    return sorted(out)


@cache
def sum_of_two_squares(K: int) -> list[tuple[int, int]]:
    """All (a, b) ∈ Z^2 with a^2 + b^2 = K."""
    out: list[tuple[int, int]] = []
    s = isqrt(K)
    for a in range(-s, s + 1):
        rem = K - a * a
        if rem < 0:
            continue
        b_abs = isqrt(rem)
        if b_abs * b_abs == rem:
            out.append((a, b_abs))
            if b_abs != 0:
                out.append((a, -b_abs))
    return out


def positive_unit_vectors_for_K(K: int) -> list[tuple[int, int]]:
    """Direction vectors (a,b) with a^2+b^2 = K and a > 0 or (a==0, b>0).

    Each undirected edge corresponds to exactly one such direction.
    """
    return [
        (a, b)
        for (a, b) in sum_of_two_squares(K)
        if a > 0 or (a == 0 and b > 0)
    ]


def all_unit_vectors_for_K(K: int) -> list[tuple[int, int]]:
    """All (a, b) ≠ (0, 0) with a^2+b^2 = K (both signs)."""
    return [(a, b) for (a, b) in sum_of_two_squares(K) if (a, b) != (0, 0)]


def edges_analytic(params: ErdosGridParams) -> int:
    """Closed-form edge count for a (mx x my) grid at squared-distance K.

    Directions (a, b) with |a| >= mx or |b| >= my don't fit in the grid;
    we clamp those to 0 contribution.
    """
    mx = params.width
    my = params.height
    total = 0
    for a, b in positive_unit_vectors_for_K(params.K):
        ax = mx - abs(a)
        ay = my - abs(b)
        if ax > 0 and ay > 0:
            total += ax * ay
    return total


def build(params: ErdosGridParams) -> Candidate:
    """Build the (rectangular) Erdős grid as a Candidate."""
    mx = params.width
    my = params.height
    points: list[LatticePoint] = []
    scale = 1.0 / (params.K ** 0.5)
    for x in range(mx):
        for y in range(my):
            points.append(
                LatticePoint(coeffs=(x, y), xy=(x * scale, y * scale))
            )
    units = all_unit_vectors_for_K(params.K)
    edges = count_edges(points, units)
    out_params: dict = {"K": params.K, "mx": mx, "my": my}
    if mx == my:
        out_params["m"] = mx
    return Candidate(
        family="erdos_grid",
        params=out_params,
        points=points,
        edges=edges,
        unit_vectors=units,
    )


def best_grid_for_n(
    n_target: int,
    *,
    K_candidates: list[int] | None = None,
    prime_limit: int = 200,
    K_max: int = 10_000_000,
) -> tuple[ErdosGridParams, int]:
    """For a target n = m^2, pick the K maximizing edges_analytic.

    Returns (params, e). Uses the analytic formula - no point-set built.
    """
    m = isqrt(n_target)
    if m * m != n_target:
        raise ValueError(f"n_target={n_target} is not a perfect square")
    if K_candidates is None:
        primes = primes_one_mod_four(prime_limit)
        K_candidates = [1, *squarefree_products_of_pmod1(primes, K_max)]
    best_e = -1
    best_K = 1
    for K in K_candidates:
        e = edges_analytic(ErdosGridParams(K=K, m=m))
        if e > best_e:
            best_e = e
            best_K = K
    return ErdosGridParams(K=best_K, m=m), best_e


def factor_pairs(n: int) -> list[tuple[int, int]]:
    """All ordered (mx, my) with mx * my = n and mx <= my, sorted by mx."""
    out: list[tuple[int, int]] = []
    for mx in range(1, isqrt(n) + 1):
        if n % mx == 0:
            out.append((mx, n // mx))
    return out


def best_grid_for_n_rect(
    n_target: int,
    *,
    K_candidates: list[int] | None = None,
    prime_limit: int = 200,
    K_max: int = 10_000_000,
) -> tuple[ErdosGridParams, int]:
    """For ANY n, pick the (mx, my, K) with mx*my=n maximizing edges_analytic.

    Returns (params, e). For n that is prime, the only choice is
    (1, n) which gives almost no edges, so callers may want to try
    (best_grid_for_n(n2)) for the next perfect square below. We just
    return the best rectangle.
    """
    if K_candidates is None:
        primes = primes_one_mod_four(prime_limit)
        K_candidates = [1, *squarefree_products_of_pmod1(primes, K_max)]
    best_e = -1
    best_params = ErdosGridParams(K=1, m=1, mx=1, my=n_target)
    for mx, my in factor_pairs(n_target):
        for K in K_candidates:
            params = ErdosGridParams(K=K, m=max(mx, my), mx=mx, my=my)
            e = edges_analytic(params)
            if e > best_e:
                best_e = e
                best_params = params
    return best_params, best_e


def sweep_frontier(
    *,
    m_values: list[int],
    K_max: int = 10_000_000,
    prime_limit: int = 200,
) -> list[dict]:
    """Best (n, e, K) per m on the *square* grid only. JSONL-ready dicts."""
    primes = primes_one_mod_four(prime_limit)
    Ks = [1, *squarefree_products_of_pmod1(primes, K_max)]
    rows: list[dict] = []
    for m in m_values:
        params, e = best_grid_for_n(m * m, K_candidates=Ks)
        rows.append(
            {
                "family": "erdos_grid",
                "n": m * m,
                "e": e,
                "density": e / (m * m),
                "K": params.K,
                "m": m,
            }
        )
    return rows


def sweep_frontier_rect(
    *,
    n_values: list[int],
    K_max: int = 10_000_000,
    prime_limit: int = 200,
) -> list[dict]:
    """Best (n, e, K, mx, my) per n on the rectangular grid. JSONL-ready.

    For every n in `n_values` we try every factorization mx * my = n and
    every K candidate, returning the densest grid graph. Square grids are
    a strict special case (mx = my). Note that for prime n only the
    degenerate (1, n) grid exists, which gives 0 unit edges.
    """
    primes = primes_one_mod_four(prime_limit)
    Ks = [1, *squarefree_products_of_pmod1(primes, K_max)]
    rows: list[dict] = []
    for n in n_values:
        params, e = best_grid_for_n_rect(n, K_candidates=Ks)
        rows.append(
            {
                "family": "erdos_grid",
                "n": n,
                "e": e,
                "density": e / n if n else 0.0,
                "K": params.K,
                "mx": params.width,
                "my": params.height,
            }
        )
    return rows
