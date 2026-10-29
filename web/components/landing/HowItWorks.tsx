"use client";
// Scroll-driven "how it works": the section is tall; a sticky preview swaps as the reader scrolls through 4 steps.
// On small screens it falls back to a simple stacked list (no sticky scroll-jacking on phones).
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "framer-motion";
import { Flag, Mic, Network, TrendingUp } from "lucide-react";
import { useRef, useState } from "react";
import VoiceOrb from "@/components/VoiceOrb";

const STEPS = [
  { icon: Flag, title: "Set a goal", body: "“Pass my maths test”, “speak English confidently”, “become an AI engineer”. Guru turns it into a 4-week plan." },
  { icon: Mic, title: "Talk", body: "Guru phones the student, or they talk in the browser — Hindi, English or Hinglish. Short turns, one question at a time." },
  { icon: Network, title: "Remember", body: "Every mistake, strength and improvement point goes into a memory graph — with the call it came from." },
  { icon: TrendingUp, title: "Improve", body: "Tomorrow's practice targets what's still weak. Progress shows by day, week and month — measured, not guessed." },
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
      <div className="text-xs uppercase tracking-wider text-muted">Your goal</div>
      <div className="font-serif text-3xl">Become an AI engineer</div>
      <div className="grid grid-cols-2 gap-3">
        {["Python basics", "Data & patterns", "Your first model", "Mini project"].map((w, i) => (
          <motion.div key={w} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.08 }}
            className={`rounded-input border px-3 py-2.5 text-sm ${i === 0 ? "border-accent bg-accent/10" : "border-line"}`}>
            <div className="text-[11px] text-muted">Week {i + 1}{i === 0 ? " · now" : ""}</div>{w}
          </motion.div>
        ))}
      </div>
    </div>
  );
  if (step === 1) return (
    <div className="grid items-center gap-6 sm:grid-cols-[auto_1fr]">
      <div className="mx-auto"><VoiceOrb state="speaking" level={0.35} size={150} /></div>
      <div className="space-y-2.5">
        <Bubble who="guru">Namaste Rahul! Aaj kis language mein baat karein?</Bubble>
        <Bubble who="me" delay={0.25}>Hinglish chalega.</Bubble>
        <Bubble who="guru" delay={0.5}>Badhiya! x + 5 = 12, x kya hoga?</Bubble>
      </div>
    </div>
  );
  if (step === 2) return (
    <svg viewBox="0 0 320 220" className="w-full" role="img" aria-label="Memory graph: a misconception linked to a topic">
      {[[160, 110, 70, 50], [160, 110, 255, 60], [160, 110, 245, 175], [160, 110, 80, 175], [70, 50, 80, 175]].map(([a, b, c, d], i) => (
        <motion.line key={i} x1={a} y1={b} x2={c} y2={d} stroke="var(--muted)" strokeOpacity={0.45} strokeDasharray={i === 4 ? "4 4" : undefined}
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: i * 0.1, duration: 0.6 }} />
      ))}
      <motion.circle cx={160} cy={110} r={13} fill="var(--bg)" stroke="var(--text)" strokeWidth={2.5} initial={{ scale: 0 }} animate={{ scale: 1 }} />
      <circle cx={70} cy={50} r={11} fill="#E5484D" /><circle cx={255} cy={60} r={9} fill="#3DD68C" /><circle cx={80} cy={175} r={10} fill="#F5A524" />
      <motion.rect x={233} y={163} width={24} height={24} rx={3} fill="#B794F6" transform="rotate(45 245 175)"
        animate={{ opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.8, repeat: Infinity }} />
      <text x={160} y={140} fill="var(--text)" fontSize={11} textAnchor="middle">Rahul</text>
      <text x={70} y={30} fill="var(--muted)" fontSize={10} textAnchor="middle">Linear equations</text>
      <text x={245} y={208} fill="#B794F6" fontSize={10} textAnchor="middle">adds instead of inverse</text>
    </svg>
  );
  return (
    <div>
      <div className="mb-3 flex justify-between text-xs text-muted"><span>English speaking · grammar</span><span className="text-m-high">improving</span></div>
      <div className="flex h-40 items-end gap-2.5">
        {[0.35, 0.42, 0.48, 0.57, 0.66, 0.72].map((v, i) => (
          <motion.div key={i} className="flex-1 origin-bottom rounded-t-md" style={{ height: `${v * 100}%`, background: "linear-gradient(to top, rgba(61,214,140,.2), #3DD68C)" }}
            initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ delay: i * 0.07, duration: 0.5 }} />
        ))}
      </div>
      <div className="mt-3 grid grid-cols-6 text-center text-[11px] text-muted">{["D1", "D2", "D3", "W2", "W3", "M1"].map((d) => <span key={d}>{d}</span>)}</div>
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
              <div className="label">How it works</div>
              <h2 className="mt-3 font-serif text-5xl leading-tight">From one call to real progress.</h2>
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
              <div className="mb-6 flex items-center gap-2 text-xs text-muted">
                <span className="h-2 w-2 rounded-full bg-m-low" /><span className="h-2 w-2 rounded-full bg-m-mid" /><span className="h-2 w-2 rounded-full bg-m-high" />
                <span className="ml-2">guru-line · {STEPS[step].title.toLowerCase()}</span>
              </div>
              <AnimatePresence mode="wait">
                <motion.div key={step} className="relative min-h-[260px]" initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} exit={{ opacity: 0, y: -20, filter: "blur(6px)" }} transition={{ duration: 0.4 }}>
                  <Preview step={step} />
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>

      {/* mobile / tablet: stacked */}
      <div className="mx-auto max-w-2xl space-y-10 px-5 py-20 lg:hidden">
        <h2 className="font-serif text-4xl leading-tight">From one call to real progress.</h2>
        {STEPS.map(({ title, body }, i) => (
          <motion.div key={title} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.3 }}>
            <div className="num text-accent">0{i + 1}</div>
            <div className="mt-1 font-serif text-2xl">{title}</div>
            <p className="mt-2 text-muted">{body}</p>
            <div className="card mt-4 p-5"><Preview step={i} /></div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
