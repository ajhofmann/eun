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

## Initial findings

A run of `configs/search/scan_cyclotomic.yaml` followed by greedy peeling
turned up a clean window where a **rank-4 cut-and-project construction
beats the optimized Erdős square-grid baseline** at every perfect-square
n in [36, 289]:

| n   | Z[ζ_12] greedy-pruned | Erdős grid (best K) | Δ      | %      |
| --- | --------------------- | ------------------- | ------ | ------ |
| 36  | 111                   | 80                  | +31    | +38.8% |
| 49  | 168                   | 120                 | +48    | +40.0% |
| 64  | 223                   | 168                 | +55    | +32.7% |
| 81  | 291                   | 224                 | +67    | +29.9% |
| 100 | 369                   | 288                 | +81    | +28.1% |
| 121 | 453                   | 360                 | +93    | +25.8% |
| 144 | 547                   | 440                 | +107   | +24.3% |
| 169 | 656                   | 528                 | +128   | +24.2% |
| 196 | 770                   | 624                 | +146   | +23.4% |
| 225 | 885                   | 744                 | +141   | +19.0% |
| 256 | 992                   | 912                 | +80    | +8.8%  |
| 289 | 1133                  | 1096                | +37    | +3.4%  |

The construction: build `Q(ζ_12)` (= Z[i, √3], rank 4) cut-and-project
with `coeff_bound=4, R=3.0, ball window`, then `greedy_peel` to the
target `n`. Every claimed unit edge is verified exactly via sympy AND
cross-verified by high-precision PARI in
`data/verified/win_zeta12_n100_cert.json`.

### Important caveats

1. **This beats *our reproduction* of the Erdős square-grid baseline.**
   It is not a claim against the strongest known finite construction
   in the literature. Our `benchmarks/known_bounds.py` only curates
   tighter values up to n=30; for n≥36 the only reference here is
   `erdos_grid`. Recent Schade (2020) / forbidden-subgraph constructions
   for n in [16, 30] beat us soundly there (-4 to -17 edges per n).
2. **This is rank 4, not rank 6/8.** The plan called rank-4 cyclotomic
   "for pipeline validation, not records." Q(ζ_12) is rank 4 over Q
   (= Q(i, √3)) — same rank as Moser. The win comes from window
   selection + dense-core pruning, not from a higher-rank lattice.
3. **It is finite, not asymptotic.** Sawin's exponent δ ≈ 0.014 needs
   astronomically many points to manifest; we are nowhere near that.

So this is a "v2 success" per the plan — smallest n where our pipeline
beats the optimized erdős-grid baseline — not a publishable improvement
over u(n) at large. The path to "publishable" is curating known_bounds
for n ≥ 30 (Moser-beam-search results, Schade-style constructions),
then running rank-6/8 sweeps with local-swap or CP-SAT pruning.

See `data/gallery/zeta12_wins_frontier.png` for the visual frontier.

## Notebooks

- [`notebooks/00_reproduce_uploaded_demo.py`](notebooks/00_reproduce_uploaded_demo.py) -
  rank-4 Moser lattice, 12 unit vectors of Z[ζ_12].
- [`notebooks/01_baseline_frontier.py`](notebooks/01_baseline_frontier.py) -
  curated u(n) table + erdos_grid sweep frontier.
- [`notebooks/02_cut_project_windows.py`](notebooks/02_cut_project_windows.py) -
  window-shape sensitivity for Z[ζ_5].

Run any of these as plain scripts: `uv run python notebooks/00_reproduce_uploaded_demo.py`.

## What's next

The toolchain is plumbed end-to-end. The actual research question -
"smallest n where a higher-rank algebraic / cut-and-project construction
beats the strongest known finite Erdős unit-distance lower bound" -
is now an experimental search, not an engineering question:

1. Extend `benchmarks.known_bounds` with more curated frontiers
   (Moser-lattice beam search to n=100, recent forbidden-subgraph
   bounds for n in [16, 30]).
2. Run the sweep configs (`configs/search/*.yaml`) at scale and harvest
   leaderboard hits with non-trivial `improvement_at_n`.
3. For each hit, run `eud verify --pari` and snapshot the certificate
   in `data/verified/`.
4. Iterate windows / fields / pruning strategy as guided by which
   families and (n, e/n) regions are surfacing wins.
