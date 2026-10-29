"use client";
// "My progress": skill scores (0-10) per day / week / month, latest improvement points, and AI feedback on the trend.
import { Sparkles, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import type { CoachFeedback, Skills } from "@/lib/types";
import { MODE_LABEL } from "@/components/GoalsPanel";

type Period = "day" | "week" | "month";
const ADJ: Record<Period, string> = { day: "daily", week: "weekly", month: "monthly" };
const COLORS = ["#FF9A3D", "#3DD68C", "#B794F6", "#7DD3FC", "#F5A524", "#E5484D", "#FFD08A", "#9F7AEA"];
const label = (skill: string) => {
  const [mode, name] = skill.split(".");
  return `${MODE_LABEL[mode as keyof typeof MODE_LABEL] ?? mode}: ${name.replace(/_/g, " ")}`;
};

export default function ProgressPanel({ studentId, refreshKey }: { studentId: string; refreshKey: number }) {
  const [period, setPeriod] = useState<Period>("week");
  const [data, setData] = useState<Skills | null>(null);
  const [fb, setFb] = useState<CoachFeedback | null>(null);
  const [asking, setAsking] = useState(false);

  const load = useCallback(() => {
    api<Skills>(`students/${studentId}/skills?period=${period}`).then(setData).catch(() => setData(null));
  }, [studentId, period]);
  useEffect(() => { load(); }, [load, refreshKey]);
  useEffect(() => setFb(null), [studentId, period]);

  const askFeedback = async () => {
    setAsking(true);
    try {
      setFb(await api<CoachFeedback>(`students/${studentId}/coach-feedback`, { method: "POST", body: { period } }));
    } catch (e) {
      setFb({ headline: "Couldn't get feedback right now.", points: [(e as Error).message], focus_next: "" });
    } finally {
      setAsking(false);
    }
  };

  // pivot: one row per bucket, one key per skill
  const skills = Array.from(new Set((data?.series ?? []).map((r) => r.skill)));
  const rows = new Map<string, Record<string, number | string>>();
  for (const r of data?.series ?? []) {
    const key = new Date(r.bucket).toLocaleDateString("en-IN", period === "month" ? { month: "short", year: "2-digit" } : { day: "numeric", month: "short" });
    rows.set(key, { ...(rows.get(key) ?? { t: key }), [r.skill]: r.score });
  }
  const chart = Array.from(rows.values());
  const latest = data?.reviews?.[0];

  return (
    <section className="card p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-medium"><TrendingUp size={18} className="text-accent" aria-hidden /> My progress</div>
        <div className="flex rounded-full border border-line p-1 text-sm" role="tablist" aria-label="Period">
          {(["day", "week", "month"] as Period[]).map((p) => (
            <button key={p} role="tab" aria-selected={period === p} onClick={() => setPeriod(p)}
              className={`rounded-full px-3.5 py-1 capitalize ${period === p ? "bg-surface-2 text-text" : "text-muted hover:text-text"}`}>{p}</button>
          ))}
        </div>
      </div>

      {chart.length ? (
        <div style={{ height: 240 }} role="img" aria-label={`Skill scores by ${period}`}>
          <ResponsiveContainer>
            <LineChart data={chart} margin={{ top: 6, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis dataKey="t" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis domain={[0, 10]} stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 10, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {skills.map((s, i) => (
                <Line key={s} type="monotone" dataKey={s} name={label(s)} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={{ r: 3 }} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="py-6 text-center text-muted">Your progress appears here after your first call.</p>
      )}
      <p className="mt-1 text-xs text-muted">Scores 0–10 from Guru&apos;s review of each call; confidence is what you said yourself.</p>

      {latest && (latest.improvements?.length ?? 0) > 0 && (
        <div className="mt-5 rounded-input border border-line p-4">
          <div className="text-sm text-muted">From your last {MODE_LABEL[latest.mode ?? "topic"]} call</div>
          {latest.summary && <p className="mt-1">{latest.summary}</p>}
          <ul className="mt-2 space-y-1 text-sm">
            {latest.improvements.map((x, i) => <li key={i}>→ {x}</li>)}
          </ul>
        </div>
      )}

      <div className="mt-5">
        <button className="btn-ghost" onClick={askFeedback} disabled={asking || !chart.length}>
          <Sparkles size={15} aria-hidden /> {asking ? "Guru is looking at your progress…" : `Ask Guru for ${ADJ[period]} feedback`}
        </button>
        {fb && (
          <div className="mt-3 rounded-input border border-accent/40 bg-accent/5 p-4" role="status">
            <div className="font-medium">{fb.headline}</div>
            <ul className="mt-2 space-y-1 text-sm">{fb.points.map((p, i) => <li key={i}>• {p}</li>)}</ul>
            {fb.focus_next && <div className="mt-2 text-sm text-accent">Next focus: {fb.focus_next}</div>}
          </div>
        )}
      </div>
    </section>
  );
}
