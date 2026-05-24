# %% [markdown]
# # Reproduce the uploaded Moser-style demo
#
# Build the rank-4 Moser lattice Z + Zi + Z*zeta + Zi*zeta with zeta = e^{i*pi/3},
# coefficients in {-2, ..., 2}, and render it. This reproduces the
# 12-fold-symmetric dodecagonal pattern from the uploaded sketch.

# %%
from pathlib import Path

from eud.core.io import write_candidate
from eud.families.moser import MoserParams, build
from eud.viz.draw import draw_candidate

OUT = Path("data/candidates")

# %%
params = MoserParams(zeta_order=6, coeff_bound=2)
candidate = build(params)
print(
    f"family={candidate.family} n={candidate.n} e={candidate.e} "
    f"e/n={candidate.density:.3f} |U|={len(candidate.unit_vectors)}"
)

# %%
write_candidate(candidate, OUT / "moser_box_B2.json")
draw_candidate(candidate, OUT / "moser_box_B2.png")

# %% [markdown]
# Sanity: enumerate the 12 unit vectors of Z[zeta_12] in this basis.

# %%
for u in candidate.unit_vectors:
    print(u)
