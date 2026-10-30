"use client";
// Searchable caller dropdown: one compact button instead of a chip per caller, so it stays tidy with any number of users.
import { Check, ChevronDown, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Student } from "@/lib/types";

const LANG: Record<string, string> = { hi: "Hindi", en: "English", "hi-en": "Hinglish" };
const sub = (s: Student) => [s.grade ? `Class ${s.grade}` : "Open profile", LANG[s.language] ?? s.language].filter(Boolean).join(" · ");

type Props = { students: Student[]; value: string; onChange: (id: string) => void; fallbackName?: string };

export default function CallerPicker({ students, value, onChange, fallbackName }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const listId = "caller-listbox";

  const current = students.find((s) => s.id === value);
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return students;
    return students.filter((s) => `${s.first_name} ${sub(s)}`.toLowerCase().includes(q));
  }, [students, query]);

  useEffect(() => setActive(0), [query, open]);
  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    const away = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  const choose = (id: string) => { onChange(id); setOpen(false); setQuery(""); };
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") { setOpen(false); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setActive((i) => Math.min(i + 1, shown.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Enter" && shown[active]) { e.preventDefault(); choose(shown[active].id); }
  };

  return (
    <div ref={root} className="relative" onKeyDown={onKey}>
      <button type="button" onClick={() => setOpen((o) => !o)} aria-haspopup="listbox" aria-expanded={open} aria-controls={listId}
        className="flex h-9 min-w-[16rem] items-center justify-between gap-3 rounded-input border border-line bg-surface-2 px-3 text-left text-sm transition-colors hover:border-accent/50 focus:border-accent focus:outline-none">
        <span className="truncate">
          <span className="font-medium">{current?.first_name ?? fallbackName ?? "Choose a caller"}</span>
          {current && <span className="ml-2 text-xs text-muted">{sub(current)}</span>}
        </span>
        <ChevronDown size={15} className={`shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-2 w-[22rem] max-w-[90vw] overflow-hidden rounded-2xl border border-line bg-[var(--bg)] shadow-glow ring-1 ring-black/5">
          <div className="flex items-center gap-2 border-b border-line px-3 py-2.5">
            <Search size={15} className="text-muted" aria-hidden />
            <input ref={input} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by name, class or language"
              aria-label="Search callers" role="combobox" aria-expanded aria-controls={listId} aria-autocomplete="list"
              className="w-full bg-transparent text-sm text-text outline-none placeholder:text-muted" />
          </div>
          <ul id={listId} role="listbox" className="max-h-72 overflow-y-auto py-1">
            {shown.length === 0 && <li className="px-4 py-6 text-center text-sm text-muted">No caller matches “{query}”</li>}
            {shown.map((s, i) => (
              <li key={s.id} role="option" aria-selected={s.id === value}>
                <button type="button" onClick={() => choose(s.id)} onMouseEnter={() => setActive(i)}
                  className={`flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm ${i === active ? "bg-surface-2" : ""}`}>
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{s.first_name}</span>
                    <span className="block truncate text-xs text-muted">{sub(s)}</span>
                  </span>
                  {s.id === value && <Check size={15} className="shrink-0 text-accent" aria-hidden />}
                </button>
              </li>
            ))}
          </ul>
          <div className="border-t border-line px-4 py-2 text-[11px] text-muted">{students.length} caller profile{students.length === 1 ? "" : "s"} · ↑ ↓ to move, Enter to select</div>
        </div>
      )}
    </div>
  );
}
