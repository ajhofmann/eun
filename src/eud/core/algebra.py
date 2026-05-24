"""Exact algebraic squared-distance checks.

Two backends:

1. `sympy` (default, always available): symbolic squared distance over
   a per-family rewrite rule. Slow but pure-Python.
2. `cypari2` (optional, for general number fields): faster norm-based
   checks via PARI. Wired in `families/pari_fields.py`.

The convention is: every point carries integer coefficients in a fixed
basis, and the family supplies an exact formula for the squared distance
of a coefficient difference. The verifier evaluates that formula
symbolically and compares to 1.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import sympy as sp

ExactSquaredDistance = Callable[[tuple[int, ...]], sp.Expr]


def make_squared_distance(
    visible_basis: Sequence[Any],
    *,
    simplify: bool = False,
) -> ExactSquaredDistance:
    """Build an exact squared-distance function from a symbolic basis.

    `visible_basis[i]` should be a sympy expression giving the i-th basis
    vector under the visible embedding (a complex sympy number / expression).

    Returns a callable that maps an integer coefficient difference vector
    to the symbolic squared distance |sum c_i b_i|^2.
    """
    basis = list(visible_basis)
    rank = len(basis)

    def squared_distance(diff: tuple[int, ...]) -> sp.Expr:
        if len(diff) != rank:
            raise ValueError(f"diff dim {len(diff)} != rank {rank}")
        z = sp.S(0)
        for c, b in zip(diff, basis, strict=True):
            z = z + sp.Integer(c) * b
        d2 = sp.expand(sp.conjugate(z) * z)
        return sp.simplify(d2) if simplify else d2

    return squared_distance


def is_exact_unit(diff: tuple[int, ...], sd: ExactSquaredDistance) -> bool:
    """Return True iff sd(diff) simplifies exactly to 1.

    `sp.simplify` alone does not always reduce `exp(I*pi*q) + exp(-I*pi*q)`
    to its rational/algebraic real form. We rewrite trig/exp first, then
    simplify. Real number-field constants (sqrt(p), etc.) are then handled
    correctly.
    """
    if all(c == 0 for c in diff):
        return False
    raw = sd(diff)
    val = sp.expand_complex(raw)
    val = sp.simplify(val.rewrite(sp.cos))
    val = sp.nsimplify(val, rational=False)
    return sp.simplify(val - 1) == 0


def exact_squared_value(diff: tuple[int, ...], sd: ExactSquaredDistance) -> sp.Expr:
    """Return the fully simplified exact squared distance for a diff vector."""
    raw = sd(diff)
    val = sp.expand_complex(raw)
    val = sp.simplify(val.rewrite(sp.cos))
    return sp.nsimplify(val, rational=False)


def verify_unit_vectors(
    unit_vectors: Sequence[tuple[int, ...]],
    sd: ExactSquaredDistance,
) -> tuple[list[tuple[int, ...]], list[tuple[int, ...]]]:
    """Split unit vectors into (verified, rejected) by exact algebra."""
    verified: list[tuple[int, ...]] = []
    rejected: list[tuple[int, ...]] = []
    for u in unit_vectors:
        if is_exact_unit(u, sd):
            verified.append(u)
        else:
            rejected.append(u)
    return verified, rejected
