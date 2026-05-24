"""Reproducible JSON certificates for unit-distance graph claims.

A certificate proves the *lower-bound* claim "this graph has at least e
unit edges on n distinct points" - it does NOT claim maximality of the
unit-distance graph. We emit:

- field defining polynomial / basis description,
- visible embedding,
- integer-coefficient point list,
- integer-coefficient unit-vector list,
- claimed edges,
- per-edge exact squared-distance check (sympy by default; cypari2
  cross-check optional),
- distinctness of points by coefficient tuple.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from eud.core.algebra import ExactSquaredDistance, is_exact_unit
from eud.core.pointset import Candidate


def _diff(candidate: Candidate, i: int, j: int) -> tuple[int, ...]:
    return tuple(
        b - a
        for a, b in zip(
            candidate.points[i].coeffs,
            candidate.points[j].coeffs,
            strict=True,
        )
    )


def build_certificate(
    candidate: Candidate,
    *,
    field_description: str,
    basis_description: list[str],
    visible_embedding: str,
    sd: ExactSquaredDistance | None = None,
    sample_edges: int | None = None,
    pari_field: Any | None = None,
    pari_prec_bits: int = 256,
    pari_tol: float = 1e-10,
) -> dict[str, Any]:
    """Build a JSON-serializable certificate for `candidate`.

    Args:
        sd: an exact symbolic squared-distance function (e.g. from
            `eud.families.cyclotomic.squared_distance_symbolic`). If
            provided, every claimed edge is checked exactly.
        sample_edges: if non-None, only check this many evenly-spaced
            edges. Default None means check ALL edges.
        pari_field: optional `families.pari_fields.NumberField` to
            cross-verify each edge with high-precision PARI arithmetic.

    The certificate is a plain dict, ready for orjson serialization.
    """
    coeffs = [list(p.coeffs) for p in candidate.points]
    distinct = len({p.coeffs for p in candidate.points}) == candidate.n

    cert: dict[str, Any] = {
        "schema_version": 1,
        "created_at": datetime.now(tz=UTC).isoformat(),
        "family": candidate.family,
        "params": candidate.params,
        "field": field_description,
        "basis": basis_description,
        "visible_embedding": visible_embedding,
        "n": candidate.n,
        "e": candidate.e,
        "points_coeffs": coeffs,
        "edges": [list(e) for e in candidate.edges],
        "unit_vector_coeffs": [list(u) for u in candidate.unit_vectors],
        "checks": {
            "all_points_distinct": distinct,
            "non_edge_policy": "lower-bound only; maximality not claimed",
        },
    }

    if pari_field is not None:
        try:
            cert["pari_field"] = pari_field.to_dict()
        except Exception as exc:  # pragma: no cover - defensive
            cert["pari_field"] = {"error": str(exc)}

    if sd is not None:
        edges_to_check = candidate.edges
        if sample_edges is not None and len(edges_to_check) > sample_edges:
            step = max(1, len(edges_to_check) // sample_edges)
            edges_to_check = edges_to_check[::step]

        bad_sympy: list[list[int]] = []
        for i, j in edges_to_check:
            if not is_exact_unit(_diff(candidate, i, j), sd):
                bad_sympy.append([i, j])
        cert["checks"]["edges_checked_sympy"] = len(edges_to_check)
        cert["checks"]["edges_failing_sympy"] = bad_sympy
        cert["checks"]["all_sympy_unit"] = not bad_sympy

    if pari_field is not None:
        bad_pari: list[list[int]] = []
        for i, j in candidate.edges:
            ok = pari_field.is_unit_visible_embedding(
                list(_diff(candidate, i, j)),
                prec_bits=pari_prec_bits,
                tol=pari_tol,
            )
            if not ok:
                bad_pari.append([i, j])
        cert["checks"]["edges_checked_pari"] = len(candidate.edges)
        cert["checks"]["edges_failing_pari"] = bad_pari
        cert["checks"]["all_pari_unit"] = not bad_pari

    return cert
