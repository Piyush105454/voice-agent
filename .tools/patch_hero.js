// One-off patch: replace the landing hero (3D graph) with the phone-call story hero + persuasive copy.
const fs = require("fs");
const p = __dirname + "/../web/app/page.tsx";
let s = fs.readFileSync(p, "utf8");
const rep = (a, b) => { if (!s.includes(a)) throw new Error("missing: " + a.slice(0, 80)); s = s.replace(a, b); };

rep(`import { ArrowRight, Calculator, Compass, Languages, Phone } from "lucide-react";
import dynamic from "next/dynamic";`, `import { ArrowRight, Calculator, Check, Compass, Languages, Phone } from "lucide-react";
import dynamic from "next/dynamic";`);
rep(`// three.js only in the browser, after first paint; a CSS glow holds the space while it loads
const Hero3D = dynamic(() => import("@/components/Hero3D"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-[radial-gradient(circle_at_center,rgba(255,154,61,.18),transparent_60%)]" />,
});`, `// the call animation is client-only; a soft glow holds its space during the first paint
const HeroCall = dynamic(() => import("@/components/landing/HeroCall"), {
  ssr: false,
  loading: () => <div className="h-[600px] w-full bg-[radial-gradient(circle_at_center,rgba(255,154,61,.16),transparent_60%)]" />,
});

// the doubts a parent or student has in the first five seconds, answered up front
const ASSURANCES = ["No app needed", "Works on any phone", "Hindi · English · Hinglish", "Parents get a summary"];`);

const start = s.indexOf(`        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_70%_40%`);
const endMarker = `            <Hero3D />
          </motion.div>
        </div>`;
const end = s.indexOf(endMarker) + endMarker.length;
if (start < 0 || end < endMarker.length) throw new Error("hero block not found");
const hero = `        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_72%_45%,rgba(255,154,61,.12),transparent_55%)]" aria-hidden />
        <div className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:radial-gradient(rgba(255,255,255,.07)_1px,transparent_1px)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" aria-hidden />
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
                <Link href="/live" className="btn-primary group px-7 py-3.5 text-base shadow-[0_14px_44px_-12px_rgba(255,154,61,.75)]">
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
        </div>`;
s = s.slice(0, start) + hero + s.slice(end);
fs.writeFileSync(p, s);

// give the scrollytelling section an anchor for "See how it works"
const h = __dirname + "/../web/components/landing/HowItWorks.tsx";
let t = fs.readFileSync(h, "utf8");
if (!t.includes('id="how"')) t = t.replace(`<section className="border-y border-line" aria-label="How it works">`, `<section id="how" className="scroll-mt-16 border-y border-line" aria-label="How it works">`);
fs.writeFileSync(h, t);
console.log("patched");
