"""Config-driven experiment runner.

A YAML config describes:
- which family to sweep (moser | cyclotomic | biquadratic | erdos_grid)
- a Cartesian-product grid of params (coeff_bound, R, window_kind, ...)
- optional pruning step (greedy / core / local-swap / cp-sat)
- optional comparison against a frontier file

Each generated candidate gets one row in the output JSONL, with metadata
about the run, params, and (if pruning is used) the per-k frontier curve.
"""

from __future__ import annotations

import itertools
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from eud.benchmarks.compare import load_frontier
from eud.benchmarks.score import improvement, is_record
from eud.core.io import append_jsonl, read_jsonl, write_jsonl
from eud.core.pointset import Candidate
from eud.search.local_search import SAConfig, local_swap
from eud.search.prune import core_peel, greedy_peel


def _load_config(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text()
    return yaml.safe_load(text)


def _build_one(family: str, params: dict[str, Any]) -> Candidate:
    """Dispatch to the per-family `build` with a params dict."""
    if family == "moser":
        from eud.families.moser import MoserParams
        from eud.families.moser import build as build_fn

        return build_fn(MoserParams(**params))
    if family == "engel_moser":
        from eud.families.engel_moser import EngelMoserParams
        from eud.families.engel_moser import build as build_fn

        return build_fn(EngelMoserParams(**params))
    if family == "moser_ring":
        from eud.families.moser_ring import MoserRingParams
        from eud.families.moser_ring import build as build_fn

        return build_fn(MoserRingParams(**params))
    if family == "cyclotomic":
        from eud.families.cyclotomic import CyclotomicParams
        from eud.families.cyclotomic import build as build_fn

        return build_fn(CyclotomicParams(**params))
    if family == "biquadratic":
        from eud.families.biquadratic import BiquadraticParams
        from eud.families.biquadratic import build as build_fn

        if "primes" in params and isinstance(params["primes"], list):
            params = {**params, "primes": tuple(params["primes"])}
        return build_fn(BiquadraticParams(**params))
    if family == "erdos_grid":
        from eud.families.erdos_grid import ErdosGridParams
        from eud.families.erdos_grid import build as build_fn

        return build_fn(ErdosGridParams(**params))
    raise ValueError(f"unknown family: {family}")


def _expand_param_grid(grid: dict[str, Any]) -> list[dict[str, Any]]:
    """Cartesian product over list-valued entries in `grid`."""
    keys: list[str] = []
    values: list[list[Any]] = []
    for k, v in grid.items():
        keys.append(k)
        values.append(v if isinstance(v, list) else [v])
    out: list[dict[str, Any]] = []
    for combo in itertools.product(*values):
        out.append(dict(zip(keys, combo, strict=True)))
    return out


def _maybe_prune(c: Candidate, prune_cfg: dict[str, Any] | None) -> list[dict]:
    """Run a pruner per k, return list of pruned candidate summary rows."""
    if not prune_cfg:
        return []
    method = prune_cfg.get("method", "greedy")
    ks = prune_cfg.get("ks", [])
    rows: list[dict] = []
    for k in ks:
        if method == "greedy":
            sub = greedy_peel(c, k)
        elif method == "core":
            sub = core_peel(c, k)
        elif method == "local-swap":
            sub = local_swap(
                c,
                k,
                config=SAConfig(
                    max_iters=prune_cfg.get("iters", 5000),
                    seed=prune_cfg.get("seed", 0),
                    restarts=prune_cfg.get("restarts", 1),
                ),
            )
        elif method == "cp-sat":
            from eud.search.ilp import CPSATConfig, cp_sat_densest_k

            sub, _ = cp_sat_densest_k(
                c,
                k,
                config=CPSATConfig(
                    time_limit_s=prune_cfg.get("time_limit_s", 60.0),
                    workers=prune_cfg.get("workers", 1),
                    seed=prune_cfg.get("seed", 0),
                ),
            )
        else:
            raise ValueError(f"unknown prune method: {method}")
        rows.append(
            {
                "method": method,
                "n": sub.n,
                "e": sub.e,
                "density": sub.density,
            }
        )
    return rows


def run_config(
    config_path: str | Path,
    out_path: str | Path,
    *,
    frontier_path: str | Path | None = None,
) -> Path:
    """Run a config-driven sweep, appending one JSONL row per candidate."""
    cfg = _load_config(config_path)
    family = cfg["family"]
    grid = cfg.get("params", {})
    prune_cfg = cfg.get("prune")
    name = cfg.get("name", "sweep")

    out = Path(out_path)
    if out.exists():
        out.unlink()

    frontier = None
    if frontier_path is not None and Path(frontier_path).exists():
        frontier = load_frontier(frontier_path)

    started_at = datetime.now(tz=UTC).isoformat()
    rows_written = 0
    for params in _expand_param_grid(grid):
        t0 = time.time()
        try:
            cand = _build_one(family, params)
        except Exception as exc:  # pragma: no cover
            append_jsonl(
                {
                    "name": name,
                    "family": family,
                    "params": params,
                    "error": str(exc),
                    "wall_time_s": time.time() - t0,
                    "started_at": started_at,
                },
                out,
            )
            continue

        row: dict[str, Any] = {
            "name": name,
            "family": family,
            "params": params,
            "n": cand.n,
            "e": cand.e,
            "density": cand.density,
            "n_units": len(cand.unit_vectors),
            "wall_time_s": time.time() - t0,
            "started_at": started_at,
        }
        if frontier is not None:
            row["frontier_e_at_n"] = frontier.best_edges_at(cand.n)
            row["improvement_at_n"] = improvement(cand, frontier)
            row["beats_frontier"] = is_record(cand, frontier)

        if prune_cfg:
            row["pruned"] = _maybe_prune(cand, prune_cfg)

        append_jsonl(row, out)
        rows_written += 1
    return out


def leaderboard(
    runs_path: str | Path,
    *,
    frontier_path: str | Path | None = None,
    top: int = 25,
) -> list[dict]:
    """Build a leaderboard from one or more JSONL run files.

    Sorts by:
      1. beats_frontier desc
      2. improvement_at_n desc (where defined)
      3. density desc
      4. n asc

    If `frontier_path` is provided, recomputes `improvement_at_n` and
    `beats_frontier` from the (potentially updated) frontier.
    """
    rows = list(read_jsonl(runs_path))
    if frontier_path is not None:
        fr = load_frontier(frontier_path)
        for r in rows:
            if "n" not in r or "e" not in r:
                continue
            base = fr.best_edges_at(r["n"])
            r["frontier_e_at_n"] = base
            r["improvement_at_n"] = (r["e"] - base) if base is not None else None
            r["beats_frontier"] = base is not None and r["e"] > base

    def key(r: dict) -> tuple:
        beats = bool(r.get("beats_frontier"))
        improv = r.get("improvement_at_n") or 0
        density = r.get("density") or 0.0
        n = r.get("n") or 10**18
        return (-int(beats), -improv, -density, n)

    rows = [r for r in rows if "n" in r and "e" in r]
    rows.sort(key=key)
    return rows[:top]


def write_leaderboard(
    runs_path: str | Path,
    out_path: str | Path,
    *,
    frontier_path: str | Path | None = None,
    top: int = 25,
) -> Path:
    rows = leaderboard(runs_path, frontier_path=frontier_path, top=top)
    return write_jsonl(rows, out_path)
