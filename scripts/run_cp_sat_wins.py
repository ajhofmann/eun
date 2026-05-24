"""CP-SAT exact densest-k pruning on the Z[zeta_12] seed.

Builds the same coeff_bound=4, R=3.0 ball-window seed used to produce the
greedy_peel "wins", then runs OR-Tools CP-SAT to find the *exact* densest
size-k induced subgraph for each k in K_VALUES.

Each row records:
- k, e (objective), best_bound (LP relaxation upper bound),
- status (OPTIMAL / FEASIBLE / ...),
- wall_time_s,
- improvement_vs_greedy: e - greedy_peel(c, k).e for the same seed,
- chosen indices (so the subgraph can be reconstructed and verified).

Usage:
    uv run python scripts/run_cp_sat_wins.py [--time-limit 1200] [--workers 8]

Output: data/runs/cp_sat_zeta12.jsonl (one row per k, written as we go).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from eud.families.cyclotomic import CyclotomicParams, build
from eud.search.ilp import CPSATConfig, cp_sat_densest_k
from eud.search.prune import greedy_peel

K_VALUES = [25, 36, 49, 64, 81, 100, 121]
DEFAULT_TIME_LIMIT_S = 1200.0  # 20 minutes per k


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-limit", type=float, default=DEFAULT_TIME_LIMIT_S)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument(
        "--out", type=Path, default=Path("data/runs/cp_sat_zeta12.jsonl")
    )
    ap.add_argument(
        "--ks",
        type=str,
        default=",".join(str(k) for k in K_VALUES),
        help="comma-separated list of k values to solve",
    )
    ap.add_argument(
        "--coeff-bound", type=int, default=4, help="seed CyclotomicParams.coeff_bound"
    )
    ap.add_argument("--R", type=float, default=3.0, help="seed CyclotomicParams.R")
    ap.add_argument(
        "--m", type=int, default=12, help="seed CyclotomicParams.m (zeta order)"
    )
    args = ap.parse_args()

    ks = [int(x) for x in args.ks.split(",") if x.strip()]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        args.out.unlink()

    print(
        f"Building seed: cyclotomic m={args.m} cb={args.coeff_bound} R={args.R} ball window..."
    )
    t_seed = time.time()
    seed = build(
        CyclotomicParams(
            m=args.m, coeff_bound=args.coeff_bound, R=args.R, window_kind="ball"
        )
    )
    print(
        f"  seed: n={seed.n} e={seed.e} density={seed.density:.3f} "
        f"({time.time() - t_seed:.1f}s)"
    )

    cfg = CPSATConfig(time_limit_s=args.time_limit, workers=args.workers, seed=0)

    with args.out.open("w") as f:
        for k in ks:
            print(f"\n=== k={k} ===")
            t0 = time.time()
            greedy_sub = greedy_peel(seed, k)
            t_greedy = time.time() - t0

            print(
                f"  greedy_peel: e={greedy_sub.e} density={greedy_sub.density:.3f} "
                f"({t_greedy:.1f}s)"
            )

            t0 = time.time()
            sub, info = cp_sat_densest_k(seed, k, config=cfg)
            t_cpsat = time.time() - t0
            print(
                f"  CP-SAT: status={info['status']} obj={info.get('objective')} "
                f"bound={info.get('best_bound')} ({t_cpsat:.1f}s)"
            )

            sub_coeff_set = {sp.coeffs for sp in sub.points}
            chosen = [i for i, p in enumerate(seed.points) if p.coeffs in sub_coeff_set]

            row = {
                "seed_family": "cyclotomic",
                "seed_params": {
                    "m": args.m,
                    "coeff_bound": args.coeff_bound,
                    "R": args.R,
                    "window_kind": "ball",
                },
                "seed_n": seed.n,
                "seed_e": seed.e,
                "k": k,
                "greedy_e": greedy_sub.e,
                "greedy_density": greedy_sub.density,
                "cp_sat_e": sub.e,
                "cp_sat_density": sub.density,
                "improvement_vs_greedy": sub.e - greedy_sub.e,
                "status": info["status"],
                "objective": info.get("objective"),
                "best_bound": info.get("best_bound"),
                "optimal": bool(info.get("optimal", False)),
                "wall_time_s": t_cpsat,
                "chosen_indices": chosen,
            }
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(
                f"  delta vs greedy: {sub.e - greedy_sub.e:+d}  "
                f"(cp_sat e={sub.e}, greedy e={greedy_sub.e})"
            )

    print(f"\nDone. Wrote {args.out}")


if __name__ == "__main__":
    main()
