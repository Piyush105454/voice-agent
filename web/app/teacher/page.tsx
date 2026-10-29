"use client";
import { ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState, Panel, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { ago, masteryBand } from "@/lib/format";

type Teacher = {
  students: { id: string; first_name: string; grade: number; avg_mastery: number | null; last_session: string | null }[];
  summaries: { body: string; created_at: string; student_id: string; first_name: string }[];
  open_safety_events: { id: string; student_id: string | null; first_name: string | null; created_at: string }[];
  heatmap: { misconceptions: { id: string; name: string }[]; students: { id: string; first_name: string }[]; cells: { student_id: string; misconception_id: string; strength: number }[] };
};

const ACTIONS: Record<string, string> = {
  adds_instead_of_inverse: "a 5-minute “balance scale” warm-up on undoing + and −",
  sign_not_flipped: "move-the-term drills, saying the new sign out loud",
  coefficient_ignored: "read “5x” aloud as “5 times x” before solving",
  neg_number_confusion: "number-line jumps with signed steps",
  distributes_partially: "“arrow from the outside number to every term” drill",
  equals_as_answer: "true/false equations like 7 = 5 + 2",
};

export default function TeacherPage() {
  const [d, setD] = useState<Teacher | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api<Teacher>("teacher/overview").then((x) => { setD(x); setError(null); }).catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);

  if (error) return <div className="mx-auto max-w-7xl px-5 py-10"><div className="card"><ErrorState message={error} retry={load} /></div></div>;
  if (!d) return <div className="mx-auto max-w-7xl space-y-4 px-5 py-10"><Skeleton className="h-16" /><Skeleton className="h-80" /></div>;

  const cell = (sid: string, mid: string) => d.heatmap.cells.find((c) => c.student_id === sid && c.misconception_id === mid)?.strength;
  // Most common misconception across the class (count of students with strength > 0.4)
  const counts = d.heatmap.misconceptions
    .map((m) => ({ ...m, n: d.heatmap.cells.filter((c) => c.misconception_id === m.id && c.strength > 0.4).length }))
    .sort((a, b) => b.n - a.n);
  const top = counts[0];
  // Positive framing: each student's strongest active misconception -> what would help
  const support = d.heatmap.students
    .map((s) => {
      const mine = d.heatmap.cells.filter((c) => c.student_id === s.id && c.strength > 0.4).sort((a, b) => b.strength - a.strength)[0];
      return mine ? { ...s, mis: d.heatmap.misconceptions.find((m) => m.id === mine.misconception_id)! } : null;
    })
    .filter(Boolean) as { id: string; first_name: string; mis: { id: string; name: string } }[];

  return (
    <div className="mx-auto max-w-7xl px-5 pb-16 pt-8 md:px-8">
      <div className="label">Teacher · Class 8A</div>
      <h1 className="mt-1 font-serif text-5xl">Where the class is stuck, and why.</h1>
      <p className="mt-2 max-w-2xl text-muted">Misconceptions, not marks. No rankings, no comparisons between students.</p>

      {d.open_safety_events.length > 0 && (
        <div className="card mt-6 flex items-start gap-3 border-m-low/50 bg-m-low/10 p-4" role="alert">
          <ShieldAlert className="mt-0.5 shrink-0 text-m-low" size={18} aria-hidden />
          <div className="text-sm">
            <div className="font-medium">Safety follow-up needed</div>
            {d.open_safety_events.map((e) => (
              <div key={e.id} className="text-muted">{e.first_name ?? "A student"} said something during a call that needs a trusted adult · {ago(e.created_at)}. The lesson was stopped. Please check in personally.</div>
            ))}
          </div>
        </div>
      )}

      {top && top.n > 0 && (
        <div className="card mt-6 p-5 shadow-glow">
          <div className="label">Suggested class action</div>
          <p className="mt-2 font-serif text-2xl">
            {top.n} student{top.n > 1 ? "s" : ""} hold “{top.name}”. Try: {ACTIONS[top.id] ?? "a short targeted warm-up"}.
          </p>
        </div>
      )}

      <Panel title="Misconception heat-map" className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[640px] border-separate border-spacing-1 text-sm">
          <caption className="sr-only">Strength of each misconception per student (0 to 1)</caption>
          <thead>
            <tr>
              <th className="text-left font-normal text-muted">Misconception</th>
              {d.heatmap.students.map((s) => (
                <th key={s.id} className="font-normal text-muted"><Link className="hover:text-text" href={`/students/${s.id}`}>{s.first_name}</Link></th>
              ))}
            </tr>
          </thead>
          <tbody>
            {d.heatmap.misconceptions.map((m) => (
              <tr key={m.id}>
                <th scope="row" className="whitespace-nowrap pr-3 text-left font-normal">{m.name}</th>
                {d.heatmap.students.map((s) => {
                  const v = cell(s.id, m.id);
                  return (
                    <td key={s.id} className="h-10 rounded-md text-center num text-xs"
                      style={{ background: v ? `rgba(183,148,246,${0.12 + v * 0.75})` : "var(--surface-2)", color: v ? (v > 0.55 ? "#0b0c0e" : "var(--text)") : "var(--muted)" }}
                      title={v ? `${s.first_name}: ${m.name} ${v.toFixed(2)}` : `${s.first_name}: not observed`}>
                      {v ? v.toFixed(2) : "·"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="Would benefit from">
          {support.length ? (
            <ul className="space-y-3 text-sm">
              {support.map((s) => (
                <li key={s.id} className="flex items-start justify-between gap-3">
                  <span><Link href={`/students/${s.id}`} className="font-medium hover:text-accent">{s.first_name}</Link> would benefit from a recap on <span className="text-misc">{s.mis.name.toLowerCase()}</span>.</span>
                </li>
              ))}
            </ul>
          ) : <EmptyState title="No active misconceptions" />}
        </Panel>
        <Panel title="Students">
          <ul className="space-y-2 text-sm">
            {d.students.map((s) => {
              const band = masteryBand(s.avg_mastery);
              return (
                <li key={s.id} className="flex items-center justify-between gap-3">
                  <Link href={`/students/${s.id}`} className="hover:text-accent">{s.first_name}</Link>
                  <span className="text-xs text-muted">{band.label} · last call {ago(s.last_session)}</span>
                </li>
              );
            })}
          </ul>
        </Panel>
      </div>

      <Panel title="Latest summaries" className="mt-4">
        {d.summaries.length ? (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {d.summaries.slice(0, 9).map((s, i) => (
              <article key={i} className="rounded-input border border-line p-4">
                <div className="mb-2 flex justify-between text-xs text-muted"><span className="text-text">{s.first_name}</span>{ago(s.created_at)}</div>
                <p className="whitespace-pre-line text-sm leading-relaxed">{s.body}</p>
              </article>
            ))}
          </div>
        ) : <EmptyState title="No summaries yet" hint="They appear after each call." />}
      </Panel>
    </div>
  );
}
