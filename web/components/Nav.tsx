"use client";
// Floating "liquid glass" pill nav: centred, fixed 16px from the top, compact. Theme toggle inside.
import { AnimatePresence, motion } from "framer-motion";
import { Moon, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const LINKS = [
  { href: "/live", label: "Practise" },
  { href: "/teacher", label: "Teacher" },
  { href: "/proof", label: "Proof" },
  { href: "/privacy", label: "Privacy" },
];

function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light"), []);
  const flip = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("gl:theme", next); } catch {}
    setTheme(next);
  };
  return (
    <button onClick={flip} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      className="grid h-9 w-9 place-items-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-text">
      <AnimatePresence mode="wait" initial={false}>
        <motion.span key={theme} initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }}
          transition={{ duration: 0.2 }}>
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}

export default function Nav() {
  const path = usePathname();
  const [hover, setHover] = useState<string | null>(null);
  if (path.startsWith("/parent")) return null; // parent view stays minimal
  const active = LINKS.find((l) => path.startsWith(l.href))?.href ?? null;
  const pill = hover ?? active;

  return (
    <header className="pointer-events-none fixed inset-x-0 top-4 z-50 flex justify-center px-3">
      <motion.nav aria-label="Main" initial={{ y: -24, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.2, 0.7, 0.2, 1] }}
        className="liquid pointer-events-auto flex h-14 items-center gap-1 rounded-full py-1.5 pl-5 pr-1.5">
        <Link href="/" className="mr-2 flex items-center gap-2 whitespace-nowrap font-serif text-[19px] tracking-tight">
          <span className="relative inline-flex h-2.5 w-2.5">
            <span className="absolute inset-0 animate-ping rounded-full bg-accent/60" aria-hidden />
            <span className="relative inline-block h-2.5 w-2.5 rounded-full bg-accent" aria-hidden />
          </span>
          Guru <span className="italic text-accent">Line</span>
        </Link>
        <div className="hidden items-center md:flex" onMouseLeave={() => setHover(null)}>
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} onMouseEnter={() => setHover(l.href)}
              className={`relative rounded-full px-3.5 py-2 text-sm transition-colors ${active === l.href ? "text-text" : "text-muted hover:text-text"}`}
              aria-current={active === l.href ? "page" : undefined}>
              {pill === l.href && (
                <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-full bg-surface-2/80 ring-1 ring-line"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }} />
              )}
              <span className="relative z-10">{l.label}</span>
            </Link>
          ))}
        </div>
        <ThemeToggle />
        <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
          <Link href="/start" className="btn-primary h-11 px-5">Start practising</Link>
        </motion.div>
      </motion.nav>
    </header>
  );
}
