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
  exact?: boolean;
}

type Tab = "gallery" | "frontier";

export default function App() {
  const [tab, setTab] = useState<Tab>("gallery");
  const [manifest, setManifest] = useState<ManifestEntry[]>([]);
  const [frontier, setFrontier] = useState<FrontierRow[]>([]);
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
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

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
          cut-and-project constructions vs. classical Erdős-grid baseline.
          north star: smallest n where higher-rank algebraic construction beats
          the strongest known finite lower bound.
        </p>
        <nav style={styles.tabs}>
          <button
            style={{ ...styles.tab, ...(tab === "gallery" ? styles.tabActive : {}) }}
            onClick={() => setTab("gallery")}
          >
            gallery
          </button>
          <button
            style={{ ...styles.tab, ...(tab === "frontier" ? styles.tabActive : {}) }}
            onClick={() => setTab("frontier")}
          >
            frontier
          </button>
        </nav>
      </header>

      {error && <div style={styles.error}>error: {error}</div>}

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
            Best-known lower bound u(n) by source. Curated table for n ≤ 30,
            optimized Erdős-grid sweep for n = m². Higher curve = stronger
            construction at that n.
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
                .slice(0, 12)
                .map((r, i) => (
                  <tr key={i}>
                    <td style={styles.td}>{r.n}</td>
                    <td style={styles.td}>{r.e}</td>
                    <td style={styles.td}>
                      {(r.density ?? r.e / r.n).toFixed(3)}
                    </td>
                    <td style={styles.td}>{r.source ?? r.family}</td>
                    <td style={styles.td}>
                      {r.K !== undefined ? `K=${r.K}, m=${r.m}` : ""}
                      {r.exact ? " (exact)" : ""}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
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
  subtitle: { margin: "6px 0 12px", opacity: 0.7, fontSize: 13, lineHeight: 1.5 },
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
  sidebar: { borderRight: "1px solid #2222", paddingRight: 12 },
  sectionTitle: { margin: "0 0 8px", fontSize: 13, opacity: 0.7, textTransform: "uppercase", letterSpacing: 0.5 },
  list: { listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 4 },
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
  listMeta: { fontSize: 11, opacity: 0.6, fontFamily: "monospace", marginTop: 2 },
  main: { display: "flex", flexDirection: "column", gap: 12 },
  statsRow: { display: "flex", gap: 16, flexWrap: "wrap" },
  stat: {
    background: "#3b82f60a",
    border: "1px solid #3b82f622",
    borderRadius: 6,
    padding: "6px 12px",
    minWidth: 60,
  },
  statLabel: { fontSize: 11, opacity: 0.6, textTransform: "uppercase", letterSpacing: 0.5 },
  statValue: { fontSize: 18, fontFamily: "monospace", fontWeight: 600 },
  description: { fontSize: 13, opacity: 0.75, margin: "4px 0 8px" },
  details: { fontSize: 12 },
  pre: {
    background: "#0001",
    padding: 10,
    borderRadius: 4,
    fontSize: 11,
    overflow: "auto",
  },
  frontierLayout: { display: "flex", flexDirection: "column", gap: 16 },
  table: { borderCollapse: "collapse", fontSize: 12 },
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
};
