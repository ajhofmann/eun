# eud viewer

Minimal Vite + React viewer for inspecting generated candidate JSON files.

## Setup

```bash
cd web
npm install
mkdir -p public/candidates public/frontiers
ln -s ../../data/candidates public/candidates  # or copy
ln -s ../../data/frontiers  public/frontiers
npm run dev
```

Then open http://127.0.0.1:5173/ and load a candidate JSON path like
`/candidates/zeta5_R2.5.json`.

This stub is intentionally lightweight: one route, one component, no math
in the frontend. Extend with frontier plot, candidate table, and certificate
viewer as needed.
