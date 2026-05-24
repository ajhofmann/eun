import { FrontierRow } from "../App";

interface GalleryPoint {
  n: number;
  e: number;
  source: string;
  name: string;
}

interface Props {
  rows: FrontierRow[];
  galleryRows?: GalleryPoint[];
  width?: number;
  height?: number;
}

const COLORS: Record<string, string> = {
  known_bounds: "#444444",
  engel_2025: "#7c3aed",
  erdos_grid: "#1f77b4",
  triangular: "#2ca02c",
  moser_hex: "#d62728",
  cyclotomic: "#ff8800",
  moser: "#8b5cf6",
  biquadratic: "#ef4444",
};

function colorFor(source: string): string {
  return COLORS[source] ?? "#888";
}

export default function FrontierPlot({
  rows,
  galleryRows = [],
  width = 900,
  height = 480,
}: Props) {
  if (rows.length === 0) return <p style={{ opacity: 0.6 }}>loading frontier…</p>;

  const padL = 56,
    padR = 16,
    padT = 16,
    padB = 40;
  const innerW = width - padL - padR;
  const innerH = height - padT - padB;

  const allRows = [...rows, ...galleryRows.map((g) => ({ ...g, density: g.e / g.n }))];
  const xs = allRows.map((r) => r.n).filter((x) => x > 0);
  const ys = allRows.map((r) => r.e / r.n);

  const xMin = Math.log10(Math.max(1, Math.min(...xs)));
  const xMax = Math.log10(Math.max(...xs));
  const yMin = 0;
  const yMax = Math.max(...ys) * 1.05;

  const sx = (n: number) => padL + ((Math.log10(n) - xMin) / (xMax - xMin || 1)) * innerW;
  const sy = (d: number) => padT + (1 - (d - yMin) / (yMax - yMin || 1)) * innerH;

  const groups = new Map<string, FrontierRow[]>();
  for (const r of rows) {
    const key = (r.source ?? r.family ?? "?") as string;
    const g = groups.get(key) ?? [];
    g.push(r);
    groups.set(key, g);
  }

  const xTicks = [1, 10, 100, 1000];
  const yTicks: number[] = [];
  for (let y = 0; y <= yMax; y += 1) yTicks.push(y);

  return (
    <div>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ background: "#fafafa", border: "1px solid #ddd", borderRadius: 8, maxWidth: "100%" }}
      >
        {/* y grid */}
        {yTicks.map((y) => (
          <g key={`yt-${y}`}>
            <line
              x1={padL}
              x2={width - padR}
              y1={sy(y)}
              y2={sy(y)}
              stroke="#0001"
            />
            <text x={padL - 8} y={sy(y) + 4} textAnchor="end" fontSize={11} fill="#888">
              {y}
            </text>
          </g>
        ))}
        {/* x ticks */}
        {xTicks.map((x) => (
          <g key={`xt-${x}`}>
            <line x1={sx(x)} x2={sx(x)} y1={padT} y2={height - padB} stroke="#0001" />
            <text x={sx(x)} y={height - padB + 16} textAnchor="middle" fontSize={11} fill="#888">
              {x}
            </text>
          </g>
        ))}
        <text
          x={padL + innerW / 2}
          y={height - 6}
          textAnchor="middle"
          fontSize={12}
          fill="#444"
        >
          n (log scale)
        </text>
        <text
          transform={`translate(14, ${padT + innerH / 2}) rotate(-90)`}
          textAnchor="middle"
          fontSize={12}
          fill="#444"
        >
          e / n
        </text>

        {/* frontier curves */}
        {Array.from(groups.entries()).map(([source, gr]) => {
          const sorted = [...gr].sort((a, b) => a.n - b.n);
          const d = sorted
            .map((r, i) => `${i === 0 ? "M" : "L"} ${sx(r.n).toFixed(2)} ${sy(r.e / r.n).toFixed(2)}`)
            .join(" ");
          return (
            <g key={source}>
              <path d={d} fill="none" stroke={colorFor(source)} strokeWidth={1.5} opacity={0.9} />
              {sorted.map((r) => (
                <circle
                  key={`${source}-${r.n}`}
                  cx={sx(r.n)}
                  cy={sy(r.e / r.n)}
                  r={2.4}
                  fill={colorFor(source)}
                />
              ))}
            </g>
          );
        })}

        {/* gallery overlay */}
        {galleryRows.map((g) => (
          <g key={g.name}>
            <circle
              cx={sx(g.n)}
              cy={sy(g.e / g.n)}
              r={6}
              fill="none"
              stroke={colorFor(g.source)}
              strokeWidth={2}
              opacity={0.85}
            />
            <text
              x={sx(g.n) + 8}
              y={sy(g.e / g.n) + 3}
              fontSize={10}
              fill="#444"
              fontFamily="monospace"
            >
              {g.name}
            </text>
          </g>
        ))}
      </svg>

      <div style={{ display: "flex", gap: 16, marginTop: 8, flexWrap: "wrap" }}>
        {Array.from(groups.keys()).map((s) => (
          <span key={s} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <span
              style={{
                display: "inline-block",
                width: 12,
                height: 12,
                background: colorFor(s),
                borderRadius: 2,
              }}
            />
            {s}
          </span>
        ))}
        {galleryRows.length > 0 && (
          <span style={{ fontSize: 12, opacity: 0.6 }}>
            ◯ = gallery candidate (overlay; not part of frontier)
          </span>
        )}
      </div>
    </div>
  );
}
