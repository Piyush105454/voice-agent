from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:80])
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")


edit("web/lib/types.ts", [
    ('''  language: string;
  grade: number;
  consented: boolean;
  topics: TopicMastery[];''', '''  language: string;
  grade: number | null;
  about?: string | null;
  phone_e164?: string | null;
  consented: boolean;
  topics: TopicMastery[];'''),
])

# ---------------------------------------------------------------- the live panel shows REAL calls
edit("web/components/SimpleView.tsx", [
    ('import { useMemo, useState } from "react";', 'import { useEffect, useMemo, useState } from "react";'),
    ('import type { Feed, GraphData, Overview } from "@/lib/types";',
     'import { api } from "@/lib/api";\nimport type { Feed, GraphData, Line, Overview } from "@/lib/types";\n\n'
     'const TABS = ["Latest call", "Previous", "Earlier"] as const;   // newest first\n'
     'const LANG_LABEL: Record<string, string> = { hi: "Hindi", en: "English", "hi-en": "Hinglish" };'),
    ('''  const [selectedCall, setSelectedCall] = useState<"Call #3" | "Call #2" | "Call #1">("Call #3");''',
     '''  const [tab, setTab] = useState(0);
  const [past, setPast] = useState<Record<string, Line[]>>({});'''),
    ('''  const activeTranscript = useMemo(() => {
    if (feed && feed.lines && feed.lines.length > 0 && selectedCall === "Call #3") {
      return feed.lines.map((l) => ({ speaker: l.speaker, text: l.text }));
    }
    if (selectedCall === "Call #3") return isRahul ? SEED_TRANSCRIPT_RAHUL : [];
    if (selectedCall === "Call #2") return SEED_CALL_2;
    return SEED_CALL_1;
  }, [feed, selectedCall, isRahul]);''',
     '''  // The student's real calls, newest first. A call's transcript is fetched when its tab is opened and refetched
  // whenever the list changes (phone transcripts arrive after hang-up, so an earlier empty answer goes stale).
  const sess = ov.sessions[tab];
  const sessKey = ov.sessions.map((s) => `${s.id}:${s.ended_at ?? ""}`).join(",");
  useEffect(() => setPast({}), [sessKey, feed?.lines?.length]);
  useEffect(() => {
    if (!sess || feed?.id === sess.id || past[sess.id]) return;
    api<Feed>(`sessions/${sess.id}/feed`).then((f) => setPast((p) => ({ ...p, [sess.id]: f.lines }))).catch(() => {});
  }, [sess?.id, feed?.id, past]);

  const activeTranscript = useMemo(() => {
    if (sess) {
      const lines = feed?.id === sess.id ? feed.lines : past[sess.id];
      return (lines ?? []).map((l) => ({ speaker: l.speaker, text: l.text }));
    }
    // no real call yet: only the built-in demo student shows the sample conversation
    if (ov.sessions.length === 0 && isRahul) return tab === 0 ? SEED_TRANSCRIPT_RAHUL : tab === 1 ? SEED_CALL_2 : SEED_CALL_1;
    return [];
  }, [sess, feed, past, tab, isRahul, ov.sessions.length]);
  const loadingCall = !!sess && feed?.id !== sess.id && past[sess.id] === undefined;
  const inProgress = !!sess && !sess.ended_at;'''),
    ('''                {isRahul ? "Class 10 · English" : ov.grade ? `Class ${ov.grade} · Hindi` : "College (Electrical Eng.) · Hindi"}
              </span>
              <span className="num rounded-full border border-line bg-surface-2 px-3 py-1 text-xs text-muted">
                +91 ••••• •3210
              </span>''',
     '''                {ov.about || (ov.grade ? `Class ${ov.grade}` : "Open profile")} · {LANG_LABEL[ov.language] ?? ov.language}
              </span>
              {ov.phone_e164 && (
                <span className="num rounded-full border border-line bg-surface-2 px-3 py-1 text-xs text-muted">
                  +91 ••••• •{ov.phone_e164.slice(-4)}
                </span>
              )}'''),
    ('''              {(["Call #3", "Call #2", "Call #1"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setSelectedCall(tab)}
                  className={`rounded-full px-3 py-1 transition-colors ${
                    selectedCall === tab ? "bg-accent text-black font-medium" : "text-muted hover:text-text"
                  }`}
                >
                  {tab}
                </button>
              ))}''',
     '''              {TABS.map((label, i) => (
                <button
                  key={label}
                  onClick={() => setTab(i)}
                  disabled={!ov.sessions[i] && !(i === 0)}
                  className={`rounded-full px-3 py-1 transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                    tab === i ? "bg-accent text-black font-medium" : "text-muted hover:text-text"
                  }`}
                >
                  {label}
                </button>
              ))}'''),
    ('''                <div className="font-serif text-lg text-text">Waiting for caller speech…</div>
                <p className="mt-1 max-w-sm text-xs">
                  Simulate an incoming call above, place a direct phone call, or send a Caller ID webhook.
                </p>''',
     '''                <div className="font-serif text-lg text-text">
                  {loadingCall ? "Loading this call…" : inProgress ? "Call in progress…" : sess ? "Nothing was said on this call" : "No call yet"}
                </div>
                <p className="mt-1 max-w-sm text-xs">
                  {loadingCall ? "" : inProgress
                    ? "Bolna sends the conversation when the call ends. It appears here by itself, no refresh needed."
                    : sess ? "The call ended before anyone spoke (not answered, or hung up straight away)."
                    : "Place a direct phone call above, or simulate an incoming call."}
                </p>'''),
    ('''            Session: {feed?.id ? feed.id.slice(0, 8) : "c9f18a24"} (phone) · 30 Oct 2026, 05:30 PM IST''',
     '''            {sess
              ? `Session ${sess.id.slice(0, 8)} (${sess.channel}) · ${new Date(sess.started_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" })} IST`
              : "No call recorded yet"}'''),
])

# ---------------------------------------------------------------- the call buttons use the typed number and show the result
edit("web/app/live/page.tsx", [
    ('''  const [journalTick, setJournalTick] = useState(0);
''', '''  const [journalTick, setJournalTick] = useState(0);
  const [callNote, setCallNote] = useState<{ tone: "ok" | "warn" | "err"; text: string } | null>(null);
'''),
    ('''  const handleCallStudent = () => run("call", async () => {
    const r = await api<CallResult>("voice/call", { method: "POST", body: { student_id: studentId } });
    setCall(r);
  });''',
     '''  const describe = (r: CallResult, who: string) => r.provider === "bolna"
    ? { tone: "ok" as const, text: `Calling ${who} through Bolna. The conversation appears below when the call ends.` }
    : { tone: "warn" as const, text: `No phone call was placed (${r.fallback_reason ?? "Bolna unavailable"}). Browser call link: ${r.url ?? "not available"}` };

  const handleCallStudent = () => run("call", async () => {
    setCallNote(null);
    try {
      const r = await api<CallResult>("voice/call", { method: "POST", body: { student_id: studentId } });
      setCall(r);
      setCallNote(describe(r, activeName));
    } catch (e) {
      setCallNote({ tone: "err", text: (e as Error).message });
    }
  });'''),
    ('''      try {
        const r = await api<CallResult>("voice/call", {
          method: "POST",
          body: { student_id: studentId, phone: directPhone || "6260993949", name: directName },
        });
        setCall(r);
      } catch {
        // handled
      }''',
     '''      setCallNote(null);
      try {
        // the typed number is dialled; empty means the number saved on the caller's profile
        const r = await api<CallResult>("voice/call", {
          method: "POST",
          body: { student_id: studentId, phone: directPhone.trim() || undefined, name: directName.trim() || undefined },
        });
        setCall(r);
        setCallNote(describe(r, directPhone.trim() || activeName));
      } catch (e) {
        setCallNote({ tone: "err", text: (e as Error).message });
      }'''),
    ('''          <span className="text-xs text-muted">
            Bolna Agent Connected — enter a verified mobile number (e.g. 6260993949) and click Call Number Now.
          </span>
        </form>''',
     '''          <span className="text-xs text-muted">
            Bolna Agent Connected — enter a verified mobile number (e.g. 6260993949), or leave it empty to call the number saved on the profile.
          </span>
        </form>
        {callNote && (
          <p role="status" className={`mt-3 rounded-input border px-3 py-2 text-xs ${
            callNote.tone === "ok" ? "border-m-high/40 bg-m-high/10 text-m-high"
            : callNote.tone === "warn" ? "border-m-mid/40 bg-m-mid/10 text-m-mid" : "border-m-low/40 bg-m-low/10 text-m-low"}`}>
            {callNote.text}
          </p>
        )}'''),
])
print("ok")
