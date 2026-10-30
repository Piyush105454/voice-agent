"use client";
import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, Check } from "lucide-react";
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

const ASSURANCES = [
  "No app needed — phone call first",
  "Works on any mobile or keypad phone",
  "Speak in Hindi or English",
  "Live research on official govt portals",
];

const ease = [0.2, 0.7, 0.2, 1] as const;
const reveal = { initial: { opacity: 0, y: 12 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true }, transition: { duration: 0.45, ease } };

const FACTS = [
  ["Any Qualification", "no Class 8, 10, or 12 limit"],
  ["Live Govt Search", "Gemini Google Search grounded"],
  ["Hindi & English", "natural spoken phone guidance"],
  ["Memory Graph", "remembers goals across calls"],
];

export default function Landing() {
  const hero = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: hero, offset: ["start start", "end start"] });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, 140]);
  const heroFade = useTransform(scrollYProgress, [0, 0.8], [1, 0]);
  const textY = useTransform(scrollYProgress, [0, 1], [0, -40]);

  return (
    <div className="overflow-x-clip">
      <ScrollProgress />
      {/* hero */}
      <section ref={hero} className="relative -mt-3 flex flex-col lg:min-h-[calc(100svh-5.25rem)]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_72%_45%,rgba(255,154,61,.12),transparent_55%)]" aria-hidden />
        <div className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:radial-gradient(var(--dot)_1px,transparent_1px)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" aria-hidden />
        <div className="mx-auto grid w-full max-w-7xl items-center gap-6 px-5 pb-4 pt-2 md:px-8 lg:flex-1 lg:grid-cols-[1.2fr_0.8fr] lg:gap-8">
          <motion.div className="relative z-10" style={{ y: textY }}>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease }}
              className="mb-3 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs text-accent-2 backdrop-blur">
              <span className="relative flex h-2 w-2"><span className="absolute inset-0 animate-ping rounded-full bg-accent/70" /><span className="relative h-2 w-2 rounded-full bg-accent" /></span>
              Guruji · Phone-First AI Career Mentor with Live Government Research
            </motion.div>
            <h1 className="font-serif text-[clamp(30px,3.4vw,50px)] leading-[1.05] tracking-tight [text-wrap:balance]">
              <WordReveal text="The career mentor that calls, researches, and remembers your goals." highlight={["remembers"]} />
            </h1>
            <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8, duration: 0.5, ease }}
              className="mt-3 max-w-3xl text-[15px] leading-relaxed text-muted md:text-base">
              Students give a missed call and speak naturally in Hindi or English. Whatever their educational qualification or interest, Guruji automatically researches verified Indian government courses, skill schemes, and scholarships in real time and updates a persistent Student Memory Graph.
            </motion.p>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.95, duration: 0.5, ease }}
              className="mt-4 flex flex-wrap items-center gap-3">
              <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <Link href="/live" className="btn-primary group px-6 py-3 text-base shadow-[0_14px_44px_-12px_rgba(255,154,61,.75)]">
                  Open Operator Console <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" aria-hidden />
                </Link>
              </motion.div>
              <Link href="/privacy" className="btn-ghost px-5 py-3 text-base">Privacy & Audit</Link>
            </motion.div>
            <motion.ul initial="hidden" animate="show" variants={{ hidden: {}, show: { transition: { staggerChildren: 0.08, delayChildren: 1.1 } } }}
              className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-sm text-muted">
              {ASSURANCES.map((a) => (
                <motion.li key={a} variants={{ hidden: { opacity: 0, y: 6 }, show: { opacity: 1, y: 0 } }} className="inline-flex items-center gap-1.5">
                  <Check size={15} className="text-m-high" aria-hidden /> {a}
                </motion.li>
              ))}
            </motion.ul>
          </motion.div>
          <motion.div className="relative" style={{ y: heroY, opacity: heroFade }}
            initial={{ opacity: 0, y: 30, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.9, delay: 0.2, ease }}>
            <div className="flex items-center justify-center lg:h-[470px]">
              <div className="w-full lg:origin-center lg:scale-[0.78]"><HeroCall /></div>
            </div>
          </motion.div>
        </div>

        {/* the four facts + portals now sit on the first screen, under the hero */}
        <div className="relative z-10 mt-auto border-t border-line">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-x-6 gap-y-2 px-5 py-3 md:grid-cols-4 md:px-8">
            {FACTS.map(([big, small], i) => (
              <motion.div key={small} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.2 + i * 0.08, duration: 0.45, ease }}>
                <div className="font-serif text-lg text-text md:text-xl">{big}</div>
                <div className="text-xs text-muted md:text-sm">{small}</div>
              </motion.div>
            ))}
          </div>
          <div className="mx-auto max-w-7xl px-5 pb-2.5 text-xs tracking-wide text-muted md:px-8">
            <span className="inline-block rounded-full border border-line bg-surface-2/60 px-3 py-1 text-muted">
              Live Grounding Across NCS (ncs.gov.in) · Skill India (PMKVY) · DGT / NCVT · AICTE / SWAYAM · National Scholarship Portal
            </span>
          </div>
        </div>
      </section>

      <HowItWorks />

      {/* bottom CTA card */}
      <section className="border-t border-line">
        <motion.div {...reveal} className="mx-auto max-w-7xl px-5 py-20 md:px-8">
          <div className="card border-gradient relative overflow-hidden px-8 py-14 text-center md:px-16">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,154,61,.16),transparent_65%)]" aria-hidden />
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3.5 py-1 text-xs text-accent-2 backdrop-blur">
              Grounded in Official Indian Government Portals · Live Memory Graph
            </div>
            <h2 className="relative font-serif text-4xl leading-tight md:text-6xl">
              Built for <span className="text-shimmer">phone-first</span> student mentorship.
            </h2>
            <p className="relative mx-auto mt-4 max-w-xl text-lg text-muted">
              Monitor live phone calls, inspect real-time student memory graphs, and run live Gemini Google Search government career research from the Operator Console.
            </p>
            <div className="relative mt-8 flex flex-wrap justify-center gap-3">
              <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                <Link href="/live" className="btn-primary px-8 py-3.5 text-base shadow-[0_12px_40px_-12px_rgba(255,154,61,.8)]">
                  Open Operator Console <ArrowRight size={16} aria-hidden />
                </Link>
              </motion.div>
              <Link href="/privacy" className="btn-ghost px-7 py-3.5 text-base">
                Privacy & Audit
              </Link>
            </div>
          </div>
        </motion.div>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-8 text-sm text-muted md:px-8">
          <span>Guruji · Phone-First Career Guidance with Live Government Research</span>
          <span className="flex gap-4">
            <Link href="/live" className="hover:text-text">Operator Console</Link>
            <Link href="/privacy" className="hover:text-text">Privacy & Audit</Link>
          </span>
        </div>
      </footer>
    </div>
  );
}
