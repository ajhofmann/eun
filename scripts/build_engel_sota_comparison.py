"""Build Engel vs published-SOTA comparison JSON from reproduction summary."""

from __future__ import annotations

import json
from pathlib import Path

from eud.benchmarks.engel_2025 import engel_2025_at
from eud.benchmarks.compare import load_frontier

REPRODUCE = Path("data/runs/engel_moser_reproduce.json")
OUT = Path("data/runs/engel_beat_sota_search.json")


def main() -> None:
    rows_in = json.loads(REPRODUCE.read_text())
    published = load_frontier(Path("data/frontiers/baseline.jsonl"))
    annotated: list[dict] = []
    for row in rows_in:
        k = int(row["k"])
        e = int(row["e"])
        target = engel_2025_at(k)
        pub_frontier = published.best_edges_at(k)
        annotated.append(
            {
                "n": k,
                "e_engel_moser": e,
                "engel_2025_e": target,
                "published_frontier_e": pub_frontier,
                "published_sota_e": target,
                "delta_vs_published_sota": e - target if target is not None else None,
                "beats_published_sota": target is not None and e > target,
                "delta_vs_engel_2025": row.get("delta_vs_engel_2025"),
                "candidate_file": row.get("candidate_file"),
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(annotated, indent=2))
    wins = [r for r in annotated if r["beats_published_sota"]]
    print(f"wrote {OUT}  wins={len(wins)}/{len(annotated)}")


if __name__ == "__main__":
    main()
