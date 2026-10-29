"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState, ErrorState, Panel, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { pct, pretty } from "@/lib/format";

type Proof = {
  eval: {
    created_at: string;
    n_students: number;
    tag_accuracy: number;
    false_positive_rate: number;
    avg_hints: number;
    notes: string | null;
    report: { per_misconception?: { id: string; accuracy: number; n: number }[]; mastery_gain_by_day?: { day: number; gain: number }[] } | null;
  } | null;
  pilot: { student_id: string; first_name: string; acc_before: number; acc_after: number; conf_before: number | null; conf_after: number | null; sessions: number }[];
};

export default function ProofPage() {
  const [d, setD] = useState<Proof | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Proof>("proof").then(setD).catch((e) => setError(e.message)); }, []);

  if (error) return <div className="mx-auto max-w-7xl px-5 py-10"><div className="card"><ErrorState message={error} /></div></div>;
  if (!d) return <div className="mx-auto max-w-7xl space-y-4 px-5 py-10"><Skeleton className="h-40" /><Skeleton className="h-64" /></div>;
  const e = d.eval;
  const correct = e ? Math.round(e.tag_accuracy * e.n_students) : null;

  return (
    <div className="mx-auto max-w-7xl px-5 pb-16 pt-8 md:px-8">
      <div className="label">Proof</div>
      <section className="py-10">
        {e ? (
          <>
            <div className="num text-[clamp(64px,12vw,160px)] leading-none text-accent">{correct} / {e.n_students}</div>
            <p className="mt-4 max-w-2xl text-xl text-muted">synthetic students, correct misconception identified</p>
            <p className="mt-1 text-xs text-muted">Run {new Date(e.created_at).toLocaleString("en-IN")}{e.notes ? ` · ${e.notes}` : ""}</p>
          </>
        ) : (
          <>
            <div className="num text-[clamp(64px,12vw,160px)] leading-none text-line">— / 30</div>
            <p className="mt-4 max-w-2xl text-xl text-muted">The synthetic-student eval hasn&apos;t been run yet.</p>
          </>
        )}
      </section>

      {e && (
        <div className="grid gap-4 md:grid-cols-3">
          <Panel title="Tag accuracy"><div className="num text-4xl">{pct(e.tag_accuracy)}</div></Panel>
          <Panel title="False-positive rate"><div className="num text-4xl">{pct(e.false_positive_rate)}</div></Panel>
          <Panel title="Avg hints to solve"><div className="num text-4xl">{e.avg_hints.toFixed(1)}</div></Panel>
          {e.report?.per_misconception && (
            <Panel title="Accuracy by misconception" className="md:col-span-2">
              <div style={{ height: 240 }}>
                <ResponsiveContainer>
                  <BarChart data={e.report.per_misconception.map((m) => ({ name: pretty(m.id), accuracy: Math.round(m.accuracy * 100) }))} margin={{ left: -18 }}>
                    <CartesianGrid stroke="var(--line)" vertical={false} />
                    <XAxis dataKey="name" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} interval={0} angle={-15} textAnchor="end" height={60} />
                    <YAxis domain={[0, 100]} unit="%" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 10 }} />
                    <Bar dataKey="accuracy" fill="var(--accent)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          )}
        </div>
      )}

      <section className="mt-16">
        <h2 className="font-serif text-3xl">Real pilot</h2>
        <p className="mt-1 text-muted">Consented students on real calls, first session vs latest. Seeded demo data is never counted here.</p>
        {d.pilot.length ? (
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {d.pilot.map((p) => (
              <article key={p.student_id} className="card p-5">
                <div className="flex justify-between"><span className="font-serif text-2xl">{p.first_name}</span><span className="text-xs text-muted">{p.sessions} calls</span></div>
                <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div><dt className="label">Accuracy</dt><dd className="num mt-1 text-xl">{pct(p.acc_before)} → <span className="text-m-high">{pct(p.acc_after)}</span></dd></div>
                  <div><dt className="label">Confidence</dt><dd className="num mt-1 text-xl">{p.conf_before ?? "—"} → <span className="text-m-high">{p.conf_after ?? "—"}</span><span className="text-xs text-muted">/10</span></dd></div>
                </dl>
              </article>
            ))}
          </div>
        ) : (
          <div className="card mt-6"><EmptyState title="No real pilot calls yet" hint="Cards appear here after consented students finish real calls (phone or Sarvam web call)." /></div>
        )}
      </section>

      <p className="mt-12 border-t border-line pt-6 text-sm text-muted">
        Synthetic results are not a substitute for classroom trials. Confidence is self-reported (1–10); Guru never infers emotion from voice.
      </p>
    </div>
  );
}
