"""Typer-based CLI entry point.

Subcommands are implemented across the package and registered here.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="eud",
    add_completion=False,
    no_args_is_help=True,
    help="Erdős unit-distance search toolchain.",
)

console = Console()


@app.command()
def info() -> None:
    """Show package and environment info."""
    from eud import __version__

    console.print(f"[bold]eud[/bold] v{__version__}")
    console.print("Subcommands: info, version, generate, verify, prune, compare, search, leaderboard")


@app.command()
def version() -> None:
    """Print just the package version."""
    from eud import __version__

    typer.echo(__version__)


@app.command()
def generate(
    family: str = typer.Option(
        ..., "--family", help="moser | engel_moser | moser_ring | zeta5 | erdos_grid | biquadratic"
    ),
    out: Path = typer.Option(..., "--out", help="output JSON path"),
    coeff_bound: int = typer.Option(2, "--coeff-bound", help="coefficient half-width"),
    denom_power: int = typer.Option(1, "--denom-power", help="for moser_ring; denominator is 3^k"),
    zeta_order: int = typer.Option(6, "--zeta-order", help="for moser/cyclotomic; m in zeta_m"),
    R: float = typer.Option(2.5, "--R", help="window radius (cyclotomic)"),
    K: int = typer.Option(5, "--K", help="K parameter (erdos_grid)"),
    primes: str = typer.Option("3,5,11", "--primes", help="comma-separated primes (biquadratic)"),
    draw: Path | None = typer.Option(None, "--draw", help="optional PNG output for the graph"),
) -> None:
    """Generate a candidate of the given family and write it to `out`."""
    from eud.core.io import write_candidate
    from eud.viz.draw import draw_candidate

    if family == "moser":
        from eud.families.moser import MoserParams, build

        candidate = build(MoserParams(zeta_order=zeta_order, coeff_bound=coeff_bound))
    elif family == "engel_moser":
        from eud.families.engel_moser import EngelMoserParams, build

        candidate = build(EngelMoserParams(coeff_bound=coeff_bound, visible_radius=R))
    elif family == "moser_ring":
        from eud.families.moser_ring import MoserRingParams, build

        candidate = build(
            MoserRingParams(coeff_bound=coeff_bound, denom_power=denom_power, visible_radius=R)
        )
    elif family == "zeta5":
        from eud.families.cyclotomic import CyclotomicParams
        from eud.families.cyclotomic import build as build_cyc

        candidate = build_cyc(CyclotomicParams(m=5, coeff_bound=coeff_bound, R=R))
    elif family == "cyclotomic":
        from eud.families.cyclotomic import CyclotomicParams
        from eud.families.cyclotomic import build as build_cyc

        candidate = build_cyc(CyclotomicParams(m=zeta_order, coeff_bound=coeff_bound, R=R))
    elif family == "erdos_grid":
        from eud.families.erdos_grid import ErdosGridParams, build

        candidate = build(ErdosGridParams(K=K))
    elif family == "biquadratic":
        from eud.families.biquadratic import BiquadraticParams
        from eud.families.biquadratic import build as build_bq

        ps = tuple(int(x) for x in primes.split(",") if x.strip())
        candidate = build_bq(BiquadraticParams(primes=ps, coeff_bound=coeff_bound))
    else:
        raise typer.BadParameter(f"unknown family: {family}")

    path = write_candidate(candidate, out)
    console.print(
        f"[green]wrote[/green] {path}  "
        f"family={candidate.family} n={candidate.n} e={candidate.e} "
        f"e/n={candidate.density:.3f}"
    )
    if draw is not None:
        draw_candidate(candidate, draw)
        console.print(f"[green]drew[/green]  {draw}")


@app.command()
def verify(
    candidate_path: Path = typer.Argument(..., help="candidate JSON to verify"),
    out: Path | None = typer.Option(None, "--out", help="optional certificate path"),
    use_pari: bool = typer.Option(False, "--pari", help="cross-check with cypari2"),
    sample: int | None = typer.Option(None, "--sample", help="only check N evenly-spaced edges"),
) -> None:
    """Build a JSON certificate for a candidate and report check results."""
    from eud.core.certificates import build_certificate
    from eud.core.io import read_candidate

    c = read_candidate(candidate_path)

    # Pick the right symbolic backend for the family.
    sd = None
    field_desc = "unspecified"
    basis_desc: list[str] = []
    visible = "unspecified"
    pari_field = None

    if c.family == "moser":
        from eud.families.moser import MoserParams, squared_distance_symbolic

        m = int(c.params.get("zeta_order", 6))
        sd = squared_distance_symbolic(MoserParams(zeta_order=m))
        field_desc = f"Q(i, zeta_{m}) (Moser)"
        basis_desc = ["1", "i", f"zeta_{m}", f"i*zeta_{m}"]
        visible = f"zeta -> exp(2*pi*i/{m})"
    elif c.family == "cyclotomic":
        from eud.families.cyclotomic import CyclotomicParams, squared_distance_symbolic

        m = int(c.params.get("m", 5))
        sd = squared_distance_symbolic(CyclotomicParams(m=m))
        field_desc = f"Q(zeta_{m})"
        basis_desc = [f"zeta_{m}^{k}" for k in range(m - 1)]  # phi(m) <= m-1 entries
        visible = f"zeta -> exp(2*pi*i/{m})"
        if use_pari:
            from eud.families.pari_fields import NumberField, pari_available

            if pari_available():
                pari_field = NumberField.cyclotomic(m)
            else:
                console.print("[yellow]cypari2 not available; skipping PARI cross-check[/yellow]")
    elif c.family == "biquadratic":
        from eud.families.biquadratic import BiquadraticParams, squared_distance_symbolic

        primes = tuple(int(p) for p in c.params.get("primes", [3, 5, 11]))
        sd = squared_distance_symbolic(BiquadraticParams(primes=primes))
        field_desc = f"Q(i, sqrt({', sqrt('.join(map(str, primes))}))"
        basis_desc = ["product of i^a * sqrt(p)^b basis"]
        visible = "i -> i ; sqrt(p_k) -> +sqrt(p_k)"
    elif c.family == "engel_moser":
        from eud.families.engel_moser import squared_distance_symbolic

        sd = squared_distance_symbolic()
        field_desc = "Q(sqrt(3), sqrt(11), i) Engel-Moser lattice"
        basis_desc = ["1", "omega_1", "omega_3", "omega_1*omega_3"]
        visible = "omega_1 -> exp(i*pi/3); omega_3 -> 5/6 + i*sqrt(11)/6"
    elif c.family == "moser_ring":
        from eud.families.moser_ring import MoserRingParams, squared_distance_symbolic

        params = MoserRingParams(
            denom_power=int(c.params.get("denom_power", 1)),
            coeff_bound=int(c.params.get("coeff_bound", 1)),
            visible_radius=float(c.params.get("visible_radius", 1.0)),
            window_kind=str(c.params.get("window_kind", "visible_disk")),
            unit_search_bound=c.params.get("unit_search_bound"),
        )
        sd = squared_distance_symbolic(params)
        field_desc = f"Moser ring common denominator 3^{params.denom_power}"
        basis_desc = ["1/3^k", "omega_1/3^k", "omega_3/3^k", "omega_1*omega_3/3^k"]
        visible = "omega_1 -> exp(i*pi/3); omega_3 -> 5/6 + i*sqrt(11)/6"
    elif c.family == "erdos_grid":
        field_desc = f"Z[i] grid; squared distance = K = {c.params.get('K')}"
        basis_desc = ["x", "y (in scaled coords)"]
        visible = "(x, y) -> (x/sqrt(K), y/sqrt(K))"
    else:
        console.print(f"[yellow]no symbolic verifier for family {c.family}; emitting structural cert only[/yellow]")

    cert = build_certificate(
        c,
        field_description=field_desc,
        basis_description=basis_desc,
        visible_embedding=visible,
        sd=sd,
        sample_edges=sample,
        pari_field=pari_field,
    )
    checks = cert["checks"]
    console.print(
        f"family={c.family} n={c.n} e={c.e} distinct={checks['all_points_distinct']}"
    )
    if "all_sympy_unit" in checks:
        console.print(
            f"sympy: checked {checks['edges_checked_sympy']} / {c.e} edges; "
            f"all unit = [{'green' if checks['all_sympy_unit'] else 'red'}]{checks['all_sympy_unit']}[/]"
        )
    if "all_pari_unit" in checks:
        console.print(
            f"pari:  checked {checks['edges_checked_pari']} / {c.e} edges; "
            f"all unit = [{'green' if checks['all_pari_unit'] else 'red'}]{checks['all_pari_unit']}[/]"
        )

    if out is not None:
        from eud.core.io import write_jsonl

        write_jsonl([cert], out)
        console.print(f"[green]wrote certificate[/green] {out}")


@app.command()
def prune(
    candidate_path: Path = typer.Argument(..., help="candidate JSON to prune"),
    ks: str = typer.Option(..., "--k", help="comma-separated list of target k values"),
    method: str = typer.Option("greedy", "--method", help="greedy | core | local-swap | cp-sat"),
    out: Path = typer.Option(..., "--out", help="output JSONL with per-k rows"),
    time_limit: float = typer.Option(60.0, "--time-limit", help="seconds (cp-sat only)"),
    seed: int = typer.Option(0, "--seed"),
    iters: int = typer.Option(5000, "--iters", help="local-swap max iterations"),
    restarts: int = typer.Option(1, "--restarts", help="local-swap restarts"),
) -> None:
    """Prune a candidate down to dense induced subgraphs of size k."""
    from eud.core.io import read_candidate, write_jsonl
    from eud.search.local_search import SAConfig, local_swap
    from eud.search.prune import per_k_frontier

    c = read_candidate(candidate_path)
    k_list = sorted({int(x) for x in ks.split(",") if x.strip()})

    if method in ("greedy", "core"):
        rows = per_k_frontier(c, k_list, method=method)
    elif method == "local-swap":
        rows = []
        for k in k_list:
            sub = local_swap(
                c, k, config=SAConfig(max_iters=iters, seed=seed, restarts=restarts)
            )
            rows.append(
                {
                    "family": c.family,
                    "params": c.params,
                    "method": "local-swap",
                    "n": sub.n,
                    "e": sub.e,
                    "density": sub.density,
                    "induced_from_n": c.n,
                }
            )
    elif method == "cp-sat":
        from eud.search.ilp import CPSATConfig, cp_sat_densest_k

        rows = []
        for k in k_list:
            sub, info = cp_sat_densest_k(
                c, k, config=CPSATConfig(time_limit_s=time_limit, seed=seed)
            )
            rows.append(
                {
                    "family": c.family,
                    "params": c.params,
                    "method": "cp-sat",
                    "n": sub.n,
                    "e": sub.e,
                    "density": sub.density,
                    "induced_from_n": c.n,
                    "solver": info,
                }
            )
    else:
        raise typer.BadParameter(f"unknown method: {method}")

    write_jsonl(rows, out)
    console.print(f"[green]wrote[/green] {out}  rows={len(rows)} method={method}")
    for r in rows:
        console.print(f"  k={r['n']:>5}  e={r['e']:>6}  e/n={r['density']:.3f}")


@app.command()
def baseline(
    out: Path = typer.Option(..., "--out", help="output JSONL path"),
    n_max: int = typer.Option(1000, "--n-max"),
    K_max: int = typer.Option(10_000_000, "--K-max"),
    prime_limit: int = typer.Option(200, "--prime-limit"),
    no_triangular: bool = typer.Option(False, "--no-triangular"),
    no_moser_hex: bool = typer.Option(False, "--no-moser-hex"),
    no_rect_grid: bool = typer.Option(False, "--no-rect-grid"),
    no_engel_2025: bool = typer.Option(False, "--no-engel-2025"),
) -> None:
    """Build the published/reproducible best finite-construction frontier.

    By default this includes Engel et al. 2025's published beam-search
    table through n=100. Use --no-engel-2025 to rebuild the older
    reproducible-only frontier.
    """
    from eud.benchmarks.compare import build_baseline_frontier
    from eud.core.io import write_jsonl

    rows = build_baseline_frontier(
        n_max=n_max,
        K_max=K_max,
        prime_limit=prime_limit,
        include_triangular=not no_triangular,
        include_moser_hex=not no_moser_hex,
        include_rect_grid=not no_rect_grid,
        include_engel_2025=not no_engel_2025,
    )
    p = write_jsonl(rows, out)
    console.print(f"[green]wrote[/green] {p}  rows={len(rows)} n_max={n_max}")


@app.command()
def compare(
    candidates_path: Path = typer.Argument(..., help="JSONL of candidate rows"),
    frontier: Path = typer.Option(..., "--frontier", help="frontier JSONL"),
    out: Path | None = typer.Option(None, "--out", help="optional output JSONL"),
) -> None:
    """Annotate candidates with frontier comparison."""
    from eud.benchmarks.compare import compare_candidates_to_frontier, load_frontier
    from eud.core.io import read_jsonl, write_jsonl

    fr = load_frontier(frontier)
    rows = list(read_jsonl(candidates_path))
    annotated = compare_candidates_to_frontier(rows, fr)
    if out is not None:
        write_jsonl(annotated, out)
        console.print(f"[green]wrote[/green] {out}")
    beats = sum(1 for r in annotated if r["beats_frontier"])
    console.print(f"compared {len(rows)} candidates; beats_frontier={beats}")


@app.command()
def search(
    config_path: Path = typer.Argument(..., help="YAML config describing the sweep"),
    out: Path = typer.Option(..., "--out", help="output JSONL of run rows"),
    frontier: Path | None = typer.Option(None, "--frontier", help="optional frontier JSONL"),
) -> None:
    """Run a config-driven family sweep, appending one row per candidate."""
    from eud.search.experiments import run_config

    p = run_config(config_path, out, frontier_path=frontier)
    console.print(f"[green]wrote[/green] {p}")


@app.command()
def leaderboard(
    runs_path: Path = typer.Argument(..., help="run rows JSONL (output of `eud search`)"),
    frontier: Path | None = typer.Option(None, "--frontier"),
    out: Path | None = typer.Option(None, "--out", help="optional output JSONL"),
    top: int = typer.Option(25, "--top"),
) -> None:
    """Rank candidates against the frontier."""
    from eud.search.experiments import leaderboard as _lb
    from eud.search.experiments import write_leaderboard

    rows = _lb(runs_path, frontier_path=frontier, top=top)
    console.print(f"top {len(rows)} candidates:")
    console.print(
        f"  {'#':>3}  {'fam':<13} {'n':>6} {'e':>6} {'e/n':>6}  {'beats':>5}  {'Δ':>5}"
    )
    for i, r in enumerate(rows, 1):
        beats = "YES" if r.get("beats_frontier") else ""
        delta = r.get("improvement_at_n")
        delta_s = f"{delta:+d}" if isinstance(delta, int) else "-"
        console.print(
            f"  {i:>3}  {r['family']:<13} {r['n']:>6} {r['e']:>6} "
            f"{r['density']:>6.3f}  {beats:>5}  {delta_s:>5}"
        )
    if out is not None:
        write_leaderboard(runs_path, out, frontier_path=frontier, top=top)
        console.print(f"[green]wrote[/green] {out}")


def main() -> None:  # pragma: no cover - thin wrapper
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
