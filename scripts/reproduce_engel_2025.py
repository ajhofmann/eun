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
    beam_width: int = 32
    beam_rounds: int = 20
    beam_additions: int = 24
    beam_drop_branches: int = 6
    beam_seeds: int = 4
    seed: int = 0


def _score(S: set[int], adj: list[set[int]]) -> int:
    return sum(1 for v in S for u in adj[v] if u in S and u > v)


def _greedy_indices(seed: Candidate, k: int) -> set[int]:
    sub = greedy_peel(seed, k)
    coeffs = {p.coeffs for p in sub.points}
    return {i for i, p in enumerate(seed.points) if p.coeffs in coeffs}


def _best_two_swap(
    S: set[int],
    adj: list[set[int]],
    *,
    max_outside: int = 200,
    max_out_pairs: int = 120,
) -> tuple[int, int, int, int, int]:
    """Remove two vertices and add two; returns (delta, out1, out2, in1, in2)."""

    outside = [u for u in range(len(adj)) if u not in S]
    if len(outside) > max_outside:
        gains = {u: sum(1 for v in adj[u] if v in S) for u in outside}
        outside = sorted(outside, key=lambda u: (-gains[u], u))[:max_outside]
    losses = {v: sum(1 for u in adj[v] if u in S) for v in S}
    best_delta = 0
    best = (-1, -1, -1, -1)
    verts = sorted(S, key=lambda v: (losses[v], v))
    out_pairs: list[tuple[int, int]] = []
    for i, v1 in enumerate(verts):
        for v2 in verts[i + 1 :]:
            out_pairs.append((v1, v2))
            if len(out_pairs) >= max_out_pairs:
                break
        if len(out_pairs) >= max_out_pairs:
            break
    for v1, v2 in out_pairs:
        base_loss = losses[v1] + losses[v2]
        cross = sum(1 for u in adj[v1] if u in S and u != v2)
        cross += sum(1 for u in adj[v2] if u in S and u != v1)
        base_loss -= cross
        for j, u1 in enumerate(outside):
            g1 = sum(1 for v in adj[u1] if v in S)
            adj_u1 = adj[u1]
            for u2 in outside[j + 1 :]:
                delta = (
                    g1
                    + sum(1 for v in adj[u2] if v in S)
                    - base_loss
                    - (1 if v1 in adj_u1 else 0)
                    - (1 if v2 in adj_u1 else 0)
                    - (1 if v1 in adj[u2] else 0)
                    - (1 if v2 in adj[u2] else 0)
                    - (1 if u2 in adj_u1 else 0)
                )
                if delta > best_delta:
                    best_delta = delta
                    best = (v1, v2, u1, u2)
    return best_delta, *best


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


def _hill_climb(S: set[int], adj: list[set[int]], *, use_two_swap: bool = False) -> set[int]:
    S = set(S)
    while True:
        if use_two_swap:
            delta2, o1, o2, i1, i2 = _best_two_swap(S, adj)
            if delta2 > 0 and o1 >= 0:
                S.remove(o1)
                S.remove(o2)
                S.add(i1)
                S.add(i2)
                continue
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
    return _hill_climb(S, adj, use_two_swap=len(S) <= 64)


def _indices_for_coeffs(seed: Candidate, coeffs: set[tuple[int, int, int, int]]) -> set[int]:
    coeff_to_idx = {tuple(p.coeffs): i for i, p in enumerate(seed.points)}
    return {coeff_to_idx[c] for c in coeffs if c in coeff_to_idx}


def try_cp_sat_polish(sub: Candidate, seed: Candidate, k: int) -> Candidate:
    """Exact densest-k on modest parent graphs when local search plateaus."""

    if k > 64 or seed.n > 450:
        return sub
    try:
        from eud.search.ilp import CPSATConfig, cp_sat_densest_k
    except ImportError:
        return sub
    refined, _ = cp_sat_densest_k(
        seed,
        k,
        config=CPSATConfig(time_limit_s=90.0, workers=1, seed=0, symmetry_level=0),
    )
    return refined if refined.n == k and refined.e > sub.e else sub


def polish_on_parent(sub: Candidate, seed: Candidate, k: int, cfg: SearchConfig) -> Candidate:
    """Re-run hill-climb swaps on the parent seed graph starting from `sub`."""

    if sub.n != k:
        return sub
    adj = adjacency(seed.n, seed.edges)
    coeffs = {tuple(p.coeffs) for p in sub.points}
    S = _indices_for_coeffs(seed, coeffs)
    if len(S) != k:
        return sub
    S = _hill_climb(S, adj, use_two_swap=k <= 64)
    polished = seed.induced_subgraph(sorted(S))
    return polished if polished.e >= sub.e else sub


def optimize(
    seed: Candidate,
    k: int,
    cfg: SearchConfig,
    *,
    initial: Candidate | None = None,
) -> tuple[Candidate, dict]:
    adj = adjacency(seed.n, seed.edges)
    rng = random.Random(cfg.seed + 1009 * k + seed.n)

    starts: list[set[int]] = [_greedy_indices(seed, k)]
    if initial is not None and initial.n == k:
        starts.insert(0, _indices_for_coeffs(seed, {tuple(p.coeffs) for p in initial.points}))
    for _ in range(cfg.starts):
        starts.append(_random_high_degree_start(adj, k, rng))

    best_S: set[int] = set()
    best_e = -1
    use_two_swap = k <= 64
    for S0 in starts:
        S = _hill_climb(S0, adj, use_two_swap=use_two_swap)
        e = _score(S, adj)
        if e > best_e:
            best_S, best_e = S, e

    no_improve = 0
    for t in range(cfg.perturb_rounds):
        strength = 1 + (t % max(1, min(8, k // 8)))
        S = _perturb_and_repair(best_S, adj, rng=rng, strength=strength)
        S = _hill_climb(S, adj, use_two_swap=use_two_swap)
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


def improve_with_beam(
    sub: Candidate,
    k: int,
    cfg: SearchConfig,
    *,
    parent: Candidate | None = None,
) -> tuple[Candidate, dict]:
    """Run coefficient-space beam search around a strong k-vertex seed."""

    parent = parent or sub
    best = sub
    if cfg.beam_width <= 0 or cfg.beam_rounds <= 0:
        return best, {"skipped": True, "best_e": best.e}
    runs: list[dict] = []
    print(
        f"k={k} beam start seed_e={sub.e} width={cfg.beam_width} "
        f"rounds={cfg.beam_rounds} seeds={cfg.beam_seeds}"
    )
    t0 = time.time()
    for beam_seed in range(cfg.beam_seeds):
        beam = beam_search(
            sub,
            k,
            config=BeamConfig(
                width=cfg.beam_width,
                rounds=cfg.beam_rounds,
                max_additions_per_state=cfg.beam_additions,
                drop_branches=cfg.beam_drop_branches,
                seed=cfg.seed + 1009 * beam_seed,
                visit_penalty=0.02,
                signature_penalty=0.01,
            ),
        )
        candidate = polish_on_parent(beam.candidate, parent, k, cfg)
        candidate = optimize(parent, k, cfg, initial=candidate)[0]
        candidate = try_cp_sat_polish(candidate, parent, k)
        runs.append(
            {
                "beam_seed": beam_seed,
                "rounds_completed": beam.rounds_completed,
                "states_seen": beam.states_seen,
                "beam_e": beam.candidate.e,
                "polished_e": candidate.e,
            }
        )
        if candidate.e > best.e:
            best = candidate
    info = {
        "width": cfg.beam_width,
        "rounds": cfg.beam_rounds,
        "max_additions_per_state": cfg.beam_additions,
        "drop_branches": cfg.beam_drop_branches,
        "beam_seeds": cfg.beam_seeds,
        "seed_e": sub.e,
        "best_e": best.e,
        "runs": runs,
        "wall_time_s": time.time() - t0,
    }
    print(
        f"k={k} beam done best_e={best.e} "
        f"({info['wall_time_s']:.1f}s)"
    )
    return best, info


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
    parser.add_argument("--beam-seeds", type=int, default=SearchConfig.beam_seeds)
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
        beam_seeds=args.beam_seeds,
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
        parent_seed = next(seed for p, seed in seeds if p == params)
        beam_sub, beam_info = improve_with_beam(sub, k, cfg, parent=parent_seed)
        for large_params, large_seed in seeds:
            if large_seed.n < max(3 * k, 150):
                continue
            large_sub, _ = optimize(large_seed, k, cfg)
            beam_large, large_info = improve_with_beam(
                large_sub,
                k,
                cfg,
                parent=large_seed,
            )
            if beam_large.e > beam_sub.e:
                print(
                    f"k={k} large-window improved e={beam_sub.e} -> {beam_large.e} "
                    f"from n={large_seed.n}"
                )
                beam_sub = beam_large
                params = large_params
                parent_seed = large_seed
                beam_info = {**beam_info, "large_window": large_info}
        if beam_sub.e > sub.e:
            print(f"k={k} beam improved e={sub.e} -> {beam_sub.e} target={target}")
        sub = beam_sub
        info = {**info, "beam": beam_info}
        if target is not None and sub.e < target:
            heavy = SearchConfig(
                starts=max(cfg.starts, 80),
                perturb_rounds=max(cfg.perturb_rounds, 120),
                beam_width=max(cfg.beam_width, 48),
                beam_rounds=max(cfg.beam_rounds, 32),
                beam_additions=max(cfg.beam_additions, 32),
                beam_drop_branches=max(cfg.beam_drop_branches, 8),
                beam_seeds=max(cfg.beam_seeds, 6),
                seed=cfg.seed + 17,
            )
            print(f"k={k} heavy pass target={target} current={sub.e}")
            heavy_sub, heavy_info = optimize(parent_seed, k, heavy, initial=sub)
            heavy_sub, heavy_beam = improve_with_beam(
                heavy_sub,
                k,
                heavy,
                parent=parent_seed,
            )
            if heavy_sub.e > sub.e:
                print(f"k={k} heavy improved e={sub.e} -> {heavy_sub.e}")
                sub = heavy_sub
                info = {**info, "heavy": heavy_info, "heavy_beam": heavy_beam}
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
