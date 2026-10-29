"use client";
// "My goals": the student's own aim per mode + the AI-made 4-week plan, with this week's focus highlighted.
import { Flag, Plus } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Goal, Mode } from "@/lib/types";

export const MODE_LABEL: Record<Mode | "open", string> = { coach: "Mentoring", maths: "Maths", english: "English speaking", topic: "Any topic", open: "Open call" };
const GOAL_MODES: Mode[] = ["topic", "english", "maths"];
const EXAMPLES: Record<Mode, string> = {
  coach: "Score 90 in my board exams",
  maths: "Pass my maths test next month",
  english: "Speak English confidently in interviews",
  topic: "Become an AI engineer",
};

function weekIndex(created: string) {
  return Math.max(0, Math.floor((Date.now() - new Date(created).getTime()) / (7 * 86400000)));
}

export default function GoalsPanel({ studentId, goals, onChange }: { studentId: string; goals: Goal[]; onChange: () => void }) {
  const [mode, setMode] = useState<Mode>("topic");
  const [aim, setAim] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const active = goals.filter((g) => g.status === "active");

  const save = async () => {
    if (aim.trim().length < 3) return;
    setSaving(true);
    setErr(null);
    try {
      await api(`students/${studentId}/goals`, { method: "POST", body: { mode, aim: aim.trim() } });
      setAim("");
      onChange();
      setTimeout(onChange, 15000); // the plan is written in the background (~10 s); refresh again to show it
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="card p-6">
      <div className="mb-4 flex items-center gap-2 font-medium"><Flag size={18} className="text-accent" aria-hidden /> My goals</div>

      {active.length ? (
        <ul className="space-y-4">
          {active.map((g) => {
            const weeks = g.plan?.weeks ?? [];
            const now = Math.min(weeks.length - 1, weekIndex(g.created_at));
            return (
              <li key={g.id} className="rounded-input border border-line p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div className="text-lg">{g.aim}</div>
                  <span className="chip border border-line text-muted">{MODE_LABEL[g.mode]} · {g.sessions} call{g.sessions === 1 ? "" : "s"}</span>
                </div>
                {weeks.length ? (
                  <ol className="mt-3 grid gap-2 sm:grid-cols-4">
                    {weeks.map((w, i) => (
                      <li key={w.week} className={`rounded-input border px-3 py-2 text-sm ${i === now ? "border-accent bg-accent/10" : "border-line"}`}>
                        <div className="text-xs text-muted">Week {w.week}{i === now ? " · now" : ""}</div>
                        <div className="mt-0.5">{w.focus}</div>
                        <div className="mt-1 text-xs text-muted">✓ {w.milestone}</div>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-2 text-sm text-muted">Guru is making your 4-week plan…</p>
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-muted">No goal yet. Tell Guru on a call, or type one below.</p>
      )}

      <form className="mt-5 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); save(); }}>
        <select value={mode} onChange={(e) => setMode(e.target.value as Mode)} aria-label="Goal type"
          className="rounded-input border border-line bg-surface-2 px-3 py-2 text-sm">
          {GOAL_MODES.map((m) => <option key={m} value={m}>{MODE_LABEL[m]}</option>)}
        </select>
        <input value={aim} onChange={(e) => setAim(e.target.value)} placeholder={`e.g. ${EXAMPLES[mode]}`} maxLength={200}
          className="min-w-0 flex-1 rounded-input border border-line bg-surface-2 px-3 py-2 text-sm" aria-label="Your goal" />
        <button className="btn-primary" disabled={saving || aim.trim().length < 3}><Plus size={15} aria-hidden /> {saving ? "Saving…" : "Set goal"}</button>
      </form>
      {err && <p className="mt-2 text-sm text-m-low" role="alert">{err}</p>}
    </section>
  );
}
