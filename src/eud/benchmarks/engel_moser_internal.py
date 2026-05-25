"""Certified Engel-Moser beam results beyond Engel et al. Table 2.

These are densest-known values produced by this repository's Engel-Moser
search, not literature claims. Use them for honest post-100 benchmarking
until an external table exists.
"""

from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_PATH = Path("data/runs/engel_moser_beyond_100.json")

# Fallback if the summary JSON has not been generated yet.
_FALLBACK_BOUNDS: list[tuple[int, int]] = [
    (121, 557),
    (144, 692),
    (169, 835),
    (196, 994),
    (225, 1161),
    (289, 1572),
]


def _load_bounds(path: Path = _DEFAULT_PATH) -> list[tuple[int, int]]:
    if path.exists():
        rows = json.loads(path.read_text())
        return [(int(r["k"]), int(r["e"])) for r in rows]
    return list(_FALLBACK_BOUNDS)


def engel_moser_internal_at(n: int, *, path: Path = _DEFAULT_PATH) -> int | None:
    """Return our certified Engel-Moser best at n, if tabulated beyond n=100."""
    for k, e in _load_bounds(path):
        if k == n:
            return e
    return None


def engel_moser_internal_rows(*, path: Path = _DEFAULT_PATH) -> list[dict]:
    """JSONL-ready rows for the internal post-100 Engel-Moser table."""
    return [
        {
            "family": "engel_moser_internal",
            "source": "engel_moser_beam_beyond_100",
            "n": n,
            "e": e,
            "density": e / n,
            "exact": False,
            "citation": "erdos-unit-search Engel-Moser beam (certified in data/verified/)",
        }
        for n, e in _load_bounds(path)
    ]
