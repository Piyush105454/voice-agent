# Guru Line in ONE container: the Python API (private, 127.0.0.1:8765) and the Next.js dashboard (public $PORT).
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
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 \
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
