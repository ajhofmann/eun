import { useEffect, useMemo, useState } from "react";
import type { Candidate } from "./components/GraphCanvas";
import ConstructionExplorer from "./components/ConstructionExplorer";
import FrontierPlot from "./components/FrontierPlot";
import InteractiveGraphCanvas from "./components/InteractiveGraphCanvas";

export interface ManifestEntry {
  name: string;
  file: string;
  description: string;
  family: string;
  n: number;
  e: number;
  density: number;
  unit_vectors: number;
}

export interface FrontierRow {
  family?: string;
  source?: string;
  n: number;
  e: number;
  density?: number;
  K?: number;
  m?: number;
  mx?: number;
  my?: number;
  exact?: boolean;
}

export interface WinV2Row {
  n: number;
  e_zeta12_v1: number;
  e_zeta12_v2: number | null;
  e_zeta12_best: number;
  best_zeta12_variant: string;
  reproducible_baseline_e: number | null;
  published_sota_e: number | null;
  delta_vs_reproducible_baseline: number;
  pct_vs_reproducible_baseline: number | null;
  delta_vs_published_sota: number | null;
  pct_vs_published_sota: number | null;
  beats_reproducible_baseline: boolean;
  beats_published_sota: boolean;
}

export interface EngelProbeRow {
  k: number;
  e?: number;
  rerendered_e?: number;
  engel_2025_e: number | null;
  delta_vs_engel_2025: number | null;
  candidate_file: string;
  image_file: string;
}

export interface EngelBeyondRow {
  k: number;
  e: number;
  density: number;
  published_baseline_e: number | null;
  delta_vs_published_baseline: number | null;
  reproducible_baseline_e: number | null;
  delta_vs_reproducible_baseline: number | null;
  candidate_file: string;
}

export interface MoserRingProbeRow {
  k: number;
  e: number;
  density: number;
  n_units: number;
  candidate_file: string;
  params: {
    denom_power: number;
    coeff_bound: number;
    visible_radius: number;
    window_kind: string;
  };
}

type Tab = "results" | "explorer" | "gallery" | "frontier" | "constructions" | "about";

export default function App() {
  const [tab, setTab] = useState<Tab>("results");
  const [manifest, setManifest] = useState<ManifestEntry[]>([]);
  const [frontier, setFrontier] = useState<FrontierRow[]>([]);
  const [v2Wins, setV2Wins] = useState<WinV2Row[]>([]);
  const [engelProbe, setEngelProbe] = useState<EngelProbeRow[]>([]);
  const [engelBeyond, setEngelBeyond] = useState<EngelBeyondRow[]>([]);
  const [moserRingProbe, setMoserRingProbe] = useState<MoserRingProbeRow[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/candidates/manifest.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j: ManifestEntry[]) => {
        setManifest(j);
        if (j.length && !selected) setSelected(j[0].file);
      })
      .catch((err: Error) => setError(`manifest: ${err.message}`));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetch("/frontiers/baseline.jsonl")
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((txt) => {
        const rows = txt
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean)
          .map((l) => JSON.parse(l) as FrontierRow);
        setFrontier(rows);
      })
      .catch((err: Error) => setError(`frontier: ${err.message}`));
  }, []);

  useEffect(() => {
    fetch("/runs/zeta12_vs_published_sota.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j: WinV2Row[]) => setV2Wins(j))
      .catch(() => {});
    fetch("/runs/engel_moser_reproduce.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j: EngelProbeRow[]) => setEngelProbe(j))
      .catch(() => {});
    fetch("/runs/engel_moser_beyond_100.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j: EngelBeyondRow[]) => setEngelBeyond(j))
      .catch(() => {});
    fetch("/runs/moser_ring_probe_best.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j: MoserRingProbeRow[]) => setMoserRingProbe(j))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) return;
    setCandidate(null);
    fetch(selected)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j: Candidate) => setCandidate(j))
      .catch((err: Error) => setError(`candidate: ${err.message}`));
  }, [selected]);

  const candidateMeta = useMemo(
    () => manifest.find((m) => m.file === selected),
    [manifest, selected]
  );

  return (
    <div style={styles.shell}>
      <header style={styles.header}>
        <h1 style={styles.title}>eud — Erdős unit-distance search</h1>
        <p style={styles.subtitle}>
          Cut-and-project constructions, reproducible baselines, and published SOTA.
          Current honest status: Z[ζ_12] trails Engel et al. 2025, while the
          Engel-Moser search now matches 5/6 checked table values and powers the
          post-100 fallback frontier.
        </p>
        <nav style={styles.tabs}>
          {(["results", "explorer", "constructions", "gallery", "frontier", "about"] as Tab[]).map((t) => (
            <button
              key={t}
              style={{ ...styles.tab, ...(tab === t ? styles.tabActive : {}) }}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>

      {error && <div style={styles.error}>error: {error}</div>}

      {tab === "results" && (
        <ResultsTab
          v2Wins={v2Wins}
          engelProbe={engelProbe}
          engelBeyond={engelBeyond}
          moserRingProbe={moserRingProbe}
          onOpenCandidate={(file) => { setSelected(file); setTab("gallery"); }}
        />
      )}

      {tab === "constructions" && <ConstructionsTab />}

      {tab === "explorer" && <ConstructionExplorer />}

      {tab === "gallery" && (
        <div style={styles.galleryLayout}>
          <aside style={styles.sidebar}>
            <h3 style={styles.sectionTitle}>candidates</h3>
            <ul style={styles.list}>
              {manifest.map((m) => (
                <li key={m.file}>
                  <button
                    style={{
                      ...styles.listItem,
                      ...(m.file === selected ? styles.listItemActive : {}),
                    }}
                    onClick={() => setSelected(m.file)}
                  >
                    <div style={styles.listName}>{m.name}</div>
                    <div style={styles.listMeta}>
                      n={m.n} e={m.e} e/n={m.density.toFixed(3)}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          <main style={styles.main}>
            {candidate ? (
              <>
                <div style={styles.statsRow}>
                  <Stat label="family" value={candidate.family} />
                  <Stat label="n" value={candidate.n} />
                  <Stat label="e" value={candidate.e} />
                  <Stat label="e/n" value={candidate.density.toFixed(3)} />
                  <Stat label="|U|" value={candidate.unit_vectors?.length ?? "?"} />
                </div>
                {candidateMeta?.description && (
                  <p style={styles.description}>{candidateMeta.description}</p>
                )}
                <InteractiveGraphCanvas candidate={candidate} />
                <details style={styles.details}>
                  <summary>params</summary>
                  <pre style={styles.pre}>
                    {JSON.stringify(candidate.params, null, 2)}
                  </pre>
                </details>
              </>
            ) : (
              <p style={{ opacity: 0.6 }}>loading candidate…</p>
            )}
          </main>
        </div>
      )}

      {tab === "frontier" && (
        <div style={styles.frontierLayout}>
          <p style={styles.description}>
            Published-SOTA-aware frontier: max over literature curated values,
            Engel et al. 2025 beam-search values through n=100, rectangular
            Erdős grid, triangular Z[ζ_6] hex / parallelogram / strip, and
            Moser visible-disk sweep.
            Higher curve = stronger construction at that n. The orange ◯
            markers are gallery candidates plotted on top.
          </p>
          <FrontierPlot
            rows={frontier}
            galleryRows={manifest.map((m) => ({
              n: m.n,
              e: m.e,
              source: m.family,
              name: m.name,
            }))}
          />
          <h3 style={styles.sectionTitle}>top-density frontier rows</h3>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>n</th>
                <th style={styles.th}>e</th>
                <th style={styles.th}>e/n</th>
                <th style={styles.th}>source</th>
                <th style={styles.th}>extra</th>
              </tr>
            </thead>
            <tbody>
              {[...frontier]
                .sort((a, b) => (b.density ?? b.e / b.n) - (a.density ?? a.e / a.n))
                .slice(0, 16)
                .map((r, i) => (
                  <tr key={i}>
                    <td style={styles.td}>{r.n}</td>
                    <td style={styles.td}>{r.e}</td>
                    <td style={styles.td}>
                      {(r.density ?? r.e / r.n).toFixed(3)}
                    </td>
                    <td style={styles.td}>{r.source ?? r.family}</td>
                    <td style={styles.td}>
                      {r.K !== undefined ? `K=${r.K}` : ""}
                      {r.mx !== undefined && r.my !== undefined ? ` ${r.mx}×${r.my}` : (r.m !== undefined ? ` m=${r.m}` : "")}
                      {r.exact ? " (exact)" : ""}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "about" && <AboutTab />}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={styles.stat}>
      <div style={styles.statLabel}>{label}</div>
      <div style={styles.statValue}>{value}</div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Results tab
// -----------------------------------------------------------------------------

function ResultsTab({
  v2Wins,
  engelProbe,
  engelBeyond,
  moserRingProbe,
  onOpenCandidate,
}: {
  v2Wins: WinV2Row[];
  engelProbe: EngelProbeRow[];
  engelBeyond: EngelBeyondRow[];
  moserRingProbe: MoserRingProbeRow[];
  onOpenCandidate: (file: string) => void;
}) {
  const sortedV2 = [...v2Wins].sort((a, b) => a.n - b.n);
  const reproWinCount = sortedV2.filter((r) => r.beats_reproducible_baseline).length;
  const sotaRows = sortedV2.filter((r) => r.published_sota_e !== null);
  const sotaWinCount = sortedV2.filter((r) => r.beats_published_sota).length;

  return (
    <div style={styles.frontierLayout}>
      <section>
        <h2 style={styles.h2}>Headline result</h2>
        <p style={styles.lead}>
          A rank-4 cyclotomic cut-and-project construction (Z[ζ_12] with a
          translated box window) improves our reproducible baseline at{" "}
          <strong>{reproWinCount}</strong> of the tested n values, but it does{" "}
          <strong>not</strong> beat published finite SOTA where Engel et al.
          2025 report a table. It trails that table at {sotaRows.length} of{" "}
          {sotaRows.length} covered n values; SOTA wins: {sotaWinCount}.
          The missing ingredient is Engel's 18-unit Moser lattice versus our
          ζ_12 lattice's 12 unit vectors.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/sota/published_vs_ours.png" alt="published SOTA vs ours" style={styles.img} />
        </div>
        <div style={styles.imgWrap}>
          <img src="/gallery/sota/gap_to_engel.png" alt="gap to Engel" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Z[ζ_12] best vs reproducible baseline vs published SOTA</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>n</th>
              <th style={styles.th}>Z[ζ_12] best</th>
              <th style={styles.th}>variant</th>
              <th style={styles.th}>repro baseline</th>
              <th style={styles.th}>Δ repro</th>
              <th style={styles.th}>Engel/SOTA</th>
              <th style={styles.th}>Δ SOTA</th>
              <th style={styles.th}>status</th>
              <th style={styles.th}>candidate</th>
            </tr>
          </thead>
          <tbody>
            {sortedV2.map((r) => {
              const hasCandidate = r.e_zeta12_v2 !== null;
              const sotaDelta = r.delta_vs_published_sota;
              return (
                <tr key={r.n} style={r.beats_reproducible_baseline ? styles.winRow : undefined}>
                  <td style={styles.td}>{r.n}</td>
                  <td style={styles.td}>{r.e_zeta12_best}</td>
                  <td style={styles.td}>{r.best_zeta12_variant}</td>
                  <td style={styles.td}>{r.reproducible_baseline_e ?? "?"}</td>
                  <td style={styles.td}>
                    {r.delta_vs_reproducible_baseline > 0
                      ? `+${r.delta_vs_reproducible_baseline}`
                      : r.delta_vs_reproducible_baseline}
                  </td>
                  <td style={styles.td}>{r.published_sota_e ?? "n/a"}</td>
                  <td style={styles.td}>
                    {sotaDelta === null ? "n/a" : sotaDelta > 0 ? `+${sotaDelta}` : sotaDelta}
                  </td>
                  <td style={styles.td}>
                    {r.beats_published_sota
                      ? "SOTA WIN"
                      : r.beats_reproducible_baseline
                      ? "repro win"
                      : "loss"}
                  </td>
                  <td style={styles.td}>
                    {hasCandidate ? (
                      <button
                        style={styles.linkBtn}
                        onClick={() => onOpenCandidate(`/candidates/winv2_zeta12_n${r.n}.json`)}
                      >
                        open →
                      </button>
                    ) : (
                      ""
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section>
        <h2 style={styles.h2}>Scaled head-to-head: natural symmetric sizes</h2>
        <p style={styles.description}>
          Each panel uses a full symmetric window or shape near the same scale:
          triangular hex disk | Engel 18-unit Moser disk | square Erdős grid |
          uploaded <code>Z[i, ρ]</code> disk | centered Z[ζ_12] window. Since
          nothing is greedily peeled, the vertex counts differ slightly across
          panels but the geometry stays symmetric.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[545, 6061, 13669].map((n) => (
            <div key={n} style={styles.imgWrap}>
              <img src={`/gallery/wins/compare_n${n}.png`} alt={`compare n=${n}`} style={styles.img} />
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Which source wins each n in the published baseline</h2>
        <p style={styles.description}>
          <code>engel_2025</code> dominates n≤100 where the published beam-search
          table exists. Beyond that, the viewer falls back to our reproducible
          construction frontier: Moser visible-disk for a while, then the
          rectangular Erdős grid.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/baseline/source_share.png" alt="source share" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Reproducing Engel 2025 with the right family</h2>
        <p style={styles.description}>
          After adding Engel's exact 18-unit lattice, a visible-disk +
          best-swap / perturb-and-repair search plus a coefficient-space beam
          reproduces 5 of the 6 checked Table 2 values exactly. It still misses
          n=64 by one edge. This is much more promising than ζ_12: the lattice
          is right, and the remaining gap is likely richer child/canonization
          machinery.
        </p>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>n</th>
              <th style={styles.th}>our Engel probe</th>
              <th style={styles.th}>Engel Table 2</th>
              <th style={styles.th}>gap</th>
              <th style={styles.th}>candidate</th>
            </tr>
          </thead>
          <tbody>
            {engelProbe.map((r) => (
              <tr key={r.k} style={r.delta_vs_engel_2025 === 0 ? styles.winRow : undefined}>
                <td style={styles.td}>{r.k}</td>
                <td style={styles.td}>{r.e ?? r.rerendered_e}</td>
                <td style={styles.td}>{r.engel_2025_e ?? "n/a"}</td>
                <td style={styles.td}>
                  {r.delta_vs_engel_2025 === null
                    ? "n/a"
                    : r.delta_vs_engel_2025 === 0
                    ? "tie"
                    : r.delta_vs_engel_2025}
                </td>
                <td style={styles.td}>
                  <button
                    style={styles.linkBtn}
                    onClick={() => onOpenCandidate(`/candidates/${r.candidate_file.split("/").pop()}`)}
                  >
                    open →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2 style={styles.h2}>Engel-Moser beyond the published n≤100 table</h2>
        <p style={styles.description}>
          Engel et al.'s public table stops at n=100. These rows run the same
          18-unit family beyond that range and compare against the repo's
          fallback frontier, which is reproducible but not a literature SOTA
          claim. The large positive deltas mean the Engel family should replace
          the older fallback baseline for these n values.
        </p>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>n</th>
              <th style={styles.th}>Engel beam e</th>
              <th style={styles.th}>e/n</th>
              <th style={styles.th}>published-aware fallback</th>
              <th style={styles.th}>Δ fallback</th>
              <th style={styles.th}>candidate</th>
            </tr>
          </thead>
          <tbody>
            {engelBeyond.map((r) => (
              <tr key={r.k} style={styles.winRow}>
                <td style={styles.td}>{r.k}</td>
                <td style={styles.td}>{r.e}</td>
                <td style={styles.td}>{r.density.toFixed(3)}</td>
                <td style={styles.td}>{r.published_baseline_e ?? "n/a"}</td>
                <td style={styles.td}>
                  {r.delta_vs_published_baseline === null
                    ? "n/a"
                    : r.delta_vs_published_baseline > 0
                    ? `+${r.delta_vs_published_baseline}`
                    : r.delta_vs_published_baseline}
                </td>
                <td style={styles.td}>
                  <button
                    style={styles.linkBtn}
                    onClick={() => onOpenCandidate(`/candidates/${r.candidate_file.split("/").pop()}`)}
                  >
                    open →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={styles.imgWrap}>
          <img src="/gallery/sota/engel_beyond_graphs.png" alt="Engel beyond-100 found graphs" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Moser ring graph probe</h2>
        <p style={styles.description}>
          The common-denominator ring has more exact unit directions than the
          18-unit lattice. These are the current best greedy-pruned ring graphs
          from the probe sweep; they are viewable in the gallery and live explorer.
        </p>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>n</th>
              <th style={styles.th}>e</th>
              <th style={styles.th}>e/n</th>
              <th style={styles.th}>|U|</th>
              <th style={styles.th}>params</th>
              <th style={styles.th}>candidate</th>
            </tr>
          </thead>
          <tbody>
            {moserRingProbe.map((r) => (
              <tr key={r.k}>
                <td style={styles.td}>{r.k}</td>
                <td style={styles.td}>{r.e}</td>
                <td style={styles.td}>{r.density.toFixed(3)}</td>
                <td style={styles.td}>{r.n_units}</td>
                <td style={styles.td}>
                  k={r.params.denom_power} cb={r.params.coeff_bound} r={r.params.visible_radius}
                </td>
                <td style={styles.td}>
                  <button
                    style={styles.linkBtn}
                    onClick={() => onOpenCandidate(`/candidates/${r.candidate_file.split("/").pop()}`)}
                  >
                    open →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={styles.imgWrap}>
          <img src="/gallery/sota/moser_ring_graphs.png" alt="Moser ring found graphs" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Negative results worth recording</h2>
        <ul style={{ ...styles.description, paddingLeft: 20 }}>
          <li>
            <strong>Higher-rank cyclotomic</strong> (m ∈ {"{15, 20, 24}"}, rank
            8, 20–30 unit vectors): always strictly worse than the Z[ζ_12] runs at
            every n we probed. Hidden window goes from 2-D to 6-D and density
            collapses faster than the extra unit-vector count helps.
          </li>
          <li>
            <strong>OR-Tools CP-SAT exact densest-k</strong>: multi-worker
            mode hangs in presolve on Apple silicon (ortools 9.15);
            single-worker at 30 s budget is strictly worse than 0.1 s of
            warm-started greedy peel. Greedy is the practical exact-pruner
            on this lattice.
          </li>
          <li>
            <strong>Local-swap simulated annealing</strong> warm-started from
            greedy: never improves on greedy at n ≤ 196 on the Z[ζ_12] seed.
          </li>
        </ul>
      </section>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Constructions tab
// -----------------------------------------------------------------------------

function ConstructionsTab() {
  return (
    <div style={styles.frontierLayout}>
      <section>
        <h2 style={styles.h2}>Triangular Z[ζ_6] (Eisenstein) hex disks</h2>
        <p style={styles.description}>
          Rank 2, 6 unit vectors {"{(1,0),(0,1),(-1,1),(-1,0),(0,-1),(1,-1)}"} in
          basis (1, ζ_6). Filled hex disk of radius r has{" "}
          <code>n = 3r²+3r+1</code>, <code>e = 9r²+3r</code>. Density caps at
          ~3 (each interior vertex has degree 6, so e/n ≤ 3 in the limit).
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/baseline/triangular_disks.png" alt="triangular" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Moser rank-4 lattice Z[i, ζ]</h2>
        <p style={styles.description}>
          12 unit vectors (the 6 sixth roots of unity for ζ_6, or the 12 twelfth
          roots for ζ_12). Z[i, ζ_3] = Z[ζ_12] as a Z-module - this is the
          identity that makes "Moser hex" and "Q(ζ_12) cut-and-project" the
          same lattice up to filtering. Density caps at 6.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/baseline/moser_disks.png" alt="moser" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Engel et al. 18-unit Moser lattice</h2>
        <p style={styles.description}>
          This is the family behind the published SOTA table through n=100:
          <code>Z&lt;1, ω₁, ω₃, ω₁ω₃&gt;</code> with{" "}
          <code>ω₁ = exp(iπ/3)</code> and{" "}
          <code>ω₃ = exp(i arccos(5/6))</code>. Engel et al. prove it has
          exactly 18 unit vectors. That is why it beats our ζ_12 lattice,
          which has only 12.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/baseline/engel_moser_disks.png" alt="engel moser" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Erdős grid (rectangular)</h2>
        <p style={styles.description}>
          Z² inside an mx × my box with unit distance{" "}
          <code>√K</code>; K = product of primes ≡ 1 mod 4 maximizes the number
          of representations as sum of two squares (= unit-vector directions).
          Asymptotically the strongest construction, but the boundary loss
          dominates at small n.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/baseline/erdos_grids.png" alt="erdos grids" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Window translation effect on Z[ζ_12]</h2>
        <p style={styles.description}>
          Same lattice (rank-4 Z[ζ_12], coeff_bound=4), six different windows on
          the 2-D hidden space, all greedy-peeled to n=100. The{" "}
          <code>box, seed=1</code> panel produces e=380; the centered ball
          gives e=369. The +11-edge "v2 win" at n=100 is just window
          selection - same algebra, smarter cookie cutter.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/showcase/window_translation_n100.png" alt="window translation" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Published baseline frontier (raw + density)</h2>
        <p style={styles.description}>
          Raw u(n) and density e/n across n ∈ [1, 1000], colored by which family
          contributes the published/reproducible baseline. Purple is Engel et al.
          2025 through n=100; orange stars are the Z[ζ_12] candidates, which sit
          below purple where the published SOTA table exists.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/baseline/strict_frontier.png" alt="strict frontier" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Sawin/OpenAI lesson: asymptotic vs finite search</h2>
        <p style={styles.description}>
          The OpenAI/Sawin result says algebraic number fields eventually beat
          Erdős' old exponent, but that asymptotic construction starts at
          astronomical n. For n≤1000, finite graph structure dominates:
          local unit-vector count, boundary loss, window shape, and search.
          The practical bridge is Engel's 18-unit Moser lattice, not ζ_12.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/sawin/finite_vs_asymptotic.png" alt="finite vs asymptotic" style={styles.img} />
        </div>
        <div style={styles.imgWrap}>
          <img src="/gallery/sawin/lessons_panel.png" alt="Sawin lessons" style={styles.img} />
        </div>
      </section>
    </div>
  );
}

// -----------------------------------------------------------------------------
// About tab
// -----------------------------------------------------------------------------

function AboutTab() {
  return (
    <div style={styles.frontierLayout}>
      <section>
        <h2 style={styles.h2}>The problem</h2>
        <p style={styles.description}>
          <strong>u(n)</strong> = max number of unit-distance pairs among n
          points in the plane (Erdős, 1946). Conjectured{" "}
          <code>u(n) = n^(1 + c/log log n)</code>; Sawin (2022) proved{" "}
          <code>u(n) ≥ n^(1 + 1/log²log n)</code> asymptotically, but the
          smallest finite witness of his construction is around{" "}
          <code>10^(1.96M)</code> points.
        </p>
        <p style={styles.description}>
          <strong>This project's question</strong>: at finite n, how high
          can we push the lower bound, with every claimed unit edge proven
          exactly (not floating-point)? Smallest n where a higher-rank
          algebraic / cut-and-project construction beats the strongest
          finite reproducible construction.
        </p>
      </section>

      <section>
        <h2 style={styles.h2}>Verification protocol</h2>
        <p style={styles.description}>
          Every "win" candidate ships with a JSON certificate. For each edge:
        </p>
        <ul style={{ ...styles.description, paddingLeft: 20 }}>
          <li>
            integer coefficient difference <code>(c₀, c₁, c₂, c₃)</code> in
            the basis <code>(1, ζ, ζ², ζ³)</code> is recorded;
          </li>
          <li>
            sympy proves <code>|c₀ + c₁ζ + c₂ζ² + c₃ζ³|² ≡ 1</code> exactly
            in Q(ζ_12);
          </li>
          <li>
            cypari2 independently verifies <code>|σ₁(...)|² ≈ 1.0</code> at
            256-bit precision (~30 decimal places).
          </li>
        </ul>
        <p style={styles.description}>
          Floats are used for plotting only.
        </p>
      </section>

      <section>
        <h2 style={styles.h2}>Pipeline</h2>
        <p style={styles.description}>
          <code>src/eud/families/</code>: erdos_grid, moser, cyclotomic,
          biquadratic, triangular, engel_moser, moser_ring, generic cut_project.
          Each exposes a
          dataclass <code>Params</code>, an <code>enumerate_unit_vectors()</code>{" "}
          (with sympy verification), and a <code>build()</code> returning a{" "}
          <code>Candidate</code> with explicit integer-coefficient points and
          edges.
        </p>
        <p style={styles.description}>
          <code>src/eud/search/</code>: greedy_peel and core_peel (deterministic
          shrinkers), local_swap (simulated annealing with warm-start from
          greedy), CP-SAT exact densest-k via OR-Tools, and Engel-style
          coefficient-space beam search.
        </p>
        <p style={styles.description}>
          <code>src/eud/benchmarks/</code>: literature curated table +
          best-of-finite-construction strict frontier builder.
        </p>
      </section>

      <section>
        <h2 style={styles.h2}>What's still open</h2>
        <ul style={{ ...styles.description, paddingLeft: 20 }}>
          <li>
            Curate <code>known_bounds</code> for n ∈ [31, 100] from
            Schade (2020) and the Moser-beam-search literature.
          </li>
          <li>
            Run multi-worker CP-SAT on Linux to <em>prove</em> optimality at
            small k (the Apple-silicon hang is OR-Tools issue, not algorithmic).
          </li>
          <li>
            Hybrid <code>Z[ζ_12] ∪ shifted-Z[ζ_12]</code> could in principle
            exceed the 12-direction density cap of 6/vertex.
          </li>
          <li>
            Adaptive ellipsoid windows per Galois conjugate for higher-rank
            cyclotomic fields (current sweep used isotropic balls in 6-D,
            which is the worst-case window shape).
          </li>
        </ul>
      </section>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  shell: {
    maxWidth: 1280,
    margin: "0 auto",
    padding: "16px 24px 48px",
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
  },
  header: { borderBottom: "1px solid #2222", paddingBottom: 12, marginBottom: 16 },
  title: { margin: 0, fontSize: 22, letterSpacing: -0.4 },
  subtitle: { margin: "6px 0 12px", opacity: 0.75, fontSize: 13, lineHeight: 1.5 },
  tabs: { display: "flex", gap: 4 },
  tab: {
    padding: "6px 14px",
    background: "transparent",
    border: "1px solid #aaa4",
    borderRadius: 6,
    cursor: "pointer",
    fontFamily: "inherit",
    fontSize: 13,
    color: "inherit",
    textTransform: "lowercase",
  },
  tabActive: { background: "#3b82f6", borderColor: "#3b82f6", color: "white" },
  error: {
    background: "#fee",
    color: "#a00",
    padding: 8,
    borderRadius: 4,
    margin: "8px 0",
    fontFamily: "monospace",
    fontSize: 12,
  },
  galleryLayout: { display: "grid", gridTemplateColumns: "260px 1fr", gap: 20 },
  sidebar: { borderRight: "1px solid #2222", paddingRight: 12, maxHeight: "80vh", overflowY: "auto" },
  sectionTitle: {
    margin: "0 0 8px",
    fontSize: 13,
    opacity: 0.7,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  list: {
    listStyle: "none",
    margin: 0,
    padding: 0,
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  listItem: {
    width: "100%",
    textAlign: "left",
    padding: "8px 10px",
    background: "transparent",
    border: "1px solid #2221",
    borderRadius: 6,
    cursor: "pointer",
    fontFamily: "inherit",
    color: "inherit",
  },
  listItemActive: { background: "#3b82f618", borderColor: "#3b82f6" },
  listName: { fontSize: 13, fontWeight: 500 },
  listMeta: {
    fontSize: 11,
    opacity: 0.6,
    fontFamily: "monospace",
    marginTop: 2,
  },
  main: { display: "flex", flexDirection: "column", gap: 12 },
  statsRow: { display: "flex", gap: 16, flexWrap: "wrap" },
  stat: {
    background: "#3b82f60a",
    border: "1px solid #3b82f622",
    borderRadius: 6,
    padding: "6px 12px",
    minWidth: 60,
  },
  statLabel: {
    fontSize: 11,
    opacity: 0.6,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  statValue: { fontSize: 18, fontFamily: "monospace", fontWeight: 600 },
  description: { fontSize: 13, opacity: 0.85, margin: "4px 0 8px", lineHeight: 1.6 },
  details: { fontSize: 12 },
  pre: {
    background: "#0001",
    padding: 10,
    borderRadius: 4,
    fontSize: 11,
    overflow: "auto",
  },
  frontierLayout: { display: "flex", flexDirection: "column", gap: 24 },
  table: { borderCollapse: "collapse", fontSize: 12, width: "100%" },
  th: {
    textAlign: "left",
    padding: "6px 12px",
    borderBottom: "1px solid #2224",
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    opacity: 0.7,
  },
  td: { padding: "6px 12px", borderBottom: "1px solid #2221", fontFamily: "monospace" },
  winRow: { background: "#ff880014" },
  h2: { margin: "0 0 8px", fontSize: 18, fontWeight: 600 },
  lead: { fontSize: 14, lineHeight: 1.6, margin: "4px 0 14px" },
  imgWrap: {
    border: "1px solid #2222",
    borderRadius: 8,
    background: "#fafafa",
    padding: 8,
    overflow: "auto",
  },
  img: { display: "block", width: "100%", maxWidth: "100%", height: "auto" },
  linkBtn: {
    background: "transparent",
    border: "1px solid #3b82f6",
    color: "#3b82f6",
    padding: "2px 8px",
    fontSize: 11,
    fontFamily: "inherit",
    borderRadius: 4,
    cursor: "pointer",
  },
};
