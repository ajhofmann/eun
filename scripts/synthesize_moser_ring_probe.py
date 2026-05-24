"""Write best Moser-ring probe subgraphs as candidates/images.

`eud search` records pruned summary rows, but the website needs concrete
candidate JSON files to visualize.  This script rebuilds each probe seed,
greedy-peels it to the requested k values, and stores the best subgraph per k.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from eud.core.io import read_jsonl, write_candidate
from eud.families.moser_ring import MoserRingParams, build
from eud.search.prune import greedy_peel
from eud.viz.draw import draw_candidate

RUN_PATH = Path("data/runs/moser_ring_probe.jsonl")
SUMMARY_PATH = Path("data/runs/moser_ring_probe_best.json")
OUT_DIR = Path("data/candidates")


def _params_from_row(row: dict) -> MoserRingParams:
    raw = row["params"]
    return MoserRingParams(
        denom_power=int(raw.get("denom_power", 1)),
        coeff_bound=int(raw.get("coeff_bound", 3)),
        visible_radius=float(raw.get("visible_radius", 2.0)),
        window_kind=str(raw.get("window_kind", "visible_disk")),
        unit_search_bound=raw.get("unit_search_bound"),
    )


def main() -> None:
    best: dict[int, tuple[int, MoserRingParams]] = {}
    for row in read_jsonl(RUN_PATH):
        params = _params_from_row(row)
        for pruned in row.get("pruned", []):
            k = int(pruned["n"])
            e = int(pruned["e"])
            if k not in best or e > best[k][0]:
                best[k] = (e, params)

    rows: list[dict] = []
    for k in sorted(best):
        expected_e, params = best[k]
        candidate = greedy_peel(build(params), k)
        if candidate.e != expected_e:
            raise RuntimeError(f"k={k}: rebuilt e={candidate.e}, expected {expected_e}")
        json_path = OUT_DIR / f"moser_ring_probe_n{k}.json"
        png_path = OUT_DIR / f"moser_ring_probe_n{k}.png"
        write_candidate(candidate, json_path)
        draw_candidate(candidate, png_path)
        row = {
            "k": k,
            "e": candidate.e,
            "density": candidate.density,
            "params": asdict(params),
            "n_units": len(candidate.unit_vectors),
            "candidate_file": str(json_path),
            "image_file": str(png_path),
        }
        rows.append(row)
        print(f"k={k} e={candidate.e} |U|={len(candidate.unit_vectors)} wrote {json_path}")

    SUMMARY_PATH.write_text(json.dumps(rows, indent=2))
    print(f"wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
