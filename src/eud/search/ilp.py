"""Exact densest-k induced subgraph via OR-Tools CP-SAT.

Variables:
    x_i in {0, 1}     for each vertex
    y_{ij} in {0, 1}  for each edge (i, j)

Constraints:
    sum_i x_i = k
    y_{ij} <= x_i,  y_{ij} <= x_j   (linearize AND)

Objective:
    maximize sum y_{ij}

Practical for n up to ~1000 vertices and moderate k.
"""

from __future__ import annotations

from dataclasses import dataclass

from eud.core.pointset import Candidate


@dataclass
class CPSATConfig:
    """Parameters for the CP-SAT exact densest-k solver."""

    time_limit_s: float = 60.0
    workers: int = 8
    seed: int = 0
    log_search: bool = False


def cp_sat_densest_k(
    candidate: Candidate,
    k: int,
    *,
    config: CPSATConfig | None = None,
) -> tuple[Candidate, dict]:
    """Solve the densest k-induced-subgraph problem on `candidate`.

    Returns `(induced_subgraph, info)` where `info` includes the solver
    status, objective value, wall time, and best bound.
    """
    from ortools.sat.python import cp_model

    config = config or CPSATConfig()
    n = candidate.n
    if k <= 0:
        return candidate.induced_subgraph([]), {"status": "trivial"}
    if k >= n:
        return candidate, {"status": "trivial"}

    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x_{i}") for i in range(n)]
    model.Add(sum(x) == k)

    obj_terms = []
    for i, j in candidate.edges:
        y = model.NewBoolVar(f"y_{i}_{j}")
        model.Add(y <= x[i])
        model.Add(y <= x[j])
        model.Add(y >= x[i] + x[j] - 1)
        obj_terms.append(y)

    model.Maximize(sum(obj_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.time_limit_s
    solver.parameters.num_search_workers = config.workers
    solver.parameters.random_seed = config.seed
    solver.parameters.log_search_progress = config.log_search

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return candidate.induced_subgraph([]), {
            "status": solver.StatusName(status),
            "objective": None,
            "wall_time_s": solver.WallTime(),
        }

    chosen = [i for i in range(n) if solver.Value(x[i]) == 1]
    info = {
        "status": solver.StatusName(status),
        "objective": int(solver.ObjectiveValue()),
        "best_bound": int(solver.BestObjectiveBound()),
        "wall_time_s": solver.WallTime(),
        "optimal": status == cp_model.OPTIMAL,
    }
    return candidate.induced_subgraph(sorted(chosen)), info
