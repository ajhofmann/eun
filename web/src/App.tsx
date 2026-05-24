import { useEffect, useMemo, useState } from "react";
import GraphCanvas, { Candidate } from "./components/GraphCanvas";
import FrontierPlot from "./components/FrontierPlot";

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
  k: number;
  R: number;
  window_kind: string;
  translation_seed: number | null;
  greedy_e: number;
  local_swap_e: number;
  best_e: number;
  best_method: string;
  strict_baseline_e: number | null;
  delta: number;
  wins: boolean;
  candidate_file: string;
}

export interface WinV1Row {
  n: number;
  e_zeta12: number;
  e_strict_baseline: number | null;
  delta: number;
  pct: number | null;
  still_a_win: boolean;
}

type Tab = "results" | "gallery" | "frontier" | "constructions" | "about";

export default function App() {
  const [tab, setTab] = useState<Tab>("results");
  const [manifest, setManifest] = useState<ManifestEntry[]>([]);
  const [frontier, setFrontier] = useState<FrontierRow[]>([]);
  const [v2Wins, setV2Wins] = useState<WinV2Row[]>([]);
  const [v1Wins, setV1Wins] = useState<WinV1Row[]>([]);
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
    fetch("/runs/zeta12_winv2_vs_strict.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j: WinV2Row[]) => setV2Wins(j))
      .catch(() => {});
    fetch("/runs/zeta12_vs_strict.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j: WinV1Row[]) => setV1Wins(j))
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
          Cut-and-project constructions vs. the strict best-of-finite-construction baseline.
          Every claimed unit edge verified exactly via sympy + cross-checked at 256-bit precision in PARI.
        </p>
        <nav style={styles.tabs}>
          {(["results", "constructions", "gallery", "frontier", "about"] as Tab[]).map((t) => (
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
        <ResultsTab v2Wins={v2Wins} v1Wins={v1Wins} onOpenCandidate={(file) => { setSelected(file); setTab("gallery"); }} />
      )}

      {tab === "constructions" && <ConstructionsTab />}

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
                <GraphCanvas candidate={candidate} />
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
            Strict best-of-finite-construction frontier: max over literature
            curated values (n ≤ 30), rectangular Erdős grid, triangular Z[ζ_6]
            hex / parallelogram / strip, and Moser visible-disk sweep.
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
  v1Wins,
  onOpenCandidate,
}: {
  v2Wins: WinV2Row[];
  v1Wins: WinV1Row[];
  onOpenCandidate: (file: string) => void;
}) {
  const sortedV2 = [...v2Wins].sort((a, b) => a.k - b.k);
  const winCount = sortedV2.filter((r) => r.wins).length;
  const sortedV1 = [...v1Wins].sort((a, b) => a.n - b.n);

  return (
    <div style={styles.frontierLayout}>
      <section>
        <h2 style={styles.h2}>Headline result</h2>
        <p style={styles.lead}>
          A rank-4 cyclotomic cut-and-project construction (Z[ζ_12] with a
          translated box window) beats every other finite construction we
          could reproduce at every perfect square <code>n ∈ [64, 196]</code>{" "}
          by <strong>+9.8% to +16.7%</strong>. {winCount} of 8 v2 candidates
          strictly beat the strict baseline; n=49 ties{" "}
          (Z[ζ_12] = Z[i, ζ_3] is literally the Moser lattice).
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/wins/v2_wins.png" alt="v2 wins" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>v2 wins vs strict baseline</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>n</th>
              <th style={styles.th}>v2 e</th>
              <th style={styles.th}>strict baseline e</th>
              <th style={styles.th}>Δ</th>
              <th style={styles.th}>%</th>
              <th style={styles.th}>window</th>
              <th style={styles.th}>seed</th>
              <th style={styles.th}>candidate</th>
            </tr>
          </thead>
          <tbody>
            {sortedV2.map((r) => {
              const pct =
                r.strict_baseline_e && r.strict_baseline_e > 0
                  ? (100 * r.delta) / r.strict_baseline_e
                  : 0;
              return (
                <tr key={r.k} style={r.wins ? styles.winRow : undefined}>
                  <td style={styles.td}>{r.k}</td>
                  <td style={styles.td}>{r.best_e}</td>
                  <td style={styles.td}>{r.strict_baseline_e ?? "?"}</td>
                  <td style={{ ...styles.td, fontWeight: r.wins ? 600 : 400 }}>
                    {r.wins ? `+${r.delta}` : r.delta === 0 ? "tie" : r.delta}
                  </td>
                  <td style={styles.td}>
                    {r.wins ? `+${pct.toFixed(1)}%` : ""}
                  </td>
                  <td style={styles.td}>
                    {r.window_kind} R={r.R}
                  </td>
                  <td style={styles.td}>
                    {r.translation_seed === null ? "centered" : `seed=${r.translation_seed}`}
                  </td>
                  <td style={styles.td}>
                    <button
                      style={styles.linkBtn}
                      onClick={() => onOpenCandidate(`/candidates/winv2_zeta12_n${r.k}.json`)}
                    >
                      open →
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section>
        <h2 style={styles.h2}>Per-n head-to-head: 5 constructions, same n, same scale</h2>
        <p style={styles.description}>
          Each panel: best triangular | best Moser | best Erdős grid | Z[ζ_12]
          v1 (centered ball) | Z[ζ_12] v2 (window-explored). The v2 panel on
          the right strictly dominates the four to its left wherever Δ &gt; 0.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[64, 81, 100, 121, 144, 169, 196].map((n) => (
            <div key={n} style={styles.imgWrap}>
              <img src={`/gallery/wins/compare_n${n}.png`} alt={`compare n=${n}`} style={styles.img} />
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Which construction wins each n in the strict baseline</h2>
        <p style={styles.description}>
          <code>known_bounds</code> (literature) for n ≤ 30; <code>moser_hex</code>{" "}
          (rank-4 visible disk) dominates n ∈ [31, ~270]; <code>erdos_grid</code>{" "}
          (rectangular sweep) takes over for n ≳ 270. The triangular Z[ζ_6]
          sweep never wins a single n - the rank-4 Moser lattice strictly
          dominates it because 12 unit vectors {">>"} 6.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/baseline/source_share.png" alt="source share" style={styles.img} />
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>v1 results (re-scored against strict baseline)</h2>
        <p style={styles.description}>
          Original v1 wins (centered ball R=3.0) re-scored: 10/12 still beat
          the strict baseline; n=36 and n=49 became ties because Z[ζ_12]
          coincides with the Moser lattice and both extract the same dense
          piece at small n.
        </p>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>n</th>
              <th style={styles.th}>e (v1, ball)</th>
              <th style={styles.th}>strict baseline</th>
              <th style={styles.th}>Δ</th>
              <th style={styles.th}>%</th>
              <th style={styles.th}>status</th>
            </tr>
          </thead>
          <tbody>
            {sortedV1.map((r) => (
              <tr key={r.n} style={r.still_a_win ? styles.winRow : undefined}>
                <td style={styles.td}>{r.n}</td>
                <td style={styles.td}>{r.e_zeta12}</td>
                <td style={styles.td}>{r.e_strict_baseline ?? "?"}</td>
                <td style={styles.td}>
                  {r.delta > 0 ? `+${r.delta}` : r.delta === 0 ? "0" : r.delta}
                </td>
                <td style={styles.td}>
                  {r.pct === null ? "" : (r.pct >= 0 ? `+${r.pct.toFixed(1)}%` : `${r.pct.toFixed(1)}%`)}
                </td>
                <td style={styles.td}>{r.still_a_win ? "WIN" : r.delta === 0 ? "TIE" : "LOSS"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2 style={styles.h2}>Negative results worth recording</h2>
        <ul style={{ ...styles.description, paddingLeft: 20 }}>
          <li>
            <strong>Higher-rank cyclotomic</strong> (m ∈ {"{15, 20, 24}"}, rank
            8, 20–30 unit vectors): always strictly worse than Z[ζ_12] v1 at
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
        <h2 style={styles.h2}>Strict frontier (raw + density)</h2>
        <p style={styles.description}>
          Raw u(n) and density e/n across n ∈ [1, 1000], colored by which family
          contributes the strict baseline. Orange stars are the seven Z[ζ_12]
          v2 wins.
        </p>
        <div style={styles.imgWrap}>
          <img src="/gallery/baseline/strict_frontier.png" alt="strict frontier" style={styles.img} />
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
          biquadratic, triangular, generic cut_project. Each exposes a
          dataclass <code>Params</code>, an <code>enumerate_unit_vectors()</code>{" "}
          (with sympy verification), and a <code>build()</code> returning a{" "}
          <code>Candidate</code> with explicit integer-coefficient points and
          edges.
        </p>
        <p style={styles.description}>
          <code>src/eud/search/</code>: greedy_peel and core_peel (deterministic
          shrinkers), local_swap (simulated annealing with warm-start from
          greedy), CP-SAT exact densest-k via OR-Tools.
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
