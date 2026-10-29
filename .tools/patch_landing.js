// One-off patch: landing page motion upgrade (scroll progress, word reveal, parallax hero, scrollytelling, CTA).
const fs = require("fs");
const p = __dirname + "/../web/app/page.tsx";
let s = fs.readFileSync(p, "utf8");
const rep = (a, b) => { if (!s.includes(a)) throw new Error("missing: " + a.slice(0, 80)); s = s.replace(a, b); };

rep(`import { motion } from "framer-motion";
import { Calculator, Compass, Languages, Phone } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";`, `import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, Calculator, Compass, Languages, Phone } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRef } from "react";
import HowItWorks from "@/components/landing/HowItWorks";
import { ScrollProgress, WordReveal } from "@/components/motion";`);

// facts we measured ourselves (no invented social proof)
rep(`const BARS = [`, `const FACTS = [
  ["~1.4 s", "to understand what you said"],
  ["3", "ways to practise"],
  ["हिं · EN", "Hindi, English or Hinglish"],
  ["Day → Month", "progress you can see"],
];

const BARS = [`);

rep(`  const phone = process.env.NEXT_PUBLIC_DEMO_PHONE;
`, `  const phone = process.env.NEXT_PUBLIC_DEMO_PHONE;
  const hero = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: hero, offset: ["start start", "end start"] });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, 140]);
  const heroFade = useTransform(scrollYProgress, [0, 0.8], [1, 0]);
  const textY = useTransform(scrollYProgress, [0, 1], [0, -40]);
`);

rep(`    <div className="overflow-x-hidden">
      {/* hero */}
      <section className="relative">`, `    <div className="overflow-x-clip">
      <ScrollProgress />
      {/* hero */}
      <section ref={hero} className="relative">`);

rep(`          <motion.div className="relative z-10" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease }}>`,
    `          <motion.div className="relative z-10" style={{ y: textY }}>`);
rep(`            <h1 className="font-serif text-[clamp(42px,6.2vw,88px)] leading-[1.0] tracking-tight">
              A tutor on a normal phone call that <span className="text-accent">remembers</span> every mistake.
            </h1>`, `            <h1 className="font-serif text-[clamp(42px,6.2vw,88px)] leading-[1.02] tracking-tight">
              <WordReveal text="A tutor on a normal phone call that remembers every mistake." highlight={["remembers"]} />
            </h1>`);
rep(`            <p className="mt-6 max-w-xl text-lg text-muted md:text-xl">`, `            <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.75, duration: 0.5, ease }}
              className="mt-6 max-w-xl text-lg text-muted md:text-xl">`);
rep(`              No app. No smartphone. Just a call. Guru learns how you think, then helps you improve, day after day.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-3">
              <Link href="/live" className="btn-primary px-6 py-3 text-base">Start practising</Link>
              <Link href="/live" className="btn-ghost px-6 py-3 text-base">See it live</Link>
            </div>`, `              No app. No smartphone. Just a call. Guru learns how you think, then helps you improve, day after day.
            </motion.p>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9, duration: 0.5, ease }}
              className="mt-10 flex flex-wrap items-center gap-3">
              <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <Link href="/live" className="btn-primary group px-6 py-3 text-base shadow-[0_12px_40px_-12px_rgba(255,154,61,.7)]">
                  Start practising <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" aria-hidden />
                </Link>
              </motion.div>
              <Link href="/live" className="btn-ghost px-6 py-3 text-base">See it live</Link>
            </motion.div>`);
rep(`          <div className="relative h-[380px] sm:h-[460px] lg:h-[620px]" aria-hidden>
            <Hero3D />
          </div>
        </div>
      </section>`, `          <motion.div className="relative h-[380px] sm:h-[460px] lg:h-[620px]" style={{ y: heroY, opacity: heroFade }}
            initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1.1, ease }} aria-hidden>
            <Hero3D />
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
      </section>`);

// numbered flow -> scrollytelling
const flowStart = s.indexOf("      {/* numbered flow */}");
const flowEnd = s.indexOf("      {/* modes */}");
if (flowStart < 0 || flowEnd < 0) throw new Error("flow block missing");
s = s.slice(0, flowStart) + "      <HowItWorks />\n\n" + s.slice(flowEnd);
s = s.replace(/const FLOW = \[[\s\S]*?\];\n\n/, "");

rep(`            <motion.div key={title} {...reveal} transition={{ ...reveal.transition, delay: i * 0.08 }}
              className="card group relative overflow-hidden p-7 shadow-glow transition-colors hover:border-accent/40">`,
    `            <motion.div key={title} {...reveal} transition={{ ...reveal.transition, delay: i * 0.08 }}
              whileHover={{ y: -6, rotateX: 3, rotateY: i === 0 ? 3 : i === 2 ? -3 : 0 }} style={{ transformPerspective: 900 }}
              className="card group relative overflow-hidden p-7 shadow-glow transition-colors hover:border-accent/40">`);

rep(`      <footer className="border-t border-line">`, `      {/* final call to action */}
      <section className="border-t border-line">
        <motion.div {...reveal} className="mx-auto max-w-7xl px-5 py-20 md:px-8">
          <div className="card border-gradient relative overflow-hidden px-8 py-14 text-center md:px-16">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,154,61,.16),transparent_65%)]" aria-hidden />
            <h2 className="relative font-serif text-4xl leading-tight md:text-6xl">Your first call takes <span className="text-shimmer">one minute</span>.</h2>
            <p className="relative mx-auto mt-4 max-w-xl text-lg text-muted">Pick Maths, English speaking or any topic. Talk in the language you like. Guru remembers the rest.</p>
            <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }} className="relative mt-8 inline-block">
              <Link href="/live" className="btn-primary px-8 py-3.5 text-base shadow-[0_12px_40px_-12px_rgba(255,154,61,.8)]">
                Start practising <ArrowRight size={16} aria-hidden />
              </Link>
            </motion.div>
          </div>
        </motion.div>
      </section>

      <footer className="border-t border-line">`);
fs.writeFileSync(p, s);
console.log("patched");
