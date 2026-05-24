"""Generic lattice utilities shared by family generators.

A lattice basis is represented as a list of complex numbers (one per
basis element), giving the visible-embedding column. Hidden-space
coordinates (other Galois conjugates) live alongside as `aux_basis`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LatticeBasis:
    """A finite-rank Z-lattice with one or more complex embeddings.

    Attributes:
        visible: complex numbers giving the i-th basis vector under the
            visible (plane) embedding.
        hidden: list of complex numbers per other embedding. Each entry
            has the same length as `visible`. Empty for purely real
            constructions like Z[i] or Z[zeta_3].
    """

    visible: tuple[complex, ...]
    hidden: tuple[tuple[complex, ...], ...] = ()
    name: str = "lattice"

    @property
    def rank(self) -> int:
        return len(self.visible)

    def project(self, coeffs: tuple[int, ...]) -> tuple[float, float]:
        z = sum(c * v for c, v in zip(coeffs, self.visible, strict=True))
        return (float(z.real), float(z.imag))

    def hidden_coords(self, coeffs: tuple[int, ...]) -> tuple[float, ...]:
        out: list[float] = []
        for h in self.hidden:
            z = sum(c * v for c, v in zip(coeffs, h, strict=True))
            out.append(float(z.real))
            out.append(float(z.imag))
        return tuple(out)


def squared_distance_visible(
    p_coeffs: tuple[int, ...],
    q_coeffs: tuple[int, ...],
    basis: LatticeBasis,
) -> float:
    """Approximate squared visible-plane distance between two lattice points."""
    diff = tuple(b - a for a, b in zip(p_coeffs, q_coeffs, strict=True))
    z = sum(c * v for c, v in zip(diff, basis.visible, strict=True))
    return float(z.real * z.real + z.imag * z.imag)


def gram_matrix(basis: LatticeBasis) -> np.ndarray:
    """Return the Gram matrix of the visible embedding (real basis vectors)."""
    rank = basis.rank
    G = np.zeros((rank, rank), dtype=float)
    vecs = [(v.real, v.imag) for v in basis.visible]
    for i in range(rank):
        for j in range(rank):
            G[i, j] = vecs[i][0] * vecs[j][0] + vecs[i][1] * vecs[j][1]
    return G
