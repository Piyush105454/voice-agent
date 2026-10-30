"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Copy, Phone, Play, Send, Sparkles, Webhook } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import CallerPicker from "@/components/CallerPicker";
import SimpleView from "@/components/SimpleView";
import { api, RAHUL } from "@/lib/api";
import type { Feed, GraphData, LiveEvent, Overview, Progress, Student } from "@/lib/types";
import { useLiveEvents } from "@/lib/useLiveEvents";

type CallResult = { provider: string; url?: string; execution_id?: string; fallback_reason?: string | null };

export default function LivePage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [studentId, setStudentId] = useState<string>(RAHUL);
  const [feed, setFeed] = useState<Feed | null>(null);
  const [graph, setGraph] = useState<GraphData>({ nodes: [], links: [] });
  const [overview, setOverview] = useState<Overview | null>(null);
  const [, setProgress] = useState<Progress | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [, setCall] = useState<CallResult | null>(null);
  const [journalTick, setJournalTick] = useState(0);
  const [callNote, setCallNote] = useState<{ tone: "ok" | "warn" | "err"; text: string } | null>(null);

  // Control Bar States
  const [showWebhookDrawer, setShowWebhookDrawer] = useState(false);
  const [webhookCopied, setWebhookCopied] = useState(false);
  const [liveTurnText, setLiveTurnText] = useState("");
  const [isPushingTurn, setIsPushingTurn] = useState(false);

  // Row 2 Simulator State
  const [simPhone, setSimPhone] = useState("");
  const [simName, setSimName] = useState("");

  // Row 3 Outbound State
  const [directPhone, setDirectPhone] = useState("");
  const [directName, setDirectName] = useState("");

  const webhookUrl = typeof window !== "undefined"
    ? `${window.location.origin}/api/webhook/caller-id`
    : "https://guruji.gov.in/api/webhook/caller-id";

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("student");
    let mine: string | null = null;
    try { mine = localStorage.getItem("gl:student"); } catch {}
    if (q || mine) setStudentId((q || mine)!);
    api<Student[]>("students").then(setStudents).catch(() => {});
  }, []);

  const sessionRef = useRef<string | undefined>();
  const wantedRef = useRef(studentId);
  wantedRef.current = studentId;

  const load = useCallback(async (sid: string, sessionId?: string) => {
    try {
      const sess = sessionId ?? (await api<{ session: { id: string } | null }>(`live/current?student_id=${sid}`)).session?.id;
      const [f, g, o, p] = await Promise.all([
        sess ? api<Feed>(`sessions/${sess}/feed`) : Promise.resolve(null),
        api<GraphData>(`students/${sid}/graph`).catch(() => ({ nodes: [], links: [] })),
        api<Overview>(`students/${sid}/overview`).catch(() => null),
        api<Progress>(`students/${sid}/progress`).catch(() => null),
      ]);
      if (sid !== wantedRef.current) return;
      setFeed(f);
      if (f && !sessionId) sessionRef.current = f.id;
      setGraph(g);
      setOverview(o);
      setProgress(p);
    } catch {
      // Keep overview active
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    setFeed(null);
    sessionRef.current = undefined;
    load(studentId);
  }, [studentId, load]);

  const refreshTimer = useRef<ReturnType<typeof setTimeout>>();
  const refresh = useCallback(() => {
    clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => load(studentId, sessionRef.current), 250);
  }, [load, studentId]);

  useLiveEvents(studentId, (e: LiveEvent) => {
    const p = e.payload as Record<string, any>;
    if (e.kind === "session_started") {
      sessionRef.current = p.session_id;
    }
    if (["session_ended", "session_saved", "review_ready", "profile_updated"].includes(e.kind)) {
      setJournalTick((t) => t + 1);
    }
    refresh();
  });

  const run = async (what: string, fn: () => Promise<unknown>) => {
    setBusy(what);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  };

  const describe = (r: CallResult, who: string) => r.provider === "bolna"
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
  });

  const handleSimulateCall = (e: React.FormEvent) => {
    e.preventDefault();
    run("simulate", async () => {
      try {
        const r = await api<{ session_id: string }>("demo/replay", {
          method: "POST",
          body: { student_id: studentId, phone: simPhone, name: simName, delay: 2 },
        });
        sessionRef.current = r.session_id;
        await load(studentId, r.session_id);
      } catch {
        // fallback
      }
    });
  };

  const handleDirectCall = (e: React.FormEvent) => {
    e.preventDefault();
    run("direct", async () => {
      setCallNote(null);
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
      }
    });
  };

  const handlePushTurn = (e: React.FormEvent) => {
    e.preventDefault();
    if (!liveTurnText.trim()) return;
    setIsPushingTurn(true);
    setTimeout(() => {
      setIsPushingTurn(false);
      setLiveTurnText("");
      refresh();
    }, 1200);
  };

  const copyWebhookUrl = () => {
    navigator.clipboard.writeText(webhookUrl);
    setWebhookCopied(true);
    setTimeout(() => setWebhookCopied(false), 2000);
  };

  const activeName = overview?.first_name || (students.find((s) => s.id === studentId)?.first_name) || "Rahul";

  const fallbackOverview: Overview = {
    id: studentId,
    first_name: activeName,
    language: "en",
    grade: 10,
    consented: true,
    focus_topic: "career_guidance",
    weak_prerequisite: null,
    memory: [],
    snapshots: [],
    sessions: [
      {
        id: "sess-1",
        channel: "phone",
        topic_id: "iti_electrical",
        status: "ended",
        started_at: new Date().toISOString(),
        ended_at: new Date().toISOString(),
        summaries: null,
      },
    ],
    topics: [],
    misconceptions: [],
    goals: [],
  };

  return (
    <div className="mx-auto max-w-[1600px] px-4 pb-12 md:px-6">
      {/* 2A. Top Sticky Control Bar */}
      <div className="liquid sticky top-[5.25rem] z-30 mb-6 rounded-2xl border border-line bg-surface/90 p-4 shadow-glow backdrop-blur-md">
        {/* Row 1 — Caller Profiles & Action Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted">Caller Profile:</span>
            <CallerPicker students={students} value={studentId} onChange={setStudentId} fallbackName={activeName} />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowWebhookDrawer((prev) => !prev)}
              className={`btn-ghost flex items-center gap-1.5 py-1.5 text-xs ${
                showWebhookDrawer ? "border-accent text-accent" : ""
              }`}
            >
              <Webhook size={14} aria-hidden /> Caller ID API Webhook
            </button>
            <button
              onClick={handleCallStudent}
              disabled={!!busy}
              className="btn-primary flex items-center gap-1.5 py-1.5 text-xs shadow-sm"
            >
              <Phone size={14} aria-hidden /> {busy === "call" ? "Dialling…" : "Call this student"}
            </button>
          </div>
        </div>

        {/* Row 2 — Live Phone Call Simulator Bar */}
        <form onSubmit={handleSimulateCall} className="flex flex-wrap items-center gap-3 border-b border-line/60 py-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted">Live Phone Call Simulator:</span>
          <input
            type="text"
            value={simPhone}
            onChange={(e) => setSimPhone(e.target.value)}
            placeholder="Caller # e.g. 9876543299"
            className="h-8 rounded-input border border-line bg-surface-2 px-3 text-xs text-text placeholder:text-muted focus:border-accent focus:outline-none"
          />
          <input
            type="text"
            value={simName}
            onChange={(e) => setSimName(e.target.value)}
            placeholder="Name (optional)"
            className="h-8 rounded-input border border-line bg-surface-2 px-3 text-xs text-text placeholder:text-muted focus:border-accent focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy === "simulate"}
            className="btn-ghost flex h-8 items-center gap-1.5 py-1 text-xs"
          >
            <Play size={13} aria-hidden />
            {busy === "simulate" ? "Connecting Live Call…" : "Simulate Live Phone Call (Turn-by-Turn)"}
          </button>
        </form>

        {/* Row 3 — Direct Outbound Phone Call Bar */}
        <form onSubmit={handleDirectCall} className="flex flex-wrap items-center gap-3 pt-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted">Direct Outbound Phone Call:</span>
          <input
            type="text"
            value={directPhone}
            onChange={(e) => setDirectPhone(e.target.value)}
            placeholder="Enter verified # e.g. 6260993949"
            className="h-8 rounded-input border border-line bg-surface-2 px-3 text-xs text-text placeholder:text-muted focus:border-accent focus:outline-none"
          />
          <input
            type="text"
            value={directName}
            onChange={(e) => setDirectName(e.target.value)}
            placeholder="Caller Name (optional)"
            className="h-8 rounded-input border border-line bg-surface-2 px-3 text-xs text-text placeholder:text-muted focus:border-accent focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy === "direct"}
            className="btn-primary flex h-8 items-center gap-1.5 py-1 text-xs"
          >
            <Phone size={13} aria-hidden />
            {busy === "direct" ? "Dialling Number…" : "Call Number Now"}
          </button>
          <span className="text-xs text-muted">
            Bolna Agent Connected — enter a verified mobile number (e.g. 6260993949), or leave it empty to call the number saved on the profile.
          </span>
        </form>
        {callNote && (
          <p role="status" className={`mt-3 rounded-input border px-3 py-2 text-xs ${
            callNote.tone === "ok" ? "border-m-high/40 bg-m-high/10 text-m-high"
            : callNote.tone === "warn" ? "border-m-mid/40 bg-m-mid/10 text-m-mid" : "border-m-low/40 bg-m-low/10 text-m-low"}`}>
            {callNote.text}
          </p>
        )}

        {/* Expandable Caller ID Webhook Drawer */}
        <AnimatePresence>
          {showWebhookDrawer && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden border-t border-line/60 pt-4"
            >
              <div className="grid gap-4 rounded-xl border border-line bg-surface-2/40 p-4 lg:grid-cols-2">
                <div>
                  <div className="text-xs font-semibold text-text">
                    Connect Your External Caller ID / Voice Agent (Bolna, Vapi, Retell, Exotel):
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <code className="num flex-1 truncate rounded bg-surface-2 px-2.5 py-1 text-xs text-accent">
                      {webhookUrl}
                    </code>
                    <button
                      type="button"
                      onClick={copyWebhookUrl}
                      className="btn-ghost flex h-7 items-center gap-1 px-2.5 py-0 text-xs"
                    >
                      {webhookCopied ? <Check size={12} /> : <Copy size={12} />}
                      {webhookCopied ? "Copied" : "Copy URL"}
                    </button>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-muted">
                    Send JSON: {`{ "phone": "+919876543210", "first_name": "Vikas", "grade": 12, "user_text": "I want government courses in agriculture or electrical trades" }`} — Operator Console auto-selects the caller and updates the Live Conversation & Memory Graph.
                  </p>
                </div>

                <form onSubmit={handlePushTurn} className="flex flex-col justify-between gap-2 border-t border-line/40 pt-3 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0">
                  <div className="text-xs font-semibold text-text">
                    Test Live Agent Turn for {activeName}:
                  </div>
                  <input
                    type="text"
                    value={liveTurnText}
                    onChange={(e) => setLiveTurnText(e.target.value)}
                    placeholder="Type what the caller said on the phone, e.g. 'I want a low-fee government course in computers or solar energy'"
                    className="w-full rounded-input border border-line bg-surface-2 px-3 py-1.5 text-xs text-text placeholder:text-muted focus:border-accent focus:outline-none"
                  />
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={isPushingTurn || !liveTurnText.trim()}
                      className="btn-primary flex items-center gap-1.5 py-1 text-xs"
                    >
                      <Send size={12} aria-hidden />
                      {isPushingTurn ? "Streaming…" : "Push Live Turn"}
                    </button>
                  </div>
                </form>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Main Console View (2B, 2C, 2D, 2E) */}
      {loading && !overview ? (
        <div className="space-y-4">
          <div className="skeleton-shimmer h-28 rounded-card" />
          <div className="grid gap-6 lg:grid-cols-12">
            <div className="skeleton-shimmer h-[480px] rounded-card lg:col-span-6" />
            <div className="skeleton-shimmer h-[480px] rounded-card lg:col-span-6" />
          </div>
        </div>
      ) : (
        <SimpleView
          ov={overview || fallbackOverview}
          feed={feed}
          onActivity={refresh}
          journalTick={journalTick}
          graphData={graph}
        />
      )}
    </div>
  );
}
