// Browser -> Next.js proxy (/api/gl/*) -> FastAPI. The admin key is added server-side.
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const r = await fetch(`/api/gl/${path.replace(/^\//, "")}`, {
    method: init?.method || "GET",
    headers: init?.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, (j && (j.error || j.detail)) || `HTTP ${r.status}`);
  return j as T;
}

export const RAHUL = "11111111-1111-4111-8111-111111111111";
