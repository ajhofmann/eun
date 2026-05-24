"""Generation API tests for the interactive web explorer."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from eud.web_api import CompareRequest, GenerateRequest, compare, generate


def test_generate_erdos_grid_candidate_json() -> None:
    out = generate(GenerateRequest(construction="erdos_grid", params={"K": 1, "m": 3}))

    assert out["family"] == "erdos_grid"
    assert out["params"]["K"] == 1
    assert out["n"] == 9
    assert out["e"] == 12
    assert len(out["points"]) == 9
    assert len(out["edges"]) == 12


def test_generate_moser_hex_candidate_json() -> None:
    out = generate(
        GenerateRequest(
            construction="moser_hex",
            params={"zeta_order": 6, "coeff_bound": 1, "visible_radius": 2.0},
        )
    )

    assert out["family"] == "moser_hex"
    assert out["n"] > 0
    assert out["e"] > 0
    assert out["unit_vectors"]


def test_generate_engel_moser_candidate_json() -> None:
    out = generate(
        GenerateRequest(
            construction="engel_moser",
            params={"coeff_bound": 2, "visible_radius": 2.0, "window_kind": "visible_disk"},
        )
    )

    assert out["family"] == "engel_moser"
    assert out["n"] > 0
    assert len(out["unit_vectors"]) == 18


def test_generate_moser_ring_candidate_json() -> None:
    out = generate(
        GenerateRequest(
            construction="moser_ring",
            params={
                "denom_power": 1,
                "coeff_bound": 2,
                "visible_radius": 1.5,
                "window_kind": "visible_disk",
            },
        )
    )

    assert out["family"] == "moser_ring"
    assert out["n"] > 0
    assert len(out["unit_vectors"]) > 18


def test_generate_rejects_unknown_params() -> None:
    with pytest.raises(HTTPException) as exc:
        generate(GenerateRequest(construction="erdos_grid", params={"K": 1, "bogus": 2}))

    assert exc.value.status_code == 400
    assert "unknown parameter" in str(exc.value.detail)


def test_generate_rejects_oversized_grid() -> None:
    with pytest.raises(HTTPException) as exc:
        generate(GenerateRequest(construction="erdos_grid", params={"K": 1, "m": 100}))

    assert exc.value.status_code == 400
    assert "max" in str(exc.value.detail)


def test_compare_subset_of_constructions_returns_pinned_n() -> None:
    out = compare(
        CompareRequest(
            target_n=25,
            constructions=["moser_hex", "engel_moser", "erdos_grid"],
        )
    )

    assert out["target_n"] == 25
    by_id = {entry["id"]: entry for entry in out["results"]}
    assert set(by_id) == {"moser_hex", "engel_moser", "erdos_grid"}
    for entry in by_id.values():
        assert "candidate" in entry, f"{entry['id']} returned an error: {entry.get('error')}"
        cand = entry["candidate"]
        assert cand["n"] == 25
        assert cand["e"] >= 0
        assert len(cand["points"]) == 25
        assert entry["source"]["n"] >= 25


def test_compare_rejects_out_of_range_target() -> None:
    with pytest.raises(HTTPException) as exc:
        compare(CompareRequest(target_n=1))

    assert exc.value.status_code == 400
    assert "target_n" in str(exc.value.detail)

