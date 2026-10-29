"use client";
import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, Calculator, Check, Compass, Languages, Phone } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRef } from "react";
import HowItWorks from "@/components/landing/HowItWorks";
import { ScrollProgress, WordReveal } from "@/components/motion";

// the call animation is client-only; a soft glow holds its space during the first paint
const HeroCall = dynamic(() => import("@/components/landing/HeroCall"), {
  ssr: false,
  loading: () => <div className="h-[600px] w-full bg-[radial-gradient(circle_at_center,rgba(255,154,61,.16),transparent_60%)]" />,
});

// the doubts a parent or student has in the first five seconds, answered up front
const ASSURANCES = ["No app needed", "Works on any phone", "Hindi · English · Hinglish", "Parents get a summary"];

const ease = [0.2, 0.7, 0.2, 1] as const;
const reveal = { initial: { opacity: 0, y: 12 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true }, transition: { duration: 0.45, ease } };

const MODES = [
  { icon: Calculator, title: "Maths", line: "Finds why an answer is wrong, the misconception, and fixes it with hints, never the answer first.", tag: "x + 5 = 12 → 17 ✗ → “+5 jumps over = and becomes −5”" },
  { icon: Languages, title: "English speaking", line: "Real conversation practice. Gentle grammar fixes, new words, and confidence you report yourself.", tag: "“I goes to school” → “I go to school”" },
  { icon: Compass, title: "Any topic", line: "Tell Guru your aim. It builds a plan, teaches in short turns, and quizzes you to check.", tag: "Goal: AI engineer → Week 1: Python basics" },
];

const FACTS = [
  ["~1.4 s", "to understand what you said"],
  ["3", "ways to practise"],
  ["हिं · EN", "Hindi, English or Hinglish"],
  ["Day → Month", "progress you can see"],
];

const BARS = [
  { label: "Day 1", v: 0.3 }, { label: "Day 2", v: 0.42 }, { label: "Day 3", v: 0.51 }, { label: "Week 2", v: 0.63 }, { label: "Month 1", v: 0.78 },
];

export default function Landing() {
  const phone = process.env.NEXT_PUBLIC_DEMO_PHONE;
  const hero = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: hero, offset: ["start start", "end start"] });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, 140]);
  const heroFade = useTransform(scrollYProgress, [0, 0.8], [1, 0]);
  const textY = useTransform(scrollYProgress, [0, 1], [0, -40]);

  return (
    <div className="overflow-x-clip">
      <ScrollProgress />
      {/* hero */}
      <section ref={hero} className="relative">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_72%_45%,rgba(255,154,61,.12),transparent_55%)]" aria-hidden />
        <div className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:radial-gradient(var(--dot)_1px,transparent_1px)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" aria-hidden />
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-5 pb-16 pt-10 md:px-8 lg:min-h-[700px] lg:grid-cols-[1.08fr_1fr] lg:pb-20 lg:pt-12">
          <motion.div className="relative z-10" style={{ y: textY }}>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease }}
              className="mb-7 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs text-accent-2 backdrop-blur">
              <span className="relative flex h-2 w-2"><span className="absolute inset-0 animate-ping rounded-full bg-accent/70" /><span className="relative h-2 w-2 rounded-full bg-accent" /></span>
              Voice AI tutor for Indian students
            </motion.div>
            <h1 className="font-serif text-[clamp(44px,6vw,84px)] leading-[1.02] tracking-tight">
              <WordReveal text="The tutor that calls, listens, and remembers every mistake." highlight={["remembers"]} />
            </h1>
            <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8, duration: 0.5, ease }}
              className="mt-6 max-w-xl text-lg leading-relaxed text-muted md:text-xl">
              A 10-minute call in Hindi, English or Hinglish. Guru finds <em className="not-italic text-text">why</em> an answer went
              wrong, fixes it with hints — never the answer first — and checks it again tomorrow.
            </motion.p>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.95, duration: 0.5, ease }}
              className="mt-9 flex flex-wrap items-center gap-3">
              <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <Link href="/start" className="btn-primary group px-7 py-3.5 text-base shadow-[0_14px_44px_-12px_rgba(255,154,61,.75)]">
                  Start practising <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" aria-hidden />
                </Link>
              </motion.div>
              <a href="#how" className="btn-ghost px-6 py-3.5 text-base">See how it works</a>
            </motion.div>
            <motion.ul initial="hidden" animate="show" variants={{ hidden: {}, show: { transition: { staggerChildren: 0.08, delayChildren: 1.1 } } }}
              className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
              {ASSURANCES.map((a) => (
                <motion.li key={a} variants={{ hidden: { opacity: 0, y: 6 }, show: { opacity: 1, y: 0 } }} className="inline-flex items-center gap-1.5">
                  <Check size={15} className="text-m-high" aria-hidden /> {a}
                </motion.li>
              ))}
            </motion.ul>
            {phone && !phone.includes("80000 00000") && (
              <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-sm text-muted">
                <Phone size={14} aria-hidden /> Give a missed call: <span className="num text-text">{phone}</span>
              </div>
            )}
          </motion.div>
          <motion.div className="relative" style={{ y: heroY, opacity: heroFade }}
            initial={{ opacity: 0, y: 30, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.9, delay: 0.2, ease }}>
            <HeroCall />
          </motion.div>
        </div>
      </section>

      {/* measured facts + stack */}
      <section className="border-t border-line">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-px overflow-hidden px-5 md:grid-cols-4 md:px-8">
          {FACTS.map(([big, small], i) => (
            <motion.div key={small} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              transition={{ delay: i * 0.08, duration: 0.5, ease }} className="py-8">
              <div className="num text-2xl text-text md:text-3xl">{big}</div>
              <div className="mt-1 text-sm text-muted">{small}</div>
            </motion.div>
          ))}
        </div>
        <div className="mx-auto max-w-7xl px-5 pb-10 text-xs uppercase tracking-[0.18em] text-muted md:px-8">
          Powered by <span className="text-text">Bolna</span> voice calls · <span className="text-text">Sarvam</span> speech · <span className="text-text">Claude</span> reasoning
        </div>
      </section>

      <HowItWorks />

      {/* modes */}
      <section className="mx-auto max-w-7xl px-5 py-20 md:px-8 md:py-28">
        <motion.h2 {...reveal} className="max-w-3xl font-serif text-4xl leading-tight md:text-5xl">
          One tutor. Three ways to practise.
        </motion.h2>
        <motion.p {...reveal} className="mt-4 max-w-2xl text-lg text-muted">Pick a mode, or let Guru pick from your goal.</motion.p>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {MODES.map(({ icon: Icon, title, line, tag }, i) => (
            <motion.div key={title} {...reveal} transition={{ ...reveal.transition, delay: i * 0.08 }}
              whileHover={{ y: -6, rotateX: 3, rotateY: i === 0 ? 3 : i === 2 ? -3 : 0 }} style={{ transformPerspective: 900 }}
              className="card group relative overflow-hidden p-7 shadow-glow transition-colors hover:border-accent/40">
              <div className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full bg-accent/10 blur-3xl transition-opacity group-hover:opacity-100 md:opacity-60" aria-hidden />
              <Icon size={24} strokeWidth={1.5} className="text-accent" aria-hidden />
              <div className="mt-6 font-serif text-2xl">{title}</div>
              <p className="mt-2 text-muted">{line}</p>
              <p className="num mt-6 rounded-input border border-line bg-surface-2 px-3 py-2 text-xs text-accent-2">{tag}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* progress teaser */}
      <section className="border-t border-line">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-5 py-20 md:px-8 md:py-28 lg:grid-cols-2">
          <motion.div {...reveal}>
            <div className="label">Progress over time</div>
            <h2 className="mt-3 font-serif text-4xl leading-tight md:text-5xl">See the improvement. Day, week, month.</h2>
            <p className="mt-4 max-w-xl text-lg text-muted">
              After every call Guru saves what went well and what to improve, then tests it again tomorrow. Mastery, accuracy and
              self-reported confidence are tracked per goal, so students, teachers and parents see real change, not guesses.
            </p>
          </motion.div>
          <motion.div {...reveal} className="card p-7 shadow-glow" role="img" aria-label="Example: mastery rising from 30% on day 1 to 78% after a month">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-muted">Example · Linear equations mastery</span>
              <span className="num text-sm text-m-high">+48 pts</span>
            </div>
            {/* The chart box (always full size) watches the viewport and drives every bar via variants:
                a bar that starts at height 0 / scaleY 0 is never "in view" itself, so it would never animate. */}
            <motion.div className="mt-8 flex h-52 items-end gap-3" initial="hidden" whileInView="show"
              viewport={{ once: true, amount: 0.3 }}>
              {BARS.map((b, i) => (
                <div key={b.label} className="flex h-full flex-1 flex-col items-center gap-2">
                  <div className="flex w-full flex-1 flex-col items-center justify-end gap-1">
                    <span className="num text-[11px] text-muted">{Math.round(b.v * 100)}%</span>
                    <motion.div className="w-full origin-bottom rounded-t-md"
                      style={{ height: Math.round(b.v * 160), background: "linear-gradient(to top, rgba(255,154,61,.25), #FF9A3D)" }}
                      variants={{ hidden: { scaleY: 0 }, show: { scaleY: 1, transition: { duration: 0.8, delay: i * 0.1, ease } } }} />
                  </div>
                  <span className="num text-xs text-muted">{b.label}</span>
                </div>
              ))}
            </motion.div>
            <p className="mt-4 text-xs text-muted">Illustrative. Real numbers appear on each student&apos;s page.</p>
          </motion.div>
        </div>
      </section>

      {/* quote */}
      <section className="border-t border-line">
        <motion.blockquote {...reveal} className="mx-auto max-w-5xl px-5 py-24 text-center font-serif text-[clamp(32px,5vw,64px)] leading-[1.1] md:py-32">
          It doesn&apos;t just mark answers wrong. <span className="text-accent">It finds why.</span>
        </motion.blockquote>
        <p className="mx-auto -mt-12 max-w-2xl px-5 pb-24 text-center text-sm text-muted">
          Guru never guesses feelings from a voice. Confidence is what the student tells us, plus how they perform.
        </p>
      </section>

      {/* final call to action */}
      <section className="border-t border-line">
        <motion.div {...reveal} className="mx-auto max-w-7xl px-5 py-20 md:px-8">
          <div className="card border-gradient relative overflow-hidden px-8 py-14 text-center md:px-16">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,154,61,.16),transparent_65%)]" aria-hidden />
            <h2 className="relative font-serif text-4xl leading-tight md:text-6xl">Your first call takes <span className="text-shimmer">one minute</span>.</h2>
            <p className="relative mx-auto mt-4 max-w-xl text-lg text-muted">Pick Maths, English speaking or any topic. Talk in the language you like. Guru remembers the rest.</p>
            <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }} className="relative mt-8 inline-block">
              <Link href="/start" className="btn-primary px-8 py-3.5 text-base shadow-[0_12px_40px_-12px_rgba(255,154,61,.8)]">
                Start practising <ArrowRight size={16} aria-hidden />
              </Link>
            </motion.div>
          </div>
        </motion.div>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-8 text-sm text-muted md:px-8">
          <span>Built with Bolna, Sarvam and Claude</span>
          <span className="flex gap-4">
            <Link href="/privacy" className="hover:text-text">Privacy</Link>
            <Link href="/proof" className="hover:text-text">Proof</Link>
            <span>Guru Line · Bolna Buildathon 2026</span>
          </span>
        </div>
      </footer>
    </div>
  );
}
