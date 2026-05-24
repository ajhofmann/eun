"""Generic cut-and-project pipeline.

For a number field with rank r over Q, the Minkowski embedding sends
each integer-coefficient lattice element into

    visible (C, ~R^2)  x  hidden_1 (C)  x  hidden_2 (C)  x  ...

We restrict points to those whose hidden-space coordinates land in a
specified `Window`, then project onto the visible plane to get a finite
unit-distance graph candidate. This is the engine used by the
`cyclotomic` and `biquadratic` families.
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from eud.core.lattice import LatticeBasis
from eud.core.pointset import LatticePoint


class Window(Protocol):
    """A subset of the hidden space (R^d) that selects which lattice points to keep."""

    def contains(self, coords: Sequence[float]) -> bool: ...


@dataclass(frozen=True)
class BoxWindow:
    """Axis-aligned box window in hidden space."""

    half_widths: tuple[float, ...]
    center: tuple[float, ...] = ()

    def contains(self, coords: Sequence[float]) -> bool:
        c = self.center if self.center else (0.0,) * len(self.half_widths)
        for x, mu, hw in zip(coords, c, self.half_widths, strict=True):
            if abs(x - mu) > hw:
                return False
        return True


@dataclass(frozen=True)
class BallWindow:
    """Euclidean ball in hidden space."""

    radius: float
    center: tuple[float, ...] = ()

    def contains(self, coords: Sequence[float]) -> bool:
        c = self.center if self.center else (0.0,) * len(coords)
        s = sum((x - mu) ** 2 for x, mu in zip(coords, c, strict=True))
        return s <= self.radius * self.radius


@dataclass(frozen=True)
class EllipsoidWindow:
    """Axis-aligned ellipsoid (sum of (x_i / a_i)^2 <= 1)."""

    axes: tuple[float, ...]
    center: tuple[float, ...] = ()

    def contains(self, coords: Sequence[float]) -> bool:
        c = self.center if self.center else (0.0,) * len(self.axes)
        s = sum(
            ((x - mu) / a) ** 2
            for x, mu, a in zip(coords, c, self.axes, strict=True)
        )
        return s <= 1.0


@dataclass
class ZonotopeWindow:
    """Convex hull of a centered zonotope spanned by `generators`.

    Membership: point is in zonotope iff it can be written as sum t_i * g_i
    with |t_i| <= 1. We test by solving a small LP via numpy: equivalent
    to checking the L_inf norm of the coefficient vector with respect to
    the (pseudo)inverse map.
    """

    generators: tuple[tuple[float, ...], ...]
    center: tuple[float, ...] = ()

    def contains(self, coords: Sequence[float]) -> bool:
        if not self.generators:
            return all(x == c for x, c in zip(coords, self.center or coords, strict=True))
        G = np.array(self.generators, dtype=float).T
        c = np.array(self.center if self.center else [0.0] * G.shape[0])
        x = np.array(coords) - c
        coeff, *_ = np.linalg.lstsq(G, x, rcond=None)
        return bool(np.max(np.abs(coeff)) <= 1.0 + 1e-9)


def random_translation(
    dim: int,
    *,
    seed: int = 0,
    scale: float = 0.5,
) -> tuple[float, ...]:
    """Random hidden-space center for cut-and-project."""
    rng = random.Random(seed)
    return tuple(rng.uniform(-scale, scale) for _ in range(dim))


def cut_project_points(
    basis: LatticeBasis,
    *,
    coeff_bound: int,
    window: Window,
) -> list[LatticePoint]:
    """Enumerate lattice points whose hidden-space image is in `window`.

    Coefficients range over [-coeff_bound, coeff_bound]^rank.
    """
    rank = basis.rank
    pts: list[LatticePoint] = []
    for coeffs in itertools.product(range(-coeff_bound, coeff_bound + 1), repeat=rank):
        hidden = basis.hidden_coords(coeffs)
        if not window.contains(hidden):
            continue
        xy = basis.project(coeffs)
        pts.append(LatticePoint(coeffs=coeffs, xy=xy, aux=hidden))
    return pts
