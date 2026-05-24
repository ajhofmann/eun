# erdos-unit-search

Search and certification toolchain for finding the smallest n where a
non-classical algebraic / cut-and-project construction beats the
strongest available finite Erdős unit-distance lower bounds.

## North star

> Find the smallest n where a higher-rank algebraic / cut-and-project
> construction beats the strongest available finite baseline for u(n).

This is *not* a re-disproof of Erdős - OpenAI/Sawin already do that
asymptotically (n^{1+δ}, δ ≈ 0.014). The deliverable here is the first
satisfying *small* witness, with an exact-arithmetic certificate.

## Architecture

- `src/eud/core/` - lattice points, candidates, edge counting, IO,
  exact algebra, certificates.
- `src/eud/families/` - construction families: `erdos_grid`, `moser`,
  `cyclotomic`, `biquadratic`, generic `cut_project`, `pari_fields`.
- `src/eud/search/` - windows, pruning (greedy / core / local-swap /
  CP-SAT), beam, config-driven experiment runner.
- `src/eud/benchmarks/` - known-bound tables, frontier comparison,
  scoring.
- `src/eud/viz/` - matplotlib plots, web export.
- `configs/` - YAML sweep configs.
- `data/` - generated candidates, frontiers, certificates.
- `web/` - small Vite + React viewer that consumes generated JSON.

## Setup

```bash
make install      # uv sync --all-extras --dev
make test         # pytest
make lint         # ruff
make smoke-moser  # reproduce uploaded Moser demo
make baseline     # build erdos_grid + Moser baseline frontier
make sweep        # run a multi-family search config
make leaderboard  # rank candidates against the frontier
```

## CLI

```bash
eud info
eud version

# Generate a candidate from a family
eud generate --family moser     --coeff-bound 2 --zeta-order 6 --out data/candidates/moser_B2.json --draw data/candidates/moser_B2.png
eud generate --family zeta5     --coeff-bound 6 --R 2.5         --out data/candidates/zeta5_R2.5.json --draw data/candidates/zeta5_R2.5.png
eud generate --family cyclotomic --zeta-order 7 --coeff-bound 4 --R 2.0 --out data/candidates/zeta7.json
eud generate --family biquadratic --primes 3,5  --coeff-bound 2 --R 1.5 --out data/candidates/biq_3_5.json
eud generate --family erdos_grid --K 65 --out data/candidates/grid_K65.json

# Verify (sympy exact + optional cypari2 cross-check)
eud verify data/candidates/zeta5_R2.5.json --pari --out data/verified/zeta5_cert.jsonl

# Prune to a per-k frontier
eud prune data/candidates/zeta5_R2.5.json --k 50,100,200,300 --method local-swap --out data/runs/zeta5_pruned.jsonl

# Build the baseline frontier (known bounds + erdos_grid sweep)
eud baseline --out data/frontiers/baseline.jsonl --n-max 1000

# Compare candidate runs against the frontier
eud compare data/runs/zeta5_pruned.jsonl --frontier data/frontiers/baseline.jsonl

# Run a config-driven sweep
eud search configs/search/biquadratic_rank6.yaml --out data/runs/biquad.jsonl --frontier data/frontiers/baseline.jsonl

# Rank candidates against the frontier
eud leaderboard data/runs/biquad.jsonl --frontier data/frontiers/baseline.jsonl --top 25
```

## Design invariants

1. Every point carries integer coordinates in a fixed lattice basis.
   Floats are for plotting only.
2. Every claimed unit edge is verified by exact algebraic
   squared-distance == 1 before being counted in a record claim.
3. Unit vectors per family are enumerated once (as integer-coefficient
   tuples), then edge counting is `O(n · |U|)` via a hash on
   coefficient tuples.

## Failure modes guarded against

- **Float lies.** Exact arithmetic for every record claim.
- **Weak baseline.** `erdos_grid` uses sum-of-two-squares-rich K, not
  naive square grid; Moser frontier reproduced before any "win" claim.
- **Fixed-degree trap.** Z[ζ_5] is for pipeline validation, not records.
  Real search starts at rank 6.
- **Asymptotic trap.** We search finite *shadows* of the proof, not the
  full Golod-Shafarevich tower.
- **Z-rank degeneracy.** `MoserParams` rejects `zeta_order` values
  (1, 2, 4) where (1, i, ζ, iζ) is Z-linearly dependent and edge counts
  inflate spuriously.

## Strict baseline frontier

`data/frontiers/baseline.jsonl` is the strict best-of-finite-construction
frontier we score every candidate against. At each n in [1, 1000] it
keeps the maximum edge count over four sources:

- **`known_bounds`**: curated literature values for n in [1, 30]
  (Edelsbrunner et al exact values for n ≤ 14; Schade 2020 / OEIS
  A186705-style lower bounds for n in [15, 30]).
- **`erdos_grid`**: rectangular `mx × my` grid sweep with K = product of
  primes ≡ 1 mod 4 (`families/erdos_grid.py`). Square grids are a
  special case but rectangles fill in non-square n. Dominates the
  frontier for n ≳ 270.
- **`triangular`**: Z[ζ_6] (Eisenstein) hex-disk / parallelogram / strip
  sweep with the 6 sixth roots of unity as unit vectors
  (`families/triangular.py`). Closed form on filled hex disks:
  n = 3r² + 3r + 1, e = 9r² + 3r.
- **`moser_hex`**: rank-4 Moser lattice Z[i, ζ] with a visible-plane
  disk window (`families/moser.py:build_in_visible_disk`), greedy-peeled
  to the target n. Dominates the frontier for n in [31, 270].

Build it from scratch (≈7 min for n_max=1000):

```bash
uv run eud baseline --out data/frontiers/baseline.jsonl --n-max 1000
```

## Findings

After re-scoring against the strict baseline above, the rank-4 Q(ζ_12)
cut-and-project construction still cleanly beats every published /
reproducible finite construction at every perfect-square n in [64, 289].
The two smallest n's (36, 49) tie with `moser_hex` because Z[ζ_12] = Z[i, ω]
*is* the Moser lattice — they're the same Z-module, just filtered by
different windows.

Re-running `configs/search/zeta12_window_explore.yaml` (translated /
non-ball windows) and harvesting via `scripts/synthesize_window_explore.py`
produces a stronger "v2" set of wins. Best per n:

| n   | v2 e (Q(ζ_12) winv2) | strict baseline | source     | Δ    | %      | window config                        |
| --- | -------------------- | --------------- | ---------- | ---- | ------ | ------------------------------------ |
| 36  | 111                  | 111             | moser_hex  | +0   | +0.0%  | tied (same lattice as moser_hex)    |
| 49  | 168                  | 168             | moser_hex  | +0   | +0.0%  | tied (same lattice as moser_hex)    |
| 64  | 224                  | 204             | moser_hex  | +20  | +9.8%  | R=2.5 box window, centered          |
| 81  | 292                  | 262             | moser_hex  | +30  | +11.5% | R=2.5 box window, centered          |
| 100 | 380                  | 327             | moser_hex  | +53  | +16.2% | R=3.0 box window, translation_seed=1 |
| 121 | 465                  | 400             | moser_hex  | +65  | +16.3% | R=3.0 box window, translation_seed=1 |
| 144 | 558                  | 478             | moser_hex  | +80  | +16.7% | R=3.0 box window, translation_seed=1 |
| 169 | 662                  | 577             | moser_hex  | +85  | +14.7% | R=3.0 ball window, translation_seed=13 |
| 196 | 782                  | 696             | moser_hex  | +86  | +12.4% | R=3.0 box window, translation_seed=1 |
| 225 | 885                  | 801             | moser_hex  | +84  | +10.5% | R=3.0 ball window, centered (v1)    |
| 256 | 992                  | 921             | moser_hex  | +71  | +7.7%  | R=3.0 ball window, centered (v1)    |
| 289 | 1133                 | 1096            | erdos_grid | +37  | +3.4%  | R=3.0 ball window, centered (v1)    |

Source data:

- [`data/runs/zeta12_winv2_vs_strict.json`](data/runs/zeta12_winv2_vs_strict.json):
  every (k, R, window_kind, translation_seed) winning candidate, plus
  `greedy_e` and `local_swap_e` per row, plus the strict baseline e.
- [`data/runs/zeta12_vs_strict.json`](data/runs/zeta12_vs_strict.json):
  the original "v1" 12-row table re-scored vs the strict baseline.
  10/12 wins still hold; n=36 and n=49 became ties.
- [`data/candidates/winv2_zeta12_n*.json`](data/candidates):
  the v2 candidate snapshots (greedy + local-swap pruned).

### What we tried and what didn't help

- **Higher-rank cyclotomic (m ∈ {15, 20, 24}).** Sweep config:
  [`configs/search/cyclotomic_higher_rank.yaml`](configs/search/cyclotomic_higher_rank.yaml).
  m=15 has 30 roots of unity (vs ζ_12's 12) but rank 8 (vs 4); the
  6-D hidden window is sparse, so coverage drops. Best m=15 candidate
  beats the *strict baseline* at n in {121, 144, 169, 196} but is
  always strictly worse than the corresponding ζ_12 wins. Synthesis:
  [`data/runs/higher_rank_vs_strict.json`](data/runs/higher_rank_vs_strict.json).
- **CP-SAT exact densest-k.** OR-Tools 9.15 multi-worker hangs on this
  hardware (Apple silicon); single-worker with 30 s budget is strictly
  worse than greedy_peel on every k we tried. Greedy_peel + warm-started
  local-swap are the practical pruners on the ζ_12 seed; both equal
  greedy here. Synthesis: [`data/runs/cp_sat_zeta12.jsonl`](data/runs/cp_sat_zeta12.jsonl).
- **Local-swap with random restarts.** With warm start from greedy
  (`SAConfig.warm_start_with_greedy=True`, the default), it never
  improves on greedy at n ≤ 196 on the ζ_12 seed; without warm start it
  is strictly worse.

### Important caveats (still apply)

1. **The literature curated table only covers n ≤ 30.** For n ∈ [31, 60]
   we don't carry tighter Schade-style references; the "strict baseline"
   at those n's is built from our own construction sweeps. New n=49
   and n=36 *do* tie with `moser_hex` though — this is a genuine
   improvement over the previous "vs erdos_grid only" framing.
2. **This is rank 4 not rank 6/8.** Q(ζ_12) = Q(i, √3) is rank 4 over Q
   — same rank as Moser. The wins come from window selection + dense-core
   pruning, not from a higher-rank lattice. We did try higher-rank
   (m ∈ {15, 20, 24}) and they don't beat ζ_12 in our search.
3. **Asymptotic record (Sawin n^{1+1/log²log n})** needs astronomically
   many points; finite shadows like ours are nowhere near that regime.

So this is a "v2 success" against the strict best-of-finite-construction
baseline — every claimed edge is sympy-exact and PARI-cross-verified
([`data/verified/`](data/verified)) — but not a published improvement
over the unknown "true" u(n).

See [`data/gallery/zeta12_wins_frontier.png`](data/gallery/zeta12_wins_frontier.png)
for the visual frontier.

## Notebooks

- [`notebooks/00_reproduce_uploaded_demo.py`](notebooks/00_reproduce_uploaded_demo.py) -
  rank-4 Moser lattice, 12 unit vectors of Z[ζ_12].
- [`notebooks/01_baseline_frontier.py`](notebooks/01_baseline_frontier.py) -
  curated u(n) table + erdos_grid sweep frontier.
- [`notebooks/02_cut_project_windows.py`](notebooks/02_cut_project_windows.py) -
  window-shape sensitivity for Z[ζ_5].

Run any of these as plain scripts: `uv run python notebooks/00_reproduce_uploaded_demo.py`.

## What's next

The toolchain is plumbed end-to-end and the strict baseline is now
multi-family. The remaining open directions:

1. **Curate `known_bounds` for n in [31, 100]** from Schade 2020 and the
   Moser-beam-search literature, so the strict baseline at small n
   isn't entirely construction-derived.
2. **Push past Q(ζ_12) by rank rather than window**: try Q(ζ_15) /
   Q(ζ_24) with ellipsoid windows tuned per Galois conjugate (the
   current sweep used the trivial isotropic ball in 6-D hidden space).
   `configs/search/cyclotomic_higher_rank.yaml` is the starting point.
3. **Fix multi-worker CP-SAT** (Apple silicon hang in OR-Tools 9.15)
   and run exact densest-k at k ≤ 49 to *prove* the v2 wins are
   actually optimal over the seed; the +20 / +30 wins at n=64 / n=81
   would be the easiest cases to verify.
4. **Hybrid union constructions**: Z[ζ_12] ∪ shifted Z[ζ_12] re-pruned
   could in principle exceed the 12-direction density cap of 6.
