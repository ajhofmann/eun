"""Attempt to reproduce Engel et al. 2025 Table 2 with our Engel-Moser family.

This is not a full reimplementation of their diverse backtracking beam search.
It is a deliberately smaller experiment:

1. build finite visible-disk windows in Engel's 18-unit Moser lattice;
2. greedy-peel / random-start to k;
3. run best-improvement 1-swap local search plus small perturb-and-repair loops.

The script writes best candidates and a summary. It is meant to answer:
"Does the 18-unit lattice itself explain the gap, before we implement their
full canonized beam search?"
"""

from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from eud.benchmarks.engel_2025 import engel_2025_at
from eud.core.certificates import build_certificate
from eud.core.edges import adjacency
from eud.core.io import write_candidate, write_jsonl
from eud.core.pointset import Candidate
from eud.families.engel_moser import EngelMoserParams, build, squared_distance_symbolic
from eud.search.engel_beam import BeamConfig, beam_search
from eud.search.prune import greedy_peel
from eud.viz.draw import draw_candidate

OUT_DIR = Path("data/candidates")
VERIFY_DIR = Path("data/verified")
SUMMARY_PATH = Path("data/runs/engel_moser_reproduce.json")
K_VALUES = [25, 36, 49, 64, 81, 100]


@dataclass(frozen=True)
class SearchConfig:
    starts: int = 60
    perturb_rounds: int = 80
    max_no_improve: int = 25
    beam_width: int = 18
    beam_rounds: int = 12
    beam_additions: int = 18
    beam_drop_branches: int = 4
    seed: int = 0


def _score(S: set[int], adj: list[set[int]]) -> int:
    return sum(1 for v in S for u in adj[v] if u in S and u > v)


def _greedy_indices(seed: Candidate, k: int) -> set[int]:
    sub = greedy_peel(seed, k)
    coeffs = {p.coeffs for p in sub.points}
    return {i for i, p in enumerate(seed.points) if p.coeffs in coeffs}


def _best_one_swap(S: set[int], adj: list[set[int]]) -> tuple[int, int, int]:
    n = len(adj)
    outside = [u for u in range(n) if u not in S]
    losses = {v: sum(1 for u in adj[v] if u in S) for v in S}
    gains = {u: sum(1 for v in adj[u] if v in S) for u in outside}
    best_delta = 0
    best_out = -1
    best_in = -1
    for u in outside:
        gu = gains[u]
        adj_u = adj[u]
        for v in S:
            delta = gu - (1 if v in adj_u else 0) - losses[v]
            if delta > best_delta:
                best_delta = delta
                best_out = v
                best_in = u
    return best_delta, best_out, best_in


def _hill_climb(S: set[int], adj: list[set[int]]) -> set[int]:
    S = set(S)
    while True:
        delta, v_out, v_in = _best_one_swap(S, adj)
        if delta <= 0:
            return S
        S.remove(v_out)
        S.add(v_in)


def _random_high_degree_start(adj: list[set[int]], k: int, rng: random.Random) -> set[int]:
    deg_order = sorted(range(len(adj)), key=lambda v: (-len(adj[v]), v))
    pool = deg_order[: min(len(adj), max(2 * k, k + 20))]
    rng.shuffle(pool)
    return set(pool[:k])


def _perturb_and_repair(
    S: set[int],
    adj: list[set[int]],
    *,
    rng: random.Random,
    strength: int,
) -> set[int]:
    S = set(S)
    losses = sorted(
        ((sum(1 for u in adj[v] if u in S), v) for v in S),
        key=lambda x: (x[0], x[1]),
    )
    to_drop = [v for _, v in losses[:strength]]
    for v in to_drop:
        S.remove(v)

    while len(S) < len(losses):
        outside = [u for u in range(len(adj)) if u not in S]
        # Mostly greedy repair, with occasional randomization to escape ties.
        scored = [
            (sum(1 for v in adj[u] if v in S), rng.random(), u)
            for u in outside
        ]
        scored.sort(reverse=True)
        S.add(scored[0][2])
    return _hill_climb(S, adj)


def optimize(seed: Candidate, k: int, cfg: SearchConfig) -> tuple[Candidate, dict]:
    adj = adjacency(seed.n, seed.edges)
    rng = random.Random(cfg.seed + 1009 * k + seed.n)

    starts: list[set[int]] = [_greedy_indices(seed, k)]
    for _ in range(cfg.starts):
        starts.append(_random_high_degree_start(adj, k, rng))

    best_S: set[int] = set()
    best_e = -1
    for S0 in starts:
        S = _hill_climb(S0, adj)
        e = _score(S, adj)
        if e > best_e:
            best_S, best_e = S, e

    no_improve = 0
    for t in range(cfg.perturb_rounds):
        strength = 1 + (t % max(1, min(8, k // 8)))
        S = _perturb_and_repair(best_S, adj, rng=rng, strength=strength)
        e = _score(S, adj)
        if e > best_e:
            best_S, best_e = S, e
            no_improve = 0
        else:
            no_improve += 1
        if no_improve >= cfg.max_no_improve:
            break

    sub = seed.induced_subgraph(sorted(best_S))
    return sub, {
        "starts": cfg.starts,
        "perturb_rounds": cfg.perturb_rounds,
        "best_e": best_e,
    }


def improve_with_beam(sub: Candidate, k: int, cfg: SearchConfig) -> tuple[Candidate, dict]:
    """Run coefficient-space beam search around a strong k-vertex seed."""

    print(
        f"k={k} beam start seed_e={sub.e} width={cfg.beam_width} "
        f"rounds={cfg.beam_rounds}"
    )
    t0 = time.time()
    beam = beam_search(
        sub,
        k,
        config=BeamConfig(
            width=cfg.beam_width,
            rounds=cfg.beam_rounds,
            max_additions_per_state=cfg.beam_additions,
            drop_branches=cfg.beam_drop_branches,
            seed=cfg.seed,
        ),
    )
    info = {
        "width": cfg.beam_width,
        "rounds": cfg.beam_rounds,
        "max_additions_per_state": cfg.beam_additions,
        "drop_branches": cfg.beam_drop_branches,
        "rounds_completed": beam.rounds_completed,
        "states_seen": beam.states_seen,
        "best_by_round": beam.best_by_round,
        "seed_e": sub.e,
        "best_e": beam.candidate.e,
        "wall_time_s": time.time() - t0,
    }
    print(
        f"k={k} beam done best_e={beam.candidate.e} "
        f"states={beam.states_seen} ({info['wall_time_s']:.1f}s)"
    )
    return (beam.candidate, info) if beam.candidate.e >= sub.e else (sub, info)


def write_exact_certificate(candidate: Candidate, path: Path) -> None:
    cert = build_certificate(
        candidate,
        field_description="Q(sqrt(3), sqrt(11), i) Engel-Moser lattice",
        basis_description=["1", "omega_1", "omega_3", "omega_1*omega_3"],
        visible_embedding="omega_1 -> exp(i*pi/3); omega_3 -> 5/6 + i*sqrt(11)/6",
        sd=squared_distance_symbolic(),
    )
    write_jsonl([cert], path)


def _parse_k_values(raw: str) -> list[int]:
    return [int(part) for part in raw.split(",") if part.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k-values", default=",".join(map(str, K_VALUES)))
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--prefix", default="engel_moser_reproduce")
    parser.add_argument("--starts", type=int, default=SearchConfig.starts)
    parser.add_argument("--perturb-rounds", type=int, default=SearchConfig.perturb_rounds)
    parser.add_argument("--beam-width", type=int, default=SearchConfig.beam_width)
    parser.add_argument("--beam-rounds", type=int, default=SearchConfig.beam_rounds)
    parser.add_argument("--beam-additions", type=int, default=SearchConfig.beam_additions)
    parser.add_argument("--beam-drop-branches", type=int, default=SearchConfig.beam_drop_branches)
    parser.add_argument("--max-coeff-bound", type=int, default=3)
    parser.add_argument("--max-visible-radius", type=float, default=4.0)
    parser.add_argument("--seed", type=int, default=SearchConfig.seed)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = SearchConfig(
        starts=args.starts,
        perturb_rounds=args.perturb_rounds,
        beam_width=args.beam_width,
        beam_rounds=args.beam_rounds,
        beam_additions=args.beam_additions,
        beam_drop_branches=args.beam_drop_branches,
        seed=args.seed,
    )
    k_values = _parse_k_values(args.k_values)
    params_grid = [
        EngelMoserParams(coeff_bound=2, visible_radius=r)
        for r in [2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5]
    ] + [
        EngelMoserParams(coeff_bound=3, visible_radius=r)
        for r in [2.5, 3.0, 3.5, 4.0]
    ]
    params_grid = [
        params
        for params in params_grid
        if params.coeff_bound <= args.max_coeff_bound
        and params.visible_radius <= args.max_visible_radius
    ]

    seeds: list[tuple[EngelMoserParams, Candidate]] = []
    for params in params_grid:
        t0 = time.time()
        seed = build(params)
        seeds.append((params, seed))
        print(
            f"seed {asdict(params)} n={seed.n} e={seed.e} "
            f"|U|={len(seed.unit_vectors)} ({time.time() - t0:.1f}s)"
        )

    rows: list[dict] = []
    for k in k_values:
        target = engel_2025_at(k)
        best: tuple[int, Candidate, EngelMoserParams, dict] | None = None
        for params, seed in seeds:
            if seed.n < k:
                continue
            sub, info = optimize(seed, k, cfg)
            if best is None or sub.e > best[0]:
                best = (sub.e, sub, params, info)
                print(f"k={k} new best e={sub.e} target={target} params={asdict(params)}")
            if target is not None and sub.e >= target:
                break
        assert best is not None
        _, sub, params, info = best
        beam_sub, beam_info = improve_with_beam(sub, k, cfg)
        if beam_sub.e > sub.e:
            print(f"k={k} beam improved e={sub.e} -> {beam_sub.e} target={target}")
        sub = beam_sub
        info = {**info, "beam": beam_info}
        cand_path = OUT_DIR / f"{args.prefix}_n{k}.json"
        png_path = OUT_DIR / f"{args.prefix}_n{k}.png"
        cert_path = VERIFY_DIR / f"{args.prefix}_n{k}_cert.jsonl"
        write_candidate(sub, cand_path)
        draw_candidate(sub, png_path)
        write_exact_certificate(sub, cert_path)
        rows.append(
            {
                "k": k,
                "e": sub.e,
                "engel_2025_e": target,
                "delta_vs_engel_2025": sub.e - target if target is not None else None,
                "params": asdict(params),
                "search": info,
                "candidate_file": str(cand_path),
                "image_file": str(png_path),
                "certificate_file": str(cert_path),
            }
        )
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(rows, indent=2))

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(rows, indent=2))
    print(f"wrote {args.summary}")
    for row in rows:
        print(
            f"k={row['k']:>3} e={row['e']:>4} "
            f"Engel={row['engel_2025_e']} Δ={row['delta_vs_engel_2025']}"
        )


if __name__ == "__main__":
    main()
