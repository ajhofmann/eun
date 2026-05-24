"""Find best zeta_12 (R, window_kind, translation_seed) per k.

Reads `data/runs/zeta12_window_explore.jsonl`, builds the corresponding
candidate, greedy-peels to k, then local-swaps with warm start to push
the result further. For any new winner vs the strict baseline, writes a
candidate JSON snapshot under `data/candidates/winv2_zeta12_n{k}.json`
and a row to `data/runs/zeta12_winv2_vs_strict.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

from eud.benchmarks.compare import load_frontier
from eud.core.io import write_candidate
from eud.families.cyclotomic import CyclotomicParams, build
from eud.search.local_search import SAConfig, local_swap
from eud.search.prune import greedy_peel

RUNS_PATH = Path("data/runs/zeta12_window_explore.jsonl")
FRONTIER_PATH = Path("data/frontiers/baseline.jsonl")
OUT_SUMMARY = Path("data/runs/zeta12_winv2_vs_strict.json")
OUT_DIR = Path("data/candidates")


def best_per_k(rows: list[dict], k_values: list[int]) -> dict[int, dict]:
    """For each k, find the (R, window, seed) tuple that maximizes greedy-peel e."""
    best: dict[int, dict] = {}
    for r in rows:
        for p in r.get("pruned", []):
            k = int(p["n"])
            if k not in k_values:
                continue
            entry = {**r["params"], "k": k, "greedy_e": int(p["e"])}
            cur = best.get(k)
            if cur is None or entry["greedy_e"] > cur["greedy_e"]:
                best[k] = entry
    return best


def main() -> None:
    fr = load_frontier(FRONTIER_PATH)

    raw = [json.loads(line) for line in RUNS_PATH.read_text().splitlines() if line.strip()]
    k_values = [49, 64, 81, 100, 121, 144, 169, 196]
    bests = best_per_k(raw, k_values)

    print(f"  {'k':>4}  {'config':<40}  {'greedy_e':>8}  {'ls_e':>5}  {'baseline':>8}  delta")
    summary: list[dict] = []
    for k in k_values:
        if k not in bests:
            continue
        cfg = bests[k]
        params = CyclotomicParams(
            m=12,
            coeff_bound=4,
            R=cfg["R"],
            window_kind=cfg["window_kind"],
            translation_seed=cfg.get("translation_seed"),
        )
        cand = build(params)
        greedy_sub = greedy_peel(cand, k)
        ls_sub = local_swap(
            cand,
            k,
            config=SAConfig(
                max_iters=30000, seed=0, restarts=8,
                start_temp=2.0, end_temp=0.005,
                warm_start_with_greedy=True,
            ),
        )
        best_e = max(greedy_sub.e, ls_sub.e)
        best_sub = ls_sub if ls_sub.e >= greedy_sub.e else greedy_sub
        baseline = fr.best_edges_at(k)
        delta = best_e - (baseline if baseline is not None else 0)
        cfg_label = f"R={cfg['R']} window={cfg['window_kind']} seed={cfg.get('translation_seed')}"
        print(
            f"  {k:>4}  {cfg_label:<40}  {greedy_sub.e:>8}  {ls_sub.e:>5}  "
            f"{str(baseline):>8}  {delta:+d}{' WIN' if delta > 0 else ''}"
        )
        out_path = OUT_DIR / f"winv2_zeta12_n{k}.json"
        write_candidate(best_sub, out_path)
        summary.append(
            {
                "k": k,
                "R": cfg["R"],
                "window_kind": cfg["window_kind"],
                "translation_seed": cfg.get("translation_seed"),
                "greedy_e": greedy_sub.e,
                "local_swap_e": ls_sub.e,
                "best_e": best_e,
                "best_method": "local_swap" if ls_sub.e > greedy_sub.e else "greedy",
                "strict_baseline_e": baseline,
                "delta": delta,
                "wins": delta > 0,
                "candidate_file": str(out_path),
            }
        )

    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2))
    wins = sum(1 for r in summary if r["wins"])
    print(f"\nwrote {OUT_SUMMARY}  wins={wins}/{len(summary)}")


if __name__ == "__main__":
    main()
