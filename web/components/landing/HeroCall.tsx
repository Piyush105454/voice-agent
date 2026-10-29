"use client";
// Hero: a real Guru call playing on a phone. The story loops (~20 s):
// incoming call -> live call with captions + waveform -> misconception found -> fixed with a hint -> parent update.
// Floating cards appear around the phone at the key moments. Mouse moves tilt the scene slightly (desktop).
// Reduced motion: the finished call is shown as a still.
import { AnimatePresence, motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { AlertTriangle, BellRing, CalendarClock, Check, Mic, Phone, PhoneOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type Line = { who: "guru" | "student"; text: string };
const SCRIPT: { at: number; line?: Line; card?: "mis" | "fixed" | "parent" | "recall" }[] = [
  { at: 3.2, line: { who: "guru", text: "Namaste Rahul! x + 5 = 12, x kya hoga?" } },
  { at: 6.2, line: { who: "student", text: "17?" } },
  { at: 7.0, card: "mis" },
  { at: 8.4, line: { who: "guru", text: "Chalo check karte hain. +5 ko dusri taraf le jaayein toh kya banega?" } },
  { at: 12.0, line: { who: "student", text: "Minus 5… toh 7!" } },
  { at: 12.8, card: "fixed" },
  { at: 14.0, line: { who: "guru", text: "Shabaash! Tumne inverse use kiya. Kal ise dobara try karenge." } },
  { at: 16.6, card: "parent" },
  { at: 17.6, card: "recall" },
];
const LOOP = 21;   // seconds
const ANSWER_AT = 2.4;

function useClock(reduce: boolean | null) {
  const [t, setT] = useState(reduce ? LOOP - 1 : 0);
  useEffect(() => {
    if (reduce) return;
    const start = performance.now();
    const id = setInterval(() => setT(((performance.now() - start) / 1000) % LOOP), 100);
    return () => clearInterval(id);
  }, [reduce]);
  return t;
}

function Waveform({ who, active }: { who: "guru" | "student" | null; active: boolean }) {
  const color = who === "student" ? "#3DD68C" : "#FF9A3D";
  return (
    <div className="flex h-10 items-center justify-center gap-[3px]" aria-hidden>
      {Array.from({ length: 28 }).map((_, i) => (
        <motion.span key={i} className="w-[3px] rounded-full" style={{ background: color, opacity: active ? 1 : 0.25 }}
          animate={active ? { height: [6, 8 + ((i * 37) % 26), 5, 10 + ((i * 53) % 20), 6] } : { height: 4 }}
          transition={active ? { duration: 0.9 + (i % 5) * 0.12, repeat: Infinity, ease: "easeInOut" } : { duration: 0.3 }} />
      ))}
    </div>
  );
}

function FloatCard({ show, className, children }: { show: boolean; className: string; children: React.ReactNode }) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div className={`absolute z-20 ${className}`} initial={{ opacity: 0, y: 14, scale: 0.92, filter: "blur(4px)" }}
          animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }} exit={{ opacity: 0, y: -8, scale: 0.96 }}
          transition={{ type: "spring", stiffness: 260, damping: 22 }}>
          <motion.div animate={{ y: [0, -5, 0] }} transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="glass rounded-2xl border border-line px-4 py-3 text-sm shadow-[0_20px_60px_-20px_rgba(0,0,0,.8)]">
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function HeroCall() {
  const reduce = useReducedMotion();
  const t = useClock(reduce);
  const ringing = t < ANSWER_AT;
  const lines = SCRIPT.filter((s) => s.line && s.at <= t).map((s) => s.line!);
  const cards = new Set(SCRIPT.filter((s) => s.card && s.at <= t).map((s) => s.card!));
  const last = SCRIPT.filter((s) => s.line && s.at <= t).at(-1);
  // someone is "speaking" for ~2.6 s after their line appears
  const speaking = last && t - last.at < 2.6 ? last.line!.who : null;
  const secs = Math.max(0, Math.floor(t - ANSWER_AT));
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { box.current?.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" }); }, [lines.length]);

  // gentle tilt toward the pointer
  const mx = useMotionValue(0), my = useMotionValue(0);
  const rx = useSpring(useTransform(my, [-0.5, 0.5], [6, -6]), { stiffness: 120, damping: 18 });
  const ry = useSpring(useTransform(mx, [-0.5, 0.5], [-8, 8]), { stiffness: 120, damping: 18 });
  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reduce) return;
    const r = e.currentTarget.getBoundingClientRect();
    mx.set((e.clientX - r.left) / r.width - 0.5);
    my.set((e.clientY - r.top) / r.height - 0.5);
  };

  return (
    <div className="relative mx-auto h-[600px] w-full max-w-[560px]" onMouseMove={onMove} onMouseLeave={() => { mx.set(0); my.set(0); }}
      style={{ perspective: 1200 }} role="img"
      aria-label="Animated example: Guru calls Rahul, finds the mistake 'adds instead of using the inverse', fixes it with a hint, and sends his parent an update.">
      {/* glow + soft rings behind the phone */}
      <div className="absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(255,154,61,.22),transparent_62%)] blur-2xl" aria-hidden />
      {[0, 1, 2].map((i) => (
        // centring via framer's x/y: an animated scale replaces the CSS transform, so -translate-* would be lost
        <motion.div key={i} aria-hidden className="absolute left-1/2 top-1/2 h-[300px] w-[300px] rounded-full border border-accent/30"
          style={{ x: "-50%", y: "-50%" }}
          animate={ringing && !reduce ? { scale: [1, 1.9], opacity: [0.5, 0] } : { scale: 1, opacity: 0 }}
          transition={{ duration: 2.2, repeat: Infinity, delay: i * 0.7, ease: "easeOut" }} />
      ))}

      <motion.div className="absolute inset-0" style={{ rotateX: rx, rotateY: ry, transformStyle: "preserve-3d" }}>
        {/* phone */}
        <div data-theme="dark" className="text-text absolute left-1/2 top-1/2 h-[560px] w-[280px] -translate-x-1/2 -translate-y-1/2 rounded-[44px] border border-[#2a2f3a] bg-[#0b0d11] p-[10px] shadow-[0_40px_120px_-30px_rgba(255,154,61,.35),0_30px_80px_-20px_rgba(0,0,0,.9)]">
          <div className="relative flex h-full flex-col overflow-hidden rounded-[36px] bg-gradient-to-b from-[#14171d] to-[#0a0b0e]">
            <div className="absolute left-1/2 top-2.5 h-6 w-24 -translate-x-1/2 rounded-full bg-black" aria-hidden />
            <AnimatePresence mode="wait">
              {ringing ? (
                <motion.div key="ring" className="flex flex-1 flex-col items-center justify-between px-6 pb-10 pt-20"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.97 }} transition={{ duration: 0.35 }}>
                  <div className="text-center">
                    <div className="text-xs uppercase tracking-[0.2em] text-muted">Incoming call</div>
                    <motion.div className="mx-auto mt-6 grid h-20 w-20 place-items-center rounded-full bg-gradient-to-br from-accent to-[#c2410c] font-serif text-3xl text-black"
                      animate={{ scale: [1, 1.06, 1] }} transition={{ duration: 1.2, repeat: Infinity }}>G</motion.div>
                    <div className="mt-4 font-serif text-2xl">Guru</div>
                    <div className="text-sm text-muted">AI tutor · Maths</div>
                  </div>
                  <div className="flex w-full justify-between px-4">
                    <div className="grid h-14 w-14 place-items-center rounded-full bg-m-low/90"><PhoneOff size={22} /></div>
                    <motion.div className="grid h-14 w-14 place-items-center rounded-full bg-m-high text-black"
                      animate={{ scale: [1, 1.12, 1], boxShadow: ["0 0 0 0 rgba(61,214,140,.6)", "0 0 0 14px rgba(61,214,140,0)", "0 0 0 0 rgba(61,214,140,0)"] }}
                      transition={{ duration: 1.1, repeat: Infinity }}><Phone size={22} /></motion.div>
                  </div>
                </motion.div>
              ) : (
                <motion.div key="call" className="flex flex-1 flex-col px-4 pb-5 pt-12"
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-accent to-[#c2410c] font-serif text-black">G</div>
                      <div>
                        <div className="text-sm leading-tight">Guru</div>
                        <div className="num text-[11px] text-m-high">● {String(Math.floor(secs / 60)).padStart(2, "0")}:{String(secs % 60).padStart(2, "0")}</div>
                      </div>
                    </div>
                    <span className="rounded-full border border-line px-2 py-0.5 text-[10px] text-muted">Hinglish</span>
                  </div>
                  <div className="mt-4"><Waveform who={speaking} active={!!speaking} /></div>
                  <div className="mt-1 text-center text-[11px] text-muted">{speaking === "student" ? "Rahul is speaking" : speaking ? "Guru is speaking" : "Listening…"}</div>
                  <div ref={box} className="mt-3 flex-1 space-y-2.5 overflow-hidden">
                    <AnimatePresence initial={false}>
                      {lines.map((l, i) => (
                        <motion.div key={i} layout initial={{ opacity: 0, y: 12, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                          transition={{ type: "spring", stiffness: 320, damping: 26 }} className={`flex ${l.who === "student" ? "justify-end" : ""}`}>
                          <div className={`max-w-[88%] rounded-2xl px-3 py-2 text-[13px] leading-snug ${
                            l.who === "student" ? "rounded-br-md bg-m-high/15 text-[#bdf5d8]" : "rounded-bl-md bg-surface-2 text-text"}`}>
                            {l.text}
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                  <div className="mt-3 flex justify-center gap-4">
                    <div className="grid h-11 w-11 place-items-center rounded-full bg-surface-2 text-muted"><Mic size={18} /></div>
                    <div className="grid h-11 w-11 place-items-center rounded-full bg-m-low/90"><PhoneOff size={18} /></div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* moments, floating around the phone */}
        <FloatCard show={cards.has("mis")} className="left-0 top-[18%] sm:-left-6">
          <div className="flex items-center gap-2 text-misc"><AlertTriangle size={15} /> <span className="font-medium">Misconception found</span></div>
          <div className="mt-0.5 text-xs text-muted">Adds instead of using the inverse</div>
        </FloatCard>
        <FloatCard show={cards.has("fixed")} className="right-0 top-[40%] sm:-right-8">
          <div className="flex items-center gap-2 text-m-high"><Check size={15} /> <span className="font-medium">Fixed with one hint</span></div>
          <div className="num mt-0.5 text-xs text-muted">Mastery 30% → <span className="text-m-high">62%</span></div>
        </FloatCard>
        <FloatCard show={cards.has("parent")} className="bottom-[16%] left-0 sm:-left-10">
          <div className="flex items-center gap-2"><BellRing size={15} className="text-accent" /> <span className="font-medium">Parent update sent</span></div>
          <div className="mt-0.5 font-deva text-xs text-muted">आज राहुल ने समीकरण हल किए…</div>
        </FloatCard>
        <FloatCard show={cards.has("recall")} className="bottom-[4%] right-0 sm:-right-4">
          <div className="flex items-center gap-2"><CalendarClock size={15} className="text-accent" /> <span className="font-medium">Tomorrow, 5:00 pm</span></div>
          <div className="mt-0.5 text-xs text-muted">5-min recall call on this mistake</div>
        </FloatCard>
      </motion.div>
    </div>
  );
}
