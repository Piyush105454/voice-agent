"use client";
// "Your learning journal": what Guru suggested (books, quotes, methods) + a day-by-day timeline of calls,
// each with what improved and what is still to fix. Same data for phone and browser calls.
import { BookOpen, Lightbulb, NotebookPen, Quote } from "lucide-react";
import { useEffect, useState } from "react";
import { MODE_LABEL } from "@/components/GoalsPanel";
import { Stagger, StaggerItem } from "@/components/motion";
import { api } from "@/lib/api";
import type { JournalDay, Resource } from "@/lib/types";

const KIND = {
  book: { icon: BookOpen, label: "Book" },
  quote: { icon: Quote, label: "Quote" },
  method: { icon: Lightbulb, label: "Method" },
} as const;

function day(iso: string) {
  const d = new Date(iso), today = new Date();
  const diff = Math.floor((today.setHours(0, 0, 0, 0) - new Date(iso).setHours(0, 0, 0, 0)) / 86400000);
  return diff === 0 ? "Today" : diff === 1 ? "Yesterday" : d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}

function ResourceCard({ r }: { r: Resource }) {
  const k = KIND[r.kind] ?? KIND.method;
  return (
    <div className="card-hover h-full rounded-card border border-line bg-surface p-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-accent"><k.icon size={14} aria-hidden /> {k.label}</div>
      <div className={`mt-2 ${r.kind === "quote" ? "font-serif text-lg italic" : "font-medium"}`}>
        {r.kind === "quote" ? `“${r.title}”` : r.title}
      </div>
      {r.by && <div className="mt-0.5 text-sm text-muted">— {r.by}</div>}
      {r.why && <p className="mt-2 text-sm text-muted">{r.why}</p>}
    </div>
  );
}

export default function JournalPanel({ studentId, refreshKey }: { studentId: string; refreshKey: number }) {
  const [data, setData] = useState<{ days: JournalDay[]; resources: Resource[] } | null>(null);
  useEffect(() => {
    api<{ days: JournalDay[]; resources: Resource[] }>(`students/${studentId}/journal`).then(setData).catch(() => setData(null));
  }, [studentId, refreshKey]);

  return (
    <section className="card p-6" aria-label="Your learning journal">
      <div className="mb-1 flex items-center gap-2 font-medium"><NotebookPen size={18} className="text-accent" aria-hidden /> Your learning journal</div>
      <p className="mb-5 text-sm text-muted">Every call, day by day — what got better, what to fix next, and what Guru suggested.</p>

      {data?.resources.length ? (
        <>
          <div className="label mb-3">Guru&apos;s suggestions for you</div>
          <Stagger className="mb-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.resources.slice(0, 6).map((r, i) => <StaggerItem key={i} className="h-full"><ResourceCard r={r} /></StaggerItem>)}
          </Stagger>
        </>
      ) : null}

      {data?.days.length ? (
        <ol className="relative space-y-6 border-l border-line pl-6">
          {data.days.map((d) => (
            <li key={d.session_id} className="relative">
              <span className="absolute -left-[31px] top-1.5 h-3 w-3 rounded-full border-2 border-accent bg-[var(--bg)]" aria-hidden />
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-medium">{day(d.started_at)}</span>
                <span className="chip border border-line text-muted">{d.mode && d.mode !== "open" ? MODE_LABEL[d.mode] : "Call"}</span>
                <span className="text-xs text-muted">{d.channel === "phone" ? "Phone" : d.channel === "web" ? "Browser" : "Replay"}</span>
              </div>
              {d.summary ? <p className="mt-1.5">{d.summary}</p>
                : <p className="mt-1.5 text-sm text-muted">
                    {/* reviews are written ~10-30 s after a call; older calls without one just show what was practised */}
                    {Date.now() - new Date(d.started_at).getTime() < 20 * 60000 ? "Review on its way…"
                      : d.topic_id ? `Practised ${d.topic_id.replace(/^(alg|num)_/, "").replace(/_/g, " ")}` : "Call finished"}
                  </p>}
              {!!d.improvements?.length && (
                <ul className="mt-2 space-y-1 text-sm">
                  {d.improvements.slice(0, 3).map((x, i) => <li key={i} className="text-muted"><span className="text-accent">→</span> {x}</li>)}
                </ul>
              )}
              {!!d.resources?.length && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {d.resources.map((r, i) => {
                    const k = KIND[r.kind] ?? KIND.method;
                    return <span key={i} className="chip border border-line"><k.icon size={12} aria-hidden /> {r.title}</span>;
                  })}
                </div>
              )}
            </li>
          ))}
        </ol>
      ) : (
        <p className="py-4 text-center text-muted">Your journal starts with your first call.</p>
      )}
    </section>
  );
}
