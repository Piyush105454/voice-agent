"use client";
import { Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { OverTimeChart } from "@/components/Charts";
import KnowledgeGraph, { GraphLegend } from "@/components/KnowledgeGraph";
import { EmptyState, ErrorState, MasteryBar, MisconceptionChip, Panel, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { ago, pretty } from "@/lib/format";
import type { GraphData, Overview } from "@/lib/types";

export default function StudentMemory({ params }: { params: { id: string } }) {
  const [ov, setOv] = useState<Overview | null>(null);
  const [graph, setGraph] = useState<GraphData>({ nodes: [], links: [] });
  const [error, setError] = useState<string | null>(null);
  const [t, setT] = useState(100); // time scrubber, % of history

  const load = useCallback(async () => {
    try {
      const [o, g] = await Promise.all([api<Overview>(`students/${params.id}/overview`), api<GraphData>(`students/${params.id}/graph`)]);
      setOv(o);
      setGraph(g);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [params.id]);
  useEffect(() => { load(); }, [load]);

  // Time scrubber: rebuild node values from learning_snapshots up to the chosen moment.
  const times = useMemo(() => (ov?.snapshots ?? []).map((s) => new Date(s.created_at).getTime()), [ov]);
  const tMin = times.length ? Math.min(...times) : 0;
  const tMax = times.length ? Math.max(...times) : 0;
  const cutoff = tMin + ((tMax - tMin) * t) / 100;
  const scrubbed = useMemo<GraphData>(() => {
    if (!ov || t === 100 || !times.length) return graph;
    const last: Record<string, number> = {};
    for (const s of ov.snapshots) if (new Date(s.created_at).getTime() <= cutoff) last[`${s.kind}:${s.key}`] = s.value;
    const nodes = graph.nodes
      .map((n) => n.kind === "topic" && last[`mastery:${n.id}`] !== undefined ? { ...n, mastery: last[`mastery:${n.id}`] }
        : n.kind === "misconception" ? (last[`misconception:${n.id}`] !== undefined ? { ...n, strength: last[`misconception:${n.id}`] } : null)
        : n)
      .filter(Boolean) as GraphData["nodes"];
    return { nodes, links: graph.links };
  }, [graph, ov, t, cutoff, times.length]);

  const forget = async (factId: string) => {
    if (!window.confirm("Forget this one fact? It cannot be undone.")) return;
    await api(`students/${params.id}/memory/${factId}`, { method: "DELETE" });
    load();
  };
  const forgetAll = async () => {
    if (!window.confirm("Delete ALL learning memory for this student? This removes Postgres rows and the graph node. It cannot be undone.")) return;
    await api(`students/${params.id}/memory`, { method: "DELETE" });
    load();
  };

  if (error) return <div className="mx-auto max-w-7xl px-5 py-10"><div className="card"><ErrorState message={error} retry={load} /></div></div>;
  if (!ov) return <div className="mx-auto max-w-7xl space-y-4 px-5 py-10"><Skeleton className="h-16" /><Skeleton className="h-[520px]" /></div>;

  const names = Object.fromEntries([...ov.topics.map((x) => [x.topic_id, x.name]), ...ov.misconceptions.map((m) => [m.id, m.name])]);

  return (
    <div className="mx-auto max-w-[1500px] px-5 pb-16 pt-8 md:px-8">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="label">Student memory</div>
          <h1 className="mt-1 font-serif text-5xl">{ov.first_name}</h1>
          <p className="mt-1 text-muted">Grade {ov.grade} · {ov.language === "hi-en" ? "Hinglish" : ov.language === "hi" ? "Hindi" : "English"} · {ov.consented ? "guardian consent on file" : "no consent: calls refused"}</p>
        </div>
        <div className="flex gap-2">
          <Link href={`/live?student=${ov.id}`} className="btn-primary">Open live console</Link>
          <Link href={`/parent/${ov.id}`} className="btn-ghost">Parent view</Link>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <Panel title="Sessions" className="lg:col-span-3 lg:max-h-[640px] lg:overflow-y-auto">
          {ov.sessions.length ? (
            <ol className="relative space-y-5 border-l border-line pl-4">
              {ov.sessions.map((s) => (
                <li key={s.id}>
                  <span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full border border-line bg-surface-2" aria-hidden />
                  <div className="text-sm">{new Date(s.started_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</div>
                  <div className="text-xs text-muted">{(s.topic_id && names[s.topic_id]) || pretty(s.topic_id) || "—"} · {s.channel} · {s.status}</div>
                  {s.summaries?.filter((x) => x.audience === "teacher").map((x, i) => (
                    <p key={i} className="mt-1.5 whitespace-pre-line text-xs text-muted">{x.body}</p>
                  ))}
                </li>
              ))}
            </ol>
          ) : <EmptyState title="No sessions yet" hint="Run the simulator on the Live page." />}
        </Panel>

        <section className="card lg:col-span-6">
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-4">
            <h2 className="label">Memory graph</h2>
            <GraphLegend />
          </div>
          {graph.nodes.length ? <KnowledgeGraph data={scrubbed} height={460} /> : <EmptyState title="Nothing remembered yet" />}
          {times.length > 1 && (
            <div className="border-t border-line px-5 py-3">
              <label className="flex items-center gap-3 text-xs text-muted">
                <span className="w-24 shrink-0">Time travel</span>
                <input type="range" min={0} max={100} value={t} onChange={(e) => setT(+e.target.value)} className="w-full accent-[var(--accent)]" aria-label="Replay how the graph changed over time" />
                <span className="num w-28 shrink-0 text-right">{t === 100 ? "now" : new Date(cutoff).toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
              </label>
            </div>
          )}
        </section>

        <Panel title="What Guru remembers" className="lg:col-span-3 lg:max-h-[640px] lg:overflow-y-auto"
          right={ov.memory.length > 0 && <button onClick={forgetAll} className="text-xs text-muted hover:text-m-low">Delete all</button>}>
          {ov.memory.length ? (
            <ul className="space-y-3">
              {ov.memory.map((f) => (
                <li key={f.id} className="rounded-input border border-line p-3">
                  <div className="flex items-start justify-between gap-2">
                    {f.kind === "misconception" ? <MisconceptionChip id={f.content.id!} name={names[f.content.id!]} />
                      : <span className="chip border border-line capitalize">{f.content.type === "profile" ? "Learner profile" : f.kind}: {pretty(f.content.id) || f.content.text || f.content.title || f.content.direction || f.content.language || f.content.type}</span>}
                    <button onClick={() => forget(f.id)} aria-label="Delete memory" className="text-muted hover:text-m-low"><Trash2 size={14} /></button>
                  </div>
                  {f.content.evidence && <p className="mt-2 text-xs text-muted">“{f.content.evidence}”</p>}
                  <p className="mt-1 text-[11px] text-muted">
                    from the call {ago(f.source_started_at)} · confidence <span className="num">{f.confidence.toFixed(2)}</span>
                  </p>
                </li>
              ))}
            </ul>
          ) : <EmptyState title="Nothing stored" hint="Facts appear after a call ends, each with its source." />}
        </Panel>

        <Panel title="Mastery now (with forgetting)" className="lg:col-span-4">
          <div className="space-y-3">
            {ov.topics.map((x) => <MasteryBar key={x.topic_id} label={x.name} value={x.p_now} sub={`${x.p_now < 0.7 ? "review due now" : `review in ${x.next_review_days} d`} · memory stability ${x.stability_days.toFixed(1)} d`} />)}
          </div>
        </Panel>
        <Panel title="Misconception strength over time" className="lg:col-span-4">
          <OverTimeChart snapshots={ov.snapshots} kind="misconception" names={names} />
        </Panel>
        <Panel title="Mastery over time" className="lg:col-span-4">
          <OverTimeChart snapshots={ov.snapshots} kind="mastery" names={names} />
        </Panel>
      </div>
    </div>
  );
}
