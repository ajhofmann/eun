"""Beam search moves for Engel-style finite unit-distance graphs.

The search state is a set of integer coefficient tuples in the Engel-Moser
lattice.  We deliberately keep this module coefficient-space-first: floats are
only introduced when converting a final state back into a `Candidate`.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from eud.core.edges import count_edges
from eud.core.pointset import Candidate, LatticePoint
from eud.families.engel_moser import basis, enumerate_unit_vectors

Coeff = tuple[int, int, int, int]
MoveKind = Literal["boundary", "triangle", "parallelogram"]


@dataclass(frozen=True)
class BeamConfig:
    """Hyperparameters for coefficient-space beam search."""

    width: int = 32
    rounds: int = 40
    max_additions_per_state: int = 32
    drop_branches: int = 6
    seed: int = 0
    visit_penalty: float = 0.05
    signature_penalty: float = 0.02
    include_boundary: bool = True
    include_triangles: bool = True
    include_parallelograms: bool = True


@dataclass(frozen=True)
class BeamState:
    """A canonical coefficient set plus search metadata."""

    coeffs: tuple[Coeff, ...]
    edges: int
    score: float
    history: tuple[str, ...] = field(default_factory=tuple)

    @property
    def key(self) -> tuple[Coeff, ...]:
        return self.coeffs


@dataclass(frozen=True)
class BeamResult:
    """Final result and lightweight diagnostics from a beam run."""

    candidate: Candidate
    best_state: BeamState
    rounds_completed: int
    states_seen: int
    best_by_round: list[dict[str, int]]


def _add(a: Coeff, b: Coeff) -> Coeff:
    return tuple(x + y for x, y in zip(a, b, strict=True))  # type: ignore[return-value]


def _sub(a: Coeff, b: Coeff) -> Coeff:
    return tuple(x - y for x, y in zip(a, b, strict=True))  # type: ignore[return-value]


def canonicalize(coeffs: set[Coeff] | tuple[Coeff, ...] | list[Coeff]) -> tuple[Coeff, ...]:
    """Translate a coefficient set to a deterministic origin and sort it.

    This is a cheap translation canonization.  It does not quotient all lattice
    symmetries, but it removes the main source of duplicate states in local
    growth searches.
    """

    if not coeffs:
        return ()
    origin = min(coeffs)
    return tuple(sorted(_sub(c, origin) for c in coeffs))


def edge_count_for_coeffs(
    coeffs: set[Coeff] | tuple[Coeff, ...] | list[Coeff],
    units: list[Coeff] | None = None,
) -> int:
    """Count exact unit edges inside a coefficient set."""

    coeff_set = set(coeffs)
    units = units or enumerate_unit_vectors()
    edges = 0
    seen: set[tuple[Coeff, Coeff]] = set()
    for p in coeff_set:
        for u in units:
            q = _add(p, u)
            if q not in coeff_set:
                continue
            a, b = (p, q) if p < q else (q, p)
            if (a, b) in seen:
                continue
            seen.add((a, b))
            edges += 1
    return edges


def coeffs_to_candidate(
    coeffs: set[Coeff] | tuple[Coeff, ...] | list[Coeff],
    *,
    family: str = "engel_moser",
    params: dict | None = None,
    units: list[Coeff] | None = None,
    notes: dict | None = None,
) -> Candidate:
    """Convert coefficient tuples into a fully indexed `Candidate`."""

    if family == "moser_ring":
        from eud.families.moser_ring import MoserRingParams, candidate_from_coeffs

        raw = params or {}
        ring_params = MoserRingParams(
            denom_power=int(raw.get("denom_power", 1)),
            coeff_bound=int(raw.get("coeff_bound", 1)),
            visible_radius=float(raw.get("visible_radius", 1.0)),
            window_kind=str(raw.get("window_kind", "visible_disk")),
            unit_search_bound=raw.get("unit_search_bound"),
        )
        return candidate_from_coeffs(
            list(canonicalize(coeffs)),
            ring_params,
            unit_vectors=units,
            notes=notes,
        )

    lat = basis()
    units = units or enumerate_unit_vectors()
    ordered = list(canonicalize(coeffs))
    points = [LatticePoint(coeffs=c, xy=lat.project(c)) for c in ordered]
    return Candidate(
        family=family,
        params=params or {},
        points=points,
        edges=count_edges(points, units),
        unit_vectors=units,
        notes=notes or {},
    )


def _internal_degrees(coeffs: set[Coeff], units: list[Coeff]) -> dict[Coeff, int]:
    deg = {c: 0 for c in coeffs}
    for p in coeffs:
        for u in units:
            q = _add(p, u)
            if q in coeffs:
                deg[p] += 1
    return deg


def _neighbor_count(v: Coeff, coeffs: set[Coeff], units: list[Coeff]) -> int:
    return sum(1 for u in units if _add(v, u) in coeffs)


def _triangle_offsets(units: list[Coeff]) -> dict[Coeff, list[Coeff]]:
    """Map an existing edge diff to offsets that complete a unit triangle."""

    unit_set = set(units)
    out: dict[Coeff, list[Coeff]] = {}
    for diff in units:
        offsets = [u for u in units if _sub(u, diff) in unit_set]
        if offsets:
            out[diff] = sorted(set(offsets))
    return out


def boundary_additions(coeffs: set[Coeff], units: list[Coeff]) -> set[Coeff]:
    """Vertices one unit step away from the current state."""

    out: set[Coeff] = set()
    for p in coeffs:
        for u in units:
            q = _add(p, u)
            if q not in coeffs:
                out.add(q)
    return out


def triangle_additions(coeffs: set[Coeff], units: list[Coeff]) -> set[Coeff]:
    """Vertices that complete a unit triangle on an existing unit edge."""

    coeff_set = set(coeffs)
    offsets_by_diff = _triangle_offsets(units)
    out: set[Coeff] = set()
    for p in coeff_set:
        for diff, offsets in offsets_by_diff.items():
            q = _add(p, diff)
            if q not in coeff_set:
                continue
            for offset in offsets:
                r = _add(p, offset)
                if r not in coeff_set:
                    out.add(r)
    return out


def parallelogram_additions(coeffs: set[Coeff], units: list[Coeff]) -> set[Coeff]:
    """Vertices that complete a unit-edge parallelogram corner."""

    coeff_set = set(coeffs)
    unit_set = set(units)
    out: set[Coeff] = set()
    for p in coeff_set:
        incident = [u for u in units if _add(p, u) in coeff_set]
        for i, u in enumerate(incident):
            for v in incident[i + 1 :]:
                if u == v or _sub(u, v) in unit_set or _sub(v, u) in unit_set:
                    # Triangle completions cover adjacent unit offsets; this
                    # branch is for the looser parallelogram closure move.
                    continue
                r = _add(_add(p, u), v)
                if r not in coeff_set:
                    out.add(r)
    return out


def _rank_additions(
    coeffs: set[Coeff],
    units: list[Coeff],
    *,
    config: BeamConfig,
    rng: random.Random,
) -> list[tuple[Coeff, MoveKind, int]]:
    additions: dict[Coeff, MoveKind] = {}
    if config.include_boundary:
        for c in boundary_additions(coeffs, units):
            additions.setdefault(c, "boundary")
    if config.include_triangles:
        for c in triangle_additions(coeffs, units):
            additions[c] = "triangle"
    if config.include_parallelograms:
        for c in parallelogram_additions(coeffs, units):
            additions.setdefault(c, "parallelogram")

    move_bonus = {"triangle": 2, "parallelogram": 1, "boundary": 0}
    ranked = [
        (c, kind, _neighbor_count(c, coeffs, units) + move_bonus[kind])
        for c, kind in additions.items()
    ]
    ranked.sort(key=lambda item: (-item[2], item[1], item[0], rng.random()))
    return ranked[: config.max_additions_per_state]


def _shrink_variants(
    coeffs: set[Coeff],
    *,
    target_k: int,
    units: list[Coeff],
    max_variants: int,
) -> list[tuple[Coeff, ...]]:
    """Drop low-contribution vertices until `target_k` remain."""

    if len(coeffs) <= target_k:
        return [canonicalize(coeffs)]
    current = set(coeffs)
    while len(current) > target_k + 1:
        deg = _internal_degrees(current, units)
        worst = min(current, key=lambda c: (deg[c], c))
        current.remove(worst)

    deg = _internal_degrees(current, units)
    drops = sorted(current, key=lambda c: (deg[c], c))[:max(1, max_variants)]
    return [canonicalize(current - {drop}) for drop in drops]


def _shape_signature(coeffs: tuple[Coeff, ...], units: list[Coeff]) -> tuple[int, tuple[int, ...]]:
    coeff_set = set(coeffs)
    degree_counts = Counter(_internal_degrees(coeff_set, units).values())
    return edge_count_for_coeffs(coeff_set, units), tuple(
        degree_counts.get(i, 0) for i in range(len(units) + 1)
    )


def _state(
    coeffs: tuple[Coeff, ...],
    *,
    units: list[Coeff],
    history: tuple[str, ...],
    visits: Counter[tuple[Coeff, ...]],
    signatures: Counter[tuple[int, tuple[int, ...]]],
    config: BeamConfig,
) -> BeamState:
    edges = edge_count_for_coeffs(coeffs, units)
    sig = _shape_signature(coeffs, units)
    score = edges - config.visit_penalty * visits[coeffs] - config.signature_penalty * signatures[sig]
    return BeamState(coeffs=coeffs, edges=edges, score=score, history=history)


def beam_search(
    initial: Candidate,
    target_k: int,
    *,
    config: BeamConfig | None = None,
) -> BeamResult:
    """Run Engel-style beam search around an initial candidate."""

    config = config or BeamConfig()
    units = [tuple(u) for u in (initial.unit_vectors or enumerate_unit_vectors())]
    rng = random.Random(config.seed + 1009 * target_k + initial.n)

    initial_coeffs = {tuple(p.coeffs) for p in initial.points}
    start_keys = _shrink_variants(
        initial_coeffs,
        target_k=target_k,
        units=units,
        max_variants=max(1, config.drop_branches),
    )

    visits: Counter[tuple[Coeff, ...]] = Counter()
    signatures: Counter[tuple[int, tuple[int, ...]]] = Counter()
    beam: list[BeamState] = []
    for key in start_keys:
        visits[key] += 1
        signatures[_shape_signature(key, units)] += 1
        beam.append(
            _state(
                key,
                units=units,
                history=("seed",),
                visits=visits,
                signatures=signatures,
                config=config,
            )
        )
    beam.sort(key=lambda s: (-s.edges, -s.score, s.key))
    beam = beam[: config.width]
    best = beam[0]
    best_by_round: list[dict[str, int]] = []

    rounds_completed = 0
    for round_idx in range(config.rounds):
        children: dict[tuple[Coeff, ...], BeamState] = {}
        for state in beam:
            coeff_set = set(state.coeffs)
            for addition, kind, _ in _rank_additions(coeff_set, units, config=config, rng=rng):
                expanded = set(coeff_set)
                expanded.add(addition)
                for key in _shrink_variants(
                    expanded,
                    target_k=target_k,
                    units=units,
                    max_variants=config.drop_branches,
                ):
                    visits[key] += 1
                    signatures[_shape_signature(key, units)] += 1
                    child = _state(
                        key,
                        units=units,
                        history=state.history + (kind,),
                        visits=visits,
                        signatures=signatures,
                        config=config,
                    )
                    old = children.get(key)
                    if old is None or (child.edges, child.score) > (old.edges, old.score):
                        children[key] = child

        if not children:
            break
        # Retain beam breadth by score, but never discard the densest child states.
        # Visit penalties can rank a 252-edge state below a 249-edge state and caused
        # the n=64 Engel reproduction miss when only `beam[:width]` updated `best`.
        child_list = list(children.values())
        round_best = max(child_list, key=lambda s: (s.edges, s.score, s.key))
        if (round_best.edges, round_best.score) > (best.edges, best.score):
            best = round_best
        ranked = sorted(child_list, key=lambda s: (-s.score, -s.edges, s.key))
        beam = ranked[: config.width]
        if round_best.key not in {s.key for s in beam}:
            beam[-1] = round_best
            beam.sort(key=lambda s: (-s.score, -s.edges, s.key))
        rounds_completed = round_idx + 1
        best_by_round.append(
            {
                "round": rounds_completed,
                "best_e": best.edges,
                "beam_best_e": round_best.edges,
                "states_seen": len(visits),
            }
        )

    candidate = coeffs_to_candidate(
        best.coeffs,
        family=initial.family,
        params={
            **initial.params,
            "beam_target_k": target_k,
            "beam_width": config.width,
            "beam_rounds": config.rounds,
        },
        units=units,
        notes={
            **initial.notes,
            "beam_search": True,
            "beam_history": list(best.history),
            "rounds_completed": rounds_completed,
        },
    )
    return BeamResult(
        candidate=candidate,
        best_state=best,
        rounds_completed=rounds_completed,
        states_seen=len(visits),
        best_by_round=best_by_round,
    )
