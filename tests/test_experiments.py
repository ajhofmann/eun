"""Config-driven experiment runner + leaderboard."""

from __future__ import annotations

from pathlib import Path

from eud.core.io import read_jsonl, write_jsonl
from eud.search.experiments import (
    _expand_param_grid,
    leaderboard,
    run_config,
)


def test_param_grid_cartesian() -> None:
    grid = {"a": [1, 2], "b": ["x", "y"], "c": 3}
    out = _expand_param_grid(grid)
    assert len(out) == 4
    assert all(d["c"] == 3 for d in out)
    assert {(d["a"], d["b"]) for d in out} == {(1, "x"), (1, "y"), (2, "x"), (2, "y")}


def test_run_config_moser_minimal(tmp_path: Path) -> None:
    cfg = tmp_path / "moser.yaml"
    cfg.write_text(
        "name: t\n"
        "family: moser\n"
        "params:\n"
        "  zeta_order: [6]\n"
        "  coeff_bound: [1]\n"
    )
    out = tmp_path / "runs.jsonl"
    run_config(cfg, out)
    rows = list(read_jsonl(out))
    assert len(rows) == 1
    r = rows[0]
    assert r["family"] == "moser"
    assert r["n"] > 0 and r["e"] >= 0


def test_run_config_with_pruning(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "name: t\n"
        "family: moser\n"
        "params:\n"
        "  zeta_order: [6]\n"
        "  coeff_bound: [2]\n"
        "prune:\n"
        "  method: greedy\n"
        "  ks: [10, 25]\n"
    )
    out = tmp_path / "runs.jsonl"
    run_config(cfg, out)
    rows = list(read_jsonl(out))
    assert len(rows) == 1
    pruned = rows[0]["pruned"]
    assert [p["n"] for p in pruned] == [10, 25]


def test_run_config_cyclotomic_grid(tmp_path: Path) -> None:
    cfg = tmp_path / "cyc.yaml"
    cfg.write_text(
        "name: t\n"
        "family: cyclotomic\n"
        "params:\n"
        "  m: 5\n"
        "  coeff_bound: [3]\n"
        "  R: [1.0, 1.5]\n"
        "  window_kind: ball\n"
    )
    out = tmp_path / "runs.jsonl"
    run_config(cfg, out)
    rows = list(read_jsonl(out))
    assert len(rows) == 2  # 2 R values


def test_leaderboard_orders_by_beats_then_improvement(tmp_path: Path) -> None:
    runs = tmp_path / "runs.jsonl"
    write_jsonl(
        [
            {"family": "a", "params": {}, "n": 100, "e": 200, "density": 2.0},
            {"family": "b", "params": {}, "n": 100, "e": 250, "density": 2.5},
            {"family": "c", "params": {}, "n": 50, "e": 80, "density": 1.6},
        ],
        runs,
    )
    frontier = tmp_path / "frontier.jsonl"
    write_jsonl(
        [
            {"family": "fr", "n": 100, "e": 220},
            {"family": "fr", "n": 50, "e": 100},
        ],
        frontier,
    )
    top = leaderboard(runs, frontier_path=frontier, top=10)
    # b beats frontier (250 > 220), a does not (200 < 220), c does not.
    assert top[0]["family"] == "b"
    assert top[0]["beats_frontier"] is True
    assert top[0]["improvement_at_n"] == 30
