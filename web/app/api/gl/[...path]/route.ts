// Server-side proxy to the FastAPI backend. The admin key is injected here and never reaches the browser.
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const API = process.env.API_INTERNAL_URL || "http://localhost:8000";
// Browser-callable paths only (no Bolna webhooks, no admin graph rebuild).
const ALLOWED = [
  /^students(\/[\w-]+(\/(graph|progress|memory|overview))?)?$/,
  /^students\/[\w-]+\/memory\/[\w-]+$/,
  /^students\/[\w-]+\/(goals|skills|coach-feedback|journal)$/,
  /^sessions\/[\w-]+\/feed$/,
  /^live\/current$/,
  /^teacher\/overview$/,
  /^parent\/[\w-]+$/,
  /^privacy\/[\w-]+$/,
  /^proof$/,
  /^events(\/stream)?$/,
  /^demo\/(replay|reset)$/,
  /^voice\/(call|status|reset_bolna)$/,
  /^simulate(\/(confidence|end))?$/,
  /^web-call\/(start|turn|end)$/,
];

async function proxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join("/");
  if (!ALLOWED.some((rx) => rx.test(path))) {
    return Response.json({ error: "not allowed" }, { status: 404 });
  }
  const url = `${API}/${path}${req.nextUrl.search}`;
  const init: RequestInit & { duplex?: "half" } = {
    method: req.method,
    headers: {
      "X-Admin-Key": process.env.ADMIN_KEY || "",
      ...(req.headers.get("content-type") ? { "Content-Type": req.headers.get("content-type")! } : {}),
    },
    cache: "no-store",
  };
  // raw bytes, not text: /web-call/turn uploads audio as multipart (the boundary is in content-type)
  if (!["GET", "HEAD"].includes(req.method)) init.body = await req.arrayBuffer();
  let upstream: Response | undefined;
  for (let attempt = 0; attempt < 2 && !upstream; attempt++) {
    try {
      upstream = await fetch(url, init);
    } catch {
      if (!["GET", "HEAD"].includes(req.method)) break;   // never replay a POST/DELETE
    }
  }
  if (!upstream) {
    return Response.json({ error: "API unreachable. Is the backend running on " + API + "?" }, { status: 502 });
  }
  const headers = new Headers({ "Content-Type": upstream.headers.get("content-type") || "application/json" });
  if (path === "events/stream") {
    headers.set("Cache-Control", "no-cache, no-transform");
    headers.set("X-Accel-Buffering", "no");
  }
  return new Response(upstream.body, { status: upstream.status, headers });
}

export { proxy as GET, proxy as POST, proxy as DELETE };
