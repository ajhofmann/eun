import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent, WheelEvent } from "react";
import type { Candidate, Point } from "./GraphCanvas";

interface Props {
  candidate: Candidate;
  width?: number;
  height?: number;
  /**
   * Compact mode hides the side detail panel and renders just the canvas with
   * an inline hover/pin readout. Intended for grid views like the compare tab.
   */
  compact?: boolean;
}

interface View {
  scale: number;
  tx: number;
  ty: number;
}

interface DragState {
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  moved: boolean;
}

const DEFAULT_VIEW: View = { scale: 1, tx: 0, ty: 0 };

// Hover hit radii (in canvas pixels). Vertex radius is generous so adjacency
// lights up before the cursor is right on top of the node.
const HOVER_VERTEX_RADIUS_PX = 14;
const HOVER_EDGE_PX = 5;

// Exponential ease rates per second.
const EASE_IN_RATE = 18;
const EASE_OUT_RATE = 10;

const PALETTE = {
  bg: "#fafbfd",
  gridMinor: "rgba(15, 23, 42, 0.045)",
  gridMajor: "rgba(15, 23, 42, 0.09)",
  edgeBase: [100, 116, 139] as const,
  nodeBase: [15, 23, 42] as const,
  edgeAccent: [245, 158, 11] as const,
  edgeHover: [14, 165, 233] as const,
  nodeFocal: [239, 68, 68] as const,
  nodeNeighbor: [245, 158, 11] as const,
  nodeHover: [14, 165, 233] as const,
  labelText: "rgba(15, 23, 42, 0.7)",
};

export default function InteractiveGraphCanvas({
  candidate,
  width = 880,
  height = 620,
  compact = false,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const hoverVertexRef = useRef<number | null>(null);
  const hoverEdgeRef = useRef<number | null>(null);
  const viewRef = useRef<View>(DEFAULT_VIEW);
  const lastFrameRef = useRef<number>(0);

  const nodeAnimRef = useRef<Float32Array>(new Float32Array(0));
  const focalAnimRef = useRef<Float32Array>(new Float32Array(0));
  const edgeAnimRef = useRef<Float32Array>(new Float32Array(0));
  const nodeTargetRef = useRef<Float32Array>(new Float32Array(0));
  const focalTargetRef = useRef<Float32Array>(new Float32Array(0));
  const edgeTargetRef = useRef<Float32Array>(new Float32Array(0));
  const xyRef = useRef<Float32Array>(new Float32Array(0));

  const [pinVertex, setPinVertex] = useState<number | null>(null);
  const [pinEdge, setPinEdge] = useState<number | null>(null);
  const [showLabels, setShowLabels] = useState(false);

  const baseProjection = useMemo(() => {
    if (candidate.points.length === 0) {
      return { base: new Float32Array(0) };
    }
    let xMin = Infinity;
    let xMax = -Infinity;
    let yMin = Infinity;
    let yMax = -Infinity;
    for (const p of candidate.points) {
      if (p.xy[0] < xMin) xMin = p.xy[0];
      if (p.xy[0] > xMax) xMax = p.xy[0];
      if (p.xy[1] < yMin) yMin = p.xy[1];
      if (p.xy[1] > yMax) yMax = p.xy[1];
    }
    const pad = 36;
    const sx = (width - 2 * pad) / Math.max(1e-9, xMax - xMin);
    const sy = (height - 2 * pad) / Math.max(1e-9, yMax - yMin);
    const s = Math.min(sx, sy);
    const ox = (width - s * (xMax + xMin)) / 2;
    const oy = (height + s * (yMax + yMin)) / 2;
    const base = new Float32Array(candidate.points.length * 2);
    for (let i = 0; i < candidate.points.length; i += 1) {
      base[i * 2] = ox + s * candidate.points[i].xy[0];
      base[i * 2 + 1] = oy - s * candidate.points[i].xy[1];
    }
    return { base };
  }, [candidate.points, width, height]);

  const adjacency = useMemo(() => {
    const adj: number[][] = Array.from(
      { length: candidate.points.length },
      () => [] as number[],
    );
    for (const [i, j] of candidate.edges) {
      adj[i]?.push(j);
      adj[j]?.push(i);
    }
    return adj.map((row) => row.sort((a, b) => a - b));
  }, [candidate.edges, candidate.points.length]);

  const incidentEdges = useMemo(() => {
    const out: number[][] = Array.from(
      { length: candidate.points.length },
      () => [] as number[],
    );
    for (let e = 0; e < candidate.edges.length; e += 1) {
      const [i, j] = candidate.edges[e];
      out[i]?.push(e);
      out[j]?.push(e);
    }
    return out;
  }, [candidate.edges, candidate.points.length]);

  // Reset transient state when a new candidate arrives.
  useEffect(() => {
    setPinVertex(null);
    setPinEdge(null);
    hoverVertexRef.current = null;
    hoverEdgeRef.current = null;
    viewRef.current = DEFAULT_VIEW;
    lastFrameRef.current = 0;
    const n = candidate.points.length;
    const m = candidate.edges.length;
    nodeAnimRef.current = new Float32Array(n);
    focalAnimRef.current = new Float32Array(n);
    edgeAnimRef.current = new Float32Array(m);
    nodeTargetRef.current = new Float32Array(n);
    focalTargetRef.current = new Float32Array(n);
    edgeTargetRef.current = new Float32Array(m);
    xyRef.current = new Float32Array(n * 2);
  }, [candidate]);

  // Animation loop.
  useEffect(() => {
    let raf = 0;
    let cancelled = false;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    function applyView() {
      const view = viewRef.current;
      const base = baseProjection.base;
      const xy = xyRef.current;
      const cx = width / 2;
      const cy = height / 2;
      for (let i = 0; i < base.length; i += 2) {
        xy[i] = cx + (base[i] - cx) * view.scale + view.tx;
        xy[i + 1] = cy + (base[i + 1] - cy) * view.scale + view.ty;
      }
    }

    function frame(now: number) {
      if (cancelled) return;
      const canvas = canvasRef.current;
      if (!canvas) {
        raf = requestAnimationFrame(frame);
        return;
      }
      if (lastFrameRef.current === 0) lastFrameRef.current = now;
      const dt = Math.min((now - lastFrameRef.current) / 1000, 0.05);
      lastFrameRef.current = now;

      const targetW = Math.round(width * dpr);
      const targetH = Math.round(height * dpr);
      if (canvas.width !== targetW || canvas.height !== targetH) {
        canvas.width = targetW;
        canvas.height = targetH;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        raf = requestAnimationFrame(frame);
        return;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const n = candidate.points.length;
      const m = candidate.edges.length;
      const nodeTarget = nodeTargetRef.current;
      const edgeTarget = edgeTargetRef.current;
      const focalTarget = focalTargetRef.current;
      const nodeAnim = nodeAnimRef.current;
      const edgeAnim = edgeAnimRef.current;
      const focalAnim = focalAnimRef.current;
      nodeTarget.fill(0);
      edgeTarget.fill(0);
      focalTarget.fill(0);

      const hv = hoverVertexRef.current;
      const he = hoverEdgeRef.current;
      const pv = pinVertex;
      const pe = pinEdge;

      if (hv !== null && hv < n) {
        nodeTarget[hv] = 1;
        focalTarget[hv] = 1;
        for (const ei of incidentEdges[hv] ?? []) {
          edgeTarget[ei] = 1;
          const [a, b] = candidate.edges[ei];
          const other = a === hv ? b : a;
          if (nodeTarget[other] < 0.82) nodeTarget[other] = 0.82;
        }
      }
      if (he !== null && he < m) {
        edgeTarget[he] = 1;
        const [a, b] = candidate.edges[he];
        if (nodeTarget[a] < 0.9) nodeTarget[a] = 0.9;
        if (nodeTarget[b] < 0.9) nodeTarget[b] = 0.9;
      }
      if (pv !== null && pv < n) {
        nodeTarget[pv] = 1;
        focalTarget[pv] = 1;
        for (const ei of incidentEdges[pv] ?? []) {
          if (edgeTarget[ei] < 0.95) edgeTarget[ei] = 0.95;
          const [a, b] = candidate.edges[ei];
          const other = a === pv ? b : a;
          if (nodeTarget[other] < 0.78) nodeTarget[other] = 0.78;
        }
      }
      if (pe !== null && pe < m) {
        edgeTarget[pe] = 1;
        const [a, b] = candidate.edges[pe];
        if (nodeTarget[a] < 0.95) nodeTarget[a] = 0.95;
        if (nodeTarget[b] < 0.95) nodeTarget[b] = 0.95;
      }

      // Ease toward targets with separate in/out rates.
      let maxNode = 0;
      let maxEdge = 0;
      for (let i = 0; i < n; i += 1) {
        const tgt = nodeTarget[i];
        const cur = nodeAnim[i];
        const k = 1 - Math.exp(-dt * (tgt > cur ? EASE_IN_RATE : EASE_OUT_RATE));
        const next = cur + (tgt - cur) * k;
        nodeAnim[i] = next;
        if (next > maxNode) maxNode = next;
        const ftgt = focalTarget[i];
        const fcur = focalAnim[i];
        const fk = 1 - Math.exp(-dt * (ftgt > fcur ? EASE_IN_RATE : EASE_OUT_RATE));
        focalAnim[i] = fcur + (ftgt - fcur) * fk;
      }
      for (let e = 0; e < m; e += 1) {
        const tgt = edgeTarget[e];
        const cur = edgeAnim[e];
        const k = 1 - Math.exp(-dt * (tgt > cur ? EASE_IN_RATE : EASE_OUT_RATE));
        const next = cur + (tgt - cur) * k;
        edgeAnim[e] = next;
        if (next > maxEdge) maxEdge = next;
      }
      const globalHighlight = Math.max(maxNode, maxEdge);

      applyView();
      const xy = xyRef.current;

      // Canvas background.
      ctx.fillStyle = PALETTE.bg;
      ctx.fillRect(0, 0, width, height);
      drawGrid(ctx, width, height, viewRef.current);

      // Base edges in one pass at a dim alpha that fades as something lights up.
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      const baseEdgeAlpha = 0.55 - 0.42 * globalHighlight;
      ctx.strokeStyle = rgba(PALETTE.edgeBase, baseEdgeAlpha);
      ctx.lineWidth = candidate.n > 2000 ? 0.5 : 0.75;
      ctx.beginPath();
      for (let e = 0; e < m; e += 1) {
        const [i, j] = candidate.edges[e];
        ctx.moveTo(xy[i * 2], xy[i * 2 + 1]);
        ctx.lineTo(xy[j * 2], xy[j * 2 + 1]);
      }
      ctx.stroke();

      // Highlighted edges (per-edge so each can have its own alpha and width).
      for (let e = 0; e < m; e += 1) {
        const intensity = edgeAnim[e];
        if (intensity < 0.02) continue;
        const [i, j] = candidate.edges[e];
        const isHovered = e === hoverEdgeRef.current;
        const color = isHovered ? PALETTE.edgeHover : PALETTE.edgeAccent;
        ctx.strokeStyle = rgba(color, 0.55 + 0.45 * intensity);
        ctx.lineWidth = 1.1 + 1.9 * intensity;
        ctx.beginPath();
        ctx.moveTo(xy[i * 2], xy[i * 2 + 1]);
        ctx.lineTo(xy[j * 2], xy[j * 2 + 1]);
        ctx.stroke();
      }

      // Base nodes at a single fill color, dimmed if a highlight is active.
      const baseRadius = candidate.n > 2000 ? 1.4 : candidate.n > 600 ? 1.9 : 2.6;
      ctx.fillStyle = rgba(PALETTE.nodeBase, 0.82 - 0.45 * globalHighlight);
      ctx.beginPath();
      for (let i = 0; i < n; i += 1) {
        ctx.moveTo(xy[i * 2] + baseRadius, xy[i * 2 + 1]);
        ctx.arc(xy[i * 2], xy[i * 2 + 1], baseRadius, 0, Math.PI * 2);
      }
      ctx.fill();

      // Highlighted nodes with halos.
      for (let i = 0; i < n; i += 1) {
        const intensity = nodeAnim[i];
        if (intensity < 0.02) continue;
        const focal = focalAnim[i];
        const px = xy[i * 2];
        const py = xy[i * 2 + 1];

        const isHoverV = i === hoverVertexRef.current;
        const isPinV = i === pinVertex;
        const isFocalNode = isHoverV || isPinV;
        const fillColor = isFocalNode
          ? (isHoverV ? PALETTE.nodeHover : PALETTE.nodeFocal)
          : PALETTE.nodeNeighbor;

        const haloColor = isFocalNode
          ? (isHoverV ? PALETTE.nodeHover : PALETTE.nodeFocal)
          : PALETTE.nodeNeighbor;
        const haloRadius = baseRadius + 6 + 8 * intensity + 5 * focal;
        const grad = ctx.createRadialGradient(px, py, baseRadius, px, py, haloRadius);
        grad.addColorStop(0, rgba(haloColor, 0.55 * intensity));
        grad.addColorStop(1, rgba(haloColor, 0));
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(px, py, haloRadius, 0, Math.PI * 2);
        ctx.fill();

        const nodeRadius = baseRadius + 1.6 * intensity + 2.4 * focal;
        ctx.fillStyle = rgba(fillColor, 1);
        ctx.beginPath();
        ctx.arc(px, py, nodeRadius, 0, Math.PI * 2);
        ctx.fill();
      }

      if (showLabels && n <= 200) {
        ctx.fillStyle = PALETTE.labelText;
        ctx.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.textBaseline = "bottom";
        for (let i = 0; i < n; i += 1) {
          ctx.fillText(String(i), xy[i * 2] + 4, xy[i * 2 + 1] - 4);
        }
      }

      raf = requestAnimationFrame(frame);
    }

    raf = requestAnimationFrame(frame);
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
  }, [
    candidate,
    baseProjection,
    incidentEdges,
    width,
    height,
    pinVertex,
    pinEdge,
    showLabels,
  ]);

  function projectNow(): Float32Array {
    const base = baseProjection.base;
    const out = new Float32Array(base.length);
    const view = viewRef.current;
    const cx = width / 2;
    const cy = height / 2;
    for (let i = 0; i < base.length; i += 2) {
      out[i] = cx + (base[i] - cx) * view.scale + view.tx;
      out[i + 1] = cy + (base[i + 1] - cy) * view.scale + view.ty;
    }
    return out;
  }

  function nearestVertex(x: number, y: number, xy: Float32Array): number | null {
    let best = -1;
    let bestDist = HOVER_VERTEX_RADIUS_PX;
    for (let i = 0; i < candidate.points.length; i += 1) {
      const dx = xy[i * 2] - x;
      const dy = xy[i * 2 + 1] - y;
      const d = Math.hypot(dx, dy);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    }
    return best === -1 ? null : best;
  }

  function nearestEdge(x: number, y: number, xy: Float32Array): number | null {
    let best = -1;
    let bestDist = HOVER_EDGE_PX;
    for (let e = 0; e < candidate.edges.length; e += 1) {
      const [i, j] = candidate.edges[e];
      const d = distToSegment(
        x,
        y,
        xy[i * 2],
        xy[i * 2 + 1],
        xy[j * 2],
        xy[j * 2 + 1],
      );
      if (d < bestDist) {
        bestDist = d;
        best = e;
      }
    }
    return best === -1 ? null : best;
  }

  function pointerToCanvas(event: ReactPointerEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (width / rect.width),
      y: (event.clientY - rect.top) * (height / rect.height),
    };
  }

  function handlePointerDown(event: ReactPointerEvent<HTMLCanvasElement>) {
    const p = pointerToCanvas(event);
    if (!p) return;
    dragRef.current = {
      startX: p.x,
      startY: p.y,
      currentX: p.x,
      currentY: p.y,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: ReactPointerEvent<HTMLCanvasElement>) {
    const p = pointerToCanvas(event);
    if (!p) return;
    const drag = dragRef.current;
    if (drag) {
      const dx = p.x - drag.currentX;
      const dy = p.y - drag.currentY;
      drag.currentX = p.x;
      drag.currentY = p.y;
      if (
        !drag.moved &&
        (Math.abs(p.x - drag.startX) > 3 || Math.abs(p.y - drag.startY) > 3)
      ) {
        drag.moved = true;
      }
      if (drag.moved) {
        const view = viewRef.current;
        viewRef.current = { scale: view.scale, tx: view.tx + dx, ty: view.ty + dy };
        hoverVertexRef.current = null;
        hoverEdgeRef.current = null;
      }
      return;
    }
    const xy = projectNow();
    const v = nearestVertex(p.x, p.y, xy);
    if (v !== null) {
      hoverVertexRef.current = v;
      hoverEdgeRef.current = null;
      return;
    }
    const e = nearestEdge(p.x, p.y, xy);
    hoverVertexRef.current = null;
    hoverEdgeRef.current = e;
  }

  function handlePointerUp(event: ReactPointerEvent<HTMLCanvasElement>) {
    const p = pointerToCanvas(event);
    const drag = dragRef.current;
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (!p || drag?.moved) return;
    const xy = projectNow();
    const v = nearestVertex(p.x, p.y, xy);
    if (v !== null) {
      setPinEdge(null);
      setPinVertex((prev) => (prev === v ? null : v));
      return;
    }
    const e = nearestEdge(p.x, p.y, xy);
    if (e !== null) {
      setPinVertex(null);
      setPinEdge((prev) => (prev === e ? null : e));
      return;
    }
    setPinVertex(null);
    setPinEdge(null);
  }

  function handlePointerLeave() {
    hoverVertexRef.current = null;
    hoverEdgeRef.current = null;
  }

  function handleWheel(event: WheelEvent<HTMLCanvasElement>) {
    event.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) * (width / rect.width);
    const y = (event.clientY - rect.top) * (height / rect.height);
    const view = viewRef.current;
    const next = Math.min(12, Math.max(0.25, view.scale * (event.deltaY < 0 ? 1.12 : 0.9)));
    viewRef.current = {
      scale: next,
      tx: x - width / 2 - ((x - width / 2 - view.tx) / view.scale) * next,
      ty: y - height / 2 - ((y - height / 2 - view.ty) / view.scale) * next,
    };
  }

  function nudgeScale(factor: number) {
    const view = viewRef.current;
    const next = Math.min(12, Math.max(0.25, view.scale * factor));
    viewRef.current = { scale: next, tx: view.tx, ty: view.ty };
  }

  function resetView() {
    viewRef.current = DEFAULT_VIEW;
  }

  const selectedNode = pinVertex !== null ? (candidate.points[pinVertex] ?? null) : null;
  const selectedNeighbors = pinVertex !== null ? (adjacency[pinVertex] ?? []) : [];
  const selectedEdge = pinEdge !== null ? (candidate.edges[pinEdge] ?? null) : null;

  const labelsDisabled = candidate.n > 200;

  const canvasBlock = (
    <div style={styles.canvasPanel}>
      <div style={styles.canvasFrame}>
        <canvas
          ref={canvasRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          onPointerUp={handlePointerUp}
          onWheel={handleWheel}
          style={styles.canvas}
        />
        <div style={{ ...styles.toolbar, ...(compact ? styles.toolbarCompact : null) }}>
          <button
            type="button"
            style={styles.toolButton}
            onClick={() => nudgeScale(1.2)}
            title="zoom in"
          >
            +
          </button>
          <button
            type="button"
            style={styles.toolButton}
            onClick={() => nudgeScale(1 / 1.2)}
            title="zoom out"
          >
            −
          </button>
          <button
            type="button"
            style={styles.toolButton}
            onClick={resetView}
            title="reset view"
          >
            reset
          </button>
          {!compact && (
            <button
              type="button"
              disabled={labelsDisabled}
              style={{
                ...styles.toolButton,
                ...(showLabels && !labelsDisabled ? styles.toolButtonActive : null),
                ...(labelsDisabled ? styles.toolButtonDisabled : null),
              }}
              onClick={() => setShowLabels((v) => !v)}
              title={labelsDisabled ? "labels available for n ≤ 200" : "toggle labels"}
            >
              labels
            </button>
          )}
        </div>
      </div>
      {compact ? (
        <CompactReadout
          pinVertex={pinVertex}
          pinEdge={pinEdge}
          adjacency={adjacency}
          candidate={candidate}
          onClear={() => {
            setPinVertex(null);
            setPinEdge(null);
          }}
        />
      ) : (
        <div style={styles.caption}>
          Hover a vertex or edge to preview its connections; click to pin. Drag to pan,
          scroll to zoom.
        </div>
      )}
    </div>
  );

  if (compact) {
    return canvasBlock;
  }

  return (
    <div style={styles.layout}>
      {canvasBlock}
      <aside style={styles.details}>
        {selectedNode && pinVertex !== null ? (
          <NodeDetail
            index={pinVertex}
            point={selectedNode}
            neighbors={selectedNeighbors}
            adjacency={adjacency}
            onPickNeighbor={(i) => {
              setPinEdge(null);
              setPinVertex(i);
            }}
            onClear={() => setPinVertex(null)}
          />
        ) : selectedEdge && pinEdge !== null ? (
          <EdgeDetail
            index={pinEdge}
            edge={selectedEdge}
            points={candidate.points}
            onPickEndpoint={(i) => {
              setPinEdge(null);
              setPinVertex(i);
            }}
            onClear={() => setPinEdge(null)}
          />
        ) : (
          <EmptyDetail />
        )}
      </aside>
    </div>
  );
}

function CompactReadout({
  pinVertex,
  pinEdge,
  adjacency,
  candidate,
  onClear,
}: {
  pinVertex: number | null;
  pinEdge: number | null;
  adjacency: number[][];
  candidate: Candidate;
  onClear: () => void;
}) {
  if (pinVertex !== null) {
    const degree = adjacency[pinVertex]?.length ?? 0;
    const coeffs = candidate.points[pinVertex]?.coeffs ?? [];
    return (
      <div style={styles.compactReadout}>
        <span style={{ ...styles.chip, ...styles.chipPrimary }}>node {pinVertex}</span>
        <span style={styles.chip}>deg {degree}</span>
        <span style={styles.compactCoeffs}>({coeffs.join(", ")})</span>
        <button type="button" style={styles.clearBtn} onClick={onClear} title="unpin">
          ×
        </button>
      </div>
    );
  }
  if (pinEdge !== null) {
    const [i, j] = candidate.edges[pinEdge] ?? [0, 0];
    return (
      <div style={styles.compactReadout}>
        <span style={{ ...styles.chip, ...styles.chipPrimary }}>edge {pinEdge}</span>
        <span style={styles.chip}>
          {i} — {j}
        </span>
        <button type="button" style={styles.clearBtn} onClick={onClear} title="unpin">
          ×
        </button>
      </div>
    );
  }
  return (
    <div style={styles.compactHint}>
      Hover to preview neighbors. Click to pin.
    </div>
  );
}

function NodeDetail({
  index,
  point,
  neighbors,
  adjacency,
  onPickNeighbor,
  onClear,
}: {
  index: number;
  point: Point;
  neighbors: number[];
  adjacency: number[][];
  onPickNeighbor: (i: number) => void;
  onClear: () => void;
}) {
  return (
    <>
      <div style={styles.detailHeader}>
        <div style={styles.headerChips}>
          <span style={{ ...styles.chip, ...styles.chipPrimary }}>node {index}</span>
          <span style={styles.chip}>deg {neighbors.length}</span>
        </div>
        <button type="button" style={styles.clearBtn} onClick={onClear} title="unpin">
          ×
        </button>
      </div>
      <dl style={styles.dl}>
        <dt style={styles.dt}>coeffs</dt>
        <dd style={styles.dd}>{formatCoeffs(point.coeffs)}</dd>
        <dt style={styles.dt}>xy</dt>
        <dd style={styles.dd}>
          ({point.xy[0].toFixed(4)}, {point.xy[1].toFixed(4)})
        </dd>
      </dl>
      <div style={styles.subheading}>neighbors</div>
      <div style={styles.neighborList}>
        {neighbors.map((nb) => (
          <button
            key={nb}
            type="button"
            style={styles.neighborButton}
            onClick={() => onPickNeighbor(nb)}
            title={`node ${nb}, degree ${adjacency[nb]?.length ?? 0}`}
          >
            <span style={styles.neighborIndex}>{nb}</span>
            <span style={styles.neighborDeg}>·{adjacency[nb]?.length ?? 0}</span>
          </button>
        ))}
      </div>
    </>
  );
}

function EdgeDetail({
  index,
  edge,
  points,
  onPickEndpoint,
  onClear,
}: {
  index: number;
  edge: [number, number];
  points: Point[];
  onPickEndpoint: (i: number) => void;
  onClear: () => void;
}) {
  const [i, j] = edge;
  const a = points[i];
  const b = points[j];
  const delta = a.coeffs.map((v, k) => v - b.coeffs[k]);
  return (
    <>
      <div style={styles.detailHeader}>
        <div style={styles.headerChips}>
          <span style={{ ...styles.chip, ...styles.chipPrimary }}>edge {index}</span>
          <span style={styles.chip}>
            {i} — {j}
          </span>
        </div>
        <button type="button" style={styles.clearBtn} onClick={onClear} title="unpin">
          ×
        </button>
      </div>
      <dl style={styles.dl}>
        <dt style={styles.dt}>i = {i}</dt>
        <dd style={styles.dd}>{formatCoeffs(a.coeffs)}</dd>
        <dt style={styles.dt}>j = {j}</dt>
        <dd style={styles.dd}>{formatCoeffs(b.coeffs)}</dd>
        <dt style={styles.dt}>Δ coeffs</dt>
        <dd style={styles.dd}>{formatCoeffs(delta)}</dd>
      </dl>
      <div style={styles.subheading}>endpoints</div>
      <div style={styles.neighborList}>
        <button
          type="button"
          style={styles.neighborButton}
          onClick={() => onPickEndpoint(i)}
        >
          <span style={styles.neighborIndex}>{i}</span>
        </button>
        <button
          type="button"
          style={styles.neighborButton}
          onClick={() => onPickEndpoint(j)}
        >
          <span style={styles.neighborIndex}>{j}</span>
        </button>
      </div>
    </>
  );
}

function EmptyDetail() {
  return (
    <div style={styles.empty}>
      <div style={styles.emptyDot} />
      <p style={styles.emptyText}>
        Hover any vertex or edge to preview its connections. Click to pin and inspect
        details.
      </p>
    </div>
  );
}

function drawGrid(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  view: View,
) {
  const minor = Math.max(8, 24 * view.scale);
  const major = Math.max(40, 120 * view.scale);
  const offMinorX = ((view.tx % minor) + minor) % minor;
  const offMinorY = ((view.ty % minor) + minor) % minor;
  const offMajorX = ((view.tx % major) + major) % major;
  const offMajorY = ((view.ty % major) + major) % major;
  ctx.lineWidth = 1;
  ctx.strokeStyle = PALETTE.gridMinor;
  ctx.beginPath();
  for (let x = offMinorX; x < w; x += minor) {
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, h);
  }
  for (let y = offMinorY; y < h; y += minor) {
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(w, y + 0.5);
  }
  ctx.stroke();
  ctx.strokeStyle = PALETTE.gridMajor;
  ctx.beginPath();
  for (let x = offMajorX; x < w; x += major) {
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, h);
  }
  for (let y = offMajorY; y < h; y += major) {
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(w, y + 0.5);
  }
  ctx.stroke();
}

function distToSegment(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
): number {
  const dx = bx - ax;
  const dy = by - ay;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.hypot(px - ax, py - ay);
  let t = ((px - ax) * dx + (py - ay) * dy) / lenSq;
  if (t < 0) t = 0;
  else if (t > 1) t = 1;
  const cx = ax + t * dx;
  const cy = ay + t * dy;
  return Math.hypot(px - cx, py - cy);
}

function rgba(rgb: readonly [number, number, number], alpha: number): string {
  const a = Math.max(0, Math.min(1, alpha));
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${a})`;
}

function formatCoeffs(coeffs: number[]): string {
  return `(${coeffs.join(", ")})`;
}

const styles: Record<string, CSSProperties> = {
  layout: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1fr) 300px",
    gap: 18,
    alignItems: "start",
  },
  canvasPanel: { minWidth: 0 },
  canvasFrame: {
    position: "relative",
    borderRadius: 12,
    overflow: "hidden",
    border: "1px solid rgba(15, 23, 42, 0.1)",
    boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px rgba(15, 23, 42, 0.05)",
    background: PALETTE.bg,
  },
  canvas: {
    display: "block",
    width: "100%",
    maxWidth: 880,
    touchAction: "none",
    cursor: "crosshair",
  },
  toolbar: {
    position: "absolute",
    top: 10,
    right: 10,
    display: "flex",
    gap: 6,
    padding: 4,
    background: "rgba(255, 255, 255, 0.85)",
    border: "1px solid rgba(15, 23, 42, 0.1)",
    borderRadius: 8,
    boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
  },
  toolbarCompact: {
    top: 6,
    right: 6,
    padding: 2,
    gap: 4,
  },
  compactReadout: {
    display: "flex",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 8,
    fontSize: 12,
  },
  compactCoeffs: {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontSize: 11,
    opacity: 0.75,
    overflowWrap: "anywhere",
  },
  compactHint: {
    marginTop: 8,
    fontSize: 11,
    opacity: 0.6,
    lineHeight: 1.45,
  },
  toolButton: {
    border: "1px solid rgba(15, 23, 42, 0.0)",
    background: "transparent",
    color: "#0f172a",
    borderRadius: 6,
    padding: "4px 8px",
    fontFamily: "inherit",
    fontSize: 12,
    cursor: "pointer",
    minWidth: 30,
  },
  toolButtonActive: {
    background: "#0f172a",
    color: "white",
  },
  toolButtonDisabled: {
    opacity: 0.4,
    cursor: "not-allowed",
  },
  caption: {
    marginTop: 8,
    fontSize: 12,
    opacity: 0.65,
  },
  details: {
    border: "1px solid rgba(15, 23, 42, 0.1)",
    borderRadius: 12,
    padding: 14,
    background: "#fff",
    minHeight: 220,
    boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
  },
  detailHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 10,
    gap: 8,
  },
  headerChips: { display: "flex", gap: 6, flexWrap: "wrap" },
  chip: {
    display: "inline-flex",
    alignItems: "center",
    padding: "2px 8px",
    borderRadius: 999,
    background: "rgba(15, 23, 42, 0.06)",
    fontSize: 11,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontWeight: 500,
  },
  chipPrimary: {
    background: "rgba(239, 68, 68, 0.12)",
    color: "#b91c1c",
  },
  clearBtn: {
    border: "1px solid rgba(15, 23, 42, 0.1)",
    background: "transparent",
    color: "rgba(15, 23, 42, 0.6)",
    borderRadius: 6,
    padding: "0 6px",
    cursor: "pointer",
    fontSize: 14,
    lineHeight: "20px",
  },
  dl: {
    display: "grid",
    gridTemplateColumns: "80px 1fr",
    gap: "8px 10px",
    margin: 0,
  },
  dt: {
    fontSize: 11,
    opacity: 0.6,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  dd: {
    margin: 0,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontSize: 12,
    overflowWrap: "anywhere",
  },
  subheading: {
    marginTop: 14,
    marginBottom: 8,
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    opacity: 0.6,
  },
  neighborList: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
    maxHeight: 260,
    overflow: "auto",
  },
  neighborButton: {
    display: "inline-flex",
    alignItems: "baseline",
    gap: 4,
    border: "1px solid rgba(245, 158, 11, 0.4)",
    background: "rgba(245, 158, 11, 0.1)",
    color: "#92400e",
    borderRadius: 6,
    padding: "3px 8px",
    cursor: "pointer",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontSize: 12,
    transition: "background 120ms ease",
  },
  neighborIndex: { fontWeight: 600 },
  neighborDeg: { fontSize: 10, opacity: 0.65 },
  empty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: "24px 8px",
    textAlign: "center",
  },
  emptyDot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    background: "rgba(14, 165, 233, 0.65)",
    boxShadow: "0 0 0 6px rgba(14, 165, 233, 0.15)",
  },
  emptyText: {
    margin: 0,
    fontSize: 13,
    lineHeight: 1.55,
    opacity: 0.72,
    maxWidth: 240,
  },
};
