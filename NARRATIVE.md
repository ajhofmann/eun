# What we learned

This repo now has a more honest answer than the first pass:

**Z[ζ_12] with translated box windows is a strong reproducible construction,
but it is not published finite SOTA.** It beats the construction baseline we
could reproduce locally, but Engel--Hammond-Lee--Su--Varga--Zsámboki (2025)
beat it at every n≤100 where they publish a table.

The project is still useful: it found a real window-selection improvement,
shipped exact certificates, exposed a bug in our small-n benchmark table, and
identified the correct next target: Engel's 18-unit Moser lattice / ring.

## The honest scorecard

Best Z[ζ_12] candidate vs our reproducible baseline and Engel et al. 2025:

| n   | Z[ζ_12] best | reproducible baseline | Δ repro | Engel 2025 | Δ SOTA |
| --- | ------------ | --------------------- | ------- | ---------- | ------ |
| 36  | 111          | 111                   | +0      | 119        | -8     |
| 49  | 168          | 168                   | +0      | 180        | -12    |
| 64  | 224          | 204                   | +20     | 252        | -28    |
| 81  | 292          | 262                   | +30     | 338        | -46    |
| 100 | 380          | 327                   | +53     | 439        | -59    |
| 121 | 465          | 400                   | +65     | n/a        | n/a    |
| 144 | 558          | 478                   | +80     | n/a        | n/a    |
| 169 | 662          | 577                   | +85     | n/a        | n/a    |
| 196 | 782          | 696                   | +86     | n/a        | n/a    |

So the claim is:

- **Yes:** Z[ζ_12] v2 beats our reproducible baseline at n=64..196.
- **No:** Z[ζ_12] v2 does not beat published finite SOTA for n≤100.
- **Unknown from this table:** n>100, because Engel et al.'s published Table 2
  stops at 100, though their density trend suggests their beam-search family
  likely remains ahead.

Source data: [`data/runs/zeta12_vs_published_sota.json`](data/runs/zeta12_vs_published_sota.json).

## The benchmark bug we fixed

The old `known_bounds.py` carried several impossible values for n=16..21
(for example n=18 had 49 and n=21 had 61). Alexeev--Mixon--Parshall (2025)
prove exact values through n=21:

```text
n:  15  16  17  18  19  20  21
u:  37  41  43  46  50  54  57
```

We corrected [`src/eud/benchmarks/known_bounds.py`](src/eud/benchmarks/known_bounds.py)
and added [`src/eud/benchmarks/engel_2025.py`](src/eud/benchmarks/engel_2025.py),
which carries Engel et al. Table 2 for n=1..100.

The baseline files now mean:

- [`data/frontiers/baseline_reproducible.jsonl`](data/frontiers/baseline_reproducible.jsonl):
  our local construction-only frontier.
- [`data/frontiers/baseline.jsonl`](data/frontiers/baseline.jsonl):
  published-SOTA-aware frontier: Engel 2025 through n=100, then local
  reproducible constructions beyond that.

## Why Engel beats us

Our successful family is `Q(ζ_12) = Z[ζ_12]`, a rank-4 cyclotomic lattice.
It has 12 unit vectors, so an interior point can have degree at most 12 and
the density cap is 6 edges per vertex.

Engel et al. use a different rank-4 lattice:

```text
M_L = Z<1, ω1, ω3, ω1ω3>
ω1 = exp(iπ/3)
ω3 = exp(i arccos(5/6))
```

They prove this lattice has exactly **18 unit vectors**, so the local degree
cap is 18 and the density cap is 9. That extra angular structure is the
missing ingredient. Their diverse beam search then uses operations like single
edge addition, triangle completion, parallelogram completion, canonization,
and visitation penalties to find dense subgraphs up to n=100.

We added this family as [`src/eud/families/engel_moser.py`](src/eud/families/engel_moser.py).
It enumerates the 18 unit vectors using Engel et al.'s exact criterion:

```text
p(a,b,c,d) = 1 and ad = bc
```

where `p` is the rational quadratic form from their Theorem 2.5. This is now
the right family to attack if we want to reproduce or improve SOTA.

## First attempt at the right family

After adding `engel_moser`, a simple visible-disk + local-swap probe already
got close to Engel et al.'s Table 2. Adding a coefficient-space beam with
boundary, triangle-completion, parallelogram-completion, translation
canonization, and diversity penalties now matches 5 of the 6 checked values:

| n   | our Engel probe | Engel 2025 | gap |
| --- | --------------- | ---------- | --- |
| 25  | 72              | 72         | 0   |
| 36  | 119             | 119        | 0   |
| 49  | 180             | 180        | 0   |
| 64  | 251             | 252        | -1  |
| 81  | 338             | 338        | 0   |
| 100 | 439             | 439        | 0   |

This is the most encouraging result in the corrected run. It says the lattice
is indeed the missing ingredient; the remaining gap is likely Engel's
full child/canonization machinery rather than geometry. The reproduction data
lives in [`data/runs/engel_moser_reproduce.json`](data/runs/engel_moser_reproduce.json).

Beyond Engel et al.'s published n≤100 table, the same 18-unit family already
beats the repo's fallback frontier by large margins:

| n   | Engel-Moser beam | fallback frontier | Δ fallback |
| --- | ---------------- | ----------------- | ---------- |
| 121 | 557              | 400               | +157       |
| 144 | 692              | 478               | +214       |
| 169 | 835              | 577               | +258       |
| 196 | 994              | 696               | +298       |
| 225 | 1161             | 801               | +360       |
| 289 | 1572             | 1096              | +476       |

These are not literature-SOTA claims beyond n=100; they show that our old
fallback baseline should be replaced by Engel-Moser once the public table ends.
Source data: [`data/runs/engel_moser_beyond_100.json`](data/runs/engel_moser_beyond_100.json).

We also added a bounded common-denominator Moser ring model. At denominator
`3^1` it exposes 42 exact unit directions (versus 18 in the lattice), and at
`3^2` our bounded enumeration finds 66. The first greedy probe is weaker than
Engel's search, so the lesson is "more unit directions are available, but the
ring needs better children/windows before it becomes a record engine."

## What remains interesting about Z[ζ_12]

The ζ_12 result is not SOTA, but it is still a good pipeline result:

1. **Window shape mattered.** A translated box window improved the centered
   ball window at n=100 from 369 to 380 edges. Same lattice, same algebra,
   smarter finite cut.
2. **Every edge is exact.** The v2 certificates in [`data/verified/`](data/verified)
   prove each edge with sympy and cross-check with PARI.
3. **Higher-rank cyclotomic was a null result.** Rank-8 fields such as ζ_15,
   ζ_20, ζ_24 have more roots of unity, but the 6-D hidden window is too sparse.
4. **CP-SAT was not competitive here.** OR-Tools multi-worker hangs on Apple
   silicon; single-worker CP-SAT underperforms greedy peel on these symmetric
   graphs.

## Visual guide

- [`data/gallery/sota/published_vs_ours.png`](data/gallery/sota/published_vs_ours.png):
  the corrected headline plot. Z[ζ_12] beats the reproducible baseline but
  trails Engel 2025 through n=100.
- [`data/gallery/sota/gap_to_engel.png`](data/gallery/sota/gap_to_engel.png):
  the negative SOTA gap: -8, -12, -28, -46, -59 at n=36,49,64,81,100.
- [`data/gallery/showcase/window_translation_n100.png`](data/gallery/showcase/window_translation_n100.png):
  same Z[ζ_12] lattice, six windows, different dense subgraphs.
- [`data/gallery/wins/compare_n100.png`](data/gallery/wins/compare_n100.png):
  local family comparison at fixed n.

## What to do next

1. **Close the n=64 Engel gap.** We now match 5/6 Table 2 checkpoints; the
   remaining one-edge miss is the best diagnostic target for missing child
   moves or stronger canonization.
2. **Promote Engel-Moser into the baseline beyond n=100.** The fallback
   frontier is now visibly too weak at n=121..289.
3. **Improve the Moser ring search.** The ring has >18 unit directions in the
   common-denominator model, but the first greedy windows do not exploit them.
4. **Use Linux for CP-SAT.** The Apple-silicon OR-Tools hang is a tooling issue;
   exact densest-k could still be valuable on smaller induced seeds.
5. **Keep both baselines visible.** Reproducible baseline tells us what our
   code can currently construct; published SOTA tells us what we must beat.
