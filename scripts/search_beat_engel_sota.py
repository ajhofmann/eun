"""Search for certified Engel-Moser graphs that beat Engel et al. 2025 Table 2."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from eud.benchmarks.engel_2025 import engel_2025_at
from eud.core.io import read_candidate

SUMMARY = Path("data/runs/engel_moser_reproduce.json")
OUT = Path("data/runs/engel_beat_sota_search.json")


def _rows_from_summary(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-reproduce",
        action="store_true",
        help="Only annotate existing engel_moser_reproduce.json",
    )
    args = parser.parse_args()
    if not args.skip_reproduce:
        subprocess.run(
            [
                sys.executable,
                "scripts/reproduce_engel_2025.py",
                "--beam-width",
                "32",
                "--beam-rounds",
                "20",
                "--beam-seeds",
                "4",
                "--starts",
                "80",
                "--perturb-rounds",
                "120",
            ],
            check=True,
        )

    rows = _rows_from_summary(SUMMARY)
    annotated: list[dict] = []
    wins: list[dict] = []
    for row in rows:
        k = int(row["k"])
        e = int(row["e"])
        target = engel_2025_at(k)
        beats = target is not None and e > target
        entry = {
            **row,
            "published_sota_e": target,
            "delta_vs_published_sota": e - target if target is not None else None,
            "beats_published_sota": beats,
        }
        annotated.append(entry)
        if beats:
            wins.append(entry)
            cand = read_candidate(row["candidate_file"])
            print(f"SOTA WIN k={k} e={e} Engel={target} Δ={e - target} n={cand.n}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(annotated, indent=2))
    print(f"wrote {OUT}  wins={len(wins)}")
    for row in annotated:
        target = row["published_sota_e"]
        delta = row["delta_vs_engel_2025"]
        flag = "WIN" if row["beats_published_sota"] else ("=" if delta == 0 else f"Δ={delta}")
        print(f"k={row['k']:>3} e={row['e']:>4} Engel={target} {flag}")


if __name__ == "__main__":
    main()
