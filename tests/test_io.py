"""Round-trip serialization for Candidate and JSONL streams."""

from __future__ import annotations

from pathlib import Path

from eud.core.io import (
    append_jsonl,
    candidate_from_dict,
    candidate_to_dict,
    read_candidate,
    read_jsonl,
    write_candidate,
    write_jsonl,
)
from eud.core.pointset import Candidate, LatticePoint


def _toy_candidate() -> Candidate:
    pts = [
        LatticePoint(coeffs=(0, 0), xy=(0.0, 0.0)),
        LatticePoint(coeffs=(1, 0), xy=(1.0, 0.0)),
    ]
    return Candidate(
        family="toy",
        params={"k": 1},
        points=pts,
        edges=[(0, 1)],
        unit_vectors=[(1, 0)],
    )


def test_candidate_roundtrip(tmp_path: Path) -> None:
    c = _toy_candidate()
    p = write_candidate(c, tmp_path / "c.json")
    loaded = read_candidate(p)
    assert loaded.family == c.family
    assert loaded.params == c.params
    assert loaded.n == c.n
    assert loaded.e == c.e
    assert loaded.points[0].coeffs == (0, 0)
    assert loaded.unit_vectors == c.unit_vectors


def test_dict_roundtrip() -> None:
    c = _toy_candidate()
    assert candidate_from_dict(candidate_to_dict(c)).edges == c.edges


def test_jsonl_streaming(tmp_path: Path) -> None:
    rows = [{"i": i, "v": i * i} for i in range(5)]
    p = write_jsonl(rows, tmp_path / "rows.jsonl")
    loaded = list(read_jsonl(p))
    assert loaded == rows


def test_jsonl_append(tmp_path: Path) -> None:
    p = tmp_path / "a.jsonl"
    append_jsonl({"x": 1}, p)
    append_jsonl({"x": 2}, p)
    assert [r["x"] for r in read_jsonl(p)] == [1, 2]
