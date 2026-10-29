"use client";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GraphData, GraphLink, GraphNode } from "@/lib/types";
import { masteryBand } from "@/lib/format";

const ForceGraph = dynamic(() => import("./ForceGraph"), { ssr: false });

const css = (v: string) =>
  typeof window === "undefined" ? "#888" : getComputedStyle(document.documentElement).getPropertyValue(v).trim();
// canvas cannot use CSS variables: "var(--m-low)" -> "#E5484D"
const resolve = (c: string) => (c.startsWith("var(") ? css(c.slice(4, -1)) : c);

type Props = {
  data: GraphData;
  active?: Record<string, number>; // node id -> timestamp of last update (pulse for 1.2 s)
  height?: number;
  showAllLabels?: boolean;
  interactive?: boolean;
};

export default function KnowledgeGraph({ data, active = {}, height = 480, showAllLabels = true, interactive = true }: Props) {
  const wrap = useRef<HTMLDivElement>(null);
  const fg = useRef<any>(null);
  const [width, setWidth] = useState(600);
  const [hover, setHover] = useState<string | null>(null);
  const reduced = useRef(false);

  useEffect(() => {
    reduced.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  // Keep node positions stable across refreshes: merge new data into the previous node objects.
  const prev = useRef<Map<string, GraphNode>>(new Map());
  const graph = useMemo(() => {
    const nodes = data.nodes.map((n) => {
      const old = prev.current.get(n.id);
      return old ? Object.assign(old, n) : { ...n };
    });
    prev.current = new Map(nodes.map((n) => [n.id, n]));
    const ids = new Set(nodes.map((n) => n.id));
    const id = (x: string | GraphNode) => (typeof x === "string" ? x : x.id);
    const links = data.links
      .filter((l) => ids.has(id(l.source)) && ids.has(id(l.target)))
      .map((l) => ({ ...l, source: id(l.source), target: id(l.target) }));
    return { nodes, links };
  }, [data]);

  // Spread the layout out (defaults cram ~15 labelled nodes together) and fit it once per node-set change.
  const configured = useRef(false);
  const fittedFor = useRef("");
  const configure = () => {
    const g = fg.current;
    if (!g || configured.current) return;
    g.d3Force("charge")?.strength(-340);
    g.d3Force("link")?.distance((l: any) => (l.kind === "PREREQUISITE_OF" ? 95 : 70));
    configured.current = true;
    g.d3ReheatSimulation();
  };
  const nodeKey = graph.nodes.map((n) => n.id).sort().join("|");
  useEffect(() => {
    fg.current?.d3ReheatSimulation?.();
  }, [graph]);

  const colors = useMemo(
    () => ({ accent: css("--accent"), misc: css("--misc"), line: css("--line"), text: css("--text"), muted: css("--muted") }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [width],
  );

  const draw = (node: GraphNode & { x: number; y: number }, ctx: CanvasRenderingContext2D, scale: number) => {
    const t = active[node.id];
    const age = t ? (Date.now() - t) / 1200 : 2;
    let r = 6;
    if (node.kind === "student") r = 9;
    else if (node.kind === "topic") r = 6 + 6 * (node.mastery ?? 0.3);
    else if (node.kind === "misconception") r = 5 + 6 * (node.strength ?? 0.3);
    else if (node.kind === "goal") r = 9;
    else if (node.kind === "skill") r = 5 + 0.7 * (node.score ?? 5);
    else if (node.kind === "confidence") r = 5 + 0.6 * (node.value ?? 5);
    else if (node.kind === "pattern") r = 6;
    else if (node.kind === "challenge") r = 8;
    else if (node.kind === "next") r = 6;
    else r = 4;

    // pulse ring for recently updated nodes
    if (age < 1 && !reduced.current) {
      const k = 1 + 0.35 * Math.sin(Math.PI * age);
      ctx.beginPath();
      ctx.arc(node.x, node.y, r * k + 6, 0, 2 * Math.PI);
      ctx.strokeStyle = colors.accent;
      ctx.globalAlpha = 1 - age;
      ctx.lineWidth = 2.5 / scale;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    ctx.beginPath();
    if (node.kind === "goal") {
      // five-point star: the student's own goal
      for (let i = 0; i < 10; i++) {
        const a = -Math.PI / 2 + (i * Math.PI) / 5, rr = i % 2 ? r * 0.45 : r;
        ctx[i ? "lineTo" : "moveTo"](node.x + rr * Math.cos(a), node.y + rr * Math.sin(a));
      }
      ctx.closePath();
      ctx.fillStyle = colors.accent;
      ctx.fill();
    } else if (node.kind === "resource" || node.kind === "works") {
      ctx.rect(node.x - r, node.y - r, 2 * r, 2 * r);
      ctx.fillStyle = node.kind === "resource" ? css("--sky") || "#4F8EF7" : resolve("var(--m-high)");
      ctx.globalAlpha = 0.8;
      ctx.fill();
      ctx.globalAlpha = 1;
    } else if (node.kind === "next" || node.kind === "confidence") {
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.setLineDash(node.kind === "next" ? [3 / scale, 2 / scale] : []);
      ctx.lineWidth = 2 / scale;
      ctx.strokeStyle = node.kind === "next" ? colors.accent : css("--sky") || "#4F8EF7";
      ctx.stroke();
      ctx.setLineDash([]);
    } else if (node.kind === "misconception" || node.kind === "pattern") {
      ctx.moveTo(node.x, node.y - r);
      ctx.lineTo(node.x + r, node.y);
      ctx.lineTo(node.x, node.y + r);
      ctx.lineTo(node.x - r, node.y);
      ctx.closePath();
      ctx.fillStyle = colors.misc;
      ctx.globalAlpha = node.kind === "pattern" ? 0.75 : 0.35 + 0.65 * (node.strength ?? 0.5);
      ctx.fill();
      ctx.globalAlpha = 1;
    } else {
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      if (node.kind === "student") {
        ctx.fillStyle = css("--bg") || "#07080A";
        ctx.fill();
        ctx.lineWidth = 2.5 / scale;
        ctx.strokeStyle = colors.text;
        ctx.stroke();
      } else if (node.kind === "topic") {
        ctx.fillStyle = resolve(masteryBand(node.mastery).color);
        ctx.fill();
      } else if (node.kind === "challenge") {
        // a problem the person brought: red new, amber improving, green solved
        ctx.fillStyle = resolve(masteryBand(node.value ?? 0).color);
        ctx.fill();
        ctx.lineWidth = 2 / scale;
        ctx.strokeStyle = colors.text;
        ctx.stroke();
      } else if (node.kind === "skill") {
        ctx.fillStyle = resolve(masteryBand((node.score ?? 0) / 10).color);
        ctx.fill();
      } else if (node.kind === "practice") {
        ctx.fillStyle = resolve("var(--m-high)");
        ctx.globalAlpha = 0.55;
        ctx.fill();
        ctx.globalAlpha = 1;
      } else {
        ctx.fillStyle = colors.muted;
        ctx.fill();
      }
    }

    const quiet = node.kind === "practice" || node.kind === "works" || node.kind === "pattern" || node.kind === "resource";
    const showLabel = (showAllLabels && !quiet) || node.id === hover || age < 1 || node.kind === "student";
    if (showLabel) {
      const fs = (node.kind === "student" ? 13 : 11) / scale; // constant on-screen size
      ctx.font = `${node.kind === "student" ? 600 : 400} ${fs}px var(--font-sans), system-ui`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = age < 1 ? colors.accent
        : node.kind === "misconception" || node.kind === "pattern" ? colors.misc
        : node.kind === "practice" || node.kind === "works" || node.kind === "resource" ? colors.muted : colors.text;
      const arrow = (t?: number) => (t == null || Math.abs(t) < 0.5 ? "" : t > 0 ? " ↑" : " ↓");
      const val =
        node.kind === "topic" && node.mastery != null ? ` · ${node.mastery.toFixed(2)}`
        : node.kind === "misconception" && node.strength != null ? ` · ${node.strength.toFixed(2)}`
        : node.kind === "skill" && node.score != null ? ` · ${node.score.toFixed(1)}${arrow(node.trend)}` : "";
      ctx.fillText((node.id === hover && node.detail ? node.detail : node.label) + val, node.x, node.y + r + 3);
    }
  };

  const linkColor = (l: GraphLink) =>
    l.kind === "HOLDS" || l.kind === "HAS_PATTERN" || l.kind === "WEAKENS" ? colors.misc
    : l.kind === "NEXT_STEP" || l.kind === "HAS_GOAL" ? colors.accent
    : l.kind === "PREREQUISITE_OF" ? colors.muted : colors.line;

  return (
    <div ref={wrap} className="relative w-full" style={{ height }} aria-label="Knowledge graph" role="img">
      {graph.nodes.length > 0 && (
        <ForceGraph
          fgRef={fg}
          onEngineTick={configure}
          graphData={graph}
          width={width}
          height={height}
          backgroundColor="rgba(0,0,0,0)"
          cooldownTime={2000}
          d3VelocityDecay={0.3}
          autoPauseRedraw={false}
          enableZoomInteraction={interactive}
          enablePanInteraction={interactive}
          enableNodeDrag={interactive}
          nodeRelSize={6}
          nodeCanvasObject={draw as any}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, 12, 0, 2 * Math.PI);
            ctx.fill();
          }}
          onNodeHover={(n: any) => setHover(n?.id ?? null)}
          linkColor={linkColor as any}
          linkWidth={(l: any) => (l.kind === "HOLDS" ? 1 + 2 * (l.value ?? 0.5) : 1)}
          linkLineDash={(l: any) => (l.kind === "PREREQUISITE_OF" || l.kind === "NEXT_STEP" || l.kind === "WEAKENS" ? [4, 3] : null)}
          linkDirectionalArrowLength={(l: any) => (l.kind === "PREREQUISITE_OF" || l.kind === "NEXT_STEP" || l.kind === "WEAKENS" ? 4 : 0)}
          linkDirectionalArrowRelPos={0.9}
          onEngineStop={() => {
            if (fittedFor.current !== nodeKey) {
              fittedFor.current = nodeKey;
              fg.current?.zoomToFit?.(500, 50);
            }
          }}
        />
      )}
    </div>
  );
}

export function GraphLegend() {
  const item = (shape: React.ReactNode, text: string) => (
    <span className="inline-flex items-center gap-1.5">
      {shape}
      {text}
    </span>
  );
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
      {item(<span className="h-2.5 w-2.5 rounded-full border-2 border-text" />, "Student")}
      {item(<span className="h-2.5 w-2.5 rounded-full bg-m-low" />, "Topic / skill: needs practice")}
      {item(<span className="h-2.5 w-2.5 rounded-full bg-m-mid" />, "Building")}
      {item(<span className="h-2.5 w-2.5 rounded-full bg-m-high" />, "Strong")}
      {item(<span className="h-2.5 w-2.5 rotate-45 bg-misc" />, "Misconception")}
      {item(<span className="w-4 border-t border-dashed border-muted" />, "Prerequisite")}
      {item(<span className="text-[11px] leading-none text-accent">★</span>, "Goal")}
      {item(<span className="h-2.5 w-2.5 rounded-full border border-text bg-m-low" />, "Problem: new / improving / solved")}
      {item(<span className="h-2.5 w-2.5 rounded-full border border-dashed border-accent" />, "Next step")}
      {item(<span className="h-2.5 w-2.5 rounded-full border-2 border-sky" />, "Confidence (self-reported)")}
      {item(<span className="h-2.5 w-2.5 rounded-full" style={{ background: "var(--m-high)", opacity: 0.55 }} />, "Practised")}
      {item(<span className="h-2.5 w-2.5 rotate-45" style={{ background: "var(--misc)", opacity: 0.75 }} />, "Mistake pattern")}
      {item(<span className="h-2.5 w-2.5" style={{ background: "var(--m-high)", opacity: 0.8 }} />, "Works for them")}
      {item(<span className="h-2.5 w-2.5" style={{ background: "var(--sky)", opacity: 0.8 }} />, "Book / method")}
    </div>
  );
}
