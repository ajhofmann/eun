"""Summarize Engel-Moser beam candidates beyond Engel et al.'s published table."""

from __future__ import annotations

import json
from pathlib import Path

from eud.benchmarks.compare import load_frontier
from eud.core.io import read_candidate

K_VALUES = [121, 144, 169, 196, 225, 289]
OUT = Path("data/runs/engel_moser_beyond_100.json")


def main() -> None:
    published = load_frontier(Path("data/frontiers/baseline.jsonl"))
    reproducible = load_frontier(Path("data/frontiers/baseline_reproducible.jsonl"))
    rows = []
    for k in K_VALUES:
        candidate_file = Path(f"data/candidates/engel_moser_beyond_n{k}.json")
        if not candidate_file.exists():
            continue
        candidate = read_candidate(candidate_file)
        published_e = published.best_edges_at(k)
        reproducible_e = reproducible.best_edges_at(k)
        rows.append(
            {
                "k": k,
                "e": candidate.e,
                "density": candidate.density,
                "published_baseline_e": published_e,
                "delta_vs_published_baseline": (
                    candidate.e - published_e if published_e is not None else None
                ),
                "reproducible_baseline_e": reproducible_e,
                "delta_vs_reproducible_baseline": (
                    candidate.e - reproducible_e if reproducible_e is not None else None
                ),
                "params": candidate.params,
                "candidate_file": str(candidate_file),
                "image_file": f"data/candidates/engel_moser_beyond_n{k}.png",
                "certificate_file": f"data/verified/engel_moser_beyond_n{k}_cert.jsonl",
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"wrote {OUT}")
    for row in rows:
        print(
            f"k={row['k']:>3} e={row['e']:>5} "
            f"published Δ={row['delta_vs_published_baseline']} "
            f"repro Δ={row['delta_vs_reproducible_baseline']}"
        )


if __name__ == "__main__":
    main()
