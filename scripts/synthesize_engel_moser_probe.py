"""Summarize and render the Engel 18-unit Moser probe sweep."""

from __future__ import annotations

import json
from pathlib import Path

from eud.benchmarks.engel_2025 import engel_2025_at
from eud.core.io import write_candidate
from eud.families.engel_moser import EngelMoserParams, build
from eud.search.local_search import SAConfig, local_swap
from eud.viz.draw import draw_candidate

RUN_PATH = Path("data/runs/engel_moser_probe.jsonl")
OUT_PATH = Path("data/runs/engel_moser_probe_best.json")
OUT_DIR = Path("data/candidates")


def main() -> None:
    best: dict[int, dict] = {}
    for line in RUN_PATH.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        for pruned in row.get("pruned", []):
            k = int(pruned["n"])
            e = int(pruned["e"])
            if k not in best or e > best[k]["e"]:
                best[k] = {
                    "k": k,
                    "e": e,
                    "params": row["params"],
                    "seed_n": row["n"],
                    "seed_e": row["e"],
                    "method": pruned.get("method"),
                }

    out_rows: list[dict] = []
    for k in sorted(best):
        r = best[k]
        params = EngelMoserParams(**r["params"])
        seed = build(params)
        sub = local_swap(
            seed,
            k,
            config=SAConfig(max_iters=10000, seed=0, restarts=4, warm_start_with_greedy=True),
        )
        engel = engel_2025_at(k)
        cand_path = OUT_DIR / f"engel_moser_probe_n{k}.json"
        png_path = OUT_DIR / f"engel_moser_probe_n{k}.png"
        write_candidate(sub, cand_path)
        draw_candidate(sub, png_path)
        out_rows.append(
            {
                **r,
                "rerendered_e": sub.e,
                "engel_2025_e": engel,
                "delta_vs_engel_2025": sub.e - engel if engel is not None else None,
                "candidate_file": str(cand_path),
                "image_file": str(png_path),
            }
        )

    OUT_PATH.write_text(json.dumps(out_rows, indent=2))
    print(f"wrote {OUT_PATH}")
    for r in out_rows:
        print(
            f"k={r['k']:>3} e={r['rerendered_e']:>4} "
            f"Engel={r['engel_2025_e']} Δ={r['delta_vs_engel_2025']}"
        )


if __name__ == "__main__":
    main()
