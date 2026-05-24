# %% [markdown]
# # Cut-and-project window exploration
#
# For a fixed Z[zeta_5] coefficient box, vary the hidden-space window
# and observe how n and e change. Box / Ball / Ellipsoid windows; random
# translations.

# %%
from pathlib import Path

from eud.families.cyclotomic import CyclotomicParams, build
from eud.viz.draw import draw_candidate
from eud.viz.plot import plot_frontier_n_e

OUT = Path("data/candidates")

# %%
configs = [
    CyclotomicParams(m=5, coeff_bound=6, R=1.5, window_kind="ball"),
    CyclotomicParams(m=5, coeff_bound=6, R=2.0, window_kind="ball"),
    CyclotomicParams(m=5, coeff_bound=6, R=2.5, window_kind="ball"),
    CyclotomicParams(m=5, coeff_bound=6, R=2.0, window_kind="ellipsoid"),
    CyclotomicParams(
        m=5, coeff_bound=6, R=2.0, window_kind="ball", translation_seed=7
    ),
]
rows = []
for p in configs:
    c = build(p)
    rows.append({"family": "zeta5", "kind": p.window_kind, "R": p.R, "n": c.n, "e": c.e})
    print(f"{p.window_kind:10s} R={p.R:.1f} ts={p.translation_seed}: n={c.n} e={c.e}")

# %%
plot_frontier_n_e(
    [{**r, "family": f"{r['kind']}_R{r['R']}"} for r in rows],
    OUT / "zeta5_window_sweep.png",
    title="Z[zeta_5] cut-and-project: e vs n by window",
)

# %% [markdown]
# Visually compare two extremes:

# %%
draw_candidate(build(configs[0]), OUT / "zeta5_ball_R1.5.png")
draw_candidate(build(configs[2]), OUT / "zeta5_ball_R2.5.png")
