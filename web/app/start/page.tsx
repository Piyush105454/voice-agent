"use client";
// New student sign-up: profile + consent captured ONCE, so calls never read a recording notice.
// The device remembers the student (localStorage), so they land straight in their own space next time.
import { motion } from "framer-motion";
import { ArrowRight, Check, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const LANGS = [
  { value: "", label: "Ask me on the call" },
  { value: "hi-en", label: "Hinglish" },
  { value: "hi", label: "Hindi" },
  { value: "en", label: "English" },
];

export default function StartPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [grade, setGrade] = useState("");
  const [language, setLanguage] = useState("");
  const [adult, setAdult] = useState(false);
  const [phone, setPhone] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState<{ id: string; name: string } | null>(null);

  useEffect(() => {
    try {
      const id = localStorage.getItem("gl:student"), n = localStorage.getItem("gl:student-name");
      if (id && n) setSaved({ id, name: n });
    } catch {}
  }, []);

  const submit = async () => {
    setErr(null);
    if (!name.trim()) return setErr("Please tell us your name.");
    if (!consent) return setErr("Please tick the permission box to continue.");
    setBusy(true);
    try {
      const r = await api<{ student_id: string }>("students", {
        method: "POST",
        body: { first_name: name.trim(), grade: grade ? Number(grade) : null, language: language || null,
                is_minor: !adult, phone: phone.trim() || null, consent },
      });
      localStorage.setItem("gl:student", r.student_id);
      localStorage.setItem("gl:student-name", name.trim());
      localStorage.setItem("gl:view", "simple");
      router.push(`/live?student=${r.student_id}`);
    } catch (e) {
      setErr((e as Error).message);
      setBusy(false);
    }
  };

  const field = "w-full rounded-input border border-line bg-surface px-4 py-3 text-base outline-none transition focus:border-accent";

  return (
    <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-20 pt-6 md:px-8 lg:grid-cols-[1fr_1.05fr]">
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <div className="label">Get started</div>
        <h1 className="mt-3 font-serif text-5xl leading-[1.05] md:text-6xl">Your own coach, <span className="hl">ready in a minute.</span></h1>
        <p className="mt-5 max-w-md text-lg text-muted">
          Tell Guru a little about you. Then just talk — about any subject, exam, skill or goal. Guru remembers every call and helps you improve day by day.
        </p>
        <ul className="mt-7 space-y-2.5 text-muted">
          {["No app, no password — this device remembers you", "Talk in Hindi, English or a mix", "Your journal of progress builds itself"].map((t) => (
            <li key={t} className="flex items-center gap-2"><Check size={16} className="text-m-high" /> {t}</li>
          ))}
        </ul>
        {saved && (
          <Link href={`/live?student=${saved.id}`} className="btn-ghost mt-8">Continue as {saved.name} <ArrowRight size={15} /></Link>
        )}
      </motion.div>

      <motion.form initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.1 }}
        onSubmit={(e) => { e.preventDefault(); submit(); }} className="card space-y-5 p-7 md:p-9" aria-label="Sign up">
        <div>
          <label htmlFor="name" className="mb-1.5 block text-sm font-medium">Your first name</label>
          <input id="name" value={name} onChange={(e) => setName(e.target.value)} maxLength={40} autoComplete="given-name"
            placeholder="e.g. Priya" className={field} autoFocus />
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="grade" className="mb-1.5 block text-sm font-medium">Class <span className="text-muted">(optional)</span></label>
            <select id="grade" value={grade} onChange={(e) => setGrade(e.target.value)} className={field}>
              <option value="">Not in school / skip</option>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => <option key={g} value={g}>Class {g}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="lang" className="mb-1.5 block text-sm font-medium">Language</label>
            <select id="lang" value={language} onChange={(e) => setLanguage(e.target.value)} className={field}>
              {LANGS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label htmlFor="phone" className="mb-1.5 block text-sm font-medium">Phone <span className="text-muted">(optional — for Guru to call you)</span></label>
          <input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" placeholder="+91 98765 43210" className={field} />
        </div>
        <label className="flex cursor-pointer items-center gap-3 text-sm">
          <input type="checkbox" checked={adult} onChange={(e) => setAdult(e.target.checked)} className="h-4 w-4 accent-[var(--accent)]" />
          I am 18 or older
        </label>
        <label className="flex cursor-pointer items-start gap-3 rounded-input border border-line bg-surface-2/60 p-4 text-sm">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--accent)]" />
          <span>
            {adult ? "I agree" : "My parent or guardian agrees"} that my calls with Guru are recorded to track my learning, and that
            summaries are shared with my teacher and parent. I can export or delete my data anytime in Privacy.
            <span className="mt-1 block text-muted">Guru is an AI. It never guesses feelings from your voice.</span>
          </span>
        </label>
        {err && <p className="text-sm text-m-low" role="alert">{err}</p>}
        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} type="submit" disabled={busy}
          className="btn-primary w-full py-3.5 text-base">
          {busy ? <Loader2 size={18} className="animate-spin" /> : <>Start talking to Guru <ArrowRight size={16} /></>}
        </motion.button>
      </motion.form>
    </div>
  );
}
