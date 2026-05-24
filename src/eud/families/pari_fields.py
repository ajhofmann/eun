"""Number-field operations via cypari2.

Wraps PARI/GP for:
- defining number fields by polynomial,
- integral bases,
- torsion units (roots of unity),
- high-precision archimedean embeddings,
- norm-one element verification.

We use PARI for cross-checks and certification, complementing the
existing sympy-based exact `is_exact_unit` for cyclotomic/biquadratic
families. PARI scales better for larger fields (rank 6, 8) where
sympy `simplify` gets slow.

Usage:
    nf = NumberField.cyclotomic(5)
    nf.is_unit_visible_embedding([1, -1, 0, 0])  -> True (1 - zeta_5)
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

try:
    import cypari2

    _PARI_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PARI_AVAILABLE = False


def pari_available() -> bool:
    return _PARI_AVAILABLE


@lru_cache(maxsize=1)
def _pari():
    if not _PARI_AVAILABLE:
        raise RuntimeError("cypari2 not installed; install with `uv add cypari2`")
    return cypari2.Pari()


@dataclass
class NumberField:
    """Wrapper around a PARI nf structure.

    Elements are represented by integer coefficients in the *power basis*
    (1, t, t^2, ..., t^{d-1}) where t is the chosen primitive element
    (e.g. zeta_m for cyclotomic fields). PARI internally uses its own
    integral basis (`nf[6]`); we convert via `nfalgtobasis` /
    `Pol(...) % polynomial`.
    """

    defining_poly: str
    nf: Any
    name: str
    rank: int

    @classmethod
    def from_polynomial(cls, poly: str, *, name: str | None = None) -> NumberField:
        pari = _pari()
        nf = pari.nfinit(poly)
        rank = int(pari.poldegree(nf[0]))
        return cls(defining_poly=poly, nf=nf, name=name or poly, rank=rank)

    @classmethod
    def cyclotomic(cls, m: int) -> NumberField:
        """Q(zeta_m) using the m-th cyclotomic polynomial."""
        pari = _pari()
        poly = pari.polcyclo(m)
        nf = pari.nfinit(poly)
        rank = int(pari.poldegree(nf[0]))
        return cls(defining_poly=str(poly), nf=nf, name=f"Q(zeta_{m})", rank=rank)

    def degree(self) -> int:
        return self.rank

    def integral_basis(self) -> list[str]:
        """String representation of PARI's integral basis (its own choice)."""
        return [str(b) for b in self.nf[6]]

    def roots_of_unity(self) -> tuple[int, list[int]]:
        """Return (order, generator coefficients in PARI integral basis)."""
        pari = _pari()
        ord_, gen = pari.nfrootsof1(self.nf)
        return int(ord_), [int(c) for c in gen]

    def _power_basis_to_alg(self, coeffs: list[int]) -> Any:
        """Build a PARI Mod(...) element from power-basis coefficients."""
        pari = _pari()
        if len(coeffs) > self.rank:
            raise ValueError(f"too many coeffs ({len(coeffs)}) for rank {self.rank}")
        padded = list(coeffs) + [0] * (self.rank - len(coeffs))
        # Build polynomial sum_k coeff[k] * x^k, then reduce mod defining poly.
        poly_str = "+".join(f"({c})*x^{k}" for k, c in enumerate(padded) if c != 0)
        if not poly_str:
            poly_str = "0"
        elem = pari(f"Mod({poly_str}, {self.defining_poly})")
        return elem

    def squared_norm_visible_high_precision(
        self,
        coeffs: list[int],
        *,
        prec_bits: int = 256,
    ) -> complex:
        """High-precision |sigma_1(x)|^2 in the visible embedding.

        `coeffs` are integer coordinates in the *power basis* (1, t, t^2, ...).
        Returns a real-valued Python complex; imaginary part should be ~0.
        """
        pari = _pari()
        pari.set_real_precision_bits(prec_bits)
        try:
            el = self._power_basis_to_alg(coeffs)
            embeddings = pari.nfeltembed(self.nf, el)
            sigma_1 = embeddings[0]
            return abs(complex(sigma_1)) ** 2
        finally:
            pari.set_real_precision_bits(38)

    def is_unit_visible_embedding(
        self,
        coeffs: list[int],
        *,
        prec_bits: int = 256,
        tol: float = 1e-10,
    ) -> bool:
        """Cross-check that |sigma_1(x)|^2 == 1 numerically.

        coeffs are in the power basis (1, t, t^2, ...). Note that the
        Python `complex` cast at the end truncates to double precision;
        a typical "true" unit has |d2 - 1| ~ 1e-15. The default tolerance
        is therefore 1e-10 - the sympy check is what actually proves
        equality. PARI is here as cross-validation, not as the canonical
        oracle.
        """
        d2 = self.squared_norm_visible_high_precision(coeffs, prec_bits=prec_bits)
        return abs(d2 - 1.0) < tol

    def to_dict(self) -> dict:
        """JSON-friendly summary for inclusion in certificates."""
        try:
            ord_, _ = self.roots_of_unity()
        except Exception:
            ord_ = None
        return {
            "name": self.name,
            "defining_poly": self.defining_poly,
            "degree": self.degree(),
            "torsion_unit_order": ord_,
            "integral_basis_size": len(self.integral_basis()),
            "basis_convention": "power basis (1, t, t^2, ...) for verification inputs",
        }
