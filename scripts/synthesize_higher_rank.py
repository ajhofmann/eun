"""Compare higher-rank (m in {15, 20, 24}) cyclotomic sweep against strict baseline.

Reads `data/runs/cyclotomic_higher_rank.jsonl` (output of `eud search`)
and the current `data/frontiers/baseline.jsonl`. Writes a sorted summary
to `data/runs/higher_rank_vs_strict.json` with one row per (k, m, params)
configuration showing whether it beats the strict baseline at that k.
"""

from __future__ import annotations

import json
from pathlib import Path

from eud.benchmarks.compare import load_frontier

RUNS_PATH = Path("data/runs/cyclotomic_higher_rank.jsonl")
FRONTIER_PATH = Path("data/frontiers/baseline.jsonl")
OUT_PATH = Path("data/runs/higher_rank_vs_strict.json")


def main() -> None:
    fr = load_frontier(FRONTIER_PATH)

    rows: list[dict] = []
    for line in RUNS_PATH.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        params = r["params"]
        for p in r.get("pruned", []):
            n = int(p["n"])
            e = int(p["e"])
            base = fr.best_edges_at(n)
            delta = e - base if base is not None else None
            rows.append(
                {
                    "m": params["m"],
                    "coeff_bound": params["coeff_bound"],
                    "R": params["R"],
                    "translation_seed": params.get("translation_seed"),
                    "k": n,
                    "e": e,
                    "method": p.get("method"),
                    "strict_baseline_e": base,
                    "delta": delta,
                    "wins": (delta is not None and delta > 0),
                }
            )

    # Best per k across all configs
    best_per_k: dict[int, dict] = {}
    for r in rows:
        k = r["k"]
        if k not in best_per_k or r["e"] > best_per_k[k]["e"]:
            best_per_k[k] = r

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {
                "rows": rows,
                "best_per_k": [best_per_k[k] for k in sorted(best_per_k)],
            },
            indent=2,
        )
    )

    print(f"wrote {OUT_PATH}  rows={len(rows)}")
    print()
    print("best higher-rank candidate per k (vs strict baseline):")
    print(
        f"  {'k':>4}  {'e_best':>6}  {'baseline':>8}  {'Δ':>5}  m  R    seed   wins?"
    )
    wins = 0
    for k in sorted(best_per_k):
        r = best_per_k[k]
        delta = r["delta"]
        delta_s = f"{delta:+d}" if isinstance(delta, int) else "?"
        win_s = "WIN" if r["wins"] else ""
        if r["wins"]:
            wins += 1
        print(
            f"  {k:>4}  {r['e']:>6}  {str(r['strict_baseline_e']):>8}  "
            f"{delta_s:>5}  {r['m']:<2} {r['R']:<4} {str(r['translation_seed']):<6} "
            f"{win_s}"
        )
    print(f"\ntotal wins (higher-rank > strict baseline): {wins} / {len(best_per_k)}")


if __name__ == "__main__":
    main()
