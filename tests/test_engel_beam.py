"""Tests for Engel-style coefficient-space beam search."""

from __future__ import annotations

from eud.families.engel_moser import EngelMoserParams, build, enumerate_unit_vectors
from eud.search.engel_beam import (
    BeamConfig,
    beam_search,
    boundary_additions,
    canonicalize,
    edge_count_for_coeffs,
    triangle_additions,
)
from eud.search.prune import greedy_peel


def test_canonicalize_removes_translations() -> None:
    state = {(3, 1, 0, 0), (4, 1, 0, 0), (3, 2, 0, 0)}
    shifted = {(13, -4, 2, 1), (14, -4, 2, 1), (13, -3, 2, 1)}
    assert canonicalize(state) == canonicalize(shifted)


def test_boundary_and_triangle_additions_are_nonempty() -> None:
    units = [tuple(u) for u in enumerate_unit_vectors()]
    coeffs = {(0, 0, 0, 0), units[0]}
    assert boundary_additions(coeffs, units)
    assert triangle_additions(coeffs, units)


def test_edge_count_for_coeffs_matches_candidate_edges() -> None:
    candidate = build(EngelMoserParams(coeff_bound=2, visible_radius=2.0))
    coeffs = {tuple(p.coeffs) for p in candidate.points}
    assert edge_count_for_coeffs(coeffs, [tuple(u) for u in candidate.unit_vectors]) == candidate.e


def test_beam_search_matches_greedy_on_small_seed() -> None:
    seed = build(EngelMoserParams(coeff_bound=2, visible_radius=2.0))
    k = 12
    greedy = greedy_peel(seed, k)
    result = beam_search(seed, k, config=BeamConfig(width=8, rounds=4, max_additions_per_state=8))
    assert result.candidate.n == k
    assert result.candidate.e >= greedy.e
    assert result.states_seen > 0
