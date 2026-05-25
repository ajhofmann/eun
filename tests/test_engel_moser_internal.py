"""Tests for internal Engel-Moser beyond-100 benchmark rows."""

from __future__ import annotations

from eud.benchmarks.compare import build_baseline_frontier
from eud.benchmarks.engel_moser_internal import engel_moser_internal_at


def test_internal_table_has_n121() -> None:
    assert engel_moser_internal_at(121) == 557


def test_baseline_includes_internal_post_100() -> None:
    rows = build_baseline_frontier(n_max=150, include_rect_grid=False, include_triangular=False, include_moser_hex=False)
    row_121 = next(r for r in rows if int(r["n"]) == 121)
    assert int(row_121["e"]) >= 557
    assert row_121.get("family") in {"engel_moser_internal", "engel_2025"}
