# %% [markdown]
# # Baseline frontier: known bounds + Erdős grid sweep
#
# Build and visualize the lower-bound frontier we will compare candidates against.
# - n in [1, 30]: curated best-known table (`benchmarks.known_bounds`).
# - n = m^2 for m in [2, 31]: optimized rectangular Z[i] grid at squared
#   distance K, K sweeping squarefree products of primes ≡ 1 (mod 4).
#
# Run as a notebook (jupytext: percent format) or as a plain script.

# %%
from pathlib import Path

import pandas as pd

from eud.benchmarks.compare import build_baseline_frontier
from eud.core.io import write_jsonl
from eud.viz.plot import plot_frontier_density, plot_frontier_n_e

OUT = Path("data/frontiers")

# %%
rows = build_baseline_frontier(n_max=1000)
write_jsonl(rows, OUT / "baseline.jsonl")
print(f"wrote {len(rows)} rows to {OUT / 'baseline.jsonl'}")

# %%
plot_frontier_n_e(rows, OUT / "baseline_n_e.png")
plot_frontier_density(rows, OUT / "baseline_density.png")
print("plots:", OUT / "baseline_n_e.png", OUT / "baseline_density.png")

# %% [markdown]
# Inspect winning K values:

# %%
df = pd.DataFrame(rows)
print(df[df["family"] == "erdos_grid"][["n", "e", "density", "K", "m"]].to_string(index=False))
