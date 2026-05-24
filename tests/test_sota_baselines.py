"""Published finite-SOTA baselines and Engel Moser lattice tests."""

from __future__ import annotations

from eud.benchmarks.compare import build_baseline_frontier
from eud.benchmarks.engel_2025 import engel_2025_at
from eud.benchmarks.known_bounds import best_known_at, is_exact
from eud.families.engel_moser import (
    EngelMoserParams,
    build,
    enumerate_unit_vectors,
    is_exact_unit_vector,
)


def test_known_bounds_corrected_small_n() -> None:
    assert best_known_at(21) == 57
    assert best_known_at(30) == 93
    assert is_exact(15)
    assert is_exact(21)


def test_engel_2025_table_values() -> None:
    assert engel_2025_at(49) == 180
    assert engel_2025_at(64) == 252
    assert engel_2025_at(81) == 338
    assert engel_2025_at(100) == 439


def test_baseline_uses_engel_2025_when_available() -> None:
    rows = build_baseline_frontier(n_max=120)
    by_n = {int(r["n"]): r for r in rows}
    for n, e in [(49, 180), (64, 252), (81, 338), (100, 439)]:
        assert by_n[n]["e"] == e
        assert by_n[n]["source"] == "engel_2025"


def test_engel_moser_unit_vectors_are_exact() -> None:
    units = enumerate_unit_vectors()
    assert len(units) == 18
    assert all(is_exact_unit_vector(u) for u in units)


def test_engel_moser_candidate_builds() -> None:
    c = build(EngelMoserParams(coeff_bound=2, visible_radius=2.0))
    assert c.family == "engel_moser"
    assert c.n > 0
    assert c.e > 0
    assert len(c.unit_vectors) == 18
