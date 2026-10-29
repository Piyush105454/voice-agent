from pathlib import Path
p = Path("web/components/JournalPanel.tsx"); s = p.read_text(encoding="utf-8")

s = s.replace('import { BookOpen, Lightbulb, NotebookPen, Quote } from "lucide-react";',
              'import { BookOpen, Compass, Lightbulb, NotebookPen, Quote, Sparkles } from "lucide-react";')
s = s.replace('import type { JournalDay, Resource } from "@/lib/types";',
              'import type { JournalDay, LearnerProfile, Resource } from "@/lib/types";')

old_card = 'export default function JournalPanel('
new_card = '''function ProfileCard({ p }: { p: LearnerProfile }) {
  const rows: [string, string | string[] | undefined][] = [
    ["What drives you", p.motivation], ["Your confidence", p.confidence_pattern],
    ["What works for you", p.what_works], ["Keep fixing", p.recurring_mistakes],
  ];
  return (
    <div className="border-gradient mb-7 rounded-card bg-surface p-5">
      <div className="flex items-center gap-2 text-sm font-medium"><Sparkles size={16} className="text-accent" aria-hidden />
        What Guru knows about you <span className="text-xs font-normal text-muted">· updated after every call</span></div>
      {p.direction && (
        <p className="mt-3 flex gap-2 font-serif text-lg leading-snug"><Compass size={18} className="mt-1 shrink-0 text-accent" aria-hidden />{p.direction}</p>
      )}
      <dl className="mt-4 grid gap-4 sm:grid-cols-2">
        {rows.filter(([, v]) => v && (!Array.isArray(v) || v.length)).map(([k, v]) => (
          <div key={k}>
            <dt className="label">{k}</dt>
            <dd className="mt-1 text-sm text-muted">{Array.isArray(v) ? v.slice(0, 3).join(" · ") : v}</dd>
          </div>
        ))}
      </dl>
      {p.next_call_plan && <p className="mt-4 rounded-input bg-surface-2/70 px-3 py-2 text-sm"><span className="text-accent">Next call:</span> {p.next_call_plan}</p>}
    </div>
  );
}

export default function JournalPanel('''
assert old_card in s; s = s.replace(old_card, new_card, 1)

s = s.replace('''  const [data, setData] = useState<{ days: JournalDay[]; resources: Resource[] } | null>(null);
  useEffect(() => {
    api<{ days: JournalDay[]; resources: Resource[] }>(`students/${studentId}/journal`).then(setData).catch(() => setData(null));''',
'''  type Journal = { days: JournalDay[]; resources: Resource[]; profile: LearnerProfile | null };
  const [data, setData] = useState<Journal | null>(null);
  useEffect(() => {
    api<Journal>(`students/${studentId}/journal`).then(setData).catch(() => setData(null));''')

old_res = '''      {data?.resources.length ? ('''
assert old_res in s
s = s.replace(old_res, '''      {data?.profile && <ProfileCard p={data.profile} />}

      {data?.resources.length ? (''', 1)
p.write_text(s, encoding="utf-8")

t = Path("web/lib/types.ts"); u = t.read_text(encoding="utf-8")
u = u.replace('export type JournalDay = {', '''export type LearnerProfile = {
  about?: string; motivation?: string; confidence_pattern?: string; recurring_mistakes?: string[];
  what_works?: string[]; watch_outs?: string[]; direction?: string; next_call_plan?: string; updated_at?: string;
};
export type JournalDay = {''', 1)
t.write_text(u, encoding="utf-8"); print("ok")
