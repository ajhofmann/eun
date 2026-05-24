"""Curated table of best-known lower bounds for u(n).

u(n) := the maximum number of unit-distance pairs among n points in R^2.

Source notes:
- Exact values for n in [1, 14] are known (Edelsbrunner et al; Schade survey).
- Lower bounds for n in [15, 30] are taken from published constructions
  (Schade 2020; OEIS A186705 and related sequences).
- For n >= 31 we do NOT carry a literature-curated entry here: the
  published values stop at n=30 in the most recent Schade-style surveys
  we could find. Instead the strict baseline at n >= 31 is built from
  the maximum over our own construction sweeps (rectangular Erdős grid,
  triangular Z[zeta_6] hex disk, Moser visible-disk, cyclotomic
  cut-and-project) inside `benchmarks/compare.build_baseline_frontier`.
- We treat values for n >= 15 as best-known *lower bounds* unless flagged
  exact. Higher-n entries in this table are conservative and meant as a
  benchmark, not as an exhaustive frontier - any new construction is
  scored against the maximum of (this table, sweep_frontier output) at
  each n.

When a candidate's edge count exceeds the value here at the same n, that
is a "beats_known" hit and gets surfaced in the leaderboard.
"""

from __future__ import annotations

# (n, e_lower_bound, exact?)
KNOWN_BOUNDS: list[tuple[int, int, bool]] = [
    (1, 0, True),
    (2, 1, True),
    (3, 3, True),
    (4, 5, True),
    (5, 7, True),
    (6, 9, True),
    (7, 12, True),
    (8, 14, True),
    (9, 18, True),
    (10, 20, True),
    (11, 23, True),
    (12, 27, True),
    (13, 30, True),
    (14, 33, True),
    (15, 37, False),
    (16, 42, False),
    (17, 44, False),
    (18, 49, False),
    (19, 52, False),
    (20, 56, False),
    (21, 61, False),
    (22, 65, False),
    (23, 70, False),
    (24, 74, False),
    (25, 80, False),
    (26, 85, False),
    (27, 90, False),
    (28, 95, False),
    (29, 99, False),
    (30, 105, False),
]


def best_known_at(n: int) -> int | None:
    """Return the curated best-known lower bound at n (or None if not in table)."""
    for k, e, _ in KNOWN_BOUNDS:
        if k == n:
            return e
    return None


def is_exact(n: int) -> bool:
    """Is u(n) known exactly at this n?"""
    for k, _, exact in KNOWN_BOUNDS:
        if k == n:
            return exact
    return False


def known_bounds_rows() -> list[dict]:
    """JSONL-ready rows for the known-bounds table."""
    return [
        {
            "family": "known_bounds",
            "n": n,
            "e": e,
            "density": e / n,
            "exact": exact,
        }
        for n, e, exact in KNOWN_BOUNDS
    ]
