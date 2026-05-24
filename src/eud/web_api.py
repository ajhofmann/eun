"""Local API for generating candidate graphs for the web explorer."""

from __future__ import annotations

from typing import Any, Literal

import sympy as sp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from eud.core.io import candidate_to_dict
from eud.core.pointset import Candidate

Construction = Literal["moser_hex", "engel_moser", "moser_ring", "moser", "cyclotomic", "erdos_grid"]

MAX_RENDER_POINTS = 8_000
MAX_ENUMERATED_COEFFS = 250_000


class GenerateRequest(BaseModel):
    """Request body for a graph generation run."""

    construction: Construction = "moser_hex"
    params: dict[str, Any] = Field(default_factory=dict)


class CompareRequest(BaseModel):
    """Request body for a multi-construction comparison at a fixed target n."""

    target_n: int = 100
    constructions: list[Construction] | None = None


COMPARE_DEFAULT_CONSTRUCTIONS: tuple[Construction, ...] = (
    "moser_hex",
    "engel_moser",
    "moser_ring",
    "cyclotomic",
    "erdos_grid",
)
COMPARE_MIN_N = 4
COMPARE_MAX_N = 600


app = FastAPI(title="eud graph explorer API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/constructions")
def constructions() -> dict[str, list[dict[str, Any]]]:
    return {
        "constructions": [
            {
                "id": "moser_hex",
                "name": "Moser visible disk",
                "params": ["zeta_order", "coeff_bound", "visible_radius"],
            },
            {
                "id": "engel_moser",
                "name": "Engel 18-unit Moser lattice",
                "params": ["coeff_bound", "visible_radius", "window_kind"],
            },
            {
                "id": "moser_ring",
                "name": "Moser ring common denominator",
                "params": ["denom_power", "coeff_bound", "visible_radius", "window_kind"],
            },
            {
                "id": "moser",
                "name": "Moser coefficient box",
                "params": ["zeta_order", "coeff_bound"],
            },
            {
                "id": "cyclotomic",
                "name": "Cyclotomic cut-and-project",
                "params": [
                    "m",
                    "coeff_bound",
                    "R",
                    "window_kind",
                    "translation_seed",
                    "translation_scale",
                ],
            },
            {
                "id": "erdos_grid",
                "name": "Erdos grid",
                "params": ["K", "m", "mx", "my"],
            },
        ]
    }


@app.post("/api/generate")
def generate(req: GenerateRequest) -> dict[str, Any]:
    try:
        candidate = _build_candidate(req.construction, req.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if candidate.n > MAX_RENDER_POINTS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"generated {candidate.n} points; the interactive viewer limit is "
                f"{MAX_RENDER_POINTS}. Lower the bounds or window size."
            ),
        )
    return candidate_to_dict(candidate)


@app.post("/api/compare")
def compare(req: CompareRequest) -> dict[str, Any]:
    """Build every requested construction and greedy-peel to the same target n."""

    if req.target_n < COMPARE_MIN_N or req.target_n > COMPARE_MAX_N:
        raise HTTPException(
            status_code=400,
            detail=(
                f"target_n must be between {COMPARE_MIN_N} and {COMPARE_MAX_N} for the "
                "interactive comparison view"
            ),
        )

    ids: tuple[Construction, ...] = (
        tuple(req.constructions) if req.constructions else COMPARE_DEFAULT_CONSTRUCTIONS
    )
    seen: set[str] = set()
    unique_ids: list[Construction] = []
    for cid in ids:
        if cid in seen:
            continue
        seen.add(cid)
        unique_ids.append(cid)

    results: list[dict[str, Any]] = []
    for cid in unique_ids:
        label = _CONSTRUCTION_LABELS.get(cid, cid)
        try:
            candidate, source = _compare_build(cid, req.target_n)
        except ValueError as exc:
            results.append({"id": cid, "label": label, "error": str(exc)})
            continue
        if candidate is None:
            results.append(
                {
                    "id": cid,
                    "label": label,
                    "error": (
                        f"no parameter combination produced n >= {req.target_n} within "
                        "the comparison sweep budget"
                    ),
                }
            )
            continue
        results.append(
            {
                "id": cid,
                "label": label,
                "candidate": candidate_to_dict(candidate),
                "source": source,
            }
        )
    return {"target_n": req.target_n, "results": results}


_CONSTRUCTION_LABELS: dict[str, str] = {
    "moser_hex": "Moser visible disk",
    "engel_moser": "Engel 18-unit Moser",
    "moser_ring": "Moser ring (k=1)",
    "moser": "Moser coefficient box",
    "cyclotomic": "Cyclotomic Z[zeta_12]",
    "erdos_grid": "Erdos grid",
}


def _compare_build(
    cid: Construction, target_n: int
) -> tuple[Candidate | None, dict[str, Any]]:
    """Run a small sweep and return the densest greedy-peeled subgraph at target_n.

    Returns (candidate, source_metadata). source_metadata records the params and
    pre-prune (n, e) of the best source candidate so the frontend can show how
    much we pruned away.
    """
    from eud.search.prune import greedy_peel

    best: Candidate | None = None
    best_source: dict[str, Any] = {}
    for cand in _compare_sweep(cid, target_n):
        if cand.n < target_n:
            continue
        if cand.n > MAX_RENDER_POINTS:
            continue
        sub = greedy_peel(cand, target_n)
        if best is None or sub.e > best.e:
            best = sub
            best_source = {
                "n": cand.n,
                "e": cand.e,
                "params": dict(cand.params),
            }
    return best, best_source


def _compare_sweep(cid: Construction, target_n: int):
    """Yield candidate builds for a construction sized around `target_n`."""
    if cid == "moser_hex":
        from eud.families.moser import MoserParams, build_in_visible_disk

        for zeta_order, coeff_bound, radius in [
            (6, 4, 2.5),
            (6, 4, 3.5),
            (6, 4, 5.0),
            (12, 4, 2.5),
            (12, 4, 3.5),
            (6, 5, 6.0),
            (12, 5, 6.0),
        ]:
            try:
                yield build_in_visible_disk(
                    MoserParams(zeta_order=zeta_order, coeff_bound=coeff_bound),
                    radius=radius,
                    coeff_bound=coeff_bound,
                )
            except ValueError:
                continue
        return

    if cid == "engel_moser":
        from eud.families.engel_moser import EngelMoserParams, build

        for coeff_bound, radius in [
            (3, 1.8),
            (3, 2.4),
            (4, 2.4),
            (4, 3.0),
            (4, 4.0),
            (5, 4.0),
        ]:
            try:
                yield build(
                    EngelMoserParams(
                        coeff_bound=coeff_bound,
                        visible_radius=radius,
                        window_kind="visible_disk",
                    )
                )
            except ValueError:
                continue
        return

    if cid == "moser_ring":
        from eud.families.moser_ring import MoserRingParams, build

        for denom_power, coeff_bound, radius in [
            (1, 2, 1.0),
            (1, 2, 1.5),
            (1, 3, 1.5),
            (1, 3, 2.0),
            (1, 4, 2.0),
            (1, 4, 2.5),
        ]:
            try:
                yield build(
                    MoserRingParams(
                        denom_power=denom_power,
                        coeff_bound=coeff_bound,
                        visible_radius=radius,
                        window_kind="visible_disk",
                    )
                )
            except ValueError:
                continue
        return

    if cid == "cyclotomic":
        from eud.families.cyclotomic import CyclotomicParams, build

        for m, coeff_bound, radius in [
            (5, 4, 2.0),
            (5, 6, 2.5),
            (8, 4, 2.0),
            (8, 5, 2.5),
            (12, 4, 2.0),
            (12, 4, 2.5),
            (12, 5, 2.5),
        ]:
            rank = int(sp.totient(m))
            if (2 * coeff_bound + 1) ** rank > MAX_ENUMERATED_COEFFS:
                continue
            try:
                yield build(
                    CyclotomicParams(
                        m=m,
                        coeff_bound=coeff_bound,
                        R=radius,
                        window_kind="ball",
                    )
                )
            except ValueError:
                continue
        return

    if cid == "erdos_grid":
        from eud.families.erdos_grid import best_grid_for_n_rect, build

        try:
            params, _ = best_grid_for_n_rect(target_n)
            yield build(params)
        except ValueError:
            return
        return

    if cid == "moser":
        from eud.families.moser import MoserParams, build

        for zeta_order, coeff_bound in [(6, 2), (6, 3), (12, 2), (12, 3)]:
            if (2 * coeff_bound + 1) ** 4 > MAX_RENDER_POINTS:
                continue
            try:
                yield build(MoserParams(zeta_order=zeta_order, coeff_bound=coeff_bound))
            except ValueError:
                continue
        return


def _build_candidate(construction: Construction, params: dict[str, Any]) -> Candidate:
    if construction == "moser_hex":
        _reject_unknown(params, {"zeta_order", "coeff_bound", "visible_radius"})
        from eud.families.moser import MoserParams, build_in_visible_disk

        coeff_bound = _int_param(params, "coeff_bound", 4, min_value=1, max_value=6)
        return build_in_visible_disk(
            MoserParams(
                zeta_order=_int_param(params, "zeta_order", 6, min_value=3, max_value=30),
                coeff_bound=coeff_bound,
            ),
            radius=_float_param(params, "visible_radius", 4.0, min_value=0.1, max_value=30.0),
            coeff_bound=coeff_bound,
        )

    if construction == "engel_moser":
        _reject_unknown(params, {"coeff_bound", "visible_radius", "window_kind"})
        from eud.families.engel_moser import EngelMoserParams, build

        coeff_bound = _int_param(params, "coeff_bound", 3, min_value=1, max_value=5)
        window_kind = _string_param(
            params,
            "window_kind",
            "visible_disk",
            allowed={"visible_disk", "coeff_box"},
        )
        if window_kind == "coeff_box" and (2 * coeff_bound + 1) ** 4 > MAX_RENDER_POINTS:
            raise ValueError(f"engel_moser coeff_bound={coeff_bound} exceeds the point limit")
        return build(
            EngelMoserParams(
                coeff_bound=coeff_bound,
                visible_radius=_float_param(
                    params, "visible_radius", 3.0, min_value=0.1, max_value=30.0
                ),
                window_kind=window_kind,
            )
        )

    if construction == "moser_ring":
        _reject_unknown(params, {"denom_power", "coeff_bound", "visible_radius", "window_kind"})
        from eud.families.moser_ring import MoserRingParams, build

        coeff_bound = _int_param(params, "coeff_bound", 3, min_value=1, max_value=5)
        window_kind = _string_param(
            params,
            "window_kind",
            "visible_disk",
            allowed={"visible_disk", "coeff_box"},
        )
        if window_kind == "coeff_box" and (2 * coeff_bound + 1) ** 4 > MAX_RENDER_POINTS:
            raise ValueError(f"moser_ring coeff_bound={coeff_bound} exceeds the point limit")
        return build(
            MoserRingParams(
                denom_power=_int_param(params, "denom_power", 1, min_value=0, max_value=2),
                coeff_bound=coeff_bound,
                visible_radius=_float_param(
                    params, "visible_radius", 2.0, min_value=0.1, max_value=30.0
                ),
                window_kind=window_kind,
            )
        )

    if construction == "moser":
        _reject_unknown(params, {"zeta_order", "coeff_bound"})
        from eud.families.moser import MoserParams, build

        coeff_bound = _int_param(params, "coeff_bound", 2, min_value=1, max_value=4)
        if (2 * coeff_bound + 1) ** 4 > MAX_RENDER_POINTS:
            raise ValueError(f"moser coeff_bound={coeff_bound} exceeds the point limit")
        return build(
            MoserParams(
                zeta_order=_int_param(params, "zeta_order", 6, min_value=3, max_value=30),
                coeff_bound=coeff_bound,
            )
        )

    if construction == "cyclotomic":
        _reject_unknown(
            params,
            {
                "m",
                "coeff_bound",
                "R",
                "window_kind",
                "translation_seed",
                "translation_scale",
            },
        )
        from eud.families.cyclotomic import CyclotomicParams, build

        m = _int_param(params, "m", 12, min_value=3, max_value=60)
        coeff_bound = _int_param(params, "coeff_bound", 4, min_value=1, max_value=8)
        rank = int(sp.totient(m))
        if (2 * coeff_bound + 1) ** rank > MAX_ENUMERATED_COEFFS:
            raise ValueError(
                f"m={m}, coeff_bound={coeff_bound} would enumerate too many "
                "coefficient tuples for interactive use"
            )
        window_kind = _string_param(
            params,
            "window_kind",
            "ball",
            allowed={"ball", "box", "ellipsoid", "all"},
        )
        if window_kind == "all" and (2 * coeff_bound + 1) ** rank > MAX_RENDER_POINTS:
            raise ValueError("window_kind=all would exceed the interactive point limit")
        return build(
            CyclotomicParams(
                m=m,
                coeff_bound=coeff_bound,
                R=_float_param(params, "R", 2.5, min_value=0.1, max_value=20.0),
                window_kind=window_kind,
                translation_seed=_optional_int_param(
                    params,
                    "translation_seed",
                    min_value=0,
                    max_value=1_000_000,
                ),
                translation_scale=_float_param(
                    params,
                    "translation_scale",
                    0.5,
                    min_value=0.0,
                    max_value=10.0,
                ),
            )
        )

    if construction == "erdos_grid":
        _reject_unknown(params, {"K", "m", "mx", "my"})
        from eud.families.erdos_grid import ErdosGridParams, build

        m = _int_param(params, "m", 12, min_value=1, max_value=200)
        mx = _optional_int_param(params, "mx", min_value=1, max_value=300)
        my = _optional_int_param(params, "my", min_value=1, max_value=300)
        width = mx if mx is not None else m
        height = my if my is not None else m
        if width * height > MAX_RENDER_POINTS:
            raise ValueError(f"grid has {width * height} points; max is {MAX_RENDER_POINTS}")
        return build(
            ErdosGridParams(
                K=_int_param(params, "K", 65, min_value=1, max_value=1_000_000),
                m=m,
                mx=mx,
                my=my,
            )
        )

    raise ValueError(f"unknown construction: {construction}")


def _reject_unknown(params: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(params) - allowed)
    if unknown:
        raise ValueError(f"unknown parameter(s): {', '.join(unknown)}")


def _int_param(
    params: dict[str, Any],
    name: str,
    default: int,
    *,
    min_value: int,
    max_value: int,
) -> int:
    value = params.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < min_value or value > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")
    return value


def _optional_int_param(
    params: dict[str, Any],
    name: str,
    *,
    min_value: int,
    max_value: int,
) -> int | None:
    if name not in params or params[name] in (None, ""):
        return None
    value = params[name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < min_value or value > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")
    return value


def _float_param(
    params: dict[str, Any],
    name: str,
    default: float,
    *,
    min_value: float,
    max_value: float,
) -> float:
    value = params.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a number")
    value = float(value)
    if value < min_value or value > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")
    return value


def _string_param(
    params: dict[str, Any],
    name: str,
    default: str,
    *,
    allowed: set[str],
) -> str:
    value = params.get(name, default)
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if value not in allowed:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(allowed))}")
    return value


def main() -> None:
    import uvicorn

    uvicorn.run("eud.web_api:app", host="127.0.0.1", port=8000)

