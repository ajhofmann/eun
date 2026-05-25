"""Copy near-n=545 compare JSON into web/public for GitHub Pages."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CANDIDATES = REPO / "data" / "candidates"
OUT_DIR = REPO / "web" / "public" / "demo" / "near545"
HERO_SRC = REPO / "data" / "gallery" / "wins" / "shareable_unpeeled_uploaded_grid_engel_near545.png"

COPY_MAP: tuple[tuple[Path, str], ...] = (
    (CANDIDATES / "uploaded_moser_disk_B2_R4.json", "uploaded_moser_disk_B2_R4.json"),
    (
        CANDIDATES / "x_compare_erdos_grid_K65_20x27_n540.json",
        "erdos_grid_K65_20x27_n540.json",
    ),
    (
        CANDIDATES / "x_compare_engel_moser_unpeeled_n543.json",
        "engel_moser_unpeeled_n543.json",
    ),
    (
        CANDIDATES / "x_compare_erdos_grid_K65_n545_peeled.json",
        "erdos_grid_K65_n545_peeled.json",
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hero",
        action="store_true",
        help="Also copy shareable PNG to web/public/demo/near545/hero.png",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    missing_both: list[str] = []
    for src, dest_name in COPY_MAP:
        dest = OUT_DIR / dest_name
        if src.is_file():
            shutil.copy2(src, dest)
            print(f"copied {dest.relative_to(REPO)}")
            continue
        if dest.is_file():
            print(f"using committed {dest.relative_to(REPO)}")
            continue
        missing_both.append(dest_name)

    if missing_both:
        raise SystemExit(
            "missing demo JSON (commit web/public/demo/near545/ or generate "
            "data/candidates and re-run):\n  "
            + "\n  ".join(missing_both)
        )

    if args.hero:
        hero_dest = OUT_DIR / "hero.png"
        if HERO_SRC.is_file():
            shutil.copy2(HERO_SRC, hero_dest)
            print(f"copied {hero_dest.relative_to(REPO)}")
        elif hero_dest.is_file():
            print(f"using committed {hero_dest.relative_to(REPO)}")
        else:
            raise SystemExit(f"missing hero PNG: {HERO_SRC}")

    print(f"done — demo bundle in {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
