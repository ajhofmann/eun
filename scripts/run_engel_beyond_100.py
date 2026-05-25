"""Generate certified Engel-Moser candidates beyond Engel et al. Table 2."""

from __future__ import annotations

import subprocess
import sys

K_VALUES = "121,144,169,196,225,289"


def main() -> None:
    cmd = [
        sys.executable,
        "scripts/reproduce_engel_2025.py",
        "--k-values",
        K_VALUES,
        "--prefix",
        "engel_moser_beyond",
        "--summary",
        "data/runs/engel_moser_beyond_100_tail.json",
        "--max-coeff-bound",
        "4",
        "--max-visible-radius",
        "5.0",
        "--beam-width",
        "24",
        "--beam-rounds",
        "16",
        "--beam-seeds",
        "3",
    ]
    subprocess.run(cmd, check=True)
    subprocess.run([sys.executable, "scripts/summarize_engel_beyond_100.py"], check=True)


if __name__ == "__main__":
    main()
