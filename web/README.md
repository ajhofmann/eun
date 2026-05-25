# eud web viewer

Vite + React app for browsing generated candidates, frontier curves, gallery
plots, and an interactive construction explorer backed by `eud-api`.

## Prerequisites

From the repository root:

```bash
make install
```

Node.js 18+ for the frontend.

## Data symlinks (dev server)

The dev server serves static JSON/PNG from `web/public/`. Symlink the generated
data directories once (paths relative to `web/`):

```bash
cd web
mkdir -p public
ln -sf ../../data/candidates public/candidates
ln -sf ../../data/frontiers public/frontiers
ln -sf ../../data/gallery public/gallery
ln -sf ../../data/runs public/runs
```

These symlinks must stay **untracked** and use **relative** paths like above.
Do not commit absolute paths (e.g. `/Users/...`); GitHub clones will break and
they leak your local username.

Rebuild the candidate manifest after adding or changing showcase JSON:

```bash
cd ..
make refresh-manifest
```

## Development

Terminal 1 — static viewer (port 5173):

```bash
make web-dev
# or: cd web && npm install && npm run dev
```

Open http://127.0.0.1:5173/

Terminal 2 — interactive explorer API (port 8000, optional):

```bash
uv run eud-api
```

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`. Use the
**explorer** tab to generate and prune candidates live.

## Production build

```bash
make web-build
```

Output is in `web/dist/` (gitignored). Symlinks under `public/` are copied into
the bundle at build time; run `make refresh-manifest` and ensure gallery/run
JSON exists before building if you ship a static site.

Preview the production bundle:

```bash
cd web && npm run preview
```

## GitHub Pages (static explorer near n=545)

Published site: **https://ajhofmann.github.io/eun/** (project Pages for the `eun` repo).

The Pages build ships only the three-graph compare demo (interactive canvases, no
`eud-api`). Enable **Settings → Pages → Build and deployment → GitHub Actions**
on the repository once.

Bundle demo JSON from local candidates (required before first build or after
regenerating compare files):

```bash
make pages-bundle   # copies into web/public/demo/near545/
make pages-build    # VITE_PAGES_MODE + base /eun/
```

Preview the Pages bundle locally:

```bash
cd web && npx vite preview --base /eun/
```

Open http://127.0.0.1:4173/eun/

Local dev of the Pages shell only:

```bash
make pages-bundle
cd web && VITE_PAGES_MODE=true npm run dev
```

The full viewer’s **X compare** tab uses the same `web/public/demo/near545/` JSON;
run `make pages-bundle` even when developing locally (or keep symlinks under
`public/candidates/` for other tabs).

## Tabs

| Tab | Content |
| --- | ------- |
| **results** | Z[ζ_12] vs baselines/SOTA tables, Engel reproduction, beyond-100, Moser ring probe, static gallery PNGs |
| **explorer** | Live generation/prune via `eud-api` (Pages: static near-545 demo only) |
| **constructions** | Baseline family diagrams and Sawin finite-vs-asymptotic panels |
| **gallery** | Candidate list from `manifest.json` + interactive graph |
| **frontier** | `baseline.jsonl` plot and top-density rows |
| **about** | Problem statement, verification protocol, pipeline map |

## Key data files

| Path | Used for |
| --- | --- |
| `data/candidates/manifest.json` | Gallery sidebar |
| `data/frontiers/baseline.jsonl` | Frontier tab (published-aware) |
| `data/runs/zeta12_vs_published_sota.json` | Results tables |
| `data/runs/engel_moser_reproduce.json` | Engel Table 2 comparison |
| `data/runs/engel_moser_beyond_100.json` | Post-100 Engel beam rows |
| `data/runs/moser_ring_probe_best.json` | Moser ring probe table |

Regenerate plots with `scripts/render_gallery_full.py` and
`scripts/refresh_gallery.py` (see root `README.md`).
