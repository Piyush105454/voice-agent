"use client";
// Student home: the voice call is the hero; learning cards (fix, last call, goals, progress, topics) below.
// No graph, no decimals. Stars + plain words. Age-aware: Class 7 and below see no numbers at all.
import { Calculator, CalendarDays, Languages, Lightbulb, Sparkles, Star } from "lucide-react";
import { useState } from "react";
import CallPanel from "@/components/CallPanel";
import ChatTranscript from "@/components/ChatTranscript";
import GoalsPanel, { MODE_LABEL } from "@/components/GoalsPanel";
import JournalPanel from "@/components/JournalPanel";
import { CountUp, PillTabs, Reveal, Stagger, StaggerItem, WordReveal } from "@/components/motion";
import ProgressPanel from "@/components/ProgressPanel";
import type { Feed, Mode, Overview } from "@/lib/types";

const MODES: { id: Mode; icon: typeof Star; hint: string }[] = [
  { id: "coach", icon: Sparkles, hint: "Talk about anything you want to improve: studies, career, work, skills or confidence. Guru remembers your journey." },
  { id: "maths", icon: Calculator, hint: "Maths drills: Guru finds why an answer is wrong and fixes it with hints." },
  { id: "english", icon: Languages, hint: "Speak freely; Guru gently fixes one mistake at a time." },
];

const TIPS: Record<string, { tip: string; example: string }> = {
  adds_instead_of_inverse: { tip: "When a number jumps over the = sign, it does the opposite. +5 becomes −5.", example: "x + 5 = 12  →  x = 12 − 5 = 7" },
  sign_not_flipped: { tip: "Moving a number across = flips its sign. −3 becomes +3.", example: "x − 3 = 7  →  x = 7 + 3 = 10" },
  coefficient_ignored: { tip: "3x means 3 times x. Divide to get x alone.", example: "3x = 12  →  x = 12 ÷ 3 = 4" },
  neg_number_confusion: { tip: "Think of a number line: minus means walk left, plus means walk right.", example: "−2 − 3: start at −2, walk 3 left → −5" },
  distributes_partially: { tip: "The number outside the bracket multiplies everything inside.", example: "2(x + 3) = 2x + 6" },
  equals_as_answer: { tip: "= means both sides are the same, not “the answer comes next”.", example: "3 + 4 = ___ + 2  →  5" },
};

const level = (p: number | null | undefined) =>
  p == null ? { stars: 0, word: "Not started", icon: "○" }
  : p < 0.4 ? { stars: Math.max(1, Math.round(p * 5)), word: "Let's practise", icon: "🌱" }
  : p < 0.7 ? { stars: Math.round(p * 5), word: "Getting there", icon: "🌿" }
  : { stars: Math.max(4, Math.round(p * 5)), word: "Strong", icon: "🌳" };

function Stars({ n, size = 18 }: { n: number; size?: number }) {
  return (
    <span className="inline-flex gap-0.5" aria-label={`${n} of 5 stars`} role="img">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star key={i} size={size} strokeWidth={1.5} className={i <= n ? "fill-accent text-accent" : "text-line"} aria-hidden />
      ))}
    </span>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-card border border-line bg-surface/60 px-4 py-3 backdrop-blur">
      <div className="text-2xl"><CountUp to={value} /></div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

export default function SimpleView({ ov, feed, onActivity, journalTick = 0 }: {
  ov: Overview; feed: Feed | null; onActivity: () => void; journalTick?: number;
}) {
  const junior = (ov.grade ?? 8) <= 7;
  const [mode, setMode] = useState<Mode>("coach");
  const [tick, setTick] = useState(0); // refreshes progress after a call
  const activity = () => { setTick((t) => t + 1); onActivity(); };
  const review = feed?.ended_at && feed.mode && feed.mode !== "maths" ? feed.review : null;
  const fix = ov.misconceptions.find((m) => m.strength > 0.3);
  const tip = fix ? TIPS[fix.id] : null;
  const arc = feed?.ended_at ? feed.arc : null;
  const before = level(arc?.mastery_before), after = level(arc?.mastery_after);
  const better = arc && arc.mastery_before != null && arc.mastery_after != null && arc.mastery_after > arc.mastery_before;
  const activeGoals = (ov.goals ?? []).filter((g) => g.status === "active").length;
  const modeInfo = MODES.find((m) => m.id === mode)!;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* greeting */}
      <div className="flex flex-wrap items-end justify-between gap-6 pt-2">
        <div>
          <h1 className="font-serif text-4xl md:text-6xl"><WordReveal text={`Hi ${ov.first_name} 👋`} /></h1>
          <Reveal delay={0.25}><p className="mt-2 max-w-xl text-lg text-muted">{ov.sessions.length
            ? "Let's practise a little today. Guru remembers where you got stuck last time."
            : "Welcome! Press Start call and tell Guru what you want to get better at."}</p></Reveal>
        </div>
        <Reveal delay={0.35} className="grid grid-cols-3 gap-3">
          <Stat value={ov.sessions.length} label="calls so far" />
          <Stat value={activeGoals} label={activeGoals === 1 ? "active goal" : "active goals"} />
          <Stat value={ov.topics.length} label="topics practised" />
        </Reveal>
      </div>

      {/* voice call: the hero */}
      <Reveal delay={0.15}>
        <CallPanel studentId={ov.id} name={ov.first_name} big mode={mode} onActivity={activity}
          toolbar={
            <div className="flex flex-col items-center gap-2">
              <PillTabs id="mode" label="What do you want to practise?" value={mode} onChange={setMode}
                options={MODES.map(({ id, icon: Icon }) => ({ value: id, label: <><Icon size={15} aria-hidden /> {MODE_LABEL[id]}</> }))} />
              <p className="text-xs text-muted">{modeInfo.hint}</p>
            </div>
          } />
      </Reveal>

      {/* phone calls (and finished calls) as a chat. A browser call in progress already shows its chat above. */}
      {feed && feed.lines.length > 0 && !(feed.channel === "web" && !feed.ended_at) && (
        <Reveal>
          <section className="card card-hover p-6" aria-label="Conversation">
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
              <div className="font-medium">
                {!feed.ended_at ? <><span className="mr-1.5 inline-block h-2 w-2 animate-livepulse rounded-full bg-accent" aria-hidden />Live phone conversation</> : "Your last conversation"}
              </div>
              <span className="text-sm text-muted">
                {feed.channel === "phone" ? "Phone call" : feed.channel === "web" ? "Browser call" : "Practice replay"}
                {feed.mode && feed.mode !== "open" ? ` · ${MODE_LABEL[feed.mode]}` : ""}
                {" · "}{new Date(feed.started_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
              </span>
            </div>
            <ChatTranscript lines={feed.lines} studentName={feed.first_name} big maxHeight={380} />
          </section>
        </Reveal>
      )}

      {/* bento: what to fix + how the last call went */}
      <Stagger className="grid gap-5 md:grid-cols-2">
        {tip && fix && (
          <StaggerItem className="h-full">
            <section className="card card-hover h-full p-6">
              <div className="flex items-center gap-2 text-accent"><Lightbulb size={18} aria-hidden /><span className="font-medium">One thing to fix</span></div>
              <p className="mt-3 text-xl leading-snug">{tip.tip}</p>
              <p className="num mt-4 rounded-input border border-line bg-surface-2 px-4 py-3 text-lg">{tip.example}</p>
              <p className="mt-3 text-sm text-muted">Guru noticed this {fix.evidence_n} time{fix.evidence_n === 1 ? "" : "s"}. Each right answer makes it fade.</p>
            </section>
          </StaggerItem>
        )}

        {review && (
          <StaggerItem className="h-full">
            <section className="card card-hover h-full p-6">
              <div className="font-medium text-accent">After your last {MODE_LABEL[feed!.mode!]} call</div>
              {review.summary && <p className="mt-3 text-lg leading-snug">{review.summary}</p>}
              {review.strengths?.length > 0 && <p className="mt-3 text-sm text-m-high">✓ {review.strengths[0]}</p>}
              {review.improvements?.length > 0 && (
                <ul className="mt-3 space-y-1.5">{review.improvements.map((x, i) => <li key={i}>→ {x}</li>)}</ul>
              )}
            </section>
          </StaggerItem>
        )}
        {feed?.ended_at && !review && feed.mode && feed.mode !== "maths" && feed.mode !== "open" && (
          <StaggerItem>
            <section className="card h-full p-6"><div className="font-medium text-accent">After your last call</div>
              <div className="mt-4 space-y-2"><div className="skeleton-shimmer h-4 w-3/4 rounded" /><div className="skeleton-shimmer h-4 w-1/2 rounded" /></div>
              <p className="mt-3 text-sm text-muted">Guru is writing your review…</p></section>
          </StaggerItem>
        )}

        {(!feed?.mode || feed.mode === "maths") && arc && arc.mastery_after != null && (
          <StaggerItem className="h-full">
            <section className="card card-hover h-full p-6">
              <div className="font-medium text-accent">After your last call</div>
              <div className="mt-4 space-y-4 text-lg">
                <div>
                  <div className="text-muted">{feed?.topic}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-3">
                    <Stars n={before.stars} /> <span className="text-muted">→</span> <Stars n={after.stars} />
                  </div>
                  <div className="mt-1 text-sm">{better ? "You got better! 🎉" : "Keep going, you're building it."}</div>
                </div>
                {arc.conf_before != null && arc.conf_after != null && (
                  <div>
                    <div className="text-muted">How sure you felt</div>
                    <div className="num mt-1 text-2xl">{arc.conf_before} → <span className={arc.conf_after > arc.conf_before ? "text-m-high" : ""}>{arc.conf_after}</span> <span className="text-sm text-muted">out of 10</span></div>
                  </div>
                )}
              </div>
            </section>
          </StaggerItem>
        )}
      </Stagger>

      <Reveal><GoalsPanel studentId={ov.id} goals={ov.goals ?? []} onChange={onActivity} /></Reveal>
      <Reveal><JournalPanel studentId={ov.id} refreshKey={tick + journalTick} /></Reveal>
      <Reveal><ProgressPanel studentId={ov.id} refreshKey={tick + journalTick} /></Reveal>

      <Reveal>
        <section className="card p-6">
          <div className="mb-4 font-medium">Your maths topics</div>
          {ov.topics.length ? (
            <Stagger className="grid gap-3 sm:grid-cols-2">
              {ov.topics.map((t) => {
                const l = level(t.p_known);
                return (
                  <StaggerItem key={t.topic_id}>
                    <div className="card-hover flex items-center justify-between gap-3 rounded-input border border-line px-4 py-3">
                      <div>
                        <div className="text-lg">{t.name}</div>
                        <div className="text-sm text-muted">{l.icon} {l.word}{!junior && ` · ${Math.round(t.p_known * 100)}%`}</div>
                      </div>
                      <Stars n={l.stars} />
                    </div>
                  </StaggerItem>
                );
              })}
            </Stagger>
          ) : <p className="text-muted">Start a call and your topics will appear here.</p>}
        </section>
      </Reveal>

      {feed?.plan && feed.plan.length > 0 && (
        <Reveal>
          <section className="card p-6">
            <div className="mb-4 flex items-center gap-2 font-medium"><CalendarDays size={18} className="text-accent" aria-hidden /> Your next practice</div>
            <ol className="grid gap-3 sm:grid-cols-3">
              {[1, 2, 3].map((d) => {
                const items = feed.plan.filter((p) => p.day === d);
                return items.length ? (
                  <li key={d} className="card-hover rounded-input border border-line px-4 py-3">
                    <div className="text-sm text-muted">{d === 1 ? "Tomorrow" : `Day ${d}`}</div>
                    {items.map((it, i) => <div key={i} className="mt-1">{it.n_questions} questions · {it.topic}</div>)}
                  </li>
                ) : null;
              })}
            </ol>
          </section>
        </Reveal>
      )}
    </div>
  );
}
