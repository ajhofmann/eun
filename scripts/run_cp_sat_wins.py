"""Push past greedy_peel on the Z[zeta_12] seed via local-swap + CP-SAT.

OR-Tools CP-SAT with multi-threaded workers hangs on this hardware (Apple
silicon + ortools 9.15), so we run with a single worker and use it only
for warm-started refinement of a pre-shrunk seed. The actual
"better-than-greedy" results are usually delivered by local-swap with
many restarts.

Pipeline per k:
1. Build the same Z[zeta_12] cb=4 R=3.0 ball seed (n=1767).
2. greedy_peel(seed, k) -> baseline e_greedy.
3. local_swap(seed, k, iters=20000, restarts=8) -> e_ls.
4. shrink seed to ~4*k via greedy_peel, then run CP-SAT (1 worker,
   single-threaded, 90 s) with the local-swap solution as a hint.
   Record e_cpsat plus solver status + best_bound.

Each row written immediately so the run can be killed and resumed.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from eud.families.cyclotomic import CyclotomicParams, build
from eud.search.ilp import CPSATConfig, cp_sat_densest_k
from eud.search.local_search import SAConfig, local_swap
from eud.search.prune import greedy_peel

K_VALUES = [25, 36, 49, 64, 81, 100, 121]
DEFAULT_TIME_LIMIT_S = 90.0  # 1.5 min per k for CP-SAT


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-limit", type=float, default=DEFAULT_TIME_LIMIT_S)
    ap.add_argument(
        "--out", type=Path, default=Path("data/runs/cp_sat_zeta12.jsonl")
    )
    ap.add_argument(
        "--ks",
        type=str,
        default=",".join(str(k) for k in K_VALUES),
    )
    ap.add_argument("--coeff-bound", type=int, default=4)
    ap.add_argument("--R", type=float, default=3.0)
    ap.add_argument("--m", type=int, default=12)
    ap.add_argument("--ls-iters", type=int, default=20000)
    ap.add_argument("--ls-restarts", type=int, default=8)
    ap.add_argument(
        "--shrink-multiplier",
        type=int,
        default=4,
        help="CP-SAT runs on greedy_peel(seed, shrink_multiplier * k).",
    )
    ap.add_argument(
        "--no-cpsat",
        action="store_true",
        help="Skip CP-SAT (only run greedy + local-swap).",
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

    cpsat_cfg_template = CPSATConfig(
        time_limit_s=args.time_limit, workers=1, seed=0
    )

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
            ls_sub = local_swap(
                seed,
                k,
                config=SAConfig(
                    max_iters=args.ls_iters,
                    seed=0,
                    restarts=args.ls_restarts,
                    start_temp=2.0,
                    end_temp=0.01,
                ),
            )
            t_ls = time.time() - t0
            print(
                f"  local_swap: e={ls_sub.e} density={ls_sub.density:.3f} "
                f"({t_ls:.1f}s)"
            )

            cp_e = ls_sub.e
            cp_status = "skipped"
            cp_bound = None
            cp_optimal = False
            cp_time = 0.0

            if not args.no_cpsat:
                shrink_size = min(seed.n, max(args.shrink_multiplier * k, 50))
                shrunk_seed = greedy_peel(seed, shrink_size)
                print(
                    f"  CP-SAT on shrunk_seed n={shrunk_seed.n} e={shrunk_seed.e} "
                    f"(time_limit={args.time_limit}s, 1 worker)..."
                )
                t0 = time.time()
                cp_sub, info = cp_sat_densest_k(
                    shrunk_seed, k, config=cpsat_cfg_template
                )
                cp_time = time.time() - t0
                cp_e = cp_sub.e
                cp_status = info.get("status", "?")
                cp_bound = info.get("best_bound")
                cp_optimal = bool(info.get("optimal", False))
                print(
                    f"  CP-SAT: e={cp_e} status={cp_status} bound={cp_bound} "
                    f"optimal={cp_optimal} ({cp_time:.1f}s)"
                )

                # Reconstruct selected coeff tuples in cp_sub for traceability.
                cp_chosen_coeffs = [tuple(p.coeffs) for p in cp_sub.points]
            else:
                cp_chosen_coeffs = []

            best_method = "greedy"
            best_e = greedy_sub.e
            for label, e in [("local_swap", ls_sub.e), ("cp_sat", cp_e)]:
                if e > best_e:
                    best_e = e
                    best_method = label

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
                "local_swap_e": ls_sub.e,
                "cp_sat_e": cp_e,
                "cp_sat_status": cp_status,
                "cp_sat_optimal": cp_optimal,
                "cp_sat_best_bound": cp_bound,
                "cp_sat_wall_time_s": cp_time,
                "best_method": best_method,
                "best_e": best_e,
                "improvement_vs_greedy": best_e - greedy_sub.e,
                "ls_chosen_coeffs": [tuple(p.coeffs) for p in ls_sub.points],
                "cp_sat_chosen_coeffs": cp_chosen_coeffs,
            }
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(
                f"  best: {best_method} e={best_e} (greedy={greedy_sub.e}, "
                f"ls={ls_sub.e}, cp_sat={cp_e})"
            )

    print(f"\nDone. Wrote {args.out}")


if __name__ == "__main__":
    main()
