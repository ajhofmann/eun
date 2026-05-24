"""Re-score the 12 zeta_12 'wins' against the strict baseline frontier.

Reads `data/runs/zeta12_vs_grid.json` (legacy: vs erdos_grid only) and
`data/frontiers/baseline.jsonl` (strict best-of-finite-construction)
and writes `data/runs/zeta12_vs_strict.json` showing how each original
win fares now.
"""

from __future__ import annotations

import json
from pathlib import Path

from eud.benchmarks.compare import load_frontier

LEGACY_PATH = Path("data/runs/zeta12_vs_grid.json")
FRONTIER_PATH = Path("data/frontiers/baseline.jsonl")
OUT_PATH = Path("data/runs/zeta12_vs_strict.json")


def main() -> None:
    legacy = json.loads(LEGACY_PATH.read_text())
    fr = load_frontier(FRONTIER_PATH)

    rows: list[dict] = []
    for r in legacy:
        n = int(r["n"])
        e_z12 = int(r["e_zeta12"])
        e_strict = fr.best_edges_at(n)
        delta = e_z12 - (e_strict if e_strict is not None else 0)
        rows.append(
            {
                "n": n,
                "e_zeta12": e_z12,
                "e_strict_baseline": e_strict,
                "delta": delta,
                "pct": (
                    100.0 * delta / e_strict if e_strict else None
                ),
                "still_a_win": delta > 0,
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2))

    surviving = [r for r in rows if r["still_a_win"]]
    print(f"wrote {OUT_PATH}")
    print(
        f"surviving wins (vs strict baseline): {len(surviving)} / {len(rows)}"
    )
    print()
    print(
        f"  {'n':>4}  {'e_zeta12':>9}  {'e_strict':>9}  {'Δ':>6}  {'%':>7}  status"
    )
    for r in rows:
        delta = r["delta"]
        pct = f"{r['pct']:+.1f}%" if r["pct"] is not None else "n/a"
        status = "WIN" if r["still_a_win"] else ("TIE" if delta == 0 else "LOSS")
        print(
            f"  {r['n']:>4}  {r['e_zeta12']:>9}  {r['e_strict_baseline']:>9}"
            f"  {delta:>+6d}  {pct:>7}  {status}"
        )


if __name__ == "__main__":
    main()
