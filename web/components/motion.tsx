"use client";
// Shared motion primitives: scroll reveals, staggered lists, count-up numbers, sliding-pill tabs, scroll progress.
// All of them respect prefers-reduced-motion (framer-motion's useReducedMotion).
import { animate, motion, useInView, useReducedMotion, useScroll, useSpring, type Variants } from "framer-motion";
import { useEffect, useRef, useState } from "react";

export const EASE = [0.2, 0.7, 0.2, 1] as const;

export function Reveal({ children, delay = 0, y = 16, className = "", as = "div" }: {
  children: React.ReactNode; delay?: number; y?: number; className?: string; as?: "div" | "section" | "li";
}) {
  const reduce = useReducedMotion();
  const M = motion[as];
  return (
    <M className={className} initial={reduce ? false : { opacity: 0, y }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }} transition={{ duration: 0.55, delay, ease: EASE }}>
      {children}
    </M>
  );
}

const container: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } } };
const item: Variants = {
  hidden: { opacity: 0, y: 18, scale: 0.98 },
  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.5, ease: EASE } },
};

export function Stagger({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} variants={container} initial={reduce ? "show" : "hidden"} whileInView="show"
      viewport={{ once: true, amount: 0.1 }}>
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <motion.div className={className} variants={item}>{children}</motion.div>;
}

/** Number that counts up when it scrolls into view. */
export function CountUp({ to, decimals = 0, suffix = "", duration = 1.2 }: { to: number; decimals?: number; suffix?: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [v, setV] = useState(reduce ? to : 0);
  useEffect(() => {
    if (!inView || reduce) return void setV(to);
    const c = animate(0, to, { duration, ease: EASE, onUpdate: setV });
    return () => c.stop();
  }, [inView, to, duration, reduce]);
  return <span ref={ref} className="num">{v.toFixed(decimals)}{suffix}</span>;
}

/** Segmented control with a pill that slides to the active option. */
export function PillTabs<T extends string>({ value, onChange, options, id, size = "md", label }: {
  value: T; onChange: (v: T) => void; options: { value: T; label: React.ReactNode }[]; id: string;
  size?: "sm" | "md"; label: string;
}) {
  return (
    <div className="relative inline-flex rounded-full border border-line bg-surface/60 p-1 backdrop-blur" role="tablist" aria-label={label}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button key={o.value} role="tab" aria-selected={active} onClick={() => onChange(o.value)}
            className={`relative rounded-full ${size === "sm" ? "px-3 py-1 text-sm" : "px-4 py-1.5 text-sm"} transition-colors ${active ? "text-text" : "text-muted hover:text-text"}`}>
            {active && (
              <motion.span layoutId={`pill-${id}`} className="absolute inset-0 rounded-full bg-surface-2 ring-1 ring-line"
                transition={{ type: "spring", stiffness: 420, damping: 34 }} />
            )}
            <span className="relative z-10 inline-flex items-center gap-1.5">{o.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/** Thin bar at the top of the page showing scroll progress. */
export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 28, mass: 0.3 });
  return <motion.div aria-hidden className="fixed inset-x-0 top-0 z-[70] h-[2px] origin-left bg-gradient-to-r from-accent via-accent-2 to-m-high" style={{ scaleX }} />;
}

/** Headline whose words rise in one after another. */
export function WordReveal({ text, className = "", highlight = [] as string[] }: { text: string; className?: string; highlight?: string[] }) {
  const reduce = useReducedMotion();
  const words = text.split(" ");
  return (
    <span className={className} aria-label={text}>
      {words.map((w, i) => (
        <span key={i} className="inline-block overflow-hidden pb-[0.08em] align-bottom" aria-hidden>
          <motion.span className={`inline-block ${highlight.includes(w.replace(/[.,]/g, "")) ? "hl" : ""}`}
            initial={reduce ? false : { y: "110%" }} animate={{ y: 0 }}
            transition={{ duration: 0.7, delay: 0.08 + i * 0.06, ease: EASE }}>
            {w}{i < words.length - 1 ? " " : ""}
          </motion.span>
        </span>
      ))}
    </span>
  );
}
