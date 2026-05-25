"""Rebuild data/candidates/manifest.json for the web gallery.

Combines (in priority order):
  - winv2_zeta12_n*.json, win_zeta12_n*.json
  - engel_moser_reproduce_n*.json, engel_moser_beyond_n*.json
  - engel_moser_probe_n*.json, moser_ring_probe_n*.json
  - uploaded_moser_disk_*.json, gallery_*.json

Each entry gets a description, n, e, density, unit_vectors count, and
a relative file path the web viewer can fetch.
"""

from __future__ import annotations

import json
from pathlib import Path

CANDIDATES = Path("data/candidates")
MANIFEST = CANDIDATES / "manifest.json"


def load_candidate_summary(p: Path) -> dict:
    raw = json.loads(p.read_text())
    return {
        "n": int(raw.get("n", len(raw.get("points", [])))),
        "e": int(raw.get("e", len(raw.get("edges", [])))),
        "unit_vectors": len(raw.get("unit_vectors", [])),
        "family": raw.get("family", "?"),
        "params": raw.get("params", {}),
    }


def main() -> None:
    v2_summary_path = Path("data/runs/zeta12_winv2_vs_strict.json")
    v2_summary = (
        json.loads(v2_summary_path.read_text()) if v2_summary_path.exists() else []
    )
    v2_by_k = {r["k"]: r for r in v2_summary}

    entries: list[dict] = []

    for n in sorted(v2_by_k, reverse=True):
        path = CANDIDATES / f"winv2_zeta12_n{n}.json"
        if not path.exists():
            continue
        s = load_candidate_summary(path)
        v2 = v2_by_k[n]
        delta = v2["delta"]
        if delta > 0:
            tag = (
                f"WIN v2: Z[\u03b6_12] {v2['best_method']} "
                f"window={v2['window_kind']} R={v2['R']} seed={v2['translation_seed']}, "
                f"n={s['n']} e={s['e']} vs strict baseline {v2['strict_baseline_e']} (\u0394=+{delta})"
            )
        else:
            tag = (
                f"TIE v2: Z[\u03b6_12], n={s['n']} e={s['e']} matches strict baseline "
                f"{v2['strict_baseline_e']}"
            )
        entries.append(
            {
                "name": f"winv2_zeta12_n{n}",
                "file": f"/candidates/winv2_zeta12_n{n}.json",
                "description": tag,
                "family": s["family"],
                "n": s["n"],
                "e": s["e"],
                "density": round(s["e"] / s["n"], 4) if s["n"] else 0.0,
                "unit_vectors": s["unit_vectors"],
            }
        )

    for path in sorted(CANDIDATES.glob("win_zeta12_n*.json"), reverse=True):
        n_label = path.stem.split("_")[-1]
        try:
            int(n_label.lstrip("n"))
        except ValueError:
            continue
        s = load_candidate_summary(path)
        entries.append(
            {
                "name": path.stem,
                "file": f"/candidates/{path.name}",
                "description": (
                    f"v1: Z[\u03b6_12] greedy-pruned ball window R=3.0 cb=4, "
                    f"n={s['n']} e={s['e']} \u2014 sympy + PARI verified"
                ),
                "family": s["family"],
                "n": s["n"],
                "e": s["e"],
                "density": round(s["e"] / s["n"], 4) if s["n"] else 0.0,
                "unit_vectors": s["unit_vectors"],
            }
        )

    engel_summary_path = Path("data/runs/engel_moser_reproduce.json")
    if engel_summary_path.exists():
        for row in json.loads(engel_summary_path.read_text()):
            path = Path(row["candidate_file"])
            if not path.exists():
                continue
            s = load_candidate_summary(path)
            entries.append(
                {
                    "name": path.stem,
                    "file": f"/candidates/{path.name}",
                    "description": (
                        f"Engel 18-unit Moser reproduction: n={s['n']} e={s['e']} "
                        f"vs Engel 2025 e={row['engel_2025_e']} "
                        f"(Δ={row['delta_vs_engel_2025']})"
                    ),
                    "family": s["family"],
                    "n": s["n"],
                    "e": s["e"],
                    "density": round(s["e"] / s["n"], 4) if s["n"] else 0.0,
                    "unit_vectors": s["unit_vectors"],
                }
            )

    engel_beyond_path = Path("data/runs/engel_moser_beyond_100.json")
    if engel_beyond_path.exists():
        for row in json.loads(engel_beyond_path.read_text()):
            path = Path(row["candidate_file"])
            if not path.exists():
                continue
            s = load_candidate_summary(path)
            entries.append(
                {
                    "name": path.stem,
                    "file": f"/candidates/{path.name}",
                    "description": (
                        f"Engel 18-unit Moser beyond n=100: n={s['n']} e={s['e']} "
                        f"vs reproducible fallback {row['reproducible_baseline_e']} "
                        f"(\u0394=+{row['delta_vs_reproducible_baseline']})"
                    ),
                    "family": s["family"],
                    "n": s["n"],
                    "e": s["e"],
                    "density": round(s["e"] / s["n"], 4) if s["n"] else 0.0,
                    "unit_vectors": s["unit_vectors"],
                }
            )

    moser_ring_path = Path("data/runs/moser_ring_probe_best.json")
    if moser_ring_path.exists():
        for row in json.loads(moser_ring_path.read_text()):
            path = Path(row["candidate_file"])
            if not path.exists():
                continue
            s = load_candidate_summary(path)
            entries.append(
                {
                    "name": path.stem,
                    "file": f"/candidates/{path.name}",
                    "description": (
                        f"Moser ring greedy probe: n={s['n']} e={s['e']} "
                        f"|U|={s['unit_vectors']} denom_power={row['params']['denom_power']} "
                        f"cb={row['params']['coeff_bound']} r={row['params']['visible_radius']}"
                    ),
                    "family": s["family"],
                    "n": s["n"],
                    "e": s["e"],
                    "density": round(s["e"] / s["n"], 4) if s["n"] else 0.0,
                    "unit_vectors": s["unit_vectors"],
                }
            )

    descriptions = {
        "gallery_moser_zeta6_B2": "Z[i, \u03b6_6] (Moser, rank 4)",
        "gallery_moser_zeta12_B2": "Z[i, \u03b6_12] (Moser, rank 4)",
        "gallery_zeta5_R2.5_B6": "Q(\u03b6_5) cut-and-project (rank 4, Penrose-style)",
        "gallery_zeta7_R2.0_B5": "Q(\u03b6_7) cut-and-project (rank 6)",
        "gallery_zeta8_R2.5_B5": "Q(\u03b6_8) cut-and-project (rank 4, octagonal)",
        "gallery_zeta12_R2.5_B5": "Q(\u03b6_12) cut-and-project (rank 4, dodecagonal)",
        "gallery_biq_3_R3.0_B3": "Q(i, sqrt 3) (rank 4)",
        "gallery_erdos_K65_m25": "Erd\u0151s grid K=65, m=25 (best classical baseline at n=625)",
        "gallery_erdos_best_n961": "Erd\u0151s grid (best K-choice at n=961): K=65 m=31",
    }
    for path in sorted(CANDIDATES.glob("gallery_*.json")):
        s = load_candidate_summary(path)
        entries.append(
            {
                "name": path.stem.replace("gallery_", ""),
                "file": f"/candidates/{path.name}",
                "description": descriptions.get(path.stem, path.stem.replace("_", " ")),
                "family": s["family"],
                "n": s["n"],
                "e": s["e"],
                "density": round(s["e"] / s["n"], 4) if s["n"] else 0.0,
                "unit_vectors": s["unit_vectors"],
            }
        )

    MANIFEST.write_text(json.dumps(entries, indent=2))
    print(f"wrote {MANIFEST}  entries={len(entries)}")


if __name__ == "__main__":
    main()
