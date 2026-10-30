"use client";
// Scroll-driven "how it works": the section is tall; a sticky preview swaps as the reader scrolls through 4 steps.
// On small screens it falls back to a simple stacked list (no sticky scroll-jacking on phones).
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "framer-motion";
import { Flag, Mic, Network, TrendingUp } from "lucide-react";
import { useRef, useState } from "react";
import VoiceOrb from "@/components/VoiceOrb";

const STEPS = [
  {
    icon: Flag,
    title: "Give a missed call & share your interest",
    body: "Students call from any mobile or keypad phone and share their education background, career interest, and family budget constraints — with no class limit.",
  },
  {
    icon: Mic,
    title: "Speak naturally in Hindi or English",
    body: "Guruji speaks clearly over the phone in Hindi or English, asking one simple question at a time to understand the student's real goals.",
  },
  {
    icon: Network,
    title: "Live government research & memory graph",
    body: "As the student speaks, Guruji researches official government portals live (NCS, Skill India, DGT, AICTE, SWAYAM, NSP) and builds a persistent Student Memory Graph.",
  },
  {
    icon: TrendingUp,
    title: "Follow a verified 4-week action plan",
    body: "Students receive a clear checklist of eligibility criteria, required documents (Aadhaar, Income & Domicile certificates), official websites, and local CSC steps.",
  },
];

function Bubble({ who, children, delay = 0 }: { who: "guru" | "me"; children: React.ReactNode; delay?: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, duration: 0.35 }}
      className={`flex ${who === "me" ? "justify-end" : ""}`}>
      <div className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${who === "me" ? "rounded-br-md bg-accent/15 text-accent-2" : "rounded-bl-md bg-surface-2"}`}>{children}</div>
    </motion.div>
  );
}

function Preview({ step }: { step: number }) {
  if (step === 0) return (
    <div className="space-y-4">
      <div className="text-xs uppercase tracking-wider text-muted">Step 01 · Missed-Call Intake & Live Research</div>
      <div className="font-serif text-3xl">Any Qualification · Any Career Interest</div>
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Week 1 · now", val: "Check official eligibility" },
          { label: "Week 2", val: "Aadhaar & Income cert" },
          { label: "Week 3", val: "Apply at local CSC" },
          { label: "Week 4", val: "Interview intro practice" },
        ].map((w, i) => (
          <motion.div key={w.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.08 }}
            className={`rounded-input border px-3 py-2.5 text-sm ${i === 0 ? "border-accent bg-accent/10" : "border-line"}`}>
            <div className="text-[11px] text-muted">{w.label}</div>{w.val}
          </motion.div>
        ))}
      </div>
    </div>
  );
  if (step === 1) return (
    <div className="grid items-center gap-6 sm:grid-cols-[auto_1fr]">
      <div className="mx-auto"><VoiceOrb state="speaking" level={0.35} size={150} /></div>
      <div className="space-y-2.5">
        <Bubble who="guru">Hello Rahul! What field or skill would you like to build a career in?</Bubble>
        <Bubble who="me" delay={0.25}>I am interested in electrical and solar work, and I need a low-fee government course.</Bubble>
        <Bubble who="guru" delay={0.5}>Verified on dgt.gov.in & scholarships.gov.in: Government ITI Electrician (₹1k–₹5k/yr) and NSP Scholarship match your profile.</Bubble>
      </div>
    </div>
  );
  if (step === 2) return (
    <svg viewBox="0 0 320 220" className="w-full" role="img" aria-label="Memory graph: verified career pathways linked to student">
      {[[160, 110, 70, 50], [160, 110, 255, 60], [160, 110, 245, 175], [160, 110, 80, 175], [70, 50, 80, 175]].map(([a, b, c, d], i) => (
        <motion.line key={i} x1={a} y1={b} x2={c} y2={d} stroke="var(--muted)" strokeOpacity={0.45} strokeDasharray={i === 4 ? "4 4" : undefined}
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: i * 0.1, duration: 0.6 }} />
      ))}
      <motion.circle cx={160} cy={110} r={13} fill="var(--bg)" stroke="var(--text)" strokeWidth={2.5} initial={{ scale: 0 }} animate={{ scale: 1 }} />
      <circle cx={70} cy={50} r={11} fill="#E5484D" /><circle cx={255} cy={60} r={9} fill="#3DD68C" /><circle cx={80} cy={175} r={10} fill="#F5A524" />
      <motion.rect x={233} y={163} width={24} height={24} rx={3} fill="#B794F6" transform="rotate(45 245 175)"
        animate={{ opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.8, repeat: Infinity }} />
      <text x={160} y={140} fill="var(--text)" fontSize={11} textAnchor="middle">Rahul (Caller)</text>
      <text x={70} y={30} fill="var(--muted)" fontSize={10} textAnchor="middle">Govt ITI (dgt.gov.in)</text>
      <text x={245} y={208} fill="#B794F6" fontSize={10} textAnchor="middle">NSP Scholarship DBT</text>
    </svg>
  );
  return (
    <div>
      <div className="mb-3 flex justify-between text-xs text-muted"><span>Career clarity & interview confidence</span><span className="text-m-high">verified plan</span></div>
      <div className="flex h-40 items-end gap-2.5">
        {[0.35, 0.42, 0.48, 0.57, 0.66, 0.72].map((v, i) => (
          <motion.div key={i} className="flex-1 origin-bottom rounded-t-md" style={{ height: `${v * 100}%`, background: "linear-gradient(to top, rgba(61,214,140,.2), #3DD68C)" }}
            initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ delay: i * 0.07, duration: 0.5 }} />
        ))}
      </div>
      <div className="mt-3 grid grid-cols-6 text-center text-[11px] text-muted">{["C1", "C2", "W1", "W2", "W3", "W4"].map((d) => <span key={d}>{d}</span>)}</div>
    </div>
  );
}

export default function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState(0);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  useMotionValueEvent(scrollYProgress, "change", (p) => setStep(Math.min(STEPS.length - 1, Math.max(0, Math.floor(p * STEPS.length)))));

  return (
    <section id="how" className="scroll-mt-16 border-y border-line" aria-label="How it works">
      {/* desktop: sticky scrollytelling */}
      <div ref={ref} className="relative hidden lg:block" style={{ height: `${STEPS.length * 75}vh` }}>
        <div className="sticky top-0 flex h-screen items-center">
          <div className="mx-auto grid w-full max-w-7xl grid-cols-2 items-center gap-16 px-8">
            <div>
              <div className="label">How Guruji works</div>
              <h2 className="mt-3 font-serif text-5xl leading-tight">From a missed call to a verified career plan.</h2>
              <p className="mt-4 text-lg text-muted">Scroll through the steps below to see how Guruji guides students over the phone and builds persistent memory.</p>
              <ol className="mt-10 space-y-2">
                {STEPS.map(({ icon: Icon, title, body }, i) => (
                  <li key={title} className={`relative rounded-card border p-5 transition-colors duration-500 ${i === step ? "border-line bg-surface/70" : "border-transparent"}`}>
                    {i === step && <motion.span layoutId="step-bar" className="absolute bottom-4 left-0 top-4 w-[3px] rounded-full bg-accent" />}
                    <div className={`flex items-center gap-3 transition-opacity duration-500 ${i === step ? "opacity-100" : "opacity-40"}`}>
                      <span className="num text-sm text-accent">0{i + 1}</span>
                      <Icon size={18} className="text-accent" aria-hidden />
                      <span className="font-serif text-2xl">{title}</span>
                    </div>
                    <AnimatePresence initial={false}>
                      {i === step && (
                        <motion.p initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden pl-[4.6rem] pt-2 text-muted">{body}</motion.p>
                      )}
                    </AnimatePresence>
                  </li>
                ))}
              </ol>
            </div>
            <div className="card border-gradient relative overflow-hidden p-8 shadow-glow">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,154,61,.10),transparent_60%)]" aria-hidden />
              <div className="mb-6 flex items-center justify-between text-xs text-muted">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-m-low" /><span className="h-2 w-2 rounded-full bg-m-mid" /><span className="h-2 w-2 rounded-full bg-m-high" />
                  <span className="ml-2">guruji · step 0{step + 1}</span>
                </div>
              </div>
              <AnimatePresence mode="wait">
                <motion.div key={step} className="relative min-h-[260px]" initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} exit={{ opacity: 0, y: -20, filter: "blur(6px)" }} transition={{ duration: 0.4 }}>
                  <Preview step={step} />
                </motion.div>
              </AnimatePresence>
              <div className="mt-6 flex items-center justify-between border-t border-line/60 pt-3 text-xs text-muted">
                <span>MVP Flow: Missed Call → Student Memory → Career Guidance → Next Step</span>
                <span className="num font-medium text-accent">0{step + 1} / 04</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* mobile / tablet: stacked */}
      <div className="mx-auto max-w-2xl space-y-10 px-5 py-20 lg:hidden">
        <div className="label">How Guruji works</div>
        <h2 className="font-serif text-4xl leading-tight">From a missed call to a verified career plan.</h2>
        <p className="mt-2 text-muted">Scroll through the steps below to see how Guruji guides students over the phone and builds persistent memory.</p>
        {STEPS.map(({ title, body }, i) => (
          <motion.div key={title} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.3 }}>
            <div className="num text-accent">0{i + 1}</div>
            <div className="mt-1 font-serif text-2xl">{title}</div>
            <p className="mt-2 text-muted">{body}</p>
            <div className="card mt-4 p-5">
              <Preview step={i} />
              <div className="mt-4 flex items-center justify-between border-t border-line/60 pt-3 text-xs text-muted">
                <span>MVP Flow: Missed Call → Student Memory → Career Guidance → Next Step</span>
                <span className="num font-medium text-accent">0{i + 1} / 04</span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
