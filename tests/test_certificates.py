"""Certificate generation and exact verification."""

from __future__ import annotations

import pytest

from eud.core.certificates import build_certificate
from eud.families.cyclotomic import (
    CyclotomicParams,
)
from eud.families.cyclotomic import (
    build as build_cyc,
)
from eud.families.cyclotomic import (
    squared_distance_symbolic as sd_cyc,
)
from eud.families.moser import (
    MoserParams,
)
from eud.families.moser import (
    build as build_moser,
)
from eud.families.moser import (
    squared_distance_symbolic as sd_moser,
)


def test_cert_moser_all_edges_pass_sympy() -> None:
    c = build_moser(MoserParams(zeta_order=6, coeff_bound=2))
    sd = sd_moser(MoserParams(zeta_order=6))
    cert = build_certificate(
        c,
        field_description="Q(i, zeta_6)",
        basis_description=["1", "i", "zeta_6", "i*zeta_6"],
        visible_embedding="zeta -> exp(i*pi/3)",
        sd=sd,
    )
    assert cert["checks"]["all_points_distinct"]
    assert cert["checks"]["edges_checked_sympy"] == c.e
    assert cert["checks"]["edges_failing_sympy"] == []
    assert cert["checks"]["all_sympy_unit"]


def test_cert_zeta5_all_edges_pass_sympy() -> None:
    c = build_cyc(CyclotomicParams(m=5, coeff_bound=3, R=1.5))
    sd = sd_cyc(CyclotomicParams(m=5))
    cert = build_certificate(
        c,
        field_description="Q(zeta_5)",
        basis_description=["1", "z", "z^2", "z^3"],
        visible_embedding="z -> exp(2*pi*i/5)",
        sd=sd,
    )
    assert cert["checks"]["edges_checked_sympy"] == c.e
    assert cert["checks"]["all_sympy_unit"]


def test_cert_detects_bogus_edge() -> None:
    """If we inject a non-unit edge, the cert must catch it."""
    c = build_moser(MoserParams(zeta_order=6, coeff_bound=2))
    bogus = c
    bogus.edges = list(c.edges) + [(0, c.n - 1)]  # very likely not unit
    sd = sd_moser(MoserParams(zeta_order=6))
    cert = build_certificate(
        bogus,
        field_description="Q(i, zeta_6)",
        basis_description=["1", "i", "zeta_6", "i*zeta_6"],
        visible_embedding="zeta -> exp(i*pi/3)",
        sd=sd,
    )
    assert cert["checks"]["edges_failing_sympy"], "expected a failing edge"
    assert not cert["checks"]["all_sympy_unit"]


def test_cert_sample_subset() -> None:
    c = build_moser(MoserParams(zeta_order=6, coeff_bound=2))
    sd = sd_moser(MoserParams(zeta_order=6))
    cert = build_certificate(
        c,
        field_description="Q(i, zeta_6)",
        basis_description=["1", "i", "zeta_6", "i*zeta_6"],
        visible_embedding="zeta -> exp(i*pi/3)",
        sd=sd,
        sample_edges=10,
    )
    assert cert["checks"]["edges_checked_sympy"] <= 10 + 1  # off-by-one tolerance
    assert cert["checks"]["all_sympy_unit"]


@pytest.mark.skipif(
    not __import__("eud.families.pari_fields", fromlist=["pari_available"]).pari_available(),
    reason="cypari2 not installed",
)
def test_pari_cross_check_zeta5() -> None:
    from eud.families.pari_fields import NumberField

    c = build_cyc(CyclotomicParams(m=5, coeff_bound=2, R=1.5))
    sd = sd_cyc(CyclotomicParams(m=5))
    nf = NumberField.cyclotomic(5)
    cert = build_certificate(
        c,
        field_description="Q(zeta_5)",
        basis_description=["1", "z", "z^2", "z^3"],
        visible_embedding="z -> exp(2*pi*i/5)",
        sd=sd,
        pari_field=nf,
    )
    assert cert["checks"]["all_sympy_unit"]
    assert cert["checks"]["all_pari_unit"]
    assert cert["pari_field"]["degree"] == 4


@pytest.mark.skipif(
    not __import__("eud.families.pari_fields", fromlist=["pari_available"]).pari_available(),
    reason="cypari2 not installed",
)
def test_pari_field_basics() -> None:
    from eud.families.pari_fields import NumberField

    nf = NumberField.cyclotomic(5)
    assert nf.degree() == 4
    ord_, _ = nf.roots_of_unity()
    assert ord_ in (5, 10)  # Z[zeta_5] roots of unity = {zeta_10}
    # x = 1 (first basis element) has |sigma_1(1)|^2 = 1
    assert nf.is_unit_visible_embedding([1, 0, 0, 0])
    # x = 2 has squared norm 4
    assert not nf.is_unit_visible_embedding([2, 0, 0, 0])
