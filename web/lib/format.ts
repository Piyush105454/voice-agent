// Mastery is never shown by colour alone: every value also gets a word label.
export function masteryBand(p: number | null | undefined): { label: string; color: string; key: "low" | "mid" | "high" | "none" } {
  if (p === null || p === undefined) return { label: "Not started", color: "var(--line)", key: "none" };
  if (p < 0.4) return { label: "Needs practice", color: "var(--m-low)", key: "low" };
  if (p < 0.7) return { label: "Building", color: "var(--m-mid)", key: "mid" };
  return { label: "Strong", color: "var(--m-high)", key: "high" };
}

export const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);
export const dec = (v: number | null | undefined, d = 2) => (v === null || v === undefined ? "—" : v.toFixed(d));

export function ago(iso: string | null | undefined): string {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  const d = Math.floor(s / 86400);
  return d === 1 ? "yesterday" : `${d} days ago`;
}

export function clock(fromIso: string, toIso?: string | null): string {
  const s = Math.max(0, Math.floor(((toIso ? new Date(toIso).getTime() : Date.now()) - new Date(fromIso).getTime()) / 1000));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export const pretty = (id: string | null | undefined) => (id ? id.replace(/_/g, " ") : "");
