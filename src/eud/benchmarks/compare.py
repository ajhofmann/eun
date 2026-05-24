"""Build a baseline frontier and compare candidates against it.

Published baseline = max over (literature curated table, Engel et al. 2025
beam-search table, rectangular Erdős grid sweep, triangular Z[zeta_6]
hex/parallelogram/strip sweep, Moser visible-disk sweep) for every n in
[1, n_max].

The strict frontier replaces the older "literature + square Erdős grid"
frontier and is the right denominator for any "beats SOTA" claim against
finite constructions.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from eud.benchmarks.engel_2025 import engel_2025_rows
from eud.benchmarks.known_bounds import known_bounds_rows
from eud.benchmarks.score import Frontier
from eud.core.io import read_jsonl, write_jsonl
from eud.families.erdos_grid import sweep_frontier_rect as grid_sweep_rect


def build_baseline_frontier(
    *,
    n_max: int = 1000,
    K_max: int = 10_000_000,
    prime_limit: int = 200,
    include_triangular: bool = True,
    include_moser_hex: bool = True,
    include_rect_grid: bool = True,
    include_engel_2025: bool = True,
) -> list[dict]:
    """Best finite-construction frontier for u(n) at every n in [1, n_max].

    Sources (each row keeps a `source` / `family` tag for provenance):
      - `known_bounds`: literature-curated values for n in [1, 30]
      - `engel_2025`: published densest-known beam-search values for n in [1, 100]
      - `erdos_grid`: rectangular grid sweep at every n
      - `triangular`: hex / parallelogram / strip sweep at every n
      - `moser_hex`: visible-disk Moser sweep at every n in {25, ..., n_max}

    Per n we keep the row with max `e` and tag `source` with the
    contributing family. Ties: known_bounds > erdos_grid > triangular >
    moser_hex (so the simpler / more cited row wins).
    """
    rows: list[dict] = []

    rows.extend(known_bounds_rows())

    if include_engel_2025:
        rows.extend(r for r in engel_2025_rows() if int(r["n"]) <= n_max)

    if include_rect_grid:
        rows.extend(
            grid_sweep_rect(
                n_values=list(range(2, n_max + 1)),
                K_max=K_max,
                prime_limit=prime_limit,
            )
        )

    if include_triangular:
        from eud.families.triangular import sweep_frontier as tri_sweep

        rows.extend(tri_sweep(n_values=list(range(2, n_max + 1))))

    if include_moser_hex:
        from eud.families.moser import sweep_frontier as moser_sweep

        rows.extend(moser_sweep(n_values=list(range(25, n_max + 1))))

    priority = {
        "known_bounds": 0,
        "engel_2025": 1,
        "erdos_grid": 2,
        "triangular": 3,
        "moser_hex": 4,
    }

    best: dict[int, dict] = {}
    for r in rows:
        n = int(r["n"])
        e = int(r["e"])
        fam = r.get("family", "?")
        prio = priority.get(fam, 99)
        cur = best.get(n)
        if cur is None:
            best[n] = {**r, "source": fam}
            continue
        cur_e = int(cur["e"])
        cur_prio = priority.get(cur.get("family", "?"), 99)
        if e > cur_e or (e == cur_e and prio < cur_prio):
            best[n] = {**r, "source": fam}
    return [best[n] for n in sorted(best)]


def write_baseline_frontier(path: str | Path, *, n_max: int = 1000) -> Path:
    rows = build_baseline_frontier(n_max=n_max)
    return write_jsonl(rows, path)


def load_frontier(path: str | Path) -> Frontier:
    return Frontier.from_jsonl_rows(list(read_jsonl(path)))


def compare_candidates_to_frontier(
    candidates: Iterable[dict],
    frontier: Frontier,
) -> list[dict]:
    """Annotate candidate dicts with frontier comparison."""
    out: list[dict] = []
    for c in candidates:
        n = int(c["n"])
        e = int(c["e"])
        base = frontier.best_edges_at(n)
        below_or_at = frontier.best_at_or_below(n)
        out.append(
            {
                **c,
                "frontier_e_at_n": base,
                "frontier_e_below_or_at_n": below_or_at,
                "improvement_at_n": (e - base) if base is not None else None,
                "improvement_vs_below_or_at": e - below_or_at,
                "beats_frontier": (base is not None and e > base),
            }
        )
    return out
