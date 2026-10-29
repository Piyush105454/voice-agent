"use client";
import { Diamond, Inbox, TriangleAlert } from "lucide-react";
import { masteryBand, pretty } from "@/lib/format";

export function MasteryBar({ label, value, sub, outOf10 }: {
  label: string; value: number | null | undefined; sub?: string; outOf10?: boolean; // outOf10: show 0-10 (skills)
}) {
  const band = masteryBand(value);
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="truncate">{label}</span>
        <span className="num text-[13px] text-muted">
          {value == null ? "—" : outOf10 ? `${(value * 10).toFixed(1)}/10` : value.toFixed(2)} · <span style={{ color: band.color }}>{band.label}</span>
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-2" role="meter" aria-label={label}
        aria-valuemin={0} aria-valuemax={1} aria-valuenow={value ?? 0} aria-valuetext={band.label}>
        <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${(value ?? 0) * 100}%`, background: band.color }} />
      </div>
      {sub && <div className="text-xs text-muted">{sub}</div>}
    </div>
  );
}

export function MisconceptionChip({ id, name, strength }: { id: string; name?: string | null; strength?: number | null }) {
  return (
    <span className="chip border border-misc/40 bg-misc/10 text-misc" title={id}>
      <Diamond size={11} strokeWidth={2} aria-hidden />
      {name || pretty(id)}
      {strength != null && <span className="num opacity-80">· {strength.toFixed(2)}</span>}
    </span>
  );
}

export function LiveBadge({ live }: { live: boolean }) {
  return live ? (
    <span className="chip border border-accent/40 bg-accent/10 font-semibold tracking-wider text-accent">
      <span className="h-2 w-2 animate-livepulse rounded-full bg-accent" aria-hidden /> LIVE
    </span>
  ) : (
    <span className="chip border border-line text-muted">ENDED</span>
  );
}

export function Waveform({ active }: { active: boolean }) {
  return (
    <span className="inline-flex h-5 items-center gap-[3px]" aria-hidden>
      {[0.2, 0.5, 0.8, 1, 0.7, 0.4, 0.6, 0.3].map((d, i) => (
        <span key={i} className={`w-[3px] origin-center rounded-full bg-accent ${active ? "animate-wave" : ""}`}
          style={{ height: active ? `${8 + d * 12}px` : "4px", animationDelay: `${i * 0.09}s`, opacity: active ? 1 : 0.35 }} />
      ))}
    </span>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-muted">
      <Inbox size={22} strokeWidth={1.5} aria-hidden />
      <div className="text-sm text-text">{title}</div>
      {hint && <div className="max-w-sm text-xs">{hint}</div>}
      {action}
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center" role="alert">
      <TriangleAlert size={22} strokeWidth={1.5} className="text-m-low" aria-hidden />
      <div className="text-sm">Couldn&apos;t load this.</div>
      <div className="max-w-md text-xs text-muted">{message}</div>
      {retry && <button className="btn-ghost mt-2" onClick={retry}>Try again</button>}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-card bg-surface-2 ${className}`} aria-hidden />;
}

export function Panel({ title, right, children, className = "" }: { title: string; right?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`card p-5 ${className}`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="label">{title}</h2>
        {right}
      </div>
      {children}
    </section>
  );
}
