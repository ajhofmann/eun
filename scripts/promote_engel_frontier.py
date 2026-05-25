"""Merge Engel-Moser internal beyond-100 rows into baseline frontiers."""

from __future__ import annotations

import json
from pathlib import Path

from eud.benchmarks.engel_moser_internal import engel_moser_internal_rows
from eud.core.io import read_jsonl, write_jsonl

FRONTIERS = [
    Path("data/frontiers/baseline.jsonl"),
    Path("data/frontiers/baseline_reproducible.jsonl"),
]


def _merge(rows: list[dict], internal: list[dict]) -> list[dict]:
    best: dict[int, dict] = {int(r["n"]): r for r in rows}
    for r in internal:
        n = int(r["n"])
        e = int(r["e"])
        cur = best.get(n)
        if cur is None or e > int(cur["e"]):
            best[n] = {**r, "source": r.get("family", "engel_moser_internal")}
    return [best[n] for n in sorted(best)]


def main() -> None:
    internal = engel_moser_internal_rows()
    for path in FRONTIERS:
        if not path.exists():
            print(f"skip missing {path}")
            continue
        merged = _merge(list(read_jsonl(path)), internal)
        write_jsonl(merged, path)
        print(f"updated {path} rows={len(merged)}")
        sample = next(r for r in merged if int(r["n"]) == 121)
        print(f"  n=121 e={sample['e']} family={sample.get('family')}")


if __name__ == "__main__":
    main()
