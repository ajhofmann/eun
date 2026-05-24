"""Lattice points and candidate unit-distance graphs.

A `LatticePoint` carries integer coefficients in a fixed lattice basis.
The plane projection `xy` is for plotting only; algebraic checks happen
via the integer coefficients and a per-family unit-vector list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LatticePoint:
    """A lattice point with exact integer coordinates and a plane projection.

    Attributes:
        coeffs: Integer coordinates in the chosen lattice basis. Used for
            exact edge tests via the per-family unit-vector list.
        xy: The plane projection of this point (visible embedding). Floats,
            for visualization only - never trust these for record claims.
        aux: Optional hidden-space coordinates (other Galois conjugates,
            window coordinates, etc.).
    """

    coeffs: tuple[int, ...]
    xy: tuple[float, float]
    aux: tuple[float, ...] = ()


@dataclass
class Candidate:
    """A unit-distance graph candidate with provenance and edges."""

    family: str
    params: dict[str, Any]
    points: list[LatticePoint]
    edges: list[tuple[int, int]]
    unit_vectors: list[tuple[int, ...]] = field(default_factory=list)
    certificate: dict[str, Any] | None = None
    notes: dict[str, Any] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.points)

    @property
    def e(self) -> int:
        return len(self.edges)

    @property
    def density(self) -> float:
        return self.e / self.n if self.n else 0.0

    def induced_subgraph(self, kept_indices: list[int]) -> Candidate:
        """Return the subgraph induced by `kept_indices`, re-indexed from 0."""
        kept = sorted(set(kept_indices))
        remap = {old: new for new, old in enumerate(kept)}
        new_points = [self.points[i] for i in kept]
        new_edges = [
            (remap[i], remap[j])
            for (i, j) in self.edges
            if i in remap and j in remap
        ]
        return Candidate(
            family=self.family,
            params={**self.params, "induced_from_n": self.n},
            points=new_points,
            edges=new_edges,
            unit_vectors=list(self.unit_vectors),
            certificate=None,
            notes={**self.notes, "induced": True},
        )
