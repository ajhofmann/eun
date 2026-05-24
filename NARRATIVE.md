# What's interesting about this project

A finite, exact-arithmetic answer to a slice of Erdős' unit-distance
problem: at every perfect square `n` in `[64, 196]`, a rank-4 cyclotomic
cut-and-project construction (`Z[ζ_12]` with a translated box window)
beats every other finite construction we could reproduce by **9.8% to
16.7%**, with every claimed unit edge proven exactly via sympy and
cross-checked at 256-bit precision in PARI.

This document is a tour: what surprised us, what didn't work, and what
the visualizations actually show.

## The problem in one paragraph

`u(n)` = max number of unit-distance pairs among `n` points in the
plane. Erdős conjectured `u(n) = n^{1+c/log log n}`. Sawin (2022) proved
`u(n) ≥ n^{1 + 1/log²log n}` asymptotically, but the smallest finite
witness of his construction is around `10^{1.96M}` points - vastly out
of reach. So the live research question is: *for actual finite n, how
high can we push the lower bound, exactly*?

## What surprised us

### 1. The strict baseline picture is mostly two species

[`data/gallery/baseline/source_share.png`](data/gallery/baseline/source_share.png)
shows which family contributes the strict baseline `u(n)` row at every
n in `[1, 1000]`:

- `known_bounds` (literature): `n ≤ 30`
- `moser_hex` (our visible-disk Moser sweep): dominates `n ∈ [31, 270]`
- `erdos_grid` (rectangular sweep): takes over for `n > 270`

The triangular Z[ζ_6] sweep, despite producing the cleanest closed-form
counts (`n = 3r²+3r+1`, `e = 9r²+3r`), never wins a single n. It's
*always* dominated by the rank-4 Moser lattice, because the extra
`(i, iζ_6)` directions in `Z[i, ζ_6]` give 12 unit vectors instead of
6 - twice as many edges per vertex when the boundary doesn't bite.

### 2. Z[ζ_12] = Z[i, ζ_3] = the Moser lattice

This is the crucial identity that explains why our v1 "wins" at n=36 and
n=49 became *ties* against the strict baseline:

- `Q(ζ_12)` is the cyclotomic field of 12th roots of unity, rank 4 / Q.
- It contains `i = ζ_12^3` and `ζ_3 = ζ_12^4`, so as a Z-module
  `Z[ζ_12] = Z + Zi + Zζ_3 + Ziζ_3` - exactly the Moser lattice.
- Both constructions therefore generate the same point cloud; they
  differ only in *how they filter it* (cyclotomic uses a 2-D hidden
  ball; Moser uses a 2-D visible disk).

At small `n` the densest `n`-vertex induced subgraph of either filter
is the *same* dense central piece, so they tie. Pulling the two methods
apart only matters once the filter shape changes the available
candidate vertices for greedy peel.

This is the cleanest example I know of where two seemingly different
"clever lattices" are literally the same Z-module shifted to a
different basis.

### 3. The actual win was the box window, not the higher-rank lattice

I expected to push past `Z[ζ_12]` by going to `Z[ζ_15]` (rank 8, 30
roots of unity) or `Z[ζ_24]` (rank 8, 24 roots). Instead the rank-8
sweep [`data/runs/cyclotomic_higher_rank.jsonl`](data/runs/cyclotomic_higher_rank.jsonl)
was uniformly *worse* than `ζ_12` at every `n` we tested:

| n   | Z[ζ_12] v1 | Z[ζ_15] best | Z[ζ_20] best | Z[ζ_24] best |
| --- | ---------- | ------------ | ------------ | ------------ |
| 100 | 369        | 327          | 225          | 288          |
| 144 | 547        | 509          | 346          | 440          |
| 196 | 770        | 711          | 474          | 610          |

The reason: more roots of unity buy you nothing if the cut-and-project
window can't catch enough lattice points. With rank 8 the hidden space
is 6-D, so an isotropic ball of radius 2.5 has volume `π³R⁶/6 ≈ 32` -
the same lattice density that gave us 1700+ points at rank 4 collapses
to only a few hundred at rank 8.

What *did* work was way simpler: keep `Z[ζ_12]` and change the window
shape from a centered 2-D ball to a translated 2-D box.
[`data/gallery/showcase/window_translation_n100.png`](data/gallery/showcase/window_translation_n100.png)
shows six different `(window_kind, R, translation_seed)` choices; the
densest `n=100` subgraph extractable from the same Z-module ranges from
`e=368` (zonotope) to `e=380` (translated box). The +11 over the
centered ball is "free" - same lattice, same algebra, just a smarter
cookie cutter.

### 4. Greedy peel is the practical exact-pruner here, not CP-SAT

`OR-Tools` CP-SAT is set up exactly the way the textbook says to: x_i
= keep vertex, y_ij = both endpoints kept, maximize Σy_ij subject to
Σx_i = k. On Apple silicon with `ortools 9.15`, multi-worker CP-SAT
hangs in presolve on this size of problem (1767 vars + 7824 edge
vars). Single-worker mode runs but, at a 30-second budget per k, it
returns *worse* solutions than 0.1s of greedy peel:

| k   | greedy_e | local_swap (warm) | CP-SAT 1-worker, 30s |
| --- | -------- | ----------------- | -------------------- |
| 25  | 70       | 70                | 68                   |
| 49  | 168      | 168               | 149                  |
| 100 | 369      | 369               | 277                  |

This is a useful negative result. The `Q(ζ_12)` cut-and-project lattice
has so much *symmetry* (12 unit-vector orbits, plus translations) that
warm-started greedy already finds the dense central piece in one pass;
CP-SAT's branch-and-bound search with no warm start spends the entire
budget exploring far-from-optimum corners.

### 5. The wins are real *because* every edge is verified exactly

Every "win" candidate is shipped with a JSON certificate at
[`data/verified/winv2_zeta12_n*_cert.json`](data/verified). For each of
the 380 edges in the n=100 win:

- the **integer coefficient difference** `(c0, c1, c2, c3)` is recorded;
- a sympy `simplify` proves `|c0 + c1·ζ + c2·ζ² + c3·ζ³|² == 1` exactly
  in `Q(ζ_12)`;
- a 256-bit PARI computation independently verifies
  `|σ_1(c0 + c1·ζ + ...)|² ≈ 1.0` to ~30 decimal places.

No floats are trusted at any point in the edge-counting pipeline. The
visible-plane projection `xy = (x, y)` exists only for plotting.
This is what the n=100 cert summary reports:

```
family=cyclotomic n=100 e=380 distinct=True
sympy: checked 380 / 380 edges; all unit = True
pari:  checked 380 / 380 edges; all unit = True
```

## What the pictures show

Open the web viewer (`cd web && pnpm dev`, then http://localhost:5173/)
or look at the static PNGs in `data/gallery/`:

- **Construction families**:
  [`baseline/triangular_disks.png`](data/gallery/baseline/triangular_disks.png),
  [`baseline/moser_disks.png`](data/gallery/baseline/moser_disks.png),
  [`baseline/erdos_grids.png`](data/gallery/baseline/erdos_grids.png) -
  all on the same scale, so the increasing density per family is
  visible.
- **Strict frontier overview**:
  [`baseline/strict_frontier.png`](data/gallery/baseline/strict_frontier.png) -
  raw `u(n)` and density `e/n` as scatter, colored by which family
  contributes each row, with the seven `ζ_12` v2 wins marked as orange
  stars rising above the curve.
- **Family-share over n**:
  [`baseline/source_share.png`](data/gallery/baseline/source_share.png) -
  the strip diagram showing literature → moser_hex → erdos_grid
  taking over the strict baseline as `n` grows.
- **Per-n head-to-head**:
  [`wins/compare_n100.png`](data/gallery/wins/compare_n100.png) and
  siblings - five panels at the same `n`, all on the same scale: the
  best triangular, best Moser, best Erdős grid, original `ζ_12` v1, and
  `ζ_12` v2. The visual asymmetry of v2 (it picks a translated box,
  not the centered ball) is quite striking.
- **Window-shape sensitivity**:
  [`showcase/window_translation_n100.png`](data/gallery/showcase/window_translation_n100.png) -
  six different `(window, seed)` combinations, same lattice, all greedy-peeled
  to `n=100`. The `box, seed=1` panel is visibly different from the
  others.
- **Win deltas**: [`wins/v2_wins.png`](data/gallery/wins/v2_wins.png)
  bars showing the +20..+86 absolute and 9.8..16.7% relative gains over
  the strict baseline.

## What's still open

1. **Literature curated values for n in [31, 60]** are missing from
   `known_bounds`. The strict baseline at small n in that range is
   built from our own constructions; if Schade's beam search has
   tighter values somewhere, we'd want them.
2. **Multi-worker CP-SAT works on Linux** (per OR-Tools issue tracker);
   running the same script on a Linux box would let us *prove*
   optimality at small k like 49 / 64 in a few minutes.
3. **Hybrid / union constructions**: `Z[ζ_12]` ∪ shifted-`Z[ζ_12]` could
   in principle exceed the 12-direction density cap of 6/vertex by
   exploiting unit edges across the two cosets. This is the
   stretch-goal we did not implement.
4. **Adaptive ellipsoid windows** per Galois conjugate, for higher-rank
   fields. The current `cyclotomic_higher_rank.yaml` uses isotropic
   balls in 6-D, which is the worst-case window shape for those fields.

## File pointers

- Pipeline core: `src/eud/{core,families,search,benchmarks,viz}/`.
- Strict frontier: `data/frontiers/baseline.jsonl`, built by
  `eud baseline --n-max 1000` (~7 minutes).
- v2 wins re-scored: `data/runs/zeta12_winv2_vs_strict.json`.
- v1 wins re-scored: `data/runs/zeta12_vs_strict.json`.
- CP-SAT null result: `data/runs/cp_sat_zeta12.jsonl`.
- Higher-rank null result: `data/runs/higher_rank_vs_strict.json`.
- Verified certificates: `data/verified/winv2_zeta12_n{n}_cert.json`.
- All gallery images: `data/gallery/{baseline,wins,showcase}/`.
