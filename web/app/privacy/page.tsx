"use client";
import { Check, Download, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState, Panel, Skeleton } from "@/components/ui";
import { api, RAHUL } from "@/lib/api";
import { pretty } from "@/lib/format";
import type { Student } from "@/lib/types";

type Privacy = {
  id: string;
  first_name: string;
  is_minor: boolean;
  consents: { purpose: string; given_by: string; granted: boolean; granted_at: string; revoked_at: string | null }[];
  data_sources: { kind: string; purpose: string; created_at: string }[];
  audit: { actor: string; action: string; entity: string; created_at: string }[];
  counts: { memory_facts: number; sessions: number; attempts: number };
};

export default function PrivacyPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [sid, setSid] = useState(RAHUL);
  const [d, setD] = useState<Privacy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => { api<Student[]>("students").then(setStudents).catch(() => {}); }, []);
  const load = useCallback(() => {
    setD(null);
    api<Privacy>(`privacy/${sid}`).then((x) => { setD(x); setError(null); }).catch((e) => setError(e.message));
  }, [sid]);
  useEffect(() => { load(); }, [load]);

  const exportData = async () => {
    const data = await api<unknown>(`students/${sid}/memory`);
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `guruline-${d?.first_name ?? sid}.json` });
    a.click();
    URL.revokeObjectURL(url);
    setMsg("Export downloaded.");
    load();
  };
  const deleteAll = async () => {
    if (!window.confirm(`Delete everything Guru remembers about ${d?.first_name}? Sessions, transcripts, mastery, misconceptions and memory facts are removed from Postgres and the graph. This cannot be undone.`)) return;
    const r = await api<{ rows: Record<string, number> }>(`students/${sid}/memory`, { method: "DELETE" });
    setMsg(`Deleted: ${Object.entries(r.rows).filter(([, n]) => n).map(([k, n]) => `${n} ${pretty(k)}`).join(", ") || "nothing left to delete"}.`);
    load();
  };

  return (
    <div className="mx-auto max-w-5xl px-5 pb-16 pt-8 md:px-8">
      <div className="label">Privacy center</div>
      <h1 className="mt-1 font-serif text-5xl">Your data, your call.</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Guru only remembers learning: misconceptions, what helps, and goals. Never mood, personality, health or family details. Every fact links to the call it came from.
      </p>

      <label className="mt-8 flex items-center gap-3 text-sm">
        <span className="text-muted">Student</span>
        <select value={sid} onChange={(e) => setSid(e.target.value)} className="rounded-input border border-line bg-surface-2 px-3 py-1.5">
          {(students.length ? students : [{ id: RAHUL, first_name: "Rahul" } as Student]).map((s) => <option key={s.id} value={s.id}>{s.first_name}</option>)}
        </select>
      </label>

      {msg && <div className="card mt-4 px-4 py-3 text-sm" role="status">{msg}</div>}
      {error ? <div className="card mt-6"><ErrorState message={error} retry={load} /></div> : !d ? <Skeleton className="mt-6 h-96" /> : (
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <Panel title="Consent">
            {d.consents.length ? (
              <ul className="space-y-2 text-sm">
                {d.consents.map((c) => {
                  const on = c.granted && !c.revoked_at;
                  return (
                    <li key={c.purpose} className="flex items-center justify-between gap-3">
                      <span className="capitalize">{pretty(c.purpose)}</span>
                      <span className={`chip border ${on ? "border-m-high/40 text-m-high" : "border-m-low/40 text-m-low"}`}>
                        {on ? <Check size={12} aria-hidden /> : <X size={12} aria-hidden />} {on ? `given by ${c.given_by}` : "revoked"}
                      </span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <EmptyState title="No consent on file" hint={`Calls to ${d.first_name} are refused until a ${d.is_minor ? "guardian" : "student"} gives consent.`} />
            )}
          </Panel>
          <Panel title="What is stored">
            <dl className="grid grid-cols-3 gap-3 text-center">
              {Object.entries(d.counts).map(([k, v]) => (
                <div key={k} className="rounded-input border border-line p-3"><dd className="num text-2xl">{v}</dd><dt className="mt-1 text-xs text-muted">{pretty(k)}</dt></div>
              ))}
            </dl>
            <div className="mt-4 flex flex-wrap gap-2">
              <button onClick={exportData} className="btn-ghost"><Download size={15} aria-hidden /> Export my data</button>
              <button onClick={deleteAll} className="btn border border-m-low/50 text-m-low hover:bg-m-low/10"><Trash2 size={15} aria-hidden /> Delete everything</button>
            </div>
          </Panel>
          <Panel title="Data sources (consented only)">
            {d.data_sources.length ? (
              <ul className="space-y-2 text-sm">
                {d.data_sources.map((s) => <li key={s.kind}><span className="capitalize">{pretty(s.kind)}</span><span className="block text-xs text-muted">{s.purpose}</span></li>)}
              </ul>
            ) : <EmptyState title="No data sources" />}
          </Panel>
          <Panel title="Who accessed this data">
            {d.audit.length ? (
              <ul className="max-h-64 space-y-1.5 overflow-y-auto text-sm">
                {d.audit.map((a, i) => (
                  <li key={i} className="flex justify-between gap-3"><span>{a.actor} <span className="text-muted">{pretty(a.action)}</span></span><span className="num shrink-0 text-xs text-muted">{new Date(a.created_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}</span></li>
                ))}
              </ul>
            ) : <EmptyState title="No access recorded" />}
          </Panel>
        </div>
      )}
    </div>
  );
}
