"""Serialization for candidates, frontier rows, and certificates.

JSON for single-record artifacts (candidates, certificates).
JSONL for streaming runs and frontier tables (one row per construction).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import orjson

from eud.core.pointset import Candidate, LatticePoint


def candidate_to_dict(c: Candidate) -> dict[str, Any]:
    return {
        "family": c.family,
        "params": c.params,
        "n": c.n,
        "e": c.e,
        "density": c.density,
        "points": [
            {"coeffs": list(p.coeffs), "xy": list(p.xy), "aux": list(p.aux)}
            for p in c.points
        ],
        "edges": [list(e) for e in c.edges],
        "unit_vectors": [list(u) for u in c.unit_vectors],
        "certificate": c.certificate,
        "notes": c.notes,
    }


def candidate_from_dict(d: dict[str, Any]) -> Candidate:
    points = [
        LatticePoint(
            coeffs=tuple(p["coeffs"]),
            xy=tuple(p["xy"]),
            aux=tuple(p.get("aux", [])),
        )
        for p in d["points"]
    ]
    return Candidate(
        family=d["family"],
        params=d.get("params", {}),
        points=points,
        edges=[tuple(e) for e in d["edges"]],
        unit_vectors=[tuple(u) for u in d.get("unit_vectors", [])],
        certificate=d.get("certificate"),
        notes=d.get("notes", {}),
    )


def write_candidate(c: Candidate, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(orjson.dumps(candidate_to_dict(c), option=orjson.OPT_INDENT_2))
    return p


def read_candidate(path: str | Path) -> Candidate:
    p = Path(path)
    return candidate_from_dict(orjson.loads(p.read_bytes()))


def write_jsonl(rows: Iterable[dict[str, Any]], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        for row in rows:
            f.write(orjson.dumps(row))
            f.write(b"\n")
    return p


def append_jsonl(row: dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("ab") as f:
        f.write(orjson.dumps(row))
        f.write(b"\n")
    return p


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    p = Path(path)
    with p.open("rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield orjson.loads(line)
