"""Tests for bounded common-denominator Moser ring experiments."""

from __future__ import annotations

from eud.families.engel_moser import enumerate_unit_vectors as enumerate_engel_units
from eud.families.moser_ring import (
    MoserRingParams,
    build,
    enumerate_unit_vectors,
    is_exact_unit_vector,
)
from eud.search.engel_beam import BeamConfig, beam_search
from eud.search.prune import greedy_peel


def test_moser_ring_denominator_zero_matches_engel_unit_count() -> None:
    params = MoserRingParams(denom_power=0)
    assert enumerate_unit_vectors(params) == enumerate_engel_units()


def test_moser_ring_denominator_one_has_more_unit_directions() -> None:
    params = MoserRingParams(denom_power=1)
    units = enumerate_unit_vectors(params)
    assert len(units) > 18
    assert all(is_exact_unit_vector(u, params.denom_power) for u in units)


def test_moser_ring_candidate_builds() -> None:
    candidate = build(MoserRingParams(denom_power=1, coeff_bound=3, visible_radius=2.0))
    assert candidate.family == "moser_ring"
    assert candidate.n > 0
    assert candidate.e > 0
    assert len(candidate.unit_vectors) > 18


def test_moser_ring_can_use_beam_engine() -> None:
    seed = build(MoserRingParams(denom_power=1, coeff_bound=2, visible_radius=1.5))
    k = 8
    greedy = greedy_peel(seed, k)
    result = beam_search(
        seed,
        k,
        config=BeamConfig(
            width=2,
            rounds=1,
            max_additions_per_state=3,
            drop_branches=2,
            include_parallelograms=False,
        ),
    )
    assert result.candidate.family == "moser_ring"
    assert result.candidate.n == k
    assert result.candidate.e >= greedy.e
