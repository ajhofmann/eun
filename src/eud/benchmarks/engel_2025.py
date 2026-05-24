"""Published densest-known UDG counts from Engel et al. (2025).

Source:
    Peter Engel, Owen Hammond-Lee, Yiheng Su, Dániel Varga,
    Pál Zsámboki, "Diverse beam search to find densest-known planar
    unit distance graphs", Experimental Mathematics (2025),
    arXiv:2406.15317, Table 2.

The table gives the highest edge count found for each vertex count
V = 1..100. Exactness is known only for the small values covered by
Alexeev--Mixon--Parshall (through n=21); beyond that these are
published densest-known lower bounds, not proven values of u(n).
"""

from __future__ import annotations

# (n, e, exact?)
ENGEL_2025_BOUNDS: list[tuple[int, int, bool]] = [
    (1, 0, True),
    (2, 1, True),
    (3, 3, True),
    (4, 5, True),
    (5, 7, True),
    (6, 9, True),
    (7, 12, True),
    (8, 14, True),
    (9, 18, True),
    (10, 20, True),
    (11, 23, True),
    (12, 27, True),
    (13, 30, True),
    (14, 33, True),
    (15, 37, True),
    (16, 41, True),
    (17, 43, True),
    (18, 46, True),
    (19, 50, True),
    (20, 54, True),
    (21, 57, True),
    (22, 60, False),
    (23, 64, False),
    (24, 68, False),
    (25, 72, False),
    (26, 76, False),
    (27, 81, False),
    (28, 85, False),
    (29, 89, False),
    (30, 93, False),
    (31, 97, False),
    (32, 101, False),
    (33, 105, False),
    (34, 109, False),
    (35, 114, False),
    (36, 119, False),
    (37, 123, False),
    (38, 128, False),
    (39, 132, False),
    (40, 137, False),
    (41, 141, False),
    (42, 146, False),
    (43, 150, False),
    (44, 155, False),
    (45, 160, False),
    (46, 164, False),
    (47, 169, False),
    (48, 174, False),
    (49, 180, False),
    (50, 183, False),
    (51, 188, False),
    (52, 192, False),
    (53, 197, False),
    (54, 202, False),
    (55, 206, False),
    (56, 211, False),
    (57, 216, False),
    (58, 221, False),
    (59, 226, False),
    (60, 231, False),
    (61, 235, False),
    (62, 240, False),
    (63, 246, False),
    (64, 252, False),
    (65, 256, False),
    (66, 261, False),
    (67, 266, False),
    (68, 271, False),
    (69, 276, False),
    (70, 281, False),
    (71, 286, False),
    (72, 291, False),
    (73, 296, False),
    (74, 301, False),
    (75, 306, False),
    (76, 312, False),
    (77, 317, False),
    (78, 322, False),
    (79, 327, False),
    (80, 332, False),
    (81, 338, False),
    (82, 345, False),
    (83, 350, False),
    (84, 355, False),
    (85, 360, False),
    (86, 365, False),
    (87, 370, False),
    (88, 375, False),
    (89, 380, False),
    (90, 385, False),
    (91, 390, False),
    (92, 396, False),
    (93, 401, False),
    (94, 406, False),
    (95, 412, False),
    (96, 418, False),
    (97, 423, False),
    (98, 429, False),
    (99, 434, False),
    (100, 439, False),
]


def engel_2025_at(n: int) -> int | None:
    """Return Engel et al.'s densest-known edge count at n, if tabulated."""
    for k, e, _ in ENGEL_2025_BOUNDS:
        if k == n:
            return e
    return None


def engel_2025_rows() -> list[dict]:
    """JSONL-ready rows for the published densest-known table."""
    return [
        {
            "family": "engel_2025",
            "source": "engel_2025_beam_search",
            "n": n,
            "e": e,
            "density": e / n,
            "exact": exact,
            "citation": "Engel et al. 2025, Table 2, arXiv:2406.15317",
        }
        for n, e, exact in ENGEL_2025_BOUNDS
    ]
