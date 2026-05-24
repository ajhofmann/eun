"""Scoring candidates against a frontier."""

from __future__ import annotations

from dataclasses import dataclass

from eud.core.pointset import Candidate


@dataclass
class Frontier:
    """Best-known (n, e) pairs across families. n -> e mapping."""

    rows: dict[int, int]

    @classmethod
    def from_jsonl_rows(cls, rows: list[dict]) -> Frontier:
        best: dict[int, int] = {}
        for r in rows:
            n = int(r["n"])
            e = int(r["e"])
            if e > best.get(n, -1):
                best[n] = e
        return cls(rows=best)

    def best_edges_at(self, n: int) -> int | None:
        return self.rows.get(n)

    def best_at_or_below(self, n: int) -> int:
        """Max e among entries with n' <= n. Useful as a non-decreasing bound."""
        out = 0
        for k, e in self.rows.items():
            if k <= n and e > out:
                out = e
        return out


def improvement(candidate: Candidate, frontier: Frontier) -> int | None:
    """Return e(candidate) - frontier.best_edges_at(candidate.n), or None
    if the frontier has no entry at this n.
    """
    base = frontier.best_edges_at(candidate.n)
    if base is None:
        return None
    return candidate.e - base


def is_record(candidate: Candidate, frontier: Frontier) -> bool:
    delta = improvement(candidate, frontier)
    return delta is not None and delta > 0
