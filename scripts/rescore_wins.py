"""Re-score zeta_12 constructions against both reproducible and published baselines.

Outputs:
  - data/frontiers/baseline_reproducible.jsonl
      Our reproducible construction-only frontier (no Engel 2025 table).
  - data/frontiers/baseline.jsonl and baseline_strict.jsonl
      Published-SOTA-aware frontier (Engel 2025 through n=100 + reproducible
      families beyond that).
  - data/runs/zeta12_vs_published_sota.json
      Honest comparison table with deltas vs both frontiers.
  - data/runs/zeta12_vs_strict.json
      Back-compat alias for the same honest table.
"""

from __future__ import annotations

import json
from pathlib import Path

from eud.benchmarks.compare import build_baseline_frontier, load_frontier
from eud.benchmarks.engel_2025 import engel_2025_at, engel_2025_rows
from eud.core.io import write_jsonl

LEGACY_PATH = Path("data/runs/zeta12_vs_grid.json")
V2_PATH = Path("data/runs/zeta12_winv2_vs_strict.json")
REPRO_FRONTIER_PATH = Path("data/frontiers/baseline_reproducible.jsonl")
PUBLISHED_FRONTIER_PATH = Path("data/frontiers/baseline.jsonl")
STRICT_ALIAS_PATH = Path("data/frontiers/baseline_strict.jsonl")
OUT_PATH = Path("data/runs/zeta12_vs_published_sota.json")
STRICT_ALIAS_OUT = Path("data/runs/zeta12_vs_strict.json")


def _best_rows(rows: list[dict]) -> list[dict]:
    priority = {"known_bounds": 0, "engel_2025": 1}
    best: dict[int, dict] = {}
    for r in rows:
        n = int(r["n"])
        e = int(r["e"])
        fam = r.get("family", "?")
        cur = best.get(n)
        if cur is None:
            best[n] = {**r, "source": fam}
            continue
        cur_e = int(cur["e"])
        if e > cur_e or (
            e == cur_e and priority.get(fam, 99) < priority.get(cur.get("family", "?"), 99)
        ):
            best[n] = {**r, "source": fam}
    return [best[n] for n in sorted(best)]


def main() -> None:
    legacy = json.loads(LEGACY_PATH.read_text())
    v2_rows = json.loads(V2_PATH.read_text()) if V2_PATH.exists() else []
    v2_by_n = {int(r["k"]): r for r in v2_rows}

    print("building reproducible-only frontier (no Engel 2025)...")
    repro_rows = build_baseline_frontier(n_max=1000, include_engel_2025=False)
    write_jsonl(repro_rows, REPRO_FRONTIER_PATH)

    published_rows = _best_rows([*repro_rows, *engel_2025_rows()])
    write_jsonl(published_rows, PUBLISHED_FRONTIER_PATH)
    write_jsonl(published_rows, STRICT_ALIAS_PATH)

    repro = load_frontier(REPRO_FRONTIER_PATH)
    published = load_frontier(PUBLISHED_FRONTIER_PATH)

    rows: list[dict] = []
    for r in legacy:
        n = int(r["n"])
        e_v1 = int(r["e_zeta12"])
        v2 = v2_by_n.get(n)
        e_v2 = int(v2["best_e"]) if v2 is not None else None
        e_best = max(e_v1, e_v2 or -1)
        repro_e = repro.best_edges_at(n)
        published_frontier_e = published.best_edges_at(n)
        engel_e = engel_2025_at(n)
        delta_repro = e_best - (repro_e if repro_e is not None else 0)
        delta_published = e_best - engel_e if engel_e is not None else None
        rows.append(
            {
                "n": n,
                "e_zeta12_v1": e_v1,
                "e_zeta12_v2": e_v2,
                "e_zeta12_best": e_best,
                "best_zeta12_variant": "v2" if e_v2 is not None and e_v2 >= e_v1 else "v1",
                "reproducible_baseline_e": repro_e,
                "published_frontier_e": published_frontier_e,
                "published_sota_e": engel_e,
                "engel_2025_e": engel_e,
                "delta_vs_reproducible_baseline": delta_repro,
                "pct_vs_reproducible_baseline": (
                    100.0 * delta_repro / repro_e if repro_e else None
                ),
                "delta_vs_published_sota": delta_published,
                "pct_vs_published_sota": (
                    100.0 * delta_published / engel_e
                    if delta_published is not None and engel_e
                    else None
                ),
                "beats_reproducible_baseline": delta_repro > 0,
                "beats_published_sota": delta_published is not None and delta_published > 0,
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2))
    STRICT_ALIAS_OUT.write_text(json.dumps(rows, indent=2))

    print(f"wrote {OUT_PATH}")
    print(f"wrote {STRICT_ALIAS_OUT}")
    print(f"wrote {REPRO_FRONTIER_PATH}")
    print(f"wrote {PUBLISHED_FRONTIER_PATH}")
    print()
    print(
        f"  {'n':>4}  {'zeta_best':>9}  {'repro':>7}  {'Δrep':>6}  "
        f"{'pub_sota':>8}  {'Δsota':>7}  status"
    )
    for r in rows:
        delta_sota = r["delta_vs_published_sota"]
        status = (
            "SOTA WIN"
            if r["beats_published_sota"]
            else "REPRO WIN"
            if r["beats_reproducible_baseline"]
            else "LOSS"
        )
        delta_sota_s = f"{delta_sota:+d}" if isinstance(delta_sota, int) else "n/a"
        print(
            f"  {r['n']:>4}  {r['e_zeta12_best']:>9}  "
            f"{str(r['reproducible_baseline_e']):>7}  "
            f"{r['delta_vs_reproducible_baseline']:>+6d}  "
            f"{str(r['published_sota_e']):>8}  {delta_sota_s:>7}  {status}"
        )


if __name__ == "__main__":
    main()
