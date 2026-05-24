import { useEffect, useRef } from "react";

export interface Point {
  coeffs: number[];
  xy: [number, number];
}

export interface Candidate {
  family: string;
  params: Record<string, unknown>;
  n: number;
  e: number;
  density: number;
  points: Point[];
  edges: [number, number][];
}

interface Props {
  candidate: Candidate;
  width?: number;
  height?: number;
}

export default function GraphCanvas({ candidate, width = 800, height = 800 }: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, c.width, c.height);
    if (candidate.points.length === 0) return;

    const xs = candidate.points.map((p) => p.xy[0]);
    const ys = candidate.points.map((p) => p.xy[1]);
    const xMin = Math.min(...xs);
    const xMax = Math.max(...xs);
    const yMin = Math.min(...ys);
    const yMax = Math.max(...ys);
    const pad = 16;
    const sx = (c.width - 2 * pad) / Math.max(1e-9, xMax - xMin);
    const sy = (c.height - 2 * pad) / Math.max(1e-9, yMax - yMin);
    const s = Math.min(sx, sy);
    const ox = (c.width - s * (xMax + xMin)) / 2;
    const oy = (c.height + s * (yMax + yMin)) / 2;
    const project = (x: number, y: number): [number, number] => [
      ox + s * x,
      oy - s * y,
    ];

    ctx.strokeStyle = "#5aa9ff";
    ctx.lineWidth = 0.6;
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    for (const [i, j] of candidate.edges) {
      const [x0, y0] = project(...candidate.points[i].xy);
      const [x1, y1] = project(...candidate.points[j].xy);
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
    }
    ctx.stroke();
    ctx.globalAlpha = 1;

    ctx.fillStyle = "#222";
    for (const p of candidate.points) {
      const [x, y] = project(...p.xy);
      ctx.beginPath();
      ctx.arc(x, y, 1.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [candidate]);

  return (
    <canvas
      ref={ref}
      width={width}
      height={height}
      style={{
        width: "100%",
        maxWidth: width,
        background: "#fafafa",
        border: "1px solid #ddd",
        borderRadius: 8,
      }}
    />
  );
}
