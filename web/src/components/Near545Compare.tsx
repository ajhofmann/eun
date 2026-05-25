import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { Candidate } from "./GraphCanvas";
import InteractiveGraphCanvas from "./InteractiveGraphCanvas";

const DEMO_FILES = {
  uploaded: "uploaded_moser_disk_B2_R4.json",
  erdos: "erdos_grid_K65_20x27_n540.json",
  engel: "engel_moser_unpeeled_n543.json",
  context: "erdos_grid_K65_n545_peeled.json",
} as const;

export const NEAR545_GRAPHS = [
  {
    id: "uploaded",
    title: "Shared Z[i, ρ] picture",
    subtitle: "rank-4 cyclotomic · 12 unit directions",
    fileKey: "uploaded" as const,
    color: "#334155",
    summary:
      "Natural disk: B=2, |z|<4. This is the uploaded construction reproduced in this repo.",
  },
  {
    id: "erdos",
    title: "Classical Erdős grid",
    subtitle: "K=65, 20×27 · 16 unit directions",
    fileKey: "erdos" as const,
    color: "#2563eb",
    summary: "Natural rectangle; no peeling. Unit distance √65.",
  },
  {
    id: "engel",
    title: "Engel-Moser 18-unit disk",
    subtitle: "coeff_bound=2, R=4 · 18 unit directions",
    fileKey: "engel" as const,
    color: "#7c3aed",
    summary: "Natural visible disk; no peeling.",
  },
];

function demoBasePath(): string {
  const raw = import.meta.env.VITE_DEMO_BASE ?? "demo/near545";
  return raw.replace(/^\/+|\/+$/g, "");
}

export function demoAssetUrl(filename: string): string {
  const base = import.meta.env.BASE_URL;
  const prefix = base.endsWith("/") ? base : `${base}/`;
  return `${prefix}${demoBasePath()}/${filename}`;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={styles.stat}>
      <div style={styles.statLabel}>{label}</div>
      <div style={styles.statValue}>{value}</div>
    </div>
  );
}

function GraphCard({
  title,
  subtitle,
  summary,
  color,
  candidate,
}: {
  title: string;
  subtitle: string;
  summary: string;
  color: string;
  candidate?: Candidate;
}) {
  const cardRef = useRef<HTMLElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    function handleFullscreenChange() {
      setIsFullscreen(document.fullscreenElement === cardRef.current);
    }
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  async function toggleFullscreen() {
    if (document.fullscreenElement === cardRef.current) {
      await document.exitFullscreen();
      return;
    }
    await cardRef.current?.requestFullscreen();
  }

  return (
    <article
      ref={cardRef}
      className="eud-x-graph-card"
      style={{
        ...styles.xCard,
        ...(isFullscreen ? styles.xCardFullscreen : null),
        borderTopColor: color,
      }}
    >
      <div style={styles.xCardHeader}>
        <div>
          <h3 style={styles.xCardTitle}>{title}</h3>
          <p style={styles.xCardSubtitle}>{subtitle}</p>
        </div>
        <button type="button" style={styles.xFullscreenBtn} onClick={toggleFullscreen}>
          {isFullscreen ? "exit full screen" : "full screen"}
        </button>
      </div>
      {candidate ? (
        <>
          <div style={styles.xStats}>
            <Stat label="n" value={candidate.n} />
            <Stat label="e" value={candidate.e} />
            <Stat label="e/n" value={candidate.density.toFixed(3)} />
            <Stat label="|U|" value={candidate.unit_vectors?.length ?? "?"} />
          </div>
          <InteractiveGraphCanvas
            candidate={candidate}
            compact
            width={isFullscreen ? 1180 : 380}
            height={isFullscreen ? 760 : 330}
          />
          <details style={styles.details}>
            <summary>params</summary>
            <pre style={styles.pre}>{JSON.stringify(candidate.params, null, 2)}</pre>
          </details>
        </>
      ) : (
        <p style={styles.description}>loading graph…</p>
      )}
      <p style={styles.description}>{summary}</p>
    </article>
  );
}

export interface Near545CompareProps {
  /** Explorer-style headline for GitHub Pages; default keeps X-compare copy. */
  variant?: "explorer" | "x-compare";
  /** Hide extended caveat / quote-tweet section (Pages shell). */
  compactFooter?: boolean;
}

export default function Near545Compare({
  variant = "x-compare",
  compactFooter = false,
}: Near545CompareProps) {
  const [candidates, setCandidates] = useState<Record<string, Candidate>>({});
  const [context, setContext] = useState<Candidate | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const entries = await Promise.all(
          NEAR545_GRAPHS.map(async (item) => {
            const file = DEMO_FILES[item.fileKey];
            const url = demoAssetUrl(file);
            const response = await fetch(url);
            if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
            return [item.id, (await response.json()) as Candidate] as const;
          }),
        );
        const contextUrl = demoAssetUrl(DEMO_FILES.context);
        const contextResponse = await fetch(contextUrl);
        const contextCandidate = contextResponse.ok
          ? ((await contextResponse.json()) as Candidate)
          : null;
        if (!cancelled) {
          setCandidates(Object.fromEntries(entries));
          setContext(contextCandidate);
        }
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : String(err));
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const uploaded = candidates.uploaded;
  const erdos = candidates.erdos;
  const engel = candidates.engel;

  const rows = NEAR545_GRAPHS.map((item) => ({
    ...item,
    candidate: candidates[item.id],
  }));

  const explorerHero = variant === "explorer";

  return (
    <div style={styles.layout}>
      <style>{`
        .eud-x-graph-card:fullscreen {
          width: 100vw;
          height: 100vh;
          box-sizing: border-box;
          overflow: auto;
          background: white;
        }
        .eud-x-graph-card:fullscreen canvas {
          max-width: none !important;
        }
      `}</style>
      <section style={styles.xHero}>
        <div>
          <h2 style={styles.h2}>
            {explorerHero
              ? "Three natural finite unit-distance constructions near n=545"
              : "The graph from X, the classical grid, and a better finite picture"}
          </h2>
          <p style={styles.lead}>
            {explorerHero
              ? "Interactive unit-distance graphs at roughly the same scale: the shared Z[i, ρ] disk, a classical Erdős grid, and a natural unpeeled Engel-Moser 18-unit disk."
              : "The uploaded picture is real and reproducible, but at its own scale it is not stronger than a classical Erdős grid. The three main cards below are all natural, unpeeled shapes/windows near n=545; the stronger small finite picture is the Engel-Moser 18-unit disk."}
          </p>
        </div>
        <div style={styles.xClaimBox}>
          <div style={styles.xClaimLabel}>Safe headline</div>
          <div style={styles.xClaimText}>
            Shared graph: n=545, e=2396 · Classical K=65 grid: n=540, e=2584 ·
            Engel-Moser: n=543, e=2914
          </div>
        </div>
      </section>

      {loadError && <div style={styles.error}>comparison load failed: {loadError}</div>}

      <section>
        <h2 style={styles.h2}>Three graphs to compare</h2>
        <div style={styles.xCardGrid}>
          {rows.map((row) => (
            <GraphCard
              key={row.id}
              title={row.title}
              subtitle={row.subtitle}
              summary={row.summary}
              color={row.color}
              candidate={row.candidate}
            />
          ))}
        </div>
      </section>

      <section>
        <h2 style={styles.h2}>Numbers, with the caveats visible</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>graph</th>
              <th style={styles.th}>n</th>
              <th style={styles.th}>e</th>
              <th style={styles.th}>e/n</th>
              <th style={styles.th}>|U|</th>
              <th style={styles.th}>what is fair to say</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={styles.td}>uploaded Z[i,ρ]</td>
              <td style={styles.td}>{uploaded?.n ?? "loading"}</td>
              <td style={styles.td}>{uploaded?.e ?? "loading"}</td>
              <td style={styles.td}>{uploaded ? uploaded.density.toFixed(3) : "loading"}</td>
              <td style={styles.td}>{uploaded?.unit_vectors?.length ?? "loading"}</td>
              <td style={styles.td}>the exact graph in the shared picture</td>
            </tr>
            <tr>
              <td style={styles.td}>Erdős grid K=65</td>
              <td style={styles.td}>{erdos?.n ?? "loading"}</td>
              <td style={styles.td}>{erdos?.e ?? "loading"}</td>
              <td style={styles.td}>{erdos ? erdos.density.toFixed(3) : "loading"}</td>
              <td style={styles.td}>{erdos?.unit_vectors?.length ?? "loading"}</td>
              <td style={styles.td}>beats the uploaded edge count with five fewer vertices</td>
            </tr>
            <tr style={styles.winRow}>
              <td style={styles.td}>Engel-Moser witness</td>
              <td style={styles.td}>{engel?.n ?? "loading"}</td>
              <td style={styles.td}>{engel?.e ?? "loading"}</td>
              <td style={styles.td}>{engel ? engel.density.toFixed(3) : "loading"}</td>
              <td style={styles.td}>{engel?.unit_vectors?.length ?? "loading"}</td>
              <td style={styles.td}>beats both as a natural unpeeled graph near n=545</td>
            </tr>
          </tbody>
        </table>
        {!compactFooter && (
          <p style={styles.description}>
            Separate same-n sanity check: after greedy peeling to exactly n=545, the saved
            K=65 grid has e={context?.e ?? "..."} from a 30×30 seed, while the peeled
            Engel-Moser candidate has e=3189. That same-n comparison is useful, but the
            three graphs on this page are the cleaner unpeeled visual comparison. This is not
            a claim that no better grid or non-grid construction exists; it is the exact
            reproducible comparison produced by this repo.
          </p>
        )}
        {compactFooter && engel && uploaded && erdos && (
          <p style={styles.description}>
            Engel-Moser has {(((engel.e - uploaded.e) / uploaded.e) * 100).toFixed(1)}% more
            edges than the shared graph and {(((engel.e - erdos.e) / erdos.e) * 100).toFixed(1)}%
            more than the nearby classical grid. All three panels are unpeeled natural
            shapes/windows.
          </p>
        )}
      </section>

      {!compactFooter && (
        <section style={styles.xCaveat}>
          <h2 style={styles.h2}>Recommended wording</h2>
          <p style={styles.description}>
            A quote tweet is fair if it avoids saying “the AI result is wrong” or “this is the
            new record.” A safer phrasing is:
          </p>
          <blockquote style={styles.quote}>
            I got nerd-sniped by this Erdős unit-distance graph that has been going around. The
            pictured Z[i,ρ] construction is real (n=545, e=2396), but a classical K=65 Erdős
            grid already gets e=2584 with n=540. I tried to find a more satisfying small finite
            picture: an unpeeled Engel-Moser 18-unit disk gets n=543, e=2914 at the same scale.
          </blockquote>
          <p style={styles.description}>
            The important caveat: Sawin/OpenAI is an asymptotic theorem. This page is about the
            specific finite picture being shared and a finite replacement that is stronger at
            roughly the same size.
          </p>
        </section>
      )}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  layout: { display: "flex", flexDirection: "column", gap: 24 },
  error: {
    padding: "10px 12px",
    background: "#ef444418",
    border: "1px solid #ef444444",
    borderRadius: 8,
    fontSize: 13,
  },
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
  description: { fontSize: 13, opacity: 0.85, margin: "4px 0 8px", lineHeight: 1.6 },
  details: { fontSize: 12 },
  pre: {
    background: "#0001",
    padding: 10,
    borderRadius: 4,
    fontSize: 11,
    overflow: "auto",
  },
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
  xHero: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1fr) minmax(260px, 380px)",
    gap: 18,
    alignItems: "start",
    border: "1px solid #2222",
    borderRadius: 12,
    padding: 18,
    background: "linear-gradient(135deg, #f8fafc, #eef2ff)",
  },
  xClaimBox: {
    border: "1px solid rgba(124, 58, 237, 0.25)",
    borderRadius: 10,
    padding: 14,
    background: "rgba(124, 58, 237, 0.08)",
  },
  xClaimLabel: {
    fontSize: 11,
    opacity: 0.65,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    fontWeight: 700,
    marginBottom: 6,
  },
  xClaimText: {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontSize: 13,
    lineHeight: 1.55,
    fontWeight: 600,
  },
  xCardGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))",
    gap: 16,
  },
  xCard: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
    border: "1px solid #2222",
    borderTop: "4px solid",
    borderRadius: 12,
    padding: 14,
    background: "#fff",
    boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
  },
  xCardFullscreen: {
    borderRadius: 0,
    padding: 24,
  },
  xCardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
  },
  xCardTitle: {
    margin: 0,
    fontSize: 16,
    fontWeight: 700,
  },
  xCardSubtitle: {
    margin: "3px 0 0",
    fontSize: 12,
    opacity: 0.65,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
  },
  xFullscreenBtn: {
    border: "1px solid #cbd5e1",
    background: "#fff",
    color: "#0f172a",
    borderRadius: 999,
    padding: "5px 10px",
    fontSize: 11,
    fontFamily: "inherit",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
  xStats: {
    display: "grid",
    gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
    gap: 8,
  },
  xCaveat: {
    border: "1px solid rgba(245, 158, 11, 0.35)",
    borderRadius: 12,
    padding: 16,
    background: "rgba(245, 158, 11, 0.06)",
  },
  quote: {
    margin: "12px 0",
    padding: "12px 14px",
    borderLeft: "4px solid #7c3aed",
    background: "#fff",
    borderRadius: 8,
    fontSize: 14,
    lineHeight: 1.6,
  },
};
