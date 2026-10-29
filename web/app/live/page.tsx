"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Copy, GraduationCap, Maximize2, Mic, Minimize2, Network, Phone, Play, RotateCcw, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CallPanel from "@/components/CallPanel";
import ChatTranscript from "@/components/ChatTranscript";
import KnowledgeGraph, { GraphLegend } from "@/components/KnowledgeGraph";
import { PillTabs } from "@/components/motion";
import SimpleView from "@/components/SimpleView";
import { ConfidenceAccuracyChart } from "@/components/Charts";
import { EmptyState, ErrorState, LiveBadge, MasteryBar, MisconceptionChip, Panel, Skeleton, Waveform } from "@/components/ui";
import { api, RAHUL } from "@/lib/api";
import { clock, dec, pretty } from "@/lib/format";
import type { Feed, GraphData, LiveEvent, Overview, Progress, Student } from "@/lib/types";
import { useLiveEvents } from "@/lib/useLiveEvents";

type Insight = { text: string; ts: number; tone: "misc" | "good" | "info" };
type CallResult = { provider: string; url?: string; execution_id?: string; fallback_reason?: string | null };

export default function LivePage() {
  const router = useRouter();
  const [students, setStudents] = useState<Student[]>([]);
  const [studentId, setStudentId] = useState<string>(RAHUL);
  const [feed, setFeed] = useState<Feed | null>(null);
  const [graph, setGraph] = useState<GraphData>({ nodes: [], links: [] });
  const [overview, setOverview] = useState<Overview | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState<Record<string, number>>({});
  const [insight, setInsight] = useState<Insight | null>(null);
  const [demo, setDemo] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [call, setCall] = useState<CallResult | null>(null);
  const [view, setView] = useState<"simple" | "advanced">("simple");
  const [browserCall, setBrowserCall] = useState(false);
  const [, tick] = useState(0);
  const [journalTick, setJournalTick] = useState(0); // phone calls: reviews/profile arrive after the call
  useEffect(() => {
    const v = localStorage.getItem("gl:view");
    if (v === "simple" || v === "advanced") setView(v);
  }, []);
  const pickView = (v: "simple" | "advanced") => {
    setView(v);
    localStorage.setItem("gl:view", v);
  };
  const graphRef = useRef(graph);
  graphRef.current = graph;

  useEffect(() => {
    // ?student=… wins; otherwise the student who signed up on this device; otherwise the demo student
    const q = new URLSearchParams(window.location.search).get("student");
    let mine: string | null = null;
    try { mine = localStorage.getItem("gl:student"); } catch {}
    if (q || mine) setStudentId((q || mine)!);
    api<Student[]>("students").then(setStudents).catch(() => {});
  }, []);

  const sessionRef = useRef<string | undefined>(); // which session the console follows
  const wantedRef = useRef(studentId);                // replies for a student we switched away from are dropped
  wantedRef.current = studentId;
  const load = useCallback(async (sid: string, sessionId?: string) => {
    try {
      const sess = sessionId ?? (await api<{ session: { id: string } | null }>(`live/current?student_id=${sid}`)).session?.id;
      const [f, g, o, p] = await Promise.all([
        sess ? api<Feed>(`sessions/${sess}/feed`) : Promise.resolve(null),
        api<GraphData>(`students/${sid}/graph`),
        api<Overview>(`students/${sid}/overview`),
        api<Progress>(`students/${sid}/progress`),
      ]);
      if (sid !== wantedRef.current) return;
      setFeed(f);
      if (f && !sessionId) sessionRef.current = f.id;
      setGraph(g);
      setOverview(o);
      setProgress(p);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
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

  // debounce refreshes: several events arrive per answer
  const refreshTimer = useRef<ReturnType<typeof setTimeout>>();
  const refresh = useCallback(() => {
    clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => load(studentId, sessionRef.current), 250);
  }, [load, studentId]);

  const say = (text: string, tone: Insight["tone"]) => setInsight({ text, tone, ts: Date.now() });
  const pulse = (...ids: (string | undefined)[]) =>
    setActive((a) => ({ ...a, ...Object.fromEntries(ids.filter(Boolean).map((id) => [id as string, Date.now()])) }));

  const mode = useLiveEvents(studentId, (e: LiveEvent) => {
    const p = e.payload as Record<string, any>;
    if (e.kind === "session_started") {
      sessionRef.current = p.session_id;
      say(`Session started · ${pretty(p.topic)}`, "info");
      pulse(studentId, p.topic);
    } else if (e.kind === "misconception_detected") {
      const before = graphRef.current.nodes.find((n) => n.id === p.misconception)?.strength;
      say(`Detected: ${pretty(p.misconception)} · strength ${before != null ? before.toFixed(2) + " → " : ""}${Number(p.strength).toFixed(2)}`, "misc");
      pulse(p.misconception, p.topic);
    } else if (e.kind === "attempt") {
      if (p.correct) say(`Correct · mastery ${Number(p.mastery).toFixed(2)}`, "good");
      pulse(p.topic, p.misconception);
    } else if (e.kind === "confidence") {
      say(`Confidence (${p.phase}): ${p.value}/10, self-reported`, "info");
    } else if (e.kind === "session_ended") {
      say("Session ended · tomorrow's plan is ready", "good");
    } else if (e.kind === "safety") {
      say("Safety stop · teacher notified", "info");
    } else if (e.kind === "session_saved") {
      say("Phone call saved to your journal", "good");
    } else if (e.kind === "review_ready" || e.kind === "profile_updated") {
      say(e.kind === "review_ready" ? "Review ready · see your journal" : "Guru updated what it knows about you", "good");
    }
    if (["session_ended", "session_saved", "review_ready", "profile_updated"].includes(e.kind)) setJournalTick((t) => t + 1);
    refresh();
  });

  const live = !!feed && !feed.ended_at;
  useEffect(() => {
    if (!live) return;
    const t = setInterval(() => tick((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, [live]);

  const run = async (what: string, fn: () => Promise<unknown>) => {
    setBusy(what);
    try {
      await fn();
    } catch (e) {
      say((e as Error).message, "info");
    } finally {
      setBusy(null);
    }
  };

  const replay = () => run("replay", async () => {
    setCall(null);
    const r = await api<{ session_id: string }>("demo/replay", { method: "POST", body: { student_id: studentId, delay: 2 } });
    sessionRef.current = r.session_id;
    await load(studentId, r.session_id);
  });
  const reset = () => {
    if (!window.confirm("Reset the demo database to the seeded BEFORE state?")) return;
    run("reset", async () => {
      await api("demo/reset", { method: "POST" });
      setCall(null);
      setActive({});
      await load(studentId);
      say("Demo reset · Rahul is back to his BEFORE state", "info");
    });
  };
  // Phone call via Bolna. If Bolna can't call (trial number not verified, out of credit...), talk in the page instead.
  const startCall = () => run("call", async () => {
    const r = await api<CallResult>("voice/call", { method: "POST", body: { student_id: studentId } });
    setCall(r);
    if (r.provider !== "bolna") setBrowserCall(true);
  });

  // pair each student line with its graded attempt (in order) to show chips in the transcript
  const lineTags = useMemo(() => {
    const tags: Record<number, Feed["attempts"][number]> = {};
    if (!feed) return tags;
    let ai = 0;
    feed.lines.forEach((l, i) => {
      const a = feed.attempts[ai];
      if (l.speaker === "student" && a && l.text.trim() === (a.student_answer || "").trim()) {
        tags[i] = a;
        ai++;
      }
    });
    return tags;
  }, [feed]);

  const lastPoint = progress?.session_points.filter((p) => p.accuracy != null && (p.conf_after ?? p.conf_before) != null).at(-1);
  const gap = lastPoint ? (lastPoint.conf_after ?? lastPoint.conf_before)! / 10 - lastPoint.accuracy! : null;
  const showInsight = insight && Date.now() - insight.ts < 6000;
  const arc = feed?.arc;
  const showArc = feed?.ended_at && arc && arc.mastery_after != null;

  return (
    <div className={`mx-auto max-w-[1600px] px-4 pb-10 md:px-6 ${demo ? "demo-mode" : ""}`}>
      {/* top bar: slim for students; session details + presenter tools only in the advanced view */}
      <div className="liquid sticky top-[5.5rem] z-30 mb-6 rounded-2xl flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5">
        <select aria-label="Student" value={studentId}
          onChange={(e) => (e.target.value === "__new" ? router.push("/start") : setStudentId(e.target.value))}
          className="rounded-full border border-line bg-surface-2 px-3 py-1.5 text-sm font-medium">
          {(students.length ? students : [{ id: RAHUL, first_name: "Rahul" } as Student]).map((s) => (
            <option key={s.id} value={s.id}>{s.first_name}{s.consented === false ? " (no consent)" : ""}</option>
          ))}
          <option value="__new">+ New student</option>
        </select>
        <PillTabs id="view" label="View" size="sm" value={view} onChange={pickView}
          options={[{ value: "simple", label: <><GraduationCap size={14} aria-hidden /> Student</> },
                    { value: "advanced", label: <><Network size={14} aria-hidden /> Advanced · graph</> }]} />
        <AnimatePresence>
          {(live || view === "advanced") && feed && (
            <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
              className="flex items-center gap-2 text-sm">
              <LiveBadge live={live} />
              {feed.topic && <span className="text-muted">{feed.topic}</span>}
              <span className="num text-muted">{clock(feed.started_at, feed.ended_at)}</span>
              <span className="chip border border-line text-muted">{feed.channel === "web" ? "Browser call" : feed.channel === "simulator" ? "Replay" : "Phone call"}</span>
              <Waveform active={live} />
            </motion.div>
          )}
        </AnimatePresence>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {view === "advanced" && (
            <>
              <span className="demo-hide text-xs text-muted" title="Realtime transport">{mode === "stream" ? "● realtime" : mode === "polling" ? "○ polling" : "…"}</span>
              <button className="btn-primary py-1.5" onClick={replay} disabled={!!busy}>
                <Play size={15} aria-hidden /> {busy === "replay" ? "Starting…" : "Replay Rahul session"}
              </button>
              <button className="btn-ghost demo-hide py-1.5" onClick={() => setBrowserCall((b) => !b)} aria-pressed={browserCall}>
                <Mic size={15} aria-hidden /> Talk in browser
              </button>
            </>
          )}
          <button className={`demo-hide py-1.5 ${view === "simple" ? "btn-primary" : "btn-ghost"}`} onClick={startCall} disabled={!!busy}
            title="Guru calls the student's phone (Bolna)">
            <Phone size={15} aria-hidden /> {busy === "call" ? "Calling…" : "Call my phone"}
          </button>
          {view === "advanced" && (
            <>
              <button className="btn-ghost demo-hide py-1.5" onClick={reset} disabled={!!busy} title="Reset demo data">
                <RotateCcw size={15} aria-hidden /> Reset
              </button>
              <button className="btn-ghost py-1.5" onClick={() => setDemo((d) => !d)} aria-pressed={demo}>
                {demo ? <Minimize2 size={15} aria-hidden /> : <Maximize2 size={15} aria-hidden />} Demo mode
              </button>
            </>
          )}
        </div>
      </div>

      {call && <CallBanner call={call} onClose={() => setCall(null)} />}

      {/* audience caption in demo mode */}
      {demo && (
        <div className="mb-4 min-h-[3.5rem] text-center font-serif text-3xl md:text-4xl" aria-live="polite">
          {showInsight ? insight!.text : feed?.topic ? `${feed.first_name} · ${feed.topic}` : "Press Replay to start"}
        </div>
      )}

      <AnimatePresence mode="wait" initial={false}>
      {view === "simple" ? (
        <motion.div key="simple" initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 24 }}
          transition={{ duration: 0.35, ease: [0.2, 0.7, 0.2, 1] }}>
        {error && !loading ? <div className="card"><ErrorState message={error} retry={() => load(studentId)} /></div>
        : !overview ? <div className="mx-auto max-w-6xl space-y-4"><div className="skeleton-shimmer h-28 rounded-card" /><div className="skeleton-shimmer h-[420px] rounded-card" /></div>
        : <SimpleView ov={overview} feed={feed} onActivity={refresh} journalTick={journalTick} />}
        </motion.div>
      ) : (<motion.div key="advanced" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}
          transition={{ duration: 0.35, ease: [0.2, 0.7, 0.2, 1] }}>
      {browserCall && (
        <div className="mb-4">
          <CallPanel studentId={studentId} name={overview?.first_name ?? "the student"} onActivity={refresh} />
        </div>
      )}

      {showArc && <BeforeAfter arc={arc!} name={feed!.first_name} />}

      {error && !loading ? (
        <div className="card"><ErrorState message={error} retry={() => load(studentId)} /></div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-12">
          {/* transcript */}
          <Panel title="Conversation" className="lg:col-span-3"
            right={feed && <span className="num text-xs text-muted">{feed.stats.correct_n}/{feed.stats.attempts_n} correct</span>}>
            {loading ? (
              <div className="space-y-3">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10" />)}</div>
            ) : !feed || !feed.lines.length ? (
              <EmptyState title="No session yet" hint="Press “Replay Rahul session” to run a scripted call through the real tutor, or start a call." />
            ) : (
              <ChatTranscript lines={feed.lines} studentName={feed.first_name} maxHeight={560}
                renderTag={(i) => lineTags[i] ? (
                  <div className="mt-1">
                    {lineTags[i].misconception_id ? (
                      <MisconceptionChip id={lineTags[i].misconception_id!} name={lineTags[i].misconception_name} />
                    ) : lineTags[i].correct ? (
                      <span className="chip border border-m-high/40 bg-m-high/10 text-m-high"><Check size={11} aria-hidden /> correct</span>
                    ) : (
                      <span className="chip border border-line text-muted">not yet · hint {lineTags[i].hint_level}</span>
                    )}
                  </div>
                ) : null} />
            )}
          </Panel>

          {/* graph */}
          <section className="card relative overflow-hidden lg:col-span-6">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,154,61,.07),transparent_65%)]" aria-hidden />
            <div className="flex items-center justify-between px-5 pt-4">
              <h2 className="label">Knowledge graph</h2>
              <div className="demo-hide"><GraphLegend /></div>
            </div>
            {loading ? <Skeleton className="m-5 h-[520px]" /> : graph.nodes.length ? (
              <KnowledgeGraph data={graph} active={active} height={demo ? 600 : 540} />
            ) : (
              <EmptyState title="No memory yet for this student" hint="The graph fills in as the student answers." />
            )}
            <AnimatePresence>
              {showInsight && !demo && (
                <motion.div key={insight!.ts} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className={`absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-full border px-4 py-2 text-sm shadow-glow backdrop-blur ${
                    insight!.tone === "misc" ? "border-misc/50 bg-misc/15 text-misc" : insight!.tone === "good" ? "border-m-high/40 bg-m-high/10 text-m-high" : "border-line bg-surface-2/90"}`}
                  role="status">
                  <Sparkles size={14} aria-hidden /> {insight!.text}
                </motion.div>
              )}
            </AnimatePresence>
          </section>

          {/* right column */}
          <div className="space-y-4 lg:col-span-3">
            <Panel title="Confidence vs performance" className="demo-hide">
              <ConfidenceAccuracyChart points={progress?.session_points ?? []} />
              {gap != null && (
                <p className="mt-2 text-xs text-muted">
                  Calibration gap <span className="num text-text">{gap > 0 ? "+" : ""}{gap.toFixed(2)}</span>{" "}
                  · {Math.abs(gap) < 0.1 ? "well calibrated" : gap > 0 ? "more confident than accurate" : "more accurate than confident"}
                </p>
              )}
              <p className="mt-1 text-[11px] text-muted">Confidence is self-reported (1–10). Guru never infers feelings from voice.</p>
            </Panel>
            <Panel title="Mastery & skills">
              {overview?.topics.length || progress?.skills?.length ? (
                <div className="space-y-3">
                  {overview?.topics.map((t) => <MasteryBar key={t.topic_id} label={t.name} value={t.p_known} />)}
                  {/* coaching calls: AI-judged skill scores (0-10), latest, with change over 30 days */}
                  {progress?.skills?.map((k) => (
                    <MasteryBar key={k.skill} value={k.score / 10} outOf10
                      label={`${k.label}${Math.abs(k.trend) >= 0.5 ? (k.trend > 0 ? " ↑" : " ↓") : ""}`} />
                  ))}
                  {progress?.self_confidence && (
                    <p className="text-xs text-muted">Self-reported confidence <span className="num text-sky">{progress.self_confidence.value}/10</span></p>
                  )}
                </div>
              ) : <EmptyState title="No topics practised yet" />}
            </Panel>
            {!!progress?.next_steps?.length && (
              <Panel title="Next best steps" className="demo-hide">
                <ol className="space-y-3 text-sm">
                  {progress.next_steps.map((n, i) => (
                    <li key={i}>
                      <div className="font-medium">{i + 1}. {n.title}</div>
                      <p className="mt-0.5 text-xs text-muted">{n.why}</p>
                      <span className="mt-1 inline-block rounded-full border border-line px-2 py-0.5 text-[10px] text-accent">{n.principle}</span>
                    </li>
                  ))}
                </ol>
              </Panel>
            )}
            {!!overview?.topics.length && (
              <Panel title="Next review" className="demo-hide">
                <ul className="space-y-1.5 text-sm">
                  {[...overview.topics].sort((a, b) => a.p_now - b.p_now).slice(0, 4).map((t) => (
                    <li key={t.topic_id} className="flex justify-between gap-2">
                      <span className="truncate">{t.name}</span>
                      <span className="num text-muted">{t.p_now < 0.7 ? "due now" : `in ${dec(t.next_review_days, 1)} d`}</span>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}
          </div>
        </div>
      )}

      {/* why-this-question ribbon */}
      {overview?.weak_prerequisite && (
        <div className="card mt-4 flex flex-wrap items-center gap-2 px-5 py-3 text-sm">
          <span className="label">Why this question?</span>
          <span>
            Weakest prerequisite for {overview.topics.find((t) => t.topic_id === overview.focus_topic)?.name ?? pretty(overview.focus_topic)} is{" "}
            <span className="text-accent">{overview.weak_prerequisite.name}</span>{" "}
            <span className="num text-muted">(mastery {overview.weak_prerequisite.mastery.toFixed(2)})</span>, so Guru checks it first and plans a recap.
          </span>
        </div>
      )}
      </motion.div>)}
      </AnimatePresence>
    </div>
  );
}

function BeforeAfter({ arc, name }: { arc: NonNullable<Feed["arc"]>; name: string }) {
  const cell = (label: string, a: number | null | undefined, b: number | null | undefined, fmt: (v: number) => string, goodUp: boolean) => {
    const better = a != null && b != null && (goodUp ? b > a : b < a);
    return (
      <div className="flex-1 px-4 py-3">
        <div className="label mb-1">{label}</div>
        <div className="num text-2xl">
          {a != null ? fmt(a) : "—"} <span className="text-muted">→</span>{" "}
          <span className={better ? "text-m-high" : ""}>{b != null ? fmt(b) : "—"}</span>
        </div>
      </div>
    );
  };
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card mb-4 flex flex-col divide-y divide-line shadow-glow md:flex-row md:divide-x md:divide-y-0">
      <div className="flex-1 px-4 py-3">
        <div className="label mb-1">After this call</div>
        <div className="font-serif text-2xl">
          {(arc.mastery_after ?? 0) > (arc.mastery_before ?? 1) || (arc.mis_after ?? 1) < (arc.mis_before ?? 0)
            ? `${name} improved.` : `${name} practised. Still building.`}
        </div>
      </div>
      {cell("Mastery", arc.mastery_before, arc.mastery_after, (v) => v.toFixed(2), true)}
      {cell(arc.misconception_name ? `“${arc.misconception_name}”` : "Misconception", arc.mis_before, arc.mis_after, (v) => v.toFixed(2), false)}
      {cell("Confidence (self-reported)", arc.conf_before, arc.conf_after, (v) => `${v}/10`, true)}
    </motion.div>
  );
}

function CallBanner({ call, onClose }: { call: CallResult; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="card mb-4 flex flex-wrap items-center gap-3 px-5 py-3 text-sm" role="status">
      {call.provider === "bolna" ? (
        <span>📞 Bolna is calling the student now <span className="num text-muted">({call.execution_id})</span>. The console updates as they answer.</span>
      ) : (
        <>
          <span>
            🎙 Sarvam web call link ready{call.fallback_reason ? <span className="text-muted"> (Bolna: {call.fallback_reason})</span> : null}. Send it to the student:
          </span>
          <code className="num max-w-full truncate rounded bg-surface-2 px-2 py-1 text-xs">{call.url}</code>
          <button className="btn-ghost py-1" onClick={() => { navigator.clipboard.writeText(call.url!); setCopied(true); }}>
            {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : "Copy"}
          </button>
          <a className="btn-ghost py-1" href={call.url} target="_blank" rel="noreferrer">Open</a>
        </>
      )}
      <button className="ml-auto text-muted hover:text-text" onClick={onClose} aria-label="Dismiss">✕</button>
    </div>
  );
}
