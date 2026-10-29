"use client";
import { MessageCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";

type Parent = {
  id: string;
  first_name: string;
  parent_hi: string | null;
  parent_en: string | null;
  sessions_this_week: number;
  plan: { day: number; topic: string; type: string; done: boolean }[];
  guardian: { name: string; preferred_language: string } | null;
};

const T = {
  hi: { title: "आज की पढ़ाई", none: "अभी कोई अपडेट नहीं है। पहली कॉल के बाद यहाँ दिखेगा।", plan: "अगले 3 दिन", day: "दिन", talk: "टीचर से बात करें", calls: "इस हफ़्ते कॉल" },
  en: { title: "Today's learning", none: "No update yet. It appears after the first call.", plan: "Next 3 days", day: "Day", talk: "Talk to the teacher", calls: "calls this week" },
};

export default function ParentPage({ params }: { params: { id: string } }) {
  const [d, setD] = useState<Parent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lang, setLang] = useState<"hi" | "en">("hi");
  useEffect(() => {
    api<Parent>(`parent/${params.id}`).then((x) => {
      setD(x);
      if (x.guardian?.preferred_language === "en") setLang("en");
    }).catch((e) => setError(e.message));
  }, [params.id]);

  if (error) return <div className="mx-auto max-w-md px-5 py-10"><ErrorState message={error} /></div>;
  if (!d) return <div className="mx-auto max-w-md space-y-4 px-5 py-10"><Skeleton className="h-12" /><Skeleton className="h-48" /></div>;

  const t = T[lang];
  // Show the update in the chosen language; if only the other language exists, show that rather than nothing.
  const body = (lang === "hi" ? d.parent_hi ?? d.parent_en : d.parent_en ?? d.parent_hi) ?? null;
  const days = [1, 2, 3].map((n) => d.plan.filter((p) => p.day === n));

  return (
    <div className="mx-auto min-h-screen max-w-md px-5 pb-16 pt-8" lang={lang}>
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-serif text-xl"><span className="h-2.5 w-2.5 rounded-full bg-accent" aria-hidden /> Guru Line</span>
        <div className="flex rounded-full border border-line p-1 text-sm" role="group" aria-label="Language">
          {(["hi", "en"] as const).map((l) => (
            <button key={l} onClick={() => setLang(l)} aria-pressed={lang === l}
              className={`rounded-full px-4 py-1.5 ${lang === l ? "bg-[var(--btn-bg)] text-[var(--btn-fg)]" : "text-muted"}`}>
              {l === "hi" ? "हिन्दी" : "English"}
            </button>
          ))}
        </div>
      </div>

      <h1 className={`mt-10 text-4xl ${lang === "hi" ? "font-deva font-medium" : "font-serif"}`}>{t.title}</h1>
      <p className="mt-1 text-muted">{d.first_name} · {d.sessions_this_week} {t.calls}</p>

      <div className={`card mt-6 space-y-4 p-6 text-xl leading-relaxed ${lang === "hi" ? "font-deva" : ""}`}>
        {body ? body.split("\n").map((s, i) => <p key={i}>{s}</p>) : <p className="text-base text-muted">{t.none}</p>}
      </div>

      {d.plan.length > 0 && (
        <div className="mt-8">
          <div className={`mb-3 text-[13px] text-muted ${lang === "hi" ? "font-deva" : "uppercase tracking-[0.14em]"}`}>{t.plan}</div>
          <ol className="flex items-start" aria-label={t.plan}>
            {days.map((items, i) => (
              <li key={i} className="flex flex-1 flex-col items-center text-center">
                <div className="flex w-full items-center">
                  <span className={`h-px flex-1 ${i === 0 ? "bg-transparent" : "bg-line"}`} />
                  <span className={`flex h-9 w-9 items-center justify-center rounded-full border text-sm ${items.every((x) => x.done) && items.length ? "border-m-high bg-m-high/20" : i === 0 ? "border-accent text-accent" : "border-line text-muted"}`}>{i + 1}</span>
                  <span className={`h-px flex-1 ${i === 2 ? "bg-transparent" : "bg-line"}`} />
                </div>
                <span className="mt-2 px-1 text-xs text-muted">{items.map((x) => x.topic).join(", ") || "—"}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <a href="mailto:sharma@school.example" className="btn-primary mt-10 w-full py-3.5 text-base">
        <MessageCircle size={18} aria-hidden /> <span className={lang === "hi" ? "font-deva" : ""}>{t.talk}</span>
      </a>
    </div>
  );
}
