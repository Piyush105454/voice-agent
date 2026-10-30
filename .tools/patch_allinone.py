from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:80])
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")


# ---- API: /health says which database it is really using (host only, never the password); graph is optional
edit("api/main.py", [
    ('''@app.get("/health")
def health():
    checks: dict[str, str] = {}''', '''@app.get("/", include_in_schema=False)
def root():
    return {"service": "Guru Line API", "health": "/health", "docs": "/docs"}


@app.get("/health")
def health():
    from urllib.parse import urlparse
    host = urlparse(settings.database_url).hostname or "?"
    checks: dict[str, str] = {}'''),
    ('''    ok = all(v == "ok" for v in checks.values())
    voice = voice_router.status()
    return JSONResponse({"ok": ok, **checks, "voice": {"active": voice["active"], "mode": voice["mode"]}},
                        status_code=200 if ok else 503)''',
     '''    ok = all(v == "ok" for v in checks.values())
    voice = voice_router.status()
    body = {"ok": ok, **checks, "database_host": host, "voice": {"active": voice["active"], "mode": voice["mode"]}}
    if host in ("localhost", "127.0.0.1"):
        body["hint"] = ("DATABASE_URL is not reaching this service: it is using the built-in localhost default. "
                        "Set DATABASE_URL on THIS service and redeploy.")
    # Postgres is the source of truth; the graph is a derived index, so a missing graph must not take the service down
    return JSONResponse(body, status_code=200 if checks["postgres"] == "ok" else 503)'''),
])

# ---- dashboard: forward the paths the public internet needs (Bolna tools/webhook, browser-call page) to the API
edit("web/next.config.mjs", [
    ('''  poweredByHeader: false,
};''', '''  poweredByHeader: false,
  // One public URL serves the dashboard AND the API's public endpoints (all-in-one deployment).
  async rewrites() {
    const api = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      { source: "/bolna/:path*", destination: `${api}/bolna/:path*` },
      { source: "/missed_call", destination: `${api}/missed_call` },
      { source: "/call", destination: `${api}/call` },
      { source: "/web-call/:path*", destination: `${api}/web-call/:path*` },
      { source: "/health", destination: `${api}/health` },
    ];
  },
};'''),
])

Path("Dockerfile").write_text('''# Guru Line in ONE container: the Python API (private, 127.0.0.1:8765) and the Next.js dashboard (public $PORT).
# The dashboard forwards /bolna/*, /web-call/*, /call, /health to the API, so one URL serves everything:
#   - Render / Railway / Fly: the default build uses this file, no settings needed. Set the env vars from .env.example.
#   - Bolna's PUBLIC_BASE_URL is simply this service's URL.

# ---- 1. build the dashboard
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
# ipv4first: Next downloads the Google fonts at build time and some networks have broken IPv6
ENV NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--dns-result-order=ipv4first API_INTERNAL_URL=http://127.0.0.1:8765
RUN npm run build

# ---- 2. runtime: Python + the Node binary
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 \\
    API_INTERNAL_URL=http://127.0.0.1:8765
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=web /usr/local/bin/node /usr/local/bin/node
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY api/ api/
COPY sql/ sql/
COPY scripts/ scripts/
COPY --from=web /web/.next/standalone/ ./web/
COPY --from=web /web/.next/static ./web/.next/static
COPY start.sh /app/start.sh
EXPOSE 10000
CMD ["bash", "/app/start.sh"]
''', encoding="utf-8", newline="\n")

Path("start.sh").write_text('''#!/bin/bash
# API on a private port; the dashboard owns the public $PORT (Render sets it; 10000 by default).
# One API worker: in-process state (Bolna cooldown, browser-call sessions) lives in memory.
cd /app/api
uvicorn main:app --host 127.0.0.1 --port 8765 --workers 1 --proxy-headers --forwarded-allow-ips '*' &
cd /app/web
HOSTNAME=0.0.0.0 PORT="${PORT:-10000}" node server.js &
# if either process dies, stop the container so the platform restarts it
wait -n
exit $?
''', encoding="utf-8", newline="\n")

Path(".dockerignore").write_text(""".git
.venv
.tools
.env
.env.*
!.env.example
tests
**/__pycache__
**/*.pyc
**/*.log
web/node_modules
web/.next
""", encoding="utf-8", newline="\n")
print("ok")
