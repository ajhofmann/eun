import { useState } from "react";
import type { CSSProperties } from "react";
import type { Candidate } from "./GraphCanvas";
import InteractiveGraphCanvas from "./InteractiveGraphCanvas";

type Construction = "moser_hex" | "engel_moser" | "moser_ring" | "moser" | "cyclotomic" | "erdos_grid";
type WindowKind = "ball" | "box" | "ellipsoid" | "all";
type VisibleWindowKind = "visible_disk" | "coeff_box";

const CONSTRUCTIONS: { id: Construction; label: string; tagline: string }[] = [
  {
    id: "moser_hex",
    label: "Moser visible disk",
    tagline: "Rank-4 Z[i, ζ] lattice filtered by visible-plane radius.",
  },
  {
    id: "engel_moser",
    label: "Engel 18-unit Moser",
    tagline: "The rank-4 18-unit lattice behind Engel et al. 2025.",
  },
  {
    id: "moser_ring",
    label: "Moser ring",
    tagline: "Common-denominator ring model with more exact unit directions.",
  },
  {
    id: "moser",
    label: "Moser coefficient box",
    tagline: "Full coefficient box in the rank-4 Moser-style lattice.",
  },
  {
    id: "cyclotomic",
    label: "Cyclotomic cut-and-project",
    tagline: "Z[ζ_m] points filtered by a hidden-space window.",
  },
  {
    id: "erdos_grid",
    label: "Erdős grid",
    tagline: "Rectangular integer grid with unit distance √K.",
  },
];

const PARAM_HELP: Record<string, string> = {
  zeta_order: "Primitive root order; 6 reproduces the classic Moser lattice.",
  coeff_bound: "Half-width B of the integer coefficient box {−B, …, B}.",
  visible_radius: "Disk radius in the visible plane used to filter points.",
  denom_power: "Common denominator exponent k; vertices are numerator coefficients over 3^k.",
  visible_window_kind: "Use a visible disk or the whole coefficient box.",
  m: "Cyclotomic order; m = 12 gives Z[ζ₁₂].",
  R: "Window radius in hidden space.",
  window_kind: "Hidden-space window shape used by the cut-and-project.",
  translation_seed: "Random offset seed for the hidden-space window center.",
  translation_scale: "Magnitude of the random translation per coordinate.",
  K: "Squared unit distance for the integer grid (e.g. K = 65).",
  grid_m: "Side length of the square grid.",
  mx: "Optional grid width override.",
  my: "Optional grid height override.",
};

const STYLES_CSS = `
@keyframes eud-pulse {
  0%, 100% { transform: scale(0.8); opacity: 0.35; }
  50% { transform: scale(1); opacity: 1; }
}
.eud-loading-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  margin: 0 2px;
  animation: eud-pulse 1.1s ease-in-out infinite;
}
.eud-loading-dot:nth-child(2) { animation-delay: 0.16s; }
.eud-loading-dot:nth-child(3) { animation-delay: 0.32s; }

.eud-input:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.7);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
}

.eud-primary-btn:not(:disabled):hover {
  background: #2563eb;
}
.eud-primary-btn:disabled {
  cursor: progress;
  opacity: 0.85;
}

.eud-tool-btn:not(:disabled):hover {
  background: rgba(15, 23, 42, 0.06);
}
.eud-neighbor:hover {
  background: rgba(245, 158, 11, 0.22);
}
`;

type ExplorerMode = "single" | "compare";

interface CompareResultEntry {
  id: Construction;
  label: string;
  candidate?: Candidate;
  source?: { n: number; e: number; params: Record<string, unknown> };
  error?: string;
}

const COMPARE_CONSTRUCTIONS: Construction[] = [
  "moser_hex",
  "engel_moser",
  "moser_ring",
  "moser",
  "cyclotomic",
  "erdos_grid",
];

const COMPARE_QUICK_PICKS = [25, 36, 49, 64, 81, 100, 144, 200, 400];

export default function ConstructionExplorer() {
  const [mode, setMode] = useState<ExplorerMode>("single");

  const [construction, setConstruction] = useState<Construction>("moser_hex");
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [compareTargetN, setCompareTargetN] = useState("64");
  const [compareSelected, setCompareSelected] = useState<Construction[]>(
    COMPARE_CONSTRUCTIONS,
  );
  const [compareResults, setCompareResults] = useState<CompareResultEntry[] | null>(null);
  const [compareTargetUsed, setCompareTargetUsed] = useState<number | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const [zetaOrder, setZetaOrder] = useState("6");
  const [coeffBound, setCoeffBound] = useState("4");
  const [visibleRadius, setVisibleRadius] = useState("4");
  const [denomPower, setDenomPower] = useState("1");
  const [visibleWindowKind, setVisibleWindowKind] = useState<VisibleWindowKind>("visible_disk");

  const [cyclotomicM, setCyclotomicM] = useState("12");
  const [cyclotomicR, setCyclotomicR] = useState("2.5");
  const [windowKind, setWindowKind] = useState<WindowKind>("ball");
  const [translationSeed, setTranslationSeed] = useState("");
  const [translationScale, setTranslationScale] = useState("0.5");

  const [gridK, setGridK] = useState("65");
  const [gridM, setGridM] = useState("12");
  const [gridMx, setGridMx] = useState("");
  const [gridMy, setGridMy] = useState("");

  const active = CONSTRUCTIONS.find((item) => item.id === construction) ?? CONSTRUCTIONS[0];

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ construction, params: paramsForConstruction() }),
      });
      if (!response.ok) {
        throw new Error(await errorMessage(response));
      }
      setCandidate((await response.json()) as Candidate);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleCompare() {
    const targetN = Number.parseInt(compareTargetN, 10);
    if (!Number.isFinite(targetN) || targetN < 4) {
      setCompareError("target n must be a positive integer ≥ 4");
      return;
    }
    if (compareSelected.length === 0) {
      setCompareError("pick at least one construction to compare");
      return;
    }
    setCompareLoading(true);
    setCompareError(null);
    try {
      const response = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_n: targetN,
          constructions: compareSelected,
        }),
      });
      if (!response.ok) {
        throw new Error(await errorMessage(response));
      }
      const body = (await response.json()) as {
        target_n: number;
        results: CompareResultEntry[];
      };
      setCompareResults(body.results);
      setCompareTargetUsed(body.target_n);
    } catch (err) {
      setCompareError(err instanceof Error ? err.message : String(err));
    } finally {
      setCompareLoading(false);
    }
  }

  function toggleCompareConstruction(id: Construction) {
    setCompareSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  function paramsForConstruction(): Record<string, number | string> {
    if (construction === "moser_hex") {
      return {
        zeta_order: intValue(zetaOrder),
        coeff_bound: intValue(coeffBound),
        visible_radius: floatValue(visibleRadius),
      };
    }
    if (construction === "moser") {
      return {
        zeta_order: intValue(zetaOrder),
        coeff_bound: intValue(coeffBound),
      };
    }
    if (construction === "engel_moser") {
      return {
        coeff_bound: intValue(coeffBound),
        visible_radius: floatValue(visibleRadius),
        window_kind: visibleWindowKind,
      };
    }
    if (construction === "moser_ring") {
      return {
        denom_power: intValue(denomPower),
        coeff_bound: intValue(coeffBound),
        visible_radius: floatValue(visibleRadius),
        window_kind: visibleWindowKind,
      };
    }
    if (construction === "cyclotomic") {
      return {
        m: intValue(cyclotomicM),
        coeff_bound: intValue(coeffBound),
        R: floatValue(cyclotomicR),
        window_kind: windowKind,
        ...(translationSeed.trim() ? { translation_seed: intValue(translationSeed) } : {}),
        translation_scale: floatValue(translationScale),
      };
    }
    return {
      K: intValue(gridK),
      m: intValue(gridM),
      ...(gridMx.trim() ? { mx: intValue(gridMx) } : {}),
      ...(gridMy.trim() ? { my: intValue(gridMy) } : {}),
    };
  }

  return (
    <div style={styles.stack}>
      <style>{STYLES_CSS}</style>
      <div style={styles.modeBar}>
        <div style={styles.modeTabs}>
          <button
            type="button"
            onClick={() => setMode("single")}
            style={{
              ...styles.modeTab,
              ...(mode === "single" ? styles.modeTabActive : null),
            }}
          >
            single
          </button>
          <button
            type="button"
            onClick={() => setMode("compare")}
            style={{
              ...styles.modeTab,
              ...(mode === "compare" ? styles.modeTabActive : null),
            }}
          >
            compare at n
          </button>
        </div>
        <p style={styles.modeHint}>
          {mode === "single"
            ? "Generate one construction and explore it in detail."
            : "Build every selected construction at the same n and inspect them side by side."}
        </p>
      </div>

      {mode === "compare" ? renderCompareMode() : renderSingleMode()}
    </div>
  );

  function renderSingleMode() {
    return (
      <>
      <section style={styles.card}>
        <div style={styles.headerRow}>
          <div style={styles.headerCopy}>
            <h2 style={styles.h2}>Interactive graph explorer</h2>
            <p style={styles.description}>
              Generate a unit-distance construction live, then hover any vertex or edge
              to see how the graph connects. Click to pin a node and dive into its
              exact coefficient coordinates.
            </p>
          </div>
          <button
            type="button"
            className="eud-primary-btn"
            style={styles.primaryButton}
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? (
              <span style={styles.loadingLabel}>
                generating
                <span style={styles.loadingDots}>
                  <span className="eud-loading-dot" />
                  <span className="eud-loading-dot" />
                  <span className="eud-loading-dot" />
                </span>
              </span>
            ) : (
              "generate graph"
            )}
          </button>
        </div>

        <div style={styles.constructionRow}>
          {CONSTRUCTIONS.map((item) => {
            const isActive = item.id === construction;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setConstruction(item.id)}
                style={{
                  ...styles.constructionPill,
                  ...(isActive ? styles.constructionPillActive : null),
                }}
              >
                <span style={styles.constructionPillLabel}>{item.label}</span>
                <span style={styles.constructionPillTag}>{item.tagline}</span>
              </button>
            );
          })}
        </div>

        <div style={styles.formGrid}>{renderParameterInputs()}</div>

        {error && <div style={styles.error}>generation failed: {error}</div>}
      </section>

      {candidate ? (
        <section style={styles.canvasCard}>
          <div style={styles.statsRow}>
            <Stat label="family" value={candidate.family} accent="slate" />
            <Stat label="n" value={candidate.n} accent="blue" />
            <Stat label="e" value={candidate.e} accent="blue" />
            <Stat label="e/n" value={candidate.density.toFixed(3)} accent="amber" />
            <Stat label="|U|" value={candidate.unit_vectors?.length ?? "?"} accent="slate" />
          </div>
          <InteractiveGraphCanvas candidate={candidate} />
          <details style={styles.details}>
            <summary style={styles.detailsSummary}>raw params</summary>
            <pre style={styles.pre}>{JSON.stringify(candidate.params, null, 2)}</pre>
          </details>
        </section>
      ) : (
        <section style={styles.emptyState}>
          <strong style={styles.emptyTitle}>{active.label}</strong>
          <p style={styles.emptyText}>{active.tagline}</p>
          <p style={styles.emptyHint}>
            Tune the parameters above and hit “generate graph” to start exploring.
          </p>
        </section>
      )}
      </>
    );
  }

  function renderCompareMode() {
    const target = compareTargetUsed;
    const successful = (compareResults ?? []).filter(
      (entry): entry is CompareResultEntry & { candidate: Candidate } => Boolean(entry.candidate),
    );
    const ranked = [...successful].sort(
      (a, b) => b.candidate.e - a.candidate.e || b.candidate.density - a.candidate.density,
    );
    const winner = ranked[0] ?? null;
    const orderedResults = [
      ...ranked,
      ...(compareResults ?? []).filter((entry) => !entry.candidate),
    ];
    return (
      <>
        <section style={styles.card}>
          <div style={styles.headerRow}>
            <div style={styles.headerCopy}>
              <h2 style={styles.h2}>Compare constructions at a fixed n</h2>
              <p style={styles.description}>
                Pick a target n and the constructions you want to inspect. The server
                builds each one, then greedy-peels them all down to the same n so you can
                compare structure and density head-to-head.
              </p>
            </div>
            <button
              type="button"
              className="eud-primary-btn"
              style={styles.primaryButton}
              onClick={handleCompare}
              disabled={compareLoading}
            >
              {compareLoading ? (
                <span style={styles.loadingLabel}>
                  comparing
                  <span style={styles.loadingDots}>
                    <span className="eud-loading-dot" />
                    <span className="eud-loading-dot" />
                    <span className="eud-loading-dot" />
                  </span>
                </span>
              ) : (
                "compare"
              )}
            </button>
          </div>

          <div style={styles.compareControls}>
            <label style={styles.field}>
              <span style={styles.label}>target n</span>
              <input
                type="number"
                className="eud-input"
                value={compareTargetN}
                min={4}
                max={600}
                onChange={(event) => setCompareTargetN(event.target.value)}
                style={styles.input}
              />
              <span style={styles.help}>between 4 and 600 inclusive</span>
            </label>
            <div style={styles.field}>
              <span style={styles.label}>quick picks</span>
              <div style={styles.quickPickRow}>
                {COMPARE_QUICK_PICKS.map((n) => {
                  const isActive = compareTargetN === String(n);
                  return (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setCompareTargetN(String(n))}
                      style={{
                        ...styles.quickPickChip,
                        ...(isActive ? styles.quickPickChipActive : null),
                      }}
                    >
                      {n}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div style={styles.compareConstructionsHeader}>
            <span style={styles.label}>include</span>
            <div style={styles.constructionRow}>
              {CONSTRUCTIONS.filter((c) => COMPARE_CONSTRUCTIONS.includes(c.id)).map(
                (item) => {
                  const isActive = compareSelected.includes(item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => toggleCompareConstruction(item.id)}
                      style={{
                        ...styles.constructionPill,
                        ...(isActive ? styles.constructionPillActive : null),
                      }}
                    >
                      <span style={styles.constructionPillLabel}>{item.label}</span>
                      <span style={styles.constructionPillTag}>{item.tagline}</span>
                    </button>
                  );
                },
              )}
            </div>
          </div>

          {compareError && (
            <div style={styles.error}>comparison failed: {compareError}</div>
          )}
        </section>

        {compareResults ? (
          <section style={styles.canvasCard}>
            <div style={styles.compareHeader}>
              <div>
                <h3 style={styles.compareTitle}>
                  Side-by-side at <span style={styles.compareTargetN}>n = {target}</span>
                </h3>
                <p style={styles.compareSubtitle}>
                  Each canvas is a greedy-peeled subgraph of the same target size.
                </p>
              </div>
              {winner && (
                <div style={styles.winnerBadge}>
                  winner: {winner.label} · e={winner.candidate.e} · e/n=
                  {winner.candidate.density.toFixed(3)}
                </div>
              )}
            </div>
            <div style={styles.compareGrid}>
              {orderedResults.map((entry, index) => (
                <CompareCard key={entry.id} entry={entry} rank={entry.candidate ? index + 1 : undefined} />
              ))}
            </div>
          </section>
        ) : (
          <section style={styles.emptyState}>
            <strong style={styles.emptyTitle}>Compare at fixed n</strong>
            <p style={styles.emptyText}>
              Pick a target n above and hit “compare” to build every selected
              construction at the same size, then peel each down to exactly n.
            </p>
          </section>
        )}
      </>
    );
  }

  function renderParameterInputs() {
    if (construction === "erdos_grid") {
      return (
        <>
          <NumberField label="K" name="K" value={gridK} onChange={setGridK} min={1} />
          <NumberField
            label="side m"
            name="grid_m"
            value={gridM}
            onChange={setGridM}
            min={1}
          />
          <NumberField
            label="mx (optional)"
            name="mx"
            value={gridMx}
            onChange={setGridMx}
            min={1}
          />
          <NumberField
            label="my (optional)"
            name="my"
            value={gridMy}
            onChange={setGridMy}
            min={1}
          />
        </>
      );
    }

    if (construction === "cyclotomic") {
      return (
        <>
          <NumberField
            label="m"
            name="m"
            value={cyclotomicM}
            onChange={setCyclotomicM}
            min={3}
          />
          <NumberField
            label="coeff bound"
            name="coeff_bound"
            value={coeffBound}
            onChange={setCoeffBound}
            min={1}
          />
          <NumberField
            label="R"
            name="R"
            value={cyclotomicR}
            onChange={setCyclotomicR}
            min={0.1}
            step={0.1}
          />
          <label style={styles.field}>
            <span style={styles.label}>window</span>
            <select
              className="eud-input"
              value={windowKind}
              onChange={(event) => setWindowKind(event.target.value as WindowKind)}
              style={styles.input}
            >
              <option value="ball">ball</option>
              <option value="box">box</option>
              <option value="ellipsoid">ellipsoid</option>
              <option value="all">all (no window)</option>
            </select>
            <span style={styles.help}>{PARAM_HELP.window_kind}</span>
          </label>
          <NumberField
            label="translation seed"
            name="translation_seed"
            value={translationSeed}
            onChange={setTranslationSeed}
            min={0}
          />
          <NumberField
            label="translation scale"
            name="translation_scale"
            value={translationScale}
            onChange={setTranslationScale}
            min={0}
            step={0.1}
          />
        </>
      );
    }

    if (construction === "engel_moser" || construction === "moser_ring") {
      return (
        <>
          {construction === "moser_ring" && (
            <NumberField
              label="denominator power"
              name="denom_power"
              value={denomPower}
              onChange={setDenomPower}
              min={0}
            />
          )}
          <NumberField
            label="coeff bound"
            name="coeff_bound"
            value={coeffBound}
            onChange={setCoeffBound}
            min={1}
          />
          <NumberField
            label="visible radius"
            name="visible_radius"
            value={visibleRadius}
            onChange={setVisibleRadius}
            min={0.1}
            step={0.1}
          />
          <label style={styles.field}>
            <span style={styles.label}>window</span>
            <select
              className="eud-input"
              value={visibleWindowKind}
              onChange={(event) => setVisibleWindowKind(event.target.value as VisibleWindowKind)}
              style={styles.input}
            >
              <option value="visible_disk">visible disk</option>
              <option value="coeff_box">coefficient box</option>
            </select>
            <span style={styles.help}>{PARAM_HELP.visible_window_kind}</span>
          </label>
        </>
      );
    }

    return (
      <>
        <NumberField
          label="zeta order"
          name="zeta_order"
          value={zetaOrder}
          onChange={setZetaOrder}
          min={3}
        />
        <NumberField
          label="coeff bound"
          name="coeff_bound"
          value={coeffBound}
          onChange={setCoeffBound}
          min={1}
        />
        {construction === "moser_hex" && (
          <NumberField
            label="visible radius"
            name="visible_radius"
            value={visibleRadius}
            onChange={setVisibleRadius}
            min={0.1}
            step={0.1}
          />
        )}
      </>
    );
  }
}

function NumberField({
  label,
  name,
  value,
  onChange,
  min,
  step = 1,
}: {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  min?: number;
  step?: number;
}) {
  return (
    <label style={styles.field}>
      <span style={styles.label}>{label}</span>
      <input
        type="number"
        className="eud-input"
        value={value}
        min={min}
        step={step}
        onChange={(event) => onChange(event.target.value)}
        style={styles.input}
      />
      {PARAM_HELP[name] && <span style={styles.help}>{PARAM_HELP[name]}</span>}
    </label>
  );
}

function CompareCard({ entry, rank }: { entry: CompareResultEntry; rank?: number }) {
  if (!entry.candidate) {
    return (
      <div style={styles.compareCard}>
        <div style={styles.compareCardHeader}>
          <strong style={styles.compareCardTitle}>{entry.label}</strong>
          <span style={styles.compareCardId}>{entry.id}</span>
        </div>
        <div style={styles.compareError}>{entry.error ?? "no candidate produced"}</div>
      </div>
    );
  }
  const cand = entry.candidate;
  return (
    <div style={{ ...styles.compareCard, ...(rank === 1 ? styles.compareCardWinner : null) }}>
      <div style={styles.compareCardHeader}>
        <div style={styles.compareCardHeading}>
          <strong style={styles.compareCardTitle}>
            {rank ? `#${rank} ` : ""}
            {entry.label}
          </strong>
          {rank === 1 && <span style={styles.winnerChip}>winner</span>}
          <span style={styles.compareCardId}>{entry.id}</span>
        </div>
        <div style={styles.compareCardStats}>
          <span style={{ ...styles.miniStat, ...styles.miniStatBlue }}>n {cand.n}</span>
          <span style={{ ...styles.miniStat, ...styles.miniStatBlue }}>e {cand.e}</span>
          <span style={{ ...styles.miniStat, ...styles.miniStatAmber }}>
            e/n {cand.density.toFixed(3)}
          </span>
          <span style={{ ...styles.miniStat, ...styles.miniStatSlate }}>
            |U| {cand.unit_vectors?.length ?? "?"}
          </span>
        </div>
      </div>
      <InteractiveGraphCanvas candidate={cand} compact width={420} height={340} />
      {entry.source && (
        <div style={styles.compareSource}>
          built from n={entry.source.n}, e={entry.source.e}
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent: "blue" | "amber" | "slate";
}) {
  const style: CSSProperties = {
    ...styles.stat,
    ...(accent === "blue" ? styles.statBlue : null),
    ...(accent === "amber" ? styles.statAmber : null),
    ...(accent === "slate" ? styles.statSlate : null),
  };
  return (
    <div style={style}>
      <div style={styles.statLabel}>{label}</div>
      <div style={styles.statValue}>{value}</div>
    </div>
  );
}

function intValue(value: string): number {
  return Number.parseInt(value, 10);
}

function floatValue(value: string): number {
  return Number.parseFloat(value);
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body.detail ?? body);
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

const styles: Record<string, CSSProperties> = {
  stack: { display: "flex", flexDirection: "column", gap: 18 },
  card: {
    border: "1px solid rgba(15, 23, 42, 0.1)",
    borderRadius: 14,
    padding: 18,
    background: "#fff",
    boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
  },
  canvasCard: {
    border: "1px solid rgba(15, 23, 42, 0.1)",
    borderRadius: 14,
    padding: 18,
    background: "#fff",
    boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: 18,
    alignItems: "flex-start",
    marginBottom: 16,
  },
  headerCopy: { minWidth: 0 },
  h2: { margin: "0 0 6px", fontSize: 20, fontWeight: 600, letterSpacing: -0.2 },
  description: {
    fontSize: 13,
    opacity: 0.78,
    lineHeight: 1.6,
    margin: 0,
    maxWidth: 560,
  },
  constructionRow: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: 8,
    marginBottom: 16,
  },
  constructionPill: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 4,
    padding: "10px 12px",
    border: "1px solid rgba(15, 23, 42, 0.12)",
    borderRadius: 10,
    background: "rgba(15, 23, 42, 0.02)",
    cursor: "pointer",
    color: "inherit",
    textAlign: "left",
    fontFamily: "inherit",
    transition: "border-color 120ms ease, background 120ms ease, box-shadow 120ms ease",
  },
  constructionPillActive: {
    borderColor: "rgba(59, 130, 246, 0.7)",
    background: "rgba(59, 130, 246, 0.08)",
    boxShadow: "0 0 0 3px rgba(59, 130, 246, 0.12)",
  },
  constructionPillLabel: { fontSize: 13, fontWeight: 600 },
  constructionPillTag: { fontSize: 11, opacity: 0.7, lineHeight: 1.4 },
  formGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
    gap: 14,
    alignItems: "start",
  },
  field: { display: "flex", flexDirection: "column", gap: 6 },
  label: {
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    opacity: 0.62,
    fontWeight: 600,
  },
  input: {
    border: "1px solid rgba(15, 23, 42, 0.16)",
    borderRadius: 8,
    padding: "8px 10px",
    font: "inherit",
    color: "inherit",
    background: "#fff",
    transition: "border-color 120ms ease, box-shadow 120ms ease",
  },
  help: { fontSize: 11, opacity: 0.6, lineHeight: 1.45 },
  primaryButton: {
    border: "1px solid #3b82f6",
    background: "#3b82f6",
    color: "white",
    borderRadius: 8,
    padding: "9px 16px",
    cursor: "pointer",
    font: "inherit",
    fontWeight: 600,
    whiteSpace: "nowrap",
    transition: "background 120ms ease",
    minWidth: 140,
  },
  loadingLabel: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
  },
  loadingDots: {
    display: "inline-flex",
    alignItems: "center",
    color: "rgba(255, 255, 255, 0.9)",
  },
  error: {
    marginTop: 12,
    borderRadius: 8,
    padding: 10,
    background: "rgba(239, 68, 68, 0.08)",
    color: "#b91c1c",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontSize: 12,
    border: "1px solid rgba(239, 68, 68, 0.2)",
  },
  statsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
    gap: 10,
    marginBottom: 14,
  },
  stat: {
    border: "1px solid rgba(15, 23, 42, 0.08)",
    background: "rgba(15, 23, 42, 0.02)",
    borderRadius: 10,
    padding: "8px 12px",
  },
  statBlue: {
    background: "rgba(59, 130, 246, 0.07)",
    border: "1px solid rgba(59, 130, 246, 0.2)",
  },
  statAmber: {
    background: "rgba(245, 158, 11, 0.08)",
    border: "1px solid rgba(245, 158, 11, 0.25)",
  },
  statSlate: {
    background: "rgba(15, 23, 42, 0.05)",
    border: "1px solid rgba(15, 23, 42, 0.12)",
  },
  statLabel: {
    fontSize: 10,
    opacity: 0.6,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    fontWeight: 600,
  },
  statValue: {
    fontSize: 18,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontWeight: 600,
    marginTop: 2,
  },
  details: { marginTop: 14, fontSize: 12 },
  detailsSummary: {
    cursor: "pointer",
    opacity: 0.7,
    userSelect: "none",
  },
  pre: {
    background: "rgba(15, 23, 42, 0.04)",
    padding: 12,
    borderRadius: 8,
    fontSize: 11,
    overflow: "auto",
    marginTop: 8,
  },
  emptyState: {
    border: "1px dashed rgba(15, 23, 42, 0.15)",
    borderRadius: 14,
    padding: 32,
    textAlign: "center",
    background: "rgba(15, 23, 42, 0.015)",
  },
  emptyTitle: {
    display: "block",
    fontSize: 15,
    fontWeight: 600,
    marginBottom: 6,
  },
  emptyText: {
    margin: 0,
    fontSize: 13,
    opacity: 0.7,
    maxWidth: 480,
    marginInline: "auto",
    lineHeight: 1.55,
  },
  emptyHint: {
    margin: "10px 0 0",
    fontSize: 12,
    opacity: 0.55,
  },
  modeBar: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  modeTabs: {
    display: "inline-flex",
    alignSelf: "flex-start",
    gap: 4,
    padding: 4,
    background: "rgba(15, 23, 42, 0.05)",
    borderRadius: 10,
  },
  modeTab: {
    border: "1px solid transparent",
    background: "transparent",
    color: "inherit",
    padding: "6px 12px",
    borderRadius: 6,
    fontFamily: "inherit",
    fontSize: 13,
    cursor: "pointer",
  },
  modeTabActive: {
    background: "#fff",
    borderColor: "rgba(15, 23, 42, 0.12)",
    boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
    fontWeight: 600,
  },
  modeHint: {
    margin: 0,
    fontSize: 12,
    opacity: 0.6,
  },
  compareControls: {
    display: "grid",
    gridTemplateColumns: "minmax(140px, 200px) minmax(0, 1fr)",
    gap: 18,
    alignItems: "flex-start",
    marginBottom: 14,
  },
  quickPickRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
  },
  quickPickChip: {
    border: "1px solid rgba(15, 23, 42, 0.15)",
    background: "rgba(15, 23, 42, 0.02)",
    color: "inherit",
    padding: "4px 10px",
    borderRadius: 999,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontSize: 12,
    cursor: "pointer",
  },
  quickPickChipActive: {
    background: "rgba(59, 130, 246, 0.12)",
    borderColor: "rgba(59, 130, 246, 0.6)",
    color: "#1d4ed8",
    fontWeight: 600,
  },
  compareConstructionsHeader: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    marginBottom: 12,
  },
  compareHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    alignItems: "flex-start",
    marginBottom: 12,
  },
  compareTitle: {
    margin: 0,
    fontSize: 16,
    fontWeight: 600,
  },
  compareTargetN: {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    color: "#b91c1c",
  },
  compareSubtitle: {
    margin: "4px 0 0",
    fontSize: 12,
    opacity: 0.65,
  },
  compareGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))",
    gap: 16,
  },
  compareCard: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
    border: "1px solid rgba(15, 23, 42, 0.1)",
    borderRadius: 12,
    padding: 12,
    background: "rgba(15, 23, 42, 0.015)",
  },
  compareCardWinner: {
    borderColor: "rgba(245, 158, 11, 0.55)",
    background: "rgba(245, 158, 11, 0.06)",
    boxShadow: "0 0 0 3px rgba(245, 158, 11, 0.10)",
  },
  compareCardHeader: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  compareCardHeading: {
    display: "flex",
    alignItems: "baseline",
    gap: 8,
    flexWrap: "wrap",
  },
  compareCardTitle: { fontSize: 14, fontWeight: 600 },
  winnerChip: {
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    borderRadius: 999,
    padding: "2px 8px",
    background: "rgba(245, 158, 11, 0.16)",
    border: "1px solid rgba(245, 158, 11, 0.35)",
    color: "#92400e",
    fontWeight: 700,
  },
  winnerBadge: {
    flexShrink: 0,
    border: "1px solid rgba(245, 158, 11, 0.35)",
    background: "rgba(245, 158, 11, 0.12)",
    color: "#92400e",
    borderRadius: 10,
    padding: "8px 10px",
    fontSize: 12,
    fontWeight: 700,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
  },
  compareCardId: {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontSize: 11,
    opacity: 0.6,
  },
  compareCardStats: {
    display: "flex",
    flexWrap: "wrap",
    gap: 4,
  },
  miniStat: {
    display: "inline-flex",
    alignItems: "center",
    fontSize: 11,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    padding: "2px 8px",
    borderRadius: 999,
    border: "1px solid transparent",
    background: "rgba(15, 23, 42, 0.04)",
  },
  miniStatBlue: {
    background: "rgba(59, 130, 246, 0.1)",
    borderColor: "rgba(59, 130, 246, 0.3)",
    color: "#1d4ed8",
  },
  miniStatAmber: {
    background: "rgba(245, 158, 11, 0.12)",
    borderColor: "rgba(245, 158, 11, 0.35)",
    color: "#92400e",
  },
  miniStatSlate: {
    background: "rgba(15, 23, 42, 0.06)",
    borderColor: "rgba(15, 23, 42, 0.15)",
    color: "#1f2937",
  },
  compareSource: {
    fontSize: 11,
    opacity: 0.6,
  },
  compareError: {
    padding: 12,
    background: "rgba(239, 68, 68, 0.08)",
    border: "1px solid rgba(239, 68, 68, 0.25)",
    borderRadius: 8,
    color: "#b91c1c",
    fontSize: 12,
  },
};
