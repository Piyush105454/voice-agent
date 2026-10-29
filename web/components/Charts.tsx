"use client";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SessionPoint, Snapshot } from "@/lib/types";
import { pretty } from "@/lib/format";

const axis = { stroke: "var(--muted)", fontSize: 11, tickLine: false, axisLine: false } as const;
const tooltipStyle = { background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 10, fontSize: 12 };
const day = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

/** Self-reported confidence (scaled /10) next to measured accuracy, per session. */
export function ConfidenceAccuracyChart({ points, height = 180 }: { points: SessionPoint[]; height?: number }) {
  const data = points
    .filter((p) => p.accuracy != null || p.conf_after != null)
    .map((p, i) => ({
      name: `${i + 1} · ${day(p.started_at)}`,
      accuracy: p.accuracy != null ? Math.round(p.accuracy * 100) : null,
      confidence: p.conf_after != null ? p.conf_after * 10 : p.conf_before != null ? p.conf_before * 10 : null,
    }));
  if (!data.length) return <div className="py-8 text-center text-xs text-muted">No sessions yet.</div>;
  return (
    <div style={{ height }} aria-label="Confidence versus accuracy per session" role="img">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis dataKey="name" {...axis} hide={data.length > 6} />
          <YAxis domain={[0, 100]} {...axis} unit="%" />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number, k) => [k === "confidence" ? `${v / 10}/10` : `${v}%`, k]} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="confidence" name="confidence (self-reported)" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive />
          <Line type="monotone" dataKey="accuracy" name="quiz accuracy" stroke="var(--m-high)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Mastery or misconception strength over time, one line per key (topic / misconception). */
export function OverTimeChart({ snapshots, kind, height = 200, names = {} }: { snapshots: Snapshot[]; kind: "mastery" | "misconception"; height?: number; names?: Record<string, string> }) {
  const rows = snapshots.filter((s) => s.kind === kind);
  const keys = Array.from(new Set(rows.map((r) => r.key)));
  if (!rows.length) return <div className="py-8 text-center text-xs text-muted">No history yet.</div>;
  // one point per timestamp: snapshots written together (same answer) share a time
  const byT = new Map<number, Record<string, number>>();
  for (const r of rows) {
    const t = new Date(r.created_at).getTime();
    byT.set(t, { ...(byT.get(t) ?? { t }), [r.key]: Number(r.value.toFixed(3)) });
  }
  const data = Array.from(byT.values()).sort((a, b) => a.t - b.t);
  const palette = kind === "misconception" ? ["#B794F6", "#D6BCFA", "#9F7AEA", "#E9D8FD", "#805AD5", "#C4B5FD"] : ["#FF9A3D", "#3DD68C", "#F5A524", "#FFD08A", "#7DD3FC", "#E5484D"];
  return (
    <div style={{ height }} role="img" aria-label={`${kind} over time`}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={(t) => day(new Date(t).toISOString())} {...axis} />
          <YAxis domain={[0, 1]} {...axis} />
          <Tooltip contentStyle={tooltipStyle} labelFormatter={(t) => new Date(t as number).toLocaleString("en-IN")} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {keys.map((k, i) => (
            <Line key={k} type="monotone" dataKey={k} name={names[k] || pretty(k)} stroke={palette[i % palette.length]} strokeWidth={2} dot={{ r: 2.5 }} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
