"""Curated table of best-known lower bounds for u(n).

u(n) := the maximum number of unit-distance pairs among n points in R^2.

Source notes:
- Exact values for n in [1, 21] are known after
  Alexeev--Mixon--Parshall (2025), extending earlier exact work of
  Edelsbrunner et al., Schade, and Ágoston--Pálvölgyi.
- Lower bounds for n in [22, 30] are from the densest-known graphs
  reproduced by Engel--Hammond-Lee--Su--Varga--Zsámboki (2025), Table 2.
- For n >= 31, published densest-known values through n=100 live in
  `benchmarks.engel_2025`; this table intentionally stays limited to
  the classic small-n curated values.
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
    (15, 37, True),
    (16, 41, True),
    (17, 43, True),
    (18, 46, True),
    (19, 50, True),
    (20, 54, True),
    (21, 57, True),
    (22, 60, False),
    (23, 64, False),
    (24, 68, False),
    (25, 72, False),
    (26, 76, False),
    (27, 81, False),
    (28, 85, False),
    (29, 89, False),
    (30, 93, False),
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
